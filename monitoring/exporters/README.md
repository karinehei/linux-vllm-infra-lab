# Exporters used by the lab monitoring stack

## node_exporter

- Image: `quay.io/prometheus/node-exporter` (see `compose.yml`)
- Listens on `127.0.0.1:9100` in the compose example
- Provides CPU, memory, disk, filesystem, and basic network metrics

Package alternative on Rocky Linux 9 (optional): install from EPEL/copr and run as a systemd unit instead of compose.

## NVIDIA DCGM exporter

- Image: `nvcr.io/nvidia/k8s/dcgm-exporter` (version pinned in `compose.yml`)
- Listens on `127.0.0.1:9400`
- Requires working NVIDIA drivers and GPU visibility in the container runtime
- Useful series: `DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED`, `DCGM_FI_DEV_FB_FREE`

If DCGM cannot run in your lab, a lighter fallback is `nvidia-gpu-exporter` / custom `nvidia-smi` textfile collector — keep one GPU metrics path only to avoid complexity.

## blackbox_exporter

- Probes `http://127.0.0.1:8000/health` for inference availability
- `probe_success` and `probe_duration_seconds` feed alerts and a simple latency panel

## vLLM `/metrics`

Many vLLM OpenAI server builds expose Prometheus metrics at `/metrics` (histograms for request latency). Scrape job `vllm` is best-effort; blackbox remains the availability backstop.
