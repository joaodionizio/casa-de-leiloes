# Plano de testes — Story 2.3

Toda contagem vem do `verify` desta story. Regressão: os 574 testes da 2.2
continuam passando sem alteração de asserção existente.

## 1. Apoio

- `tests/catalog_support.py`: `load_fixture(name)`; `FakeArtic` com `handler`
  configurável e `requests: list[httpx.Request]` (conta e inspeciona chamadas);
  `artic_client(fake)` → `ArticClient(transport=httpx.MockTransport(fake.handler))`;
  `install(app, fake)` → `app.state.artic_client = artic_client(fake)`;
  `search_params(request)` → `json.loads(request.url.params["params"])`.
- Reuso de `tests/auth_support.py` (`build_client`, `login`, `seed_demo_users`,
  e-mails semeados) e dos fixtures `db_session_factory`/`clean_users`.

## 2. Guarda de rede (CAP-7)

Em `tests/conftest.py`:

- No `pytest_sessionstart`, troca `socket.getaddrinfo` por um invólucro que
  permite só `localhost`, `127.0.0.1`, `::1` e IPs de loopback; para qualquer
  outro host, anota o host em `BLOCKED_HOSTS` e levanta `OSError`. (libpq resolve
  em C e não passa por aqui; `TestClient` não abre socket.)
- Fixture `autouse` por teste: falha o teste se `BLOCKED_HOSTS` não estiver
  vazio ao final, com o host na mensagem, e limpa a lista. Uma chamada real que
  o código transforme em 503 ainda reprova.
- `tests/test_network_guard.py`: (1) `ArticClient()` padrão + `search("monet")`
  → `CatalogUnavailable` e `"api.artic.edu"` anotado (o teste limpa a lista ao
  terminar); (2) `getaddrinfo("localhost", ...)` continua funcionando.

## 3. Cliente e adaptador — sem banco (`tests/test_artic.py`)

| Caso | Esperado |
| --- | --- |
| Cabeçalhos | toda requisição (busca e detalhe) leva `User-Agent: casa-de-leiloes/1.0` e `AIC-User-Agent: casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)` exatos e `Accept: application/json`. |
| Requisição da busca | GET, host `api.artic.edu`, caminho `/api/v1/artworks/search`, só o parâmetro `params`; `search_params()` == objeto de `aic-contract.md` §2 com o termo; contém `{"term":{"is_public_domain":true}}` e `{"exists":{"field":"image_id"}}` em `bool.filter` e `multi_match` com `operator: "and"` em `bool.must`; não-ASCII ("cézanne", "日本") sem `\u` no valor bruto. |
| Termo nunca é DSL | Termos `{"match_all":{}}`, `"},"query":{"match_all":{}},"x":{"`, `*:*` e `is_public_domain:false`: `search_params()` tem exatamente as chaves `q`, `query`, `limit`, `fields`; `bool.filter` igual ao fixo; `multi_match.query` e `q` iguais ao termo, byte a byte. Teste de `build_search_query` direto e via requisição. |
| Requisição do detalhe | caminho `/api/v1/artworks/27992`, `fields` exato. |
| Sem redirect | handler devolve 301 com `Location: https://example.org/x` → `CatalogUnavailable(reason="redirect")` e `len(fake.requests) == 1` (o host do `Location` nunca é requisitado). |
| Parsing busca (`search_monet.json`) | o adaptador devolve 7 dos 8 itens (só o de `id` string some); `is_public_domain` ausente → `None`; `image_id "../evil"` → `None`. A elegibilidade (serviço, §4) reduz a 3. |
| Parsing detalhe completo | todos os campos; strings com `strip`. |
| Campos ausentes (`artwork_missing_fields.json`) | ausente/`""`/não string → `None`; `title` "Study". |
| 404 no detalhe | `None` (não é falha). |
| Falhas | `ConnectTimeout`, `ReadTimeout` → `timeout`; `ConnectError` → `connect`; 403 HTML, 429, 500, 502, 503, 400 e 404 na busca → `http_<status>`; corpo HTML com `application/json` e `Content-Type: text/html` → `not_json`; `[]`, `{"data": "x"}`, `data` ausente, detalhe com `data.id` diferente → `bad_shape`. Nenhuma outra exceção. |
| Timeout configurado | `DEFAULT_TIMEOUT` = connect 3, read 5, write 5, pool 3. |
| IIIF | `iiif_image_url("2d484387-2509-5e8e-2c43-22f9981972eb")` (em `app.artic`) == `https://www.artic.edu/iiif/2/2d484387-2509-5e8e-2c43-22f9981972eb/full/843,/0/default.jpg`; `image_id` fora do regex (maiúsculas, `../evil`, `https://x`, vazio) → `ValueError`. |
| `get_image` (P6.1) | requisição GET a `https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg` exata (esquema, host, caminho, sem query) com `User-Agent` e `AIC-User-Agent` exatos; 200 `image/jpeg` → bytes do fixture `image_sample.jpg`; 404 → `None`; timeout, conexão, 3xx (uma única requisição, sem seguir), 403, 429, 400, 500, 502, 503, `text/html`, `application/json` com HTML, corpo vazio e corpo sem assinatura JPEG → `CatalogUnavailable` com o motivo certo (`timeout`, `connect`, `redirect`, `http_<status>`, `not_image`); corpo acima do teto (`MAX_IMAGE_BYTES` reduzido no teste) → `bad_shape`; `image_id` inválido → `ValueError` com zero requisições. |

