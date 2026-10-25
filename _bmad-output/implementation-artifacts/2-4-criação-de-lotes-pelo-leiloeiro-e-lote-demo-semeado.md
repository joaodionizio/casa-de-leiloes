# Story 2.4 — Criação de lotes pelo leiloeiro e lote demo semeado

Status: done

Chave do sprint: `2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado`
Épico: 2. Data de criação: 24/10/2026.

## Story e objetivo

Como leiloeiro, e como avaliador que chega à aplicação,
quero criar lotes a partir de obras buscadas e encontrar um lote demo já aberto,
para que obras entrem em leilão pelas mesmas regras, com ou sem intervenção manual.

Nesta story entrego: a tabela `lots` (migration Alembic); a criação de lote pelo
`AUCTIONEER`, a partir de uma obra elegível do catálogo da Story 2.3, com o
**snapshot** da obra copiado para o nosso PostgreSQL; lance inicial e incremento
mínimo em centavos; início e fim validados com a hora do banco; o lote associado
ao leiloeiro da sessão; a lista mínima "Meus lotes" exigida pelo `epics.md`; o
formulário de criação na interface; o lote demo semeado a partir de uma fixture
versionada, offline e idempotente; testes em PostgreSQL real; documentação.

Depois de criado, o lote não depende mais da AIC para nenhum dado de negócio. Só a
imagem continua vindo do museu, pelo proxy same-origin do AD-22 revisado. O lote
criado fica disponível para a Story 2.5 exibir na vitrine.

As questões P1 a P9 foram decididas por mim no `bmad-spec`, antes de qualquer
código, e a spec aprovada (`_bmad-output/specs/spec-story-2-4-criacao-lotes/`) é o
contrato canônico; as decisões finais estão em "Decisões fechadas" e a
implementação em "Registro de implementação". O texto de "Questões abertas" é o
registro histórico de antes da decisão.

## Fontes e base real

Uso `CLAUDE.md`, `docs/ARQUITETURA.md` (AD-3, AD-5, AD-6, AD-8, AD-9, AD-11,
AD-12, AD-16, AD-17, AD-19, AD-22, AD-23, AD-24, AD-26, AD-27, AD-30 e as questões
Q4 e Q8), `docs/FRONTEND-WORKFLOW.md`, `DESIGN.md`, `EXPERIENCE.md`,
`_bmad-output/planning-artifacts/epics.md` (Story 2.4, FR3, FR19),
`sprint-status.yaml`, `docs/desafio-elite-dev.md` (painel do leiloeiro, dados de
teste), as Stories 2.1, 2.2 e 2.3 e a spec da 2.3 (`SPEC.md`,
`backend-contract.md`, `aic-contract.md`), só para o contrato de `ArtworkDetail`.

**Título e escopo conferidos no `epics.md`.** O título exato é **"Criação de lotes
pelo leiloeiro e lote demo semeado"**; o slug real do `sprint-status.yaml` é
`2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado`. ADs declaradas pelo
`epics.md`: AD-3, AD-6, AD-12, AD-22, AD-23, AD-24, AD-30. Dependência declarada:
**Q4** (ordem na inicialização e definição de "lote demo realmente aberto"), que
vira a P8. Cobertura: FR3 e a parte de lote do FR19.

**Divergências encontradas:**

- **"Meus lotes" está no critério do `epics.md`.** O primeiro critério diz que o
  lote "fica associado a mim **e aparece na lista dos meus lotes no painel**". A
  lista de "ENTRA" da instrução desta sessão não cita a lista, e a de "NÃO ENTRA"
  não a exclui (exclui busca/filtro de lotes, que é OPT1). Como a story/`epics.md`
  está acima do resto, incluo uma lista mínima, só leitura, sem estado derivado,
  sem resultado, sem cancelar (P9). Resultado e total recebido continuam na 4.5;
  cancelar, na 3.6.
- **Nome do arquivo da 2.1.** A instrução cita
  `2-1-formato-de-erro-e-validação-de-origem.md`; o arquivo real é
  `2-1-formato-de-erros-e-validacao-de-origin.md`. Li o real.
- **UX.** O `epics.md` diz que não há documento de UX; depois dele aprovei
  `DESIGN.md` e `EXPERIENCE.md`, que o `CLAUDE.md` torna vinculantes para
  front-end. Sigo o `CLAUDE.md`, como na 2.3.
- **AD-3 pede CHECK "não negativo"**; para lance inicial e incremento proponho
  `> 0` (P5), mais estrito e compatível com o AD-3 e com o critério do `epics.md`
  ("valores não positivos onde não cabem").
- **A fixture da 2.3 não chega à imagem de produção.** O `.dockerignore` exclui
  `backend/tests`, e o `Dockerfile` copia só `backend/app`, `migrations`,
  `alembic.ini` e `scripts/start.sh`. A fixture do seed precisa morar em
  `backend/app/` (P8).
- **`clean_users` vai quebrar.** O fixture `clean_users` de `tests/conftest.py`
  faz `TRUNCATE users`; com a FK de `lots.auctioneer_id` para `users`, isso falha.
  Será ajustado para limpar `lots` antes (ou `TRUNCATE ... CASCADE` restrito ao
  banco `_test`), sem afrouxar nenhuma asserção.
- A skill `bmad-create-story` não está instalada em `.claude/skills/`. Sigo a
  estrutura das stories 2.1 a 2.3.

**Base existente (conferida nos arquivos, sem git):**

- `backend/app/catalog.py`: `get_artwork(client, external_id) -> ArtworkLookup`
  com `LookupStatus` (`FOUND`, `NOT_FOUND`, `NOT_PUBLIC_DOMAIN`, `NO_IMAGE`) e
  `ArtworkDetail` (`external_id`, `title`, `artist_display`, `date_display`,
  `image_id`, `image_url`, `medium_display`, `dimensions`, `department_title`,
  `artwork_type_title`, `credit_line`, `source_url`). A docstring já diz: "A 2.4
  reusa `get_artwork()` sem reimplementar o parsing". `image_url` é a rota nossa
  `/api/catalog/images/{image_id}`; `source_url` é derivada do `id`.
  `CatalogUnavailable` atravessa o serviço; só a rota traduz para 503
  `catalog_unavailable`.
- `backend/app/artic.py`: `IMAGE_ID_PATTERN`, `ArticClient` (timeouts connect 3 s,
  read 5 s, sem retry). `app.state.artic_client` é substituído nos testes por um
  `ArticClient` com `httpx.MockTransport`.
- `backend/app/access.py`: `api_route(..., policy=AccessPolicy.AUCTIONEER)`,
  `require_auctioneer` (devolve o `User`), `NO_STORE`. Política resolve antes do
  corpo (2.2 P8).
- `backend/app/csrf.py`: todo `POST` em `/api` exige `Origin`/`Referer` igual a
  `APP_ORIGIN` e `Content-Type: application/json`, antes do roteamento.
- `backend/app/errors.py`: `error_response(status, code, details=..., headers=...)`,
  `error_responses(...)` para o OpenAPI, catálogo `MESSAGES` fixado por igualdade
  exata em `test_errors.py`. Precedente de 422 com `details` próprio: a rota de
  imagem (`[{"loc": ["path", "image_id"], "type": "invalid_image_id"}]`).
- `backend/app/db.py`: `get_session` (Session curta por requisição, sem commit
  automático), `hide_parameters=True`, naming convention de constraints.
- `backend/app/seed.py`: `seed_users(session)` com `INSERT ... ON CONFLICT (id) DO
  NOTHING RETURNING id`, IDs fixos; `main()` faz um commit; `python -m app.seed`
  só precisa de `DATABASE_URL` e não importa `app.main` (teste com `runpy`). O
  leiloeiro semeado é `219e37a5-0def-4b26-87d4-b08668f7c112`.
- `backend/scripts/start.sh`: `alembic upgrade head` → `python -m app.seed` →
  `uvicorn`, com `set -eu`; um teste fixa essa ordem.
- `backend/migrations/versions/`: `0001_baseline`, `0002_users`. Próxima: `0003`.
- Front-end: `CatalogSearch.tsx` (busca + detalhe, vista lista/detalhe abaixo de
  64rem), `ArtworkDetailPanel.tsx` (sem botão de ação, por regra da 2.3),
  `api/catalog.ts` (tipos `ArtworkDetail`), `App.tsx` mostra o catálogo só para
  `AUCTIONEER`. Sem roteador, sem biblioteca de teste de front (Q10 aberta nessa
  parte). Mensagens pelo `code`, nunca pelo `message`.
- Último `verify` registrado (2.3, correções do review): **763 passed**.

## Critérios de aceitação

1. **CA1 — Criação pelo leiloeiro.** Dado estar logado como `AUCTIONEER`, quando
   envio a criação (`POST /api/lots`, P6) com a obra escolhida, lance inicial,
   incremento mínimo, início e fim, então recebo `201` com o lote criado, e o
   lote fica salvo no PostgreSQL com o snapshot da obra (P1, P2), os valores em
   centavos e os horários em UTC. O `auctioneer_id` vem **só** da sessão: o
   cliente não o envia, e um campo `auctioneer_id` (ou qualquer campo desconhecido)
   no corpo é recusado com 422 (P6).
2. **CA2 — Snapshot autoritativo e íntegro.** O snapshot gravado é o que o
   servidor obteve da fonte decidida na P1, nunca título, artista, `image_id`,
   domínio público ou outro metadado vindo do cliente. Campos do AD-23 presentes
   (P2). Nenhum byte de imagem é gravado (AD-22).
3. **CA3 — Domínio público e imagem obrigatórios.** Dado uma obra sem
   `is_public_domain=true`, sem `image_id` válido ou inexistente na AIC, quando
   tento criar o lote, então a criação é recusada com motivo claro (código na P6)
   e nada é gravado.
4. **CA4 — AIC indisponível na criação.** Se a fonte da P1 depender da AIC e ela
   estiver indisponível, lenta, com 403/429/5xx ou resposta incompatível, então
   recebo 503 `catalog_unavailable`, a interface mostra mensagem clara em
   português, permite tentar de novo sem perder o que digitei, e **nenhum lote é
   gravado**.
5. **CA5 — Dinheiro exato.** Lance inicial e incremento mínimo trafegam na API como
   inteiros em centavos, ficam em `BIGINT` com sufixo `_cents` e CHECK no banco
   (P5). Número não inteiro (inclusive `100.0`), string, booleano, zero, negativo
   ou acima do limite → 422 no formato único. Nenhum `float` em regra financeira,
   no back-end nem no front-end (conversão de reais para centavos por texto, P5).
6. **CA6 — Horários coerentes.** Início e fim seguem o formato, o fuso e as regras
   da P4; `ends_at > starts_at` também é CHECK no banco. As regras que comparam com
   "agora" usam um único instante lido do PostgreSQL (`clock_timestamp()`) na
   operação, passado como parâmetro para a regra de domínio (AD-6, AD-26). O
   navegador nunca decide.
7. **CA7 — Política de acesso.** Visitante sem login → 401; `BIDDER` → 403; ambos
   no formato único, **sem chamada à AIC e sem lote gravado** (teste conta linhas
   e requisições do transporte falso). A rota declara `AccessPolicy.AUCTIONEER`
   por `api_route`; o teste de política da 2.2 passa sem mudança no verificador.
   A proteção da 2.1 vale: `Origin` estrangeiro ou ausente → 403 `csrf_*`; sem JSON
   → 415; em nenhum caso o handler roda.
8. **CA8 — Atomicidade.** Uma falha em qualquer ponto da criação (validação,
   AIC, violação de constraint, exceção inesperada) não deixa lote parcial nem
   linha órfã. A chamada externa (se houver, P1) acontece **antes** de abrir a
   transação de escrita; a transação só insere e confirma.
9. **CA9 — Independência da AIC depois de criado.** Dado um lote criado, com a AIC
   indisponível (transporte falso falhando), a leitura dos dados do lote (P9) e o
   seed funcionam; só a imagem pode falhar e cair no placeholder.
