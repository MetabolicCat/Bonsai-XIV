#!/bin/bash
# The full gate: what CI runs, and what `make check` runs. Each tool
# invocation lives in the Makefile; this only sequences them.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for step in lock-check lint typecheck shellcheck ui-check test; do
    echo "=== ${step} ==="
    make -C "$repo_root" --no-print-directory "$step"
done

echo "=== All checks passed ==="
