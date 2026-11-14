#!/usr/bin/env bash
# Registra o MCP hub-knowledge nas CLIs do host (escopo "host": lê docs/memória, grava memória).
# Mostra o que vai mudar e pede confirmação para cada CLI.
#
# Limite conhecido: Claude Code e agy guardam o cabeçalho com o token em texto puro na
# config do usuário. O token só vale para o escopo "host" e é rotacionado por hub-kill.sh.
source "$(dirname "$0")/lib.sh"
load_env

TOKEN_FILE="$HUB_RUNTIME_DIR/host.token"
[ -s "$TOKEN_FILE" ] || die "rode scripts/secrets-load.sh antes"
TOKEN="$(cat "$TOKEN_FILE")"
URL="http://127.0.0.1:${HUB_MCP_PORT:-8765}/mcp"

confirm() { read -r -p "$1 [s/N] " ans; [ "$ans" = "s" ] || [ "$ans" = "S" ]; }

# --- Claude Code
if command -v claude >/dev/null 2>&1; then
  echo "Claude Code: claude mcp add --scope user --transport http hub-knowledge $URL --header 'Authorization: Bearer ***'"
  if confirm "Registrar no Claude Code?"; then
    claude mcp remove --scope user hub-knowledge >/dev/null 2>&1 || true
    claude mcp add --scope user --transport http hub-knowledge "$URL" --header "Authorization: Bearer $TOKEN"
  fi
fi

# --- Codex: token por variável de ambiente (não fica no config.toml)
CODEX_CFG="$HOME/.codex/config.toml"
if command -v codex >/dev/null 2>&1; then
  if grep -q '^\[mcp_servers.hub-knowledge\]' "$CODEX_CFG" 2>/dev/null; then
    echo "Codex: [mcp_servers.hub-knowledge] já existe em $CODEX_CFG (não alterado)"
  else
    echo "Codex: acrescentar em $CODEX_CFG:"
    printf '  [mcp_servers.hub-knowledge]\n  url = "%s"\n  bearer_token_env_var = "HUB_MCP_TOKEN"\n' "$URL"
    if confirm "Acrescentar no Codex?"; then
      cp "$CODEX_CFG" "$CODEX_CFG.bak.$(date +%s)"
      printf '\n[mcp_servers.hub-knowledge]\nurl = "%s"\nbearer_token_env_var = "HUB_MCP_TOKEN"\n' "$URL" >> "$CODEX_CFG"
    fi
  fi
  echo "Codex lê o token de HUB_MCP_TOKEN. Adicione ao seu shell (ex.: ~/.bashrc):"
  echo "  export HUB_MCP_TOKEN=\"\$(cat \"\${XDG_RUNTIME_DIR:-/run/user/\$(id -u)}/agentes-hub/host.token\" 2>/dev/null)\""
fi

# --- Antigravity (agy): formato de config MCP varia por versão; só imprime o bloco.
if command -v agy >/dev/null 2>&1; then
  echo
  echo "Antigravity: adicione este servidor na configuração MCP do agy (veja 'agy --help'/docs):"
  printf '  {"mcpServers": {"hub-knowledge": {"serverUrl": "%s", "headers": {"Authorization": "Bearer <conteúdo de %s>"}}}}\n' "$URL" "$TOKEN_FILE"
fi
