#!/usr/bin/env bash
# Lê $HUB_DATA_DIR/alerts/alerts.jsonl e mostra notificações no desktop (notify-send).
# Roda no HOST como serviço systemd --user (systemd/hub-notify.service).
set -euo pipefail
ALERTS="${1:?uso: hub-notify.sh <arquivo alerts.jsonl>}"
# O arquivo é criado pelo hub-rag (dono: subuid do container); tail -F espera ele aparecer.
command -v notify-send >/dev/null || { echo "notify-send ausente" >&2; exit 1; }

tail -n 0 -F "$ALERTS" | while IFS= read -r line; do
  parsed="$(printf '%s' "$line" | python3 -c '
import json, sys
try:
    a = json.loads(sys.stdin.read())
except ValueError:
    sys.exit(0)
urg = "critical" if a.get("severity") == "critical" or a.get("kind") in ("hook_denied", "secret_dropped") else "normal"
skip = {"ts", "source", "kind", "severity"}
body = ", ".join(f"{k}={str(v)[:80]}" for k, v in a.items() if k not in skip)
kind, src = a.get("kind", "alerta"), a.get("source", "?")
print(urg)
print(f"hub: {kind} ({src})")
print(body[:300])
')" || continue
  [ -n "$parsed" ] || continue
  urgency="$(sed -n 1p <<<"$parsed")"
  title="$(sed -n 2p <<<"$parsed")"
  body="$(sed -n 3p <<<"$parsed")"
  notify-send --app-name=agentes-hub --urgency="$urgency" "$title" "$body" || true
done
