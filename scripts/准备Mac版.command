#!/bin/bash
set -euo pipefail
base="$(cd "$(dirname "$0")" && pwd)"
exec /bin/bash "$base/mac-prepare-v2.sh" "$@"
