# Assumptions

These assumptions bound the v1 lab design. Challenge or update them when hardware/network differs.

## Environment

1. **One primary GPU host** is available for demos (physical or VM with GPU passthrough).
2. The host OS can be installed as **Rocky Linux 9** (or a close RHEL 9 clone) with sudo/root access.
3. An **Ansible control node** can reach the host over **SSH** (key-based auth preferred).
4. The control node may be Linux, macOS, or WSL2; playbooks are written for POSIX Ansible.

## Hardware / GPU

5. The GPU is an **NVIDIA** device supported by the chosen driver and vLLM/CUDA stack.
6. Host has enough **system RAM and disk** for the selected model weights and KV cache (exact sizes left to `group_vars` once a model is chosen).
7. PCIe / MIG / multi-instance GPU partitioning is **not** required for v1.
8. Internet access (or a local mirror) exists on first provision to pull packages and container images. Air-gapped mode is a future hardening topic.

## Software / models

9. The served model is an **open-weight** model legally usable in the lab; licensing is the operator’s responsibility.
10. Model artifacts live on **local disk** (or a pre-mounted shared filesystem); this repo does not vendor weights.
11. Default API is **HTTP** on a private network; TLS termination is optional hardening, not assumed day-1.
12. Clients speak the **OpenAI-compatible** HTTP schema that vLLM exposes.

## Operations

13. The lab is **single-tenant** or trusted multi-user on a shared research network — not a public multi-tenant SaaS.
14. Operators can use **journalctl** and container logs for first-line debugging.
15. Time sync (chrony/NTP) is available so logs and metrics correlate.
16. SELinux is **enforcing** or at least documented; roles should prefer compatible patterns rather than disabling SELinux.

## Out of scope (assumed not required for v1)

17. Kubernetes / OpenShift or full campus HPC. **Optional laboratory Slurm** lives under `hpc/` and is not required to run the core vLLM lab.
18. Model training, fine-tuning, or experiment tracking platforms.
19. Formal HA/failover across hosts.
20. Enterprise IdP (OIDC/SAML) in front of the API — may be noted as a future control.
