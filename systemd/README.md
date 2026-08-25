# systemd units (vLLM)

| File | Purpose |
|------|---------|
| `vllm.service` | Reference unit showing boot enablement, restart limits, journal logging |
| Ansible template | `ansible/roles/vllm/templates/vllm.service.j2` → `/etc/systemd/system/vllm.service` |
| Health timer | `vllm-health.timer` / `vllm-health.service` (periodic `/health` probe) |

## Operator commands

```bash
systemctl status vllm
systemctl start vllm
systemctl stop vllm
systemctl restart vllm
journalctl -u vllm
journalctl -u vllm -f
```

Lifecycle behavior and failure modes: [`docs/systemd-lifecycle.md`](../docs/systemd-lifecycle.md).
