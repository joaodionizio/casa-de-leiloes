# Auditoria e plano mínimo — Story 6.1

> Plano de preparação preservado abaixo. A implementação autorizada em
> 28/10/2026 usa a matriz CA1 centralizada, sem alterar `conftest.py` ou a
> configuração para dotenv; essas instruções posteriores substituem as
> propostas de distribuição dos testes e isolamento de §3/§6.
> Resultados reais e limites: [implementation-evidence.md](implementation-evidence.md).
>
> Correção autorizada R6.1-01: substituo a proposta de derivar escritas de
> `policy_by_route` por descoberta bruta das rotas HTTP registradas, antes e
> independentemente da validação de política. Não aplico exceções de caminho.

## 1. Fontes vivas, limites e estado atual

Li `CLAUDE.md`, `docs/ARQUITETURA.md` (especialmente AD-11/12/19/22/29 e Q7),
`docs/desafio-elite-dev.md`, a Story 6.1 de `epics.md`,
`docs/FECHAMENTO-DE-EPICO.md`, `deferred-work.md`, `code-review-epic-5.md` e
`sprint-status.yaml`. Para planejar as provas de navegador, também li DESIGN,
EXPERIENCE, VITRINE-BLUEPRINT e FRONTEND-WORKFLOW. Releio as fontes afetadas na
implementação: esta fotografia não as congela.

O sprint registra 6.1/Épico 6 em backlog; preservei esses estados. O review do
Épico 5 aprova integração e registra fechamento documental excepcional, sem
comprovar merge/deploy/smoke. O processo canônico ainda exige os gates reais.
Uso o candidato inicial `8a460d26bb280e5a35379254a82b73c3224813a1`, confirmado
externamente, como referência de início do Épico 6, sem atribuir a confirmação
ao usuário; a produção antiga documentada é
`3d3ea97`. Não confirmei branch, commits ou conteúdo publicado.

| Área inspecionada | Estado comprovável pela leitura do código |
| --- | --- |
| Montagem | `backend/app/main.py:create_app` registra handlers e `ApiWriteGuardMiddleware` antes das rotas; monta auth, catálogo, lotes, carteira, arremates, lances, auditoria, comprovante, cancelamento e sala. SPA é registrada por último. FastAPI usa debug falso por padrão, sem opção de debug no factory. |
| CSRF | `csrf.py` cobre POST/PUT/PATCH/DELETE em `/api` e `/api/…`, inclusive `root_path`. Origem configurada prevalece sobre Host/Forwarded. Origin presente tem precedência; sem ele usa Referer; ausência de ambos e duplicações são recusadas. Origem é checada antes do conteúdo/roteamento. |
| JSON | Exige exatamente um Content-Type cujo media type seja `application/json`; aceita charset e diferenças de caixa, recusa `+json`, formulários, texto e ausência. JSON malformado com header correto é 422 do parser, não 415 do guard. Logout e cancelamento não exigem payload, mas exigem o header; não passarei a obrigar `{}` nessas rotas. |
| Sessão/acesso | `auth.py`, `config.py`, `security.py` e `access.py`: Argon2id; JWT HS256 com 8 h; cookie HTTPS `__Host-auction_session`, Secure/HttpOnly/Lax/Path=/, sem Domain. HTTP só é aceito para hosts locais, com `auction_session` sem Secure. Políticas são dependências reais; usuário/papel são reconferidos no banco. Logout remove cookie, sem revogação do token copiado. |
| CORS | Não encontrei registro de middleware CORS no app. Os testes de métodos seguros/preflight e de auth conferem ausência de cabeçalhos `access-control-*`. Isso prova configuração/resposta local, não configuração de um proxy publicado. |
| AIC e mídia | `artic.py` usa destinos fixos, timeouts, sem redirects, ID validado, teto e assinatura JPEG. `catalog.py` converte indisponibilidade em 503 `catalog_unavailable`; imagem é pública, same-origin e `no-store`. Bytes ficam em memória durante a resposta; não há cache persistente. |
| Vitrine/detalhe | GET `/api/lots` e `/api/lots/{lot_id}` leem snapshots locais em `lots.py`; `image_url_for` só compõe a URL, sem acessar a AIC. `VitrinePage.tsx`/`LotPage.tsx` consomem a API local. A criação de novos lotes e a busca de obras continuam dependendo da AIC, conforme o desenho vigente. |
| Sala | `bids.py:read_public_room` lê estado/histórico local. `lot_room.py:read_room` usa Session curta em threadpool e o mesmo read model para o snapshot WS. A sala usa GET `/api/lots/{lot_id}/bids` e `/ws/lots/{lot_id}`; comandos continuam no POST. |
| Auditoria | `lot_audit.py` usa um statement local com lote/bids/settlement/receipt, valida cadeia/âncora e projeta só campos públicos. `AuditPage.tsx` mostra dados e integridade; não contém imagem nem campo image_url. Não acrescentarei imagem para satisfazer um fallback inexistente nessa tela. |
| Comprovante | `lot_receipt.py` lê receipt persistido e reutiliza verificação local; retorna pseudônimo/valor/data/contagem/hash, sem ID privado/HMAC. `ReceiptPage.tsx` usa `ArtworkImage`; link público é `/lots/{lot_id}/receipt`, API `/api/lots/{lot_id}/receipt`. |
| Placeholder | `ArtworkImage.tsx` troca o src para `/artwork-placeholder.svg` no onError; texto/dados são renderizados separadamente. A mídia falhar não condiciona leitura de negócio. |
| Leituras/erros | Leituras não chamam settlement; auditoria/comprovante usam autoflush desativado e rollback. `errors.py` registra handlers de HTTP, validação e Exception; o 500 usa mensagem fixa, sem texto da exceção. Stack pode ir ao log do servidor pelo mecanismo existente, nunca ao corpo público. |

