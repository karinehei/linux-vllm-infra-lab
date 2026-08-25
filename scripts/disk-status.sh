#!/usr/bin/env bash
# disk-status.sh — filesystem free space + model/cache directory sizes
# Exit: 0 OK, 1 when usage exceeds warning threshold or paths missing (strict)
set -euo pipefail

ENV_FILE="${VLLM_ENV_FILE:-/etc/vllm/vllm.env}"
WARN_PCT="${DISK_WARN_PERCENT:-85}"
MODEL_PATH="${VLLM_MODEL_PATH:-}"
CACHE_PATH="${VLLM_CACHE_PATH:-}"
STRICT_MISSING=0

usage() {
  cat <<'EOF'
Usage: disk-status.sh [--warn-percent N] [--model-path PATH] [--cache-path PATH]
                      [--strict-missing]

Checks filesystem free space and sizes of model/cache directories.
Warning threshold default: 85% used (override with DISK_WARN_PERCENT or --warn-percent).
Exit 0 if under threshold; 1 if any monitored filesystem is at/above threshold.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --warn-percent) WARN_PCT="${2:?}"; shift 2 ;;
    --model-path) MODEL_PATH="${2:?}"; shift 2 ;;
    --cache-path) CACHE_PATH="${2:?}"; shift 2 ;;
    --strict-missing) STRICT_MISSING=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

read_env_key() {
  local key="$1"
  [[ -r "${ENV_FILE}" ]] || return 0
  grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -n1 | cut -d= -f2- || true
}

[[ -n "${MODEL_PATH}" ]] || MODEL_PATH="$(read_env_key VLLM_MODEL_PATH)"
[[ -n "${CACHE_PATH}" ]] || CACHE_PATH="$(read_env_key VLLM_CACHE_PATH)"
MODEL_PATH="${MODEL_PATH:-/var/lib/vllm/models}"
CACHE_PATH="${CACHE_PATH:-/var/lib/vllm/cache}"

human_size() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "missing"
    return 0
  fi
  du -sh "${path}" 2>/dev/null | awk '{print $1}'
}

echo "=== Disk status ==="
echo "warn_threshold_percent: ${WARN_PCT}"

status=0
seen_mps=""

echo
echo "-- filesystems --"
for path in / "${MODEL_PATH}" "${CACHE_PATH}"; do
  [[ -e "${path}" ]] || continue
  mp="$(df -P "${path}" 2>/dev/null | awk 'NR==2 {print $6}')"
  [[ -n "${mp}" ]] || continue
  case " ${seen_mps} " in
    *" ${mp} "*) continue ;;
  esac
  seen_mps="${seen_mps} ${mp}"

  used_pct="$(df -P "${path}" 2>/dev/null | awk 'NR==2 {gsub(/%/,"",$5); print $5}')"
  avail="$(df -Pk "${path}" 2>/dev/null | awk 'NR==2 {print $4}')"
  echo "mount=${mp} used=${used_pct}% avail_1k_blocks=${avail}"
  if [[ "${used_pct}" =~ ^[0-9]+$ ]] && (( used_pct >= WARN_PCT )); then
    echo "WARN: ${mp} is at ${used_pct}% (>= ${WARN_PCT}%)"
    status=1
  fi
done

echo
echo "-- vLLM directories --"
for label_path in "models:${MODEL_PATH}" "cache:${CACHE_PATH}"; do
  label="${label_path%%:*}"
  path="${label_path#*:}"
  if [[ ! -e "${path}" ]]; then
    echo "${label}: path=${path} size=missing"
    if [[ "${STRICT_MISSING}" -eq 1 ]]; then
      status=1
    fi
    continue
  fi
  echo "${label}: path=${path} size=$(human_size "${path}")"
done

if [[ "${status}" -eq 0 ]]; then
  echo
  echo "OK: disk usage under ${WARN_PCT}% warning threshold"
else
  echo
  echo "ERROR: disk warning threshold exceeded or required paths missing"
fi
exit "${status}"
