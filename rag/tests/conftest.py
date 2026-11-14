"""Fixtures shared by the hub-rag test suite."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_ROOT = REPO_ROOT / "rag"
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))


@pytest.fixture(autouse=True)
def policy_dir(monkeypatch: pytest.MonkeyPatch):
    """Point configuration at this checkout and isolate its cached settings."""
    from hub_rag import config

    monkeypatch.setenv("HUB_POLICY_DIR", str(REPO_ROOT / "policy"))
    for cached in (config.settings, config.ingest_policy, config.scopes_policy):
        cached.cache_clear()
    yield
    for cached in (config.settings, config.ingest_policy, config.scopes_policy):
        cached.cache_clear()
