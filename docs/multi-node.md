# Multi-node centralized Linux administration

This lab is managed as a **small fleet** from one Ansible control node—not a single snowflake server.

## Architecture

```text
Ansible control node
        |
        +---- ai-node-01          (group: ai_nodes)
        |       NVIDIA GPU
        |       vLLM + node_exporter
        |
        +---- utility-node-01     (group: monitoring_nodes)
                Prometheus / Grafana
                administrative / metrics services
```

| Group | Purpose | Typical roles |
|-------|---------|----------------|
| `all` | Shared baseline | `common`, `security` |
| `ai_nodes` | GPU inference | `users`, `container_runtime`, `nvidia`, `vllm`, `node_exporter` |
| `monitoring_nodes` | Central metrics UI | `container_runtime`, `node_exporter`, `monitoring` |

Inventory: [`ansible/inventory/hosts.yml`](../ansible/inventory/hosts.yml)  
Site playbook: [`ansible/playbooks/site.yml`](../ansible/playbooks/site.yml)

## What this demonstrates

| Practice | How |
|----------|-----|
| Centralized configuration | One inventory + `group_vars` / `host_vars` + `site.yml` |
| Consistent package management | `common` role on every host (`common_packages`, optional `dnf` update) |
| Service deployment by role | vLLM only on `ai_nodes`; Prometheus/Grafana only on `monitoring_nodes` |
| Security configuration | SSH hardening + firewalld applied fleet-wide, with group-specific port allowlists |
| Drift prevention | Re-run the same playbook; modules are idempotent (`state=present`, templates+handlers) |
| Host- vs group-specific config | `group_vars/ai_nodes.yml` vs `host_vars/ai-node-01.yml` |

Variable precedence (simplified): **host_vars > group_vars > role defaults**.

## Deploy the environment

```bash
# Full fleet from the control node
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml

# Only inference nodes
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --limit ai_nodes

# Only utility / monitoring
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --limit monitoring_nodes
```

Convenience playbooks: `ai-server.yml` (AI group), `monitoring.yml` (utility group).

## Scraping AI nodes from the utility host

By default vLLM binds to `127.0.0.1` (secure lab posture). Central Prometheus on `utility-node-01` can still scrape **node_exporter** when:

1. `node_exporter` listens on a reachable address (`0.0.0.0` in the role default)
2. `node_exporter_firewall_allow_cidrs` includes the utility host (see `group_vars/ai_nodes.yml`)

To scrape vLLM `/health` or `/metrics` remotely, set on the AI host (host_vars or group_vars):

```yaml
vllm_host: "192.0.2.10"   # private NIC / ansible_host
vllm_firewall_allow_cidrs: ["192.0.2.20/32"]  # utility-node-01
```

Prometheus scrape targets are **generated from inventory** (`roles/monitoring/templates/prometheus.yml.j2`)—adding a host updates targets on the next converge.

## Adding a third Linux server (no automation rewrite)

Example: add another GPU inference node `ai-node-02`.

1. **Inventory** — add the host under the existing group (or create a new group if the role set differs):

```yaml
ai_nodes:
  hosts:
    ai-node-01:
      ansible_host: 192.0.2.10
      ansible_user: rocky
    ai-node-02:
      ansible_host: 192.0.2.11
      ansible_user: rocky
```

2. **Host vars** (optional) — `ansible/inventory/host_vars/ai-node-02.yml`:

```yaml
common_manage_hostname: true
common_hostname: ai-node-02
vllm_max_model_len: 2048          # host-specific tuning
monitoring_scrape_ip: 192.0.2.11
```

3. **Group vars** — usually unchanged; `ai_nodes.yml` already defines the role baseline.

4. **Converge**:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --limit ai-node-02
# then refresh monitoring so Prometheus picks up the new scrape target:
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --limit monitoring_nodes --tags monitoring
```

Example: add a second utility host for a jump box—place it in `monitoring_nodes` or a new `bastion` group with only `common` + `security` roles in `site.yml` (one playbook edit for a **new role set**, not a rewrite of existing roles).

Idempotency: running `site.yml` again against all hosts should report mostly `ok`/`skipped` when nothing changed—that is configuration drift prevention.

## Related

- [`ansible/README.md`](../ansible/README.md)
- [`docs/monitoring.md`](monitoring.md)
- [`docs/security.md`](security.md)
