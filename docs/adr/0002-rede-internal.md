# ADR 0002: serviços do hub em rede podman `internal`

- **Data:** 2026-11-14
- **Status:** aceita

## Contexto

O hub-rag guarda conteúdo privado e executa dependências de terceiros. Se for comprometido, o dano depende de existir um canal de saída. As hipóteses a testar eram:

- se uma rede `internal` aceita publicar porta em `127.0.0.1` no podman rootless;
- se ela bloqueia o DNS externo, que poderia servir de canal de exfiltração.

## Teste (podman 6.1.3 rootless, netavark/pasta)

```
podman network create --internal hubtest-int
podman run -d --network hubtest-int -p 127.0.0.1:16333:6333 qdrant/qdrant:v1.20.1
curl http://127.0.0.1:16333/                    -> responde (porta publicada funciona)
podman exec … getent hosts example.com          -> sem resolução externa
podman exec … bash -c ':> /dev/tcp/1.1.1.1/80'  -> conexão bloqueada
```

## Decisão

Todos os serviços da Fase 1 ficam só em `hub-internal`. O MCP é publicado apenas em `127.0.0.1`. Os modelos são baixados por containers temporários com rede (`scripts/pull-embed-model.sh`, `scripts/download-guard-model.sh`), nunca pelo serviço em execução.

## Consequências

- O hub-rag roda com `HF_HUB_OFFLINE=1`: modelo ausente significa classificador indisponível, com política fail-closed (tudo vai para quarentena).
- O comportamento pode mudar em outras versões do podman ou do netavark. O checklist do RUNBOOK repete o teste.
