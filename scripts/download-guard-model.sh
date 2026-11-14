#!/usr/bin/env bash
# Baixa o classificador de prompt injection para $HUB_DATA_DIR/models (cache Hugging Face).
#
# Llama Prompt Guard 2 é "gated": antes, aceite a licença em
#   https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
# com a sua conta e crie um token de LEITURA. O token é pedido aqui, passado só para
# o container temporário e não é salvo em lugar nenhum. Revogue-o depois, se quiser.
#
#   scripts/download-guard-model.sh            # Prompt Guard 2 (multilíngue)
#   scripts/download-guard-model.sh --fallback # protectai deberta (só inglês, sem licença)
source "$(dirname "$0")/lib.sh"
load_env

MODEL="meta-llama/Llama-Prompt-Guard-2-86M"
TOKEN_ENV=()
if [ "${1:-}" = "--fallback" ]; then
  MODEL="protectai/deberta-v3-base-prompt-injection-v2"
else
  read -r -s -p "Token de leitura do Hugging Face: " HF_TOKEN; echo
  [ -n "$HF_TOKEN" ] || die "token vazio"
  TOKEN_ENV=(-e "HF_TOKEN=$HF_TOKEN")
fi

mkdir -p "$HUB_DATA_DIR/models"
info "baixando $MODEL"
hpodman unshare chown -R 10001:10001 "$HUB_DATA_DIR/models"
hpodman run --rm --user 10001:10001 -e HF_HUB_OFFLINE=0 -e HF_HOME=/models \
  "${TOKEN_ENV[@]}" -v "$HUB_DATA_DIR/models:/models:Z" localhost/hub-rag:"${HUB_RAG_TAG:-dev}" \
  python -c "from huggingface_hub import snapshot_download; print(snapshot_download('$MODEL', allow_patterns=['*.json', '*.safetensors', '*.model', '*.txt']))"
unset HF_TOKEN
info "ok. Reinicie o hub-rag: scripts/hub-compose.sh restart hub-rag"
