# Ansible — centrally managed Linux lab

Idempotent roles for a **small multi-node** Rocky Linux 9 / RHEL 9-compatible environment.

## Architecture

```text
Ansible control node
        |
        +---- ai_nodes          (GPU + vLLM)
        +---- monitoring_nodes  (Prometheus/Grafana)
```

Details: [`docs/multi-node.md`](../docs/multi-node.md).

## Provisioning commands

```bash
# Entire fleet (recommended)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml

# AI nodes only
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/ai-server.yml

# Utility / monitoring only
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/monitoring.yml
```

## Roles

| Role | Applied to | Purpose |
|------|------------|---------|
| `common` | all | Packages, timezone, hostname, chrony |
| `security` | all | SSH hardening, firewalld |
| `users` | ai_nodes | vLLM service account + directories |
| `container_runtime` | ai + monitoring | Podman (default) or Docker |
| `nvidia` | ai_nodes | GPU detect / toolkit |
| `vllm` | ai_nodes | Inference service |
| `node_exporter` | flagged hosts | Host metrics for Prometheus |
| `monitoring` | monitoring_nodes | Prometheus/Grafana compose stack |

## Inventory layout

```
ansible/inventory/
├── hosts.yml
├── hosts.yml.example
├── group_vars/
│   ├── all.yml
│   ├── ai_nodes.yml
│   ├── monitoring_nodes.yml
│   └── ai_nodes_vault.yml.example
└── host_vars/
    ├── ai-node-01.yml
    └── utility-node-01.yml
```

## Drift prevention

Re-run `site.yml` regularly. Ansible modules converge to the declared state (packages present, templates checksum-matched, services enabled). Unexpected manual edits are overwritten or reported as `changed` on the next run.

## Related docs

- [Multi-node administration](../docs/multi-node.md)
- [NVIDIA guidance](../docs/nvidia.md)
- [Monitoring](../docs/monitoring.md)
- [Secrets / Vault](../docs/security/secrets.md)
