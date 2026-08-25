# Operational scripts

Production-style Bash helpers for the vLLM inference host. Prefer running on the GPU node (or via SSH).

```
scripts/
├── health-check.sh      # service + HTTP /health + /v1/models (exit 0/1)
├── gpu-status.sh        # nvidia-smi summary (graceful without NVIDIA)
├── service-status.sh    # systemd enable/active/PID summary
├── disk-status.sh       # free space + model/cache sizes (warn threshold)
├── diagnose.sh          # combined report (secrets redacted)
├── test-inference.py    # OpenAI-compatible chat smoke test
└── health/check_vllm_api.sh   # minimal HTTP-only probe
```

## Quick use

```bash
./scripts/health-check.sh
./scripts/gpu-status.sh
./scripts/service-status.sh
./scripts/disk-status.sh --warn-percent 85
./scripts/diagnose.sh | tee /tmp/vllm-diagnose.txt
```

Exit codes: **0** = OK/healthy (or GPU tooling absent with `gpu-status.sh --allow-missing`); **non-zero** = problem.

Environment knobs (optional):

| Variable | Used by | Default |
|----------|---------|---------|
| `VLLM_BASE_URL` | health-check | from `/etc/vllm/vllm.env` or `http://127.0.0.1:8000` |
| `VLLM_ENV_FILE` | several | `/etc/vllm/vllm.env` |
| `VLLM_MODEL_PATH` / `VLLM_CACHE_PATH` | disk-status | `/var/lib/vllm/models` / `cache` |
| `DISK_WARN_PERCENT` | disk-status / diagnose | `85` |
| `VLLM_HEALTH_TIMEOUT` | health-check | `5` |

`diagnose.sh` never prints raw HF tokens; journal lines are redacted for common secret patterns.
