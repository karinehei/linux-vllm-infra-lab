"""Shared fixtures for unit and integration tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def vllm_base_url() -> str:
    return os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
