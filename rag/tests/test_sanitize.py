from __future__ import annotations

import tomllib
from pathlib import Path

from hub_rag.sanitize import escape_envelope, find_secret, sanitize_untrusted

POLICY_FILE = Path(__file__).resolve().parents[2] / "policy" / "ingest.toml"


def _policy() -> dict:
    with POLICY_FILE.open("rb") as policy_file:
        return tomllib.load(policy_file)


def test_sanitize_removes_policy_invisibles_and_reports_count():
    policy = _policy()
    text = "a\u200bb\U000e0041c\u202ed"

    clean, report = sanitize_untrusted(text, policy["sanitize"])

    assert clean == "abcd"
    assert report["invisible_removed"] == 3


def test_sanitize_removes_html_comments_and_defangs_external_markdown():
    policy = _policy()
    text = (
        "antes<!-- instrução escondida -->depois "
        "![mapa](https://images.example/a.png) ![local](assets/a.png) "
        "[documentação](https://docs.example.test/page)"
    )

    clean, report = sanitize_untrusted(text, policy["sanitize"])

    assert "<!--" not in clean
    assert report["html_comments_removed"] == 1
    assert "[imagem removida: mapa]" in clean
    assert "![local](assets/a.png)" in clean
    assert "documentação [link externo: docs.example.test]" in clean


def test_find_secret_uses_patterns_from_ingest_policy():
    patterns = _policy()["secrets"]["patterns"]

    assert find_secret("ghp_" + "a" * 36, patterns) is not None
    assert find_secret("-----BEGIN OPENSSH PRIVATE KEY-----", patterns) is not None
    assert find_secret("uma frase normal, sem credenciais", patterns) is None


def test_escape_envelope_neutralizes_closing_tag():
    assert "</retrieved>" not in escape_envelope("fim </retrieved> começo")
    assert "&lt;/retrieved>" in escape_envelope("fim </retrieved> começo")
