---
id: SPEC-story-2-3-busca-obras-aic
companions:
  - decisions.md
  - aic-contract.md
  - backend-contract.md
  - frontend-catalog.md
  - test-plan.md
  - implementation-map.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../../docs/ARQUITETURA.md
sources:
  - ../../implementation-artifacts/2-3-busca-de-obras-no-art-institute-of-chicago.md
---

> **Contrato canônico.** Esta SPEC e os arquivos em `companions:` são o contrato
> completo da Story 2.3. A story em `sources:` fica só para rastreio. P1 a P11,
> P7.1, P8.1 e C1 a C4 foram aprovados pelo Joaodionizio em 24/10/2026
> (`decisions.md`). Nenhuma decisão aberta.
>
> **Revisão de 24/10/2026 (teste manual): imagem por proxy same-origin.** A suposição
> aprovada de que o navegador carregaria o IIIF direto foi refutada: todas as
> requisições `default.jpg` do navegador deram HTTP 403 (Cloudflare). Decidi trocar só
> o transporte da imagem por um proxy controlado no nosso back-end,
> `GET /api/catalog/images/{image_id}` (CAP-13, P6.1 em `decisions.md`). Os bytes
> continuam não armazenados e a falha da mídia continua degradando para o placeholder.

# Story 2.3: busca de obras no Art Institute of Chicago

## Why

Mandato do desafio (FR2, parte do NFR2): o leiloeiro escolhe a obra que vira lote
num catálogo real de domínio público. Esta story entrega só a escolha (buscar,
ver o detalhe com os dados que a 2.4 vai copiar para o lote) sem gravar nada. É a
primeira dependência externa da aplicação: precisa falhar de forma controlada,
sem derrubar o resto, e ser testável sem internet. As chamadas reais de
24/10/2026 (`aic-contract.md` §1) mostraram três fatos que a story não previa: o
Cloudflare da AIC devolveu 403 quando a identificação recomendada pela
documentação não estava presente, o parâmetro `q` não filtra e o firewall recusa
alguns termos.

## Capabilities

- **CAP-1**
  - **intent:** O leiloeiro busca obras por termo e recebe só obras de domínio público com imagem.
  - **success:** `GET /api/catalog/artworks?q=monet` com sessão `AUCTIONEER` → 200 `{"items": [...]}` com até 20 `ArtworkSummary`; a consulta enviada à AIC é o objeto construído pelo servidor (`aic-contract.md` §2): `bool.must.multi_match` com o termo (`operator: and`) e os filtros `is_public_domain=true` e `exists image_id`; o termo entra só como valor; item com `is_public_domain` diferente de `true`, sem `image_id` válido ou sem `id` inteiro positivo é descartado mesmo que a AIC o devolva; termo sem correspondência → 200 `{"items": []}` e a interface mostra "Nenhuma obra encontrada.".
- **CAP-2**
  - **intent:** O leiloeiro abre o detalhe de uma obra elegível com o snapshot que a 2.4 vai copiar.
  - **success:** `GET /api/catalog/artworks/{external_id}` → 200 `ArtworkDetail` (campos em `backend-contract.md` §4, incluindo `dimensions`); texto ausente, vazio ou não string na AIC → `null`, nunca inventado; obra inexistente (404 real da AIC), fora do domínio público ou sem `image_id` elegível → 404 `not_found`, sem distinção no contrato público; o serviço guarda o motivo interno (`NOT_FOUND`, `NOT_PUBLIC_DOMAIN`, `NO_IMAGE`) para uso futuro.
- **CAP-3**
  - **intent:** Falhas externas chegam como erro claro e limitado no tempo, sem afetar o resto da aplicação.
  - **success:** Erro de conexão (inclui DNS), timeout, 3xx, 403 externo (Cloudflare), 429, 5xx, JSON inválido e resposta incompatível (inclui qualquer outro status inesperado) → 503 `catalog_unavailable` no formato único, com `Cache-Control: no-store`, sem eco de corpo, URL ou cabeçalho da AIC e sem 500; o 404 real do detalhe da AIC não é falha (CAP-2); espera limitada (connect 3 s, read 5 s), sem retry; o log registra a categoria; com a AIC falhando, `/health`, login, `/api/me` e logout respondem normalmente.
- **CAP-4**
  - **intent:** Só o leiloeiro usa a busca e o detalhe, e recusas não geram tráfego externo.
  - **success:** As duas rotas de dados (a rota de mídia é pública, CAP-13) são registradas por `api_route(..., policy=AccessPolicy.AUCTIONEER)`; sem sessão → 401, `BIDDER` → 403, ambos no formato único e com o transporte falso com zero requisições; anônimo com `q` inválido → 401; o teste de política da 2.2 lista as rotas como `AUCTIONEER` sem mudança no verificador.
