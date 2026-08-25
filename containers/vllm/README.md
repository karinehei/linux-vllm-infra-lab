# vLLM container deployment

OpenAI-compatible inference via the official `vllm/vllm-openai` image (optional thin `Containerfile` wrapper adds a healthcheck).

## Files

| File | Purpose |
|------|---------|
| `Containerfile` | Wrapper image + `HEALTHCHECK` on `/health` |
| `compose.yml` | Manual Podman/Docker Compose bring-up |
| `vllm.env.example` | Env template (copy to `vllm.env`, never commit secrets) |

## Quick start (compose)

```bash
cd containers/vllm
cp vllm.env.example vllm.env
# edit VLLM_MODEL / paths; set HF token only if the model is gated
mkdir -p /var/lib/vllm/models /var/lib/vllm/cache
podman compose -f compose.yml up -d
# or: docker compose -f compose.yml up -d
```

Default publish address is **`127.0.0.1:8000`**. For a private NIC:

```bash
# in vllm.env
VLLM_HOST=10.0.0.20
```

Do not set `VLLM_HOST=0.0.0.0` unless firewall CIDRs are in place (`vllm_firewall_allow_cidrs`).

## Persistent cache

| Host path | Container | Use |
|-----------|-----------|-----|
| `/var/lib/vllm/models` | ro | Pre-placed weights |
| `/var/lib/vllm/cache` | rw | HF / transformers / vLLM download cache |

## Production-like path

Prefer Ansible + systemd (`ansible/roles/vllm`) over long-lived compose on the lab server. See [`docs/vllm.md`](../../docs/vllm.md).
