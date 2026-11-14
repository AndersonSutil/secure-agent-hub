#!/usr/bin/env bash
# Reindexa as fontes de overlay/sources.toml (incremental por hash).
#   scripts/index.sh                 # todas
#   scripts/index.sh --source NOME   # uma
#   scripts/index.sh --dry-run
source "$(dirname "$0")/lib.sh"
load_env
hub_compose exec -T hub-rag hub-rag-index "$@"
