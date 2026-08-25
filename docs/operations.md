# Operations guide

## Provision / converge

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml
```

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --limit ai-node-01
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/site.yml --tags security,vllm
```

Multi-node layout: [`multi-node.md`](multi-node.md).

## Service lifecycle (systemd)

```bash
systemctl status vllm
systemctl start vllm
systemctl stop vllm
systemctl restart vllm
journalctl -u vllm
journalctl -u vllm -f
```

Enabled units start after boot once network (and Docker, if used) are ready. Restarts after crashes are limited so permanent errors stay visible — see [`systemd-lifecycle.md`](systemd-lifecycle.md).

Default API bind: `127.0.0.1:8000` (not public). Inference docs: [`vllm.md`](vllm.md).

```bash
/usr/local/sbin/vllm-preflight
/usr/local/sbin/check-vllm-health --wait 300
./scripts/health-check.sh
./scripts/diagnose.sh
python3 scripts/test-inference.py --base-url http://127.0.0.1:8000
```

Operational scripts: [`../scripts/README.md`](../scripts/README.md).

## Model changes

Update `vllm_model` in `ansible/inventory/group_vars/ai_nodes.yml` (or `host_vars/`), re-run `--tags vllm`, then `systemctl restart vllm`.

## GPU / drivers

See [`nvidia.md`](nvidia.md).

## Secrets

See [`security/secrets.md`](security/secrets.md). Full review: [`security.md`](security.md).

## Monitoring

Lightweight Prometheus/Grafana stack: [`monitoring.md`](monitoring.md) · compose under `monitoring/`.
