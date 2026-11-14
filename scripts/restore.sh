#!/usr/bin/env bash
# Restaura um backup de scripts/backup.sh (substitui as coleções memory/quarantine).
#   scripts/restore.sh /caminho/agentes-hub-AAAAMMDD-HHMMSS.tar.age [--yes]
source "$(dirname "$0")/lib.sh"
load_env
FILE="${1:?uso: restore.sh <backup.tar.age> [--yes]}"
[ -f "$FILE" ] || die "arquivo não encontrado: $FILE"
if [ "${2:-}" != "--yes" ]; then
  read -r -p "Substituir as coleções memory/quarantine atuais pelo backup? [s/N] " ans
  [ "$ans" = "s" ] || [ "$ans" = "S" ] || die "cancelado"
fi

# Extrai dentro do diretório de snapshots do Qdrant, num subdiretório temporário.
STAMP="restore-$(date +%s)"
DEST="$HUB_DATA_DIR/qdrant-snapshots/$STAMP"
mkdir -p "$DEST"
info "decriptando $FILE"
hub_tools -v "$(dirname "$SOPS_AGE_KEY_FILE"):/age:ro" -v "$(cd "$(dirname "$FILE")" && pwd):/in:ro" \
  -v "$DEST:/out" -- sh -c "age -d -i '/age/$(basename "$SOPS_AGE_KEY_FILE")' '/in/$(basename "$FILE")' | tar -xf - -C /out"

found=0
# Caminho visto DENTRO do container qdrant: /qdrant/snapshots/<STAMP>/<coleção>/<arquivo>.
for snap in "$DEST"/*/*.snapshot; do
  [ -e "$snap" ] || continue
  found=1
  col="$(basename "$(dirname "$snap")")"
  rel="$STAMP/$col/$(basename "$snap")"
  info "recuperando $col"
  hub_compose exec -T hub-rag python - "$col" "$rel" <<'PY'
import json, sys, urllib.request
col, rel = sys.argv[1], sys.argv[2]
body = json.dumps({"location": f"file:///qdrant/snapshots/{rel}", "priority": "snapshot"}).encode()
req = urllib.request.Request(f"http://qdrant:6333/collections/{col}/snapshots/recover?wait=true",
                             data=body, method="PUT", headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req, timeout=600)))
PY
done
# Remove os snapshots decriptados (em claro) usando um container, porque o dono é o subuid.
hpodman run --rm --security-opt label=disable -v "$HUB_DATA_DIR/qdrant-snapshots:/s" \
  localhost/hub-tools:dev rm -rf "/s/$STAMP"
[ "$found" = 1 ] || die "nenhum snapshot encontrado no backup"
info "restauração concluída"
