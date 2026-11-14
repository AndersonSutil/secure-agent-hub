"""Alertas (JSONL) lidos no host pelo hub-notify, e log de chamadas MCP."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .config import settings

log = logging.getLogger("hub_rag")


def _append(path: Path, record: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:  # alerta nunca derruba o serviço
        log.error("falha ao gravar %s: %s", path, exc)


def alert(kind: str, severity: str = "normal", **fields) -> None:
    """kind: quarantine | secret_dropped | auth_failed | rate_limited | guard_unavailable."""
    record = {"ts": time.time(), "source": "hub-rag", "kind": kind, "severity": severity, **fields}
    log.warning("ALERTA %s %s", kind, fields)
    _append(settings().alerts_file, record)


def log_call(scope: str, tool: str, **fields) -> None:
    _append(settings().calls_log, {"ts": time.time(), "scope": scope, "tool": tool, **fields})
