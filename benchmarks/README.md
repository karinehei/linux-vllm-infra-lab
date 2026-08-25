# vLLM benchmarks

Reproducible load against a **live** OpenAI-compatible vLLM endpoint.

## Important: examples vs measurements

| Artifact | Meaning |
|----------|---------|
| [`result.example.json`](result.example.json) | **Example schema only** — placeholders / zeros, not real numbers |
| `python … --dry-run-schema` | Prints the same kind of example schema |
| `benchmarks/results/*.json` | **Collected measurements** from a live run (`result_type: collected_measurement`) |

This project does **not** ship fabricated benchmark scores.

## Run

```bash
# Default: end-to-end latency + req/s (+ tokens/s when usage is present)
python3 benchmarks/benchmark_vllm.py \
  --url http://127.0.0.1:8000 \
  --requests 100 \
  --concurrency 4 \
  --max-tokens 64

# Also measure time-to-first-token and decode generation tokens/s (streaming)
python3 benchmarks/benchmark_vllm.py \
  --url http://127.0.0.1:8000 \
  --requests 50 \
  --concurrency 4 \
  --max-tokens 64 \
  --ttft
```

Optional: `--model <id>` (default: first model from `GET /v1/models`).

Outputs JSON under `benchmarks/results/` (gitignored).

## Metrics

| Metric | Source |
|--------|--------|
| total / successful / failed requests | Per-request outcomes |
| latency p50 / p95 / p99 / mean | End-to-end successful request latency (ms) |
| throughput requests/second | `successful_requests / wall_time` |
| tokens/second | Sum of `usage.completion_tokens` / wall_time (when API returns usage) |
| TTFT p50/p95/p99 | Streaming first content delta (`--ttft`) |
| generation tokens/second | Mean of `completion_tokens / (e2e − TTFT)` with `--ttft` |

Stdlib only (no pip packages).
