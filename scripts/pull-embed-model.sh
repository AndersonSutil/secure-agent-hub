#!/usr/bin/env bash
# Baixa o modelo de embedding para $HUB_DATA_DIR/ollama-embed.
# O ollama-embed do compose fica numa rede SEM internet; por isso o download roda
# num container temporário com rede, que é removido ao final.
source "$(dirname "$0")/lib.sh"
load_env
MODEL="${HUB_EMBED_MODEL:-qwen3-embedding:0.6b}"
IMAGE="$(sed -n 's/^ *image: \(docker.io\/ollama\/ollama[^ ]*\)/\1/p' "$HUB_ROOT/compose.yaml" | head -1)"
[ -n "$IMAGE" ] || die "imagem do ollama não encontrada no compose.yaml"
mkdir -p "$HUB_DATA_DIR/ollama-embed"
info "baixando $MODEL com $IMAGE"
hpodman run --rm --name hub-ollama-pull -v "$HUB_DATA_DIR/ollama-embed:/root/.ollama:Z" \
  --entrypoint /bin/sh "$IMAGE" -c "ollama serve >/dev/null 2>&1 & sleep 3; ollama pull '$MODEL'"
info "modelo pronto"