10. **CA10 — Meus lotes.** Dado estar logado como `AUCTIONEER`, quando abro "Meus
    lotes" (P9), então vejo os lotes que eu criei, inclusive o recém-criado, e
    nunca os de outro leiloeiro. `BIDDER` → 403; anônimo → 401. Leitura pura (GET,
    AD-19): não altera estado nem chama a AIC.
11. **CA11 — Lote demo semeado.** Dado a aplicação iniciando sem lote demo
    realmente aberto (definição na P8), quando o seed roda, então cria um lote demo
    a partir de uma fixture versionada em `backend/app/`, sem consultar a API
    externa, com horários relativos ao instante do banco, marcado como demo, ligado
    ao leiloeiro semeado e validado pelas mesmas regras de domínio da criação
    manual (dinheiro, horários, snapshot).
12. **CA12 — Idempotência do seed.** Dado já existir um lote demo realmente aberto,
    quando o seed roda de novo, então nenhum lote é criado. O seed **nunca** faz
    `UPDATE` nem `DELETE` em `lots`: lotes demo antigos (encerrados) ficam
    exatamente iguais, byte a byte. Duas execuções simultâneas do seed criam no
    máximo um lote demo (P8). O seed continua sem `APP_ORIGIN`, `JWT_SECRET` e sem
    importar `app.main`.
13. **CA13 — Interface.** Logado como leiloeiro, o fluxo é: buscar obra → abrir
    detalhe → "Criar lote com esta obra" → formulário com a obra (somente leitura),
    início, fim, lance inicial e incremento → revisão → publicar → confirmação
    (P9). Mensagens em português pelo `code`/`details.type`, nunca pelo `message`.
    Nenhum controle sem função; nada da vitrine (2.5), de cancelar (3.6) nem de
    resultado (4.5).
14. **CA14 — Migração.** A tabela `lots` nasce na revisão `0003` com `downgrade`,
    FK para `users`, CHECKs e tipos da seção "Schema provável", aplicada pelos
    testes a partir das migrations. `GET /health` continua 200 sem banco e criar a
    app continua sem banco e sem rede.
15. **CA15 — Verificação e documentação.** `./verify.sh` completo com a saída real
    registrada; README, `docs/uso_de_ia.md`, esta story e `sprint-status.yaml`
    atualizados; a resolução da Q4 (parte desta story) registrada em
    `docs/ARQUITETURA.md` (questões e histórico), sem alterar AD; antes de `done`,
    a conferência de coerência documental (seção "Fechamento"). Paro na 2.4.

## Decisões herdadas (não reabro)

| Fonte | O que já está decidido |
| --- | --- |
| AD-3 | Dinheiro em centavos, `BIGINT`, sufixo `_cents`, CHECK no banco, nenhum `float` em nenhuma camada. |
| AD-5 | Anti-sniping soma 2 min ao `ends_at` atual (3.4). Consequência aqui: `ends_at` será **atualizado** depois, só para frente; a CHECK `ends_at > starts_at` continua válida. |
| AD-6, AD-26 | Hora do PostgreSQL (`clock_timestamp()`), um instante por operação, passado à regra de domínio; o navegador nunca decide. Na criação não há trava de lote (a linha é nova): leio o instante dentro da transação de escrita. |
| AD-8, AD-9 | Lance e fechamento travam a linha do lote (`SELECT ... FOR UPDATE`) e releem `ends_at`. Consequência aqui: `ends_at` é coluna mutável e o lote é uma linha única por lote (sem tabela de versões). |
| AD-11 | `AUCTIONEER` cria e gerencia os próprios lotes e não dá lance; `BIDDER` não cria lote. |
| AD-12 | Snapshot copiado no lote; leitura de lote nunca usa a AIC; seed e testes com fixtures, offline. |
| AD-16 | Fluxo vertical: o lote criado aqui é o ponto de partida da 2.5 em diante. |
| AD-17, AD-27 | Testes críticos em PostgreSQL real (nunca SQLite); `verify` fail-fast. |
| AD-19, AD-29 | GET/HEAD/OPTIONS nunca alteram estado; nenhuma leitura liquida. Escrita só por `POST` JSON com `Origin` validado. |
| AD-22 (revisado) | Não guardar bytes; guardar `image_id`; o navegador usa `GET /api/catalog/images/{image_id}` (pública); falha → placeholder. Sem hotlink direto. |
| AD-23 | `is_public_domain=true` obrigatório; snapshot mínimo: `external_id`, `title`, `artist_display`, `date_display`, `medium_display`, `department_title`, `artwork_type_title`, `image_id`, referência/URL IIIF, crédito/origem, URL da fonte. |
| AD-24 | Seed idempotente na inicialização; lotes demo marcados; novo lote demo só se todos estiverem encerrados; nunca altera nem apaga lote antigo; horários relativos ao momento atual; fixtures versionadas, sem API externa. |
| AD-30 | `lots`, `/api/lots`, colunas e campos em inglês; interface em português. |
| 2.1 | Envelope único de erro; 422 sanitizado (`loc` e `type`); proteção de escrita antes do roteamento. |
| 2.2 | `api_route` como único registro; `require_auctioneer`; 401/403 no formato único; `error_responses()` no OpenAPI; seed por `python -m app.seed` no `start.sh`; IDs fixos dos usuários. |
| 2.3 | `catalog.get_artwork()` e `LookupStatus` como serviço reutilizável; 503 `catalog_unavailable`; proxy de imagem público; mensagens do front pelo `code`; sem roteador e sem ferramenta de teste de front até agora. |

## Política de acesso das rotas novas

| Rota | Método | Política | Sem login | `BIDDER` | `AUCTIONEER` |
| --- | --- | --- | --- | --- | --- |
| `/api/lots` (criar lote) | `POST` | `AUCTIONEER` | 401 | 403 | 201 |
| `/api/lots/mine` (meus lotes, P9) | `GET` | `AUCTIONEER` | 401 | 403 | 200 só com os próprios |

Nenhuma rota existente muda de política. `GET /api/lots` e `GET /api/lots/{lot_id}`
(públicas) são da 2.5 e **não** nascem aqui.

## Questões abertas (decidir no `bmad-spec`, antes do código)

> Registro histórico: o texto das questões é o de antes das decisões. O contrato
> vigente está em "Critérios de aceitação", "Política de acesso das rotas novas",
> "Esquema e contrato finais" e "Decisões fechadas". Onde as duas versões divergem
> (rota `/api/me/lots` → `/api/lots/mine`; limite de 100 itens → todos; teto de R$ 100
> milhões → faixa técnica `1..9007199254740991`; três códigos de obra → um só; fixture
> `demo_lot.json` → `demo_artwork.json`), vale "Decisões fechadas".

Cada questão tem no máximo três opções. As recomendações são propostas; a decisão
é minha. Marco se a decisão é **local** (fica nesta story) ou **afeta stories
futuras** (ainda registrada só aqui, sem virar AD, salvo indicação).

### P1 — Fonte autoritativa do snapshot

**Problema.** No envio do formulário, de onde vêm título, artista, `image_id`,
domínio público e demais metadados gravados no lote? Minha preocupação declarada:
o cliente não pode alterar nenhum deles e criar um snapshot adulterado.

- **(a)** O front-end envia todos os metadados da obra selecionada; o back-end
  valida tipos e formato.
- **(b)** O front-end envia só `external_id` (mais os termos do leilão); o
  back-end chama de novo `catalog.get_artwork(client, external_id)` (o mesmo
  serviço da 2.3), exige `LookupStatus.FOUND` e grava o `ArtworkDetail` que ele
  mesmo obteve.
- **(c)** Híbrido: o front-end envia `external_id` e também o `image_id` (e/ou
  `title`) que o leiloeiro viu; o back-end refaz a consulta como em (b), grava só o
  que obteve e recusa (409) se o `image_id` mudou desde o detalhe exibido.

**Consequências.**
- (a) Não depende da AIC no `POST`, mas qualquer cliente com sessão de leiloeiro
  pode gravar título, artista, `image_id` e "domínio público" arbitrários: o AD-23
  vira promessa da interface, não do servidor. Assinar o payload no detalhe (HMAC)
  resolveria, ao custo de um segredo e um mecanismo novos; não recomendo.
- (b) O servidor é a única fonte; o AD-23 é reconferido no momento da criação
  (uma obra pode ter deixado de ser elegível entre a busca e o envio). Custo: o
  `POST` depende da AIC (CA4: 503 e nada gravado), soma até ~8 s de espera no pior
  caso e gasta uma requisição da cota de 60/min. A chamada externa ocorre **antes**
  da transação de escrita (CA8), com a `Session` sem transação de escrita aberta.
  O que o leiloeiro viu e o que é gravado podem diferir se a AIC mudar a obra entre
  o detalhe e o envio (raro; o resumo da confirmação mostra o que foi gravado).
- (c) Mesmas garantias de (b), mais a garantia "o que você viu é o que foi
  gravado" para a imagem. Custo: mais um campo, mais um código de erro (409) e um
  estado novo na interface, para um caso raro.

**Sub-ponto (título ausente).** A AIC pode devolver `title: null` (a 2.3 mostra
"Sem título"). Proponho manter o contrato da 2.3: aceitar e gravar `null`, exibindo
"Sem título". A alternativa é recusar a criação sem título (mais um motivo de
recusa).

**Recomendação:** (b), com `title` nulo aceito. **Afeta stories futuras:** define
que a criação depende da AIC; 2.5 e seguintes leem só o banco.

### P2 — Campos do snapshot e a "referência/URL IIIF"

**Problema.** O AD-23 lista "referência/URL IIIF" e "URL da fonte, se disponível".
Na 2.3, `image_url` virou a **nossa** rota (`/api/catalog/images/{image_id}`) e a
URL IIIF real é montada só no servidor a partir de uma base fixa.

- **(a)** Gravar todos os campos de `ArtworkDetail`, **exceto** `image_url`:
  `external_id`, `title`, `artist_display`, `date_display`, `medium_display`,
  `dimensions`, `department_title`, `artwork_type_title`, `credit_line`,
  `source_url` e `image_id`. A "referência IIIF" do AD-23 é o próprio `image_id`
  (é o identificador IIIF), com a base fixa no código; `image_url` é derivada na
  leitura.
- **(b)** Como (a), mais uma coluna `iiif_image_url` com a URL IIIF completa do
  momento da criação.
- **(c)** Como (a), mais `image_url` (a rota same-origin) gravada.

**Consequências.** (a) não grava nada derivável, mantém uma única regra de montagem
de URL e não deixa dado morto (o proxy só aceita `image_id` e monta a URL com a
constante); registro na story que a "referência IIIF" do AD-23 é cumprida pelo
`image_id` + base fixa, sem remover campo nem mudar AD. (b) cumpre a letra do AD-23
com uma coluna que nenhum código lê; se a AIC mudar a base, a coluna fica obsoleta
e o proxy continua usando a constante. (c) acopla o banco a uma rota nossa.
`is_public_domain` não é gravado em nenhuma opção: só lotes de obras elegíveis
existem, e a elegibilidade é verificada na criação (P1) e na fixture (P8).
`dimensions` entra porque a 2.3 o consolidou (P11 da 2.3).

**Recomendação:** (a). **Local**, mas a 2.5 depende dos nomes.

### P3 — Estado do lote: persistido ou derivado

**Problema.** A 2.5 separa ao vivo, agendados e encerrados; a 3.6 cancela; a 4.3
liquida; o AD-19 proíbe leitura de alterar estado; o AD-9 relê "`ends_at` e o
estado" sob a trava.

- **(a)** Sem coluna de estado nesta story. Fase temporal sempre derivada de
  `starts_at`/`ends_at` contra a hora do banco (agendado: `now < starts_at`; ao
  vivo: `starts_at <= now < ends_at`; encerrado: `now >= ends_at`). Os marcos que
  não são temporais nascem nas stories que os usam, como colunas aditivas (por
  exemplo, `cancelled_at` na 3.6 e `settled_at`/resultado na 4.3).
- **(b)** Coluna `status` com o ciclo completo (`SCHEDULED`, `LIVE`, `ENDED`,
  ...), atualizada por um processo quando o tempo passa.
