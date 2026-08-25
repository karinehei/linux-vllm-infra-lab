#!/usr/bin/env bash
# gpu-status.sh — NVIDIA GPU summary via nvidia-smi
# Exit: 0 when data reported (or tooling absent with --allow-missing),
#       1 when tooling missing without --allow-missing or query fails.
set -euo pipefail

ALLOW_MISSING=0

usage() {
  cat <<'EOF'
Usage: gpu-status.sh [--allow-missing]

Reports GPU model, VRAM total/used, utilization, and temperature when available.
With --allow-missing, exits 0 and prints a warning if nvidia-smi is unavailable.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-missing) ALLOW_MISSING=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if ! command -v nvidia-smi >/dev/null 2>&1; then
  msg="nvidia-smi not found — NVIDIA driver tools unavailable"
  if [[ "${ALLOW_MISSING}" -eq 1 ]]; then
    echo "WARN: ${msg}"
    exit 0
  fi
  echo "ERROR: ${msg}" >&2
  exit 1
fi

if ! nvidia-smi >/dev/null 2>&1; then
  msg="nvidia-smi failed — GPU unavailable or driver not loaded"
  if [[ "${ALLOW_MISSING}" -eq 1 ]]; then
    echo "WARN: ${msg}"
    exit 0
  fi
  echo "ERROR: ${msg}" >&2
  exit 1
fi

# CSV query; temperature may be "[N/A]" on some devices.
query='name,memory.total,memory.used,utilization.gpu,temperature.gpu'
if ! rows="$(nvidia-smi --query-gpu="${query}" --format=csv,noheader,nounits 2>/dev/null)"; then
  echo "ERROR: nvidia-smi query failed" >&2
  exit 1
fi

trim() {
  # shellcheck disable=SC2001
  echo "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

echo "=== GPU status ==="
idx=0
while IFS=',' read -r name mem_total mem_used util temp; do
  name="$(trim "${name}")"
  mem_total="$(trim "${mem_total}")"
  mem_used="$(trim "${mem_used}")"
  util="$(trim "${util}")"
  temp="$(trim "${temp}")"

  echo "GPU ${idx}:"
  echo "  model:          ${name}"
  echo "  vram_total_mib: ${mem_total}"
  echo "  vram_used_mib:  ${mem_used}"
  echo "  utilization_pct:${util}"
  if [[ -n "${temp}" && "${temp}" != "[N/A]" && "${temp}" != "N/A" ]]; then
    echo "  temperature_c:  ${temp}"
  else
    echo "  temperature_c:  unavailable"
  fi
  idx=$((idx + 1))
done <<<"${rows}"

if [[ "${idx}" -eq 0 ]]; then
  echo "ERROR: no GPU rows returned" >&2
  exit 1
fi

exit 0
