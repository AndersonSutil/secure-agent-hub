# ADR 0004: repositório público + overlay privado

- **Data:** 2026-11-14
- **Status:** aceita

## Contexto

O hub precisa ser reinstalável em outra máquina e também servir de portfólio. A primeira ideia era desenvolver num repositório privado e exportar uma cópia "limpa" para o público.

## Problemas da cópia exportada

- o histórico do público vira uma sequência de dumps, que vale pouco como portfólio;
- as duas cópias tendem a divergir;
- o script de limpeza vira um ponto único por onde dados podem vazar.

## Decisão

- **Público:** o próprio repositório de desenvolvimento, genérico desde o início. Tudo que é pessoal vem de variáveis.
- **Privado:** só o overlay (`.env`, `sources.toml`, segredos sops, `private-terms.txt`), clonado em `overlay/` e ignorado pelo público.
- **Proteção contra vazamento:**
  - pre-commit com `gitleaks` e `scripts/check-private-terms.sh` (termos do overlay);
  - `gitleaks` no CI;
  - revisão do diff antes de cada push.
- **Segurança por obscuridade não é requisito:** as defesas precisam funcionar mesmo com a configuração pública (princípio de Kerckhoffs).

## Consequências

- O histórico do público deve ser revisado antes do primeiro push, porque um termo privado num commit antigo fica para sempre.
- Allowlists de rede específicas da máquina ficam em `overlay/egress.local.toml`.