- **(c)** Coluna `status` só para o ciclo não temporal, nascendo agora com um único
  valor (`ACTIVE`), ampliada depois (`CANCELLED` na 3.6, `SETTLED` na 4.3); a fase
  temporal continua derivada.

**Consequências.** (a) não cria nada que eu não uso; evita estado que envelhece; as
colunas futuras são `ADD COLUMN` nulas, sem desmontar nada. Ponto de atenção:
"encerrado" sem liquidação vira "Encerrado, apurando resultado" (Q8, 2.5), e a 3.6
e a 4.3 precisam garantir por CHECK que cancelado e liquidado não coexistam. (b)
contraria o AD-19 na prática: entre o fim e a atualização, a leitura mostraria
"ao vivo" para um lote vencido, ou teria de corrigir o estado (proibido); exige
job só para mudar rótulo. (c) antecipa um enum com um único valor e obriga cada
story futura a alterar a CHECK; ganha exclusão mútua "de graça" entre cancelado e
liquidado.

**Recomendação:** (a). **Afeta stories futuras** (2.5, 3.6, 4.3, 4.4); registro
aqui e na 2.5, sem AD nova. Nesta story nenhuma resposta calcula fase (P9), então
a Q8 continua para a 2.5.

### P4 — Horários: formato, fuso e regras

**Problema.** O enunciado diz só "horário de início e fim". O AD-6 dá ao banco a
autoridade da hora. Falta decidir formato, fuso, se o início pode ser "agora" ou
passado e se há limites.

**Fixo em todas as opções (decorre das ADs e do enunciado):** a API recebe ISO
8601 **com fuso obrigatório** (`Z` ou `±hh:mm`); horário sem fuso → 422 (Pydantic
`AwareDatetime`); o back-end converte para UTC e grava `TIMESTAMPTZ`; a resposta
devolve UTC com `Z`; `ends_at > starts_at` (422 e CHECK no banco); `ends_at > now`
do banco (um lote que já nasce encerrado não pode ser "ao vivo" nunca, o que
contraria o propósito da criação); o front-end converte o `datetime-local` do
navegador para ISO UTC e mostra os horários no fuso do navegador, com o fuso
indicado no texto.

- **(a)** `starts_at` obrigatório e livre (passado aceito): se for passado, o lote
  nasce ao vivo. Sem outros limites.
- **(b)** `starts_at` opcional. Ausente = "começar agora", e o servidor grava o
  `now` do banco. Presente = agendado, e precisa ser `> now`. Limites de produto:
  duração mínima de 5 min (`ends_at - starts_at`) e horizonte máximo de 30 dias
  para `ends_at`.
- **(c)** Como (b), sem duração mínima nem horizonte máximo.

**Consequências.** (a) é a mais simples, mas aceita "início em 2020" e deixa o
"agora" ao relógio do navegador (desvio de alguns segundos ou minutos), o que
contraria o espírito do AD-6. (b) e (c) fazem do "agora" sempre a hora do banco e
não aceitam início passado (o seed usa o mesmo caminho: começar agora). A duração
mínima de (b) não vem do enunciado: evita lote de segundos que já nasce dentro da
janela de anti-sniping de 2 min (AD-5); o horizonte de 30 dias evita lote "eterno"
por erro de digitação. Ambos são regra de produto minha, não da arquitetura. (c)
não inventa regra além das ADs, mas aceita lote de 1 s. Erros de horário saem como
422 `validation_error` com `details` próprios (P6), e o front mostra a mensagem do
campo.

**Recomendação:** (b), se eu aceitar as duas regras de produto; senão (c).
**Local** (a 3.4 só depende de `ends_at > starts_at` e de `TIMESTAMPTZ`).

### P5 — Dinheiro: nomes, limites e conversão no front-end

**Problema.** O AD-3 deixou os nomes exatos para a modelagem; falta limite superior
e o modo de digitar reais sem `float`.

**Fixo:** API em inteiros de centavos, `StrictInt` (rejeita `100.0`, `"100"`,
`true`); banco `BIGINT NOT NULL` com CHECK.

- **(a)** Nomes `starting_bid_cents` e `min_increment_cents`; ambos `> 0` (CHECK e
  422); teto de `10_000_000_000` centavos (R$ 100.000.000,00) para cada um, também
  em CHECK. No front, campo de texto em reais (`inputMode="decimal"`), aceitando
  `1234`, `1234,5`, `1234,56` e `1.234,56`; o valor vira centavos por **análise de
  texto** (parte inteira × 100 + centavos, até 2 casas; mais de 2 casas, letras ou
  separador errado → erro no campo), nunca `parseFloat`/`Number("12,34")`; o
  resumo da revisão mostra o valor formatado **a partir dos centavos calculados**,
  para eu conferir antes de publicar.
- **(b)** Como (a), com `<input type="number" step="0.01">` no front.
- **(c)** Como (a), com o campo já em centavos na interface.

**Consequências.** (a) é exata e explicável; o teto fica muito abaixo do inteiro
seguro do JavaScript (2^53) e do `BIGINT`, e protege a interface de valores
absurdos; não é regra do enunciado, é limite técnico meu. (b) faz o navegador
converter para `float` (`valueAsNumber`) e depende da localidade. (c) é ruim de
usar. Sem ferramenta de teste de front (Q10 ainda aberta nessa parte), o conversor
é validado pelo roteiro manual e pelo resumo; a alternativa é introduzir Vitest só
para ele (reabre a decisão de ferramenta da 2.2 P15 e da 2.3 P10).

**Recomendação:** (a), sem ferramenta nova. **Afeta stories futuras:** os nomes
`starting_bid_cents`/`min_increment_cents` serão usados pela 3.2/3.4; o conversor
será reutilizado no depósito (3.1) e no lance (3.5).

### P6 — Contrato da criação: corpo, resposta e erros

**Rota:** `POST /api/lots` (já listada no AD-30). **Corpo proposto** (conforme P1,
P4, P5): `{"external_id", "starts_at" (P4), "ends_at", "starting_bid_cents",
"min_increment_cents"}`, com `extra="forbid"` (campo desconhecido, inclusive
`auctioneer_id`, `title`, `image_id`, `is_demo` → 422). **Resposta:** `201` com o
lote (`id`, snapshot da P2, `image_url` derivada, valores, horários em UTC,
`created_at`), `Cache-Control: no-store`. Sem `Location` (a página do lote é da
2.5).

**Problema.** Como sair cada recusa de obra e de horário, com "motivo claro"
(`epics.md`), sem quebrar o envelope da 2.1.

- **(a)** Códigos novos, um por motivo de obra: 422 `artwork_not_found`, 422
  `artwork_not_public_domain`, 422 `artwork_without_image` (a partir do
  `LookupStatus` que a 2.3 guardou para isto); AIC indisponível → 503
  `catalog_unavailable` (já existe); regras de horário e dinheiro → 422
  `validation_error` com `details` no formato da 2.1 e `type` próprio
  (`ends_at_not_after_starts_at`, `ends_at_not_in_future`, `starts_at_not_in_future`
  e, se P4 (b), `duration_too_short`, `ends_at_too_far`), como o precedente
  `invalid_image_id` da rota de imagem.
- **(b)** Um só código para obra inelegível: 422 `artwork_not_eligible` ("não é de
  domínio público, não tem imagem ou não foi encontrada").
- **(c)** Como (a), mas obra inexistente → 404 `not_found`.

**Consequências.** (a) dá a mensagem exata pedida pelo `epics.md` e reaproveita o
`LookupStatus`; acrescenta 3 entradas no catálogo `MESSAGES` (fixado em
`test_errors.py`, só acréscimo). (b) é menor, mas não diz o motivo. (c) mistura
"recurso da URL não existe" com "referência no corpo inválida". Em todas, a
precedência é: proteção da 2.1 → 401 → 403 → 422 do corpo (Pydantic) → consulta à
AIC (503/422 de obra) → transação (422 de horário com o `now` do banco) → 201. A
validação de horário que não depende de "agora" (`ends_at > starts_at`, fuso,
duração) acontece já no Pydantic, antes da AIC; só as comparações com o `now` do
banco ficam na transação.

**Recomendação:** (a). **Afeta stories futuras:** mensagens do front.

### P7 — Envio duplicado e mesma obra em vários lotes

**Problema.** Um duplo clique ou uma nova tentativa depois de timeout de rede pode
criar dois lotes iguais. Também não está decidido se a mesma obra pode estar em
dois lotes não encerrados.

- **(a)** Sem idempotência no servidor; o front desabilita "Publicar" durante o
  envio e, após sucesso, sai do formulário. A mesma obra pode estar em vários
  lotes.
- **(b)** Cabeçalho `Idempotency-Key` gerado pelo front por formulário, com tabela
  ou coluna `UNIQUE` para a chave.
- **(c)** Recusar (409 `artwork_already_in_auction`) obra que já esteja num lote não
  encerrado do mesmo leiloeiro, checado na transação com trava consultiva por
  `external_id`.

**Consequências.** (a) é a menor e explicável; resta um caso raro (timeout depois do
commit e nova tentativa manual) que eu resolveria cancelando um dos lotes na 3.6.
(b) resolve o caso raro com mais uma estrutura e mais testes. (c) cria regra de
produto não pedida e, com a fase derivada (P3), não pode ser `UNIQUE` parcial no
banco (o predicado dependeria do relógio), então exigiria trava e checagem na
aplicação.

**Recomendação:** (a), registrando a limitação no README. **Local.**

### P8 — Seed do lote demo (inclui Q4)

**Problema.** Definir "lote demo realmente aberto", a ordem na inicialização, a
marcação, a duração, a fixture, os valores e a proteção contra duas inicializações
simultâneas.

**Proposta comum a todas as opções:**

- `python -m app.seed` faz, **numa única transação**: trava consultiva
  `pg_advisory_xact_lock` com uma chave constante do seed (serializa dois seeds
  simultâneos, como num deploy do Render com duas instâncias); `seed_users`; lê
  `now = clock_timestamp()`; se existir lote com `is_demo = true` e
  `ends_at > now`, não faz nada; senão insere um lote demo novo, com o mesmo
  serviço de domínio da criação manual (regras da P4 e da P5, sem a AIC), ligado ao
  leiloeiro semeado (`219e37a5-...`), com `starts_at = now` (ao vivo de imediato:
  o enunciado pede "lote publicado com lances abertos") e `ends_at = now + duração`.
- **"Realmente aberto" (Q4)** = `is_demo AND ends_at > clock_timestamp()`. Hoje não
  há cancelamento nem liquidação; a 3.6 acrescenta "e não cancelado". Um demo
  vencido e ainda não liquidado conta como encerrado (o seed cria outro). Ordem no
  `start.sh`: migrations → seed → servidor (como hoje); o catch-up de fechamento da
  4.4 entra **antes** do seed quando existir. Registro essa resolução parcial da Q4
  em `docs/ARQUITETURA.md`.
- Nunca `UPDATE`/`DELETE` em `lots`; o `id` do lote demo é gerado (não há "ID fixo"
  possível para vários demos ao longo do tempo; IDs fixos continuam valendo para os
  usuários).
- Marcação: coluna `is_demo BOOLEAN NOT NULL DEFAULT false`; o `POST /api/lots`
  nunca a liga (campo recusado pelo `extra="forbid"`).

**Opções para a fixture:**

- **(a)** JSON versionado em `backend/app/seed_data/demo_lot.json`, **no formato do
  nosso snapshot** (os campos da P2, não o JSON da AIC), mais os termos
  (`starting_bid_cents`, `min_increment_cents`, duração); carregado por caminho
  relativo ao módulo e validado pelo mesmo modelo Pydantic do snapshot antes do
  insert. Valores copiados da obra 27992 ("A Sunday on La Grande Jatte — 1884", já
  conferida na AIC real pelo smoke da 2.3).
- **(b)** Constantes Python em `app/seed.py`, com os mesmos dados.
- **(c)** Reaproveitar `tests/fixtures/artic/artwork_27992.json` passando pelo
  adaptador da AIC (`_artwork_from`) e por `catalog._detail`.

**Consequências.** (a) separa dado de código, é "fixture versionada" no sentido do
AD-24, entra na imagem (o `Dockerfile` copia `backend/app`) e não acopla o boot ao
parser da AIC; um teste prova que o arquivo é lido sem rede e sem `app.main`. (b) é
igualmente offline e ainda mais simples, mas mistura dado com código. (c) não
funciona em produção (`backend/tests` está no `.dockerignore`) e faria o boot
depender do parser da integração externa; descarto.

**Parâmetros que eu escolho (proposta):** duração do demo de **72 h**; lance
inicial **R$ 100,00** (`10000`); incremento **R$ 10,00** (`1000`). Sobre a duração:
o seed só roda na inicialização; com o serviço acordado (heartbeat, 4.2) nenhum
demo novo nasce até o próximo boot, então uma duração curta pode deixar o
avaliador sem lote aberto; uma duração longa acumula menos demos encerrados na
vitrine, mas não demonstra o encerramento (o avaliador cria o próprio lote para
isso). Alternativas: 24 h ou 7 dias.

**Recomendação:** fixture (a), com a proposta comum, 72 h, R$ 100,00 e R$ 10,00.
**Afeta stories futuras** (Q4: 3.6 e 4.4).

### P9 — Interface: "Meus lotes", navegação e o que acontece depois de criar

**Problema.** O `epics.md` exige "aparece na lista dos meus lotes no painel"; não
há roteador (2.2 P15 e 2.3 P10 deixaram para a 2.5); a vitrine não existe; o
`EXPERIENCE.md` §5 lista para o leiloeiro "Vitrine, Meus lotes, Criar lote" e o §6
lista as etapas buscar → escolher → conferir → início/fim → lance inicial →
incremento → revisão → publicar.

- **(a)** Sem roteador. Navegação do leiloeiro com dois destinos que funcionam,
  "Criar lote" (a busca da 2.3, que é a etapa 1) e "Meus lotes", como estado em
  `App.tsx`; "Vitrine" só aparece na 2.5. No detalhe da obra, botão "Criar lote com
  esta obra" abre o formulário (obra em leitura, com imagem; início "Agora" ou
  "Agendar"; fim; lance inicial; incremento) com um resumo de revisão visível antes
  de "Publicar lote" (sem modal). Depois do sucesso: confirmação no próprio painel
  com o resumo **do que o servidor gravou** (resposta do `POST`), formulário
  fechado, ações "Ver meus lotes" e "Criar outro lote". "Meus lotes" é uma lista
  densa (`DESIGN.md` §10) por `GET /api/me/lots`, do mais recente para o mais
  antigo, com miniatura, título, artista, início, fim, lance inicial e incremento,
  **sem coluna de estado** (a fase depende da Q8, da 2.5), sem ações e sem paginação
  (limite de 100 itens no servidor).