- **CAP-5**
  - **intent:** A entrada é validada antes de qualquer chamada externa e o usuário nunca escolhe destino de rede nem estrutura de consulta.
  - **success:** `q` ausente, vazio, só espaços ou com mais de 100 caracteres após `strip` → 422 `validation_error`; `external_id` não inteiro, ≤ 0 ou > 2147483647 → 422; `/` codificado no caminho → 404 do roteador; em todos, zero requisições à AIC; host, esquema e caminho da AIC são constantes; um termo com aparência de DSL ou JSON chega à AIC só como o valor de `multi_match.query`, com a estrutura da consulta inalterada; o cliente não segue redirecionamento (um 3xx gera exatamente uma requisição).
- **CAP-6**
  - **intent:** A busca e o detalhe são leituras puras.
  - **success:** Nenhuma migration, tabela ou mudança de seed; durante chamadas `AUCTIONEER` às duas rotas de dados o banco só recebe `SELECT` (a rota de imagem não usa o banco); `HEAD`/`OPTIONS` → 405 sem requisição à AIC; criar a app e responder `/health` não abre conexão externa.
- **CAP-7**
  - **intent:** O `verify` nunca depende da AIC real nem da internet.
  - **success:** Os testes usam o `ArticClient` real com `httpx.MockTransport` e fixtures JSON versionadas; uma guarda em `tests/conftest.py` recusa e registra a resolução de qualquer host fora de loopback e reprova o teste que tentou; um meta-teste prova que o cliente padrão é barrado.
- **CAP-8**
  - **intent:** Existe uma verificação manual, fora do `verify`, de que a integração real funciona.
  - **success:** `cd backend && uv run python -m scripts.smoke_artic` imprime PASS/FAIL para os seis itens do AD-23 (busca, detalhe, `is_public_domain=true`, imagem IIIF, campos usados, indisponibilidade) e sai com 0 só se todos passarem; a indisponibilidade é a falha determinística em `127.0.0.1:9`; não usa banco, login, segredo nem `app.main` e não grava nada; a saída real entra na story.
- **CAP-9**
  - **intent:** O leiloeiro busca e confere obras pela interface, em português, com estados claros.
  - **success:** O roteiro manual (`test-plan.md` §7) passa no navegador cobrindo os dez estados de `frontend-catalog.md` §3, o placeholder, 320 px, desktop largo e teclado; `BIDDER` e visitante não veem a busca; mensagens vêm do `code`, nunca do `message`; não existe botão de criar lote (nem habilitado, nem desabilitado) nem navegação sem função.
- **CAP-10**
  - **intent:** A imagem chega ao navegador pelo nosso proxy same-origin e sua falha nunca esconde os dados nem invalida a obra.
  - **success:** `image_url` é sempre `/api/catalog/images/{image_id}` (URL relativa, mesma origem), montada no servidor com `image_id` validado; o navegador nunca pede `www.artic.edu`; o `<img>` fica numa caixa de proporção fixa com `referrerPolicy="no-referrer"`; erro de carga (inclui 404/503 do proxy) troca pelo placeholder local `/artwork-placeholder.svg` com "Imagem indisponível", mantendo título, artista e metadados; a falha de carga é só da interface e não muda o contrato nem a elegibilidade.
- **CAP-11**
  - **intent:** O contrato novo fica documentado e fixado por teste.
  - **success:** `/api/openapi.json` tem os três caminhos (busca, detalhe e imagem, nessa ordem) depois de `/api/me`, com `ErrorResponse` em 401/403/422/503 (e 404 no detalhe) e os schemas `ArtworkSummary`, `ArtworkDetail` e `ArtworkSearchResponse` com exatamente os campos de `backend-contract.md` §4; `MESSAGES` ganha só `catalog_unavailable`; `code_for_status(503)` continua `internal_error`.
- **CAP-12**
  - **intent:** A entrega fica verificada e documentada.
  - **success:** `./verify.sh` completo passa, com saída real registrada; smoke executado com saída real; README, `docs/uso_de_ia.md`, Q7 em `docs/ARQUITETURA.md` (questões e histórico, sem alterar AD), story e `sprint-status.yaml` atualizados.

