# Architecture overview

## Purpose

Provision a single-node (extendable to small multi-node) **research AI inference lab** on Rocky Linux 9 that:

1. Installs and configures NVIDIA GPU software stack
2. Runs a container runtime suitable for GPU workloads
3. Serves an open-source LLM with **vLLM** over an **OpenAI-compatible HTTP API**
4. Manages the service with **systemd**
5. Exposes operational primitives: health checks, logs, basic metrics, tests, and benchmarks

This is an **infrastructure engineering** artifact, not an application product.

## Logical components

| Component | Responsibility |
|-----------|----------------|
| Control node | Runs Ansible; holds inventory, secrets handling policy, and playbooks |
| GPU inference host | Rocky Linux 9; NVIDIA drivers/toolkit; container runtime; vLLM |
| vLLM service | Containerized inference; OpenAI-compatible `/v1` endpoints |
| systemd | Starts/stops/restarts vLLM; restart policies; dependency ordering |
| Health scripts | Liveness/readiness against API and GPU visibility |
| Monitoring | Node/GPU exporters → Prometheus → Grafana (lab-scale; see `monitoring/`) |
| Tests / benchmarks | Smoke + integration checks; latency/throughput helpers |

## Runtime data flow

```
Client (curl / SDK / pytest)
    │  HTTPS or HTTP (lab-only) / SSH tunnel
    ▼
Host firewall (nftables/firewalld) ── allow API port from trusted CIDR
    ▼
systemd unit ──► Podman/Docker ──► vLLM container
                      │
                      ├── NVIDIA Container Toolkit (GPU device passthrough)
                      ├── Model weights volume (local disk or NFS mount)
                      └── Logs → journald / container logs → optional shipper
```

## Host layers (bottom → top)

1. **OS:** Rocky Linux 9, minimal install + required packages  
2. **GPU stack:** NVIDIA driver, CUDA userspace as required by container toolkit  
3. **Runtime:** Podman (preferred) or Docker Engine + NVIDIA Container Toolkit  
4. **Workload:** vLLM image + model cache  
5. **Control plane (local):** systemd unit + Ansible-managed config  
6. **Observability:** health scripts, exporters, optional Prometheus/Grafana  

## Network model (lab default)

- Inference API bound to lab/private interface or localhost + SSH tunnel
- No public internet exposure in the default design
- SSH for administration; Ansible over SSH
- Optional reverse proxy / TLS termination documented as a hardening step, not required for day-1 lab

## Scaling posture

| Mode | Support in this project |
|------|-------------------------|
| Single GPU host | Supported (`ai_nodes` with one host) |
| Multi-GPU on one host | Supported via vLLM tensor parallelism knobs (group_vars) |
| Small multi-host fleet | Supported: `ai_nodes` + `monitoring_nodes` via `site.yml` |
| Large HPC / Kubernetes | Out of core scope; optional lab Slurm under [`hpc/`](../hpc/README.md) |

## Non-goals

- Chat UI / web frontend
- Multi-tenant SaaS auth product
- Full Kubernetes / OpenShift platform (may be noted as a future evolution)
- Training / fine-tuning pipelines (inference-focused)