- **(b)** Como (a), mas "Meus lotes" fica numa seção abaixo da busca, na mesma
  página, sem navegação.
- **(c)** Introduzir React Router agora, com rotas para "Criar lote" e "Meus
  lotes".

**Consequências.** (a) cumpre o `epics.md` e o `EXPERIENCE.md` sem controle morto e
sem antecipar a decisão de rotas; a 2.5 troca o estado por rotas. A lista sem estado
evita decidir a Q8 aqui (leituras de lote vencido e não liquidado precisariam dizer
"Encerrado, apurando resultado"); a 2.5/4.5 acrescentam estado e resultado. (b)
mistura duas tarefas numa página longa, ruim no mobile. (c) antecipa a 2.5. Em
todas: nenhum botão de vitrine, cancelar ou resultado; mensagens pelo `code` e
`details.type`; o resumo e a confirmação mostram reais formatados a partir dos
centavos; o 401 durante o fluxo leva ao login com "Sua sessão expirou", como na
2.3; um 503 no `POST` mantém o formulário preenchido e oferece "Tentar novamente".
Composição visual, estados e responsividade detalhados no `bmad-spec`.

**Recomendação:** (a). **Afeta a 2.5** (navegação vira rotas; lista ganha estado).

### Orientação técnica (não é decisão nova)

- **Módulo.** `app/lots.py` com o modelo `Lot`, os modelos da API, a regra de
  domínio pura (recebe `now`, AD-26) e o serviço `create_lot(session, ...)`, usado
  pela rota e pelo seed; rotas registradas por `register_lot_routes(app)` depois do
  catálogo em `create_app()`. `app/lots.py` não importa `app.main` (o seed o
  importa).
- **Ordem no handler** (P1 b): política → corpo validado → `get_artwork` (fora de
  transação de escrita; a `Session` só fez a leitura da autenticação) → recusas de
  obra → transação: `SELECT clock_timestamp()` → regras com `now` → `INSERT` com
  `created_at = now` (o mesmo instante) → commit → 201. Exceção em qualquer ponto
  → rollback (a `Session` da requisição fecha sem commit).
- **Chamada externa e banco.** Para não manter transação aberta durante a chamada à
  AIC, encerrar (`rollback`) a leitura da autenticação antes de chamar o catálogo;
  a decisão fina fica no plano técnico.
- **Log.** Como na 2.3: categoria da falha da AIC, nunca o corpo, o termo nem o
  usuário. Nenhum dado de lote sensível.
- **OpenAPI.** `responses=error_responses(401, 403, 422, 503)` no `POST` e
  `error_responses(401, 403)` no `GET`; os dois caminhos novos entram na lista
  fixada de `test_openapi.py` (só acréscimo).

## Esquema e contrato finais

**Tabela `lots` (migration `0003`, conferida no PostgreSQL real por `information_schema`).**

| Coluna | Tipo no PostgreSQL | Restrição |
| --- | --- | --- |
| `id` | `uuid` | PK `pk_lots`; sem default (a aplicação gera) |
| `auctioneer_id` | `uuid` | `NOT NULL`, FK `fk_lots_auctioneer_id_users` → `users(id)` `ON DELETE RESTRICT`; índice `ix_lots_auctioneer_id` |
| `external_id` | `integer` | `NOT NULL`, CHECK `> 0` (`ck_lots_external_id_positive`) |
| `title`, `artist_display`, `date_display`, `medium_display`, `dimensions`, `department_title`, `artwork_type_title`, `credit_line` | `text` | nulos |
| `image_id` | `character varying(36)` | `NOT NULL`, CHECK pelo regex do `IMAGE_ID_PATTERN` (`ck_lots_image_id_format`) |
| `source_url` | `text` | `NOT NULL` |
| `starting_bid_cents`, `min_increment_cents` | `bigint` | `NOT NULL`, CHECK `> 0 AND <= 9007199254740991` (`ck_lots_starting_bid_range`, `ck_lots_min_increment_range`) |
| `starts_at`, `ends_at` | `timestamp with time zone` | `NOT NULL`; CHECK `ends_at > starts_at` (`ck_lots_ends_after_starts`) |
| `is_demo` | `boolean` | `NOT NULL`, default `false` |
| `created_at` | `timestamp with time zone` | `NOT NULL`; sem default (é o instante do banco da operação) |

Sem `UNIQUE` em `external_id` (P7) e sem coluna `status` (P3). As colunas futuras
(lance atual, líder, `cancelled_at`, liquidação) nascem aditivas nas stories que as
usam; o lote continua uma linha travável por `SELECT ... FOR UPDATE`.

**`POST /api/lots`** (`AUCTIONEER`). Corpo: `external_id`, `starting_bid_cents`,
`min_increment_cents`, `starts_at` (opcional/`null`), `ends_at`; qualquer outro campo →
422 `extra_forbidden`. `201` devolve o `LotResponse` (`id`, os 11 campos do snapshot,
`image_url` derivada, valores, `starts_at`, `ends_at`, `created_at` em UTC com `Z`;
sem `is_demo` e sem `auctioneer_id`), `Cache-Control: no-store`, sem `Location`.
Erros: 401, 403, 403 `csrf_*`, 415, 422 `validation_error` (`details` com
`ends_at_not_after_start`, `starts_at_not_in_future`, `datetime_format`,
`timezone_aware` e os tipos do Pydantic), 422 `artwork_not_eligible`, 503
`catalog_unavailable`, 500 genérico.

**`GET /api/lots/mine`** (`AUCTIONEER`): `{"items": [LotResponse...]}`, todos os lotes
do dono da sessão, `created_at DESC, id DESC`, sem paginação nem limite, `no-store`.

## Tarefas e subtarefas

- [x] **T1 — Planejar comigo (todas as CAs).** `bmad-spec` (Opus) decide P1 a P9
  comigo e as registra nesta story, em primeira pessoa e com a alternativa
  descartada, antes de qualquer código. Como há front-end, seguir o ciclo da seção
  "Front-end".
- [x] **T2 — Migration e modelo (CA14, P2, P3, P5, P8).** `0003_lots.py` com
  `downgrade`; modelo `Lot`; CHECKs e FK; ajuste de `clean_users` (limpar `lots`
  antes, sempre pela guarda do banco `_test`) e fixture `clean_lots`.
- [x] **T3 — Regra de domínio e serviço (CA5, CA6, CA8, P4, P5).** Validação pura
  de dinheiro e horários recebendo `now`; `create_lot()` transacional com
  `clock_timestamp()`; nenhum `float`.
- [x] **T4 — Rotas (CA1–CA4, CA7, CA10, P1, P6, P9).** `POST /api/lots` e
  `GET /api/me/lots` por `api_route(..., policy=AccessPolicy.AUCTIONEER)`, handlers
  `def`, `extra="forbid"`, reuso de `catalog.get_artwork()`, códigos novos no
  catálogo de erros, `no-store`, OpenAPI.
- [x] **T5 — Seed do lote demo (CA11, CA12, P8).** Fixture versionada em
  `backend/app/`; `seed_demo_lot()` com trava consultiva e `clock_timestamp()`; uma
  só transação com `seed_users`; log `seed: N user(s) inserted, demo lot
  created|kept`.
- [x] **T6 — Testes do back-end (todas as CAs).** Matriz abaixo, em PostgreSQL real
  onde houver banco; transporte falso da AIC; nenhum teste afrouxado.
- [x] **T7 — Interface (CA13, P5, P9).** `api/lots.ts` tipado, conversor de reais
  para centavos por texto, formulário, revisão, confirmação, "Meus lotes",
  navegação do leiloeiro; seguindo `DESIGN.md` e `EXPERIENCE.md`; validação manual
  no navegador (roteiro no build).
- [x] **T8 — Verificar e documentar (CA15).** `./verify.sh` completo com a saída
  real; README; `docs/uso_de_ia.md`; Q4 em `docs/ARQUITETURA.md`; esta story e o
  `sprint-status.yaml`; conferência de coerência documental. Parar na 2.4.

### Review Findings

Code review de 25/10/2026 (`bmad-code-review`, Opus, sessão separada), sobre o estado
atual dos arquivos, sem git. As cinco camadas paralelas falharam por limite da API
(429); a revisão foi feita por um só revisor, com sondas executadas. `./verify.sh` do
review: exit 0, pytest 969 passed e 1 warning, `npm test` 39. Nenhum BLOCKER, HIGH ou
MEDIUM. Nada foi corrigido; status mantido em `review`.

- [x] [Review][Patch] LOW — `ends_at`/`starts_at` muito distante com offset negativo vira 500 em vez de 422: `9999-12-31T23:00:00-05:00` passa no Pydantic e `astimezone(UTC)` em `resolve_schedule` lança `OverflowError` (reproduzido), depois da chamada à AIC; nada é gravado [backend/app/lots.py:222] — **corrigido** (L1, `AfterValidator` em `ApiDatetime`; validado no re-review final)
- [x] [Review][Patch] LOW — `aria-live="polite"` do feedback do dinheiro anuncia a cada tecla ("Valor reconhecido: R$ 1,00", "R$ 12,00"…), ruidoso para leitor de tela; o erro já está ligado por `aria-describedby` [frontend/src/MoneyField.tsx:58] — **corrigido** (L2; validado no re-review final)
- [x] [Review][Patch] LOW — documentação desatualizada sobre `npm test`: o README e a Q10 do `ARQUITETURA.md` dizem que ele testa só o conversor de dinheiro; hoje roda também `lotTime` e `lotDraft` [README.md:61, docs/ARQUITETURA.md:797] — **corrigido** (L3; validado no re-review final)
- [x] [Review][Defer] LOW — `frontend-lot-creation.md` §1 (linha AD-6) ainda diz "nenhuma comparação com o relógio do navegador", contradizendo a revisão do §5 [_bmad-output/specs/spec-story-2-4-criacao-lotes/frontend-lot-creation.md:19] — deferred: correção é na spec; decisão minha. Depois decidi corrigir antes do fechamento: **corrigido** (D1; validado no re-review final).

