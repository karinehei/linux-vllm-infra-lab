#!/bin/bash
#SBATCH --job-name=gpu-test
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --gres=gpu:1
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

set -euo pipefail

echo "=== Slurm GPU test job ==="
echo "job_id=${SLURM_JOB_ID:-unknown}"
echo "host=$(hostname -f 2>/dev/null || hostname)"
echo "date=$(date -Is 2>/dev/null || date)"
echo "partition=${SLURM_JOB_PARTITION:-unknown}"
echo "gres=${SLURM_JOB_GRES:-unknown}"
echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"

echo
echo "=== nvidia-smi ==="
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: nvidia-smi not found on allocated node" >&2
  exit 1
fi
nvidia-smi

echo
echo "=== allocation sanity ==="
# Fail closed if the scheduler did not place us on a GPU context
if [[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GRES:-}" ]]; then
  echo "ERROR: CUDA_VISIBLE_DEVICES and SLURM_JOB_GRES both empty; check GRES/gres.conf" >&2
  exit 1
fi

echo
echo "=== done (GPU visible to job) ==="
