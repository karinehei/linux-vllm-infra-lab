# Deployment validation

Use this procedure on a **real** Rocky Linux 9 lab after Ansible converge. It
separates **static checks** (this repository) from **host evidence** (SSH, GPU,
vLLM, Prometheus).

Do **not** copy placeholder text from the results template into a report as if
it were measured. Leave Actual blank until you run the command on a host.

Related: [`testing.md`](testing.md) (CI policy), [`setup.md`](setup.md) (first
converge), [`monitoring.md`](monitoring.md), [`vllm.md`](vllm.md).

## What this repository can validate without a lab host

From a control node (Linux/WSL recommended) with `requirements-dev.txt`
installed:

```bash
make check
```

| Check | Expected | Requires lab host? |
|-------|----------|--------------------|
| yamllint | Exit 0 | No |
| ansible-playbook --syntax-check | Exit 0 for `site.yml`, `ai-server.yml`, `monitoring.yml` | No |
| ansible-lint | Exit 0 | No |
| ruff | Exit 0 | No |
| shellcheck | Exit 0 | No |
| pytest `tests/unit` | All unit tests pass | No |

GitHub Actions **Static CI** runs the same class of checks. It does **not**
prove that vLLM started, that a GPU is visible, or that Prometheus scraped a
target.

## What requires a Linux / GPU host

Record Actual only after running the command. If you did not run it, set Result
to `not_run`.

### A. Control node and inventory

| ID | Check | Command / action | Expected |
|----|-------|------------------|----------|
| A1 | SSH to AI node | `ssh rocky@<ai-node>` | Login with key, no password prompt |
| A2 | SSH to utility node | `ssh rocky@<utility-node>` | Same |
| A3 | Inventory addresses | Review `ansible/inventory/hosts.yml` | Not documentation-only `192.0.2.0/24` if you intend to converge |

### B. Ansible converge (does not start vLLM by default)

`vllm_service_started` defaults to `false`. A successful playbook run installs
units and configs; it is **not** evidence that inference is serving.

| ID | Check | Command / action | Expected |
|----|-------|------------------|----------|
| B1 | Syntax on control node | `make ansible-syntax` | Exit 0 |
| B2 | Converge AI nodes | `ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --limit ai_nodes` | Play recap `failed=0` |
| B3 | Converge monitoring | Same playbook `--limit monitoring_nodes` with Vault password set | Play recap `failed=0`; Grafana password assert passes |
| B4 | Compose provider | On utility node: `podman compose version` (or `docker compose version`) | Non-zero version string; `lab-monitoring.service` start-pre succeeds |

### C. GPU and container runtime (AI node)

| ID | Check | Command / action | Expected |
|----|-------|------------------|----------|
| C1 | GPU PCI | `lspci \| grep -i nvidia` | NVIDIA device listed |
| C2 | Driver | `nvidia-smi` | Driver/CUDA user-space reported; at least one GPU |
| C3 | Toolkit / CDI | `test -s /etc/cdi/nvidia.yaml` (Podman) | CDI spec present after nvidia role |
| C4 | Preflight | `sudo /usr/local/sbin/vllm-preflight` | Exit 0 when GPU+runtime are healthy |

### D. Inference API (AI node)

Start only when weights/cache/GPU are ready: `sudo systemctl start vllm`.

| ID | Check | Command / action | Expected |
|----|-------|------------------|----------|
| D1 | Unit | `systemctl status vllm` | `active (running)` after model load, or `failed` with a journal reason |
| D2 | Health | `curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health` | `200` |
| D3 | Models | `curl -sS http://127.0.0.1:8000/v1/models` | JSON listing the configured model |
| D4 | Smoke | `python3 scripts/test-inference.py --base-url http://127.0.0.1:8000` | Exit 0; a completion is printed |
| D5 | Bind | `ss -lntp \| grep 8000` (or `lsof -iTCP:8000`) | Listen address is `127.0.0.1` unless you set a private NIC |
| D6 | Firewall | `sudo firewall-cmd --list-rich-rules` | No public vLLM accept unless `vllm_firewall_allow_cidrs` was set |

