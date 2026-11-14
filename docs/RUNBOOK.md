# Runbook

## Instalar numa máquina nova

Pré-requisitos: podman ≥ 5 com `podman compose` (docker-compose ou podman-compose), Python ≥ 3.11 e, para GPU, o NVIDIA Container Toolkit com CDI gerado.

```bash
git clone https://github.com/<você>/secure-agent-hub agentes-hub
git clone https://github.com/<você>/<seu-overlay-privado> agentes-hub/overlay   # ou: mkdir overlay && cp .env.example overlay/.env
```

1. **Chave age:** restaure do gerenciador de senhas para `~/.config/sops/age/keys.txt` (`chmod 600`). Numa instalação nova sem overlay, o bootstrap gera uma chave; guarde-a no gerenciador de senhas na hora.
2. Ajuste `overlay/.env` (caminhos, GPU) e `overlay/sources.toml`.
3. Rode:
   ```bash
   scripts/bootstrap.sh
   scripts/index.sh
   scripts/register-mcp-host.sh
   ```
4. Opcional: classificador de injeção.
   ```bash
   scripts/download-guard-model.sh              # Prompt Guard 2: aceite a licença no Hugging Face antes
   scripts/download-guard-model.sh --fallback   # alternativa só em inglês, sem licença
   scripts/hub-compose.sh restart hub-rag
   ```
5. Se houver backup: `scripts/restore.sh <arquivo.tar.age>`.

## Operação diária

| Tarefa | Comando |
|---|---|
| Subir depois do boot | automático (`hub-up.service`), ou `scripts/up.sh` |
| Status | `scripts/hub-compose.sh ps` |
| Logs | `scripts/hub-compose.sh logs -f hub-rag` |
| Reindexar agora | `scripts/index.sh` (ou `--source NOME`) |
| Ver alertas | `tail -f $HUB_DATA_DIR/alerts/alerts.jsonl` |
| Ver chamadas MCP | `tail -f $HUB_DATA_DIR/logs/mcp-calls.jsonl` |
| Backup | `scripts/backup.sh` |

## Adicionar uma fonte

1. Acrescente um bloco `[[source]]` em `overlay/sources.toml`. Use `trust = "untrusted"` e `collection = "docs_untrusted"` para qualquer coisa que veio da internet.
2. `scripts/up.sh` (regenera as montagens e recria o hub-rag).
3. `scripts/index.sh --source NOME`.

Em host com SELinux enforcing, se o índice disser que o caminho não existe ou der "permission denied", acrescente `selinux_relabel = true` (aplica `:z`, que muda o rótulo SELinux dos seus arquivos).

## Revisar a quarentena

O que caiu na quarentena aparece como alerta. Para inspecionar:

```bash
scripts/hub-compose.sh exec hub-rag python -c "
from hub_rag import store
pts, _ = store.client().scroll('quarantine', limit=50, with_payload=True)
for p in pts: print(p.payload.get('guard_score'), p.payload.get('source'), p.payload.get('path'), p.payload['text'][:120].replace('\n',' '))"
```

Falso positivo recorrente: ajuste `[guard].threshold` em `policy/ingest.toml`, ou mova a fonte para `trusted` se ela for de fato sua.

## Rotacionar tokens / emergência

```bash
scripts/hub-kill.sh --restart      # derruba, gera tokens novos, sobe
scripts/register-mcp-host.sh       # atualiza Claude Code / Codex / agy
cd overlay && git commit -am "rotação de tokens" && git push
```

## Atualizar

- Imagens fixadas por digest: o Renovate abre PRs. Depois do merge: `scripts/bootstrap.sh`.
- Dependências Python do hub-rag: `scripts/hub-compose.sh build hub-rag && scripts/up.sh`.
- Depois de qualquer atualização: `pytest rag/tests` e o checklist de verificação abaixo.

## Checklist de verificação

1. `curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8765/mcp` → `401`.
2. Com cabeçalho `Host: evil.example` e token válido → `421`.
3. `scripts/index.sh` passa sem erros; nenhum `.env` aparece no índice.
4. Os fixtures de injeção (`rag/tests/fixtures/injection`) vão para a quarentena ou ficam saneados.
5. `podman exec <qdrant> bash -c ':> /dev/tcp/1.1.1.1/80'` falha (a rede internal continua fechada).