Não identifiquei defeito funcional que justifique alterar código de produto com
base nesta inspeção estática. Identifiquei lacunas de prova abaixo; isso não é
declaração de suíte verde nem certificação geral de segurança.

Trato previsões antigas de `deferred-work.md` como histórico: catch-up antes do
seed e settlement disparado por POST foram superados pela AD-19 atual e pelo
código. Preservo `migrations → seed → lifespan/catch-up → scheduler → tráfego`.
Não reabro Q10 por textos históricos: as rotas públicas do comprovante já estão
implementadas. Dívidas de cache/429, rede via proxy nos testes, idempotência,
rotação, timeouts/capacidade e `loc` do 422 não ganham escopo automaticamente.

## 2. Matriz dos quatro critérios de aceite

| Critério da Story 6.1 | Prova atual | Lacuna e entrega mínima planejada | Limite do aceite |
| --- | --- | --- | --- |
| CA1 — Toda escrita rejeita Origin divergente e conteúdo não JSON | Middleware global, testes sintéticos dos quatro métodos e provas específicas das seis escritas reais | Completar Content-Type ausente para criação, depósito e lance; não JSON para cancelamento. Confrontar inventário runtime com o mapa das provas, conforme §3. | 403 de papel, 404/405 ou 422 de payload não substituem a prova CSRF. |
| CA2 — Cookie no deploy e ausência de CORS permissivo | Testes de config HTTPS/local, login/logout com PostgreSQL e negativas de CORS | Reexecutar provas existentes; registrar inspeção publicada do candidato conforme §7. Não há defeito local demonstrado que exija nova implementação de sessão/CORS. | **Parte publicada pendente.** Nenhuma observação de produção foi feita nesta sessão. |
| CA3 — AIC indisponível preserva vitrine/sala/auditoria/comprovante; mídia usa placeholder | Vitrine compara transportes saudável/falho; auditoria e receipt passam com cliente sem capacidades; proxy testa falhas; Playwright cobre vitrine/detalhe com imagem 503 | Completar sala REST/WS sob falha explícita e controle de proxy; ampliar casos existentes de navegador para conteúdo da sala e placeholder no comprovante (§4). | Provas de banco/ASGI e UI simulada são complementares; não equivalem a E2E publicado. |
| CA4 — Erro inesperado produz 500 genérico sem stack | `test_errors.py` e falhas injetadas em rotas reais de criação/lance, com corpo genérico e sentinelas privadas ausentes | Reutilizar os testes; reforçar asserções locais de corpo exato, debug falso e ausência de rotas sintéticas, sem endpoint novo (§5). | Não forçar falha real nem expor segredos no deploy. |