- **CAP-13** (revisão de 24/10/2026)
  - **intent:** O navegador recebe a imagem da obra sem depender do Cloudflare da AIC, sem que o servidor guarde nada nem vire proxy genérico.
  - **success:** `GET /api/catalog/images/{image_id}` com `AccessPolicy.PUBLIC` (obras de domínio público, nenhum dado de conta, a vitrine da 2.5 usará as mesmas imagens); o único dado do usuário é `image_id`, validado pelo mesmo regex da P6 antes de qualquer chamada (inválido → 422, zero requisições); o servidor chama só `https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg` (host, esquema, caminho, tamanho e formato fixos), com `User-Agent` e `AIC-User-Agent` aprovados e `follow_redirects=False`; upstream 200 `image/jpeg` com corpo JPEG (até 5 MiB) → 200 `image/jpeg` com os bytes, `Cache-Control: no-store` e `X-Content-Type-Options: nosniff`; upstream 404 → 404 `not_found`; 3xx, 403, 429, 5xx, outro status, conexão, timeout, tipo ou corpo que não seja JPEG, corpo acima do limite → 503 `catalog_unavailable`, sem corpo nem cabeçalho do upstream; nada vai ao filesystem, ao banco nem a cache.

## Constraints

- AD-23: elegível = `is_public_domain is True` e `image_id` válido; filtro na consulta **e** reconferência por item no servidor.
- AD-12/AD-22: a AIC só alimenta a escolha da obra; nada desta story é lido por lote existente; o servidor só busca bytes de imagem no proxy da CAP-13, em memória, e nunca guarda nem faz cache deles.
- AD-11/2.2: política só por `api_route` (busca e detalhe `AUCTIONEER`, mídia `PUBLIC`); nada de `@app.get`, `APIRouter`, `include_router`; dependências `def`.
- AD-1/AD-25: chamada à AIC síncrona dentro de handler `def` (threadpool), nunca no event loop.
- AD-19/AD-29: rotas só `GET`, sem escrita; sem CORS; sem nova autenticação.
- 2.1: erro só pelo envelope único e pelo catálogo `MESSAGES`; `detail` da AIC nunca chega ao cliente; o 422 do handler global fica como está, sem `no-store` (C4).
- Destino de rede fixo no código (`ARTIC_API_BASE_URL`, `ARTIC_IIIF_BASE_URL`, `ARTIC_WEBSITE_BASE_URL`); sem variável de ambiente nova; só o construtor do `ArticClient` aceita outra base, usado por testes e pelo smoke.
- A consulta à AIC é um objeto construído pelo servidor; nenhuma DSL ou JSON do usuário é incorporado; serializado em `params` como JSON compacto UTF-8 (`ensure_ascii=False`).
- Toda chamada do servidor envia `User-Agent: casa-de-leiloes/1.0` e `AIC-User-Agent: casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)`. É identificação recomendada pela documentação da AIC, não autenticação; sem e-mail.
- AD-4: TypeScript simples; sem React Router, sem biblioteca de UI, sem ferramenta de teste nova.
- AD-30: código, rotas e campos em inglês; interface e mensagens em português.
- Testes nunca afrouxados: `test_openapi.py`, `test_errors.py` e `test_access_policy.py` só ganham o que é novo.

## Non-goals

- Criar lote, persistir snapshot, recusa de criação fora do domínio público com motivo, "Meus lotes", lote demo (2.4).
- Vitrine, página do lote, roteador (2.5); busca e filtro de lotes (OPT1, 6.5).
- Paginação, cache, nova tentativa automática, fila.
- Guardar, redimensionar, converter ou fazer cache de imagem; proxy genérico (URL, host, tamanho, região, rotação ou formato escolhidos pelo cliente); qualquer outro tipo de mídia.
- Navegação do leiloeiro ("Vitrine", "Meus lotes", "Criar lote") e qualquer botão de ação de lote.
- `alt_text` da AIC no contrato; testes automatizados de front-end (Q10 continua aberta).
- Content-Security-Policy, revisão global de segurança (6.1), identidade completa e dark mode (6.2, 6.7).

## Success signal

- Logado como leiloeiro na URL local, busco "monet", vejo até 20 obras de Monet em domínio público com imagem, abro uma e confiro título, artista, data, técnica, dimensões, departamento, tipo, crédito, número no acervo e link da fonte; "qxzvkwjq" mostra "Nenhuma obra encontrada."; sem rede externa, a busca mostra "O catálogo do museu não respondeu" e o login continua funcionando; `./verify.sh` passa sem internet e o smoke imprime seis PASS contra a AIC real.

## Assumptions

- ~~O navegador carrega o IIIF sem `AIC-User-Agent`.~~ **Refutada** no teste manual de 24/10/2026 (HTTP 403 em toda `default.jpg`); substituída pelo proxy da CAP-13. A premissa nova (o IIIF responde 200 `image/jpeg` ao servidor com os cabeçalhos aprovados) foi confirmada pelo smoke.
- Recarregar a página volta ao estado inicial da busca (sem termo na URL), mantendo a sessão.
- Título ausente na AIC vira `null` no contrato e "Sem título" na interface.
- `artist_display` pode ter `\n`; a interface exibe com `white-space: pre-line`.
