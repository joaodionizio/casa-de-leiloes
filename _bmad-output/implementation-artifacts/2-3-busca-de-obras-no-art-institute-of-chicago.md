# Story 2.3 — Busca de obras no Art Institute of Chicago

Status: done

Chave do sprint: `2-3-busca-de-obras-no-art-institute-of-chicago`
Épico: 2. Data de criação: 24/10/2026.

## Story e objetivo

Como leiloeiro,
quero buscar obras no catálogo do Art Institute of Chicago,
para que eu escolha a obra que vai virar lote.

Nesta story entrego: a integração do back-end com a API do Art Institute of
Chicago (AIC), restrita a obras com `is_public_domain=true`; duas rotas de
leitura restritas a `AUCTIONEER` (busca e detalhe com o snapshot mínimo do
AD-23) e uma rota pública de mídia, `GET /api/catalog/images/{image_id}`, que
entrega a imagem da obra pela nossa origem; o erro claro, no formato único, quando
a AIC estiver indisponível ou lenta; a tela de busca do leiloeiro, com a imagem
da obra e o placeholder local; testes
que nunca dependem da API real; e um smoke test separado, fora do `verify`, contra
a API real. Não crio lote, não persisto nada e não antecipo a 2.4.

O status `ready-for-dev` indica que o artefato está criado. As questões P1 a P10
(seção "Questões abertas") são decididas por mim no planejamento, antes de
qualquer código, e registradas nesta story.

## Fontes e base real

Uso `CLAUDE.md`, `docs/ARQUITETURA.md` (AD-11, AD-12, AD-19, AD-22, AD-23,
AD-25, AD-27, AD-29, AD-30 e a questão Q7), `_bmad-output/planning-artifacts/epics.md`
(Story 2.3), `sprint-status.yaml`, `docs/desafio-elite-dev.md` (painel do
leiloeiro e "Gestão da API externa") e as Stories 2.1 e 2.2, só como base.

**Título e escopo conferidos no `epics.md`.** O título exato é **"Busca de obras
no Art Institute of Chicago"**. ADs declaradas pelo `epics.md`: AD-12, AD-22,
AD-23. Dependência declarada: **Q7** (como simular "API indisponível" no smoke
test), que vira a P9. Cobertura: FR2 e parte do NFR2.

**Dependências das stories concluídas:**

- **2.1:** formato único de erro (`error_response()`, catálogo `MESSAGES`, `detail`
  de `HTTPException` nunca exposto), 422 sanitizado e 500 genérico. As rotas da
  2.3 são `GET`, então a proteção de `Origin`/`Content-Type` não se aplica a elas
  (só a escritas).
- **2.2:** `AccessPolicy.AUCTIONEER`, `api_route(...)` como único registro de rota,
  `require_auctioneer`, 401 sem sessão e 403 do outro papel, meta-teste que
  reprova rota sem política ou com a dependência errada, `error_responses()` no
  OpenAPI, a tela de login e o `SiteHeader` com o papel em português.

**Divergências encontradas (nenhuma exige decisão minha antes desta story):**

- O `epics.md` diz "Não há documento de UX". Depois dele, aprovei `DESIGN.md` e
  `EXPERIENCE.md` (24/10/2026), e o `CLAUDE.md` os torna vinculantes para
  front-end, abaixo da story e da arquitetura. Sigo o `CLAUDE.md`.
- O critério 1 do `epics.md` fala em buscar "no painel". O painel do leiloeiro do
  enunciado (buscar, criar lote, cancelar, ver resultados) está distribuído entre
  2.3, 2.4, 3.6 e 4.5. Nesta story existe só a parte de busca e detalhe. O
  `EXPERIENCE.md` §5 lista a navegação do leiloeiro como "Vitrine, Meus lotes,
  Criar lote", mas esses destinos só ganham função na 2.4 e na 2.5; pela regra do
  `CLAUDE.md` (nenhum controle sem funcionalidade), não aparecem aqui.
- O AD-23 lista "comportamento quando a API está indisponível" como item do smoke
  test da integração real; a Q7 registra que isso só é verificável com falha
  simulada. É exatamente a dependência declarada no `epics.md` (P9).
- O `sprint-status.yaml` ainda registra `epic-1: in-progress`; isso já está em
  `deferred-work.md` e não mexo aqui.
- A skill `bmad-create-story` não está instalada em `.claude/skills/` (o
  `_bmad/bmm/v6-shims/README.md` só a menciona). Sigo a estrutura das stories
  2.1 e 2.2.

**Base existente (conferida nos arquivos, sem git):**

- `backend/app/main.py`: `create_app()` registra `/health`, as rotas de
  autenticação, o WebSocket técnico e, por último, a SPA. Configuração por app em
  `app.state.session_config` (precedente para guardar o cliente da AIC na app e
  substituí-lo nos testes).
- `backend/app/access.py`: `api_route(app, path, methods=..., policy=...)` grava a
  política e aplica a dependência; não se usa `@app.get`, `APIRouter` nem
  `include_router`. Dependências `def`, no threadpool.
- `backend/app/errors.py`: `CODE_BY_STATUS` não tem 502, 503 nem 504;
  `code_for_status(503)` hoje devolve `internal_error`. Um código próprio para a
  AIC indisponível precisa entrar no catálogo e ser devolvido pela rota com
  `error_response(...)`, como `invalid_credentials` na 2.2 (OQ-3).
- `backend/pyproject.toml`: `httpx` existe só no grupo `dev` (é usado pelo
  `TestClient`). Não há cliente HTTP nas dependências de produção (P2).
- `backend/tests/test_openapi.py` fixa a lista de `paths`;
  `backend/tests/test_errors.py` fixa o catálogo de mensagens por igualdade exata.
  Ambos mudam nesta story, acrescentando o que é novo, sem afrouxar.
- Nenhum teste faz chamada de rede externa hoje.
- Front-end: `App.tsx` decide entre login e usuário autenticado; autenticado não
  mostra conteúdo ainda (só um `h1` oculto). Sem roteador e sem biblioteca de
  testes (Q10, "ferramenta de teste do front-end", segue aberta). Mensagens em
  português mapeadas pelo `code`, nunca pelo texto do servidor (2.2 P15). Tokens
  do `DESIGN.md` já em `index.css`. Não existe placeholder de imagem em
  `frontend/public/` (só `favicon.svg`).
- Sem Content-Security-Policy na aplicação: a imagem sai da nossa própria origem
  (rota de mídia), então nenhum cabeçalho precisa de ajuste.
- Último `verify` registrado (2.2, correções do review): 574 testes passaram.

## Critérios de aceitação

1. **CA1 — Busca restrita ao domínio público.** Dado estar logado como
   leiloeiro, quando busco por um termo (rota e parâmetros na P1, limites na P7),
   então recebo só obras com `is_public_domain=true`. O filtro vai na consulta à
   AIC **e** é reconferido em cada item no nosso back-end: item com
   `is_public_domain` falso, ausente ou não booleano é descartado, mesmo que a AIC
   o devolva (AD-23, filtro obrigatório). Cada item traz pelo menos o
   identificador da obra na AIC, título, artista e a referência da imagem
   (formato na P6). Itens sem imagem seguem a P5.
