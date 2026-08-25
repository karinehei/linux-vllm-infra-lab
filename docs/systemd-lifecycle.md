# systemd lifecycle for vLLM

The inference API is managed as a native systemd service named **`vllm`**. Ansible renders `/etc/systemd/system/vllm.service` from `ansible/roles/vllm/templates/vllm.service.j2`.

With `vllm_service_enabled: true`, the unit is **enabled** and starts after boot once dependencies are satisfied (`WantedBy=multi-user.target`).

## Day-2 commands

```bash
systemctl status vllm
systemctl start vllm
systemctl stop vllm
systemctl restart vllm
journalctl -u vllm
journalctl -u vllm -f
```

Useful extras:

```bash
systemctl is-enabled vllm
systemctl is-active vllm
systemctl reset-failed vllm    # after start-limit is hit
/usr/local/sbin/vllm-preflight
/usr/local/sbin/check-vllm-health --wait 300
```

## What the unit does

| Concern | Behavior |
|---------|----------|
| Boot start | `enabled` + `WantedBy=multi-user.target` |
| Dependencies | `network-online.target`; Docker when used; soft `After=`/`Wants=` on `nvidia-persistenced` |
| Preflight | `/usr/local/sbin/vllm-preflight` must succeed (runtime + optional `nvidia-smi`) |
| Unexpected exit | `Restart=on-failure` after `RestartSec=15` |
| Restart limit | 3 attempts / 300s, then **stay failed** (`StartLimitAction=none`) |
| Logs | `StandardOutput=`/`StandardError=journal`, `SyslogIdentifier=vllm` |
| Privileges | No `--privileged`; host unit uses `PrivateTmp`, `ProtectHome`, and related hardening; GPU via NVIDIA toolkit/CDI |

Automatic recovery is **intentionally limited**. Permanent misconfiguration (bad model, missing GPU, auth failure) should end in `failed`, not an infinite restart loop.

## Failure scenarios

### If vLLM crashes (process/container exits)

1. systemd sees a non-zero / unexpected exit.
2. It waits `RestartSec` (default 15s) and starts the unit again.
3. After `StartLimitBurst` failures inside `StartLimitIntervalSec`, restarts **stop**.
4. `systemctl status vllm` shows `failed` / `start-limit-hit`.
5. Logs remain in the journal — inspect with `journalctl -u vllm -b`.

Clear the limit only after fixing the cause:

```bash
systemctl reset-failed vllm
systemctl start vllm
```

### If the GPU is unavailable

- **Preflight** runs `nvidia-smi` when `vllm_require_gpu_preflight: true`.
- If the driver is missing or the GPU is offline, ExecStartPre fails → unit never starts the container → status is `failed` with a clear preflight message in the journal.
- If the GPU disappears **after** start, the container typically exits (CUDA error) → same restart/limit path as a crash.
- Soft ordering on `nvidia-persistenced` improves boot races but does not hide a dead GPU.

### If the model cannot load

Examples: wrong `vllm_model`, gated model without token, insufficient VRAM, corrupt cache.

1. Container starts, vLLM logs the load error to stdout/stderr → journal.
2. Process exits non-zero.
3. Limited `on-failure` retries run (useful for transient HF/network blips).
4. Unit settles in `failed` so the error stays visible.
5. Fix model/VRAM/token/cache, then `reset-failed` + `start` (or `restart`).

Do **not** switch to `Restart=always` to “keep trying” — that hides the outage from operators.

## Troubleshooting startup

1. **Status first**

   ```bash
   systemctl status vllm -l --no-pager
   ```

   Note `Active:`, `Main PID`, and the last log lines systemd embeds.

2. **Full journal for this boot**

   ```bash
   journalctl -u vllm -b --no-pager
   ```

3. **Run preflight manually**

   ```bash
   sudo /usr/local/sbin/vllm-preflight
   nvidia-smi
   ```

4. **Container runtime**

   ```bash
   podman ps -a | grep vllm || docker ps -a | grep vllm
   podman logs vllm 2>/dev/null || docker logs vllm 2>/dev/null
   ```

5. **Config snapshot**

   ```bash
   cat /etc/vllm/vllm.json
   # tokens live in /etc/vllm/vllm.env (mode 0640) — do not paste secrets into tickets
   ```

6. **Common fixes**

   | Symptom in journal | Likely fix |
   |--------------------|------------|
   | `nvidia-smi failed` | Drivers / reboot / passthrough — see `docs/nvidia.md` |
   | CUDA OOM / memory | Smaller model, lower `vllm_max_model_len` / utilization — see `docs/vllm.md` |
   | 401 / gated repo | Vault HF token — see `docs/security/secrets.md` |
   | `start-limit-hit` | Fix root cause, then `systemctl reset-failed vllm` |
   | Port bind error | Something else on `vllm_port`, or wrong `vllm_host` |

7. **Smoke test once active**

   ```bash
   /usr/local/sbin/check-vllm-health --wait 300
   python3 scripts/test-inference.py --base-url http://127.0.0.1:8000
   ```

## Related

- Runbook: [`runbooks/vllm-startup.md`](runbooks/vllm-startup.md)
- Unit source: `ansible/roles/vllm/templates/vllm.service.j2`
- Reference copy: [`../systemd/vllm.service`](../systemd/vllm.service)