## 4. Serviço e rotas — PostgreSQL real (`tests/integration/test_catalog_routes.py`)

Cliente: `build_client(..., session_factory=seeded)` + `install(app, fake)`.

| Grupo | Casos |
| --- | --- |
| Busca | `AUCTIONEER` `q=monet` → 200, 3 itens na ordem (`aic-contract.md` §5), cada um só com as 6 chaves de `ArtworkSummary` e `image_url` na base IIIF fixa; item `is_public_domain` falso, ausente e `null` nunca aparece; **obra sem `image_id` e com `image_id` inválido nunca aparecem**; `q="  monet  "` chega à AIC como `monet`; `Cache-Control: no-store`. |
| Sem correspondência | `search_empty.json` (termo "qxzvkwjq") → **200 `{"items": []}`** com `no-store`. |
| Detalhe | 27992 → 200 com as 12 chaves de `ArtworkDetail` (inclui `dimensions`), `source_url` = `https://www.artic.edu/artworks/27992`; campos ausentes → `null`; 404 da AIC, não PD e **sem `image_id` → 404 `not_found`** com `no-store` e corpo idêntico nos três; `get_artwork()` devolve `NOT_FOUND`, `NOT_PUBLIC_DOMAIN`, `NO_IMAGE` (serviço direto). |
| Falhas da AIC | cada falha de §3 (exceto 404 do detalhe) na busca e no detalhe → 503, corpo exatamente `{"status":503,"code":"catalog_unavailable","message":MESSAGES[...]}`, `no-store`, sem `artic`, `cloudflare`, `<html` nem `detail` no texto; `caplog` tem `reason=` e não tem o termo. |
| Entrada | `q` ausente, `""`, `"   "`, 101 caracteres após `strip` → 422 `validation_error` (`details[].loc == ["query","q"]`, sem o termo no corpo); `external_id` `abc`, `0`, `-1`, `1.5`, `2147483648` → 422; `1%2F2` e `%2e%2e%2f1` → 404; em todos, `fake.requests == []`. |
| Política | sem cookie → 401 `unauthorized` na busca e no detalhe; `BIDDER` → 403 `forbidden`; anônimo com `q` inválido → 401; `AUCTIONEER` → 200; **nos casos 401/403, `fake.requests == []`** (nada chega ao transporte). |
| Sem efeito colateral | `event.listen(db_engine, "before_cursor_execute", ...)` só durante as chamadas `AUCTIONEER` à busca e ao detalhe: todo statement começa com `SELECT`; `HEAD` e `OPTIONS` → 405 e `fake.requests == []`. |
| Imagem (P6.1) | `tests/test_catalog_image_route.py`, sem banco (rota `PUBLIC`): sem sessão, `image_id` válido → 200 `image/jpeg` com os bytes do fixture, `no-store`, `nosniff`; a URL upstream é exatamente a fixa (parâmetros `?url=` do cliente ignorados); cabeçalhos exatos; 301 → 503 após uma requisição; upstream 404 → 404 `not_found`; cada falha de `IMAGE_FAILURES` e o corpo grande → 503 `catalog_unavailable` com corpo exato, `no-store`, sem `cloudflare`, `<html`, `artic` no texto e `operation=image reason=` no log; `image_id` inválido (`abc`, maiúsculas, `..`, `%2e%2e`, `%0A`, `.jpg`, URL, `full`) → 422/404 e `fake.requests == []`; segmentos extras → 404 do roteador; `HEAD`/`OPTIONS`/`POST` não chegam ao upstream; a rota é `PUBLIC` e busca/detalhe seguem `AUCTIONEER` (`policy_by_route`, `policy_problems == []`). Busca e detalhe devolvem `image_url == "/api/catalog/images/{image_id}"`, nunca `artic.edu`. |
| Isolamento | com o falso sempre levantando `ConnectError`: `/health` 200, login 200, `/api/me` 200, logout 204. |

