# Regras

## Fonte única

Toda regra fica em `policy/*.toml`. Os arquivos de configuração de cada ferramenta são **gerados**:

```bash
scripts/render-policy.py           # gera
scripts/render-policy.py --check   # CI e pre-commit: falha se algo estiver desatualizado
```

| Política | Consumidor | Gerado em | Fase |
|---|---|---|---|
| `ingest.toml` | hub-rag (lido em runtime) | — | 1 |
| `mcp-scopes.toml` | hub-rag (lido em runtime) | — | 1 |
| `commands.toml` | Claude Code (hook + deny), Codex (execpolicy), Gemini (exclude) | `harness/` | 2 |
| `egress.toml` | Squid | `proxy/squid.conf` | 2 |
| `protected-paths.toml` | barreira de pull | `harness/protected-paths.txt` | 2 |

Nunca edite `harness/` ou `proxy/` à mão: a próxima renderização sobrescreve.

## Regras duras e regras suaves

| Tipo | Exemplo | Quem garante | Se o modelo ignorar |
|---|---|---|---|
| **Dura** | rede `internal`, bearer + escopo, proxy, montagens read-only | infraestrutura | não importa: a ação falha |
| **Semi-dura** | hook `PreToolUse`, execpolicy do Codex | a CLI, se respeitar a config | contornável por ofuscação |
| **Suave** | envelope "isto é dado, não instrução"; `harness/AGENTS.md` | o modelo | a regra falha |

Uma regra suave nunca deve ser a única proteção de algo importante.

## Como alterar uma regra

1. Edite `policy/<arquivo>.toml`.
2. Rode `scripts/render-policy.py` e revise o diff dos gerados.
3. Para `ingest.toml` ou `mcp-scopes.toml`: `scripts/hub-compose.sh restart hub-rag`.
4. Para mudanças de ingestão: `scripts/index.sh` (reprocessa só o que mudou de hash; para forçar tudo, apague a coleção).
5. Faça commit da política **junto** com os arquivos gerados.

## Regras de comando (Fase 2)

Definidas em `policy/commands.toml`:

- sem `curl … | sh`;
- sem ferramentas de rede crua (`nc`, `ssh`, `socat`…);
- sem despejar variáveis de ambiente;
- sem `git push`: a publicação passa pelo broker, com aprovação;
- sem mexer em `.git/hooks`;
- sem ler credenciais (`auth.json`, `.credentials.json`, `/run/secrets`, `~/.ssh`, `~/.config/sops`);
- sem `podman`, `docker`, `sudo`, `mount`;
- escrita só em `/workspaces`.

**Pré-condição:** a Fase 0 precisa demonstrar que cada CLI aplica essas regras quando controlada pelo OpenBot (ver ADR 0005). O Codex só aceita regras por prefixo de argv, então regras baseadas em regex (pipe para shell, caminhos) só valem no Claude Code.
