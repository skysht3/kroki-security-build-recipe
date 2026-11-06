#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
IMAGE_TAG="${1:-kroki-secure:0.34.0-flat}"
LAYERED_TAG="${2:-${IMAGE_TAG}-layered}"

command -v python3 >/dev/null
if [[ "$IMAGE_TAG" == "$LAYERED_TAG" ]]; then
  printf 'Final and layered tags must differ\n' >&2
  exit 1
fi
for tag in "$IMAGE_TAG" "$LAYERED_TAG"; do
  existing="$(docker image ls --quiet --filter "reference=$tag")"
  if [[ -n "$existing" ]]; then
    printf 'Refusing to overwrite existing image: %s\n' "$tag" >&2
    exit 1
  fi
done

docker build --platform linux/amd64 --progress=plain \
  --file Dockerfile --tag "$LAYERED_TAG" .
./scripts/flatten-image.py "$LAYERED_TAG" "$IMAGE_TAG"
printf 'Built: %s\n' "$IMAGE_TAG"
