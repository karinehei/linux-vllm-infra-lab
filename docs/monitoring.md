# Lightweight monitoring

Portfolio-scale observability for a single GPU inference host. Prefer a small Prometheus + Grafana stack over a multi-tenant observability platform.

## Architecture

```text
Linux host
 ├── node_exporter
 ├── NVIDIA DCGM exporter
 └── vLLM
        ↓
    Prometheus
        ↓
      Grafana
```

Blackbox exporter (optional but included) probes vLLM `/health` so availability does not depend solely on the `/metrics` scrape.

## Signals

| Need | How it is covered |
|------|-------------------|
| CPU | `node_cpu_seconds_total` via node_exporter |
| RAM | `node_memory_*` via node_exporter |
| Disk | `node_filesystem_*` via node_exporter |
| GPU utilization | `DCGM_FI_DEV_GPU_UTIL` |
| GPU memory | `DCGM_FI_DEV_FB_USED` / `DCGM_FI_DEV_FB_FREE` |
| Inference availability | `probe_success` (blackbox) and/or `up{job="vllm"}` |
| Latency | Blackbox `probe_duration_seconds`; vLLM histogram when `/metrics` exists; deeper load tests via `benchmarks/benchmark_vllm.py` |

## Bring-up

```bash
cd monitoring
export GRAFANA_ADMIN_PASSWORD='replace-me'
podman compose -f compose.yml up -d
```

UI (localhost):

- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

Configs:

- [`monitoring/prometheus/prometheus.yml`](../monitoring/prometheus/prometheus.yml)
- [`monitoring/prometheus/alerts/lab-alerts.yml`](../monitoring/prometheus/alerts/lab-alerts.yml)

## Alert rules (why they exist)

| Alert | Detects | Why it matters |
|-------|---------|----------------|
| `InferenceServiceUnavailable` | `/health` probe failing for 2m | Users/automation cannot call the API; check systemd/journal |
| `InferenceMetricsTargetDown` | `/metrics` scrape `up==0` for 5m | Metrics path broken; confirm whether API itself is down |
| `GpuMemoryNearExhaustion` | FB used/(used+free) > 90% for 5m | Precursor to CUDA OOM under load |
| `DiskSpaceLow` | Root FS < 15% free for 10m | Cache/images fill disk; pulls and logs fail |
| `HostMemoryHigh` | Host memory pressure > 90% for 5m | OOM risk for host services, not only the GPU |

Alertmanager is **not** required for the portfolio demo; inspect firing alerts in the Prometheus UI. Add Alertmanager only if you need email/Slack routing.

## Security notes

- Compose publishes Prometheus/Grafana on **127.0.0.1** only (same posture as the default vLLM bind).
- Change `GRAFANA_ADMIN_PASSWORD`; do not expose Grafana publicly without auth/TLS.
- Scraping vLLM on localhost avoids opening extra firewall ports for metrics.

## Multi-node scrape caveat

Default `vllm_host` is `127.0.0.1` (secure lab bind). Prometheus on `utility-node-01` therefore **cannot** scrape vLLM on `ai-node-01` until you either:

1. Bind vLLM to a private NIC and allow the utility CIDR (`vllm_host` + `vllm_firewall_allow_cidrs`), or  
2. Run the single-host compose stack on the AI node for local scrapes.

Node exporter scrapes work when `node_exporter_firewall_allow_cidrs` includes the utility host (see `group_vars/ai_nodes.yml`). Fleet scrape config is rendered by Ansible `roles/monitoring` from inventory.

## Limitations

- Laboratory scale (not campus-wide observability).
- DCGM scrape is optional (`monitoring_scrape_dcgm`); enable only when a DCGM exporter is actually running on GPU nodes.
- vLLM histogram metric names can differ by version — use blackbox latency + `benchmarks/benchmark_vllm.py` when empty.
- Compose on a single host (`monitoring/compose.yml`) and Ansible utility-node deploy are two supported paths; pick one per lab.
