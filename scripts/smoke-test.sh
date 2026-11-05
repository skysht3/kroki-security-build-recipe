#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${KROKI_URL:-http://127.0.0.1:8001}}"
BASE_URL="${BASE_URL%/}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

curl --fail --silent --show-error "$BASE_URL/health" >/dev/null
printf 'PASS /health\n'

check_svg() {
  local format="$1" content="$2" output="$TMP_DIR/$1.svg"
  printf '%s\n' "$content" \
    | curl --fail --silent --show-error \
        --header 'Content-Type: text/plain' \
        --data-binary @- \
        "$BASE_URL/$format/svg" --output "$output"
  grep -q '<svg' "$output" || {
    printf 'FAIL %s: response did not contain SVG\n' "$format" >&2
    return 1
  }
  printf 'PASS %s -> SVG\n' "$format"
}

check_svg plantuml $'@startuml\nAlice -> Bob: Hello\n@enduml'
check_svg d2 'a -> b: hello'
check_svg goat $'+---+\n| A |\n+---+'
