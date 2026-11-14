# harness/

Arquivos **gerados** por `scripts/render-policy.py` a partir de `policy/`, exceto:

- `AGENTS.md`: regras suaves para os agentes (editado à mão);
- `claude/hooks/guard.py`: implementação do hook `PreToolUse` (lê `claude/guard-rules.json`).

Uso previsto na Fase 2, dentro do container do agente:

| Arquivo | Destino |
|---|---|
| `claude/settings.json` | `~/.claude/settings.json` |
| `claude/hooks/guard.py` + `guard-rules.json` | `/opt/hub/harness/claude/` |
| `codex/rules/hub.rules` | `~/.codex/rules/hub.rules` |
| `gemini/settings.json` | `~/.gemini/settings.json` |
| `AGENTS.md` | `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md` |

Antes de confiar em qualquer um deles, confirme que a CLI aplica a regra quando é controlada por outro programa (ADR 0005).