**Rejeitados:** "Ver meus lotes" depois de falha incerta descarta o rascunho (caminho
definido na spec §2/§7.3, raro); "Tentar novamente" na falha incerta reenvia (P7 e spec
§7.3); 403 de origem tratado como "incerto" (spec §6); JSON malformado sem sessão dar 422
antes do 401 (comportamento real do FastAPI, já fixado e registrado).

## Matriz de testes esperados

| Grupo | Casos |
| --- | --- |
| Migration/schema (PostgreSQL) | `upgrade head` e `downgrade` da `0003`; tipos `BIGINT` em `*_cents`, `TIMESTAMPTZ` em `starts_at`/`ends_at`/`created_at`, `UUID` em `id`/`auctioneer_id`; FK recusa `auctioneer_id` inexistente; `DELETE` de usuário com lote é recusado; CHECKs recusam `*_cents` zero, negativo e acima do teto, `ends_at <= starts_at`, `external_id <= 0`, `image_id` fora do regex; `is_demo` padrão `false`; snapshot completo legível sem a AIC. |
| Regra de domínio (unitário, `now` fixo) | `ends_at > starts_at` (igual recusa); `ends_at > now` no limite exato; início ausente = `now`; início presente `<= now` recusado (limite exato); duração mínima e horizonte no limite exato, se P4 (b); dinheiro `> 0` e teto no limite; nenhum `float` aceito. |
| Criação (PostgreSQL, AIC falsa) | `AUCTIONEER` → 201 com o snapshot da AIC falsa (fixture `artwork_27992.json`), valores e horários em UTC; linha gravada igual à resposta; `auctioneer_id` = usuário da sessão; `auctioneer_id`, `title`, `image_id`, `is_public_domain`, `is_demo` no corpo → 422 e nada gravado; fuso ausente → 422; `100.0`, `"100"`, `true` em `*_cents` → 422; `created_at` e o `now` das regras são o instante do banco (caminho real com margens). |
| Adulteração do snapshot | Com P1 (b): o servidor grava o que a AIC falsa devolveu, mesmo que o cliente tente mandar outros metadados (recusados); a AIC falsa recebe exatamente uma requisição de detalhe com o `external_id` validado. |
| Obra inelegível | `NOT_FOUND`, `NOT_PUBLIC_DOMAIN`, `NO_IMAGE` → códigos da P6, nada gravado. |
| AIC na criação | Timeout, conexão recusada, 403, 429, 5xx, JSON inválido → 503 `catalog_unavailable`, nada gravado, nenhum 500; log só com a categoria. |
| Política (PostgreSQL) | Sem login → 401 e `BIDDER` → 403 no `POST` e no `GET`, sem chamada à AIC e sem linha nova; teste de política lista as duas rotas como `AUCTIONEER`. |
| Proteção 2.1 | `POST /api/lots` com `Origin` estrangeiro, sem `Origin`/`Referer`, sem JSON → 403/415, handler não roda, nada gravado. |
| Transação | Falha forçada depois do `INSERT` e antes do commit (por exemplo, violação de CHECK provocada ou exceção injetada) → nenhuma linha; erro inesperado → 500 genérico sem stack. |
| Meus lotes (PostgreSQL) | Lista só os do leiloeiro da sessão (outro `AUCTIONEER` inserido no teste não vê os meus); ordem; campos; sem limite (101 lotes devolvem 101, A2); funciona com a AIC falsa falhando (CA9); GET não grava (contagem igual); `no-store`. |
| Seed (PostgreSQL) | Banco vazio → 3 usuários e 1 lote demo aberto, ligado ao leiloeiro semeado, `starts_at` = instante do banco (margem), `ends_at` = `starts_at` + duração; segunda execução → nenhum lote novo e nenhuma coluna alterada; demo encerrado inserido no teste (horários no passado) → um demo novo criado e o antigo idêntico byte a byte; demo aberto existente + demos antigos → nada muda; dois seeds simultâneos (threads com conexões próprias) → exatamente um demo novo; lote manual aberto não conta como demo; fixture lida de `backend/app/` com a guarda de rede ativa; subprocesso sem `APP_ORIGIN`/`JWT_SECRET` e sem importar `app.main` continua passando. |
| Fixture | O arquivo existe em `backend/app/`, valida no modelo do snapshot, `image_id` casa o regex, nenhum dado pessoal; o `.dockerignore` não o exclui. |
| OpenAPI e catálogo de erros | Os dois caminhos novos na lista fixada, com `ErrorResponse`; os códigos novos da P6 no teste de igualdade exata. |
| Regressões | Os 763 testes da 2.3 (a contagem nova vem só do `verify`); `/health` sem banco; login, logout, `/api/me`, seed de usuários; catálogo, proxy de imagem, guarda de rede; política e meta-teste sem afrouxar; SPA e fallback; WebSocket técnico; `docker build`. |
| Front | `lint`, `tsc --noEmit`, build no `verify`; roteiro manual: fluxo completo, cada erro de campo, conversão de reais (`1.234,56`, `0,5`, `10`, `1,234`, `abc`), início "Agora" e "Agendar", AIC indisponível no envio (formulário preservado), sessão expirada, duplo clique, confirmação, "Meus lotes", imagem quebrada → placeholder, 320 px, desktop largo, teclado. |

Testes que dependem de constraint, FK, migration, persistência ou idempotência do
seed rodam em PostgreSQL real; nenhum usa SQLite.

## Arquivos criados e alterados

**Criados (back-end):** `backend/app/lots.py`, `backend/app/seed_data/demo_artwork.json`,
`backend/migrations/versions/0003_lots.py`, `backend/tests/lot_support.py`,
`backend/tests/test_lot_rules.py`, `backend/tests/test_seed_fixture.py`,
`backend/tests/integration/test_lots_migration.py`,
`backend/tests/integration/test_lot_creation.py`,
`backend/tests/integration/test_my_lots.py`.

**Alterados (back-end):** `backend/app/main.py` (registra as rotas),
`backend/app/errors.py` (`artwork_not_eligible`), `backend/app/seed.py` (lote demo,
trava, uma transação), `backend/tests/conftest.py` (`clean_users` e `clean_lots`),
`test_openapi.py`, `test_errors.py`, `test_access_policy.py`,
`integration/test_database.py` e `integration/test_seed.py` (só acréscimos e o ajuste de
limpeza).

**Criados (front-end):** `src/money.ts`, `src/money.test.ts`, `src/lotTime.ts`,
`src/lotDraft.ts`, `src/api/lots.ts`, `src/LotArtwork.tsx`, `src/MoneyField.tsx`,
`src/LotForm.tsx`, `src/LotReview.tsx`, `src/LotCreated.tsx`, `src/LotCreation.tsx`,
`src/MyLots.tsx`.

**Alterados (front-end):** `src/App.tsx`, `src/SiteHeader.tsx`, `src/CatalogSearch.tsx`,
`src/ArtworkDetailPanel.tsx`, `src/App.css`, `package.json` (script `test` e
`typecheck` dos dois projetos), `tsconfig.app.json` e `tsconfig.node.json`.

**Outros:** `verify.sh` (etapa "Frontend: test"), `README.md`, `docs/uso_de_ia.md`,
`docs/ARQUITETURA.md` (Q4 e Q10 em parte, histórico; nenhuma AD), `CLAUDE.md` (os dois
resumos de questões), `deferred-work.md`, `sprint-status.yaml` e esta story.

**Intocados:** `Dockerfile`, `.dockerignore`, `compose.yaml`, `scripts/start.sh`,
`app/artic.py`, `app/catalog.py`, `app/access.py`, `app/csrf.py`, `app/auth.py`,
`app/db.py`, `app/users.py`, migrations `0001` e `0002`, `pyproject.toml`, `uv.lock`,
`package-lock.json` (nenhuma dependência nova).

## Persistência, seed e integrações

- **Banco:** uma revisão nova (`0003`), uma tabela (`lots`). `users` intocada.
- **Seed:** passa a garantir o lote demo; continua offline e sem `app.main`.
- **Integração externa:** só o `POST /api/lots` consulta a AIC (P1), antes da transação
  de escrita; leitura de lote e seed nunca a usam; a imagem continua pelo proxy público
  da 2.3.
- **Segredos:** nenhum novo. **Deploy:** nenhuma variável nova; o próximo deploy
  aplica a `0003` e o seed cria o primeiro lote demo na produção.

## Front-end

**Esta story tem front-end: SIM** (formulário de criação, revisão, confirmação,
"Meus lotes", navegação do leiloeiro). Não é a Vitrine; o `VITRINE-BLUEPRINT.md`
não é leitura obrigatória.

A fase seguinte usa obrigatoriamente `@docs/FRONTEND-WORKFLOW.md`,
`@_bmad-output/planning-artifacts/DESIGN.md` e
`@_bmad-output/planning-artifacts/EXPERIENCE.md`. Pontos que o `bmad-spec` precisa
cobrir: formulário como campos e divisores, sem card (`DESIGN.md` §5); obra como
protagonista também no formulário (imagem e ficha antes dos campos); valores muito
legíveis; "Meus lotes" como lista densa que aguenta 30 a 50 registros, títulos
longos e valores grandes; estados nunca só por cor; erros por campo ligados por
`aria-describedby`; foco gerenciado entre detalhe, formulário e confirmação; sem
cara de dashboard SaaS.

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

- Vitrine pública, página pública do lote, `GET /api/lots`, `GET /api/lots/{lot_id}`,
  roteador e estado derivado ao vivo/agendado/encerrado nas leituras (2.5, Q8).
- Lances, carteira, saldo, anti-sniping em ação (3.x); cancelamento (3.6);
  WebSocket (4.1); encerramento, liquidação e catch-up (4.3, 4.4); resultado e
  total recebido no painel (4.5); auditoria e comprovante (5.x).
- Busca e filtro de lotes (OPT1, 6.5); edição de lote; exclusão de lote.
- Cache da AIC, miniatura menor, limite de requisições na rota de imagem
  (`deferred-work.md`, 2.5).
- Ferramenta de teste de front-end (salvo decisão diferente na P5).
- Não crio a Story 2.5, não altero stories concluídas e não uso git.

## Fechamento (regra de toda story a partir desta)

Antes de `done`, confiro a coerência entre os documentos afetados: `ARQUITETURA.md`
(Q4), spec/decisions da 2.4, esta story, `docs/uso_de_ia.md`, `CLAUDE.md` (só se
um resumo ficar desatualizado), `epics.md` (só se um critério precisar de nota),
`README.md` e `deferred-work.md`. Preservo a sequência: decisão → motivo →
alternativa descartada → evidência/mudança de plano → decisão revisada →
limitação/adiamento. Não altero AD para registrar detalhe local.

## Decisões fechadas (P1 a P9, D1 a D14, Q1 e A2 a A4)

Decidi tudo antes do código, com a spec em `_bmad-output/specs/spec-story-2-4-criacao-lotes/`
(`decisions.md`). Registro a decisão e a alternativa que descartei. A implementação
seguiu todas, sem reabrir.

