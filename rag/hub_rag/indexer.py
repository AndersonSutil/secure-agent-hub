"""Indexador incremental: fontes de overlay/sources.toml -> Qdrant.

Uso (dentro do container hub-rag):
    python -m hub_rag.indexer               # todas as fontes habilitadas
    python -m hub_rag.indexer --source NOME
    python -m hub_rag.indexer --dry-run     # mostra o que faria
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import logging
import sys
import time
from pathlib import Path

from . import store
from .alerts import alert
from .chunking import chunk_text
from .config import Source, ingest_policy, load_sources
from .embed import embed
from .guard import get_guard, verdict
from .sanitize import find_secret, sanitize_untrusted

log = logging.getLogger("hub_rag.indexer")


def ignored(rel: str, globs: list[str]) -> bool:
    candidate = "/" + rel
    return any(fnmatch.fnmatch(candidate, g) or fnmatch.fnmatch(rel, g) for g in globs)


def iter_files(source: Source, policy: dict):
    files_pol = policy["files"]
    exts = set(files_pol["text_extensions"])
    for path in sorted(source.path.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue  # symlinks podem apontar para fora da fonte montada
        rel = path.relative_to(source.path).as_posix()
        if path.suffix.lower() not in exts or ignored(rel, files_pol["ignore_globs"]):
            continue
        if path.stat().st_size > files_pol["max_bytes"]:
            continue
        yield path, rel


def read_document(path: Path) -> list[tuple[str, int | None]]:
    """Retorna [(texto, página|None)]."""
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return [(page.extract_text() or "", n + 1) for n, page in enumerate(reader.pages)]
    return [(path.read_text(encoding="utf-8", errors="replace"), None)]


def index_source(source: Source, *, dry_run: bool = False, force: bool = False) -> dict:
    policy = ingest_policy()
    stats = {"files_seen": 0, "files_indexed": 0, "chunks": 0, "quarantined": 0, "secrets_dropped": 0, "removed": 0}
    known = store.indexed_files(source.collection, source.name)
    known_q = store.indexed_files("quarantine", source.name)
    present: set[str] = set()

    for path, rel in iter_files(source, policy):
        stats["files_seen"] += 1
        present.add(rel)
        raw = path.read_bytes()
        file_sha = hashlib.sha256(raw).hexdigest()
        if not force and (known.get(rel) == file_sha or known_q.get(rel) == file_sha):
            continue
        if dry_run:
            stats["files_indexed"] += 1
            continue

        keep: list[tuple[str, dict]] = []
        quarantine: list[tuple[str, dict]] = []
        for text, page in read_document(path):
            for chunk in chunk_text(text, path.suffix, policy["chunk"]["max_chars"], policy["chunk"]["overlap"]):
                body = chunk.text
                if find_secret(body, policy["secrets"]["patterns"]):
                    stats["secrets_dropped"] += 1
                    alert("secret_dropped", fonte=source.name, path=rel, line=chunk.start_line)
                    continue
                payload = {
                    "source": source.name, "path": rel, "page": page, "start_line": chunk.start_line,
                    "chunk_index": chunk.index, "file_sha": file_sha, "trust": source.trust,
                    "ingested_by": "indexer", "ingested_at": time.time(),
                }
                if source.trust == "untrusted":
                    body, report = sanitize_untrusted(body, policy["sanitize"])
                    decision, score = verdict(body, source.trust)
                    payload |= {"sanitize": report, "guard_score": score, "guard_model": get_guard().model_name}
                    if decision == "quarantine":
                        payload["original_collection"] = source.collection
                        quarantine.append((body, payload))
                        continue
                keep.append((body, payload))

        store.delete_file(source.collection, source.name, rel)
        store.delete_file("quarantine", source.name, rel)
        for target, items in ((source.collection, keep), ("quarantine", quarantine)):
            if not items:
                continue
            vectors = embed([b for b, _ in items])
            payloads = [p | {"text": b} for b, p in items]
            ids = [store.point_id(target, source.name, rel, p["page"], p["chunk_index"], file_sha) for _, p in items]
            store.upsert(target, vectors, payloads, ids)
        if quarantine:
            stats["quarantined"] += len(quarantine)
            alert("quarantine", fonte=source.name, path=rel, chunks=len(quarantine))
        stats["files_indexed"] += 1
        stats["chunks"] += len(keep)

    for rel in (set(known) | set(known_q)) - present:
        stats["removed"] += 1
        if not dry_run:
            store.delete_file(source.collection, source.name, rel)
            store.delete_file("quarantine", source.name, rel)
    return stats


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="indexa só esta fonte")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="reprocessa mesmo sem mudança de hash (ex.: depois de mudar a política ou o classificador)")
    args = ap.parse_args(argv)

    sources = [s for s in load_sources() if s.enabled and (not args.source or s.name == args.source)]
    if not sources:
        print("Nenhuma fonte habilitada em sources.toml.", file=sys.stderr)
        return 1
    rc = 0
    for src in sources:
        if not src.path.is_dir():
            print(f"[{src.name}] caminho {src.path} não existe no container (mount ausente?)", file=sys.stderr)
            rc = 1
            continue
        stats = index_source(src, dry_run=args.dry_run, force=args.force)
        print(f"[{src.name}] -> {src.collection} ({src.trust}): {stats}")
    store.delete_expired("memory")
    if not args.dry_run:
        print("coleções:", store.counts())
    return rc


if __name__ == "__main__":
    sys.exit(main())
