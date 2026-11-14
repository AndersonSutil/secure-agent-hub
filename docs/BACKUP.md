# Backup e migração

| Dado | Onde fica | Backup |
|---|---|---|
| Código, políticas, documentação | repositório público | git |
| `.env`, fontes, segredos criptografados | overlay privado | git (os segredos já estão criptografados com sops) |
| Chave age | `~/.config/sops/age/keys.txt` | **cópia manual no gerenciador de senhas** |
| Coleções `memory` e `quarantine` | Qdrant | `scripts/backup.sh` (tar criptografado com age) |
| Coleções `docs`, `docs_untrusted`, `code` | Qdrant | não precisa: `scripts/index.sh` recria |
| Modelos (embedding, classificador) | `$HUB_DATA_DIR` | não precisa: os scripts baixam de novo |
| Logins das CLIs | configs de cada CLI | **não copie**: faça login de novo na máquina nova |

## Backup

```bash
scripts/backup.sh
```

O resultado é `$BACKUP_DIR/agentes-hub-AAAAMMDD-HHMMSS.tar.age`. Ele só pode ser aberto com a sua chave age. Mantenha `BACKUP_DIR` num disco diferente do disco de dados.

## Restaurar

```bash
scripts/restore.sh /caminho/agentes-hub-AAAAMMDD-HHMMSS.tar.age
```

Isso substitui as coleções `memory` e `quarantine` pelas do backup.

## Perdi a chave age

Os segredos do overlay viram irrecuperáveis, mas eles são só tokens MCP. Para recomeçar:

1. apague `overlay/secrets/hub.sops.yaml` e `overlay/.sops.yaml`;
2. rode `scripts/secrets-init.sh`, que gera uma chave nova e tokens novos;
3. rode `scripts/register-mcp-host.sh`.

Os backups antigos de memória também ficam ilegíveis.