| Questão | Decidi | Descartei |
| --- | --- | --- |
| P1 snapshot | o front envia só `external_id` e os termos; o servidor reconsulta a AIC e grava o que ele mesmo obteve; título `null` aceito | o front enviar os metadados (o AD-23 viraria promessa da interface); híbrido com 409 se o `image_id` mudou |
| P2 campos | os 11 campos do `ArtworkDetail`, sem `image_url`; `image_id` é a referência IIIF | coluna `iiif_image_url` (dado morto); gravar `image_url` (acopla o banco a uma rota nossa) |
| P3 estado | sem coluna `status`; a fase é derivada do tempo | `status` com o ciclo completo; `status` de um valor só |
| P4 horários | `starts_at` opcional (`null` = hora do banco), futuro se vier; `ends_at` obrigatório e posterior; fuso obrigatório; sem duração mínima nem horizonte | `starts_at` obrigatório e livre; duração mínima de 5 min e horizonte de 30 dias |
| P5 dinheiro | centavos `BIGINT`, `> 0`, `StrictInt`; reais por texto no front; faixa técnica única `1..9007199254740991` (A4: também no banco) | teto comercial de R$ 100 milhões; `<input type="number">`; campo em centavos |
| P6 obra inelegível | um código, 422 `artwork_not_eligible`; AIC fora → 503 `catalog_unavailable` | três códigos por motivo; 404 para obra inexistente |
| P7 duplo envio | sem `Idempotency-Key`; o front bloqueia o segundo envio; a mesma obra pode virar vários lotes | chave de idempotência; 409 para obra já em lote aberto |
| P8 seed | fixture JSON em `backend/app/seed_data/`, obra 27992, 72 h, R$ 100,00 e R$ 10,00; demo aberto = `is_demo` e `ends_at > agora`; trava consultiva | constantes em Python; reaproveitar a fixture de teste pelo parser da AIC |
| P9 Meus lotes | `GET /api/lots/mine`, todos os lotes do dono, sem estado; sem React Router (A2: sem limite) | `/api/me/lots`; limite de 100; seção na mesma página; React Router |
| D1 | `user.id` guardado e `session.rollback()` antes da AIC; a transação de escrita só abre depois | chamar a AIC com a leitura da autenticação aberta |
| D2 | horário como string ISO com estrutura verificada por regex antes do `AwareDatetime` | `AwareDatetime` puro (aceitaria número como timestamp Unix) |
| D3, D7 | faixa do dinheiro `1..2^53-1`; CHECKs de dinheiro, tempo, `external_id` e `image_id` | teto comercial; só validar na API |
| D5 | a pré-checagem `ends_at <= starts_at` roda antes da AIC; o resto, com a hora do banco, depois | validar `starts_at` no passado antes da AIC (um segundo instante) |
| D8 | uma transação: trava → usuários → hora do banco → demo aberto? → `create_lot`; `READ COMMITTED` | `pg_try_advisory_lock`; trava de sessão; `FOR UPDATE` |
| D11 | `clean_users` faz `TRUNCATE lots, users` (sem `CASCADE`) | `TRUNCATE users CASCADE` |
| D12 | navegação "Criar lote"/"Meus lotes" no header; a busca fica montada e oculta; revisão como etapa, sem modal | desmontar a busca; revisão como resumo vivo |
| D13 | reais → centavos por regex e concatenação de texto; `formatCents` textual | `parseFloat`, `Number("12,34")`, `Intl` para parsear |
| D14 / A3 | `resolve_artwork_for_lot` (AIC, só o POST) separado de `create_lot` (sem rede, compartilhado com o seed) | um `create_lot` que recebe `external_id` e chama a AIC |
| Q1 | `money.test.ts` com `node:test`, `npm test` no `verify` | só roteiro manual; Vitest com Testing Library |

## Registro de implementação (24/10/2026)

Implementei a partir da spec aprovada, sem git, sem deploy e sem ler `.env*`.

**Back-end.** `app/lots.py` reúne o modelo `Lot`, `LotTerms`/`CreateLotRequest`,
`ArtworkSnapshot`, a regra pura (`resolve_schedule`, `ends_not_after_scheduled_start`), o
nível externo (`resolve_artwork_for_lot`), o de persistência (`database_now`,
`create_lot`) e as duas rotas. O handler do `POST` segue a ordem da D1: política →
`user.id` → `rollback()` → pré-checagem sem `now` → AIC → hora do banco → `create_lot` →
commit → 201. A migration `0003` tem `downgrade`. O seed ganhou `acquire_seed_lock`,
`seed_demo_lot` e `run_seed` (uma transação) e continua sem `app.main`, sem rede e sem
`APP_ORIGIN`/`JWT_SECRET`.

**Front-end.** Navegação do leiloeiro no `SiteHeader`; `LotCreation` com as etapas
`catalog → form → review → created`; `LotForm`, `LotReview`, `LotCreated`, `MyLots`;
`money.ts` com teste de `node --test`; sem dependência nova e sem React Router.

### Desvios e detalhes em relação à spec

- **Regex do horário.** O `backend-contract.md` mostrava o offset como obrigatório no
  padrão `API_DATETIME_PATTERN`, mas o `test-plan.md` e a D2 pedem `timezone_aware` para
  horário sem offset. Tornei o offset opcional no regex (só a estrutura), de modo que
  "sem offset" chega ao `AwareDatetime` e sai como `timezone_aware`, e número, data sem
  hora e espaço no lugar do `T` saem como `datetime_format`. O comportamento é o do
  `test-plan.md`; só o padrão do contrato foi ajustado.
- **Tipo do erro de data impossível (R10).** `2030-02-30T10:00:00Z` sai como
  `datetime_from_date_parsing`; fixei esse tipo real no teste.
- **JSON malformado sem sessão.** O FastAPI decodifica o JSON antes de resolver as
  dependências: o corpo ilegível vence o 401 e dá 422 `json_invalid`. Fixei esse
  comportamento real em teste. Com campos inválidos mas JSON legível, o 401 vence.
- **Limites do "demo aberto" no teste.** Usei ±5 s em torno do relógio do banco (a spec
  diz ±1 s) para o teste não depender de milissegundos; a regra testada é a mesma.
- **Testes de concorrência livre.** Os dois seeds em corrida (5 repetições) passam, mas
  passam também sem a trava: a corrida real quase nunca ocorre. A prova de que a trava
  funciona são os dois testes determinísticos (uma conexão segura a trava, o seed espera
  em `pg_locks` e depois cria ou não). Conferi com uma mutação temporária, que removi:
  sem `acquire_seed_lock`, os dois determinísticos falham.
- **Fronteira da transação.** Conferi com outra mutação temporária, removida: sem o
  `session.rollback()` antes da AIC, o teste de `pg_stat_activity` vê 1 conexão `idle in
  transaction` e falha.
- **Fora da lista prevista.** Nenhum arquivo fora do mapa de implementação foi alterado.

### Evidências (comandos executados em 24/10/2026)

- Direcionados: `test_lots_migration.py` 21 passed; `test_lot_rules.py` 57 passed;
  `test_lot_creation.py` 86 passed; `test_my_lots.py` 11 passed; `test_seed.py` 28 passed
  (7 da 2.2 e 21 novos); `test_seed_fixture.py` 6 passed.
- `cd frontend && npm test`: 14 testes, 14 passaram, 0 falharam.
- `./verify.sh` completo, exit 0: `ruff check` "All checks passed!"; `ruff format
  --check` "55 files already formatted"; **pytest: 969 passed, 1 warning** (a 2.3 registrou
  763; os 206 a mais são testes novos, sem asserção existente afrouxada); ESLint, `tsc
  --noEmit` dos dois projetos, `npm test` (14) e o build do Vite (36 módulos) sem erro;
  `docker build` concluído; "verify.sh: todas as etapas passaram."
- Imagem de produção: `docker run --entrypoint ls` mostra `app/seed_data/demo_artwork.json`
  dentro da imagem; rodando `alembic upgrade head` e `python -m app.seed` na imagem
  contra o banco `_test`, o log diz "seed: 3 user(s) inserted; demo lot created", sem
  `APP_ORIGIN`, sem `JWT_SECRET` e sem rede.
- Pilha real (uvicorn, banco `_test`, login de verdade): `GET /api/lots/mine` do
  leiloeiro devolveu o demo (R$ 100,00 e R$ 10,00, término 72 h depois do início); o
  licitante recebeu 403 e o anônimo 401. Fiz **uma** chamada real `POST /api/lots` com a
  obra 27992 contra a AIC de verdade (fora do `pytest`) e recebi 201 com o snapshot. Não
  rodei o smoke completo da 2.3: nenhum código da integração externa mudou.

### Riscos e limitações restantes

- Não testei nada no navegador (não há navegador nesta sessão): o formulário, a revisão,
  a confirmação, "Meus lotes", o foco entre etapas, 320 px e o teclado dependem do meu
  roteiro manual (`test-plan.md` §9) e do code review. Os componentes não têm teste
  automatizado (Q10, em parte); só `money.ts` tem.
- Sem idempotência no servidor (P7): timeout depois do commit e nova tentativa manual
  pode criar dois lotes; a tela manda conferir "Meus lotes" antes.
- "Meus lotes" sem paginação (A2): com muitos lotes, a resposta cresce e cada miniatura
  é uma chamada à AIC sem cache (D1 da 2.3).
- O demo vencido só é substituído no próximo boot (P8).
- `loc` do 422 de campo extra contém o nome da chave enviada (item já deferido na 2.1).
- Não fiz deploy: o próximo deploy aplica a `0003` e o seed cria o primeiro demo na
  produção. Nenhuma variável nova.

## Bug de runtime no primeiro teste manual (25/10/2026)

**O que o teste manual mostrou.** Meu primeiro teste manual abriu `http://localhost:5173`
e a aplicação ficou **completamente branca**, antes de qualquer tela. O console apontou
`lotTime.ts:21` com `Uncaught TypeError: Invalid option : option` em
`new DateTimeFormat`. Lint, `tsc --noEmit`, o build do Vite e o `verify` inteiro tinham
passado: nada disso executa o módulo.

**Causa exata.** Em `frontend/src/lotTime.ts` (linhas 21 a 25 antes da correção),
`new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short',
timeZoneName: 'short' })` combinava `dateStyle`/`timeStyle` com `timeZoneName`, o que o
`Intl` recusa. Como a construção estava no nível do módulo, o erro acontecia na
importação, antes de o React renderizar, e derrubava a tela inteira. Reproduzi o erro
idêntico no Node. Erro meu: escrevi a combinação da spec sem executá-la.

**Correção (só formatação da interface).** Troquei as opções por campos explícitos,
`day: 'numeric'`, `month: 'short'`, `year: 'numeric'`, `hour: '2-digit'`,
`minute: '2-digit'` e `timeZoneName: 'short'`. Mantive o fuso (a spec pede o fuso
indicado) e o visual: no Node, `2026-10-25T16:00:00Z` em `America/Sao_Paulo` sai
"25 de out. de 2026, 13:00 BRT", o mesmo texto de `medium`/`short` mais o fuso. Não mudei
`localInputToIso`, nem a regra de horário do back-end (P4), nem o fuso de persistência.
Descartei remover `timeZoneName` (a spec e o README dizem que os horários aparecem no
fuso do navegador) e descartei construir o formatador de forma preguiçosa só para
esconder o erro.

**Teste de regressão.** `frontend/src/lotTime.test.ts` (`node:test`, sem dependência
nova) importa e executa o módulo de verdade: o formatador não lança, uma data UTC vira
texto não vazio com o ano e a hora, o nome do fuso aparece depois da hora (sem comparar o
texto exato, que varia por ICU), texto ilegível volta como veio, e `localInputToIso`
aceita e recusa as entradas certas e traduz o horário de parede conforme o `TZ` da
máquina (`UTC`, `America/Sao_Paulo`, `Asia/Tokyo`), sem regra própria. Conferi por
mutação temporária que ele pega o bug: com o código antigo, a execução falha com
`TypeError: Invalid option : option` e `pass 0`; com a correção, passa. Restaurei a
correção depois.

**Observação.** Ao escrever o teste, vi que o `Date` do V8 faz rollover de
`2026-02-30T10:00` para 2 de março em vez de recusar. O `<input type="datetime-local">`
não emite uma data assim, então não é alcançável pela interface; não alterei a função e
deixei a observação num comentário do teste.

