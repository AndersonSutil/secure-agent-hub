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
    echo "Codex: hub-knowledge já existe em $CODEX_CFG (não alterado)"
  else
    echo "Codex: codex mcp add hub-knowledge --url $URL --bearer-token-env-var HUB_MCP_TOKEN"
    if confirm "Registrar no Codex?"; then
      cp "$CODEX_CFG" "$CODEX_CFG.bak.$(date +%s)"
      codex mcp add hub-knowledge --url "$URL" --bearer-token-env-var HUB_MCP_TOKEN
    fi
  fi
  # Opcional e desligado por padrão: sem aprovação automática, `codex exec` (não interativo)
  # não consegue chamar as ferramentas do hub. Trade-off: uma injeção poderia fazer o Codex
  # gravar memória sem perguntar (a escrita continua saneada, classificada e marcada trust=agent).
  if ! grep -q 'default_tools_approval_mode' "$CODEX_CFG" 2>/dev/null; then
    echo "Codex: aprovar automaticamente as ferramentas do hub-knowledge (necessário para 'codex exec')?"
    echo "  Alternativa sem mudar a config: codex exec -c 'mcp_servers.hub-knowledge.default_tools_approval_mode=\"approve\"' ..."
    read -r -p "Dispensar a aprovação só para o hub-knowledge? [s/N] " ans
    if [ "$ans" = "s" ] || [ "$ans" = "S" ]; then
      cp "$CODEX_CFG" "$CODEX_CFG.bak.$(date +%s)"
      python3 - "$CODEX_CFG" <<'PY'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1])
t = p.read_text()
m = re.search(r'(?ms)^\[mcp_servers\.hub-knowledge\]\n(.*?)(?=^\[|\Z)', t)
body = m.group(1).rstrip("\n") + '\ndefault_tools_approval_mode = "approve"\n\n'
p.write_text(t[:m.start(1)] + body + t[m.end(1):])
PY
    fi
  fi
  # O token não fica no config.toml: o Codex lê HUB_MCP_TOKEN do ambiente.
  # shellcheck disable=SC2016  # a expansão acontece quando o shell do usuário ler o ~/.bashrc
  LINE='export HUB_MCP_TOKEN="$(cat "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/agentes-hub/host.token" 2>/dev/null)"  # agentes-hub'
  if grep -qF '# agentes-hub' "$HOME/.bashrc" 2>/dev/null; then
    echo "\$HOME/.bashrc já exporta HUB_MCP_TOKEN"
  else
    echo "Codex precisa de HUB_MCP_TOKEN no ambiente. Linha para ~/.bashrc:"
    echo "  $LINE"
    if confirm "Acrescentar ao ~/.bashrc?"; then
      printf '\n%s\n' "$LINE" >> "$HOME/.bashrc"
    fi
  fi
fi

# --- Antigravity (agy): formato de config MCP varia por versão; só imprime o bloco.
if command -v agy >/dev/null 2>&1; then
  echo
  echo "Antigravity: adicione este servidor na configuração MCP do agy (veja 'agy --help'/docs):"
  printf '  {"mcpServers": {"hub-knowledge": {"serverUrl": "%s", "headers": {"Authorization": "Bearer <conteúdo de %s>"}}}}\n' "$URL" "$TOKEN_FILE"
fi