## 3. Inventário completo de escritas e evidência por rota

Derivei a lista dos registradores chamados por `main.py` e dos decorators
`api_route`, incluindo `access.py` e `spa.py`; uma extração AST somente leitura
confirmou **seis POST, zero PUT, zero PATCH, zero DELETE**. Não importei a app
nem carreguei `.env*`. Os testes planejados confrontarão também `app.routes`
em runtime, com e sem SPA, usando configuração fictícia de teste.

| ID | Rota real e política | Registro | Origin divergente + JSON → 403 `csrf_origin_mismatch` | Origin válido + sem Content-Type → 415 | Origin válido + Content-Type não JSON → 415 |
| --- | --- | --- | --- | --- | --- |
| W1 | POST `/api/auth/login` — PUBLIC | `auth.py:44` | Existente: `test_csrf_auth.py::test_foreign_or_missing_origin_is_403` | Existente: `test_without_json_content_type_is_415`, parâmetro None | Mesmo teste, parâmetros text/plain e application/x-www-form-urlencoded |
| W2 | POST `/api/auth/logout` — PUBLIC | `auth.py:86` | Mesmo teste de origem, parâmetro LOGOUT | Mesmo teste de tipo, parâmetro LOGOUT/None | Mesmo teste, LOGOUT/text/plain e formulário |
| W3 | POST `/api/lots` — AUCTIONEER | `lots.py:784` | Existente: `integration/test_lot_creation.py::test_foreign_origin_missing_origin_and_non_json_never_reach_the_handler` | **Complementar no teste existente** | Existente: text/plain; preservar |
| W4 | POST `/api/wallet/deposit` — BIDDER | `wallet.py:202` | Existente: `integration/test_wallet_routes.py::test_foreign_origin_missing_origin_and_non_json_never_reach_the_handler` | **Complementar no teste existente** | Existente: text/plain; preservar |
| W5 | POST `/api/lots/{lot_id}/bids` — BIDDER | `bids.py:742` | Existente: `integration/test_bid_routes.py::test_csrf_protection_runs_before_the_handler` | **Complementar no teste existente** | Existente: application/x-www-form-urlencoded; preservar |
| W6 | POST `/api/lots/{lot_id}/cancel` — AUCTIONEER | `lot_cancellation.py:118` | Existente: `integration/test_lot_cancellation.py::test_csrf_guard_is_inherited_without_a_body` | Existente: no_content_type | **Complementar no teste existente**, enviando bytes com text/plain |

Para todas as células 415, exigir `code=unsupported_media_type` e envelope do
catálogo, não somente status. Não conto ausência de **Origin** como ausência de
**Content-Type**: são verificações diferentes. Não uso `json=` ao construir o
caso sem Content-Type, pois httpx o adiciona; envio bytes por `content=` e
confiro o header efetivamente enviado. Os casos não JSON usam corpo presente.

Os testes específicos mantêm sessão válida do papel autorizado e lote existente
quando necessário, com controles positivos já existentes: login válido, logout
204, criação 201, depósito aceito, lance 201 e cancelamento aceito. Nas recusas,
preservo asserções de banco inalterado, nenhuma chamada AIC e nenhum cookie
emitido/removido, conforme a rota. Prova antes de autenticação/banco pode usar
dependência que falha se executada, em complemento às provas transacionais.