**Evidências (comandos executados em 25/10/2026).** `npm test`: 22 testes (14 do
`money` e 8 do `lotTime`), 22 passaram, 0 falharam; `npm run lint`, `npm run typecheck`
e `npm run build` sem erro; `./verify.sh` completo registrado abaixo. O roteiro manual
(`test-plan.md` §9) continua meu e recomeça do passo 1, agora que a tela abre.

**Lição.** Lint, tipos e build não detectam erro de execução em código de módulo. Daqui
em diante, módulo de front-end com lógica pura ou construção no nível do módulo ganha um
teste que o execute.

## Ajustes do teste manual (25/10/2026)

**O que observei no navegador.** Registro só o que vi. Primeiro, a aplicação local
respondia 500 ao criar lote porque o banco de desenvolvimento estava na revisão `0002`
enquanto o `head` era `0003`. Era o **ambiente local desatualizado**, não uma falha da
migration: depois de aplicar o schema local, o fluxo passou a funcionar. Observei: as
validações de dinheiro; a validação de início agendado no passado; a validação de
término no passado; a revisão; a criação real, que chegou à tela "Lote criado"; o
celular a 375 px; o `BIDDER` sem nenhum controle do leiloeiro; e o anônimo chegando ao
login.

**Ainda não observado, e por isso não registrado como feito:** o HTTP 201 na aba Rede,
o payload exato do POST, 320 px, a navegação por teclado e o refresh de "Meus lotes".

**Investigação: uma data passada chegava à revisão?** Sim. A captura mostrava "Revise o
lote" com término em 23/10/2026 (teste feito em 25/10) e "Publicar lote" ativo, depois de
a tela ter exibido "O término precisa ser depois do momento da publicação.". Li
`LotForm`, `LotDraft`, `LotReview` e `LotCreation`: o "Revisar lote" já reexecutava
`checkDraft` com o valor ATUAL do rascunho, e `LotCreation` só entra na revisão com o
`request` que esse `checkDraft` devolve; não havia valor velho sendo reaproveitado. A
causa era outra: `checkDraft` **nunca comparava com "agora"**. Eu o desenhei assim porque
a spec (`frontend-lot-creation.md` §5) dizia "nenhum `min` com o relógio do navegador" e
"nada aqui compara com agora". Provei com uma sonda antes de corrigir: término
`2026-10-23T17:18` com "Assim que eu publicar" devolvia `ok: true` e um request com
`ends_at` no passado. A mensagem que apareceu no formulário veio do **servidor**, ao
clicar em "Publicar", depois de passar pela revisão; a revisão que vi era a etapa
intermediária legítima do fluxo, não um segundo cálculo. Não era defeito do servidor
(que recusou corretamente), e sim a falta de validação preventiva no front.

**Decisão (minha, 25/10/2026).** Passo a validar de forma **preventiva** no front com o
relógio do navegador: "assim que eu publicar" exige `término > agora`; agendado exige
`início > agora` e `término > início`. Isto revisa a frase da spec §5; o servidor, com a
hora do PostgreSQL, continua sendo a autoridade final e repete as regras (AD-6, P4
inalterados, nenhuma mudança no back-end). Descartei manter só a validação do servidor
(a pessoa só descobria o erro ao publicar) e descartei o atributo `min` do input (o
navegador não explica o motivo).

**Correção.** `checkDraft(externalId, draft, now)` recebe `now` por parâmetro (nunca lê o
relógio sozinho; o formulário passa `new Date()`), e um novo `momentError` valida cada
horário. Um rascunho inválido nunca gera `request`, então não chega à revisão. Para o
teste rodar no Node, os imports de `lotDraft.ts` ganharam a extensão `.ts` (o `tsconfig`
já permite).

**Regressão.** `frontend/src/lotDraft.test.ts` (`node:test`, `now` fixo, sem dependência
nova): término passado com "assim que eu publicar" → inválido; término igual a agora →
inválido e um minuto depois → válido; início agendado passado ou igual a agora →
inválido; término menor ou igual ao início → inválido; início futuro com término posterior
→ válido, com os ISO em UTC; mesma regra em `UTC`, `America/Sao_Paulo` e `Asia/Tokyo`;
o mesmo rascunho que valia deixa de valer quando o relógio avança; erros de dinheiro
preservados. (Nesta rodada a suíte também tinha dois casos do estado "confirmado", removidos
no último ajuste, abaixo.) Conferi por mutação temporária (neutralizei a comparação com
`now`): 8 testes falharam; restaurei e os 14 passaram.

**Data e hora (UX).** Mantive `<input type="datetime-local">`, sem biblioteca, e melhorei o
que está ao redor: o campo ficou mais alto (`min-height: 3rem`, mais padding) e ganhou um
resumo discreto do horário escolhido com o fuso (`DateTimeField`). Nesta rodada eu tinha
acrescentado um botão "Confirmar data e hora" com estado de "confirmado"; **removi tudo isso
depois do reteste** (veja "Último ajuste de UX" abaixo).

**Dinheiro (UX).** A lógica não mudou. O `MoneyField` ganhou uma ajuda (simplificada no
último ajuste, abaixo) e, quando o valor é válido, "✓ Valor reconhecido: R$ 1.250,00" (o `formatCents` dos centavos calculados; os
centavos internos nunca aparecem). Os erros de zero, negativo, formato, mais de duas casas
e overflow foram preservados. `MAX_CENTS` e a API não mudaram. O teste do `money` ganhou os
três exemplos (5 → 500, 5,50 → 550, 1.250,00 → 125000).

**Layout.** Não redesenhei nada: a assimetria do catálogo vazio em desktop vem do layout
lista/detalhe da 2.3 e não é defeito bloqueante da 2.4. Só mexi no CSS dos campos de
data/hora e do feedback monetário.

**Evidências (comandos executados em 25/10/2026).** `npm test`: 37 testes (14 do
`money`, que ganhou 1 caso de exemplos monetários, 8 do `lotTime` e 14 do `lotDraft`), 37
passaram, 0 falharam. `npm run lint`, `npm run typecheck` e `npm run build` sem erro; o
typecheck do projeto Node passou a alcançar `lotDraft.ts` e `api/lots.ts` pelo teste e
exigiu a extensão `.ts` nos imports de `lotDraft.ts`. `./verify.sh` completo, exit 0: Ruff
limpo (55 arquivos formatados), **pytest 969 passed, 1 warning**, ESLint, `tsc` dos dois
projetos, `npm test` (37), build do Vite (37 módulos) e `docker build`; "verify.sh: todas
as etapas passaram." Não rodei o smoke da AIC e não vi as telas no navegador depois destes
ajustes: o reteste do formulário (confirmação de data e hora, dinheiro, foco, 375 px) é
meu. A story e o `sprint-status.yaml` continuam em `review`.

## Último ajuste de UX (25/10/2026)

**Observado no reteste manual** (só o que vi): o `POST /api/lots` retornou HTTP 201 na aba
Rede; a resposta mostrou valores em centavos coerentes com a interface; a validação
preventiva passou a impedir que uma data passada chegue à revisão; o "Valor reconhecido"
funcionou; a criação real continuou funcionando depois dos ajustes; e o celular a
aproximadamente 375 px continuou utilizável. **Não conferi** o payload exato na aba
Payload, nem 320 px, nem o teclado, e por isso não os registro como validados.

**Botão "Confirmar data e hora" removido.** Eu o tinha pedido porque o seletor nativo do
Edge às vezes era desconfortável para sair depois de escolher a data. Como não dá para pôr
um botão dentro do seletor nativo sem substituir o componente inteiro, decidi **não manter
uma etapa artificial**. Removi o botão, o estado separado de horário confirmado
(`startsAtConfirmed` e `endsAtConfirmed`) e a regra que exigia confirmação antes de
avançar. Descartei trocar o seletor por um calendário próprio ou por biblioteca. "Revisar
lote" é a confirmação natural do formulário: reexecuta `checkDraft` com o valor ATUAL e o
`now` do clique, então término passado com "assim que eu publicar", início agendado
passado e término menor ou igual ao início continuam sem avançar; só valores válidos
avançam. O `DateTimeField` ficou um `datetime-local` mais alto com um resumo discreto do
horário escolhido e o fuso. O servidor segue como autoridade final; nada mudou no
back-end.

**Dinheiro: ponto no lugar da vírgula.** O teste manual mostrou que `655.3` não era
reconhecido sem explicar como corrigir. Isso é correto no formato pt-BR (a vírgula separa
os centavos; o ponto só vale como milhar de três dígitos), mas a mensagem era genérica.
Agora uma entrada como `655.3`, `12.5` ou `12.50` (ponto seguido de um ou dois dígitos) dá
o erro próprio `dot_decimal`: "Use vírgula para os centavos. Ex.: 655,30.". Nunca é
reinterpretada em silêncio. Seguem aceitos `5`, `5,50`, `1.250,00` e `1.234` (milhar), e
seguem recusados, com a mensagem genérica de formato, `1.5.3`, `1.2345`, `1.23,45` e
`655.`. Sem `float` e sem mudar a API nem o `MAX_CENTS`. Observação: `655.300` continua
sendo lido como R$ 655.300,00 (milhar válido), porque o formato pt-BR é inerentemente assim;
o "Valor reconhecido" mostra o que foi entendido antes de avançar.

**Ajuda dos campos de dinheiro simplificada.** A linha com três equivalências ficou pesada;
agora é "Digite o valor em reais. Use vírgula para centavos. Ex.: 5,50 ou 1.250,00.", e o
"✓ Valor reconhecido: R$ X" confirma a interpretação.

**Testes.** `lotDraft.test.ts`: removi só os dois casos do estado "confirmado" e adaptei o
auxiliar; mantive todos os que provaram o bug da data passada e acrescentei um que revalida
o valor atual (válido que vira inválido ao editar, e a troca de modo). Refiz a mutação
(neutralizar a comparação com `now`): 9 testes falharam; restaurado, os 13 passaram.
`money.test.ts`: o caso `10.5` saiu de "formato" e passou a "ponto decimal", e há um teste
novo para `655.3`, `12.5`, `12.50`, `0.5`, `1.23`, a mensagem, o que continua aceito e os
formatos que continuam recusados.

**Evidências (comandos executados em 25/10/2026).** `npm test`: 37 testes (16 do `money`, 8 do
`lotTime` e 13 do `lotDraft`), 37 passaram, 0 falharam; `npm run lint`, `npm run typecheck`
e `npm run build` sem erro. `./verify.sh` completo, exit 0: Ruff limpo (55 arquivos
formatados), **pytest 969 passed, 1 warning**, ESLint, `tsc` dos dois projetos, `npm test`
(37), build do Vite (37 módulos) e `docker build`; "verify.sh: todas as etapas passaram."
Não alterei o back-end nesta rodada, não rodei o smoke da AIC e não vi as telas depois do
ajuste: o último reteste é meu. A story e o `sprint-status.yaml` continuam em `review`.

## Feedback monetário inválido (25/10/2026)

O reteste manual identificou que, ao digitar `333.55`, o campo deixava de mostrar o
"Valor reconhecido", mas não mostrava um erro específico: para quem digita, parecia só
"sem reconhecimento". A causa estava no `MoneyField`: o erro do ponto decimal (`dot_decimal`)
só aparecia depois de "Revisar lote". Ajustei o UX, sem mudar a lógica financeira, a API
nem o `MAX_CENTS`.

O campo agora tem um único espaço de feedback, simétrico: valor válido → "✓ Valor
reconhecido: R$ X" (verde); valor inválido → "✕" e a mensagem, em vermelho (`aria-invalid` e
`aria-describedby`; o `aria-live` foi removido no code review, L2). O símbolo e o texto garantem que o estado
não dependa só da cor. Campo vazio não mostra nada até o envio. Para ponto usado como
decimal, a mensagem usa o que foi digitado: `333.55` → "Use vírgula para os centavos. Ex.:
333,55."; `12.5` → "Ex.: 12,50.". Os demais formatos inválidos mostram a mensagem que já
existia (formato, mais de duas casas, zero, valor alto demais). O erro do "Revisar lote"
ocupa o mesmo lugar, sem duplicar.

