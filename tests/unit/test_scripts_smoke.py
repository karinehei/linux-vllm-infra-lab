from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


@pytest.mark.parametrize(
    "script",
    [
        "health-check.sh",
        "gpu-status.sh",
        "service-status.sh",
        "disk-status.sh",
        "diagnose.sh",
        "health/check_vllm_api.sh",
    ],
)
def test_script_has_shebang_and_pipefail(script: str) -> None:
    path = SCRIPTS / script
    text = path.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text


def _bash_script(script_relative: str, *args: str) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    # Relative path + cwd=ROOT works for Git Bash and Linux; absolute Windows
    # paths often break under WSL's system32 bash.exe.
    rel = Path("scripts") / script_relative
    proc = subprocess.run(
        [bash, rel.as_posix(), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if proc.returncode == 127 or "No such file" in (proc.stderr or ""):
        pytest.skip(f"bash cannot execute {rel.as_posix()} on this platform")
    return proc


def test_gpu_status_help_documents_allow_missing() -> None:
    proc = _bash_script("gpu-status.sh", "--help")
    assert proc.returncode == 0, proc.stderr
    assert "--allow-missing" in proc.stdout


def test_health_check_help() -> None:
    proc = _bash_script("health-check.sh", "--help")
    assert proc.returncode == 0, proc.stderr
    assert "/v1/models" in proc.stdout


def test_diagnose_help() -> None:
    proc = _bash_script("diagnose.sh", "--help")
    assert proc.returncode == 0, proc.stderr
    assert "Redacts" in proc.stdout or "redact" in proc.stdout.lower()
