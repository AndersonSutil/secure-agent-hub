# ADR 0003: sops + age em vez de OpenBao/Vault

- **Data:** 2026-11-14
- **Status:** aceita

## Contexto

O plano inicial usava o OpenBao para os segredos de máquina e também para as senhas pessoais. O uso é de uma pessoa só, numa máquina só, com migração ocasional de computador.

## Alternativas

| | OpenBao | sops + age | Gerenciador de senhas |
|---|---|---|---|
| Serviço rodando | sim | não | não |
| Unseal a cada boot | sim (manual) | não | não |
| Backup | snapshots de raft | o próprio git | sincronização do app |
| Segredos dinâmicos e auditoria | sim | não | não |
| Autofill e celular para senhas pessoais | não | não | sim |

## Decisão

- **Segredos de máquina** (tokens MCP e tokens futuros de serviços) ficam em `overlay/secrets/*.sops.yaml`, criptografados com age e versionados no overlay privado. Em runtime são decriptados para tmpfs (`$XDG_RUNTIME_DIR`).
- **Senhas pessoais** ficam em KeePassXC ou Bitwarden, fora do hub.
- **Chave age:** fica em `~/.config/sops/age/keys.txt`, com cópia no gerenciador de senhas. Ela é a raiz de confiança.

## Consequências

- Não há tokens dinâmicos nem auditoria de leitura de segredos. A rotação é manual (`scripts/hub-kill.sh`).
- Reavaliar se surgirem várias máquinas ou várias pessoas, ou necessidade de credenciais de curta duração (por exemplo, o broker da Fase 3).
