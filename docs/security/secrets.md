# Secrets handling

## Principles

- Never commit tokens, passwords, or private keys.
- Prefer SSH public-key auth for Ansible.
- Use **Ansible Vault** for values that must live near inventory.

## Where to store secrets

| Secret | Recommended location |
|--------|----------------------|
| SSH private key | Operator machine only (`~/.ssh/`), referenced from inventory if needed |
| Vault password | `~/.ansible/lab-vault-pass` (mode 0600) or `--ask-vault-pass` |
| Hugging Face token | Encrypted `ansible/inventory/group_vars/vault.yml` as `vault_vllm_hf_token` |
| Grafana admin password | Same vault file as `vault_monitoring_grafana_admin_password` (required for monitoring nodes) |
| Registry credentials | Same vault file; map into role vars |
| Model license files | Host disk under `vllm_model_path`, not git |

## Vault-compatible pattern

Requires `ansible-vault` on the control node — see [`../setup.md`](../setup.md) if the command is missing.

1. Copy the example:

```bash
cp ansible/inventory/group_vars/ai_nodes_vault.yml.example \
   ansible/inventory/group_vars/vault.yml
```

2. Edit placeholders, then encrypt:

```bash
ansible-vault encrypt ansible/inventory/group_vars/vault.yml
```

3. Wire references:

In `ansible/inventory/group_vars/ai_nodes.yml` (uncomment when using a gated model):

```yaml
vllm_hf_token: "{{ vault_vllm_hf_token }}"
```

`monitoring_nodes.yml` already maps `monitoring_grafana_admin_password` from
`vault_monitoring_grafana_admin_password`. The monitoring role refuses empty
values and published lab defaults.

4. Run:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --ask-vault-pass
# or AI nodes only:
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/ai-server.yml --ask-vault-pass
```

`vault.yml` under `group_vars/` is auto-loaded for all groups when present; keep it encrypted.

## Git hygiene

Ensure these remain untracked or encrypted:

- `ansible/inventory/group_vars/vault.yml`
- `*.vault`
- `.vault_pass` / vault password files
- `.env` files with tokens
