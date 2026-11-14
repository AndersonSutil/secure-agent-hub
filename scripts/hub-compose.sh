#!/usr/bin/env bash
# Wrapper do compose com overlay/.env, GPU opcional e montagens das fontes.
# Ex.: scripts/hub-compose.sh up -d | ps | logs -f hub-rag | down
source "$(dirname "$0")/lib.sh"
load_env
hub_compose "$@"
