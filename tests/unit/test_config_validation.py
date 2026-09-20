#!/usr/bin/env python3
"""Static configuration validation used by CI (no GPU, no remote SSH)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def iter_yaml_files() -> list[Path]:
    patterns = [
        "ansible/**/*.yml",
        "ansible/**/*.yaml",
        "containers/**/*.yml",
        ".github/workflows/*.yml",
        ".yamllint.yml",
        ".ansible-lint",
        "monitoring/**/*.yml",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(ROOT.glob(pattern))
    seen: set[Path] = set()
    out: list[Path] = []
    for path in sorted(files):
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        out.append(path)
    return out


def test_yaml_files_parse() -> None:
    errors: list[str] = []
    files = iter_yaml_files()
    assert files, "expected YAML files under ansible/ and workflows"
    for path in files:
        try:
            with path.open(encoding="utf-8") as fh:
                list(yaml.safe_load_all(fh))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    assert not errors, "YAML parse failures:\n" + "\n".join(errors)


def test_required_repo_paths_exist() -> None:
    required = [
        "ansible/playbooks/site.yml",
        "ansible/playbooks/ai-server.yml",
        "ansible/playbooks/monitoring.yml",
        "ansible/inventory/hosts.yml",
        "ansible/inventory/group_vars/all.yml",
        "ansible/inventory/group_vars/ai_nodes.yml",
        "ansible/inventory/group_vars/monitoring_nodes.yml",
        "ansible/inventory/host_vars/ai-node-01.yml",
        "ansible/inventory/host_vars/utility-node-01.yml",
        "ansible/roles/vllm/tasks/main.yml",
        "ansible/roles/monitoring/tasks/main.yml",
        "ansible/roles/node_exporter/tasks/main.yml",
        "scripts/health-check.sh",
        "scripts/diagnose.sh",
        "benchmarks/benchmark_vllm.py",
        "docs/testing.md",
        "docs/multi-node.md",
        "docs/deployment-validation.md",
        "docs/security/secrets.md",
    ]
    missing = [p for p in required if not (ROOT / p).is_file()]
    assert not missing, f"missing required paths: {missing}"


def test_inventory_defines_ai_and_monitoring_groups() -> None:
    inv = yaml.safe_load((ROOT / "ansible/inventory/hosts.yml").read_text(encoding="utf-8"))
    children = inv["all"].get("children") or {}
    assert "ai_nodes" in children
    assert "monitoring_nodes" in children
    assert "ai-node-01" in (children["ai_nodes"].get("hosts") or {})
    assert "utility-node-01" in (children["monitoring_nodes"].get("hosts") or {})


def test_group_vars_vllm_defaults_are_private_by_default() -> None:
    data = yaml.safe_load(
        (ROOT / "ansible/inventory/group_vars/ai_nodes.yml").read_text(encoding="utf-8")
    )
    assert data.get("vllm_host") == "127.0.0.1"
    assert data.get("vllm_firewall_allow_cidrs") == []
    assert "vllm_model" in data
    assert "vllm_port" in data


def test_site_playbook_targets_expected_groups() -> None:
    data = yaml.safe_load((ROOT / "ansible/playbooks/site.yml").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    hosts = [p.get("hosts") for p in data if isinstance(p, dict)]
    assert "all" in hosts
    assert "ai_nodes" in hosts
    assert "monitoring_nodes" in hosts


def test_prometheus_blackbox_uses_compose_dns() -> None:
    standalone = (ROOT / "monitoring/prometheus/prometheus.yml").read_text(encoding="utf-8")
    assert 'replacement: "blackbox-exporter:9115"' in standalone
    assert "replacement: 127.0.0.1:9115" not in standalone
    template = (ROOT / "ansible/roles/monitoring/templates/prometheus.yml.j2").read_text(
        encoding="utf-8"
    )
    assert "monitoring_blackbox_address" in template
    assert "replacement: 127.0.0.1:9115" not in template


def test_grafana_password_is_not_hardcoded() -> None:
    banned = "lab-change-me"
    for rel in [
        "ansible/inventory/group_vars/monitoring_nodes.yml",
        "monitoring/compose.yml",
        "monitoring/.env.example",
    ]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert banned not in text, f"{rel} still contains a published Grafana password"
    defaults = yaml.safe_load(
        (ROOT / "ansible/roles/monitoring/defaults/main.yml").read_text(encoding="utf-8")
    )
    assert defaults.get("monitoring_grafana_admin_password") in (None, "")
    assert banned in (defaults.get("monitoring_grafana_disallowed_passwords") or [])
    compose = (ROOT / "monitoring/compose.yml").read_text(encoding="utf-8")
    assert "${GRAFANA_ADMIN_PASSWORD:?" in compose


def test_podman_role_installs_and_validates_compose() -> None:
    tasks = (ROOT / "ansible/roles/container_runtime/tasks/podman.yml").read_text(encoding="utf-8")
    assert "podman compose version" in tasks
    defaults = (ROOT / "ansible/roles/container_runtime/defaults/main.yml").read_text(
        encoding="utf-8"
    )
    assert "podman-compose" in defaults
    unit = (ROOT / "ansible/roles/monitoring/templates/lab-monitoring.service.j2").read_text(
        encoding="utf-8"
    )
    assert "ExecStartPre=/usr/bin/podman compose version" in unit


def test_vllm_image_pin_unchanged_without_compat_change() -> None:
    data = yaml.safe_load(
        (ROOT / "ansible/inventory/group_vars/ai_nodes.yml").read_text(encoding="utf-8")
    )
    assert data.get("vllm_container_image") == "vllm/vllm-openai:v0.6.3"
    assert data.get("vllm_model") == "Qwen/Qwen2.5-7B-Instruct"


def test_markdown_internal_links_resolve() -> None:
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    skip_parts = {".venv", "venv", "node_modules", ".git"}
    missing: list[str] = []
    for path in ROOT.rglob("*.md"):
        if skip_parts.intersection(path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for match in link_re.finditer(text):
            raw = match.group(1).strip()
            target = raw.split()[0].split("#")[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            dest = (path.parent / target).resolve()
            if not dest.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not missing, "broken internal markdown links:\n" + "\n".join(missing)


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__]))
