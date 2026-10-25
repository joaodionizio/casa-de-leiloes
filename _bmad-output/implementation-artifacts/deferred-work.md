# Trabalho adiado

## Deferred from: code review of 2-1-formato-de-erros-e-validacao-de-origin.md (24/10/2026)

- O `loc` do 422 pode ecoar chaves escolhidas pelo cliente em modelos `dict[str, ...]` ou `extra="forbid"`, e `details` não tem limite de itens. Inalcançável com as rotas atuais; mudar o conteúdo do `loc` exige rever a D1 da 2.1.
- `sprint-status.yaml` ainda registra `epic-1: in-progress` e a 1.4 como `review`. Pré-existente; fechar quando o épico 1 for formalmente encerrado.

## Deferred from: code review of 2-2-login-papéis-e-política-de-acesso.md (24/10/2026)

- Para a Story 4.1: `websocket_route` só funciona hoje com `AccessPolicy.PUBLIC`. Com `OPTIONAL`, `AUTHENTICATED` ou papel, as dependências esperam `Request` e a conexão quebra (`TypeError: require_user() missing 1 required positional argument: 'request'`, reproduzido no review). Decidir na 4.1 se `websocket_route` fica limitado a `PUBLIC` (recusando outra política no registro) ou se o WebSocket ganha um mecanismo de autenticação próprio.

## Deferred from: code review of 2-3-busca-de-obras-no-art-institute-of-chicago.md (24/10/2026)

- Chamadas repetidas de mídia à AIC (D1): a rota `GET /api/catalog/images/{image_id}` é pública, sem cache (`no-store`) e serve a imagem de 843 px também para as miniaturas. Uma busca com 20 resultados pode disparar até 20 chamadas ao IIIF, e a miniatura e a imagem grande da mesma obra usam a mesma URL. Não sei se a cota do IIIF é compartilhada com a da API (60 req/min por IP anônimo na documentação). Cache de navegador ou de servidor, miniatura menor e limite de requisições na nossa rota ficam fora da Story 2.3; decidir na 2.5 (vitrine pública usa as mesmas imagens), medindo o 429/503 real.
- A guarda de rede dos testes (`tests/conftest.py`, `socket.getaddrinfo`) não trata `HTTPS_PROXY`/`ALL_PROXY`: com um proxy no ambiente, um cliente httpx sem `MockTransport` poderia conectar ao proxy local em vez de resolver o host externo. LOW teórico, hoje inalcançável (os testes do catálogo injetam `MockTransport` e o teste do cliente padrão falha de forma visível); revisitar se algum teste passar a criar um cliente httpx real.

