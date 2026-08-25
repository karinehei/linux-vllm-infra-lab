#!/usr/bin/env python3
"""Smoke-test the OpenAI-compatible vLLM API (stdlib only)."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, Any, float]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        parsed: Any = json.loads(body) if body else None
        return resp.status, parsed, elapsed_ms


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test vLLM OpenAI-compatible /v1/models and chat completions."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL without trailing /v1 (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model id for chat.completions (default: first id from /v1/models)",
    )
    parser.add_argument(
        "--prompt",
        default="Say hello in one short sentence.",
        help="User message for the smoke chat completion",
    )
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    models_url = f"{base}/v1/models"
    chat_url = f"{base}/v1/chat/completions"

    try:
        status, models_body, models_ms = http_json("GET", models_url, timeout=args.timeout)
    except urllib.error.HTTPError as exc:
        print(f"ERROR: GET /v1/models failed: HTTP {exc.code} {exc.reason}")
        return 1
    except urllib.error.URLError as exc:
        print(f"ERROR: GET /v1/models failed: {exc.reason}")
        return 1
    except Exception as exc:  # noqa: BLE001 — surface any transport/parse issue cleanly
        print(f"ERROR: GET /v1/models failed: {exc}")
        return 1

    data = (models_body or {}).get("data") if isinstance(models_body, dict) else None
    if status != 200 or not isinstance(data, list) or not data:
        print(f"ERROR: unexpected /v1/models response (status={status}): {models_body!r}")
        return 1

    model_ids = [item.get("id") for item in data if isinstance(item, dict) and item.get("id")]
    model = args.model or model_ids[0]
    print(f"OK: /v1/models ({models_ms:.0f} ms) — {len(model_ids)} model(s); using {model!r}")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": args.max_tokens,
        "temperature": 0.2,
    }

    try:
        status, chat_body, chat_ms = http_json(
            "POST", chat_url, payload=payload, timeout=args.timeout
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"ERROR: POST /v1/chat/completions failed: HTTP {exc.code} — {detail[:400]}")
        return 1
    except urllib.error.URLError as exc:
        print(f"ERROR: POST /v1/chat/completions failed: {exc.reason}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: POST /v1/chat/completions failed: {exc}")
        return 1

    if status != 200 or not isinstance(chat_body, dict):
        print(f"ERROR: unexpected chat response (status={status}): {chat_body!r}")
        return 1

    try:
        content = chat_body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(f"ERROR: chat response missing choices/message/content: {chat_body!r}")
        return 1

    preview = " ".join(str(content).split())
    if len(preview) > 160:
        preview = preview[:157] + "..."

    print(f"OK: /v1/chat/completions ({chat_ms:.0f} ms)")
    print(f"LATENCY_MS: {chat_ms:.1f}")
    print(f"REPLY: {preview}")
    print("SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
