"""Acesso ao Qdrant: coleções, upsert incremental por arquivo, busca."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from functools import lru_cache

from qdrant_client import QdrantClient, models

from .config import settings

_KEYWORD_FIELDS = ("source", "path", "trust", "file_sha", "source_agent")


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    return QdrantClient(url=settings().qdrant_url, timeout=60)


def ensure_collection(name: str, dim: int) -> None:
    c = client()
    if c.collection_exists(name):
        return
    c.create_collection(name, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
    for field in _KEYWORD_FIELDS:
        c.create_payload_index(name, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD)
    c.create_payload_index(name, field_name="expires_at", field_schema=models.PayloadSchemaType.FLOAT)


def point_id(*parts: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, ":".join(str(p) for p in parts)))


def upsert(collection: str, vectors: list[list[float]], payloads: list[dict], ids: list[str]) -> None:
    if not vectors:
        return
    ensure_collection(collection, len(vectors[0]))
    client().upsert(collection, points=[
        models.PointStruct(id=i, vector=v, payload=p) for i, v, p in zip(ids, vectors, payloads, strict=True)
    ])


def _eq(field: str, value: str) -> models.FieldCondition:
    return models.FieldCondition(key=field, match=models.MatchValue(value=value))


def indexed_files(collection: str, source: str) -> dict[str, str]:
    """path -> file_sha já indexados para uma fonte."""
    c = client()
    if not c.collection_exists(collection):
        return {}
    state: dict[str, str] = {}
    offset = None
    while True:
        points, offset = c.scroll(
            collection, scroll_filter=models.Filter(must=[_eq("source", source)]),
            with_payload=["path", "file_sha"], with_vectors=False, limit=1000, offset=offset,
        )
        for p in points:
            state[p.payload["path"]] = p.payload["file_sha"]
        if offset is None:
            return state


def delete_file(collection: str, source: str, path: str) -> None:
    c = client()
    if c.collection_exists(collection):
        c.delete(collection, points_selector=models.FilterSelector(
            filter=models.Filter(must=[_eq("source", source), _eq("path", path)])))


def delete_expired(collection: str) -> None:
    c = client()
    if c.collection_exists(collection):
        c.delete(collection, points_selector=models.FilterSelector(filter=models.Filter(must=[
            models.FieldCondition(key="expires_at", range=models.Range(lt=time.time()))])))


@dataclass(frozen=True)
class Hit:
    collection: str
    score: float
    payload: dict


def search(collections: list[str], vector: list[float], k: int) -> list[Hit]:
    c = client()
    not_expired = models.Filter(should=[
        models.IsEmptyCondition(is_empty=models.PayloadField(key="expires_at")),
        models.FieldCondition(key="expires_at", range=models.Range(gt=time.time())),
    ])
    hits: list[Hit] = []
    for name in collections:
        if not c.collection_exists(name):
            continue
        res = c.query_points(name, query=vector, limit=k, query_filter=not_expired, with_payload=True)
        hits += [Hit(name, p.score, p.payload or {}) for p in res.points]
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:k]


def counts() -> dict[str, int]:
    c = client()
    return {col.name: c.count(col.name, exact=True).count for col in c.get_collections().collections}
