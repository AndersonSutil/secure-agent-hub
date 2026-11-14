# secure-agent-hub

Self-hosted knowledge and memory hub for coding agents (Claude Code, Codex, Antigravity), designed around prompt-injection threat modeling. Rootless podman, no cloud services beyond the LLM providers themselves.

*[Português abaixo](#português)*

## What it does

- **MCP server** (`hub-knowledge`, streamable HTTP on `127.0.0.1`) with `search_knowledge`, `remember` and `recall`. Every agent CLI on the machine shares the same documentation index and long-term memory.
- **Provenance-aware RAG.** Each source is `trusted` or `untrusted`. Results come wrapped in `<retrieved trust=… source=…>` envelopes that are explicitly marked as data, not instructions.
- **Ingestion guardrails:**
  - secret-file and secret-regex filtering;
  - Unicode smuggling removal (zero-width, bidi, tag characters);
  - HTML-comment and external-image stripping;
  - a local prompt-injection classifier (Llama Prompt Guard 2) with a fail-closed quarantine.
- **Network isolation.** Vector DB, embedder and RAG server live on a podman `internal` network: no egress and no external DNS ([ADR 0002](docs/adr/0002-rede-internal.md)).
- **Policy as code.** One source of truth (`policy/*.toml`) is rendered into Claude Code hooks, Codex execpolicy rules, Gemini CLI excludes, a Squid egress allowlist and a protected-paths list for reviewing agent changes.
- **Portable secrets.** sops + age, decrypted only to tmpfs. Personal passwords stay in a password manager ([ADR 0003](docs/adr/0003-sops-age-em-vez-de-vault.md)).
- **Operations:**
  - an idempotent bootstrap;
  - age-encrypted backups;
  - a kill switch that rotates every token;
  - desktop notifications for security alerts.

## Threat model in one paragraph

An agent is dangerous when it simultaneously reads untrusted content, holds private data and has an outbound channel (the "lethal trifecta"). Architectural controls in this repo (no-egress network, scoped tokens, read-only mounts, Host-header validation) break one leg of the trifecta and are treated as boundaries. Classifiers, sanitizers and command hooks only reduce frequency and are documented as such. Known open gaps, such as exfiltration through allowed LLM-provider domains, are listed in [docs/MODELO-DE-AMEACAS.md](docs/MODELO-DE-AMEACAS.md).

## Quick start

```bash
git clone https://github.com/AndersonSutil/secure-agent-hub && cd secure-agent-hub
mkdir overlay && cp .env.example overlay/.env    # edit paths / GPU
scripts/bootstrap.sh            # builds, generates age key + tokens, starts the stack
scripts/index.sh                # index sources from overlay/sources.toml
scripts/register-mcp-host.sh    # register the MCP server in Claude Code / Codex / agy
```

Requirements: podman ≥ 5 with `podman compose`, Python ≥ 3.11, optionally an NVIDIA GPU with CDI.

## Layout

| Path | Contents |
|---|---|
| `policy/` | rules (single source of truth) |
| `rag/` | hub-rag: indexer + MCP server (Python, FastMCP, qdrant-client) |
| `harness/`, `proxy/` | files generated from `policy/` (agent harness, egress proxy) |
| `scripts/` | bootstrap, secrets, indexing, backup/restore, kill switch |
| `docs/` | architecture, threat model, rules, runbook, ADRs (Portuguese) |
| `overlay/` | **not in this repo**: per-machine private config (a separate private repo) |

## Status

Phase 1 (RAG + memory for host CLIs) is implemented. Phase 2, an isolated autonomous-agent runner, is on hold: see [ADR 0005](docs/adr/0005-openbot-go-no-go.md).

---

## Português

Hub local de conhecimento e memória para agentes de código, projetado a partir de um modelo de ameaças de prompt injection.

**O que ele faz:**
- um servidor MCP de busca e memória compartilhada;
- RAG com proveniência e nível de confiança por fonte;
- saneamento e classificador de injeção na entrada;
- isolamento de rede;
- regras como código;
- segredos com sops + age.

**Por onde começar:**
- [Arquitetura](docs/ARQUITETURA.md)
- [Modelo de ameaças](docs/MODELO-DE-AMEACAS.md)
- [Regras](docs/REGRAS.md)
- [Runbook](docs/RUNBOOK.md) (inclui instalar em outra máquina)
- [Backup](docs/BACKUP.md)
- [ADRs](docs/adr/)

## License

MIT, see [LICENSE](LICENSE).