### E. Monitoring (utility node)

Prometheus scrapes Blackbox at Compose DNS `blackbox-exporter:9115`, not at
`127.0.0.1:9115` inside the Prometheus container.

vLLM `/metrics` and `/health` appear as scrape targets **only** when
`vllm_host` is a reachable private NIC (or `monitoring_vllm_scrape_target` is
set). Localhost-only API remains private.

| ID | Check | Command / action | Expected |
|----|-------|------------------|----------|
| E1 | Stack | `systemctl status lab-monitoring` | `active` (oneshot remain-after-exit) |
| E2 | Prometheus UI | SSH tunnel `9090` then open `/targets` | `prometheus` job up; `node` jobs up if node_exporter firewall CIDRs match |
| E3 | Blackbox | Prometheus target `blackbox-exporter:9115` used by job `vllm_health` | Exporter reachable on the container network |
| E4 | vLLM scrape | `/targets` job `vllm` / `vllm_health` | Present only if the API bind is reachable; otherwise absent by design |
| E5 | Grafana | Tunnel `3000`; log in with the Vault password | Datasource Prometheus; no published default password |

### F. Optional GPU integration tests

| ID | Check | Command / action | Expected |
|----|-------|------------------|----------|
| F1 | Host script | `./tests/integration/run_on_gpu_host.sh` | Exit 0 against a live API |
| F2 | Benchmark | `python3 benchmarks/benchmark_vllm.py --url http://127.0.0.1:8000 ...` | JSON under `benchmarks/results/` with `result_type: collected_measurement` |

Do not invent latency or token/s numbers. If F2 was not run, leave metrics blank.

---

## Results template

Copy this table into an operator log. Fill **Actual** and **Result** only from
commands you ran. Valid Result values: `pass`, `fail`, `not_run`.

**Environment (fill in)**

| Field | Value |
|-------|-------|
| Date | |
| Operator | |
| Ansible control node OS | |
| AI node hostname / OS | |
| Utility node hostname / OS | |
| GPU model / driver (from `nvidia-smi`) | |
| `vllm_container_image` | |
| `vllm_model` | |
| `container_runtime` | |
| Vault used for Grafana password | yes / no |

**Static checks (control node)**

| Check | Expected | Actual | Result | Notes |
|-------|----------|--------|--------|-------|
| `make check` / Static CI | All linters and unit tests pass | | | |
| ansible-playbook syntax | Exit 0 | | | |

**Host checks**

| ID | Expected | Actual | Result | Notes |
|----|----------|--------|--------|-------|
| A1 SSH AI node | Key login works | | | |
| A2 SSH utility node | Key login works | | | |
| B2 Converge ai_nodes | failed=0 | | | |
| B3 Converge monitoring_nodes | failed=0 | | | |
| B4 `podman compose version` | Provider present | | | |
| C1 NVIDIA PCI | Device listed | | | |
| C2 `nvidia-smi` | GPU visible | | | |
| D1 `systemctl status vllm` | active or explained failed | | | |
| D2 `/health` | HTTP 200 | | | |
| D4 `test-inference.py` | Exit 0 | | | |
| D5 Listen address | 127.0.0.1 or documented private NIC | | | |
| E2 Prometheus targets | Jobs match bind/firewall design | | | |
| E3 Blackbox via Compose DNS | `blackbox-exporter:9115` | | | |
| E4 vLLM scrape from utility | Present only if private NIC bind | | | |
| F1 GPU integration tests | Exit 0 | | | |
| F2 Benchmark JSON | Measured, not example schema | | | |

**Explicitly not claimed**

- Any latency, throughput, or GPU utilization figure that was not written by
  `benchmark_vllm.py` or a Prometheus query you captured
- Successful deployment on hardware that was not reached in this log
