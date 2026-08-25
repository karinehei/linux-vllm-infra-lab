# Testing and CI

This repository separates **static checks** (safe on GitHub-hosted runners) from **GPU/integration checks** (lab host only).

## Why GPU tests are not on normal hosted CI

GitHub-hosted runners (`ubuntu-latest`) do **not** provide:

- An NVIDIA GPU or supported driver/toolkit stack
- Local access to your Rocky Linux lab inventory
- Guaranteed capacity to download multi‑GB model weights on every PR

Running vLLM inference in that environment would be **flaky, slow, expensive**, and could block unrelated infrastructure changes. Hardware-specific latency/throughput is also a poor merge gate for Ansible and shell updates.

| Suite | Where it runs | Needs GPU / vLLM |
|-------|---------------|------------------|
| Static CI | GitHub Actions on push/PR | No |
| Integration / benchmark | Linux GPU host (manual) | Yes |

## Static CI (GitHub Actions)

Workflow: [`.github/workflows/static-ci.yml`](../.github/workflows/static-ci.yml)

Runs:

1. **yamllint** — Ansible, compose, workflow YAML
2. **ansible-playbook --syntax-check** — `ansible/playbooks/ai-server.yml`
3. **ansible-lint** — playbook + roles
4. **Ruff** — Python lint for `scripts/`, `benchmarks/`, `tests/`
5. **ShellCheck** — operational Bash scripts
6. **pytest** — `tests/unit` (config validation + unit tests)

Local equivalent:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
sudo apt-get install -y shellcheck   # or brew install shellcheck

yamllint -c .yamllint.yml ansible containers .github/workflows .yamllint.yml .ansible-lint
ansible-playbook --syntax-check -i ansible/inventory/hosts.yml ansible/playbooks/ai-server.yml
ansible-lint -c .ansible-lint ansible/playbooks/ai-server.yml ansible/roles
ruff check scripts benchmarks tests
shellcheck scripts/*.sh scripts/health/*.sh tests/integration/run_on_gpu_host.sh
pytest tests/unit -v
```

## Integration tests (GPU host)

Workflow: [`.github/workflows/integration-gpu.yml`](../.github/workflows/integration-gpu.yml) — **manual** `workflow_dispatch` that documents the policy (does not claim a GPU on `ubuntu-latest`).

On the lab host with vLLM up:

```bash
export VLLM_BASE_URL=http://127.0.0.1:8000
./scripts/gpu-status.sh
./scripts/health-check.sh
./tests/integration/run_on_gpu_host.sh
```

Pytest markers:

| Marker | Meaning |
|--------|---------|
| `gpu` | Needs NVIDIA tooling / GPU |
| `integration` | Needs live OpenAI-compatible API |
| `benchmark` | Sends live load via `benchmark_vllm.py` |

Markers are defined in `pyproject.toml`. Do not run them on hosted CI.

## Test layout

```
tests/
├── unit/                 # Static CI
│   ├── test_config_validation.py
│   ├── test_benchmark_vllm.py
│   └── test_scripts_smoke.py
└── integration/          # GPU host
    ├── test_gpu_vllm.py
    └── run_on_gpu_host.sh
```
