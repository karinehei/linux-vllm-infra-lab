# Runbook: vLLM will not start or stay running

## Symptoms

- `systemctl status vllm` shows `failed`, `activating (auto-restart)`, or `start-limit-hit`
- API clients cannot connect to `http://127.0.0.1:8000`
- Health script exits non-zero

## Immediate commands

```bash
systemctl status vllm
systemctl stop vllm
journalctl -u vllm
journalctl -u vllm -f
```

While following logs in another session:

```bash
systemctl start vllm
systemctl restart vllm
```

## Decision tree

1. **Preflight failed** (`vllm-preflight: ERROR`)  
   - Fix GPU/drivers or container runtime; re-run `/usr/local/sbin/vllm-preflight`.

2. **Container starts then exits during model load**  
   - Read journal for OOM, HF auth, or path errors; adjust `vllm_model` / VRAM settings / Vault token.

3. **`start-limit-hit`**  
   - Do not keep restarting blindly. Fix cause, then:

   ```bash
   systemctl reset-failed vllm
   systemctl start vllm
   ```

4. **Unit active but API down**  
   - Wait for model load (can take minutes), then `check-vllm-health --wait 300`.

Full narrative: [`../systemd-lifecycle.md`](../systemd-lifecycle.md).
