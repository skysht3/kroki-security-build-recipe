#!/usr/bin/env python3
"""Flatten a package-cleaned Linux image, preserving its image configuration."""

import argparse
import io
import json
import re
import signal
import subprocess
import sys
import tarfile
import uuid


BUILD_PACKAGES = {"build-essential", "gcc", "g++", "libc6-dev", "linux-libc-dev"}
RESTORED = {"Env", "Entrypoint", "Cmd", "WorkingDir", "User", "ExposedPorts", "Labels", "StopSignal"}


def docker(*args, **kwargs):
    return subprocess.run(["docker", *args], check=True, **kwargs)


def inspect(image):
    return json.loads(docker("image", "inspect", "--", image, capture_output=True, text=True).stdout)[0]


def require_new_tag(tag):
    if not re.fullmatch(r"[a-z0-9][a-z0-9._:/-]*:[A-Za-z0-9_][A-Za-z0-9_.-]*", tag):
        raise ValueError("Output must be an explicit repository:tag (no digest or wildcard)")
    if docker("image", "ls", "--quiet", "--filter", f"reference={tag}",
              capture_output=True, text=True).stdout.strip():
        raise ValueError(f"Refusing to overwrite existing image: {tag}")


def quote(value):
    # Dockerfile ENV/LABEL expansion must not interpret literal dollars or quotes.
    if any(c in value for c in "\r\n\0"):
        raise ValueError("Multiline/NUL configuration cannot be restored safely")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$") + '"'


def normalized(config):
    # Docker versions may omit empty fields or serialize them as null/[]/{}.
    # In particular, an absent WorkingDir must never become '/'.
    return {k: v for k, v in config.items() if v is not None and v != ""
            and v != [] and v != {} and v is not False}


def import_changes(config):
    for key, value in normalized(config).items():
        if key not in RESTORED:
            raise ValueError(f"Unsupported image Config.{key}; refusing lossy export/import")
    changes = []
    seen = set()
    for item in config.get("Env") or []:
        key, value = item.split("=", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in seen:
            raise ValueError("Unsupported or duplicate environment key")
        seen.add(key)
        changes.append(f"ENV {key}={quote(value)}")
    for key, value in (config.get("Labels") or {}).items():
        changes.append(f"LABEL {quote(key)}={quote(value)}")
    for key in ("Entrypoint", "Cmd"):
        if config.get(key):
            changes.append(f"{key.upper()} {json.dumps(config[key], ensure_ascii=True)}")
    for key in ("WorkingDir", "User", "StopSignal"):
        if config.get(key):
            value = config[key]
            # These commands have different quoting rules. Restrict to literal tokens.
            if not re.fullmatch(r"[A-Za-z0-9_./:@+-]+", value):
                raise ValueError(f"Unsupported characters in Config.{key}")
            if key == "WorkingDir" and not value.startswith("/"):
                raise ValueError("WorkingDir must be absolute")
            instruction = "WORKDIR" if key == "WorkingDir" else key.upper()
            changes.append(f"{instruction} {value}")
    for port in config.get("ExposedPorts") or {}:
        if not re.fullmatch(r"[0-9]+/(tcp|udp|sctp)", port):
            raise ValueError("Unsupported ExposedPorts entry")
        changes.append(f"EXPOSE {port}")
    return [arg for change in changes for arg in ("--change", change)]


def check_packages(container):
    archive = docker("container", "cp", f"{container}:/var/lib/dpkg/status", "-",
                     capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        member = tar.getmember("status")
        with tar.extractfile(member) as status:
            paragraphs = status.read().decode("utf-8").split("\n\n")
    installed = set()
    for paragraph in paragraphs:
        fields = dict(line.split(": ", 1) for line in paragraph.splitlines()
                      if ": " in line and not line.startswith(" "))
        if fields.get("Status", "").endswith(" ok installed"):
            installed.add(fields["Package"])
    if not installed:
        raise ValueError("No installed packages found in dpkg status; cannot verify cleanup")
    remaining = sorted(installed & BUILD_PACKAGES)
    if remaining:
        raise ValueError(f"Remove build packages before flattening: {', '.join(remaining)}")


def flatten(source, target):
    require_new_tag(target)
    original = inspect(source)
    if original["Os"] != "linux" or original.get("OsVersion") or original.get("OsFeatures"):
        raise ValueError("Only Linux images without OS-specific features are supported")
    platform = "/".join(filter(None, (original["Os"], original["Architecture"], original.get("Variant"))))
    changes = import_changes(original["Config"])
    container = f"kroki-flatten-{uuid.uuid4().hex}"
    imported_id = None
    exporter = None
    created = False
    published = False
    try:
        # Only image Config above is authoritative. Creation overrides are never copied.
        created = True
        docker("container", "create", "--name", container, "--entrypoint=/bin/true",
               original["Id"], stdout=subprocess.DEVNULL)
        check_packages(container)
        exporter = subprocess.Popen(["docker", "container", "export", container], stdout=subprocess.PIPE)
        result = subprocess.run(["docker", "image", "import", f"--platform={platform}", *changes, "-"],
                                stdin=exporter.stdout, capture_output=True, text=True)
        exporter.stdout.close()
        output = result.stdout.strip()
        if re.fullmatch(r"sha256:[a-f0-9]{64}", output):
            imported_id = output
        export_status = exporter.wait()
        if result.returncode or export_status or not imported_id:
            raise RuntimeError(f"export/import failed (export={export_status}, import={result.returncode}): "
                               f"{result.stderr.strip()}")
        actual = inspect(imported_id)
        expected_config = normalized(original["Config"])
        actual_config = normalized(actual["Config"])
        if expected_config != actual_config:
            keys = sorted(k for k in expected_config.keys() | actual_config.keys()
                          if expected_config.get(k) != actual_config.get(k))
            raise ValueError(f"Image configuration changed: {', '.join(keys)}")
        for key in ("Os", "Architecture", "Variant"):
            if (original.get(key) or "") != (actual.get(key) or ""):
                raise ValueError(f"Image platform changed: {key}")
        if actual["Size"] >= original["Size"]:
            raise ValueError("Flattened image is not smaller than the source image")
        require_new_tag(target)
        docker("image", "tag", imported_id, target)
        published = True
    finally:
        if exporter is not None:
            if exporter.stdout is not None:
                exporter.stdout.close()
            if exporter.poll() is None:
                exporter.terminate()
                exporter.wait()
        # Cleanup failures propagate; they must not be reported as success.
        try:
            if created:
                docker("container", "rm", "--force", "--volumes", container, stdout=subprocess.DEVNULL)
        finally:
            if imported_id and not published:
                docker("image", "rm", imported_id, stdout=subprocess.DEVNULL)
    print(f"Config preserved; {original['Size']} -> {actual['Size']} bytes")
    print(f"Flattened: {target}")


def interrupted(_signum, _frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Layered image after package cleanup")
    parser.add_argument("target", help="New local repository:tag; existing tags are rejected")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        flatten(args.source, args.target)
    except (ValueError, RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
