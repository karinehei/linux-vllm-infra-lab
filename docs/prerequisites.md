# Prerequisites

## Target host

- Rocky Linux 9 (x86_64) preferred
- NVIDIA GPU with sufficient VRAM for the chosen model
- Disk space for OS + container images + model weights
- Network: SSH from Ansible control node; optional client access to API port

## Control node

- Ansible 2.14+ (or distribution package equivalent)
- SSH client and Python 3
- Access to this repository

## Operator skills assumed

- Comfortable with `systemctl`, `journalctl`, firewalld/nftables basics
- Able to install Rocky Linux and enable a network interface
- Familiar with container concepts (images, volumes, ports)

Exact GPU/driver matrix will be pinned when the first implementation pass lands.
