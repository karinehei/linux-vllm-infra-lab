# Runbook: GPU not visible

```bash
nvidia-smi
/usr/local/sbin/vllm-preflight
journalctl -u vllm -b --no-pager | tail -n 100
```

If `nvidia-smi` fails on the host, fix drivers before restarting vLLM (`docs/nvidia.md`). If the host is fine but the container lacks a GPU, re-check NVIDIA Container Toolkit / CDI and re-run the `nvidia` Ansible role.
