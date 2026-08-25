# vLLM OpenAI-compatible inference

This lab runs **vLLM** in a container and exposes the standard OpenAI-compatible HTTP API (`/v1/models`, `/v1/chat/completions`, `/v1/completions`, `/health`).

## Network exposure (default: not public)

| Setting | Default | Meaning |
|---------|---------|---------|
| `vllm_host` | `127.0.0.1` | Host publish address for the API port |
| `vllm_port` | `8000` | Only port published for inference |
| `vllm_firewall_allow_cidrs` | `[]` | Firewall stays closed for vLLM |

Use SSH tunneling for remote clients:

```bash
ssh -L 8000:127.0.0.1:8000 rocky@ai-node-01
python3 scripts/test-inference.py --base-url http://127.0.0.1:8000
```

To serve on a **private** NIC only:

```yaml
vllm_host: "10.0.0.20"
vllm_firewall_allow_cidrs: ["10.0.0.0/8"]
```

Avoid `vllm_host: "0.0.0.0"` unless you accept LAN-wide exposure and have CIDR controls.

## Ansible variables

| Variable | Role |
|----------|------|
| `vllm_model` | HF id or local path under `vllm_model_path` |
| `vllm_port` / `vllm_host` | Host bind |
| `vllm_gpu_memory_utilization` | Engine GPU memory fraction |
| `vllm_max_model_len` | Context length (VRAM sensitive) |
| `vllm_tensor_parallel_size` | Keep `1` for single GPU |
| `vllm_cache_path` | Persistent HF/vLLM download cache |
| `vllm_hf_token` | Optional; from Ansible Vault only |
| `vllm_service_started` | Set `true` when ready to run |

Provision:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/ai-server.yml --tags vllm
```

## Persistent paths

| Path | Purpose |
|------|---------|
| `/var/lib/vllm/models` | Optional pre-placed weights (ro in container) |
| `/var/lib/vllm/cache` | Persistent HF / transformers / vLLM cache (rw) |
| `/etc/vllm/vllm.env` | Runtime environment (mode `0640`) |
| `/etc/vllm/vllm.json` | Documented config snapshot |

## Health checks and restart

- Host preflight: `/usr/local/sbin/vllm-preflight` (GPU/runtime; fails the unit before start)
- Host health script: `/usr/local/sbin/check-vllm-health`
- systemd timer: `vllm-health.timer`
- Unit policy: `Restart=on-failure`, `RestartSec=15`, burst **3 / 300s**, then stay `failed`

See [`systemd-lifecycle.md`](systemd-lifecycle.md) for crash / GPU / model-load behavior.

```bash
systemctl status vllm
systemctl start vllm
systemctl stop vllm
systemctl restart vllm
journalctl -u vllm
journalctl -u vllm -f
```

## Selecting a model by VRAM (single GPU)

Weights are only part of the footprint. **KV cache** grows with `vllm_max_model_len` and concurrency. Rule of thumb for **fp16/bf16, batch≈1**:

| GPU VRAM | Reasonable starting models | Suggested `vllm_max_model_len` |
|----------|----------------------------|--------------------------------|
| 8 GB | 1–3B instruct (e.g. TinyLlama, Phi-3-mini) | 2k–4k |
| 12 GB | ~3–7B with care; prefer 4-bit/AWQ if needed | 2k–4k |
| 16 GB | ~7B instruct (e.g. Qwen2.5-7B) | 4k |
| 24 GB | 7–13B comfortably; some 14B | 4k–8k |
| 40–48 GB | 30–34B class or longer context on 7–13B | 8k+ |
| 80 GB | 70B class (still tune len/util) | per workload |

Also:

1. Check `nvidia-smi` free memory after driver load.
2. Lower `vllm_gpu_memory_utilization` (e.g. `0.80`) if you OOM at startup.
3. Lower `vllm_max_model_len` before switching to a smaller model.
4. Prefer **non-gated** models for demos unless Vault provides an HF token.
5. Keep `vllm_tensor_parallel_size: 1` on a single GPU.

Default in this repo: **`Qwen/Qwen2.5-7B-Instruct`** (public, ~16 GB+ class card at 4k context).

Example overrides in `group_vars`:

```yaml
# 8–12 GB card
vllm_model: "microsoft/Phi-3-mini-4k-instruct"
vllm_max_model_len: 2048
vllm_gpu_memory_utilization: 0.85
```

## Smoke test

```bash
python3 scripts/test-inference.py --base-url http://127.0.0.1:8000
```

Stdlib only (no `pip install`).

## Compose alternative

See [`containers/vllm/`](../containers/vllm/) for `Containerfile`, `compose.yml`, and `vllm.env.example`. Prefer Ansible+systemd on the managed lab host.
