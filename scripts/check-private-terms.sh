#!/usr/bin/env bash
# Pre-commit do repositório PÚBLICO: bloqueia commit que contenha termos privados
# listados em overlay/private-terms.txt (um termo por linha, # comenta).
#   scripts/check-private-terms.sh [arquivos...]   (sem argumentos: arquivos staged)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TERMS="${HUB_PRIVATE_TERMS:-$ROOT/overlay/private-terms.txt}"
if [ ! -f "$TERMS" ]; then
  echo "aviso: $TERMS não existe; verificação de termos privados ignorada" >&2
  exit 0
fi
mapfile -t files < <(if [ $# -gt 0 ]; then printf '%s\n' "$@"; else git -C "$ROOT" diff --cached --name-only --diff-filter=ACMR; fi)
[ ${#files[@]} -gt 0 ] || exit 0
pattern_file="$(mktemp)"
trap 'rm -f "$pattern_file"' EXIT
grep -v '^\s*#' "$TERMS" | sed '/^\s*$/d' > "$pattern_file"
[ -s "$pattern_file" ] || exit 0
fail=0
for f in "${files[@]}"; do
  case "$f" in overlay/*) continue;; esac
  [ -f "$ROOT/$f" ] || continue
  if hits="$(grep -n -i -F -f "$pattern_file" "$ROOT/$f")"; then
    echo "TERMO PRIVADO em $f:" >&2
    printf '%s\n' "$hits" | cut -c1-160 >&2
    fail=1
  fi
done
# O nome do arquivo também conta.
if printf '%s\n' "${files[@]}" | grep -i -F -f "$pattern_file" >/dev/null; then
  echo "TERMO PRIVADO em nome de arquivo" >&2
  fail=1
fi
exit $fail
