# Trabalho adiado

## Deferred from: code review of 2-1-formato-de-erros-e-validacao-de-origin.md (24/10/2026)

- O `loc` do 422 pode ecoar chaves escolhidas pelo cliente em modelos `dict[str, ...]` ou `extra="forbid"`, e `details` não tem limite de itens. Inalcançável com as rotas atuais; mudar o conteúdo do `loc` exige rever a D1 da 2.1.
- `sprint-status.yaml` ainda registra `epic-1: in-progress` e a 1.4 como `review`. Pré-existente; fechar quando o épico 1 for formalmente encerrado.

## Deferred from: code review of 2-2-login-papéis-e-política-de-acesso.md (24/10/2026)

- Para a Story 4.1: `websocket_route` só funciona hoje com `AccessPolicy.PUBLIC`. Com `OPTIONAL`, `AUTHENTICATED` ou papel, as dependências esperam `Request` e a conexão quebra (`TypeError: require_user() missing 1 required positional argument: 'request'`, reproduzido no review). Decidir na 4.1 se `websocket_route` fica limitado a `PUBLIC` (recusando outra política no registro) ou se o WebSocket ganha um mecanismo de autenticação próprio.
