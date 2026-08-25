# Runbook: inference API down

```bash
systemctl status vllm
journalctl -u vllm -b --no-pager
/usr/local/sbin/check-vllm-health
curl -sS -m 5 http://127.0.0.1:8000/v1/models || true
```

If the unit is failed, follow [`vllm-startup.md`](vllm-startup.md). If the unit is active but slow to answer, wait for model load, then re-check health.
