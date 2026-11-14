# ADR 0005: OpenBot, go/no-go da Fase 2

- **Data:** 2026-11-14
- **Status:** pendente (aguarda decisão do usuário)

## Critérios definidos no plano

1. Os termos de uso permitem pelo menos um provedor útil.
2. O WebRTC do app funciona com o servidor atrás de proxy (com ou sem um `egress-gw` liberando só TURN).
3. Os hooks do Claude ou o execpolicy do Codex são respeitados em pelo menos um provedor quando controlados pelo OpenBot. Alternativa: aceitar explicitamente o modelo "container + proxy" sem harness.

## Resultados até agora

| Critério | Resultado |
|---|---|
| 1. Termos de uso | só o Codex com assinatura é aceitável (ADR 0001); Claude e Gemini, só com chave de API |
| DNS na rede internal (pré-requisito do proxy) | bloqueado (ADR 0002) |
| 2. WebRTC atrás de proxy | **não testado** |
| 3. Hooks/execpolicy via OpenBot | **não testado** (exige login do Codex dentro de um container de teste) |

## Análise

Com o critério 1, o OpenBot com assinatura vira "Codex com interface, fila e rotinas". Você já usa o Codex diretamente, e o hub da Fase 1 dá a mesma memória e o mesmo conhecimento a todas as CLIs.

O que o OpenBot ainda acrescenta:
- agentes persistentes com rotinas agendadas;
- app no celular.

Em troca, ele traz:
- licença não comercial;
- releases diárias;
- execução em `danger-full-access`.

## Recomendação

**No-go por enquanto.** Reabrir se aparecer necessidade concreta de agentes persistentes e agendados, ou se você aceitar pagar por chave de API para o Claude no OpenBot. Nesse caso, executar os testes dos critérios 2 e 3 antes de qualquer uso real.