A falha de carga da imagem no navegador não tem teste de back-end: não chega ao
servidor e não muda elegibilidade (CAP-10); é coberta pelo roteiro manual §7.

## 5. Contrato e regressão (sem banco)

- `test_openapi.py`: lista de `paths` ganha `/api/catalog/artworks`,
  `/api/catalog/artworks/{external_id}` e `/api/catalog/images/{image_id}` (nessa
  ordem) depois de `/api/me`; a rota de imagem documenta `image/jpeg` no 200 e
  `ErrorResponse` em 404/422/503, sem 401/403; 401/403/422/503
  (e 404 no detalhe) referenciam `ErrorResponse`; `sorted(properties)` exato de
  `ArtworkSummary`, `ArtworkDetail`, `ArtworkSearchResponse`; nenhum schema com
  `_score`, `thumbnail`, `config`, `is_public_domain`, `alt_text`;
  `HTTPValidationError` continua ausente.
- `test_errors.py`: `MESSAGES ==` ganha `"catalog_unavailable"` com o texto
  exato; `code_for_status(503) == "internal_error"` intacto.
- `test_access_policy.py`: `EXPECTED_POLICIES` ganha as duas rotas de dados
  `AccessPolicy.AUCTIONEER` e a rota de imagem `AccessPolicy.PUBLIC`; verificador e meta-testes inalterados.
- Criar a app (`create_app`) não chama a AIC (guarda + falso com zero chamadas).

## 6. Smoke real — fora do `verify` (CAP-8, Q7)

Comando:

```bash
cd backend
uv run python -m scripts.smoke_artic
```

Sem banco, `.env`, login, segredo ou escrita; importa só `app.artic` e
`app.catalog`; cada chamada usa `DEFAULT_TIMEOUT` (pior caso por item: 8 s);
~8 requisições, bem abaixo de 60/min. Saída: uma linha
`PASS|FAIL <n> <item> — <detalhe curto>` por item e o resumo `6/6 PASS`; código
de saída 0 só com tudo `PASS`. Falha num item não interrompe os seguintes.

