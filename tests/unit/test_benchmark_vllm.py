from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks" / "benchmark_vllm.py"


def load_benchmark_module():
    name = "benchmark_vllm"
    spec = importlib.util.spec_from_file_location(name, BENCH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Required so @dataclass can resolve typing on the module during exec_module.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bench():
    return load_benchmark_module()


def test_percentile_empty(bench) -> None:
    assert bench.percentile([], 50) is None


def test_percentile_known_values(bench) -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert bench.percentile(values, 50) == 30.0
    assert bench.percentile(values, 0) == 10.0
    assert bench.percentile(values, 100) == 50.0


def test_summarize_latencies(bench) -> None:
    summary = bench.summarize_latencies([100.0, 200.0, 300.0, 400.0])
    assert summary["p50"] is not None
    assert summary["p95"] is not None
    assert summary["p99"] is not None
    assert summary["mean"] == 250.0
    assert summary["min"] == 100.0
    assert summary["max"] == 400.0


def test_build_payload_stream_flag(bench) -> None:
    non_stream = bench.build_payload("m", "hi", 16, stream=False)
    assert non_stream["stream"] is False
    assert "stream_options" not in non_stream

    streamed = bench.build_payload("m", "hi", 16, stream=True)
    assert streamed["stream"] is True
    assert streamed["stream_options"]["include_usage"] is True


def test_dry_run_schema_is_example_not_measurement() -> None:
    proc = subprocess.run(
        [sys.executable, str(BENCH), "--dry-run-schema"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["result_type"] == "example_schema"
    assert "EXAMPLE" in data["_comment"].upper() or "example" in data["_comment"].lower()
