# Implementação e evidências — Story 6.1

Data: 28/10/2026 (America/Maceio). Estado: **review**, SPEC **in-review**.

## Escopo e decisões

Usei `bmad-build` exclusivamente para a Story 6.1, conforme autorização.
O candidato inicial da branch `epico-6-entrega-robustez-documentacao-e-opcionais`
foi confirmado externamente como `8a460d26bb280e5a35379254a82b73c3224813a1`.
Não atribuo essa confirmação ao usuário, não usei Git para verificá-la e não
deduzo publicação desse identificador.

Revalidei o inventário **runtime** do app real, com/sem SPA, antes de editar:
seis POST (login, logout, criação, depósito, lance e cancelamento), nenhum
PUT/PATCH/DELETE, sem problemas de política, `debug=False`. Execução exit 0.

Decidi centralizar CA1 em `test_csrf.py`, porque a sentinela no despacho da
rota real prova que dependências e handler não são alcançados. Cada caso tem
controle com headers válidos que alcança essa mesma sentinela. Descartei
espalhar complementos equivalentes entre quatro arquivos de integração;
preservei todas as provas autenticadas/transacionais existentes.

Não alterei produto, `conftest.py`, configuração, contratos de sessão/CSRF,
422, arquitetura ou infraestrutura de teste. Não criei rota de crash/debug.

## Evidência por critério

| Critério | Prova implementada/reaproveitada | Limite |
| --- | --- | --- |
| CA1 | `test_every_real_write_is_refused_before_route_dispatch`: seis rotas × três negativos × com/sem SPA; inventário bruto via `http_write_inventory(app.routes)` confrontado com W1–W6 antes das checagens separadas `policy_problems`/`policy_by_route`. Corpo em bytes, header efetivo, envelope completo, nenhuma chamada ao despacho, nenhum Set-Cookie/CORS. Controle positivo da sentinela em cada caso; provas autenticadas/transacionais preservadas. Regressões da correção R6.1-01 abaixo. | A implementação original derivava escritas do mapa de políticas e perdeu esta garantia no review. A correção exige discrepância para a sétima escrita sem política, inclusive nos caminhos documentais. |
| CA2 automatizado/local | `test_config.py`, `integration/test_auth_flow.py`, `test_csrf_auth.py` e `test_csrf.py`: `__Host-auction_session`, HttpOnly, Secure, SameSite=Lax, Path=/, sem Domain; logout coerente; sem CORS permissivo. | Não prova cookie emitido pelo deploy nem borda/proxy. |
| CA3 backend | Vitrine/detalhe com status 200 explícito antes de comparar bytes. Sala usa lote com lance persistido, REST 200 e snapshot WS real equivalente (exceto `as_of`), ping/pong, uma query no recorte WS, Session encerrada, privacidade e banco intacto; transporte ConnectError instalado, zero requests de negócio e controle do proxy 503 com uma request. Auditoria/comprovante conservam provas PostgreSQL com cliente AIC sem capacidades. | Lotes já persistidos; busca/criação externas podem falhar. Q7 não foi reaberta. |
| CA3 navegador | Casos existentes de imagem quebrada preservam vitrine/título/valor/navegação, sala/ficha/valor/estado/histórico. Comprovante a 320/1280 px mantém artista, alias, valor, data, bid_count, hash e link; placeholder e request de mídia contada; navegação chega à auditoria íntegra com histórico e sem imagem. | Playwright usa API simulada; complementa ASGI/PostgreSQL, não é E2E publicado. |
| CA4 | Três testes existentes de erro inesperado/response validation/middleware exigem igualdade do envelope 500 literal. Sentinelas fictícias de SQL/caminho/segredo/tipo/stack não aparecem. App real com/sem SPA tem debug falso e inventário sem sintéticas. Falhas reais de commit/criação/lance já cobertas são preservadas. | Resposta pública; não alego auditoria completa dos logs. |

## Execução original — anterior à correção R6.1-01

Executei em cópia isolada das fontes permitidas, sem `.env*`, credenciais ou
Git, com dependências locais reaproveitadas, variáveis locais fictícias e
PostgreSQL `_test`. Conferi correspondência SHA-256 dos arquivos copiados.
Preservei o runtime histórico da 4.2 e usei o runtime exclusivo da 6.1
explicitamente autorizado; detalhes temporários ficaram fora da SPEC.

A tentativa inicial de focal no sandbox terminou em exit 2 antes do pytest:
`uv` não conseguiu criar lock no cache. A reexecução autorizada fora do
sandbox iniciou o pytest; não houve correção de produto por esse incidente.

