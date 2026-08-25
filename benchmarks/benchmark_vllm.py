#!/usr/bin/env python3
"""
Reproducible vLLM OpenAI-compatible inference benchmark (stdlib only).

Does not fabricate metrics: JSON under benchmarks/results/ is written only from
live API measurements collected during this run.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PROMPT = (
    "Write a short technical paragraph explaining what a Linux systemd unit is."
)


@dataclass
class RequestResult:
    ok: bool
    latency_ms: float
    ttft_ms: float | None = None
    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    error: str | None = None
    streamed: bool = False


@dataclass
class BenchmarkReport:
    """Collected measurements from a single live run (not an example)."""

    schema: str = "research-ai-infrastructure-lab.benchmark_vllm.v1"
    result_type: str = "collected_measurement"
    disclaimer: str = (
        "Values in this file were measured against a live endpoint in this run. "
        "They are not sample/placeholder numbers."
    )
    timestamp_utc: str = ""
    url: str = ""
    model: str = ""
    gpu: str | None = None
    requests: int = 0
    concurrency: int = 0
    max_tokens: int = 0
    stream_for_ttft: bool = False
    prompt_chars: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    wall_time_sec: float = 0.0
    latency_ms: dict[str, float | None] = field(default_factory=dict)
    throughput_requests_per_second: float | None = None
    tokens_per_second: float | None = None
    ttft_ms: dict[str, float | None] | None = None
    generation_tokens_per_second: float | None = None
    errors_sample: list[str] = field(default_factory=list)


def percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def summarize_latencies(values_ms: list[float]) -> dict[str, float | None]:
    if not values_ms:
        return {"p50": None, "p95": None, "p99": None, "mean": None, "min": None, "max": None}
    ordered = sorted(values_ms)
    return {
        "p50": round(percentile(ordered, 50) or 0.0, 3),
        "p95": round(percentile(ordered, 95) or 0.0, 3),
        "p99": round(percentile(ordered, 99) or 0.0, 3),
        "mean": round(statistics.fmean(ordered), 3),
        "min": round(ordered[0], 3),
        "max": round(ordered[-1], 3),
    }


def detect_gpu() -> str | None:
    """Best-effort host GPU label; None if nvidia-smi is unavailable."""
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return " | ".join(lines) if lines else None


def resolve_model(base_url: str, model: str | None, timeout: float) -> str:
    if model:
        return model
    url = f"{base_url.rstrip('/')}/v1/models"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"No models returned from {url}")
    mid = data[0].get("id")
    if not mid:
        raise RuntimeError(f"Unexpected /v1/models payload: {body!r}")
    return str(mid)


def build_payload(model: str, prompt: str, max_tokens: int, stream: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": stream,
    }
    if stream:
        # OpenAI-compatible: include usage on the final SSE chunk when the server supports it.
        payload["stream_options"] = {"include_usage": True}
    return payload


def run_non_stream(
    chat_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
) -> RequestResult:
    payload = build_payload(model, prompt, max_tokens, stream=False)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        chat_url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            body = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return RequestResult(False, elapsed_ms, error=f"HTTP {exc.code}: {detail}")
    except Exception as exc:  # noqa: BLE001 — record transport failures per request
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return RequestResult(False, elapsed_ms, error=str(exc))

    usage = body.get("usage") if isinstance(body, dict) else None
    completion_tokens = None
    prompt_tokens = None
    if isinstance(usage, dict):
        if isinstance(usage.get("completion_tokens"), int):
            completion_tokens = usage["completion_tokens"]
        if isinstance(usage.get("prompt_tokens"), int):
            prompt_tokens = usage["prompt_tokens"]

    try:
        _ = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return RequestResult(
            False,
            elapsed_ms,
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            error="missing choices/message/content",
        )

    return RequestResult(
        True,
        elapsed_ms,
        completion_tokens=completion_tokens,
        prompt_tokens=prompt_tokens,
        streamed=False,
    )


def run_stream(
    chat_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
) -> RequestResult:
    """Streaming request: measure TTFT (first content delta) and end-to-end latency."""
    payload = build_payload(model, prompt, max_tokens, stream=True)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        chat_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    started = time.perf_counter()
    ttft_ms: float | None = None
    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    saw_content = False

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            while True:
                line = resp.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text or text.startswith(":"):
                    continue
                if not text.startswith("data:"):
                    continue
                data_str = text[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                usage = chunk.get("usage") if isinstance(chunk, dict) else None
                if isinstance(usage, dict):
                    if isinstance(usage.get("completion_tokens"), int):
                        completion_tokens = usage["completion_tokens"]
                    if isinstance(usage.get("prompt_tokens"), int):
                        prompt_tokens = usage["prompt_tokens"]

                choices = chunk.get("choices") if isinstance(chunk, dict) else None
                if not isinstance(choices, list) or not choices:
                    continue
                delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                content = delta.get("content") if isinstance(delta, dict) else None
                if content:
                    saw_content = True
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - started) * 1000.0

        elapsed_ms = (time.perf_counter() - started) * 1000.0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return RequestResult(False, elapsed_ms, error=f"HTTP {exc.code}: {detail}", streamed=True)
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return RequestResult(False, elapsed_ms, error=str(exc), streamed=True)

    if not saw_content:
        return RequestResult(
            False,
            elapsed_ms,
            ttft_ms=ttft_ms,
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            error="stream completed without content deltas",
            streamed=True,
        )

    return RequestResult(
        True,
        elapsed_ms,
        ttft_ms=ttft_ms,
        completion_tokens=completion_tokens,
        prompt_tokens=prompt_tokens,
        streamed=True,
    )


def run_benchmark(
    base_url: str,
    model: str,
    requests_n: int,
    concurrency: int,
    max_tokens: int,
    prompt: str,
    timeout: float,
    measure_ttft: bool,
) -> BenchmarkReport:
    chat_url = f"{base_url.rstrip('/')}/v1/chat/completions"
    worker = run_stream if measure_ttft else run_non_stream

    results: list[RequestResult] = []
    wall_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [
            pool.submit(worker, chat_url, model, prompt, max_tokens, timeout)
            for _ in range(requests_n)
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    wall_time = time.perf_counter() - wall_started

    oks = [r for r in results if r.ok]
    fails = [r for r in results if not r.ok]
    latencies = [r.latency_ms for r in oks]
    ttfts = [r.ttft_ms for r in oks if r.ttft_ms is not None]

    completion_tokens_total = sum(r.completion_tokens or 0 for r in oks if r.completion_tokens)
    tokens_measured = [r for r in oks if r.completion_tokens]

    tokens_per_second = None
    if completion_tokens_total > 0 and wall_time > 0:
        tokens_per_second = round(completion_tokens_total / wall_time, 3)

    gen_rates: list[float] = []
    for r in oks:
        if r.completion_tokens and r.ttft_ms is not None and r.latency_ms > r.ttft_ms:
            gen_sec = (r.latency_ms - r.ttft_ms) / 1000.0
            if gen_sec > 0:
                gen_rates.append(r.completion_tokens / gen_sec)
        elif (
            r.completion_tokens
            and r.ttft_ms is None
            and r.latency_ms > 0
            and not measure_ttft
        ):
            # Non-stream: e2e includes prefill; still report as approximate generation rate.
            gen_rates.append(r.completion_tokens / (r.latency_ms / 1000.0))

    generation_tps = round(statistics.fmean(gen_rates), 3) if gen_rates else None
    rps = round(len(oks) / wall_time, 3) if wall_time > 0 else None

    report = BenchmarkReport(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        url=base_url.rstrip("/"),
        model=model,
        gpu=detect_gpu(),
        requests=requests_n,
        concurrency=concurrency,
        max_tokens=max_tokens,
        stream_for_ttft=measure_ttft,
        prompt_chars=len(prompt),
        total_requests=len(results),
        successful_requests=len(oks),
        failed_requests=len(fails),
        wall_time_sec=round(wall_time, 3),
        latency_ms=summarize_latencies(latencies),
        throughput_requests_per_second=rps,
        tokens_per_second=tokens_per_second,
        ttft_ms=summarize_latencies(ttfts) if measure_ttft else None,
        generation_tokens_per_second=generation_tps,
        errors_sample=[r.error for r in fails[:5] if r.error],
    )

    if oks and len(tokens_measured) < len(oks):
        report.errors_sample.append(
            f"note: completion_tokens present on {len(tokens_measured)}/{len(oks)} successful responses"
        )

    return report


def default_results_dir() -> Path:
    return Path(__file__).resolve().parent / "results"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark a live vLLM OpenAI-compatible API. "
            "Writes collected measurements only (never fabricated)."
        )
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL without /v1 (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model id (default: first id from GET /v1/models)",
    )
    parser.add_argument("--requests", type=int, default=20, help="Total requests to send")
    parser.add_argument("--concurrency", type=int, default=2, help="Concurrent workers")
    parser.add_argument("--max-tokens", type=int, default=64, help="max_tokens per request")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="User prompt text")
    parser.add_argument("--timeout", type=float, default=300.0, help="Per-request timeout seconds")
    parser.add_argument(
        "--ttft",
        action="store_true",
        help="Use streaming to measure time-to-first-token and decode generation tokens/s",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory for JSON output (default: benchmarks/results/)",
    )
    parser.add_argument(
        "--dry-run-schema",
        action="store_true",
        help="Print example JSON schema only; do not call the API or write measurements",
    )
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1 or args.max_tokens < 1:
        print("ERROR: --requests, --concurrency, and --max-tokens must be >= 1", file=sys.stderr)
        return 2

    if args.dry_run_schema:
        example = {
            "_comment": (
                "EXAMPLE SCHEMA ONLY — not measured data. "
                "Run without --dry-run-schema against a live API to collect real results."
            ),
            "result_type": "example_schema",
            "model": "...",
            "gpu": "...",
            "requests": 100,
            "concurrency": 4,
            "latency_ms": {"p50": 0, "p95": 0, "p99": 0},
            "throughput_requests_per_second": 0,
            "tokens_per_second": 0,
        }
        print(json.dumps(example, indent=2))
        return 0

    results_dir = args.results_dir or default_results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)

    try:
        model = resolve_model(args.url, args.model, timeout=min(60.0, args.timeout))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot resolve model from {args.url}: {exc}", file=sys.stderr)
        return 1

    print(
        f"Benchmarking model={model!r} url={args.url} "
        f"requests={args.requests} concurrency={args.concurrency} "
        f"max_tokens={args.max_tokens} ttft={args.ttft}"
    )

    report = run_benchmark(
        base_url=args.url,
        model=model,
        requests_n=args.requests,
        concurrency=args.concurrency,
        max_tokens=args.max_tokens,
        prompt=args.prompt,
        timeout=args.timeout,
        measure_ttft=args.ttft,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = "".join(c if c.isalnum() or c in "-._" else "_" for c in model)[:80]
    out_path = results_dir / f"benchmark_{safe_model}_{stamp}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    print("--- collected measurements ---")
    print(f"total={report.total_requests} ok={report.successful_requests} fail={report.failed_requests}")
    print(f"latency_ms={report.latency_ms}")
    print(f"throughput_requests_per_second={report.throughput_requests_per_second}")
    print(f"tokens_per_second={report.tokens_per_second}")
    if report.ttft_ms is not None:
        print(f"ttft_ms={report.ttft_ms}")
    print(f"generation_tokens_per_second={report.generation_tokens_per_second}")
    print(f"gpu={report.gpu}")
    print(f"wrote {out_path}")

    if report.successful_requests == 0:
        print("ERROR: all requests failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
