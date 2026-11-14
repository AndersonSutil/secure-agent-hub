# shellcheck shell=bash
# Funções comuns dos scripts. Uso: source "$(dirname "$0")/lib.sh"
set -euo pipefail

HUB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HUB_ROOT

die() { printf 'erro: %s\n' "$*" >&2; exit 1; }
info() { printf '==> %s\n' "$*" >&2; }

# Dentro de uma distrobox/toolbox o podman é o do host.
host_exec() {
  if command -v podman >/dev/null 2>&1; then
    "$@"
  elif [ -x /usr/bin/distrobox-host-exec ]; then
    /usr/bin/distrobox-host-exec "$@"
  else
    die "podman não encontrado (nem distrobox-host-exec)"
  fi
}

hpodman() { host_exec podman "$@"; }

load_env() {
  local overlay="${HUB_OVERLAY_DIR:-$HUB_ROOT/overlay}"
  [ -f "$overlay/.env" ] || die "faltando $overlay/.env (copie de .env.example)"
  set -a
  # shellcheck disable=SC1091
  . "$overlay/.env"
  set +a
  HUB_OVERLAY_DIR="$(cd "$HUB_ROOT" && cd "${HUB_OVERLAY_DIR:-./overlay}" && pwd)"
  HUB_DATA_DIR="${HUB_DATA_DIR/#\~/$HOME}"
  SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
  SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE/#\~/$HOME}"
  BACKUP_DIR="${BACKUP_DIR/#\~/$HOME}"
  HUB_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/agentes-hub"
  export HUB_OVERLAY_DIR HUB_DATA_DIR SOPS_AGE_KEY_FILE BACKUP_DIR HUB_RUNTIME_DIR
}

# Roda o hub-tools (sops, age, gitleaks...) com o repositório em /work.
# Extra args do podman vêm antes de "--".
hub_tools() {
  local extra=()
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do extra+=("$1"); shift; done
  [ "${1:-}" = "--" ] && shift
  # Sem -i: o hub-tools nunca lê stdin (e -i roubaria o stdin de prompts do script).
  hpodman run --rm --network none --security-opt label=disable \
    -v "$HUB_ROOT:/work" -w /work "${extra[@]}" localhost/hub-tools:dev "$@"
}

hub_compose() {
  local files=(-f "$HUB_ROOT/compose.yaml")
  if [ "${EMBED_GPU:-cpu}" != "cpu" ]; then files+=(-f "$HUB_ROOT/compose.gpu.yaml"); fi
  [ -f "$HUB_OVERLAY_DIR/compose.sources.yaml" ] && files+=(-f "$HUB_OVERLAY_DIR/compose.sources.yaml")
  # distrobox-host-exec não repassa o ambiente: as variáveis vão explícitas via env.
  host_exec env \
    HUB_DATA_DIR="$HUB_DATA_DIR" HUB_OVERLAY_DIR="$HUB_OVERLAY_DIR" \
    HUB_RUNTIME_DIR="$HUB_RUNTIME_DIR" EMBED_GPU="${EMBED_GPU:-cpu}" \
    PODMAN_COMPOSE_WARNING_LOGS=false \
    podman compose --project-directory "$HUB_ROOT" --env-file "$HUB_OVERLAY_DIR/.env" "${files[@]}" "$@"
}
