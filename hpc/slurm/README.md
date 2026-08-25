# Slurm configuration examples (laboratory)

Copy to the appropriate paths on each node (often `/etc/slurm/` or `/etc/slurm/slurm.conf` depending on the package), **remove the `.example` suffix**, and edit hostnames/IPs.

These files are aligned with each other for a three-host lab:

| Name in config | Suggested role |
|----------------|----------------|
| `controller` | `slurmctld` |
| `compute01` | CPU `slurmd` |
| `gpu01` | GPU `slurmd` |

## Files

| File | Purpose |
|------|---------|
| `slurm.conf.example` | Cluster name, partitions, node definitions, GRES type |
| `gres.conf.example` | GPU device mapping on `gpu01` |
| `cgroup.conf.example` | Optional containment (enable only if cgroup plugin is used) |

## Shared requirements

1. **Same Slurm major version** on controller and compute nodes.
2. **Munge** shared key and running `munge` service on every Slurm host.
3. Hostname resolution (`/etc/hosts` or DNS) for `controller`, `compute01`, `gpu01`.
4. On `gpu01`: working NVIDIA driver (`nvidia-smi`) before expecting GRES to go `idle`.

## Minimal service order

```bash
# all Slurm hosts
systemctl enable --now munge

# controller
systemctl enable --now slurmctld

# compute01 and gpu01
systemctl enable --now slurmd
```

## Verify

```bash
sinfo
scontrol show nodes
scontrol show partition
```

If `gpu01` shows `*drain*` or GRES unknown, check `gres.conf`, driver state, and `slurmd` logs (`journalctl -u slurmd`).

## Not included (on purpose)

- `slurmdbd` / MySQL accounting
- `slurmrestd`
- Fancy topologies, burst buffers, MPI integration guides

Add those only when the lab needs them.
