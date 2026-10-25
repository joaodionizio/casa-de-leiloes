# Trabalho adiado

## Deferred from: code review of 2-1-formato-de-erros-e-validacao-de-origin.md (24/10/2026)

- O `loc` do 422 pode ecoar chaves escolhidas pelo cliente em modelos `dict[str, ...]` ou `extra="forbid"`, e `details` não tem limite de itens. Inalcançável com as rotas atuais; mudar o conteúdo do `loc` exige rever a D1 da 2.1.
- `sprint-status.yaml` ainda registra `epic-1: in-progress` e a 1.4 como `review`. Pré-existente; fechar quando o épico 1 for formalmente encerrado.

## Deferred from: code review of 2-2-login-papéis-e-política-de-acesso.md (24/10/2026)

- Para a Story 4.1: `websocket_route` só funciona hoje com `AccessPolicy.PUBLIC`. Com `OPTIONAL`, `AUTHENTICATED` ou papel, as dependências esperam `Request` e a conexão quebra (`TypeError: require_user() missing 1 required positional argument: 'request'`, reproduzido no review). Decidir na 4.1 se `websocket_route` fica limitado a `PUBLIC` (recusando outra política no registro) ou se o WebSocket ganha um mecanismo de autenticação próprio.

## Deferred from: code review of 2-3-busca-de-obras-no-art-institute-of-chicago.md (24/10/2026)

- Chamadas repetidas de mídia à AIC (D1): a rota `GET /api/catalog/images/{image_id}` é pública, sem cache (`no-store`) e serve a imagem de 843 px também para as miniaturas. Uma busca com 20 resultados pode disparar até 20 chamadas ao IIIF, e a miniatura e a imagem grande da mesma obra usam a mesma URL. Não sei se a cota do IIIF é compartilhada com a da API (60 req/min por IP anônimo na documentação). Cache de navegador ou de servidor, miniatura menor e limite de requisições na nossa rota ficam fora da Story 2.3; decidir na 2.5 (vitrine pública usa as mesmas imagens), medindo o 429/503 real.
- A guarda de rede dos testes (`tests/conftest.py`, `socket.getaddrinfo`) não trata `HTTPS_PROXY`/`ALL_PROXY`: com um proxy no ambiente, um cliente httpx sem `MockTransport` poderia conectar ao proxy local em vez de resolver o host externo. LOW teórico, hoje inalcançável (os testes do catálogo injetam `MockTransport` e o teste do cliente padrão falha de forma visível); revisitar se algum teste passar a criar um cliente httpx real.

## Deferred from: implementation of 2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado.md (24/10/2026)

- `Idempotency-Key` (P7): criar lote não tem idempotência no servidor. Um timeout depois do commit seguido de nova tentativa manual pode criar dois lotes da mesma obra; a interface manda conferir "Meus lotes" antes de repetir. Revisitar se o duplo envio aparecer na prática.
- Paginação de "Meus lotes" (A2): `GET /api/lots/mine` devolve todos os lotes do leiloeiro, sem limite. Aceitável na escala do desafio; com volume real, a resposta cresce e as miniaturas disparam muitas chamadas de mídia à AIC (D1 da 2.3). Paginar ou carregar sob demanda quando houver necessidade.
- Para a Story 2.5: registrar `GET /api/lots/{lot_id}` **depois** de `GET /api/lots/mine`; senão "mine" cai no parâmetro. `GET /api/lots` (público) também nasce lá; hoje responde 405.
- Para a Story 3.6: o predicado do demo aberto ganha `AND cancelled_at IS NULL` (`app/seed.py`, `seed_demo_lot`). Para a 4.4: o catch-up de fechamento entra antes do `run_seed` na inicialização.
- Testes automatizados de componentes do front-end: a 2.4 só testa lógica pura (`money.ts`, `lotTime.ts` e `lotDraft.ts`). Componentes (formulário, revisão, "Meus lotes") dependem do teste manual e do code review.
- O `loc` do 422 de `extra_forbidden` em `POST /api/lots` contém o nome da chave enviada pelo cliente (item já deferido na 2.1; aqui o corpo é um modelo com `extra="forbid"`).

## Deferred from: code review of 2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado.md (25/10/2026)

- `frontend-lot-creation.md` §1 (linha AD-6) ainda diz "nenhuma comparação com o relógio do navegador", contradizendo a revisão de 25/10/2026 no §5 (validação preventiva com `now` injetado). Corrigir na spec quando eu decidir. **Resolvido em 25/10/2026**, antes do fechamento da 2.4: decidi corrigir, a spec foi sincronizada (§1 e §5, `SPEC.md`, `decisions.md`) e o re-review final validou. Mantido aqui só como histórico.