Planejo aproveitar `test_csrf.py` para acrescentar um confronto enxuto entre
as escritas descobertas no app real e um mapa W1–W6 das provas específicas
acima. O confronto usa método/caminho, enumera todos os métodos de cada rota e
recusa tipo/Mount não inspecionável, sem ignorar exceções silenciosamente.
Na correção R6.1-01, uso os tipos HTTP e métodos públicos das rotas reais para
descobrir escritas; reservo `policy_problems`/`policy_by_route`, em
`tests/access_policy.py`, exclusivamente à conferência de políticas. Descartei
derivar o observado do mapa de políticas: isso excluía a própria rota sem
política que a prova deveria detectar. O teste falha se
uma nova escrita não estiver associada às provas de origem e dos dois casos de
Content-Type. O mapa é rastreabilidade; a execução dos testes referenciados é
que comprova cada recusa. Não acrescento outra suíte completa das mesmas
requisições nem simulo PUT/PATCH/DELETE como se estivessem registrados.

Cobertura transversal existente a preservar:

- `test_csrf.py`: Origin/Referer, precedência, headers duplicados, Host/Forwarded, charset/caixa, `+json`, body vazio, JSON exigido, `root_path`, métodos seguros e guard antes do roteador.
- `test_real_app_has_no_write_route_outside_api`: app com SPA sem escrita escapando de `/api`; fallback real aceita somente GET/HEAD.
- `test_access_policy.py`: inventário exato com/sem SPA e dependência efetiva da política; reprova tipo desconhecido e endpoints reaproveitados sem proteção.

Inspecionei todos os outros registradores HTTP: `catalog.py` tem três GET;
`lots.py`, além do POST, tem GET mine/lista/detalhe; `wallet.py`, GET da carteira;
`my_wins.py`, GET `/api/me/wins`; `bids.py`, GET público e GET mine;
`lot_audit.py` e `lot_receipt.py`, GET públicos; `auth.py`, GET `/api/me`;
`main.py`, GET `/health`; `spa.py`, GET/HEAD `/{full_path:path}`. O framework
registra documentação/OpenAPI em GET/HEAD. `register_room_routes` registra
WebSocket, não escrita HTTP. Não há rota de registro de usuário, refresh,
settlement, crash ou debug no produto atual.

## 4. AIC indisponível: prova mínima dos fluxos

Q7 está **resolvida**, conforme AD-23 e Story 2.3:
`backend/scripts/smoke_artic.py:check_unavailable` aponta o cliente para
`http://127.0.0.1:9` e exige `CatalogUnavailable(connect)`. O script também faz
chamadas reais nos outros itens e fica fora do verify. Não o executo nesta
especificação nem o acrescento ao gate offline.

A prova adicional da 6.1 é diferente: preciso demonstrar que os consumidores
dos snapshots locais, inclusive os fluxos dos Épicos 4/5, continuam atendidos.
Somente testar a exceção de `ArticClient` não demonstra isso.

