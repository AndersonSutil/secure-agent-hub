# hub-rag: indexador + servidor MCP. Roda sem root, com rootfs somente leitura (compose).
FROM docker.io/library/python:3.12-slim-trixie@sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177

ARG WITH_GUARD=1
ARG TORCH_VERSION=2.15.0+cpu
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/models

WORKDIR /opt/hub/rag
COPY requirements.lock pyproject.toml ./
COPY hub_rag ./hub_rag

# Dependências com versões exatas (requirements.lock); o pacote local entra sem deps.
# torch CPU só com o classificador (GPU não compensa a imagem de vários GB).
# hadolint ignore=DL3013
RUN if [ "$WITH_GUARD" = "1" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}"; \
    fi \
 && pip install -r requirements.lock \
 && pip install --no-deps . \
 && useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin hub

USER 10001
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3)"]
CMD ["hub-rag-server"]
