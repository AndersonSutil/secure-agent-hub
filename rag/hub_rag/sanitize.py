"""Saneamento de conteúdo não confiável e detecção de segredos (funções puras)."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from urllib.parse import urlparse

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_MD_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_HTML_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def _cp(value: str) -> int:
    return int(value.removeprefix("U+"), 16)


@lru_cache(maxsize=8)
def _strip_table(ranges: tuple[tuple[str, str], ...]) -> dict[int, None]:
    table: dict[int, None] = {}
    for start, end in ranges:
        for cp in range(_cp(start), _cp(end) + 1):
            table[cp] = None
    return table


def strip_invisible(text: str, ranges: list[list[str]]) -> tuple[str, int]:
    """Remove caracteres invisíveis/bidi/tag. Retorna (texto, quantos removidos)."""
    table = _strip_table(tuple(tuple(r) for r in ranges))
    cleaned = text.translate(table)
    return cleaned, len(text) - len(cleaned)


def _is_external(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https", "ftp", "data", "javascript") or url.startswith("//")


def defang_markdown(text: str, *, strip_images: bool, defang_links: bool) -> str:
    if strip_images:
        def _img(m: re.Match) -> str:
            alt, url = m.group(1), m.group(2)
            return f"[imagem removida: {alt}]" if _is_external(url) else m.group(0)
        text = _MD_IMAGE.sub(_img, text)
        text = _HTML_IMG.sub("[imagem HTML removida]", text)
    if defang_links:
        def _link(m: re.Match) -> str:
            label, url = m.group(1), m.group(2)
            if not _is_external(url):
                return m.group(0)
            host = urlparse(url if "://" in url else "https:" + url).hostname or "?"
            return f"{label} [link externo: {host}]"
        text = _MD_LINK.sub(_link, text)
    return text


def sanitize_untrusted(text: str, policy: dict) -> tuple[str, dict]:
    """Aplica as regras de policy/ingest.toml [sanitize]. Retorna (texto, relatório)."""
    report: dict = {}
    text = unicodedata.normalize("NFKC", text)
    text, removed = strip_invisible(text, policy["strip_ranges"])
    report["invisible_removed"] = removed
    if policy.get("strip_html_comments", True):
        text, n = _HTML_COMMENT.subn("", text)
        report["html_comments_removed"] = n
    text = defang_markdown(
        text,
        strip_images=policy.get("strip_external_markdown_images", True),
        defang_links=policy.get("defang_external_links", True),
    )
    return text, report


@lru_cache(maxsize=8)
def _compiled(patterns: tuple[str, ...]) -> list[re.Pattern]:
    return [re.compile(p) for p in patterns]


def find_secret(text: str, patterns: list[str]) -> str | None:
    """Retorna o padrão que casou (nunca o segredo) ou None."""
    for rx in _compiled(tuple(patterns)):
        if rx.search(text):
            return rx.pattern
    return None


def escape_envelope(text: str) -> str:
    """Impede que o conteúdo feche o envelope <retrieved> e injete fora dele."""
    return re.sub(r"</?\s*retrieved", lambda m: m.group(0).replace("<", "&lt;"), text, flags=re.IGNORECASE)
