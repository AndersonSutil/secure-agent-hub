#!/usr/bin/env bash
# Botão de emergência: derruba o hub e invalida todos os tokens MCP.
#   scripts/hub-kill.sh            # para tudo e rotaciona tokens
#   scripts/hub-kill.sh --restart  # idem e sobe de novo com os tokens novos
source "$(dirname "$0")/lib.sh"
load_env
info "parando containers do hub"
hub_compose down --timeout 5 || true
info "rotacionando tokens"
"$HUB_ROOT/scripts/secrets-init.sh" --rotate
"$HUB_ROOT/scripts/secrets-load.sh"
if [ "${1:-}" = "--restart" ]; then
  hub_compose up -d
fi
info "feito. Tokens antigos invalidados. Atualize as CLIs com scripts/register-mcp-host.sh"
info "e faça commit/push de overlay/secrets/hub.sops.yaml no repositório privado."
