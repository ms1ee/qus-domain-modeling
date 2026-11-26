#!/usr/bin/env bash
set -euo pipefail
PRD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PRD_PYTHON="${PRDBENCH_PYTHON:-/home/kg/.venvs/prdbench/bin/python}"
export PYTHONDONTWRITEBYTECODE=1
exec "$PRD_PYTHON" -u "$PRD_ROOT/generate/run_batch.py" "$@"
