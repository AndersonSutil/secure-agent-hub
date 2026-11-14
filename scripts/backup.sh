#!/usr/bin/env bash
# Backup criptografado (age) do que não dá para recriar: coleções memory e quarantine.
# docs/docs_untrusted são reindexáveis; segredos já estão no git (sops).
# Saída: $BACKUP_DIR/agentes-hub-<data>.tar.age
source "$(dirname "$0")/lib.sh"
load_env
[ -n "${BACKUP_DIR:-}" ] || die "defina BACKUP_DIR no overlay/.env"
COLLECTIONS=(memory quarantine)
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

info "criando snapshots no Qdrant: ${COLLECTIONS[*]}"
NAMES="$(hub_compose exec -T hub-rag python - "${COLLECTIONS[@]}" <<'PY'
import json, sys, urllib.request
base = "http://qdrant:6333"
for col in sys.argv[1:]:
    try:
        urllib.request.urlopen(f"{base}/collections/{col}", timeout=10)
    except Exception:
        continue  # coleção ainda não existe
    req = urllib.request.Request(f"{base}/collections/{col}/snapshots?wait=true", method="POST")
    name = json.load(urllib.request.urlopen(req, timeout=600))["result"]["name"]
    print(f"{col}/{name}")
PY
)"
[ -n "$NAMES" ] || die "nenhuma coleção para salvar"

mapfile -t SNAPS <<<"$NAMES"
LIST="${SNAPS[*]}"
RECIPIENT="$(hub_tools -v "$(dirname "$SOPS_AGE_KEY_FILE"):/age:ro" -- age-keygen -y "/age/$(basename "$SOPS_AGE_KEY_FILE")")"
OUT="agentes-hub-$STAMP.tar.age"
# shellcheck disable=SC2086
hub_tools -v "$HUB_DATA_DIR/qdrant-snapshots:/snap:ro" -v "$BACKUP_DIR:/out" -- \
  sh -c "cd /snap && tar -cf - $LIST | age -r '$RECIPIENT' -o '/out/$OUT'"
info "backup: $BACKUP_DIR/$OUT"

# Apaga os snapshots em claro pela API (o arquivo pertence ao subuid do Qdrant).
hub_compose exec -T hub-rag python - "${SNAPS[@]}" <<'PY'
import sys, urllib.request
for item in sys.argv[1:]:
    col, name = item.split("/", 1)
    req = urllib.request.Request(f"http://qdrant:6333/collections/{col}/snapshots/{name}", method="DELETE")
    urllib.request.urlopen(req, timeout=60)
PY
info "snapshots temporários em claro removidos"