| Fluxo | Prova existente aproveitada | Complemento mínimo planejado e resultado exigido |
| --- | --- | --- |
| Vitrine/detalhe | `integration/test_public_lots.py::test_public_reads_never_touch_the_catalog_client` compara bytes com FakeArtic saudável/falho, relógio fixo e zero requests; teste seguinte exclui dependência do catálogo. Testes de pureza preservam dados em todas as fases. | Preservar o cenário; explicitar status 200 das respostas comparadas se necessário para impedir igualdade entre duas falhas. Reutilizar Playwright `vitrine.spec.ts`, grupo imagem quebrada: placeholder, título, ficha, valores e navegação. |
| Sala REST/WS | `test_bid_reads.py` cobre contrato/histórico/pureza; `integration/test_lot_room_ws.py::test_public_real_snapshot_is_one_pure_query_and_closes_session` cobre snapshot real, privacidade, threadpool, ping/pong e banco inalterado. | Ampliar esse teste existente com `ArticClient` real instalado via `FakeArtic`/`httpx.MockTransport` que levanta ConnectError. Usar lote local válido com histórico, GET detalhe e GET bids 200, snapshot WS correto e ping/pong funcional, sem chamadas externas de negócio. Preservar o recorte de contagem SQL do snapshot; não misturar queries REST nessa contagem. |
| Auditoria pública | `integration/test_lot_audit.py::test_complete_history_public_projection_and_persisted_aliases` usa `app.state.artic_client=object()` e valida histórico real completo, aliases e hash; `test_public_state_matrix_and_read_purity` cobre fases/settlement. `audit.spec.ts` cobre acesso anônimo, histórico e resultado. | Nenhum teste novo para repetir essa independência: a ausência de capacidades externas já é prova mais forte que um retorno saudável. Manter os testes e confirmar zero dependência de mídia: a tela atual não pede imagem. |
| Comprovante público | `integration/test_lot_receipt.py::test_sold_public_receipt_is_persisted_private_and_read_only` usa cliente sem capacidades e compara campos do receipt persistido, sem dados privados e sem escrita. | Ampliar o caso público existente em `frontend/e2e/receipt.spec.ts`: `images: 'broken'`, src do placeholder local e mensagem de imagem indisponível; manter título/artista, alias, valor, data, contagem/hash e link para auditoria utilizáveis. Não criar uma cópia da suíte de receipt. |
| Proxy e ligação da falha | `test_artic.py` cobre timeout/erro de conexão/status; `test_catalog_image_route.py::test_upstream_failures_are_503_catalog_unavailable` cobre o caminho HTTP do proxy e envelope sanitizado. | No mesmo cenário ampliado da sala, depois das leituras de negócio e da asserção de zero requests, pedir a imagem pelo proxy com o mesmo transporte falho e exigir 503 `catalog_unavailable`, com request contabilizado. Isso prova que a falha injetada estava ativa; nenhum acesso real à rede. Não repetir a matriz de falhas do cliente/proxy. |

Os testes usam fixtures locais de lotes/lances e, para receipt/audit, settlement
persistido pelos helpers existentes (`settlement_support`). Não criam dados
por consulta real à AIC nem mockam o resultado de negócio das rotas sob teste.
WebSocket usa o engine de teste pela substituição já existente de
`lot_room.get_engine`; não substituo `read_room` por payload inventado nessa
prova. O scheduler é controlado pela fixture existente, para não liquidar
durante leitura; não introduzo flag de produto para desativá-lo.

Completo o caso existente de detalhe com imagem quebrada em `vitrine.spec.ts`
com histórico local simulado não vazio e asserções de valor/estado/histórico
preservados na sala. Não repito matrizes de responsividade ou todos os cenários
de lance. Auditoria continua com seus testes de navegação/conteúdo atuais;
não invento placeholder onde não existe mídia.

Componho a evidência em duas camadas: PostgreSQL/ASGI real prova origem dos dados
e ausência de dependência externa; Playwright com API simulada prova o onError
e preservação do conteúdo no browser. Declaro essa separação no registro de
resultados. Descartei um novo E2E completo contra stack real, porque as duas
camadas existentes conseguem provar os contratos exigidos sem novo harness.

"Somente a mídia degrada" vale para os quatro fluxos de lotes **já criados**.
A busca/detalhe de obras externas e a criação de novo lote podem retornar 503
quando dependem da AIC; não prometo catálogo offline nem novas criações offline.

## 5. Cookie, CORS e erro 500: evidências reaproveitadas

