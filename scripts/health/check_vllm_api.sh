#!/usr/bin/env bash
# Probe local vLLM OpenAI-compatible API (repo helper; Ansible installs a host copy).
set -euo pipefail

BASE_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000}"
TIMEOUT="${VLLM_HEALTH_TIMEOUT:-5}"

if curl -fsS --max-time "${TIMEOUT}" "${BASE_URL}/health" >/dev/null; then
  echo "OK: ${BASE_URL}/health"
  exit 0
fi

if curl -fsS --max-time "${TIMEOUT}" "${BASE_URL}/v1/models" >/dev/null; then
  echo "OK: ${BASE_URL}/v1/models"
  exit 0
fi

echo "ERROR: vLLM not healthy at ${BASE_URL}"
exit 1