Comandos executados em `backend/` da cópia isolada:

```sh
uv run pytest tests/test_csrf.py tests/test_csrf_auth.py tests/test_access_policy.py tests/test_errors.py tests/test_config.py tests/test_security.py tests/integration/test_auth_flow.py tests/integration/test_roles.py
uv run pytest tests/integration/test_lot_creation.py tests/integration/test_wallet_routes.py tests/integration/test_bid_routes.py tests/integration/test_lot_cancellation.py
uv run pytest tests/integration/test_public_lots.py tests/integration/test_bid_reads.py tests/integration/test_lot_room_ws.py tests/integration/test_lot_audit.py tests/integration/test_lot_receipt.py tests/test_artic.py tests/test_catalog_image_route.py
```

| Execução | Resultado real | Exit code |
| --- | --- | --- |
| Focal 1 — segurança/sessão/erros/papéis | 477 passed, 12.04 s | 0 |
| Focal 2 — escritas e efeitos transacionais | 197 passed, 31.80 s | 0 |
| Focal 3 — leituras locais/WS/AIC/auditoria/comprovante | 234 passed, 20.88 s | 0 |
| Playwright focal — vitrine/sala/WS/auditoria/comprovante | 115 passed, 12.4 s | 0 |
| Gate `./verify.sh` | Todas as etapas passaram; 2314 pytest, 192 Node | 0 |

Cada grupo de pytest emitiu um `StarletteDeprecationWarning` existente. Não alterei
dependências por esse aviso. Nenhum defeito de produto foi revelado por esses
focais. Na pasta `frontend/`, executei:

```sh
npm run test:e2e -- e2e/vitrine.spec.ts e2e/lot-room.spec.ts e2e/lot-room-ws.spec.ts e2e/audit.spec.ts e2e/receipt.spec.ts
```

O browser emitiu avisos de `NO_COLOR`/`FORCE_COLOR` e `ECONNREFUSED` no proxy
Vite para o backend local sem stack real; a suíte usa API simulada e todos os
115 casos passaram. Não interpreto essa execução como stack real ou deploy.
Na raiz da cópia isolada executei **`./verify.sh`**, com exit 0 e saída final
literal `verify.sh: todas as etapas passaram.`:

- Ruff check aprovado; Ruff format: 110 arquivos conformes.
- Docker/Compose e PostgreSQL saudáveis.
- Pytest: **2314 passed**, um warning, **148.98 s**.
- ESLint e TypeScript aprovados.
- Node: **192 passed**, zero falhas e zero skips.
- Vite: 80 módulos; build de produção aprovado.
- Docker build aprovado, com reutilização de camadas em cache.

Não executei também `VERIFY_E2E=1` por rotina, pois os 115 casos focais de
browser já atendem a spec. A suíte opt-in `real-stack.spec.ts` não foi executada.
As 250 fontes permitidas foram reconferidas por SHA-256 após focais/browser
e novamente após o verify;
nenhum código ou teste mudou depois da cópia validada. As alterações finais
são apenas documentação e status.

Não houve finding de produto que justificasse correção: os contratos atuais
passaram. A única interrupção de execução foi o lock de cache no sandbox,
resolvido por reexecução autorizada. Avisos de ferramentas foram registrados
acima, sem ampliar o escopo.

Depois do gate, restaurei o bind mount local do PostgreSQL, que o Compose da
cópia isolada havia recriado, preservando o volume. Na raiz original executei:

```sh
COMPOSE_DISABLE_ENV_FILE=1 docker compose -p casa-de-leiloes -f compose.yaml --env-file /dev/null up -d --wait postgres
```

Exit 0, PostgreSQL `Healthy`, sem leitura de dotenv ou mudança de fontes.
Essa restauração do ambiente local não é deploy.

## Arquivos alterados

- `backend/tests/test_csrf.py`
- `backend/tests/test_access_policy.py`
- `backend/tests/test_errors.py`
- `backend/tests/integration/test_lot_room_ws.py`
- `backend/tests/integration/test_public_lots.py`
- `frontend/e2e/vitrine.spec.ts`
- `frontend/e2e/receipt.spec.ts`
- `SPEC.md`, `security-audit.md` e este registro da 6.1
- `_bmad-output/implementation-artifacts/6-1-revisão-de-segurança-e-de-erros.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/uso_de_ia.md`

## Pendências públicas e encerramento