| Evidência automatizada existente | O que efetivamente demonstra |
| --- | --- |
| `test_config.py::test_https_origin_uses_the_host_prefixed_secure_cookie` e testes local HTTP/remote HTTP | Nome/Secure derivados de APP_ORIGIN; HTTP remoto é recusado. |
| `integration/test_auth_flow.py::test_valid_login_returns_the_user_and_the_session_cookie` | Login HTTPS emite HttpOnly/Secure/Lax/Path=/, sem Domain, `__Host-` e max-age 28800. O mesmo teste diferencia desenvolvimento HTTP. |
| `test_logout_deletes_the_cookie_with_the_same_attributes_and_ends_the_session` | Logout mantém atributos ao apagar cookie; sessão do navegador termina. O teste de token copiado preserva a limitação até exp. |
| `test_csrf_auth.py::test_no_cors_headers_even_on_a_preflight_style_request`, `assert_no_session_effects` e `test_csrf.py::test_safe_methods_are_never_refused_by_the_guard` | Sem cabeçalhos permissivos nas respostas negativas/preflight locais; nenhuma abertura implícita de CORS. |
| `test_security.py`, `test_access_policy.py` e `integration/test_roles.py` | Argon2id/JWT/papéis/dependências; regressões pertinentes, sem novo mecanismo de auth. |
| `test_errors.py::test_unexpected_error_is_a_generic_500` | 500 JSON genérico, sem RuntimeError, sentinela privada, Traceback, caminho ou SELECT. |
| `test_invalid_response_is_a_500_not_a_422` e `test_failure_inside_the_guard_is_the_contract_500` | Sanitização também para validação de resposta e exceção no middleware. |
| `integration/test_lot_creation.py::test_a_failure_at_commit_leaves_no_row_and_a_generic_500` e `test_bid_routes.py` nos casos de atomicidade | Rotas reais produzem corpo exato e genérico sob falhas injetadas, sem sentinela privada nem gravação parcial. |

O contrato público inesperado é exatamente:

```json
{"status":500,"code":"internal_error","message":"Erro interno. Tente novamente mais tarde."}
```

Planejo reforçar os testes existentes de 500 com igualdade do envelope completo
onde hoje só há verificação parcial. Confirmo `debug is False` no app criado
pelo factory e ausência das rotas `/api/test/*` no inventário real, com e sem
SPA. As rotas sintéticas de `tests/synthetic_api.py` continuam exclusivamente
no ambiente de testes; falhas de rotas reais são injetadas por monkeypatch.
Sentinelas usadas nos erros são fictícias; não leio segredos reais para testar
ausência deles. Não crio endpoint, flag de crash nem modo de debug de produção.

Não altero a política atual de logs/observabilidade nem o contrato do 422 para
tratar dívidas que exigiriam outra decisão. A ausência de stack/secrets aqui
é uma propriedade da **resposta ao cliente**, sem alegar auditoria total dos logs.

## 6. Arquivos prováveis, execução mínima e testes direcionados

| Arquivo | Alteração provável, somente se necessária à prova |
| --- | --- |
| `backend/tests/conftest.py` | Isolamento estritamente de teste para impedir leitura de dotenv antes de `pytest_sessionstart` e dos consumidores de configuração, se ainda necessário; usar variáveis fictícias, sem alterar configuração de produção. |
| `backend/tests/test_csrf.py` | Confronto runtime entre escritas reais e mapa de evidências por rota, com/sem SPA, reaproveitando os verificadores existentes. |
| `backend/tests/integration/test_lot_creation.py` | Caso Content-Type ausente; preservar negativos existentes e ausência de efeitos/AIC. |
| `backend/tests/integration/test_wallet_routes.py` | Caso Content-Type ausente; preservar saldo. |
| `backend/tests/integration/test_bid_routes.py` | Caso Content-Type ausente e envelope 415; preservar lote/bids/carteiras e prova sem trava. |
| `backend/tests/integration/test_lot_cancellation.py` | Content-Type não JSON com bytes; reforçar envelopes dos casos atuais sem efeitos. |
| `backend/tests/integration/test_lot_room_ws.py` | Ampliar snapshot real com falha AIC instalada, detalhe/sala REST e controle de mídia 503; manter privacidade/pureza. |
| `backend/tests/integration/test_public_lots.py` | Apenas reforço de status 200 no teste de independência existente, se necessário. |
| `backend/tests/test_errors.py`, `backend/tests/test_access_policy.py` | Asserções adicionais de envelope/debug/ausência de rotas sintéticas nos testes atuais; sem duplicar cenários de falha. |
| `frontend/e2e/vitrine.spec.ts`, `frontend/e2e/receipt.spec.ts` | Ampliar casos existentes de imagem quebrada para conteúdo da sala e fallback do comprovante. Sem CSS/JSX novo. |
| Spec/evidência da 6.1 e `docs/uso_de_ia.md` | Registrar plano, execução real, limitações e inspeção publicada pendente. Sprint só muda na fase autorizada e conforme evidências. |

