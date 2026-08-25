# Container assets

| Path | Purpose |
|------|---------|
| `vllm/` | vLLM OpenAI-compatible server (Containerfile, compose, env example) |

Managed hosts should use Ansible (`roles/vllm` → systemd). Compose is for manual experiments on a GPU box.
