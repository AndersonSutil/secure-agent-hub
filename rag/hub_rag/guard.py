"""Classificador de prompt injection (Prompt Guard 2 ou fallback), local e offline.

O modelo é baixado uma vez por scripts/download-guard-model.sh para HUB_GUARD_CACHE.
Em runtime roda com HF_HUB_OFFLINE=1: o hub-rag não tem acesso à internet.
"""
from __future__ import annotations

import logging
import os
import threading

from .config import ingest_policy, settings

log = logging.getLogger("hub_rag.guard")

# Rótulos que indicam ataque nos modelos suportados.
_MALICIOUS = {"LABEL_1", "MALICIOUS", "INJECTION", "JAILBREAK"}
_WINDOW_CHARS = 1500  # ~512 tokens; textos maiores são avaliados por janelas (máximo).


class Guard:
    def __init__(self) -> None:
        self._pipe = None
        self._model_name: str | None = None
        self._lock = threading.Lock()
        self._failed = False

    def _load(self) -> None:
        if self._pipe is not None or self._failed:
            return
        with self._lock:
            if self._pipe is not None or self._failed:
                return
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("HF_HOME", str(settings().guard_cache))
            policy = ingest_policy()["guard"]
            try:
                from transformers import pipeline  # import pesado, só quando necessário
            except ImportError as exc:
                log.error("transformers indisponível: %s", exc)
                self._failed = True
                return
            for name in (policy["model"], policy["fallback_model"]):
                try:
                    self._pipe = pipeline("text-classification", model=name, top_k=None, device=-1)
                    self._model_name = name
                    log.info("guard carregado: %s", name)
                    return
                except Exception as exc:  # modelo ausente do cache, gated etc.
                    log.warning("guard %s indisponível: %s", name, exc)
            self._failed = True

    @property
    def model_name(self) -> str | None:
        self._load()
        return self._model_name

    def score(self, text: str) -> float | None:
        """Probabilidade (0..1) de o texto conter injeção. None se não houver modelo."""
        self._load()
        if self._pipe is None:
            return None
        windows = [text[i:i + _WINDOW_CHARS] for i in range(0, max(len(text), 1), _WINDOW_CHARS)]
        best = 0.0
        for result in self._pipe(windows, truncation=True, max_length=512):
            for item in result:
                if item["label"].upper() in _MALICIOUS:
                    best = max(best, float(item["score"]))
        return best


_guard = Guard()


def get_guard() -> Guard:
    return _guard


def verdict(text: str, trust: str) -> tuple[str, float | None]:
    """Retorna ("allow"|"quarantine", score). Só avalia os níveis de policy guard.apply_to_trust."""
    policy = ingest_policy()["guard"]
    if trust not in policy["apply_to_trust"]:
        return "allow", None
    score = get_guard().score(text)
    if score is None:
        return ("quarantine" if policy["on_unavailable"] == "quarantine" else "allow"), None
    return ("quarantine" if score >= policy["threshold"] else "allow"), score
