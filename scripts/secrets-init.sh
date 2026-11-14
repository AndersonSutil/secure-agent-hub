#!/usr/bin/env bash
# Cria (ou rotaciona) os segredos do hub em overlay/secrets/hub.sops.yaml, criptografados com age.
#   scripts/secrets-init.sh            # cria se não existir
#   scripts/secrets-init.sh --rotate   # gera tokens novos (invalida os antigos)
# Se não houver chave age, gera uma em $SOPS_AGE_KEY_FILE. GUARDE uma cópia dela no
# seu gerenciador de senhas: sem ela não há como decriptar em outro computador.
source "$(dirname "$0")/lib.sh"
load_env

ROTATE=0
[ "${1:-}" = "--rotate" ] && ROTATE=1
SECRETS="$HUB_OVERLAY_DIR/secrets/hub.sops.yaml"

if [ ! -f "$SOPS_AGE_KEY_FILE" ]; then
  info "gerando chave age em $SOPS_AGE_KEY_FILE"
  mkdir -p "$(dirname "$SOPS_AGE_KEY_FILE")"
  chmod 700 "$(dirname "$SOPS_AGE_KEY_FILE")"
  (umask 077; hub_tools -- age-keygen 2>/dev/null > "$SOPS_AGE_KEY_FILE")
  info "IMPORTANTE: copie o conteúdo de $SOPS_AGE_KEY_FILE para o KeePassXC/Bitwarden agora."
fi

KEYDIR="$(dirname "$SOPS_AGE_KEY_FILE")"
KEYNAME="$(basename "$SOPS_AGE_KEY_FILE")"
RECIPIENT="$(hub_tools -v "$KEYDIR:/age:ro" -- age-keygen -y "/age/$KEYNAME")"
[ -n "$RECIPIENT" ] || die "não foi possível ler a chave pública age"

mkdir -p "$HUB_OVERLAY_DIR/secrets"
if [ ! -f "$HUB_OVERLAY_DIR/.sops.yaml" ]; then
  cat > "$HUB_OVERLAY_DIR/.sops.yaml" <<EOF
creation_rules:
  - path_regex: secrets/.*\\.sops\\.yaml\$
    age: $RECIPIENT
EOF
  info "criado $HUB_OVERLAY_DIR/.sops.yaml"
fi

if [ -f "$SECRETS" ] && [ "$ROTATE" = 0 ]; then
  info "$SECRETS já existe (use --rotate para gerar tokens novos)"
  exit 0
fi

# Gera os tokens dentro do container e criptografa sem tocar o disco em claro.
REL_OVERLAY="$(realpath --relative-to="$HUB_ROOT" "$HUB_OVERLAY_DIR")"
case "$REL_OVERLAY" in ../*) die "o overlay precisa ficar dentro do repositório (padrão: ./overlay)";; esac
# shellcheck disable=SC2016  # expansão acontece dentro do container, de propósito
hub_tools -e SOPS_AGE_RECIPIENTS="$RECIPIENT" -- sh -c '
  set -eu
  gen() { python3 -c "import secrets; print(secrets.token_urlsafe(48))"; }
  printf "mcp_token_host: %s\nmcp_token_admin: %s\nmcp_token_executor: %s\nmcp_token_reader: %s\n" \
    "$(gen)" "$(gen)" "$(gen)" "$(gen)" \
  | sops --encrypt --age "$SOPS_AGE_RECIPIENTS" --input-type yaml --output-type yaml /dev/stdin
' > "$SECRETS.tmp"
mv "$SECRETS.tmp" "$SECRETS"
info "segredos gravados (criptografados) em $SECRETS"
if [ "$ROTATE" = 1 ]; then
  info "rotação feita: rode scripts/secrets-load.sh e scripts/register-mcp-host.sh"
fi
