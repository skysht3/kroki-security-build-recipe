#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-kroki-secure:0.34.0-flat}"
if (( $# > 0 )); then shift; fi
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:latest}"

# A read-only bind mount of docker.sock still grants powerful Docker API access.
# Run only a trusted Trivy image; pin its digest for hardened environments.
docker run --rm \
  --volume /var/run/docker.sock:/var/run/docker.sock:ro \
  --volume kroki-trivy-cache:/root/.cache/trivy \
  "$TRIVY_IMAGE" image \
  --scanners vuln "$@" "$IMAGE"
