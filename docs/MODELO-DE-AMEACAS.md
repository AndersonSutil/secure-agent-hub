# Modelo de ameaças

## Ativos

| Ativo | Onde fica | Impacto se vazar |
|---|---|---|
| Logins de assinatura (Claude, ChatGPT, Google) | configs das CLIs | uso da sua conta; possível suspensão |
| Chave age | `~/.config/sops/age/keys.txt` | decripta todos os segredos do overlay |
| Tokens MCP | tmpfs + configs das CLIs | leitura de docs/memória, escrita na memória |
| Código e documentos privados | discos locais, índice Qdrant | vazamento de propriedade intelectual |
| Memória dos agentes | Qdrant `memory` | envenenamento persistente das decisões |

## Princípio: quebrar a tríade letal

Um agente só é explorável por prompt injection de forma grave quando tem as três condições ao mesmo tempo:

1. lê **conteúdo não confiável** (web, PDF de terceiros, issue, e-mail);
2. tem acesso a **dados privados ou segredos**;
3. tem um **canal de saída** (rede, publicação, mensagem).

As defesas que **garantem** algo são as de arquitetura, que removem uma das três condições. Saneamento e classificador só **reduzem a frequência**.

## Vetores e defesas

| Vetor | Defesa | Força | Fase |
|---|---|---|---|
| Documento indexado com instrução escondida | trust por fonte, saneamento, classificador, envelope `<retrieved>` | média | 1 |
| Memória envenenada por um agente comprometido | `remember` saneado + classificado, TTL, `trust=agent` visível | média | 1 |
| Segredo indexado por engano | filtro de arquivos + regex de segredos (descarta e alerta) | média | 1 |
| Exfiltração pelo hub-rag | rede `internal` sem rota nem DNS externo | **forte** | 1 |
| Site malicioso chamando o MCP local (DNS rebinding) | validação do cabeçalho Host (421) + bearer | **forte** | 1 |
| Token MCP vazado | escopo mínimo, rate limit, `hub-kill.sh` rotaciona tudo | média | 1 |
| Agente do OpenBot executando comando perigoso | container + proxy (forte); hooks/execpolicy (fraco) | ver nota 1 | 2 |
| Agente alterando `CLAUDE.md`, `.mcp.json`, `.vscode/` etc. para atacar o host | `pull-from-agents.sh` bloqueia `policy/protected-paths.toml` | **forte** | 2 |
| Exfiltração pelo domínio do provedor (chave do atacante, Files API) | nenhuma completa; o proxy só reduz | **aberto** | 2 |

## Limites conhecidos (não resolvidos)

1. **Hooks e regras de comando são contornáveis.** Regex não resolve ofuscação (`c''at`, base64, scripts temporários). Elas servem como lombada e trilha de auditoria, não como fronteira. A fronteira é o container + o proxy.
2. **Domínios de provedor liberados permitem exfiltração.** Um agente injetado pode enviar dados para `api.anthropic.com` ou `api.openai.com` usando uma chave de API **do atacante** (ex.: upload pela Files API). Fechar isso exige inspeção TLS e regras por chave, o que está fora do escopo.
3. **O maior risco atual está no host, não no hub.** CLIs que rodam no host com acesso total (por exemplo, Antigravity em modo sem sandbox, Codex com `danger-full-access`) leem a web e o seu home. Recomendações:
   - usar o Codex com `--sandbox workspace-write` por padrão;
   - não rodar agentes sem sandbox em pastas com segredos;
   - aplicar os hooks de `harness/claude/` também ao Claude Code do host (opcional, exige sua decisão).
4. **O classificador erra.** Prompt Guard 2 tem falsos positivos e negativos. O limiar fica em `policy/ingest.toml` e o padrão sem modelo é fail-closed (quarentena).
5. **Tokens MCP ficam em texto nas configs do Claude Code e do agy.** Mitigação: escopo `host` limitado e rotação com `hub-kill.sh`.
6. **A chave age em disco é a raiz de confiança.** Quem lê seu home decripta os segredos. É o mesmo nível de risco das credenciais das CLIs que já estão no home.

## Resposta a incidente

1. `scripts/hub-kill.sh` derruba o hub e rotaciona todos os tokens MCP.
2. Revogue os logins dos provedores que estavam no ambiente afetado (sessões nas páginas de conta de cada provedor).
3. Revise `data/logs/mcp-calls.jsonl` e `data/alerts/alerts.jsonl`.
4. Se houver suspeita de memória envenenada: apague a coleção `memory` e restaure um backup anterior (`scripts/restore.sh`).
