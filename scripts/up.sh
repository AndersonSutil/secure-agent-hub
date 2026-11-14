#!/usr/bin/env bash
# Sobe o hub depois de um boot: carrega os tokens (tmpfs) e inicia os containers.
source "$(dirname "$0")/lib.sh"
load_env
"$HUB_ROOT/scripts/secrets-load.sh"
python3 "$HUB_ROOT/scripts/render-sources.py" --overlay "$HUB_OVERLAY_DIR" >/dev/null
hub_compose up -d
