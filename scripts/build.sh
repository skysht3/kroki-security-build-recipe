#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
IMAGE_TAG="${1:-kroki-secure:0.34.0-local}"

docker build --platform linux/amd64 --progress=plain \
  --file Dockerfile --tag "$IMAGE_TAG" .
printf 'Built: %s\n' "$IMAGE_TAG"
