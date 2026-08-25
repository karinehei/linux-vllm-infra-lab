# HPC extension — laboratory Slurm

**Optional.** The core repository (Ansible → Rocky hosts → systemd vLLM) works **without** installing Slurm.

This directory is a **laboratory-scale** Slurm sketch for a university-style research computing interview: enough configuration and job examples to demonstrate scheduler concepts, node registration, GPU GRES, and job submission. It is **not** a production HPC cluster (no HA controllers, no federation, no full accounting fabric, no multi-site topology).

---

## Minimal lab architecture

```text
Slurm controller (slurmctld)
       |
       +---- compute01     # CPU partition worker
       |
       +---- gpu01         # GPU partition worker (NVIDIA + GRES)
```

| Host (example) | Role | Daemons |
|----------------|------|---------|
| `controller` | Control plane | `slurmctld` (optional: `slurmdbd` later) |
| `compute01` | CPU compute | `slurmd` |
| `gpu01` | GPU compute | `slurmd` + NVIDIA drivers |

Example names match [`slurm/slurm.conf.example`](slurm/slurm.conf.example). Replace with your lab hostnames/IPs.

How this relates to the core lab:

- **vLLM as a service** (core): long-running OpenAI-compatible API under systemd on `ai_nodes`.
- **Slurm jobs** (this extension): queued, time-bounded batch work that may use a GPU for training, batch inference, or a short-lived container — then exit and free the resource.

---

## Concepts (lab vocabulary)

### Scheduler

Slurm decides **which job runs where and when**, given resource requests (CPUs, memory, GPUs, time limits). Users submit work; they do not SSH in and monopolize a GPU indefinitely (unless policy allows interactive allocations).

### Partitions

A **partition** is a queue/policy bucket (who may submit, default time limits, which nodes belong). This lab defines:

| Partition | Nodes | Intent |
|-----------|-------|--------|
| `cpu` | `compute01` | Short CPU jobs |
| `gpu` | `gpu01` | Jobs that request a GPU via GRES |

### Nodes

A **node** is a machine registered in `slurm.conf` with counts for CPUs, memory, and features. `slurmd` on that host reports state to `slurmctld`.

### Jobs

A **job** is a unit of work submitted with `sbatch` / `salloc` / `srun`. It has an ID, state (`PENDING`, `RUNNING`, `COMPLETED`, …), and allocated resources.

### GPU resources (GRES)

**GRES** (Generic RESource) advertises accelerators. For NVIDIA:

1. `gres.conf` maps GPU devices on `gpu01`.
2. `slurm.conf` sets `GresTypes=gpu` and `Gres=gpu:1` on the node.
3. Jobs request `#SBATCH --gres=gpu:1` (or `--gpus=1` on newer Slurm).

Without GRES, the scheduler cannot fairly allocate GPUs across users.

---

## Layout

```text
hpc/
├── README.md                 # This file
├── slurm/
│   ├── README.md             # Apply configs on a lab cluster
│   ├── slurm.conf.example
│   ├── gres.conf.example
│   └── cgroup.conf.example
└── jobs/
    ├── cpu-test.sbatch
    └── gpu-test.sbatch
```

Core Ansible playbooks under `ansible/playbooks/` **do not** install Slurm. Keep HPC optional.

---

## Example operator commands

After a lab Slurm install using the example configs:

```bash
# Cluster / partition / node view
sinfo

# Jobs in the queues
squeue

# Detailed node records (CPUs, GRES, state)
scontrol show nodes

# Submit the sample GPU job
sbatch hpc/jobs/gpu-test.sbatch

# Submit a CPU-only job
sbatch hpc/jobs/cpu-test.sbatch

# Follow job output (replace JOBID)
# tail -f slurm-JOBID.out
```

Illustrative `sinfo` shape (values depend on your hosts):

```text
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
cpu*      up     1:00:00        1   idle compute01
gpu       up     2:00:00        1   idle gpu01
```

---

## Persistent vLLM service vs scheduled HPC jobs

| | **vLLM as systemd service** (core lab) | **AI work as Slurm jobs** (this extension) |
|--|----------------------------------------|--------------------------------------------|
| Lifetime | Stays up; API always (when healthy) | Starts, runs, exits; GPU freed |
| Interface | OpenAI-compatible HTTP | Batch scripts, `srun`, logs under Slurm |
| Scheduling | Manual/ops (`systemctl`) | Fair share / queue / time limits |
| Best for | Interactive demos, apps calling an API | Training, sweeps, offline batch inference |
| Contention | One long-lived consumer of the GPU | Many users take turns via GRES |

Both can coexist: e.g. systemd vLLM on one GPU host for serving, and Slurm `gpu` partition on other GPUs for batch — or use Slurm only when the API is stopped. Do not assume one GPU can run a full vLLM server and a heavy training job without explicit sharing policy (MIG, time-slicing, or separate devices).

---

## Laboratory vs production HPC

This extension **demonstrates concepts**. It does **not** provide:

- Redundant `slurmctld` / shared state HA
- Site-wide identity (LDAP/SSS), fairshare accounting, QoS at campus scale
- Parallel filesystem (Lustre/GPFS) design
- Network topology / InfiniBand tuning
- Security hardening of munge keys across a large estate

Treat `*.example` files as teaching templates. Validate on disposable VMs before any shared research network.

---

## Suggested lab bring-up (manual)

1. Provision Rocky Linux 9 hosts (Ansible `common`/`security` from the core repo is fine).
2. Install Slurm packages from your site’s preferred repo (OS, EPEL, or vendor build) — versions must match across nodes.
3. Distribute a shared **Munge** key; start `munge` everywhere.
4. Install example configs from `hpc/slurm/` (rename to remove `.example`), fix hostnames/IPs.
5. Start `slurmctld` on the controller; start `slurmd` on `compute01` and `gpu01`.
6. On `gpu01`, confirm `nvidia-smi` and that `gres.conf` device indexes match.
7. Run `sinfo`, then `sbatch hpc/jobs/cpu-test.sbatch` and `hpc/jobs/gpu-test.sbatch`.

Package names and exact unit paths vary by Slurm build; see [`slurm/README.md`](slurm/README.md).

---

## Relationship to core documentation

| Doc | Role |
|-----|------|
| [`docs/multi-node.md`](../docs/multi-node.md) | Central Ansible management of AI + utility nodes |
| [`docs/vllm.md`](../docs/vllm.md) | Persistent inference API |
| [`docs/security.md`](../docs/security.md) | Lab security review (Slurm adds its own trust boundaries) |
