# Runbooks

| Runbook | Trigger |
|---------|---------|
| [`vllm-startup.md`](vllm-startup.md) | Unit failed / start-limit / will not become healthy |
| [`api-down.md`](api-down.md) | Health check fails / clients cannot reach `/v1` |
| [`gpu-not-visible.md`](gpu-not-visible.md) | `nvidia-smi` fails inside or outside container |
| [`oom-or-kv-cache.md`](oom-or-kv-cache.md) | CUDA OOM / degraded throughput |

Lifecycle reference: [`../systemd-lifecycle.md`](../systemd-lifecycle.md).
