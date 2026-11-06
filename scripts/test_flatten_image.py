"""Configuration and failure-path regression tests; no Docker daemon required."""

import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch


spec = importlib.util.spec_from_file_location("flatten_image", Path(__file__).with_name("flatten-image.py"))
flatten = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flatten)


class ConfigurationTests(unittest.TestCase):
    def test_image_fields_and_literal_environment(self):
        changes = flatten.import_changes({
            "Env": ['EMPTY=', 'LITERAL=$HOME "quoted" \\path', 'EQUALS=a=b'],
            "Entrypoint": ["/bin/sh", "-c", "exec tool $OPTIONS"],
            "Cmd": ["arg with spaces"], "User": "1000:1000", "WorkingDir": "/app",
            "ExposedPorts": {"8000/tcp": {}, "8001/udp": {}},
            "Labels": {"label": 'literal $HOME "quoted"'}, "StopSignal": "SIGTERM",
        })[1::2]
        self.assertIn('ENV EMPTY=""', changes)
        self.assertIn('ENV LITERAL="\\$HOME \\"quoted\\" \\\\path"', changes)
        self.assertIn('ENV EQUALS="a=b"', changes)
        self.assertIn('ENTRYPOINT ["/bin/sh", "-c", "exec tool $OPTIONS"]', changes)
        self.assertIn('CMD ["arg with spaces"]', changes)
        self.assertIn('LABEL "label"="literal \\$HOME \\"quoted\\""', changes)
        self.assertIn("USER 1000:1000", changes)
        self.assertIn("WORKDIR /app", changes)
        self.assertIn("STOPSIGNAL SIGTERM", changes)

    def test_absent_defaults_are_not_invented(self):
        self.assertEqual(flatten.import_changes({"User": "kroki"}), ["--change", "USER kroki"])
        self.assertEqual(flatten.normalized({"WorkingDir": "", "Cmd": None, "Labels": {}}), {})
        self.assertNotEqual(flatten.normalized({}), flatten.normalized({"WorkingDir": "/"}))

    def test_lossy_configuration_is_rejected(self):
        for key, value in {
            "Volumes": {"/data": {}}, "Healthcheck": {"Test": ["NONE"]},
            "Shell": ["/bin/bash", "-c"], "OnBuild": ["RUN true"],
            "Hostname": "container-default", "AttachStdout": True,
            "StopTimeout": 0, "ArgsEscaped": True, "FutureField": "unknown",
        }.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                flatten.import_changes({key: value})

    def test_ambiguous_values_are_rejected(self):
        for config in ({"Env": ["A=1", "A=2"]}, {"Env": ["A=one\ntwo"]},
                       {"Env": ["bad key=value"]}, {"WorkingDir": "relative"},
                       {"User": "user\nLABEL evil=true"}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                flatten.import_changes(config)

    @patch.object(flatten, "docker")
    def test_existing_tag_is_rejected(self, docker):
        docker.return_value.stdout = "existing-image-id\n"
        with self.assertRaisesRegex(ValueError, "overwrite"):
            flatten.require_new_tag("example:new")

    def test_only_explicit_tags_are_allowed(self):
        for tag in ("example", "example:*", "example@sha256:abc", "--option"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                flatten.require_new_tag(tag)

    @patch.object(flatten, "docker")
    def test_package_cleanup_is_verified_from_filesystem(self, docker):
        def archive(contents):
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode="w") as tar:
                entry = tarfile.TarInfo("status")
                entry.size = len(contents)
                tar.addfile(entry, io.BytesIO(contents))
            return data.getvalue()

        docker.return_value.stdout = archive(b"Package: libc6\nStatus: install ok installed\n")
        flatten.check_packages("temporary-container")
        docker.return_value.stdout = archive(b"Package: linux-libc-dev\nStatus: install ok installed\n")
        with self.assertRaisesRegex(ValueError, "linux-libc-dev"):
            flatten.check_packages("temporary-container")


class FailureTests(unittest.TestCase):
    def exercise(self, *, export_status=0, import_status=0, mismatch=False,
                 package_failure=False, interrupt=False, cleanup_failure=False):
        image_id = "sha256:" + "a" * 64
        original = {"Id": "source-id", "Os": "linux", "Architecture": "amd64",
                    "Config": {"User": "kroki"}, "Size": 100}
        actual = {**original, "Size": 80}
        if mismatch:
            actual["Config"] = {"User": "kroki", "WorkingDir": "/"}
        exporter = MagicMock()
        exporter.wait.return_value = export_status
        exporter.poll.return_value = 0
        result = subprocess.CompletedProcess([], import_status, image_id + "\n", "failure" if import_status else "")
        with patch.object(flatten, "require_new_tag"), \
             patch.object(flatten, "inspect", side_effect=[original, actual]), \
             patch.object(flatten, "check_packages", side_effect=ValueError("packages") if package_failure else None), \
             patch.object(flatten, "docker") as docker, \
             patch.object(flatten.subprocess, "Popen", return_value=exporter), \
             patch.object(flatten.subprocess, "run", side_effect=KeyboardInterrupt if interrupt else None,
                          return_value=result):
            if cleanup_failure:
                def call(*args, **_kwargs):
                    if args[:2] == ("container", "rm"):
                        raise subprocess.CalledProcessError(1, ["docker", "container", "rm"])
                docker.side_effect = call
            with self.assertRaises((RuntimeError, ValueError, KeyboardInterrupt, subprocess.CalledProcessError)):
                flatten.flatten("source:tag", "output:tag")
            self.assertTrue(any(call.args[:2] == ("container", "rm") for call in docker.call_args_list))
            if export_status or import_status or mismatch:
                self.assertTrue(any(call.args[:2] == ("image", "rm") for call in docker.call_args_list))
                self.assertFalse(any(call.args[:2] == ("image", "tag") for call in docker.call_args_list))

    def test_export_failure_does_not_publish_partial_import(self):
        self.exercise(export_status=1)

    def test_import_failure_is_not_success(self):
        self.exercise(import_status=1)

    def test_configuration_mismatch_is_not_success(self):
        self.exercise(mismatch=True)

    def test_package_failure_cleans_container(self):
        self.exercise(package_failure=True)

    def test_interruption_cleans_container(self):
        self.exercise(interrupt=True)

    def test_cleanup_failure_is_not_success(self):
        self.exercise(cleanup_failure=True)


@unittest.skipUnless(os.environ.get("KROKI_DOCKER_TESTS") == "1", "Set KROKI_DOCKER_TESTS=1 for Docker tests")
class DockerTests(unittest.TestCase):
    def test_real_import_and_rejections(self):
        prefix = f"kroki-flatten-test:{uuid.uuid4().hex}"
        tags = []
        before = flatten.docker("container", "ls", "--all", "--quiet",
                                "--filter", "name=kroki-flatten-", capture_output=True).stdout
        try:
            with tempfile.TemporaryDirectory() as directory:
                context = Path(directory)
                (context / "large").write_bytes(b"x" * 65536)
                (context / "small").write_text("payload\n")
                (context / "status").write_text("Package: libc6\nStatus: install ok installed\n")
                recipe = '''FROM scratch
COPY large /payload
COPY small /payload
COPY status /var/lib/dpkg/status
ENV PATH=/fixture EMPTY="" EQUALS="a=b" LITERAL="\\$HOME \\"quoted\\" \\\\path"
LABEL literal="\\$HOME \\"quoted\\" \\\\path"
ENTRYPOINT ["/original", "arg with spaces", "$LITERAL"]
CMD ["command argument"]
USER 1000:1000
WORKDIR /work
EXPOSE 8000/tcp 8001/udp
STOPSIGNAL SIGTERM
'''
                def build(suffix, contents):
                    tag = f"{prefix}-{suffix}"
                    (context / "Dockerfile").write_text(contents)
                    flatten.docker("build", "--quiet", "--platform=linux/amd64", "--tag", tag,
                                   directory, capture_output=True)
                    tags.append(tag)
                    return tag

                base = build("base", recipe)
                # Dockerfile CMD may add the unsupported legacy ArgsEscaped flag.
                # Construct an import-native base to exercise supported Cmd configs.
                config = flatten.inspect(base)["Config"]
                config.pop("ArgsEscaped", None)
                container = flatten.docker("container", "create", "--entrypoint=/fixture", base,
                                           capture_output=True, text=True).stdout.strip()
                try:
                    archive = flatten.docker("container", "export", container, capture_output=True).stdout
                finally:
                    flatten.docker("container", "rm", container, stdout=subprocess.DEVNULL)
                imported = f"{prefix}-imported"
                tags.append(imported)
                flatten.docker("image", "import", "--platform=linux/amd64", *flatten.import_changes(config),
                               "-", imported, input=archive, capture_output=True)
                source = build("source", f"FROM {imported}\nCOPY large /payload\nCOPY small /payload\n")
                expected = flatten.inspect(source)["Config"]
                self.assertIn('LITERAL=$HOME "quoted" \\path', expected["Env"])
                target = f"{prefix}-flat"
                tags.append(target)
                flatten.flatten(source, target)
                self.assertEqual(flatten.normalized(expected), flatten.normalized(flatten.inspect(target)["Config"]))
                self.assertEqual(len(flatten.inspect(target)["RootFS"]["Layers"]), 1)
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    flatten.flatten(source, target)
                for suffix, directive in (("volume", "VOLUME /data"),
                                          ("health", "HEALTHCHECK CMD /probe")):
                    unsupported = build(suffix, f"FROM {source}\n{directive}\n")
                    with self.assertRaisesRegex(ValueError, "Unsupported"):
                        flatten.flatten(unsupported, f"{prefix}-rejected")
                (context / "status").write_text("Package: linux-libc-dev\nStatus: install ok installed\n")
                unclean = build("unclean", f"FROM {source}\nCOPY status /var/lib/dpkg/status\n")
                with self.assertRaisesRegex(ValueError, "linux-libc-dev"):
                    flatten.flatten(unclean, f"{prefix}-rejected")
                after = flatten.docker("container", "ls", "--all", "--quiet",
                                       "--filter", "name=kroki-flatten-", capture_output=True).stdout
                self.assertEqual(before, after)
        finally:
            for tag in reversed(tags):
                subprocess.run(["docker", "image", "rm", tag], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    unittest.main()
