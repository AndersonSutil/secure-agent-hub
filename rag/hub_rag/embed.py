"""Cliente mínimo do endpoint /api/embed do Ollama."""
from __future__ import annotations

import httpx

from .config import settings

_BATCH = 32


def embed(texts: list[str], *, query: bool = False) -> list[list[float]]:
    """Gera embeddings. Para consultas, o Qwen3-Embedding recomenda um prefixo de instrução."""
    if not texts:
        return []
    s = settings()
    if query:
        texts = [f"Instruct: Given a search query, retrieve relevant passages\nQuery: {t}" for t in texts]
    out: list[list[float]] = []
    with httpx.Client(timeout=120) as client:
        for i in range(0, len(texts), _BATCH):
            resp = client.post(f"{s.ollama_url}/api/embed", json={"model": s.embed_model, "input": texts[i:i + _BATCH]})
            resp.raise_for_status()
            out.extend(resp.json()["embeddings"])
    return out