Não há arquivo de produto previamente indicado para mudança. `main.py`,
`csrf.py`, `errors.py`, `access.py`, `auth.py`, `config.py`, `security.py`,
`artic.py`, `catalog.py`, read models e componentes são pontos de conferência,
não uma lista autorizada de refatoração. Helpers de teste já existem; não
planejo adicionar framework ou arquivo novo de suíte sem necessidade.

Plano mínimo para a fase de implementação, quando autorizada:

1. Revalidar fontes/código/inventário e cobertura existentes; interromper se surgir escolha humana necessária.
2. Completar somente as células ausentes de CA1 e o confronto do inventário. Manter os negativos já eficazes, sem uma segunda suíte dos seis POST.
3. Ampliar as provas existentes de sala e fallback no browser; reutilizar as provas de vitrine, auditoria, receipt e proxy indicadas em §4.
4. Reforçar asserções de 500/configuração, sem código de crash/debug; corrigir produto somente se teste revelar violação concreta das decisões vigentes.
5. Executar focais, Playwright pertinente e gate final; registrar saída/exit code reais, arquivos efetivamente afetados e pendências públicas. Parar na 6.1.

Comandos planejados, **não executados nesta especificação**. Executar na pasta
`backend/`, usando o mesmo ambiente local fictício de banco/origem do verify,
PostgreSQL `_test` isolado, guardas atuais e sem carregar `.env*`:

```sh
uv run pytest tests/test_csrf.py tests/test_csrf_auth.py tests/test_access_policy.py tests/test_errors.py tests/test_config.py tests/test_security.py tests/integration/test_auth_flow.py tests/integration/test_roles.py
uv run pytest tests/integration/test_lot_creation.py tests/integration/test_wallet_routes.py tests/integration/test_bid_routes.py tests/integration/test_lot_cancellation.py
uv run pytest tests/integration/test_public_lots.py tests/integration/test_bid_reads.py tests/integration/test_lot_room_ws.py tests/integration/test_lot_audit.py tests/integration/test_lot_receipt.py tests/test_artic.py tests/test_catalog_image_route.py
```

As configurações `BaseSettings` atuais têm `env_file` padrão. Para cumprir a
restrição de não leitura, a execução futura deve neutralizar esse carregamento
no processo de teste **antes** dos imports/fixtures (configuração somente de
teste, sem alterar o runtime) e fornecer valores locais fictícios. Apenas
exportar variáveis não garante que o arquivo não será aberto. Não imprimir
ambiente, cookies ou tokens. Reutilizar eventual mecanismo já presente quando
revalidar o candidato; não executar às cegas um comando que leia o arquivo.

Na pasta `frontend/`, a camada de browser direcionada é:

```sh
npm run test:e2e -- e2e/vitrine.spec.ts e2e/lot-room.spec.ts e2e/lot-room-ws.spec.ts e2e/audit.spec.ts e2e/receipt.spec.ts
```

Gate final obrigatório, na raiz, após os complementos/correções:

```sh
./verify.sh
```

O script atual faz Ruff/formatação, Docker/Compose/PostgreSQL, pytest, ESLint,
typecheck, Node tests, Vite e Docker build; falha na primeira etapa. O verify
padrão não executa Playwright. Aceito o comando focal de browser acima como
evidência adicional; `VERIFY_E2E=1 ./verify.sh` é alternativa para executar
também a suíte de browser no gate. Não faço os dois verifies completos por
rotina. Mudança/falha posterior invalida a evidência pertinente e exige nova
verificação. O build não equivale a deploy, e `real-stack.spec.ts` continua
opt-in separado por `E2E_REAL_BASE_URL`.

## 7. Evidências obrigatórias do deploy / Story 6.4

