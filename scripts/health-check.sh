#!/usr/bin/env bash
# health-check.sh — vLLM service + OpenAI-compatible API probe
# Exit: 0 healthy, non-zero unhealthy
set -euo pipefail

SERVICE_NAME="${VLLM_SERVICE_NAME:-vllm}"
ENV_FILE="${VLLM_ENV_FILE:-/etc/vllm/vllm.env}"
TIMEOUT="${VLLM_HEALTH_TIMEOUT:-5}"
BASE_URL="${VLLM_BASE_URL:-}"

usage() {
  cat <<'EOF'
Usage: health-check.sh [--base-url URL] [--timeout SECONDS] [--service NAME]

Checks systemd unit (or container process), HTTP /health, and /v1/models.
Exit 0 if healthy; non-zero if unhealthy.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="${2:?}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    --service) SERVICE_NAME="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

read_env_key() {
  local key="$1"
  [[ -r "${ENV_FILE}" ]] || return 0
  # Only read known keys; never echo secrets from the env file.
  grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -n1 | cut -d= -f2- || true
}

if [[ -z "${BASE_URL}" ]]; then
  host="$(read_env_key VLLM_HOST)"
  port="$(read_env_key VLLM_PORT)"
  host="${host:-127.0.0.1}"
  port="${port:-8000}"
  # Env may bind 0.0.0.0 — probe via loopback in that case.
  if [[ "${host}" == "0.0.0.0" || "${host}" == "::" || "${host}" == "*" ]]; then
    host="127.0.0.1"
  fi
  BASE_URL="http://${host}:${port}"
fi
BASE_URL="${BASE_URL%/}"

ok() { echo "OK: $*"; }
fail() { echo "ERROR: $*" >&2; }

failures=0

# --- service / process ---
service_ok=0
if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
    ok "systemd unit '${SERVICE_NAME}' is active"
    service_ok=1
  else
    state="$(systemctl is-active "${SERVICE_NAME}" 2>/dev/null || true)"
    echo "WARN: systemd unit '${SERVICE_NAME}' is not active (state=${state:-unknown})"
  fi
fi

if [[ "${service_ok}" -eq 0 ]]; then
  if command -v podman >/dev/null 2>&1 && podman ps --format '{{.Names}}' 2>/dev/null | grep -qx 'vllm'; then
    ok "podman container 'vllm' is running"
    service_ok=1
  elif command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'vllm'; then
    ok "docker container 'vllm' is running"
    service_ok=1
  elif pgrep -f '[v]llm' >/dev/null 2>&1; then
    ok "vllm-related process found"
    service_ok=1
  else
    fail "no active vLLM service/container/process found"
    failures=$((failures + 1))
  fi
fi

http_get() {
  local url="$1"
  curl -fsS --connect-timeout "${TIMEOUT}" --max-time "${TIMEOUT}" "${url}"
}

# --- HTTP API ---
if ! command -v curl >/dev/null 2>&1; then
  fail "curl is required for API checks"
  exit 1
fi

health_url="${BASE_URL}/health"
models_url="${BASE_URL}/v1/models"

models_body="$(mktemp)"
trap 'rm -f "${models_body}"' EXIT

api_reachable=0
if http_get "${health_url}" >/dev/null 2>&1; then
  ok "HTTP ${health_url}"
  api_reachable=1
else
  echo "WARN: HTTP ${health_url} failed (timeout=${TIMEOUT}s); checking /v1/models"
fi

if http_get "${models_url}" >"${models_body}" 2>/dev/null; then
  if grep -q '"data"' "${models_body}" 2>/dev/null || grep -q '"id"' "${models_body}" 2>/dev/null; then
    ok "HTTP ${models_url}"
    api_reachable=1
  else
    fail "${models_url} returned unexpected payload"
    failures=$((failures + 1))
  fi
else
  fail "HTTP ${models_url} failed (timeout=${TIMEOUT}s)"
  failures=$((failures + 1))
fi

if [[ "${api_reachable}" -eq 0 ]]; then
  fail "HTTP API unreachable at ${BASE_URL}"
  failures=$((failures + 1))
fi

if [[ "${failures}" -gt 0 ]]; then
  echo "UNHEALTHY (${failures} check(s) failed) base_url=${BASE_URL}"
  exit 1
fi

echo "HEALTHY base_url=${BASE_URL}"
exit 0
