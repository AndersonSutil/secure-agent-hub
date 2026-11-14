#!/usr/bin/env bash
# Decripta overlay/secrets/hub.sops.yaml e grava os tokens em $XDG_RUNTIME_DIR/agentes-hub
# (tmpfs: some no reboot, nunca vai para o disco). Rode depois de cada boot, antes do compose.
source "$(dirname "$0")/lib.sh"
load_env

SECRETS="$HUB_OVERLAY_DIR/secrets/hub.sops.yaml"
[ -f "$SECRETS" ] || die "faltando $SECRETS (rode scripts/secrets-init.sh)"
[ -f "$SOPS_AGE_KEY_FILE" ] || die "faltando a chave age em $SOPS_AGE_KEY_FILE (restaure do gerenciador de senhas)"

mkdir -p "$HUB_RUNTIME_DIR"
chmod 700 "$HUB_RUNTIME_DIR"
REL="$(realpath --relative-to="$HUB_ROOT" "$SECRETS")"
KEYDIR="$(dirname "$SOPS_AGE_KEY_FILE")"

JSON="$(hub_tools -v "$KEYDIR:/age:ro" -e "SOPS_AGE_KEY_FILE=/age/$(basename "$SOPS_AGE_KEY_FILE")" \
  -- sops --decrypt --output-type json "/work/$REL")" || die "falha ao decriptar (chave age errada?)"

umask 077
printf '%s' "$JSON" | python3 -c '
import json, sys
data = json.load(sys.stdin)
prefix = "mcp_token_"
for key, value in sorted(data.items()):
    if key.startswith(prefix):
        print(key[len(prefix):] + "=" + value)
' > "$HUB_RUNTIME_DIR/hub_mcp_tokens"
# Token só do host, para o register-mcp-host.sh.
grep '^host=' "$HUB_RUNTIME_DIR/hub_mcp_tokens" | cut -d= -f2- > "$HUB_RUNTIME_DIR/host.token"
grep '^admin=' "$HUB_RUNTIME_DIR/hub_mcp_tokens" | cut -d= -f2- > "$HUB_RUNTIME_DIR/admin.token"
# O hub-rag roda com um subuid: o arquivo precisa ser legível por "outros". Continua
# protegido porque o diretório pai ($XDG_RUNTIME_DIR, 0700) só é acessível por você.
chmod 0644 "$HUB_RUNTIME_DIR/hub_mcp_tokens"
info "tokens carregados em $HUB_RUNTIME_DIR (tmpfs)"
