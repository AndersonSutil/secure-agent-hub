"""Divisão de texto em trechos. Markdown por cabeçalho, código por blocos, resto por janela."""
from __future__ import annotations

import re
from dataclasses import dataclass

CODE_EXT = {".lua", ".luau", ".py", ".ts", ".tsx", ".js"}
MD_EXT = {".md", ".mdx"}

_MD_HEADING = re.compile(r"^(#{1,6})\s+\S", re.MULTILINE)
# Início de função/bloco de topo em Luau/Lua/Python/TS/JS.
_CODE_BOUNDARY = re.compile(
    r"^(?:local\s+function|function|export\s+type|type|def|class|async\s+def|"
    r"export\s+(?:default\s+)?(?:async\s+)?function|(?:async\s+)?function|"
    r"export\s+class|const\s+\w+\s*=\s*(?:async\s*)?\()",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int
    start_line: int


def _window(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    out, start = [], 0
    step = max(1, max_chars - overlap)
    while start < len(text):
        end = min(len(text), start + max_chars)
        # Corta em quebra de linha próxima para não partir no meio de uma linha.
        if end < len(text):
            nl = text.rfind("\n", start + step // 2, end)
            if nl > start:
                end = nl
        out.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return out


def _split_at(text: str, pattern: re.Pattern) -> list[str]:
    starts = sorted({0, *(m.start() for m in pattern.finditer(text))})
    return [text[a:b] for a, b in zip(starts, [*starts[1:], len(text)], strict=True) if text[a:b].strip()]


def _merge_small(parts: list[str], max_chars: int) -> list[str]:
    merged: list[str] = []
    for part in parts:
        if merged and len(merged[-1]) + len(part) <= max_chars:
            merged[-1] += part
        else:
            merged.append(part)
    return merged


def chunk_text(text: str, suffix: str, max_chars: int = 1200, overlap: int = 150) -> list[Chunk]:
    """Divide `text` conforme o tipo do arquivo (`suffix`, ex. '.md')."""
    if not text.strip():
        return []
    suffix = suffix.lower()
    if suffix in MD_EXT:
        sections = _split_at(text, _MD_HEADING)
    elif suffix in CODE_EXT:
        sections = _split_at(text, _CODE_BOUNDARY)
    else:
        sections = re.split(r"(?<=\n\n)", text)
    sections = _merge_small(sections, max_chars)

    chunks: list[Chunk] = []
    cursor = 0
    for section in sections:
        for piece in _window(section, max_chars, overlap):
            if not piece.strip():
                continue
            pos = text.find(piece, cursor)
            if pos < 0:
                pos = cursor
            line = text.count("\n", 0, pos) + 1
            chunks.append(Chunk(text=piece, index=len(chunks), start_line=line))
            cursor = pos + 1
    return chunks
