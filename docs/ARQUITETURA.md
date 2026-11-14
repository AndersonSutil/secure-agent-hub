# Arquitetura

## Objetivo

Dar a agentes de código (Claude Code, Codex, Antigravity e, opcionalmente, OpenBot) três coisas que eles não têm sozinhos:

1. **Conhecimento consultável:** documentação e anotações indexadas, com origem e nível de confiança.
2. **Memória compartilhada:** um agente grava uma decisão e outro recupera.
3. **Regras versionadas:** uma única fonte (`policy/`) que vira configuração de cada ferramenta.

Tudo roda em uma máquina, em containers rootless, sem serviços na nuvem além dos próprios provedores de LLM.

## Fases

| Fase | Conteúdo | Estado |
|---|---|---|
| 0 | Viabilidade do OpenBot: termos de uso, hooks, WebRTC atrás de proxy, DNS | parcial (ver ADRs 0001 e 0002) |
| 1 | RAG + memória via MCP para as CLIs do host, segredos sops/age | implementada |
| 2 | OpenBot "Executor" isolado com proxy, harness e barreira de pull | só com go da Fase 0 |
| 3 | Pesquisador separado, broker com aprovação, canary tokens | sob demanda |

## Fase 1

```
host (só 127.0.0.1)
  Claude Code / Codex / agy ──HTTP + Bearer──▶ :8765 hub-rag (MCP)
  hub-notify (systemd --user) ◀── alerts.jsonl
  hub-index.timer ──▶ hub-rag-index (a cada 30 min)

rede hub-internal (internal: sem rota externa, sem DNS externo)
  hub-rag ──▶ qdrant (vetores)
          └─▶ ollama-embed (qwen3-embedding, GPU opcional)
```

| Serviço | Imagem | Rede | Portas no host |
|---|---|---|---|
| `qdrant` | `qdrant/qdrant` (digest fixo) | internal | nenhuma |
| `ollama-embed` | `ollama/ollama` (digest fixo) | internal | nenhuma |
| `hub-rag` | build local (`rag/`) | internal | `127.0.0.1:8765` |

**Por que a rede é `internal`:** o hub-rag guarda conteúdo privado e roda código de terceiros (dependências Python, modelo do classificador). Sem rota de saída, um comprometimento dele não tem para onde mandar dados. A ADR 0002 registra o teste: o DNS externo não resolve e conexões TCP para fora falham.

### Coleções

| Coleção | Origem | Trust | Tratamento |
|---|---|---|---|
| `docs` | suas pastas | `trusted` | filtro de arquivos e de segredos, chunking |
| `docs_untrusted` | material de terceiros (PDFs, docs baixadas) | `untrusted` | + saneamento + classificador |
| `memory` | ferramenta `remember` dos agentes | `agent` | + saneamento + classificador, TTL de 90 dias, máximo 2 KB |
| `quarantine` | o que o classificador reprovou | — | nunca é devolvido em buscas; gera alerta |
| `code` | repositórios (opcional, desligado) | `trusted` | igual a `docs` |

### Fluxo de indexação

```
arquivo ─▶ ignorado? (policy/ingest.toml: .env, chaves, binários, >1 MB) ─▶ descarta
        ─▶ chunking (markdown por título, código por função, resto por janela)
        ─▶ segredo? (regex) ─▶ descarta + alerta
        ─▶ untrusted? ─▶ saneamento (Unicode invisível, comentários HTML, imagens/links externos)
                      ─▶ classificador ≥ limiar ─▶ quarantine + alerta
        ─▶ embedding (Ollama) ─▶ Qdrant (payload: source, path, linha, sha256, trust, guard_score)
```

A indexação é incremental: só arquivos com SHA-256 diferente são reprocessados, e arquivos apagados saem do índice.

### Ferramentas MCP

| Ferramenta | Escopos | Faz |
|---|---|---|
| `search_knowledge` | host, executor, admin | busca em docs e memória; resultado em envelope `<retrieved trust=…>` |
| `remember` | host, executor, admin | grava memória (saneada e classificada) |
| `recall` | host, executor, admin | busca só na memória |
| `list_sources` | host, executor, admin | fontes e tamanho das coleções |
| `submit_research` | reader | grava resumo de pesquisa em `docs_untrusted` |
| `reindex` | admin | reindexa fontes |

Os escopos ficam em `policy/mcp-scopes.toml`. Cada escopo tem um token próprio (`overlay/secrets/hub.sops.yaml`).

## Segredos

```
chave age (~/.config/sops/age/keys.txt; cópia no gerenciador de senhas)
   │ decripta
   ▼
overlay/secrets/hub.sops.yaml (no git, criptografado) ── secrets-load.sh ──▶ $XDG_RUNTIME_DIR/agentes-hub (tmpfs)
                                                                                 └─▶ montado read-only no hub-rag
```

Senhas pessoais **não** ficam no hub: ficam num gerenciador de senhas (KeePassXC/Bitwarden). Ver ADR 0003.

## Repositórios

- **Público** (`secure-agent-hub`): todo o código, as políticas e a documentação, sem nada pessoal.
- **Privado** (overlay, clonado em `overlay/`): `.env`, `sources.toml`, segredos sops, termos privados.

Ver ADR 0004.
