# Runbook: CUDA OOM / KV-cache pressure

```bash
journalctl -u vllm -b --no-pager | grep -iE 'out of memory|CUDA|OOM'
nvidia-smi
```

Mitigations (then `systemctl restart vllm`):

- Lower `vllm_max_model_len`
- Lower `vllm_gpu_memory_utilization` (e.g. `0.80`)
- Choose a smaller model (`docs/vllm.md`)

Avoid raising restart burst limits to paper over OOM loops.
