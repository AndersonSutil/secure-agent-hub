#!/usr/bin/env bash
# Fase 0: teste descartável do OpenBot isolado. NÃO é para uso real (docs/adr/0005).
#
#   spikes/openbot/run.sh up      # cria redes, sobe squid + openbot
#   spikes/openbot/run.sh net     # testes automáticos de rede (DNS, proxy, LAN)
#   spikes/openbot/run.sh login   # login da conta OpenBot (interativo, você)
#   spikes/openbot/run.sh shell   # shell no container (para codex login etc.)
#   spikes/openbot/run.sh logs    # o que o proxy permitiu/negou
#   spikes/openbot/run.sh down    # para e remove containers/redes (dados ficam)
#   spikes/openbot/run.sh purge   # down + apaga os dados do teste
#
# Por que podman run e não compose: o docker-compose envia o perfil seccomp inline e a
# API compat do podman só aceita caminho de arquivo ("file name too long").
#
# Isolamento:
# - openbot só na rede internal (sem rota nem DNS externo); saída só pelo Squid com a
#   allowlist "executor" gerada de policy/egress.toml.
# - seccomp oficial do projeto (v0.70.0): libera user namespaces/ptrace para o Electron.
# - execpolicy do Codex e AGENTS.md montados read-only em ~/.codex.
source "$(dirname "$0")/../../scripts/lib.sh"
load_env

OPENBOT_IMAGE="ghcr.io/nightly-labs/openbot:0.70.0@sha256:1a1687ca5d16a003def143cc8059467abd3d9fbb4cc57768a03b33f6f3f4a936"
SQUID_IMAGE="docker.io/ubuntu/squid:6.10-24.10_beta@sha256:c9f5212b147a766529c7b026e2bebed37b998d33d0066b658596af5eba7cc65c"
SPIKE_DATA="$HUB_DATA_DIR/spike-openbot"
DIR="$HUB_ROOT/spikes/openbot"
NET_INT=openbot-spike-internal
NET_EGR=openbot-spike-egress
OB=openbot-spike
SQ=openbot-spike-squid
PROXY=http://$SQ:3128

case "${1:-}" in
  up)
    mkdir -p "$SPIKE_DATA"
    hpodman unshare sh -c "mkdir -p '$SPIKE_DATA/.codex/rules' && chown -R 1000:1000 '$SPIKE_DATA'"
    python3 "$HUB_ROOT/scripts/render-policy.py" >/dev/null
    hpodman network exists "$NET_INT" || hpodman network create --internal "$NET_INT" >/dev/null
    hpodman network exists "$NET_EGR" || hpodman network create "$NET_EGR" >/dev/null
    hpodman container exists "$SQ" || hpodman run -d --name "$SQ" --network "$NET_INT" \
      --security-opt no-new-privileges:true \
      -v "$HUB_ROOT/proxy/squid.conf:/etc/squid/squid.conf:ro,z" "$SQUID_IMAGE" >/dev/null
    # Squid também na rede com saída (só ele).
    hpodman network connect "$NET_EGR" "$SQ" 2>/dev/null || true
    hpodman container exists "$OB" || hpodman run -d --name "$OB" --network "$NET_INT" \
      --security-opt "seccomp=$DIR/seccomp.json" --security-opt no-new-privileges:true \
      --shm-size 1g --stop-timeout 60 --memory 6g --pids-limit 4096 \
      -e HTTP_PROXY=$PROXY -e HTTPS_PROXY=$PROXY -e http_proxy=$PROXY -e https_proxy=$PROXY \
      -e NO_PROXY=localhost,127.0.0.1 -e no_proxy=localhost,127.0.0.1 -e NODE_USE_ENV_PROXY=1 \
      -v "$SPIKE_DATA:/data:Z" \
      -v "$HUB_ROOT/harness/codex/rules/hub.rules:/data/.codex/rules/hub.rules:ro,z" \
      -v "$HUB_ROOT/harness/AGENTS.md:/data/.codex/AGENTS.md:ro,z" \
      "$OPENBOT_IMAGE" >/dev/null
    hpodman ps --filter "name=openbot-spike" --format '{{.Names}} {{.Status}}'
    ;;
  net)
    echo "== DNS externo (esperado: bloqueado)"
    hpodman exec "$OB" sh -c 'getent hosts example.com >/dev/null && echo "RESOLVEU (ruim)" || echo "bloqueado (ok)"'
    echo "== TCP direto sem proxy (esperado: bloqueado)"
    hpodman exec "$OB" sh -c 'timeout 5 bash -c ":> /dev/tcp/1.1.1.1/443" 2>/dev/null && echo "SAIU (ruim)" || echo "bloqueado (ok)"'
    for url in https://api.openai.com/v1/models https://chatgpt.com https://openbot.run \
               https://example.com https://pastebin.com http://192.168.0.1 http://10.0.0.1; do
      code="$(hpodman exec "$OB" sh -c "curl -s -o /dev/null -m 10 -w '%{http_code}' -x $PROXY '$url' 2>/dev/null; true")"
      echo "== via proxy $url -> ${code:-erro}"
    done
    ;;
  login) hpodman exec -it "$OB" openbot login ;;
  shell) hpodman exec -it "$OB" bash ;;
  logs) hpodman logs --tail "${2:-80}" "$SQ" 2>&1 | grep -v -E '^\s*$' ;;
  down)
    hpodman stop -t 60 "$OB" "$SQ" 2>/dev/null || true
    hpodman container rm "$OB" "$SQ" 2>/dev/null || true
    hpodman network remove "$NET_INT" "$NET_EGR" 2>/dev/null || true
    ;;
  purge)
    "$0" down
    hpodman unshare rm -rf "$SPIKE_DATA"
    ;;
  *) sed -n '4,11p' "$0"; exit 1 ;;
esac
