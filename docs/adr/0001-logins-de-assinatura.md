# ADR 0001: logins de assinatura em ferramentas de terceiros (OpenBot)

- **Data:** 2026-11-14
- **Status:** aceita

## Contexto

O OpenBot (nightly-labs/openbot) controla os agentes usando os logins que o usuário já tem nas CLIs: a sessão do Claude Agent SDK, o Codex App Server e o Gemini/Antigravity CLI. A pergunta é se os termos de cada provedor permitem esse uso com **planos de consumidor**, sem chave de API.

## Fontes consultadas (2026-11-14)

- **Anthropic,** [Legal and compliance (Claude Code docs)](https://code.claude.com/docs/en/legal-and-compliance):
  - desenvolvedores que usam o Agent SDK devem usar chave de API;
  - a Anthropic proíbe terceiros de oferecer login claude.ai ou de "route requests through Free, Pro, Max, or Ultra plan credentials";
  - **permite** que o usuário entre "to the unmodified Claude Code binary with their own Claude subscription";
  - a aplicação pode ocorrer "without prior notice".
- **OpenAI,** [Sign in with ChatGPT (cookbook)](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt): o uso do plano é liberado para projetos open source e pessoais que rodam localmente. Não há texto específico sobre o caso do OpenBot.
- **Google,** [termos do Gemini CLI](https://www.geminicli.com/docs/resources/tos-privacy) (atualizados em abril de 2026): acessar os serviços "using third-party software" viola os termos e pode levar à suspensão.
- **OpenBot,** `docs/provider-terms.md`: admite que a Anthropic "has not confirmed" o uso de login de assinatura pelo app.

## Decisão

| Provedor | Veredito | Uso no OpenBot |
|---|---|---|
| Claude (plano de consumidor) | ambíguo, com risco de bloqueio sem aviso; o OpenBot embute o SDK, o que o aproxima do caso proibido | **não usar**. Se quiser o Claude no OpenBot, usar chave de API (cobrada por uso) |
| ChatGPT/Codex (plano) | ambíguo, com tendência a permitido para uso pessoal local | permitido, só local e sem expor o servidor a terceiros |
| Gemini/Antigravity (conta pessoal) | proibido | **não usar** |

Fora do OpenBot nada muda: rodar as CLIs oficiais diretamente, inclusive com o MCP deste hub, é uso normal.

## Consequências

- Com assinatura, o OpenBot fica restrito ao Codex. Isso reduz o valor dele em relação a usar o Codex diretamente. Ver ADR 0005.
- Reavaliar se algum provedor publicar uma regra explícita.
