# Prerequisites

## Target host

- Rocky Linux 9 (x86_64) preferred
- NVIDIA GPU with sufficient VRAM for the chosen model (see [`vllm.md`](vllm.md))
- Disk space for OS + container images + model weights / HF cache
- Network: SSH from Ansible control node; API defaults to localhost (SSH tunnel for clients)

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
