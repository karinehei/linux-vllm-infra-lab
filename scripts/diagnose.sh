#!/usr/bin/env bash
# diagnose.sh — collect troubleshooting info without leaking secrets
# Exit: 0 if collection completed; 1 if critical health checks fail (still prints report)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="${VLLM_SERVICE_NAME:-vllm}"
ENV_FILE="${VLLM_ENV_FILE:-/etc/vllm/vllm.env}"
LOG_LINES="${DIAG_LOG_LINES:-80}"
DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-85}"

usage() {
  cat <<'EOF'
Usage: diagnose.sh [--log-lines N]

Collects OS, kernel, container runtime, NVIDIA, systemd, disk, and API health.
Redacts token/password/secret values. Safe to attach to lab tickets.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log-lines) LOG_LINES="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

section() {
  echo
  echo "======== $* ========"
}

run_script() {
  local script="$1"
  shift
  if [[ -x "${SCRIPT_DIR}/${script}" ]]; then
    bash "${SCRIPT_DIR}/${script}" "$@" || true
  elif [[ -f "${SCRIPT_DIR}/${script}" ]]; then
    bash "${SCRIPT_DIR}/${script}" "$@" || true
  else
    echo "WARN: missing ${SCRIPT_DIR}/${script}"
  fi
}

redact_line() {
  # Redact assignment values for sensitive keys; leave key names visible.
  sed -E \
    -e 's/\b(HF_TOKEN|HUGGING_FACE_HUB_TOKEN|PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|AWS_SECRET_ACCESS_KEY)[=:][[:space:]]*[^[:space:]]+/\1=<REDACTED>/gI' \
    -e 's/(Bearer[[:space:]]+)[A-Za-z0-9._\-]+/\1<REDACTED>/g'
}

echo "=== vLLM lab diagnose ==="
echo "timestamp: $(date -Is 2>/dev/null || date)"
echo "host: $(hostname -f 2>/dev/null || hostname)"

section "Operating system"
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "name: ${NAME:-unknown}"
  echo "version: ${VERSION:-${VERSION_ID:-unknown}}"
  echo "id: ${ID:-unknown}"
else
  uname -a
fi
echo "uname: $(uname -a)"

section "Kernel"
echo "release: $(uname -r)"
echo "machine: $(uname -m)"

section "Container runtime"
if command -v podman >/dev/null 2>&1; then
  echo "podman: $(podman --version 2>/dev/null | head -n1)"
  podman info --format '{{.Host.OCIRuntime.Name}} {{.Host.Arch}}' 2>/dev/null || true
elif command -v docker >/dev/null 2>&1; then
  echo "docker: $(docker --version 2>/dev/null | head -n1)"
  docker info --format '{{.ServerVersion}} {{.OSType}}/{{.Architecture}}' 2>/dev/null || true
else
  echo "WARN: neither podman nor docker found"
fi

section "NVIDIA state"
run_script gpu-status.sh --allow-missing

section "systemd service status"
run_script service-status.sh --service "${SERVICE_NAME}"

section "Recent service logs (redacted, last ${LOG_LINES} lines)"
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u "${SERVICE_NAME}" -n "${LOG_LINES}" --no-pager 2>/dev/null | redact_line || echo "WARN: no journal entries"
else
  echo "WARN: journalctl not available"
fi

section "Disk space"
DISK_WARN_PERCENT="${DISK_WARN_PERCENT}" run_script disk-status.sh --warn-percent "${DISK_WARN_PERCENT}"

section "API / health"
run_script health-check.sh

section "Safe config snapshot"
if [[ -r /etc/vllm/vllm.json ]]; then
  echo "-- /etc/vllm/vllm.json --"
  cat /etc/vllm/vllm.json
else
  echo "WARN: /etc/vllm/vllm.json not readable"
fi

if [[ -r "${ENV_FILE}" ]]; then
  echo
  echo "-- ${ENV_FILE} (redacted) --"
  # Drop obvious secret keys entirely; redact anything that still looks sensitive.
  grep -Ev '^(HF_TOKEN|HUGGING_FACE_HUB_TOKEN)=' "${ENV_FILE}" | redact_line || true
else
  echo "WARN: ${ENV_FILE} not readable"
fi

section "Summary"
health_rc=0
bash "${SCRIPT_DIR}/health-check.sh" >/dev/null 2>&1 || health_rc=$?
svc_rc=0
bash "${SCRIPT_DIR}/service-status.sh" >/dev/null 2>&1 || svc_rc=$?

echo "service_exit: ${svc_rc} (0=active)"
echo "health_exit: ${health_rc} (0=healthy)"
if [[ "${health_rc}" -eq 0 && "${svc_rc}" -eq 0 ]]; then
  echo "OVERALL: OK"
  exit 0
fi
echo "OVERALL: NEEDS ATTENTION"
exit 1