Como o feedback é vivo, um valor parcial enquanto se digita (por exemplo `5,` ou `0` antes de
`0,50`) mostra o erro por um instante; aceitei isso para manter o comportamento uniforme e
previsível. O ponto como milhar válido continua aceito (`1.250,00`, `1.250`). A lista de
valores a recusar pedida incluía `10.999`; mantive `10.999` aceito, porque no formato pt-BR
é milhar válido (R$ 10.999,00), igual a `1.250`; o que se recusa é `10,999` (mais de duas
casas). Isso fica registrado para você confirmar.

`money.test.ts` ganhou: `333.55` e `12.5` são `dot_decimal` com a mensagem sugerindo
`333,55` e `12,50`; `abc`, `1,2,3`, `10,999`, `1.5.3` e `-5` não recebem a dica da vírgula;
`1.250,00`, `1.250`, `5` e `5,50` continuam válidos; e os motivos de formato, zero, casas e
overflow seguem corretos. Esta rodada não tem evidência manual nova: o reteste final é meu.

**Evidências (comandos executados em 25/10/2026).** `npm test`: 39 testes (18 do `money`, 8 do
`lotTime` e 13 do `lotDraft`), 39 passaram; lint, typecheck e build sem erro. `./verify.sh`
completo, exit 0: Ruff limpo (55 arquivos), **pytest 969 passed, 1 warning**, `npm test` (39),
build do Vite (37 módulos) e `docker build`; "verify.sh: todas as etapas passaram." Sem
back-end, sem smoke e sem tela vista por mim: o reteste final é meu. A story e o
`sprint-status.yaml` continuam em `review`.

## Primeiro code review (25/10/2026)

**Resultado.** O primeiro `bmad-code-review` (Opus) encontrou **0 BLOCKER, 0 HIGH e 0
MEDIUM**, mais L1 (LOW, bug), L2 (LOW, acessibilidade), L3 (LOW, documentação) e D1
(contradição documental). O reviewer rodou o `./verify.sh` por conta própria, exit 0
(pytest 969 passed, `npm test` 39 passed, ESLint, `tsc`, build e `docker build`). Os
subagentes do review **não rodaram por limite 429**; o Opus principal fez o review
completo e executou o `verify`. Não houve review multiagente, e não o registro como se
tivesse havido. Aprovei corrigir L1, L2, L3 e D1 antes do fechamento.

**L1 (bug): datetime que não cabe em UTC virava 500.** `9999-12-31T23:00:00-05:00` passava
pela validação estrutural, mas `astimezone(UTC)` lançava `OverflowError: date value out of
range`, o que, na criação, acontecia depois da chamada à AIC e terminava em 500. Reproduzi
nos dois extremos (o máximo com offset negativo e `0001-01-01T00:00:00+05:00`). Corrigi no
tipo `ApiDatetime` (`app/lots.py`), com um `AfterValidator` que tenta normalizar para UTC e,
se estourar, recusa com `datetime_format`: a invariante é garantida na entrada, sem
`try/except` espalhado pelo handler. Resultado: 422 `validation_error` com `loc
["body", "<campo>"]` e `type: "datetime_format"`, **sem chamar a AIC** e sem linha gravada.
Descartei tratar o `OverflowError` no handler (duplicaria a regra e chamaria a AIC antes).
P4, a hora do PostgreSQL, a comparação de futuro, `starts_at=null` e `ends_at > início`
não mudaram. Testes: unitário do validador (estouram `9999-12-31T23:00:00-05:00`, o limite
exato `9999-12-31T19:00:00-05:00` e `0001-01-01T00:00:00+05:00` e `+00:01`, em `starts_at`
e `ends_at`) e de rota (422, `fake.requests == []`, zero linhas). Casos extremos que
cabem seguem válidos: `9999-12-31T23:59:59.999999Z`, `9999-12-31T18:59:59-05:00`,
`0001-01-01T05:00:00+05:00`; a rota ainda cria um lote com esse término máximo. Mutação
temporária (removi o validador): os 8 casos de rejeição falharam com o `OverflowError`
real; restaurado, passam. Num dos meus casos, a conta estava errada
(`19:00:01-04:59` cabe em UTC); corrigi a entrada do teste, não o comportamento.

**L2 (acessibilidade): `aria-live` do feedback monetário removido.** O valor reconhecido
muda a cada tecla e o leitor de tela reanunciaria "R$ 1,00", "R$ 12,00"... durante a
digitação. Removi o `aria-live` de `MoneyField`; mantive o feedback visual verde e
vermelho, o texto (não só a cor), o `aria-describedby` e o `aria-invalid`.
**Conferência do `dot_decimal`:** renderizei o `MoneyField` de verdade (SSR em memória,
com um arquivo temporário fora do repositório, removido depois). Para `333.33`: `aria-invalid
="true"`, `aria-describedby="…-hint …-feedback"` e o parágrafo
`money-feedback money-invalid` com "✕ Use vírgula para os centavos. Ex.: 333,33.". Para `5`,
`5,50` e `1.250,00`: `aria-invalid="false"` e "✓ Valor reconhecido" verde; para `abc`, a
mensagem de formato. Não precisei mudar o parser.

**L3 (documentação): `npm test`.** README e `docs/ARQUITETURA.md` diziam que `npm test` só
testa o conversor de dinheiro. Atualizei só essas frases: hoje cobre a lógica pura de
`money`, `lotTime` e `lotDraft`.

**D1 (contradição da spec): corrigida agora.** `frontend-lot-creation.md` ainda resumia o
AD-6 como "nenhuma comparação com o relógio do navegador". A decisão final: o front pode
comparar com `new Date()` (injetado como `now`) só para validação **preventiva** de UX; o
backend, com `clock_timestamp()`, é a autoridade final e revalida tudo. Reescrevi o texto
vigente e mantive um "Histórico" da mudança. Ao relê-la, achei no mesmo arquivo e em
`test-plan.md` três trechos que meus ajustes anteriores tinham deixado desatualizados e
corrigi junto: o `Intl.DateTimeFormat` com `dateStyle`/`timeStyle` (o que causou a tela
branca), `10.5` listado como `format` (agora `dot_decimal`) e a ajuda do dinheiro. Também
ajustei `SPEC.md` e `decisions.md` (a frase "nunca a do navegador") e o comentário de
`lotTime.ts`. O AD-6 não mudou: o navegador não virou autoridade.

**`deferred-work.md`.** Não havia entrada de L1, L2, L3 nem da contradição D1 da 2.4; o "D1"
que existe lá é o da Story 2.3 (chamadas de mídia à AIC), sem relação. Nada a remover.
(Corrigido no re-review final: havia, sim, a entrada da contradição D1 da 2.4, na seção
"Deferred from: code review" da 2.4; ficou marcada como resolvida, sem apagar o histórico.
O D1 da 2.3 continua intacto.)

**Evidências (comandos executados em 25/10/2026).** Direcionados: `test_lot_rules.py` e
`test_lot_creation.py`, 159 passed (depois de corrigir a entrada do meu caso de teste).
`npm test`: 39 passed; lint, typecheck e build sem erro. `./verify.sh` completo, exit 0: Ruff
limpo (55 arquivos), **pytest 985 passed, 1 warning** (969 antes; os 16 a mais são os testes
do L1), `npm test` (39), build do Vite (37 módulos) e `docker build`; "verify.sh: todas as
etapas passaram." Sem smoke externo, sem git e sem deploy. Story e `sprint-status.yaml`
continuam em `review`, esperando o re-review.

## Re-review final (25/10/2026)

Re-review direcionado (Opus, sessão nova), só de L1, L2, L3, D1, das regressões dessas
correções e da sincronização documental; os demais arquivos críticos não mudaram e não
refiz o review inteiro. Sem git, sem deploy e sem alterar código. Resultado: **0 BLOCKER,
0 HIGH, 0 MEDIUM**.

- **L1 validado.** `ApiDatetime` = `AwareDatetime` + `BeforeValidator` (estrutura) +
  `AfterValidator` (`_api_datetime_normalizable`, tenta `astimezone(UTC)` e recusa o
  `OverflowError` com `datetime_format`). A recusa acontece no Pydantic, antes da
  pré-checagem e da AIC; o handler não tem `try/except` novo. `resolve_schedule`, P4,
  `starts_at=null` e `clock_timestamp()` como autoridade final não mudaram. Os 16 testes
  novos cobrem o risco, não só a implementação: 4 entradas que estouram × 2 campos no
  unitário (inclusive o primeiro que estoura, `9999-12-31T19:00:00-05:00`); 7 extremos que
  cabem seguem aceitos; na rota, os dois extremos em `starts_at` e em `ends_at` dão 422
  `validation_error` com `details` exatos, `fake.requests == []` e zero linhas; e um lote
  com término `9999-12-31T23:59:59.999999Z` ainda é criado (201).
- **L2 validado.** Sem `aria-live` no `MoneyField`; `aria-describedby` liga dica e
  feedback; `aria-invalid` segue o erro; "✓"/"✕" e o texto evitam depender só da cor.
  Conferi o parser no Node: `333.33` → `dot_decimal` com "Use vírgula para os centavos.
  Ex.: 333,33."; `5`, `5,50`, `1.250,00` válidos; `10.999` → R$ 10.999,00 (válido) e
  `10,999` → `too_many_decimals`, conforme a minha decisão final. O formato pt-BR não foi
  reaberto.
- **L3 validado.** README e Q10 do `ARQUITETURA.md` dizem que `npm test` cobre a lógica
  pura de `money`, `lotTime` e `lotDraft`, sem número fixo de testes.
- **D1 validado.** `frontend-lot-creation.md` §1 e §5, `SPEC.md` e `decisions.md` dizem a
  mesma coisa: o front compara com `now` injetado (`new Date()`) só como validação
  preventiva de UX; o servidor revalida com `clock_timestamp()` e é a autoridade final. O
  histórico da mudança ficou no §5. O AD-6 não foi alterado ("não uso o relógio do
  navegador para decisões de domínio").
- **`verify` rodado de novo no re-review:** exit 0; Ruff "All checks passed!", "55 files
  already formatted"; **pytest 985 passed, 1 warning**; ESLint, `tsc`, `npm test` (39
  testes, 39 passaram, 0 falharam), build do Vite (37 módulos) e `docker build`;
  "verify.sh: todas as etapas passaram."
- **Resíduos documentais (LOW), corrigidos no fechamento:** a entrada da contradição D1
  da 2.4 continuava como pendente em `deferred-work.md` (a correção tinha dito que não
  havia) e a linha de testes de componentes ainda dizia "só `money.ts`"; os itens desta
  seção "Review Findings" ainda estavam abertos; `docs/uso_de_ia.md` atribuía a mim o caso
  de teste com a conta errada, que foi escrito pela IA; a dica do campo de dinheiro no §4
  da spec era a antiga. Nada disso muda comportamento.

**Evidência manual considerada** (só o que vi): banco local em `0002` que precisou da
`0003`; fluxo funcionando depois da migration; validações monetárias e temporais; data
passada bloqueada antes da revisão; revisão; criação; "Lote criado"; `POST /api/lots` 201
com valores em centavos coerentes; celular a cerca de 375 px; `BIDDER` sem controles do
leiloeiro; anônimo no login; feedback monetário válido. **Não observado:** o payload exato
do POST, 320 px, o teclado e o refresh de "Meus lotes".

## Conferência documental (fechamento)

Conferi a coerência entre `docs/ARQUITETURA.md` (Q4 e Q10 em parte, histórico; nenhuma
AD), a spec e `decisions.md`, esta story, `docs/uso_de_ia.md`, `CLAUDE.md` (só os dois
resumos de questões), `README.md` e `deferred-work.md`. O `epics.md` não precisou de nota
(a story entrega o que o critério pede, com `/api/lots/mine` no lugar de uma lista
"no painel"). O teste manual, o code review e o re-review final foram feitos.

## Registro e status

Status: **done** (25/10/2026). Implementada em 24/10/2026, só a 2.4; a 2.5 não foi
iniciada. `./verify.sh` do re-review final: exit 0, 985 passed, `npm test` 39. O commit é
meu; sem deploy nesta story.
