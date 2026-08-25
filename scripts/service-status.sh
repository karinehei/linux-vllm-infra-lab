#!/usr/bin/env bash
# service-status.sh — concise systemd / container status for vLLM
# Exit: 0 if active, 1 otherwise (2 usage error)
set -euo pipefail

SERVICE_NAME="${VLLM_SERVICE_NAME:-vllm}"

usage() {
  cat <<'EOF'
Usage: service-status.sh [--service NAME]

Prints enablement, active state, main PID, and a short systemctl summary.
Exit 0 when the unit is active; 1 when inactive/failed/missing.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service) SERVICE_NAME="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

echo "=== Service status (${SERVICE_NAME}) ==="

if ! command -v systemctl >/dev/null 2>&1; then
  echo "WARN: systemctl not available"
  if command -v podman >/dev/null 2>&1 && podman ps --format '{{.Names}}' 2>/dev/null | grep -qx 'vllm'; then
    echo "container: podman vllm running"
    podman ps --filter name=^vllm$ --format 'table {{.ID}}\t{{.Status}}\t{{.Ports}}'
    exit 0
  fi
  if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'vllm'; then
    echo "container: docker vllm running"
    docker ps --filter name=^vllm$ --format 'table {{.ID}}\t{{.Status}}\t{{.Ports}}'
    exit 0
  fi
  echo "ERROR: cannot determine vLLM service state"
  exit 1
fi

enabled="$(systemctl is-enabled "${SERVICE_NAME}" 2>/dev/null || echo unknown)"
active="$(systemctl is-active "${SERVICE_NAME}" 2>/dev/null || echo unknown)"
failed="$(systemctl is-failed "${SERVICE_NAME}" 2>/dev/null || echo unknown)"

echo "enabled: ${enabled}"
echo "active:  ${active}"
echo "failed:  ${failed}"

if systemctl show "${SERVICE_NAME}" >/dev/null 2>&1; then
  main_pid="$(systemctl show -p MainPID --value "${SERVICE_NAME}" 2>/dev/null || echo 0)"
  nrestarts="$(systemctl show -p NRestarts --value "${SERVICE_NAME}" 2>/dev/null || echo unknown)"
  result="$(systemctl show -p Result --value "${SERVICE_NAME}" 2>/dev/null || echo unknown)"
  echo "main_pid: ${main_pid}"
  echo "nrestarts: ${nrestarts}"
  echo "result: ${result}"
  echo
  systemctl status "${SERVICE_NAME}" --no-pager -l -n 10 2>/dev/null || true
fi

if [[ "${active}" == "active" ]]; then
  exit 0
fi
exit 1
