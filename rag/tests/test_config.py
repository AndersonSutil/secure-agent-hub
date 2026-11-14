from __future__ import annotations

from pathlib import Path

import pytest

from hub_rag.config import Source, load_sources, load_tokens, scopes_policy


def test_source_rejects_memory_invalid_trust_and_untrusted_docs():
    with pytest.raises(ValueError):
        Source("memory", "/sources/memory", "memory", "trusted")
    with pytest.raises(ValueError):
        Source("invalid", "/sources/invalid", "docs", "agent")
    with pytest.raises(ValueError):
        Source("untrusted", "/sources/untrusted", "docs", "untrusted")


def test_load_sources_uses_container_path(tmp_path):
    sources_file = tmp_path / "sources.toml"
    sources_file.write_text(
        """[[source]]
name = "manual"
container_path = "/mounted/manual"
collection = "docs"
trust = "trusted"
enabled = false
""",
        encoding="utf-8",
    )

    assert load_sources(sources_file) == [
        Source("manual", Path("/mounted/manual"), "docs", "trusted", enabled=False)
    ]


def test_load_tokens_maps_valid_token_and_ignores_comments(tmp_path):
    tokens_file = tmp_path / "tokens"
    token = "x" * 40
    tokens_file.write_text(f"# generated\n\nhost={token}\n", encoding="utf-8")

    assert load_tokens(tokens_file) == {token: "host"}


def test_load_tokens_rejects_short_token(tmp_path):
    tokens_file = tmp_path / "tokens"
    tokens_file.write_text("host=short-token\n", encoding="utf-8")

    with pytest.raises(ValueError, match="curto demais"):
        load_tokens(tokens_file)


def test_all_mcp_scopes_define_permissions_and_rate_limit():
    for scope in scopes_policy().values():
        for key in ("read", "write", "tools", "rate_per_minute"):
            assert key in scope