2. **CA2 — Detalhe com o snapshot mínimo.** Dado uma obra da lista, quando abro o
   detalhe, então vejo os campos do snapshot mínimo do AD-23: `external_id`,
   `title`, `artist_display`, `date_display`, `medium_display`,
   `department_title`, `artwork_type_title`, `image_id`, referência/URL IIIF,
   crédito/origem (`credit_line`) e URL da fonte na AIC. Campo textual ausente na
   AIC vem `null`, de forma consistente, nunca inventado. Obra inexistente ou fora
   do domínio público segue a P4. O detalhe é leitura ao vivo da AIC: nada é
   gravado.
3. **CA3 — Imagem e placeholder.** Dado um item ou o detalhe, quando a imagem
   carrega, então aparece com dimensões estáveis; quando falha (erro, 404, 503,
   rede), então aparece o placeholder local e título, artista e demais dados
   continuam visíveis e utilizáveis (AD-22). O navegador pede a imagem à nossa
   própria origem, `GET /api/catalog/images/{image_id}`, nunca ao domínio da AIC
   (o IIIF direto deu 403 do Cloudflare no teste manual; P6.1). O back-end busca o
   JPEG no IIIF da AIC e só repassa os bytes em trânsito, em memória: não os
   persiste, não grava no banco nem no filesystem e não mantém cache.
4. **CA4 — AIC indisponível ou lenta.** Dado a AIC com timeout, recusa de
   conexão, erro de DNS, resposta 5xx, 429, JSON malformado ou formato inesperado,
   quando busco ou abro o detalhe, então recebo o erro no formato único com o
   status e o código da P3, mensagem em português, sem 500, sem stack, sem ecoar
   corpo, URL ou cabeçalhos da AIC; a interface mostra uma mensagem clara em
   português e permite tentar de novo. A espera tem limite (P3). O restante da
   aplicação continua funcionando: com a AIC falhando, `/health`, login, logout e
   `/api/me` respondem normalmente (teste). O servidor registra no log a categoria
   da falha, sem segredo nem dado pessoal.
5. **CA5 — Política de acesso.** Dado um visitante sem login, quando chama a busca
   ou o detalhe, então recebe 401; dado um `BIDDER`, recebe 403; ambos no
   formato único e **sem nenhuma chamada à AIC** (o teste prova que o cliente
   falso não foi acionado). A busca e o detalhe declaram `AccessPolicy.AUCTIONEER`
   por `api_route`. A rota de imagem, `GET /api/catalog/images/{image_id}`, declara
   `AccessPolicy.PUBLIC` (obras de domínio público, nenhum dado de conta, e a
   vitrine pública da 2.5 usa as mesmas imagens). O teste de política da 2.2 passa
   com as três rotas sem alteração do verificador. Na interface, `BIDDER` e
   visitante não veem a busca.
6. **CA6 — Entrada validada e sem SSRF.** O termo de busca e a paginação seguem a
   P7; fora dos limites → 422 no formato único da 2.1. O identificador da obra no
   detalhe é inteiro positivo; qualquer outro valor → 422, antes de chamar a AIC.
   O host e o caminho da AIC são fixos no código; o usuário nunca escolhe host,
   esquema nem caminho; o identificador só entra no caminho depois de validado;
   redirecionamentos da AIC não são seguidos para outro host.
7. **CA7 — Sem efeito colateral e sem bloqueio do event loop.** As rotas são
   `GET`, não gravam no banco, não criam tabela nem migration e não mudam o seed
   (AD-19, AD-29). A chamada à AIC é síncrona em handler `def` (threadpool),
   nunca no event loop. Importar e criar a aplicação e responder `/health`
   continuam sem banco e sem rede externa. As respostas das rotas da 2.3 levam
   `Cache-Control` que impede cache compartilhado (valor na P8).
8. **CA8 — Testes sem a API real.** Dado o `verify`, quando os testes rodam,
   então nenhum deles acessa a AIC real: o cliente é substituído por um falso
   alimentado por fixtures versionadas (respostas no formato real da AIC, sem
   dados pessoais) e por falhas simuladas; um teste ou guarda reprova qualquer
   tentativa de chamada real à AIC durante o `pytest`.
9. **CA9 — Smoke test da integração real.** Existe um smoke test separado,
   documentado no README e fora do `verify`, que cobre os itens do AD-23: busca;
   detalhe; filtro `is_public_domain=true`; imagem IIIF respondendo; presença dos
   campos usados; e o comportamento com a API indisponível, por falha simulada
   (P9). Eu o executo, e a story registra a saída real.
10. **CA10 — Interface do leiloeiro.** Dado estar logado como leiloeiro, quando
    abro a aplicação, então encontro a busca de obras (lugar e navegação na P10),
    em português, com os estados: inicial, buscando, resultados, nenhum resultado,
    termo inválido, catálogo indisponível e erro inesperado; a lista é visual e
    compacta (`EXPERIENCE.md` §6, "lista visual, não cards gigantes"); abrir um
    item mostra o detalhe do CA2. As mensagens vêm do `code`, não do `message` do
    servidor. Não aparecem: botão "Criar lote" nem qualquer ação de lote (2.4),
    "Meus lotes" (2.4), busca de lotes da vitrine (OPT1, 6.5). O layout segue
    `DESIGN.md` e `EXPERIENCE.md` e é definido no `bmad-spec`.
11. **CA11 — Verificação e documentação.** Executo `./verify.sh` completo e
    registro a saída real. README atualizado (smoke test, dependência da AIC e
    seus limites, o que acontece se ela cair); `docs/uso_de_ia.md` atualizado;
    resolução da Q7 registrada em `docs/ARQUITETURA.md` (questões e histórico),
    sem alterar AD. Paro na 2.3.

## Política de acesso das rotas novas

| Rota | Método | Política | Sem login | `BIDDER` |
| --- | --- | --- | --- | --- |
| `/api/catalog/artworks?q=...` (busca de obras na AIC) | `GET` | `AUCTIONEER` | 401 | 403 |
| `/api/catalog/artworks/{external_id}` (detalhe de uma obra da AIC) | `GET` | `AUCTIONEER` | 401 | 403 |
| `/api/catalog/images/{image_id}` (imagem da obra, P6.1) | `GET` | `PUBLIC` | 200 | 200 |

Nenhuma rota existente muda de política. Nenhuma rota de escrita nasce nesta story.

## Decisões já fechadas pela arquitetura e pelo `epics.md`

Não reabro nenhuma delas.