| # | Item AD-23 | Como prova |
| --- | --- | --- |
| 1 | Busca real | `search_artworks(client, "monet")` → ≥ 1 item; e `"qxzvkwjq"` → 0 itens (o termo filtra, P7.1). |
| 2 | Detalhe real | `get_artwork(client, 27992)` → `FOUND`, `title` e `artist_display` não vazios. |
| 3 | `is_public_domain=true` | Em `client.search("monet")`, antes da reconferência, todo item tem `is_public_domain is True` (a AIC aplica o filtro); e `get_artwork(client, 129884)` → `NOT_PUBLIC_DOMAIN` (controle negativo). |
| 4 | Imagem IIIF | `httpx` `GET` em `iiif_image_url(image_id)` do item 2 (o `image_url` do contrato agora é a URL do nosso proxy), com os cabeçalhos aprovados e `stream`: lê só o primeiro bloco e fecha; espera 200 e `Content-Type` `image/jpeg`; e `client.get_image(image_id)` (o mesmo caminho do proxy) devolve bytes que começam com a assinatura JPEG. Um `GET` cru do detalhe 27992 confere `config.iiif_url.rstrip("/") == ARTIC_IIIF_BASE_URL.rstrip("/")` e `config.website_url == ARTIC_WEBSITE_BASE_URL` (deriva, C1). |
| 5 | Campos usados | No mesmo `GET` cru, cada nome de `fields` do detalhe existe como chave em `data`; imprime quais vieram `null`. |
| 6 | API indisponível | `ArticClient(api_base_url="http://127.0.0.1:9")` → `CatalogUnavailable(reason="connect")`. Falha determinística e local; nenhuma tentativa de derrubar a AIC; sem endereço não roteável. |

A saída real vai para a story. O smoke não entra no `verify.sh` nem no `pytest`
(`scripts/` fora de `testpaths`).

## 7. Roteiro manual no navegador (antes do review)

Pré: `docker compose up -d --wait postgres`, back-end e `npm run dev`.

1. Visitante: tela de login, nenhuma busca. `GET /api/catalog/artworks?q=a` na
   barra → JSON 401.
2. `bidder1@example.com`: sem busca na tela; mesma URL → 403.
3. `auctioneer@example.com`: "Buscar obras" no estado inicial com orientação;
   nenhum botão "Criar lote".
4. Buscar com campo vazio/espaços → mensagem no campo, sem requisição (aba Rede).
5. "monet" → "Buscando…", depois lista com miniaturas, título, artista, data;
   se 20, aviso de refino.
6. "qxzvkwjq" → "Nenhuma obra encontrada.".
7. Abrir uma obra → detalhe com imagem grande, ficha completa (inclui
   Dimensões), link da fonte abrindo em nova aba.
8. Placeholder: DevTools → Network → Request blocking → bloquear
   `*/api/catalog/images/*` → nova busca → miniaturas e imagem grande com
   placeholder e "Imagem indisponível"; textos e ficha intactos; sem salto de
   layout; o detalhe continua abrindo.
9. Catálogo indisponível: com uvicorn e Vite locais rodando, desligar a rede
   externa da máquina (Wi-Fi) e buscar → "O catálogo do museu não respondeu…" +
   "Tentar novamente"; login, `/api/me` e "Sair" continuam funcionando (tudo é
   localhost). Parar o back-end não serve: isso é o estado 7.
10. Erro inesperado: com o front aberto, parar o uvicorn e buscar → "Não foi
    possível falar com o servidor…".
11. Recarregar a página → sessão mantida, busca volta ao estado inicial.
12. Teclado: só Tab/Enter/Espaço do campo ao detalhe e volta; foco visível
    sempre; leitor de tela anuncia "Buscando obras…" e o resultado.
13. 320 px: sem rolagem horizontal; detalhe em troca de vista com "← Voltar aos
    resultados", foco e rolagem restaurados. Desktop ≥ 64rem: lista e detalhe
    lado a lado, detalhe fixo ao rolar.
14. Imagem real: miniaturas e imagem grande carregam pelo proxy. Aba Rede: as
    requisições são `GET /api/catalog/images/{image_id}` (200 `image/jpeg`, mesma
    origem) e **nenhuma** vai a `www.artic.edu`. (A suposição original, IIIF direto
    do navegador, foi refutada com 403 neste teste em 24/10/2026; P6.1.)
