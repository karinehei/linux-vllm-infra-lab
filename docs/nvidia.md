# NVIDIA GPU preparation for this lab

## Design stance

Ansible **detects** GPU/driver state and can install the **NVIDIA Container Toolkit**.
**Driver installation is opt-in** (`nvidia_install_drivers: false` by default).

Blind DKMS/driver installs on remote physical hosts are a common cause of:

- boot to black screen / broken display manager
- kernel/module mismatch after updates
- loss of remote SSH if networking depends on the broken boot

## Prerequisites (manual checklist)

1. Rocky Linux 9 (or RHEL 9-compatible) with secure boot policy understood (MOK if needed).
2. NVIDIA GPU visible in hardware (`lspci | grep -i nvidia`).
3. Out-of-band/console access before changing drivers on physical boxes.
4. Matching kernel headers/`kernel-devel` if building modules.
5. After drivers: `nvidia-smi` works on the **host**.
6. Then install/configure the container toolkit (Ansible default path).

## Recommended lab flow

```text
1. Install OS
2. Install NVIDIA drivers using your site standard (or enable nvidia_install_drivers once)
3. Reboot
4. Confirm nvidia-smi
5. ansible-playbook ...  # toolkit + vLLM config
6. Set vllm_service_started: true when weights/GPU are ready
```

## Ansible variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `nvidia_install_drivers` | `false` | Install driver RPMs via Ansible |
| `nvidia_cuda_repo_enabled` | `false` | Add NVIDIA CUDA network repo |
| `nvidia_install_container_toolkit` | `true` | Install toolkit + CDI/runtime hooks |
| `nvidia_require_gpu` | `false` | Fail play if no NVIDIA PCI device |

## Container runtimes

- **Podman:** `nvidia-ctk cdi generate` → `--device nvidia.com/gpu=all`
- **Docker:** `nvidia-ctk runtime configure --runtime=docker` → `--gpus all`
