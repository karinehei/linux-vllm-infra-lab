#!/bin/bash
#SBATCH --job-name=cpu-test
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=512M
#SBATCH --time=00:05:00
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

set -euo pipefail

echo "=== Slurm CPU test job ==="
echo "job_id=${SLURM_JOB_ID:-unknown}"
echo "host=$(hostname -f 2>/dev/null || hostname)"
echo "date=$(date -Is 2>/dev/null || date)"
echo "partition=${SLURM_JOB_PARTITION:-unknown}"
echo "cpus_on_node=${SLURM_CPUS_ON_NODE:-unknown}"

echo
echo "=== uname ==="
uname -a

echo
echo "=== simple workload ==="
# Trivial CPU work so the job is more than an empty script
python3 - <<'PY' || python - <<'PY'
print("cpu-test: ok")
for i in range(3):
    print(f"tick {i}")
PY

echo
echo "=== done ==="
