"""Configuração: variáveis de ambiente + policy/*.toml + overlay/sources.toml."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

TRUST_LEVELS = ("trusted", "untrusted", "agent")
COLLECTIONS = ("docs", "docs_untrusted", "memory", "quarantine", "code")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    qdrant_url: str = field(default_factory=lambda: _env("HUB_QDRANT_URL", "http://qdrant:6333"))
    ollama_url: str = field(default_factory=lambda: _env("HUB_OLLAMA_URL", "http://ollama-embed:11434"))
    embed_model: str = field(default_factory=lambda: _env("HUB_EMBED_MODEL", "qwen3-embedding:0.6b"))
    policy_dir: Path = field(default_factory=lambda: Path(_env("HUB_POLICY_DIR", "/opt/hub/policy")))
    sources_file: Path = field(default_factory=lambda: Path(_env("HUB_SOURCES_FILE", "/opt/hub/overlay/sources.toml")))
    tokens_file: Path = field(default_factory=lambda: Path(_env("HUB_TOKENS_FILE", "/run/secrets/hub_mcp_tokens")))
    alerts_file: Path = field(default_factory=lambda: Path(_env("HUB_ALERTS_FILE", "/data/alerts/alerts.jsonl")))
    calls_log: Path = field(default_factory=lambda: Path(_env("HUB_CALLS_LOG", "/data/logs/mcp-calls.jsonl")))
    guard_cache: Path = field(default_factory=lambda: Path(_env("HUB_GUARD_CACHE", "/models")))
    # 0.0.0.0 só dentro do container; o compose publica apenas em 127.0.0.1.
    bind_host: str = field(default_factory=lambda: _env("HUB_BIND_HOST", "0.0.0.0"))  # noqa: S104
    bind_port: int = field(default_factory=lambda: int(_env("HUB_BIND_PORT", "8765")))


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()


def _load_toml(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


@lru_cache(maxsize=1)
def ingest_policy() -> dict:
    return _load_toml(settings().policy_dir / "ingest.toml")


@lru_cache(maxsize=1)
def scopes_policy() -> dict:
    return _load_toml(settings().policy_dir / "mcp-scopes.toml")["scopes"]


@dataclass(frozen=True)
class Source:
    name: str
    path: Path
    collection: str
    trust: str
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.collection not in COLLECTIONS or self.collection in ("memory", "quarantine"):
            raise ValueError(f"fonte {self.name}: coleção inválida {self.collection!r}")
        if self.trust not in ("trusted", "untrusted"):
            raise ValueError(f"fonte {self.name}: trust deve ser trusted|untrusted")
        if self.collection == "docs" and self.trust != "trusted":
            raise ValueError(f"fonte {self.name}: 'docs' só aceita trust=trusted; use docs_untrusted")


def load_sources(path: Path | None = None) -> list[Source]:
    """Lê overlay/sources.toml. Cada fonte é montada em /sources/<name> pelo compose."""
    path = path or settings().sources_file
    if not path.is_file():
        return []
    data = _load_toml(path)
    out = []
    for raw in data.get("source", []):
        out.append(Source(
            name=raw["name"],
            path=Path(raw.get("container_path", f"/sources/{raw['name']}")),
            collection=raw["collection"],
            trust=raw["trust"],
            enabled=raw.get("enabled", True),
        ))
    return out


def load_tokens(path: Path | None = None) -> dict[str, str]:
    """Arquivo `escopo=token` por linha (gerado pelo secrets-load). Retorna token -> escopo."""
    path = path or settings().tokens_file
    tokens: dict[str, str] = {}
    if not path.is_file():
        return tokens
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        scope, token = line.split("=", 1)
        scope, token = scope.strip(), token.strip()
        if len(token) < 32:
            raise ValueError(f"token do escopo {scope} curto demais (mínimo 32 caracteres)")
        tokens[token] = scope
    return tokens