Continuam pendentes: cookie realmente emitido pelo deploy, aceitação/envio
pelo navegador publicado, logout real, borda/proxy, CORS/preflight publicado
e identidade do commit efetivamente implantado. Preservo a matriz pública de
`security-audit.md` §7 e os gates de `docs/FECHAMENTO-DE-EPICO.md`.

Não fiz deploy nem aleguei publicação do candidato. Encaminhei a implementação
para **review independente** após os gates; CA2 publicado continua pendente.
Story/sprint estão em **review**, SPEC em **in-review**, Épico 6 em
**in-progress**. Não marquei done, não iniciei 6.2 e não executei code review
nesta sessão.

## Correção do implementador — R6.1-01 — 28/10/2026

Usei exclusivamente `bmad-build` para esta correção autorizada, com delegação
da implementação de `test_csrf.py` conforme o workflow. Decidi separar a
descoberta de escrita da validação de política; descartei alterar a exceção
documental por nome ou código de produção. O review independente permanece
histórico: este registro não é re-review nem aprovação do finding.

**Causa raiz confirmada:** a matriz derivava o observado de `policy_by_route`,
que só retorna rotas com política válida e dependência efetiva. O complemento
`policy_problems` tolera `/api/docs` e `/api/openapi.json` por caminho. Logo,
um POST sem política nesses caminhos era omitido das duas provas: o review
executou a matriz com sete escritas e os 36 casos passaram indevidamente.

