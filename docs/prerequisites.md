# Prerequisites

## Target host

- Rocky Linux 9 (x86_64) preferred
- NVIDIA GPU with sufficient VRAM for the chosen model (see [`vllm.md`](vllm.md))
- Disk space for OS + container images + model weights / HF cache
- Network: SSH from Ansible control node; API defaults to localhost (SSH tunnel for clients)

## Container Compose provider (Podman)

Rocky/RHEL 9 AppStream provides **Podman** but not always a working
`podman compose` implementation. The monitoring stack
(`lab-monitoring.service`, `monitoring/compose.yml`) requires a Compose
provider:

```bash
podman compose version
# or, if you selected Docker:
docker compose version
```

The `container_runtime` role installs `podman-compose` (retrying via EPEL when
needed) and **fails** if `podman compose` is still missing. Docker CE installs
`docker-compose-plugin` and verifies `docker compose version`.

## Control node

- Linux or WSL with Python 3.12+ recommended
- Ansible 2.14+ (install via project `requirements-dev.txt` venv, or `ansible-core` package)
- SSH client; key-based access to managed hosts
- Access to this repository

**Setup steps (venv location, inventory, Vault, first converge):** [`setup.md`](setup.md).

## Operator skills assumed

- Comfortable with `systemctl`, `journalctl`, firewalld/nftables basics
- Able to install Rocky Linux and enable a network interface
- Familiar with container concepts (images, volumes, ports)
