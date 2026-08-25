# Control-node setup

How to prepare the **Ansible control node** (laptop or jump host) before converging Rocky Linux lab hosts. This is not a local “run the app” guide — inference runs on GPU servers after Ansible provisions them.

For host OS / GPU requirements, see [`prerequisites.md`](prerequisites.md). Secrets details: [`security/secrets.md`](security/secrets.md).

## 1. Install Ansible tooling

Prefer a **Python virtualenv on a Linux filesystem**. On WSL, do **not** put `.venv` under `/mnt/d/...` (NTFS mounts make `pip install` extremely slow or appear hung).

```bash
# From the repo root (repo may live on /mnt/d; venv stays in $HOME)
python3 -m venv ~/.venvs/linux-vllm-infra-lab
source ~/.venvs/linux-vllm-infra-lab/bin/activate
pip install -U pip
pip install -r requirements-dev.txt

ansible --version
ansible-vault --version
```

Activate that venv in every shell where you run playbooks, `make check`, or vault commands.

**Quick alternative (Vault / playbooks only):**

```bash
sudo apt update
sudo apt install -y ansible-core
```

Optional shortcuts after tools are on `PATH`: [`Makefile`](../Makefile) (`make help`, `make deploy`, `make check`).

## 2. Configure inventory

1. Edit `ansible/inventory/hosts.yml` — replace example `192.0.2.x` addresses and `ansible_user`.
2. Confirm SSH key login works: `ssh rocky@<ai-node>`.
3. Review `ansible/inventory/group_vars/ai_nodes.yml` (model, bind address, VRAM knobs).

Single GPU host is enough: keep one entry under `ai_nodes`. Add `monitoring_nodes` only if you have a utility host.

## 3. Optional: Ansible Vault

Needed only if you use a Hugging Face token or non-default Grafana password.

```bash
cp ansible/inventory/group_vars/ai_nodes_vault.yml.example \
   ansible/inventory/group_vars/vault.yml
# Edit placeholders, then:
ansible-vault encrypt ansible/inventory/group_vars/vault.yml
```

Uncomment `vllm_hf_token: "{{ vault_vllm_hf_token }}"` in `ai_nodes.yml` when using a token. Pass `--ask-vault-pass` (or a mode-`0600` password file) on playbook runs. Never commit plaintext `vault.yml`.

## 4. First converge

NVIDIA **drivers** are opt-in (`nvidia_install_drivers: false` by default). Install them yourself or enable once, reboot, then set back to `false` — see [`nvidia.md`](nvidia.md).

```bash
# Full lab (AI + monitoring groups present in inventory)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml

# Or AI only
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --limit ai_nodes
```

`vllm_service_started` defaults to **`false`**, so the unit is installed but not started until GPU + disk are ready.

## 5. Start inference (on the AI node)

```bash
sudo systemctl start vllm
journalctl -u vllm -f
```

First start may pull the image and download weights into `/var/lib/vllm/cache`. When ready:

```bash
# On the AI node, or via SSH tunnel from the control node:
ssh -L 8000:127.0.0.1:8000 rocky@ai-node-01
python3 scripts/test-inference.py --base-url http://127.0.0.1:8000
```

Day-2 checks: `./scripts/diagnose.sh`. API / VRAM notes: [`vllm.md`](vllm.md).

## 6. Static checks only (no GPU)

On the control node, with the venv active:

```bash
make check
# or: make lint && make test
```

Hosted GitHub Actions runs the same class of checks; live GPU tests stay on the lab host ([`testing.md`](testing.md)).
