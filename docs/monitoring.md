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
cp .env.example .env
# set GRAFANA_ADMIN_PASSWORD in .env — compose will not start Grafana without it
podman compose -f compose.yml up -d
```

UI (localhost):

- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

Configs:

- [`monitoring/prometheus/prometheus.yml`](../monitoring/prometheus/prometheus.yml)
- [`monitoring/prometheus/alerts/lab-alerts.yml`](../monitoring/prometheus/alerts/lab-alerts.yml)

Standalone compose requires a Compose provider (`podman compose version`) and
`GRAFANA_ADMIN_PASSWORD` in `monitoring/.env` (copy from `.env.example`). There
is no published default Grafana password.

Prometheus reaches Blackbox on the **container network** at
`blackbox-exporter:9115`. Using `127.0.0.1:9115` as the Blackbox scrape address
from inside the Prometheus container targets Prometheus itself and fails.

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
- Set `GRAFANA_ADMIN_PASSWORD` (Vault on managed hosts, `.env` for standalone compose). Do not expose Grafana publicly without auth/TLS.
- Scraping vLLM on localhost avoids opening extra firewall ports for metrics.

## Multi-node scrape (supported path)

Default `vllm_host` is `127.0.0.1` (secure lab bind). Prometheus on
`utility-node-01` therefore **does not** include vLLM `/metrics` or blackbox
`/health` targets for that host until the API is reachable on the lab network.

**Supported connection (does not publish on all interfaces):**

1. Bind vLLM to the AI node's **private NIC** only (the `ansible_host` / `monitoring_scrape_ip`, not `0.0.0.0`).
2. Allow only the utility host in `vllm_firewall_allow_cidrs`.
3. Re-converge `ai_nodes` then `monitoring_nodes` so Prometheus regenerates scrape config.

```yaml
# ansible/inventory/host_vars/ai-node-01.yml (example documentation IPs)
vllm_host: "192.0.2.10"
vllm_firewall_allow_cidrs:
  - 192.0.2.20/32
```

Alternatives that keep the API off the LAN:

- SSH tunnel from the utility host to `127.0.0.1:8000` on the AI node (not automated here).
- Run the single-host compose stack **on the AI node** for local Prometheus (Blackbox still via Compose DNS).

Node exporter scrapes work when `node_exporter_firewall_allow_cidrs` includes the utility host (see `group_vars/ai_nodes.yml`). Fleet scrape config is rendered by Ansible `roles/monitoring` from inventory.

## Limitations

- Laboratory scale (not campus-wide observability).
- DCGM scrape is optional (`monitoring_scrape_dcgm`); enable only when a DCGM exporter is actually running on GPU nodes.
- vLLM histogram metric names can differ by version — use blackbox latency + `benchmarks/benchmark_vllm.py` when empty.
- Compose on a single host (`monitoring/compose.yml`) and Ansible utility-node deploy are two supported paths; pick one per lab.
