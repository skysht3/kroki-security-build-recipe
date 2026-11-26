#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if (( $# > 1 )); then
  printf 'Usage: %s [image-tag]\n' "$0" >&2
  exit 2
fi
IMAGE_TAG="${1:-kroki-secure:0.37.1}"
existing="$(docker image ls --quiet --filter "reference=$IMAGE_TAG")"
if [[ -n "$existing" ]]; then
  printf 'Refusing to overwrite existing image: %s\n' "$IMAGE_TAG" >&2
  exit 1
fi
docker build --platform linux/amd64 --progress=plain \
  --file Dockerfile --tag "$IMAGE_TAG" .
printf 'Built: %s\n' "$IMAGE_TAG"
