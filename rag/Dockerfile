# hub-rag: indexador + servidor MCP. Roda sem root, com rootfs somente leitura (compose).
FROM docker.io/library/python:3.12-slim-trixie@sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177

ARG WITH_GUARD=1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/models

WORKDIR /opt/hub/rag
COPY pyproject.toml ./
COPY hub_rag ./hub_rag

# torch CPU (o classificador é pequeno; GPU não compensa a imagem de vários GB).
RUN if [ "$WITH_GUARD" = "1" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.4,<3" && \
      pip install ".[guard]"; \
    else pip install .; fi \
 && useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin hub

USER 10001
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3).status==200 else 1)"
CMD ["hub-rag-server"]
