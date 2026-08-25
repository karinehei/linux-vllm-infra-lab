#!/usr/bin/env bash
# Run GPU / live-API integration tests on a lab host (not GitHub-hosted runners).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

export VLLM_BASE_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000}"

echo "Running integration tests against ${VLLM_BASE_URL}"
echo "Host GPU probe:"
./scripts/gpu-status.sh --allow-missing || true

python3 -m pytest tests/integration -m "integration and gpu" -v "$@"
