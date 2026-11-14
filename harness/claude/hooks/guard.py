#!/usr/bin/env python3
"""Hook PreToolUse do Claude Code: aplica harness/claude/guard-rules.json.

Lê o evento JSON no stdin. Para negar, sai com código 2 e explica no stderr
(o Claude Code mostra a mensagem ao modelo e não executa a ferramenta).
Toda negação vai para $HUB_ALERTS_FILE (JSONL), que o hub-notify lê.

Fail-closed: se as regras não puderem ser carregadas, nega tudo.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
import time
from pathlib import Path

RULES_FILE = Path(os.environ.get("HUB_GUARD_RULES", Path(__file__).resolve().parent.parent / "guard-rules.json"))
ALERTS_FILE = os.environ.get("HUB_ALERTS_FILE", "/data/alerts/alerts.jsonl")

PATH_KEYS = ("file_path", "path", "notebook_path")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def alert(rule_id: str, tool: str, detail: str) -> None:
    try:
        Path(ALERTS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": time.time(), "source": "claude-hook", "kind": "hook_denied",
                "rule": rule_id, "tool": tool, "detail": detail[:300],
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass


def deny(rule_id: str, why: str, tool: str, detail: str) -> None:
    alert(rule_id, tool, detail)
    print(f"Bloqueado pela política do hub ({rule_id}): {why}", file=sys.stderr)
    sys.exit(2)


def path_matches(path: str, globs: list[str]) -> bool:
    norm = os.path.normpath(os.path.expanduser(path))
    return any(fnmatch.fnmatch(norm, g) or fnmatch.fnmatch(norm, g.lstrip("*/")) for g in globs)


def main() -> None:
    try:
        rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
        event = json.load(sys.stdin)
    except Exception as exc:  # fail-closed
        print(f"Hook do hub sem regras válidas ({exc}); negando por segurança.", file=sys.stderr)
        sys.exit(2)

    tool = event.get("tool_name", "")
    tin = event.get("tool_input", {}) or {}

    if tool == "Bash":
        command = str(tin.get("command", ""))
        for rule in rules["bash_deny"]:
            if re.search(rule["regex"], command):
                deny(rule["id"], rule["why"], tool, command)
        # Caminhos sensíveis citados no comando.
        for token in re.split(r"[\s'\"=;|&<>()]+", command):
            if token and path_matches(token, rules["read_deny_globs"]):
                deny("read-deny", "Caminho sensível.", tool, command)
        return

    paths = [str(tin[k]) for k in PATH_KEYS if tin.get(k)]
    for p in paths:
        if path_matches(p, rules["read_deny_globs"]):
            deny("read-deny", "Caminho sensível.", tool, p)
        if tool in WRITE_TOOLS:
            real = os.path.realpath(p)
            if not any(real == r or real.startswith(r.rstrip("/") + "/") for r in rules["write_allow_roots"]):
                deny("write-outside-workspace", "Escrita só é permitida no workspace.", tool, p)


if __name__ == "__main__":
    main()
