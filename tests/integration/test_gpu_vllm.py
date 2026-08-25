"""
GPU / live-API integration tests.

These tests are intentionally excluded from normal hosted CI.
Run on a Linux GPU host with vLLM listening (see docs/testing.md).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.gpu]


def _get_json(url: str, timeout: float = 30.0):
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_nvidia_smi_available() -> None:
    if not shutil.which("nvidia-smi"):
        pytest.skip("nvidia-smi not installed on this host")
    proc = subprocess.run(
        ["nvidia-smi"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_vllm_models_endpoint(vllm_base_url: str) -> None:
    try:
        status, body = _get_json(f"{vllm_base_url}/v1/models", timeout=60.0)
    except urllib.error.URLError as exc:
        pytest.fail(f"vLLM API not reachable at {vllm_base_url}: {exc}")
    assert status == 200
    assert isinstance(body.get("data"), list)
    assert body["data"], "expected at least one model"


def test_vllm_chat_completion(vllm_base_url: str) -> None:
    _, models = _get_json(f"{vllm_base_url}/v1/models", timeout=60.0)
    model = models["data"][0]["id"]
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with the single word: pong"}],
            "max_tokens": 8,
            "temperature": 0.0,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{vllm_base_url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            assert resp.status == 200
    except urllib.error.URLError as exc:
        pytest.fail(f"chat completion failed: {exc}")
    content = body["choices"][0]["message"]["content"]
    assert isinstance(content, str) and content.strip()


@pytest.mark.benchmark
def test_benchmark_smoke(vllm_base_url: str, tmp_path, repo_root) -> None:
    script = repo_root / "benchmarks" / "benchmark_vllm.py"
    out_dir = tmp_path / "results"
    proc = subprocess.run(
        [
            "python3",
            str(script),
            "--url",
            vllm_base_url,
            "--requests",
            "2",
            "--concurrency",
            "1",
            "--max-tokens",
            "16",
            "--results-dir",
            str(out_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
        env={**os.environ},
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    files = list(out_dir.glob("benchmark_*.json"))
    assert files, "expected a collected measurement JSON file"
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["result_type"] == "collected_measurement"
    assert data["successful_requests"] >= 1
