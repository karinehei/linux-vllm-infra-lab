# Tests

| Suite | Path | CI |
|-------|------|----|
| Unit + config validation | `tests/unit/` | Static CI (GitHub-hosted) |
| GPU / API / inference / benchmark | `tests/integration/` | Lab host only (manual) |

Full policy and commands: [`docs/testing.md`](../docs/testing.md).

```bash
# Static (no GPU)
pytest tests/unit -v

# Integration (GPU host + running vLLM)
export VLLM_BASE_URL=http://127.0.0.1:8000
./tests/integration/run_on_gpu_host.sh
```