| Fonte | O que já está decidido |
| --- | --- |
| AD-12 | Fonte: Art Institute of Chicago. Seed e testes com fixtures locais; seed offline. Smoke test pequeno da integração real antes da implementação completa. A API externa nunca é back-end de leitura de lote existente (aqui não há lote: a busca é leitura ao vivo do catálogo, que é o uso previsto). |
| AD-22 (revisado em 24/10/2026) | Não armazenar bytes; a mídia vem do IIIF da AIC, mas o navegador a pede à nossa rota same-origin e pública, `GET /api/catalog/images/{image_id}`, que valida o `image_id`, usa host/caminho/tamanho/formato fixos e só repassa os bytes em trânsito; placeholder local se falhar; o resto continua funcionando. |
| AD-23 | `is_public_domain=true` é filtro obrigatório; campos do snapshot mínimo; smoke test com seis itens (busca, detalhe, filtro, IIIF, campos, indisponibilidade). |
| AD-11 + 2.2 | Busca é do leiloeiro: `AccessPolicy.AUCTIONEER`, registrada por `api_route`; 401 sem login, 403 de `BIDDER`. O `epics.md` exige que licitante e visitante sejam recusados pela política. |
| AD-19, AD-29 | GET não altera estado. |
| AD-1, AD-25 | Operação bloqueante (rede) fora do event loop: handler `def`. |
| AD-30 | Rotas, campos e código em inglês; mensagens e interface em português. |
| AD-17, AD-27 | `verify` fail-fast; testes no mesmo commit; nada de SQLite. Os testes desta story não precisam de banco para a lógica da AIC, mas os de política usam o PostgreSQL real, como na 2.2. |
| 2.1 | Formato único de erro; 500 genérico; `detail` nunca exposto; 422 sanitizado. |
| 2.2 OQ-3 | Código específico devolvido pela rota com `error_response(status, code)`, sem hierarquia de exceções. |
| 2.2 P15 | Mensagens da interface mapeadas pelo `code`. |
| `epics.md` 2.3 | Testes do `verify` não dependem da API real; smoke test separado, documentado e fora do `verify`. |
| `CLAUDE.md` | Nenhum controle sem funcionalidade; obra protagonista; roxo como assinatura; estados nunca só por cor. |

## Questões abertas (decidir no planejamento, antes do código)

> Registro histórico: o texto das questões é o de antes das decisões. O contrato
> vigente está em "Critérios de aceitação", "Política de acesso das rotas novas" e
> "Decisões fechadas"; a P6 (URL IIIF carregada pelo navegador) foi revisada pela
> P6.1 depois do teste manual.

Cada questão tem no máximo três opções. As recomendações são propostas; a decisão
é minha.

### P1 — Rotas e formato das respostas

**Problema.** O AD-30 não nomeia as rotas do catálogo externo, e elas não podem
ser confundidas com os nossos lotes (`/api/lots`).

- **(a)** `GET /api/catalog/artworks?q=...` (busca) e
  `GET /api/catalog/artworks/{external_id}` (detalhe).
- **(b)** `GET /api/artworks/search?q=...` e `GET /api/artworks/{external_id}`.
- **(c)** `GET /api/museum/search?q=...` e `GET /api/museum/artworks/{external_id}`.

Formato proposto, em todas: busca `{"items": [ArtworkSummary, ...]}` (mais o que a
P7 decidir sobre paginação), com `ArtworkSummary = {external_id, title,
artist_display, image_id, image_url}`; detalhe `ArtworkDetail` com os campos do
CA2. O nome `external_id` segue o AD-23, que é o nome que a 2.4 vai persistir.

**Consequências.** (a) deixa explícito que é catálogo externo, separado dos
lotes, e lê bem no Swagger. (b) sugere que `artworks` é recurso nosso, que não
existe no banco. (c) amarra o nome ao "museu" em vez do papel do recurso.

**Recomendação:** (a).

### P2 — Cliente HTTP (dependência de produção)

**Problema.** Não há cliente HTTP nas dependências de produção.

- **(a)** Promover `httpx` para dependência de produção e usar `httpx.Client`
  síncrono, com `httpx.MockTransport` nos testes.
- **(b)** `urllib.request` da biblioteca padrão, sem dependência nova.
- **(c)** `requests`.

**Consequências.** (a) já está no lock (versão usada pelo `TestClient`), tem
timeouts separados por fase e um transporte de teste oficial, sem rede. (b) não
acrescenta nada, mas timeout, erro e teste ficam mais manuais e difíceis de
explicar. (c) traz uma dependência nova sem transporte de teste equivalente.

**Recomendação:** (a).

### P3 — Timeout, status e código de erro da AIC

**Problema.** Definir o limite de espera e como cada falha chega ao cliente.

- **(a)** Um só erro para toda falha da AIC (timeout, conexão, DNS, 5xx, 429,
  JSON malformado, formato inesperado): **503** com código novo
  `catalog_unavailable` e mensagem "O catálogo do museu está indisponível no
  momento. Tente novamente em instantes." Timeouts propostos: conexão 3 s,
  leitura 5 s, sem novas tentativas automáticas.
- **(b)** Separar `catalog_timeout` (504), `catalog_bad_response` (502) e
  `catalog_rate_limited` (503).
- **(c)** Como (a), com uma nova tentativa automática em timeout ou 5xx.

**Consequências.** (a) é simples para a interface (uma mensagem) e não revela
detalhe da integração; o log do servidor guarda a categoria para diagnóstico. (b)
dá mais informação ao cliente sem ação diferente para o usuário. (c) pode dobrar
a espera (até ~16 s) e pesa no limite de requisições da AIC. Em todas, o 404 de
obra e o 422 seguem a P4 e a P6 da 2.1.

**Recomendação:** (a).

### P4 — Detalhe de obra inexistente ou fora do domínio público

**Problema.** A interface só oferece obras do domínio público, mas a rota de
detalhe pode receber qualquer número.

- **(a)** Ambos → 404 `not_found` ("Recurso não encontrado."), indistinguíveis.
- **(b)** Inexistente → 404; fora do domínio público → código próprio (ex.: 422
  `artwork_not_public_domain`).
- **(c)** Devolver a obra com `is_public_domain: false` e deixar a interface
  decidir.

