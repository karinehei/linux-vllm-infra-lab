# Lightweight lab monitoring

Minimal Prometheus-based observability for a single GPU inference host.  
**Not** a full SRE platform (no Loki/Tempo/Thanos/Alertmanager HA).

## Architecture

```text
Linux host
 ├── node_exporter          # CPU, RAM, disk, …
 ├── NVIDIA DCGM exporter   # GPU util, GPU memory, …
 └── vLLM (:8000)
        │  /metrics (when enabled) + /health
        ↓
    Prometheus
        ↓
      Grafana
```

Optional: `blackbox_exporter` probes `http://127.0.0.1:8000/health` for availability and probe latency when you want an HTTP check independent of the process scrape.

## Quick start (compose)

On the GPU host (or a small admin host that can reach exporters):

```bash
cd monitoring
# edit prometheus/prometheus.yml targets if not localhost
podman compose -f compose.yml up -d
# or: docker compose -f compose.yml up -d
```

Default UI binds (localhost only):

| Service | URL |
|---------|-----|
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 (admin / see compose env) |

SSH tunnel from your laptop if needed:

```bash
ssh -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 rocky@utility-node-01
```

## What is monitored

| Signal | Source |
|--------|--------|
| CPU | node_exporter |
| RAM | node_exporter |
| Disk | node_exporter |
| GPU utilization | DCGM exporter |
| GPU memory | DCGM exporter |
| Inference availability | Prometheus `up` on vLLM job and/or blackbox `/health` |
| Request / probe latency | vLLM histograms when `/metrics` is available; else blackbox probe duration |

## Files

| Path | Purpose |
|------|---------|
| `compose.yml` | Prometheus, Grafana, node_exporter, dcgm-exporter, blackbox |
| `prometheus/prometheus.yml` | Scrape config |
| `prometheus/alerts/lab-alerts.yml` | Alert rules + explanations in comments |
| `grafana/` | Datasource + lab overview dashboard provisioning |
| `exporters/README.md` | Exporter notes / non-compose install tips |

Full write-up: [`docs/monitoring.md`](../docs/monitoring.md).
