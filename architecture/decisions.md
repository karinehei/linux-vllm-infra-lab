# Design decisions

Record of important choices for this portfolio lab. Prefer reversible defaults and interview-defendable trade-offs.

## 1. Rocky Linux 9 as the OS baseline

**Decision:** Target Rocky Linux 9 (RHEL-compatible).

**Rationale:**
- Common in enterprise and research HPC/AI environments
- Predictable package and SELinux behavior vs. rolling distros
- Skills transfer directly to RHEL / AlmaLinux

**Alternatives considered:** Ubuntu LTS (strong NVIDIA/docs ecosystem), bare RHEL (subscription). Rocky chosen for free RHEL-compat storytelling without Ubuntu-default bias.

## 2. Ansible as the provisioner

**Decision:** Idempotent Ansible roles; no Terraform for v1.

**Rationale:**
- Fits configuration of an existing physical/VM GPU host
- Demonstrates Linux admin + automation in one toolchain
- Inventory + `group_vars` make multi-host extension natural

**Alternatives:** cloud-init alone (less reusable), Puppet/Chef (heavier), Terraform+cloud GPU (different story). Terraform may be added later for cloud GPU VMs.

## 3. Podman preferred, Docker supported

**Decision:** Prefer **Podman** + systemd integration; keep Docker as a documented alternative.

**Rationale:**
- Daemonless / rootless-friendly posture aligns with modern RHEL guidance
- Quadlet/systemd patterns map cleanly to `systemd/` in this repo
- Many labs still use Docker; abstraction in the `container_runtime` role keeps both paths

## 4. Containers for vLLM, not bare-metal Python env as primary

**Decision:** Run vLLM in a container with GPU passthrough.

**Rationale:**
- Isolates CUDA/Python dependency hell from the host OS
- Reproducible image tags for demos and rollbacks
- Matches how many research platforms ship inference

**Trade-off:** Slightly more moving parts (toolkit, CDI/devices) than a conda env; acceptable for infra portfolio depth.

## 5. systemd for service lifecycle

**Decision:** Manage the containerized vLLM process via systemd units (or Podman Quadlet generated units).

**Rationale:**
- Native Linux ops model (enable, restart, journalctl)
- Boot-time start and restart-on-failure without custom supervisors
- Familiar interview narrative for “how do you run this in production on a box?”

## 6. OpenAI-compatible API only — no frontend

**Decision:** Expose vLLM’s OpenAI-compatible HTTP API; clients are curl, SDKs, tests, and benchmarks.

**Rationale:**
- Keeps the project squarely in platform/infra territory
- Avoids conflating UI work with systems engineering
- Matches how research groups integrate models into existing tools

## 7. Inventory groups for a small fleet

**Decision:** Manage hosts in `ai_nodes` and `monitoring_nodes` from one control node (`site.yml`).

**Rationale:** Demonstrates centralized Linux administration with group- and host-specific variables, without requiring Kubernetes.

**Alternatives considered:** Single undifferentiated inventory (weaker portfolio signal); full HPC/Slurm as the only path (kept optional under `hpc/`).

## 8. Observability: minimal but real

**Decision:** Health scripts + journald, plus a lightweight Prometheus/Grafana stack under `monitoring/` (compose and optional Ansible `monitoring` role on utility nodes).

**Rationale:** Demonstrates ops maturity without building a full observability platform.

## 9. Secrets stay out of git

**Decision:** Inventory examples and group_vars use placeholders; API tokens and Grafana passwords reference Ansible Vault variables (see `docs/security/secrets.md`).

**Rationale:** Portfolio repos must not ship credentials or licensed weights.
