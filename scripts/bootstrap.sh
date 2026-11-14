#!/usr/bin/env bash
# Instala/atualiza o hub nesta máquina. Idempotente: pode rodar quantas vezes quiser.
# Pré-requisitos: podman >= 5 com "podman compose", overlay/.env preenchido.
source "$(dirname "$0")/lib.sh"
load_env

info "verificando pré-requisitos"
ver="$(hpodman version --format '{{.Client.Version}}')"
[ "${ver%%.*}" -ge 5 ] || die "podman >= 5 necessário (encontrado $ver)"
hpodman compose version >/dev/null 2>&1 || die "'podman compose' indisponível (instale docker-compose ou podman-compose)"
if [ "${EMBED_GPU:-cpu}" != "cpu" ]; then
  host_exec sh -c 'ls /etc/cdi/*.yaml /var/run/cdi/*.yaml 2>/dev/null | grep -q .' \
    || die "EMBED_GPU=$EMBED_GPU mas não há especificação CDI (rode: sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml)"
fi
avail_gb="$(df -BG --output=avail "$(dirname "$HUB_DATA_DIR")" 2>/dev/null | tail -1 | tr -dc 0-9)"
[ "${avail_gb:-0}" -ge 10 ] || info "AVISO: menos de 10 GB livres perto de $HUB_DATA_DIR"

info "criando diretórios de dados em $HUB_DATA_DIR"
mkdir -p "$HUB_DATA_DIR"/{qdrant,qdrant-snapshots,ollama-embed,alerts,logs,models}
# hub-rag roda como uid 10001 dentro do user namespace rootless.
hpodman unshare chown -R 10001:10001 "$HUB_DATA_DIR/alerts" "$HUB_DATA_DIR/logs" "$HUB_DATA_DIR/models"
chmod 0755 "$HUB_DATA_DIR/alerts" "$HUB_DATA_DIR/logs" 2>/dev/null || true
[ -f "$HUB_OVERLAY_DIR/sources.toml" ] || cp "$HUB_ROOT/sources.example.toml" "$HUB_OVERLAY_DIR/sources.toml"

info "build das imagens locais"
hpodman build -q -t localhost/hub-tools:dev "$HUB_ROOT/tools" >/dev/null
hub_compose build hub-rag

info "renderizando políticas e montagens"
python3 "$HUB_ROOT/scripts/render-policy.py"
python3 "$HUB_ROOT/scripts/render-sources.py" --overlay "$HUB_OVERLAY_DIR"

info "segredos"
"$HUB_ROOT/scripts/secrets-init.sh"
"$HUB_ROOT/scripts/secrets-load.sh"

if [ ! -d "$HUB_DATA_DIR/ollama-embed/models/manifests" ]; then
  "$HUB_ROOT/scripts/pull-embed-model.sh"
fi

info "instalando serviços systemd --user (notificações e reindexação)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
for unit in "$HUB_ROOT"/systemd/*.{service,timer}; do
  sed -e "s#@HUB_ROOT@#$HUB_ROOT#g" -e "s#@HUB_DATA_DIR@#$HUB_DATA_DIR#g" "$unit" > "$UNIT_DIR/$(basename "$unit")"
done
host_exec systemctl --user daemon-reload
host_exec systemctl --user enable --now hub-notify.service hub-index.timer
host_exec systemctl --user enable hub-up.service

info "subindo o hub"
hub_compose up -d --wait
info "pronto. Próximos passos: scripts/index.sh e scripts/register-mcp-host.sh"
[ -d "$HUB_DATA_DIR/models/hub" ] || [ -n "$(ls -A "$HUB_DATA_DIR/models" 2>/dev/null)" ] \
  || info "classificador ausente: rode scripts/download-guard-model.sh (sem ele, conteúdo untrusted vai para quarentena)"