**Consequências.** (a) mantém a regra do AD-23 no servidor e o contrato mínimo.
(b) antecipa a mensagem que a 2.4 precisa na criação ("recusada com motivo
claro"), mas essa recusa é da 2.4, no `POST` do lote. (c) expõe obra que o AD-23
não deixa virar lote. Em todas, o serviço interno distingue os dois casos, para a
2.4 poder reaproveitá-lo sem eu decidir agora o que ela responde.

**Recomendação:** (a).

### P5 — Obras sem imagem

**Problema.** Há obras de domínio público sem `image_id`, e o enunciado pede lote
"com imagem".

- **(a)** Excluir da busca: filtro na consulta à AIC (`image_id` existente) e
  reconferência por item no back-end, como o domínio público.
- **(b)** Listar com placeholder e um aviso "sem imagem"; a 2.4 decide se aceita.
- **(c)** Listar com placeholder, sem aviso.

**Consequências.** (a) simplifica a 2.4 e a vitrine; a lista pode ficar menor
para alguns termos. (b) e (c) mostram obras que provavelmente não poderão virar
lote, e (c) as confunde com imagem que falhou. Em todas, o placeholder continua
necessário para imagem que falha ao carregar (CA3).

**Recomendação:** (a).

### P6 — Quem monta a URL IIIF e com que tamanho

**Problema.** O AD-22 manda o navegador carregar do IIIF, e o AD-23 pede a
"referência/URL IIIF" no snapshot.

- **(a)** O back-end devolve `image_id` e `image_url`, montada com base fixa no
  código: `https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg`
  (largura que a documentação da AIC recomenda, a confirmar no smoke test). A
  lista e o detalhe usam a mesma URL; o CSS ajusta o tamanho.
- **(b)** O back-end devolve `image_id`; o front-end monta a URL com a base fixa e
  larguras por contexto (ex.: menor na lista, 843 no detalhe).
- **(c)** Montar com o `config.iiif_url` que vem na resposta da AIC.

**Consequências.** (a) concentra a regra num só lugar e é a que a 2.4 pode
persistir; a lista baixa imagens maiores que o necessário. (b) economiza banda,
mas espalha conhecimento do IIIF pelo front e larguras fora da recomendada podem
ser mais lentas. (c) deixa a AIC decidir o host do `src` da imagem. Em todas, o
`image_id` é validado (formato UUID) antes de entrar na URL.

**Recomendação:** (a).

### P7 — Termo de busca, quantidade e paginação

**Problema.** Limites de entrada e quantos resultados mostrar.

- **(a)** `q` obrigatório, de 1 a 100 caracteres depois de `strip`; 20 resultados
  por página; parâmetro `page` (1 a 10) e `has_next` na resposta.
- **(b)** `q` com os mesmos limites; só os 20 primeiros resultados, sem
  paginação.
- **(c)** Como (b), com `limit` escolhido pelo cliente até 50.

**Consequências.** (a) permite ir além dos 20 primeiros, ao custo de um controle,
mais um estado na interface e mais testes. (b) é a menor entrega: termos
genéricos mostram só os 20 mais relevantes, e eu refino o termo. (c) põe na mão
do cliente quanto peso cada busca coloca na AIC. Em todas, `q` vazio ou só com
espaços → 422; o limite de paginação da AIC é confirmado no smoke test.

**Recomendação:** (b).

### P8 — Cache e identificação perante a AIC

**Problema.** A AIC tem limite de requisições e pede identificação do cliente; a
documentação dela fala em cabeçalho `AIC-User-Agent` com nome do projeto e
contato (a confirmar no smoke test).

- **(a)** Sem cache no servidor; enviar `AIC-User-Agent` com o nome do projeto e
  a URL pública do repositório, sem e-mail pessoal; respostas das rotas da 2.3
  com `Cache-Control: no-store`.
- **(b)** Como (a), mais um cache em memória com TTL curto (ex.: 5 min) por termo
  e por obra.
- **(c)** Sem cache e sem cabeçalho de identificação.

**Consequências.** (a) é a mais simples e coerente com o uso de um só leiloeiro;
cada busca é uma chamada. (b) reduz chamadas, mas acrescenta estado em memória,
expiração e testes, e esconde por alguns minutos uma AIC que voltou ou caiu. (c)
ignora o pedido da AIC. O contato no cabeçalho é escolha minha: não coloco e-mail
sem eu dizer qual.

**Recomendação:** (a).

### P9 — Smoke test e "API indisponível" (Q7)

**Problema.** O AD-23 pede que o smoke test cubra a API indisponível, o que não é
verificável contra a API real.

- **(a)** Script manual `backend/scripts/smoke_artic.py`, fora do `verify`: chama
  o nosso serviço de catálogo contra a AIC real (busca, detalhe, filtro, campos e
  um `HEAD`/`GET` da imagem IIIF) e, para a indisponibilidade, roda o mesmo
  serviço apontado para um endereço local sem servidor (porta fechada),
  conferindo que o resultado é o erro da P3. A base da AIC entra como parâmetro do
  serviço, não como variável de ambiente da aplicação.
- **(b)** Smoke test só com a API real; a indisponibilidade fica provada apenas
  pelas falhas simuladas do `pytest` (que existem de qualquer forma pelo CA8).
- **(c)** Smoke test como testes `pytest` com marcador próprio (ex.: `-m smoke`),
  excluídos por padrão do `verify`.

**Consequências.** (a) cobre os seis itens do AD-23 num comando só e exercita o
caminho real de rede (DNS/conexão recusada), que o transporte falso não exercita.
(b) é menor, mas deixa o sexto item fora do smoke test, contra a letra do AD-23.
(c) reaproveita o `pytest`, mas exige configuração para nunca rodar no `verify`
por engano.

**Recomendação:** (a). Registro a resolução da Q7 no `docs/ARQUITETURA.md`.

### P10 — Front-end: onde fica a busca e ferramenta de teste

**Problema.** Não há roteador (a 2.2 P15 o deixou para a 2.5) nem ferramenta de
teste de front-end (Q10 aberta).

- **(a)** Sem dependência nova: logado como `AUCTIONEER`, o `App.tsx` mostra a
  seção "Buscar obras" do painel; o detalhe abre na mesma tela; `BIDDER` continua
  como hoje. Validação manual no navegador; sem testes automatizados de
  front-end (Q10 continua aberta).
- **(b)** Introduzir `react-router` agora, com uma rota própria para a busca.
- **(c)** Como (a), mais Vitest e Testing Library, fechando essa parte da Q10.

**Consequências.** (a) entrega o critério com o mínimo e mantém a decisão de
navegação para a 2.5, que precisa de rotas de verdade (vitrine e página do lote).
(b) antecipa essa decisão. (c) cria a base de testes de front-end, ao custo de
escopo e tempo de `verify` num dia já cheio. A composição visual (lista, detalhe,
estados, responsividade) é definida no `bmad-spec`, não aqui.

**Recomendação:** (a).

### Orientação técnica (não é decisão nova)

- O cliente da AIC fica guardado na aplicação (como `app.state.session_config`) e
  é substituído nos testes; nada de rede na importação ou na criação da app.
- O back-end lê só os campos necessários (`fields=` na consulta) e transforma a
  resposta da AIC num modelo nosso: o front-end nunca recebe o JSON da AIC
  repassado.
- Os textos da AIC são exibidos como texto (o React escapa); `artist_display`
  pode ter quebra de linha.

## Tarefas e subtarefas

- [x] **T1 — Planejar comigo (todas as CAs).** Decidir P1 a P10 e registrá-las
  nesta story, em primeira pessoa e com a alternativa descartada, antes de
  qualquer código. Como há front-end, seguir o ciclo da seção "Front-end".
- [x] **T2 — Dependência e cliente (CA4, CA6, CA7, P2, P3, P8).** Cliente HTTP
  síncrono com timeouts, host fixo, sem redirecionamento para outro host,
  cabeçalho de identificação; guardado na app e substituível nos testes.
- [x] **T3 — Serviço de catálogo (CA1, CA2, CA6, P4, P5, P6, P7).** Busca e
  detalhe; filtro de domínio público na consulta e por item; tratamento de obra
  sem imagem; montagem da URL IIIF; conversão para os modelos nossos; distinção
  interna entre inexistente e fora do domínio público; toda falha da AIC vira a
  falha da P3.
- [x] **T4 — Rotas (CA4, CA5, CA6, CA7, P1, P3, P6.1).** Duas rotas `GET` com
  `api_route(..., policy=AccessPolicy.AUCTIONEER)` (busca e detalhe) e a rota
  pública de imagem com `AccessPolicy.PUBLIC`, handlers `def`,
  `responses=error_responses(...)`, `Cache-Control` da P8; código novo no
  catálogo de erros.
- [x] **T5 — Fixtures e testes do back-end (CA1–CA8).** Fixtures versionadas da
  AIC; matriz abaixo; guarda contra chamada real no `pytest`.
- [x] **T6 — Smoke test (CA9, P9).** Script fora do `verify`, documentado; eu o
  executo e a saída real entra nesta story.
- [x] **T7 — Interface (CA3, CA10, P10).** Cliente tipado em `src/api/`, tela de
  busca e detalhe, estados, mensagens pelo `code`, placeholder local, imagem com
  dimensões estáveis e `loading="lazy"` fora do primeiro viewport; só para
  `AUCTIONEER`. Fonte do layout: `bmad-spec`.
- [x] **T8 — Verificar e documentar (CA11).** `./verify.sh` completo com a saída
  real; README; `docs/uso_de_ia.md`; Q7 em `docs/ARQUITETURA.md`; esta story e o
  `sprint-status.yaml`. Parar na 2.3.

## Matriz de testes esperados

| Grupo | Casos |
| --- | --- |
| Busca (fixtures) | Resultado só com domínio público; item com `is_public_domain` falso, ausente ou `null` na resposta é descartado; item sem imagem conforme P5; campos do `ArtworkSummary`; termo normalizado; resultado vazio → `items: []` com 200; consulta enviada à AIC contém o filtro de domínio público e os `fields=` esperados. |
| Detalhe (fixtures) | Todos os campos do CA2; campo ausente → `null`; URL da fonte e URL IIIF corretas; obra inexistente (404 da AIC) e obra fora do domínio público conforme P4. |
| Falhas da AIC | Timeout de conexão e de leitura; conexão recusada; 500/502/503; 429; JSON malformado; JSON com formato inesperado (ex.: `data` ausente, tipo errado) → status e código da P3, mensagem do catálogo, sem corpo/URL/cabeçalho da AIC na resposta; nenhum 500. |
| Isolamento | Com a AIC falhando, `/health`, login, `/api/me` e logout respondem normalmente; importar e criar a app não chama a AIC. |
| Entrada | `q` ausente, vazio, só espaços e acima do limite → 422 sanitizado; `external_id` não numérico, zero, negativo e com caminho (`../`, `%2F`) → 422 ou 404 do roteador, nunca chamada à AIC com host ou caminho alterado; paginação conforme P7. |
| Imagem | `image_id` fora do formato esperado não vira URL nem chama a AIC; `image_url` do contrato é sempre `/api/catalog/images/{image_id}`; a rota de mídia só chama o host IIIF fixo (URL upstream exata, cabeçalhos, sem redirecionamento), devolve os bytes do fixture, 404 do upstream vira 404, e toda outra falha vira 503 `catalog_unavailable`. |
| Política (PostgreSQL real) | Sem login → 401; `BIDDER` → 403; `AUCTIONEER` → 200; nos dois primeiros casos o cliente falso não é chamado; busca e detalhe aparecem no teste de política como `AUCTIONEER` e a rota de imagem como `PUBLIC`. |
| Sem efeito colateral | As rotas não gravam no banco (contagem/estado inalterados); `HEAD`/`OPTIONS` não chamam a AIC além do que o `GET` faria e não alteram estado. |
| Sem rede real | A guarda reprova uma tentativa de chamar o host da AIC durante o `pytest`. |
| OpenAPI | Os três caminhos novos no schema, com o envelope de erro documentado (401/403/404/422/503 na busca e no detalhe; 404/422/503 e `image/jpeg` na imagem). |
| Catálogo de erros | O código novo da P3 e sua mensagem entram no teste de igualdade exata de `test_errors.py`. |
| Front | `lint`, `tsc --noEmit` e build no `verify`; validação manual no navegador (roteiro no build): buscar, nenhum resultado, termo inválido, AIC indisponível (back-end apontado para endereço fechado ou rede bloqueada), imagem quebrada → placeholder, detalhe, `BIDDER` sem busca, 320 px e desktop largo. Testes automatizados de front-end só se P10 (c). |
| Smoke (fora do `verify`) | Os seis itens do AD-23, com a saída real registrada. |

## Regressões que devem continuar verdes

- Os 574 testes do último `verify` da 2.2 (contagem registrada naquela story; a
  nova contagem vem só do `verify` desta story).
- `/health` 200 sem banco e sem rede; criação da app sem banco.
- Login, logout, `/api/me`, cookie e seed da 2.2 sem mudança de comportamento.
- Teste de política e meta-teste da 2.2 sem afrouxar o verificador.
- Proteção de escrita da 2.1 intacta (as rotas novas são `GET`).
- SPA, fallback de rotas do cliente e 404 JSON sob `/api/`.
- WebSocket técnico `/api/infra-check/ws`, público, até a 4.1.
- `docker build` no `verify`.

`test_openapi.py` e `test_errors.py` mudam só para acrescentar o que é novo;
nenhuma asserção existente é removida ou enfraquecida.

## Persistência, seed e integrações

- **Banco/migrations:** nenhuma. Nenhuma tabela, coluna ou revisão Alembic nova.
- **Seed:** nenhum efeito. O seed continua offline e só com as contas da 2.2; o
  lote demo é da 2.4.
- **Integração externa:** API do Art Institute of Chicago (busca e detalhe de
  obras) e IIIF da AIC (imagem), ambos chamados só pelo back-end; o navegador
  pede a imagem à nossa rota same-origin. Nenhum byte de imagem é guardado.
- **Segredos:** nenhum segredo novo. A AIC não exige chave.
- **Deploy:** nenhuma variável nova no Render (a menos que a decisão da P9 ou da
  P8 crie uma, o que as recomendações evitam).

## Arquivos prováveis

| Área | Arquivo | Ação |
| --- | --- | --- |
| Back-end | módulo novo do catálogo da AIC (cliente, serviço, modelos e rotas; nome no plano técnico, ex.: `backend/app/catalog.py`) | novo |
| Back-end | `backend/app/main.py` | alterado (registrar rotas, cliente na app) |
| Back-end | `backend/app/errors.py` | alterado (código da P3) |
| Infra | `backend/pyproject.toml`, `backend/uv.lock` | alterados (P2) |
| Smoke | `backend/scripts/smoke_artic.py` | novo (P9) |
| Testes | fixtures JSON da AIC (ex.: `backend/tests/fixtures/artic/`) | novos |
| Testes | testes do catálogo (serviço, rotas, falhas, política) e da rota de imagem | novos |
| Testes | `backend/tests/test_openapi.py`, `backend/tests/test_errors.py`, `backend/tests/conftest.py` (guarda de rede, se for o lugar) | alterados |
| Front-end | `frontend/src/api/catalog.ts` | novo |
| Front-end | componentes da busca e do detalhe (nomes no `bmad-spec`) | novos |
| Front-end | `frontend/src/App.tsx`, `frontend/src/App.css` | alterados |
| Front-end | placeholder local em `frontend/public/` | novo |
| Docs | `README.md`, `docs/uso_de_ia.md`, `docs/ARQUITETURA.md` (Q7 e revisão do AD-22) | alterados |
| BMAD | esta story, `sprint-status.yaml` | alterados |
| Sem mudança | migrations, `app/seed.py`, `app/users.py`, `app/csrf.py`, `app/access.py`, `app/auth.py`, `Dockerfile`, `compose.yaml`, `scripts/start.sh`, `verify.sh` | intocados |

## Front-end

**Esta story tem front-end: SIM.** O `epics.md` pede busca "no painel", imagem
da obra (pela nossa rota de mídia) ou placeholder, detalhe com os campos do snapshot e mensagem clara em
português quando a AIC cair. Isso é tela nova, componente visual e fluxo de
interação.

A fase seguinte usa obrigatoriamente:

- `@docs/FRONTEND-WORKFLOW.md`
- `@_bmad-output/planning-artifacts/DESIGN.md`
- `@_bmad-output/planning-artifacts/EXPERIENCE.md`

A busca não é a Vitrine; o `VITRINE-BLUEPRINT.md` não é leitura obrigatória
desta story.

Ciclo:

```text
bmad-spec (Opus)
→ minha aprovação
→ bmad-build (Sonnet)
→ verify
→ teste manual no navegador
→ bmad-code-review (Opus, nova sessão)
→ correções / re-review
→ commit feito por mim
```

## Fora de escopo

- Criar lote, copiar o snapshot para o banco, validar datas e valores do lote,
  "Meus lotes", lote demo semeado e recusa de criação de obra fora do domínio
  público (todos da 2.4).
- Vitrine, página do lote e roteador (2.5).
- Busca e filtro de lotes da vitrine (OPT1, 6.5).
- Cache persistente, fila ou nova tentativa em segundo plano para a AIC.
- Guardar, redimensionar, converter ou fazer cache de imagem no servidor, e proxy
  genérico (descartados no AD-22 revisado). O proxy de imagem controlado da P6.1
  **faz parte** desta story.
- Carteira, lances, sala, WebSocket real, auditoria, comprovante.
- Identidade visual completa e responsividade de todas as telas (6.2); dark mode
  (6.7); revisão de segurança global (6.1).
- Não crio a Story 2.4 e não uso git.

## Decisões fechadas (P1 a P11, P6.1, P7.1, P7.2, P8.1, C1 a C5)

Aprovadas por mim em 24/10/2026; o detalhe e a evidência das chamadas reais ficam em
`_bmad-output/specs/spec-story-2-3-busca-obras-aic/` (`decisions.md`,
`aic-contract.md`). A implementação seguiu todas, sem reabrir; a P6.1 (proxy de
imagem) foi aprovada depois do teste manual, que refutou o transporte direto da P6.

- **P1 Rotas.** Decidi `GET /api/catalog/artworks?q=` e
  `GET /api/catalog/artworks/{external_id}`; `catalog` deixa claro que o recurso é
  externo e `/api/lots` fica livre para a 2.4. O resumo inclui `date_display`.
  Descartei `/api/artworks/...`, que sugere recurso nosso.
- **P2 Cliente HTTP.** Decidi promover `httpx` (0.28.1, já no lock) a dependência de
  produção, `httpx.Client` síncrono em handler `def`, um cliente curto por chamada,
  `MockTransport` nos testes. Descartei `urllib.request` e `requests`.
- **P3 Falhas externas.** Decidi 503 `catalog_unavailable` para conexão, DNS,
  timeout, 3xx, 403/Cloudflare, 429, 5xx, JSON inválido e formato incompatível;
  connect 3 s, read 5 s, sem retry. O 404 real do detalhe é P4. Descartei códigos
  separados (502/504) e a nova tentativa automática.
- **P4 Detalhe inelegível.** Decidi 404 `not_found` para inexistente, fora do domínio
  público ou sem imagem; o motivo existe só no serviço (`LookupStatus`). Descartei um
  422 próprio, que anteciparia a recusa da 2.4.
- **P5 Sem imagem.** Decidi excluir da busca e do detalhe a obra sem `image_id`
  válido; o placeholder cobre só a falha de carga no navegador. Descartei listar com
  aviso "sem imagem".
- **P6 IIIF.** Decidi base fixa e `image_id` validado por regex antes de compor a URL
  (o transporte direto do navegador foi revisado pela P6.1); front com
  `referrerPolicy="no-referrer"`. Descartei usar `config.iiif_url` e montar
  a URL no front.
- **P6.1 Proxy de imagem (revisão após o teste manual).** Veja a seção "Correção
  pós-teste manual" abaixo: decidi servir a imagem por `GET /api/catalog/images/{image_id}`
  (`PUBLIC`) em vez do IIIF direto do navegador, que deu 403. Descartei manter o
  hotlink, guardar as imagens, cache no servidor e proxy genérico.
- **P7 Termo.** Decidi `q` com `strip`, 1 a 100 caracteres, 20 resultados, sem
  paginação. Descartei paginação e `limit` escolhido pelo cliente.
- **P7.1 Filtro do termo.** Decidi não depender só de `q` (que não filtra): o servidor
  constrói `bool` com `must: multi_match` (`operator: and`) e filtros de domínio
  público e `image_id` existente, em `params`; o `q` de topo só ordena. "Nenhum
  resultado" passou a ser real. Descartei só `q`.
- **P7.2 Firewall por termo.** O Cloudflare recusa alguns termos (403 → 503). Não
  filtro caracteres no servidor; a mensagem sugere outro termo.
- **P8/P8.1 Cache e identificação.** Decidi sem cache, `no-store`, e os dois
  cabeçalhos de identificação com a URL pública do Render, sem e-mail pessoal. Não é
  autenticação. Descartei cache em memória com TTL.
- **P9 Smoke e Q7.** Decidi o script manual `backend/scripts/smoke_artic.py`, fora do
  `verify`, com a indisponibilidade em `127.0.0.1:9`. Descartei `pytest -m smoke`.
- **P10 Front-end.** Decidi sem React Router, sem biblioteca de teste nova e sem
  botão "Criar lote"; ≥ 64rem lado a lado, abaixo troca de vista.
- **P11 Campos extras.** Decidi `dimensions` no detalhe e `alt_text` fora do contrato.
- **C1 a C4.** Base IIIF fixa com deriva acusada pelo smoke; `nenhum resultado` real
  pela P7.1; identificação obrigatória na prática (403 observado); o 422 global fica
  sem `no-store`, sem mecanismo especial.

## Registro de implementação (24/10/2026)

Implementei a partir da spec aprovada, sem git, sem deploy e sem ler `.env*`.

**Back-end.** `app/artic.py` (constantes, `ArticClient`, `build_search_query`,
`CatalogUnavailable`, adaptador `ArticArtwork`); `app/catalog.py` (modelos,
elegibilidade, `image_url_for`, `search_artworks`, `get_artwork`, as duas rotas
`AUCTIONEER` e a rota pública de imagem, depois da P6.1); `CATALOG_UNAVAILABLE` em `app/errors.py`; `main.py` guarda
`ArticClient()` em `app.state` e registra as rotas depois da autenticação;
`pyproject.toml` e `uv.lock` com `httpx` em produção. Sem migration, tabela nem
mudança de seed.

**Smoke.** `backend/scripts/smoke_artic.py`, fora do `verify`.

**Testes.** `tests/catalog_support.py` e 7 fixtures JSON em `tests/fixtures/artic/`;
`test_artic.py` (cliente e adaptador, sem banco), `test_network_guard.py` e a guarda
de `getaddrinfo` em `conftest.py`; `integration/test_catalog_routes.py` (PostgreSQL
real); acréscimos em `test_openapi.py`, `test_errors.py` e `test_access_policy.py`.

**Front-end.** `api/catalog.ts`, `CatalogSearch.tsx`, `ArtworkDetailPanel.tsx`,
`ArtworkImage.tsx`, `public/artwork-placeholder.svg`, seção "Catálogo" em `App.css`
e `App.tsx` mostrando a busca só para `AUCTIONEER` (`BIDDER` mantém o `h1` oculto).
Sem dependência nova.

**Documentação.** README (seção do catálogo e três itens em "Comportamentos que podem
surpreender"), `docs/uso_de_ia.md`, Q7 em `docs/ARQUITETURA.md` (questões e histórico,
nenhuma AD alterada), esta story e o `sprint-status.yaml`.

### Desvios e ajustes em relação à spec

- `except httpx.HTTPError` residual no cliente vira `bad_shape`, para nada escapar além
  de `CatalogUnavailable` (a spec pedia "nada mais escapa", mas só listava
  `TimeoutException` e `TransportError`).
- `FAILURES_BOTH`, `raising`, `status_handler` e `body_handler` ficaram em
  `catalog_support.py` (a spec os descrevia nos testes), para os testes do cliente e das
  rotas compartilharem a mesma lista de falhas.
- A fixture `artwork_27992.json` foi escrita à mão e depois alinhada aos valores que o
  smoke e a rota viram na AIC real (`artist_display` e `date_display` do 27992).
- No front, abaixo de 64rem a vista do detalhe oculta também o cabeçalho e o
  formulário, não só a lista, para o detalhe ocupar a tela; o termo e os resultados
  ficam no estado. O botão "← Voltar aos resultados" existe sempre no DOM, mas só é
  exibido na vista estreita do detalhe.
- Ao enviar a busca, o foco vai para o campo na hora (o botão fica desabilitado
  durante a busca e perderia o foco).
- Um 422 vindo do servidor volta ao estado inicial com a mensagem do campo.
- O roteiro manual no navegador (`test-plan.md` §7) é meu e **não foi executado** por
  esta sessão: não houve navegador. Os 10 estados, o placeholder, 320 px, desktop
  largo e o teclado seguem sem verificação visual.

### Evidências (comandos executados em 24/10/2026)

- Testes direcionados: `tests/test_artic.py` e `tests/test_network_guard.py`: 64
  passed; `tests/integration/test_catalog_routes.py`: 66 passed.
- `./verify.sh` completo: exit 0. Ruff check e `ruff format --check` limpos;
  **pytest: 707 passed** (a 2.2 registrou 574; os testes existentes seguem sem
  alteração de asserção, só acréscimos nos três arquivos de contrato); ESLint, `tsc
  --noEmit` e build do Vite sem erros; `docker build` concluído (o estágio de runtime roda
  `uv sync --frozen --no-dev`, que agora inclui o `httpx`).
- Smoke real contra a AIC, `cd backend && uv run python -m scripts.smoke_artic`, exit 0:

```text
PASS 1 Busca real — 'monet' → 20 obras; 'qxzvkwjq' → 0
PASS 2 Detalhe real — 27992: A Sunday on La Grande Jatte — 1884
PASS 3 is_public_domain=true — 20 itens com is_public_domain=true; 129884 → NOT_PUBLIC_DOMAIN
PASS 4 Imagem IIIF — 200 image/jpeg; config.iiif_url e website_url iguais às constantes
PASS 5 Campos usados — 11 campos presentes; null neste detalhe: nenhum
PASS 6 API indisponível (simulada) — http://127.0.0.1:9 → CatalogUnavailable(connect)
6/6 PASS
```

- Conferência extra das rotas reais, com a app em processo, login do leiloeiro e o
  banco `_test`: busca "monet" → 200 com 20 itens e `no-store`; "qxzvkwjq" → 200
  `{"items": []}`; detalhe 27992 → 200 com os 12 campos; 129884 e 999999999 → 404
  `not_found`; o termo `<script>` → 503 `catalog_unavailable` (403 do firewall,
  P7.2), com `artic request failed: operation=search reason=http_403` no log.

### Riscos e limitações restantes

- ~~A imagem IIIF sem `AIC-User-Agent` no navegador só se confirma no teste manual.~~
  Confirmada como falha (403) e corrigida pelo proxy da P6.1; veja a seção "Correção
  pós-teste manual".
- DNS lento não é limitado pelo `connect` no modo síncrono; o threadpool isola o event
  loop (aceito na spec).
- 60 req/min por IP anônimo da AIC, compartilhado no Render; sem cache, 429 vira 503.
- Termos legítimos recusados pelo firewall aparecem como "indisponível".
- O Starlette 1.9 avisa que `TestClient` sobre `httpx` está deprecado (`httpx2`); o
  aviso aparece nos testes e não afeta o runtime.
- Sem teste automatizado de front-end (Q10 segue aberta).

## Correção pós-teste manual: imagens por proxy same-origin (24/10/2026)

**O que o teste manual mostrou.** Busca, detalhe, lista vazia, loading, offline e
placeholder funcionavam, mas **todas** as imagens IIIF falharam no navegador com
`default.jpg` → HTTP 403 (Cloudflare), na lista e no detalhe; a interface caiu no
placeholder em todas as obras. O smoke tinha obtido 200 `image/jpeg` porque envia
`User-Agent` e `AIC-User-Agent`, que a tag `<img>` não consegue enviar. A suposição
aprovada (CAP-10, AD-22: o navegador carrega o IIIF direto) foi **refutada**.

**P6.1 — o que decidi.** Troquei só o transporte da imagem, por um proxy controlado
no nosso back-end: `GET /api/catalog/images/{image_id}` →
`https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg` → JPEG. Os bytes
continuam não armazenados, não persistidos e sem cache. A rota é `PUBLIC` (obras de
domínio público, nenhum dado de conta, e a vitrine da 2.5 precisará das mesmas
imagens; descartei `AUCTIONEER` para não mudar o contrato de novo); busca e detalhe
seguem `AUCTIONEER`. Aceita só `image_id` (mesmo regex da P6; inválido → 422 sem
chamada), com host, esquema, caminho, tamanho e formato fixos, `follow_redirects=False`
e os cabeçalhos da P8. Upstream 200 `image/jpeg` com assinatura JPEG e até 5 MiB →
200 com os bytes (`no-store`, `nosniff`); upstream 404 → 404 `not_found`; 3xx, 403,
429, 5xx, conexão, timeout, tipo/corpo inesperado ou grande demais → 503
`catalog_unavailable`, sem expor corpo do upstream. `image_url` do contrato passou a
ser `/api/catalog/images/{image_id}`. Descartei o hotlink direto, baixar e guardar a
imagem, proxy genérico, `StreamingResponse`, cache e fetch/blob no navegador.
Registrado como revisão da consequência técnica do AD-22 em `docs/ARQUITETURA.md`.

**Implementação.** `app/artic.py`: `iiif_image_url` (movida de `catalog.py`),
`ArticClient.get_image`, `iiif_base_url` no construtor (só testes e smoke),
`MAX_IMAGE_BYTES`, e a classificação de status compartilhada com `_get`;
`app/catalog.py`: `image_url_for`, e a rota de imagem; testes novos
(`test_catalog_image_route.py`, `get_image` em `test_artic.py`, fixture
`image_sample.jpg`) e as asserções de `image_url` em `test_catalog_routes.py`
trocadas para a URL same-origin (mudança do contrato, não afrouxamento); acréscimos em
`test_openapi.py` e `test_access_policy.py`; smoke item 4 passou a exercitar também
`get_image`; front-end: só o comentário de `ArtworkImage.tsx` (o componente já usava
`image_url` do contrato, `<img>`, placeholder no `onError` e `no-referrer`).
Documentos da spec (SPEC, decisions, aic-contract, backend-contract, frontend-catalog,
test-plan, implementation-map), `docs/ARQUITETURA.md` (AD-22), README e
`docs/uso_de_ia.md` atualizados.

**Evidências (comandos executados em 24/10/2026).**

- Direcionados: `test_catalog_image_route.py` 33 passed; `test_artic.py -k get_image`
  22 passed; os arquivos de catálogo, contrato, política e guarda de rede juntos: 244
  passed.
- `./verify.sh` completo: exit 0; Ruff check e format limpos; **763 passed** (707 antes
  desta correção); ESLint, `tsc`, build do Vite e `docker build` sem erro.
- Smoke real, exit 0, 6/6 PASS; o item 4 agora lê:
  `PASS 4 Imagem IIIF — 200 image/jpeg; get_image → 197727 bytes JPEG; config.iiif_url e website_url iguais às constantes`.
- A rota real contra o IIIF da AIC, em processo e sem sessão: imagem do 27992 → 200
  `image/jpeg`, `no-store`, 197727 bytes, assinatura `ffd8ff`; UUID inexistente → 404
  `not_found`; `abc` → 422 `validation_error` com `loc` `["path","image_id"]`.
- **Não fiz** o teste manual no navegador nem o code review: o reteste das imagens é
  meu. O restante do roteiro manual segue pausado até lá.

**Riscos novos.**

- Sem cache (`no-store`, por instrução): cada miniatura e cada abertura de detalhe são
  uma chamada do servidor à AIC, e a miniatura e a imagem grande usam a mesma URL de
  843 px. Uma busca com 20 resultados dispara até 20 chamadas contra o limite de 60
  por minuto por IP; excedido, a AIC responde 429 e as imagens caem no placeholder.
  Cache de navegador ou de servidor ficou fora desta correção e é decisão minha.
- A rota é pública: qualquer pessoa pode pedir imagens por `image_id` válido e gastar
  a cota da AIC do nosso IP; mitigado só por validar o UUID, o teto de 5 MiB e os
  timeouts. Rate limiting da nossa rota não existe.
- Os bytes passam pela memória do processo (até 5 MiB por requisição simultânea), e a
  chamada ao IIIF ocupa uma thread do pool durante o download.

## Reteste manual (24/10/2026)

Teste feito por mim no navegador. Registro só o que observei:

**Antes da correção das imagens.**

- Estado inicial do catálogo, loading em rede limitada, busca válida (`GET
  /api/catalog/artworks?q=monet` e `q=portrait` → 200), 20 resultados, nenhum
  resultado, detalhe da obra (200) e erro/offline de comunicação.
- Toda imagem `default.jpg` do IIIF retornava HTTP 403 no navegador, na lista e no
  detalhe, e o placeholder aparecia em todas as obras. Isso refutou a suposição de
  carregar o IIIF direto e motivou a P6.1.

**Depois do proxy same-origin.**

- As miniaturas reais carregaram, e o detalhe com a imagem real também.
- A aba Rede mostrou `/api/catalog/images/{image_id}`, com várias respostas 200
  `image/jpeg`.
- Pelo menos uma imagem retornou 503; nesse caso o placeholder local apareceu
  corretamente e os metadados da obra continuaram disponíveis.
- `BIDDER` não recebeu acesso ao catálogo.
- Atualizar a página manteve a sessão e devolveu o catálogo ao estado inicial.
- No mobile, o fluxo lista → detalhe → "Voltar" funcionou.

**Não registro como observado:** a navegação por teclado, a largura exata de 320 px e
cada um dos dez estados do roteiro individualmente. Esses itens faziam parte do
roteiro (`test-plan.md` §7), mas não tenho evidência explícita deles aqui.

O 503 de uma imagem é compatível com o risco D1 abaixo (chamadas repetidas à AIC sem
cache); não investiguei a causa daquele caso. O code review (Opus, sessão separada)
rodou depois disso: 0 BLOCKER, 0 HIGH, 1 MEDIUM documental (M1, corrigido nesta
rodada), L1 a L3 e D1.

## Correções do code review (24/10/2026)

- **M1 (corrigido).** A story e o `implementation-map.md` ainda descreviam o IIIF
  direto do navegador, o back-end que nunca baixa bytes, duas rotas `AUCTIONEER` e o
  proxy de imagem como fora de escopo. Reescrevi o contrato principal (objetivo, CA3,
  CA5, tabela de políticas, resumo do AD-22, matriz de testes, integração externa,
  fora de escopo, registro de implementação) e o `implementation-map.md`, em vez de só
  acrescentar notas.
- **L2 (corrigido).** Removi o texto oculto da miniatura (`ArtworkImage.tsx`): na
  falha, a miniatura mostra apenas o placeholder com `alt=""`, e o título é a primeira
  informação anunciada pelo botão; o detalhe mantém a legenda visível "Imagem
  indisponível".
- **L3 (registrado).** O reteste manual acima, aqui e em `docs/uso_de_ia.md`.
- **Sincronia dos resumos.** O resumo do AD-22 em `CLAUDE.md` e a referência de imagem
  em `_bmad-output/planning-artifacts/epics.md` (AR9 e o critério da Story 2.3)
  foram atualizados para o AD-22 revisado; nada mais nesses arquivos mudou.
- **L1 (não alterado, por decisão minha).** A guarda de rede do `conftest.py` não
  trata `HTTPS_PROXY`/`ALL_PROXY`: é um risco teórico, não um bug atual (os testes do
  catálogo injetam `MockTransport`, e o próprio review confirmou que o caso não passa
  em silêncio). Registrado em `deferred-work.md`.
- **D1 (mantido).** Rota de imagem `PUBLIC`, sem cache, 843 px, sem miniatura
  alternativa e sem nova camada de armazenamento. Não mudei P8 nem P6.1. Limitações
  aceitas e adiadas (também em `deferred-work.md`): uma busca de 20 resultados pode
  disparar várias chamadas de mídia; não sei se a cota do IIIF é compartilhada com a
  da API; cache e tamanho menor para a miniatura ficam fora da Story 2.3.

**Evidências das correções do review (comandos executados em 24/10/2026).** O L2 só
mexe no front (a Story não tem teste automatizado de front, Q10): `npm run lint`,
`npm run typecheck` e `npm run build` sem erro. `./verify.sh` completo: exit 0, Ruff
check e format limpos, **763 passed** (igual ao do reviewer), ESLint, `tsc`, build do
Vite e `docker build` sem erro. Não rodei o smoke real de novo: nenhum código da
integração com a AIC mudou, e o proxy de imagem ficou intocado.

## Registro e status

Status: **done**. Story criada e especificada em 24/10/2026; implementada em
24/10/2026; imagens corrigidas (P6.1) no mesmo dia depois do primeiro teste manual;
reteste manual, code review, correções (M1, L2, L3) e re-review final concluídos em
24/10/2026, sem BLOCKER, HIGH ou MEDIUM pendente. L1 e D1 ficam em
`deferred-work.md`. O commit é meu.