Agora `http_write_inventory` percorre `app.routes` usando `APIRoute`/`Route`,
`.methods` e `.path`, sem consultar política, lista esperada ou allowlist.
Percorro `Mount.routes` com prefixos; recuso Mount opaco, tipo desconhecido,
métodos ausentes/vazios, métodos não suportados e duplicata método/caminho.
Ignoro WebSockets conhecidos e métodos seguros. As interfaces públicas são
descritas na [documentação Starlette](https://starlette.dev/routing/) e na
[referência FastAPI](https://fastapi.tiangolo.com/reference/apirouter/).
`assert_real_write_inventory` compara o observado com a lista W1–W6 existente;
somente depois a matriz confere `policy_problems` e `policy_by_route`.

O app atual, com e sem SPA, conserva exatamente POST login, logout, criação,
depósito, lance e cancelamento listados em W1–W6; nenhum PUT/PATCH/DELETE.
Preservei os 36 negativos e seus controles positivos no despacho real.

**Regressão obrigatória:**
`test_write_inventory_rejects_unprotected_real_app_mutations` registra uma
sétima escrita somente no app descartável: três caminhos (`/api/docs`,
`/api/openapi.json`, `/api/unexpected`) × `Route`/`APIRoute` × com/sem SPA.
Nos 12 casos, exige inventário bruto igual às seis anteriores mais a nova
escrita, ausência dela no mapa de políticas e `AssertionError` na mesma
validação CA1 usada pela matriz. Nos caminhos documentais, demonstra inclusive
que `policy_problems` ainda retorna lista vazia; isso não impede a descoberta
bruta nem a reprovação. Não adicionei mutações às rotas de produção.

As outras regressões comprovam descoberta com metadata inválida/dependência
incorreta, todos os quatro métodos em rota única, exclusão de métodos seguros
e WebSocket, prefixos de Mount, superfícies opacas e duplicatas. Nenhuma
mudança em `tests/access_policy.py`, `test_access_policy.py`, produção,
`conftest.py`, configuração, frontend ou E2E.

Invalidei a evidência anterior pertinente a CA1 e renovei os focais no candidato
corrigido. Preservei a evidência Playwright de CA3: o escopo desta correção
ficou estritamente no inventário backend. Usei nova cópia isolada sem dotenv
ou credenciais, dependências locais e PostgreSQL `_test`; conferi SHA-256 das
250 fontes permitidas antes do focal. Preservei as baselines anteriores.

Comandos realmente executados, nesta ordem, em `backend/` da cópia isolada:

```sh
uv run pytest tests/test_csrf.py -k write_inventory
uv run pytest tests/test_csrf.py tests/test_access_policy.py tests/test_csrf_auth.py tests/integration/test_lot_creation.py tests/integration/test_wallet_routes.py tests/integration/test_bid_routes.py tests/integration/test_lot_cancellation.py
```

Saídas finais literais, ambos exit 0:

```text
================ 29 passed, 256 deselected, 1 warning in 0.34s =================
VALIDATION_EXIT_CODE=0
======================= 533 passed, 1 warning in 34.29s ========================
VALIDATION_EXIT_CODE=0
```

Depois dos focais verdes executei **`./verify.sh` completo**, na raiz da cópia
isolada, com **exit 0**. O script é idêntico ao da raiz original; não alterei
configuração ou `conftest.py` para executá-lo. Saída real pertinente:

```text
=== Backend: Ruff check ===
All checks passed!
=== Backend: Ruff format --check ===
110 files already formatted
=== Infra: Docker e PostgreSQL ===
 Container casa-de-leiloes-postgres-1 Healthy
=== Backend: pytest ===
================= 2343 passed, 1 warning in 138.38s (0:02:18) ==================
=== Frontend: lint ===
=== Frontend: typecheck ===
=== Frontend: test ===
ℹ tests 192
ℹ pass 192
ℹ fail 0
ℹ skipped 0
=== Frontend: build ===
✓ 80 modules transformed.
✓ built in 81ms
=== Imagem: docker build ===
#25 DONE 0.0s
verify.sh: todas as etapas passaram.
VALIDATION_EXIT_CODE=0
```

ESLint, TypeScript, build Vite e Docker terminaram sem falha. O warning
Starlette/httpx já existente apareceu nos focais e no gate; não alterei
dependências por ele. Não encontrei comportamento inesperado de produto.

O Compose da cópia recriou o contêiner local por causa do caminho do bind
mount. Após o gate restaurei o mount original, preservando o volume, na raiz:

```sh
COMPOSE_DISABLE_ENV_FILE=1 docker compose -p casa-de-leiloes -f compose.yaml --env-file /dev/null up -d --wait postgres
```

Resultado: exit 0, `Container casa-de-leiloes-postgres-1 Healthy`. Não é deploy.
Reconferi as 250 fontes permitidas da raiz e da cópia pelos hashes do candidato
testado: zero divergências. Somente `test_csrf.py` mudou entre as fontes de
execução desta correção; nenhuma mudança em produção/frontend/CA3/CA4.

Arquivos alterados nesta correção, além dos registros locais de execução BMAD:

- `backend/tests/test_csrf.py`
- `SPEC.md`, `security-audit.md` e este `implementation-evidence.md`
- `_bmad-output/implementation-artifacts/6-1-revisão-de-segurança-e-de-erros.md`
- `_bmad-output/implementation-artifacts/code-review-story-6-1.md`, somente no adendo do implementador
- `docs/uso_de_ia.md`

Não identifiquei alteração fora da lista prevista nem arquivo de segredo
alterado na conferência por nomes. Não reescrevi os comandos históricos do
review nem as baselines anteriores. **R6.1-01 corrigido pelo implementador,
aguardando re-review independente**; não declaro aprovação do reviewer.
Story/sprint continuam **review**, SPEC **in-review**, Épico 6 **in-progress**
e CA2 publicado pendente. Parei sem iniciar 6.2 ou executar code review.

Ocorrência de processo: antes de ler o anexo executei indevidamente
`git status --short`, contrariando a restrição do pedido; consulta somente de
leitura, sem alteração de arquivos. Registrei o ocorrido e não executei outro
comando Git/gh. Não houve leitura de `.env*`, credenciais ou valores de
segredos, cookies ou tokens reais.

## Extensão local CA1 — W7 da Story 6.2A — 29/10/2026

Decidi renovar a evidência CA1 afetada pelo POST /api/auth/register, sem alterar middleware nem CA2 publicado. Inventário bruto independente da política encontra sete escritas; expectativa histórica de seis falha; mutações agora acrescentam oitava inesperada e continuam reprovando, inclusive caminhos documentais. Matriz com/sem SPA cobre os três bloqueios antes do despacho. Integração PostgreSQL do cadastro comprova zero User/Wallet/cookie nos negativos e controle positivo no mesmo app/caminho. Políticas/OpenAPI/ausência de aliases atualizados sem enfraquecer descoberta.

Focais ampliados 589 passed, exit 0; gate final VERIFY_E2E=1 ./verify.sh exit 0, 2408 pytest/197 Node/317 Playwright aprovados e 7 real-stack opt-in ignorados. Smoke pertinente separado: três testes reais aprovados e duas carteiras zero confirmadas. Comandos, candidato/cópia, correções e limites em [evidência da 6.2A](../spec-story-6-2a-cadastro-de-usuarios/implementation-evidence.md).

A prova histórica de seis escritas não comprova o candidato com W7; esta extensão é evidência de implementação local, não re-review independente. 6.1 permanece review devido à pendência publicada; **CA2 publicado não foi alterado nem considerado aprovado**. Sem Git/deploy ou .env*.
