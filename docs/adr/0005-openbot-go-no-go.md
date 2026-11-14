# ADR 0005: OpenBot, go/no-go da Fase 2

- **Data:** 2026-11-14
- **Status:** Fase 0 executada. Decisão final é do usuário (recomendação abaixo).

## Critérios definidos no plano

1. Os termos de uso permitem pelo menos um provedor útil.
2. O app conecta ao servidor atrás de proxy (com ou sem `egress-gw`).
3. Os hooks do Claude ou o execpolicy do Codex são respeitados quando o OpenBot controla a CLI. Alternativa: aceitar explicitamente o modelo "container + proxy" sem harness.

## Ambiente de teste (`spikes/openbot/run.sh`)

| Item | Configuração |
|---|---|
| Imagem | `ghcr.io/nightly-labs/openbot:0.70.0`, fixada por digest. Procedência verificada com `gh attestation verify`: SLSA v1, workflow `release.yml`, tag `v0.70.0` |
| Container | podman 6.1.3 rootless, seccomp oficial do projeto, `no-new-privileges`, 6 GB de RAM, 4096 pids |
| Rede | `internal` (sem rota nem DNS externo); saída só pelo Squid com a allowlist `executor` de `policy/egress.toml` |
| Harness | `harness/codex/rules/hub.rules` e `AGENTS.md` montados read-only em `~/.codex` |
| Provedor | Codex com login ChatGPT, separado e revogável; modelo GPT-6-Luna |

## Resultados

| Teste | Resultado |
|---|---|
| 1. Termos de uso | só o Codex com assinatura é aceitável (ADR 0001) |
| Podman rootless (não suportado oficialmente) | **funciona** com `podman run`. O docker-compose do podman falha ao enviar o seccomp inline ("file name too long") |
| DNS externo / TCP direto | **bloqueados** |
| Proxy | provedores e openbot.run passam; example.com, pastebin e LAN são negados |
| 2. WebRTC atrás de proxy | **funciona** depois de liberar `CONNECT` para `^turn[a-z0-9-]*\.openbot\.run$` nas portas 3478/5349. Sem UDP, o Chromium faz TURN-TCP/TLS pelo próprio proxy (`turn-us`, `turn2`). Signal: `signal-us.openbot.run:443`. Não precisou de `egress-gw` |
| Telemetria | o OpenBot envia dados a `analytics.openbot.run` por padrão, **antes** do login. Bloqueado pela política sem efeito visível no app |
| Atualização de CLIs | o OpenBot baixa binários em runtime do GitHub Releases (Codex 0.160.1), fora do digest da imagem. Também tenta `api.github.com`, `x.ai`, `devin.ai`, `cursor.com`, `opencode.ai` e o atualizador do Chromium (todos negados, sem quebrar o app) |
| 3. execpolicy do Codex via OpenBot | **aplicado** mesmo em `danger-full-access`: `printenv`, `env`, `nc` e `cd x && git push` foram rejeitados antes de executar, com a justificativa da política |
| execpolicy: contornos | `codex execpolicy check` mostra que **não** pega `git -C dir push`, `sh -c '…'`, caminhos absolutos (`/usr/bin/nc`), `python3 -c`, nem `cat /proc/self/environ`. Na prática, o próprio modelo se recusou a executar essas variantes (regra suave, não garantia) |
| Adulteração da política | `rm` do `hub.rules` falhou (montagem read-only) |
| Credenciais do agente | o agente **lê** `~/.codex/auth.json` (o token do ChatGPT), como já indicava a documentação do OpenBot |

## Bugs encontrados no hub durante o teste (corrigidos)

- O `squid.conf` gerado tinha `openbot.run` e `.openbot.run` juntos, e o Squid recusava iniciar. O `render-policy` agora rejeita sobreposições.
- A primeira regex de TURN não cobria `turn2.openbot.run`.

## Análise

Os critérios 2 e 3 passaram, então tecnicamente dá para rodar o OpenBot isolado. O que o teste **não** muda:

- **Com assinatura, só o Codex é aceitável.** O ganho em relação ao `codex exec` com o hub é a interface, a fila, as rotinas e o celular.
- **O harness é lombada, não fronteira.** A proteção real é container + proxy, e o proxy precisa liberar os domínios do provedor (exfiltração pela chave do atacante) e agora também um relay TURN, que é um canal genérico de dados.
- **O agente lê o token do ChatGPT.** Uma injeção bem-sucedida pode tentar mandá-lo para fora pelos domínios liberados.
- **Fora do digest:** binários baixados em runtime, licença não comercial, releases diárias.

## Recomendação

- **Para o fluxo atual, no-go.** O ganho sobre o `codex exec` + hub não justifica um segundo login exposto a um app de terceiros e a exceção TURN no proxy.
- **Se você quiser uso real** (rotinas, celular), é **go condicional**, com:
  - este setup (`spikes/openbot/run.sh`);
  - só o Codex, com login dedicado;
  - montagem de workspace só com clones e a barreira de pull da Fase 2;
  - telemetria bloqueada;
  - versão fixada;
  - repetir este teste a cada atualização.