| Evidência pública ainda necessária | Registro esperado, sem dados sensíveis |
| --- | --- |
| Identidade do candidato publicado | Confirmação humana do commit realmente implantado e sua relação com o candidato testado/revisado; data e hora com fuso America/Maceio, URL pública e resultado. Não deduzir publicação de `main`, branch, health ou done do épico. |
| Cookie de sessão HTTPS | Inspeção de login real: somente nome e atributos HttpOnly/Secure/SameSite=Lax/Path=/, ausência de Domain, prefixo `__Host-`; verificar que navegador aceita e envia cookie na mesma origem. Nunca salvar/copiar valor do cookie/token em evidências. |
| Logout e CORS na borda | Logout público remove cookie com atributos corretos; respostas/preflight de origem divergente não recebem CORS permissivo, inclusive após proxy/infraestrutura. Headers locais não provam essa camada. |
| Rotas e contratos publicados | Confirmar bundle/API/deep-links do mesmo candidato, ausências de debug/crash, respostas sanitizadas observáveis sem induzir crash. A prova determinística do 500 fica nos testes; não provocar falha destrutiva em produção. |
| Fluxos novos do candidato | Validação final da 6.4 inclui cold start, seed, criação, vitrine, depósito/lance, atualização em outro navegador, fechamento, comprovante público e auditoria. `/health` sozinho não prova banco, scheduler ou fluxo. |
| Mídia degradada no browser publicado | Se testada por interceptação local de mídia no navegador, rotular como falha simulada de mídia; não alegar queda real da AIC. Confirmar conteúdo preservado e placeholder sem mudar configuração de produção. |

Não há evidência pública nova nesta sessão. O CA2 publicado permanece pendente
mesmo se os testes locais passarem; não marcar aceite integral/done por inferência.
As inspeções acima podem ser coletadas na publicação do candidato e serão
reconfirmadas na 6.4 se o candidato mudar. Preservo os gates de review agregado,
confirmação humana, merge/deploy manuais e smoke do processo canônico.

## 8. Riscos de regressão e decisões pendentes

| Risco | Controle no escopo |
| --- | --- |
| Falso positivo de CSRF causado por sessão inválida, rota inexistente ou payload inválido | Papel/lote válidos, corpo apropriado, códigos exatos do guard e controles positivos existentes. |
| Novo método/rota fica sem prova | Confronto runtime de método/caminho com mapa das evidências e checagens de política/escopo, inclusive app com SPA. |
| httpx injeta Content-Type e invalida o caso ausente | Enviar bytes e verificar o request efetivo. |
| Mudança em logout/cancelamento exige corpo e quebra cliente | Preservar ausência de payload permitida com header JSON. |
| Teste da sala acessa banco errado, liquida em background ou mascara SQL real | Engine `_test`, scheduler controlado existente, Session/read model reais, recorte SQL e snapshot sem efeitos. |
| Mock de rede mascara dependência de negócio | Transporte falho com contador; negócio deve fazer zero chamadas, controle da imagem deve alcançá-lo e falhar. Preservar guardas de rede; não abrir rede real por causa do LOW histórico de proxy. |
| API simulada é tomada como prova do backend/deploy | Registrar cada camada e manter pendências de §7. |
| Debug ou exceção vaza internals | App real debug falso, sem rotas sintéticas; falhas de teste com sentinelas fictícias e envelope exato. |
| Evidência de commit antigo é tomada como atual | Separar `3d3ea97`, base informada `8a460d26…` e futuro commit candidato/publicado confirmado. |

**Decisões humanas pendentes: nenhuma identificada.** A revisão desta spec e
a liberação posterior de código não foram antecipadas. Se uma lacuna exigir
mudar AD, política de sessão/CSRF, fallback ou outra decisão humana, paro nesse
ponto e apresento opções, consequências, risco, custo e recomendação. Não
adoto uma alternativa por conta própria.

Nesta preparação executei apenas leitura/busca, resolução da skill, extração
AST e escrita documental. Não executei pytest, Playwright, verify, smoke AIC,
Git/gh ou deploy; não alego contagens de testes aprovados, tempos ou evidência
de produção. Não invoquei `bmad-build`.
