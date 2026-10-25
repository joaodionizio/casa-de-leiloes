# Story 2.5 — Vitrine pública e página do lote

Status: done

Chave do sprint: `2-5-vitrine-pública-e-página-do-lote`
Épico: 2. Data de criação: 25/10/2026.

## Story e objetivo

Como visitante,
quero ver os lotes separados em ao vivo, agendados e encerrados e abrir cada um,
para que eu encontre o que está em disputa agora.

Nesta story transformo os lotes persistidos na 2.4 na experiência pública do produto.
Qualquer pessoa, **sem login**, abre a aplicação e cai na vitrine; vê os lotes
separados pelo estado temporal; abre a página pública de um lote com imagem, ficha da
obra, lance inicial, incremento mínimo e horários. O login deixa de ser a porta de
entrada e passa a ser uma ação explícita ("Entrar"). Usuários autenticados veem a mesma
vitrine, com as opções do seu papel.

Entrego: duas leituras públicas (`GET /api/lots` e `GET /api/lots/{lot_id}`), com o
estado temporal derivado no servidor a partir da hora do PostgreSQL; a vitrine; a página
do lote; a navegação pública com URL própria para cada lote; o header por papel; os
estados de carregando, vazio e erro; testes em PostgreSQL real; documentação.

Não entrego nada de lance. A página do lote é a base que a sala (3.5, 4.1) vai
completar, sem controle falso de lance agora.

> **Leitura desta story (25/10/2026).** A spec final e aprovada está em
> `_bmad-output/specs/spec-story-2-5-vitrine-publica/` e prevalece sobre qualquer texto
> antigo abaixo. As questões P1 a P9 foram decididas por mim antes do código; o texto da
> seção "Questões abertas" é o de antes das decisões (registro histórico) e as decisões
> vigentes, D1 a D20, estão em "Decisões fechadas". Onde um trecho antigo ainda cita
> `settlement_status`, cache de imagem, duas consultas, `id DESC` nos encerrados ou 12
> encerrados iniciais, ele foi corrigido ou marcado; vale o que está em "Decisões
> fechadas".

## Fontes e base real

Uso `CLAUDE.md`, `docs/ARQUITETURA.md` (AD-4, AD-6, AD-11, AD-12, AD-15, AD-19, AD-22,
AD-23, AD-24, AD-26, AD-29, AD-30 e as questões Q4, Q8 e Q10),
`docs/FRONTEND-WORKFLOW.md`, `DESIGN.md`, `EXPERIENCE.md`, `VITRINE-BLUEPRINT.md`
(obrigatório: a story toca a Vitrine), `epics.md` (Story 2.5, FR6, NFR2),
`sprint-status.yaml`, as Stories 2.1 a 2.4, a spec da 2.4 (`SPEC.md`, `decisions.md`,
`database-schema.md`, `backend-contract.md`, `frontend-lot-creation.md`, `test-plan.md`)
e a spec da 2.3 (`SPEC.md`, `backend-contract.md`), para a estratégia de mídia.

**Título e escopo conferidos no `epics.md`.** O título exato é **"Vitrine pública e
página do lote"**; o slug real é `2-5-vitrine-pública-e-página-do-lote`. ADs declaradas
pelo `epics.md`: AD-6, AD-15, AD-19, AD-22, AD-29. Dependência declarada: **Q8** (nome e
cálculo do estado "Encerrado, apurando resultado"), que vira a P8. Cobertura: FR6 e
parte do NFR2.

**Divergências encontradas:**

- **"Encerrado, apurando resultado" (Q8).** O `epics.md` exige que um lote com `ends_at`
  vencido e ainda não liquidado apareça como "Encerrado, apurando resultado", e o AD-19
  diz que a leitura "representa" esse estado transitório. Como a liquidação só existe na
  4.3, **todo** lote encerrado hoje é "encerrado e não liquidado". A instrução desta
  sessão fala em três estados e pede para não misturar o fim temporal com a liquidação.
  **Decisão final (P8):** não crio segundo eixo agora. Existe só `phase`
  (`scheduled`/`live`/`ended`); "Encerrado, apurando resultado" é cópia de interface para
  todo `ended`, sem `settlement_status`, coluna, campo, enum ou valor de liquidação.
- **"Lotes cancelados não aparecem."** O critério existe no `epics.md`, mas o
  cancelamento só nasce na 3.6 (`cancelled_at`). Hoje o critério é vazio: não há lote
  cancelado. Registro em `deferred-work.md` que a 3.6 precisa acrescentar o filtro às
  duas leituras públicas desta story (além do predicado do seed, já registrado).
- **Imagens (D1 da 2.3).** `deferred-work.md` diz textualmente: cache, miniatura menor e
  limite da rota de imagem "ficam fora da Story 2.3; decidir na 2.5 (vitrine pública usa
  as mesmas imagens)". A vitrine multiplica as chamadas ao proxy público, `no-store`, de
  843 px, contra o limite de 60 req/min da AIC. **Decisão final (P9):** a estratégia da 2.3 fica
  intacta (proxy `no-store`, 843 px, sem cache novo); o risco continua no `deferred-work.md`.
- **`GET /api/lots` responde 405 hoje.** `test_lot_creation.py` (linha 787) fixa esse
  405 com o comentário de que a 2.5 cria o GET público. A troca para 200 é mudança de
  contrato prevista pela própria 2.4, não afrouxamento; `PUT`/`DELETE` continuam 405.
- **Ordem das rotas.** `app/lots.py` registra `GET /api/lots/mine` com o comentário
  "Registrada antes de qualquer `/api/lots/{lot_id}` (2.5)". A rota nova precisa vir
  depois, e um teste fixa isso (CA5).
- **"Lance atual" e countdown.** `DESIGN.md` §7 e o blueprint mostram "lance atual" e
  tempo restante nos lotes ao vivo. Não existe lance antes da 3.4: mostro o **lance
  inicial**, com esse rótulo. O countdown depende da P3.
- **Rótulos.** O blueprint decidiu "Próximos lotes" como título da **seção** de
  agendados; a instrução desta sessão pede "Agendado" como texto do **estado**. Não há
  conflito: o estado de cada lote diz "Agendado" e a seção pode se chamar "Próximos
  lotes" (a story prevalece se houver dúvida).
- **Login como porta de entrada.** Hoje o `App.tsx` mostra o formulário de login a
  qualquer anônimo, e o `BIDDER` logado vê só um `h1` oculto. Ambos mudam: anônimo e
  `BIDDER` passam a ver a vitrine.
- **Links condicionais do blueprint** ("Ver todos", "Ver agenda", "Ver arquivo", âncoras
  do header) só aparecem com destino real. Nesta story não há páginas de listagem, então
  não são renderizados.
- **AD-22 e a palavra "cache".** O AD-22 revisado diz que os bytes ficam "sem
  filesystem, banco ou cache" e a 2.3 decidiu `no-store` (P8). Se a P9 permitir cache
  **do navegador**, preciso confirmar que o AD-22 fala do servidor (ver P9). **Resolvido:**
  a P9 não permitiu cache algum, então o AD-22 não é tocado.
- A skill `bmad-create-story` não está instalada em `.claude/skills/`. Sigo a estrutura
  das stories 2.1 a 2.4.

**Base existente (conferida nos arquivos, sem git):**

- `backend/app/lots.py`: modelo `Lot` (sem coluna `status`, P3 da 2.4); `database_now
  (session)` lê `clock_timestamp()` e devolve UTC; `LotResponse` (privado, com
  `created_at`, sem `is_demo` nem `auctioneer_id`); `lot_response()` com `image_url`
  derivada por `image_url_for`; `register_lot_routes` registra `POST /api/lots` e
  `GET /api/lots/mine` (`AUCTIONEER`), nessa ordem. O `backend-contract.md` §7 da 2.4
  definiu a fase temporal como conceito único (agendado `now < starts_at`; ao vivo
  `starts_at <= now < ends_at`; encerrado `now >= ends_at`) e disse que, quando a 2.5 a
  expuser, ela sai do back-end com a hora do banco, de uma função única em
  `app/lots.py`.
- `backend/app/seed.py`: "demo aberto" = `is_demo AND ends_at > now` (o mesmo que "não
  encerrado"); cada demo dura 72 h e um novo nasce no boot quando todos venceram. Demos
  encerrados se acumulam e vão aparecer em "Encerrados".
- `backend/app/access.py`: `AccessPolicy.PUBLIC` com a dependência `public()` (não toca
  no banco); `api_route` é o único registro; `NO_STORE`.
- `backend/app/catalog.py`: `GET /api/catalog/images/{image_id}` é `PUBLIC`,
  `no-store`, 843 px, sem cache; 404 do upstream → 404, qualquer outra falha → 503.
- `backend/app/spa.py`: o fallback serve `index.html` a qualquer caminho fora de `/api` e
  `/health` sem extensão, só `GET`/`HEAD`. Um link direto para `/lots/<id>` já recebe a
  SPA em produção (teste da 1.3); o Vite faz o mesmo em desenvolvimento.
- `backend/app/errors.py`: envelope `{status, code, message[, details]}`; 422 com
  `details` `{loc, type}`; 404 `not_found` existe.
- Front-end: sem roteador; `App.tsx` decide entre login e área autenticada;
  `SiteHeader.tsx` com a navegação do leiloeiro ("Criar lote", "Meus lotes") por estado;
  `ArtworkImage.tsx` (caixa estável, placeholder no `onError`, `lazy` fora do `large`);
  `money.ts` com `formatCents`; `lotTime.ts` com `formatDateTime` (fuso do navegador);
  testes de lógica pura com `node --test` no `verify` (Q10, em parte).
- Último `verify` registrado (2.4, re-review final): **pytest 985 passed**, `npm test` 39.

## Critérios de aceitação

1. **CA1 — Vitrine sem login.** Dado um visitante sem sessão, quando abre a aplicação
   (`/`), então vê a vitrine, não o formulário de login. Nenhuma leitura da vitrine ou do
   lote exige sessão. `BIDDER` e `AUCTIONEER` logados veem a mesma vitrine e o mesmo
   conteúdo de lote.
2. **CA2 — Três estados, nunca só por cor.** Dado lotes agendados, ao vivo e encerrados,
   quando abro a vitrine, então vejo três grupos (forma do contrato na P1, ordem na P4),
   e cada lote mostra o estado em texto em português ("Ao vivo", "Agendado",
   "Encerrado", e o texto da P8 para encerrado não liquidado); cor, se usada, sempre
   acompanha o texto. Grupo vazio tem tratamento explícito, sem conteúdo falso. Lotes
   cancelados não aparecem (vazio até a 3.6; a 3.6 acrescenta o filtro).
3. **CA3 — Estado derivado no servidor, com a hora do banco.** A classificação usa um
   **único** instante do PostgreSQL por leitura (`clock_timestamp()` avaliado uma vez,
   nunca por linha), aplicado a todos os lotes da resposta, e esse instante (`as_of`) e as
   linhas pertencem ao **mesmo snapshot**: cada rota executa **um único statement**
   (`WITH clock AS MATERIALIZED (…) SELECT … FROM clock LEFT OUTER JOIN lots …`), nunca
   duas consultas independentes (P2 refinada, D1). Fronteiras:
   `now < starts_at` → agendado; `starts_at <= now < ends_at` → ao vivo; `now >= ends_at`
   → encerrado, com microssegundos. O navegador nunca classifica nem reclassifica um
   lote; ele apresenta o valor recebido (P3 define o que acontece com a página aberta).
4. **CA4 — Encerrado não liquidado e leitura sem efeito.** Dado um lote com `ends_at`
   vencido, quando a vitrine ou a página do lote o lê, então ele aparece com a
   representação da P8 ("Encerrado, apurando resultado"), separando o fim temporal da
   liquidação (que não existe nesta story). A leitura não altera estado, não trava o
   lote, não liquida, não roda o seed e não faz `INSERT`, `UPDATE` nem `DELETE`
   (AD-19, AD-29).
5. **CA5 — Rotas públicas.** `GET /api/lots` e `GET /api/lots/{lot_id}` declaram
   `AccessPolicy.PUBLIC` por `api_route`, respondem `Cache-Control: no-store` e seguem os
   contratos das P1 e P6. `GET /api/lots/{lot_id}` fica registrada **depois** de
   `GET /api/lots/mine`: `GET /api/lots/mine` continua `AUCTIONEER` (401 anônimo, 403
   `BIDDER`), e um teste fixa a ordem em `app.routes`. `GET /api/lots` deixa de ser 405;
   `PUT`/`DELETE /api/lots` continuam 405.
6. **CA6 — Erros do detalhe.** `lot_id` fora do formato UUID e UUID válido inexistente
   seguem a P6, no formato único da 2.1; erro inesperado de banco → 500 genérico, sem
   stack. Vitrine vazia → 200 com grupos vazios, não erro.
7. **CA7 — Independência da AIC.** Com o transporte da AIC sempre falhando, as duas
   rotas devolvem exatamente a mesma resposta e o transporte não recebe nenhuma
   requisição. Todos os dados de negócio (título, artista, data, técnica, dimensões,
   departamento, tipo, crédito, URL da fonte, valores, horários) vêm só do PostgreSQL.
8. **CA8 — Nada interno exposto.** Nenhuma rota pública devolve `auctioneer_id`,
   `is_demo`, e-mail, nome ou qualquer dado de usuário; os campos são exatamente os da P1
   e da P6 (teste das chaves e do OpenAPI). O lote demo aparece como qualquer outro lote,
   sem marca "DEMO".
9. **CA9 — Imagem.** `image_url` é sempre a rota same-origin
   `/api/catalog/images/{image_id}`, derivada do `image_id` persistido; nunca hotlink, e
   nenhum byte é guardado. Imagem que falha cai no placeholder local e não esconde título,
   estado, valores nem horários. A política de cache e de quantidade de chamadas segue a
   P9.
10. **CA10 — Página do lote.** Dado um lote, quando abro a página dele, então vejo
    imagem (ou placeholder), título ("Sem título" se `null`), artista, data, os
    atributos da P6, lance inicial e incremento mínimo em reais (`formatCents`, a partir
    dos centavos), início e término com fuso, e o estado em texto. Não existe botão "Dar
    lance", habilitado ou desabilitado, nem campo de valor, carteira, histórico ou
    countdown falso.
11. **CA11 — Navegação e login explícito.** A navegação segue a P5: vitrine → lote →
    voltar funciona por clique e pelo botão "voltar" do navegador; recarregar a página do
    lote mostra o mesmo lote; o login abre só pelo botão "Entrar"; o destino depois do
    login segue a P5. Header: anônimo → marca, "Vitrine" (se a P5 mantiver), "Entrar";
    `BIDDER` → marca, "Vitrine", identificação, "Sair" (sem carteira nem lances);
    `AUCTIONEER` → marca, "Vitrine", "Criar lote", "Meus lotes", identificação, "Sair".
    O fluxo de criação de lote e "Meus lotes" da 2.4 continua funcionando.
12. **CA12 — Estados, responsividade e acessibilidade.** Vitrine e página do lote têm
    estados de carregando, erro do nosso servidor (com "Tentar novamente"), vazio,
    grupos vazios e imagem quebrada. Funcionam em desktop, 375 px e 320 px, sem rolagem
    horizontal global, com títulos longos, valores grandes e datas legíveis. Hierarquia
    de headings coerente; cada lote é um link acessível por teclado com nome que inclui o
    título; foco movido para o `h1` da nova vista ao navegar; foco visível; `alt` na
    imagem; nada essencial depende de hover. A composição segue `DESIGN.md`,
    `EXPERIENCE.md` e `VITRINE-BLUEPRINT.md` (obra protagonista, sem cara de SaaS).
13. **CA13 — Página aberta com o tempo passando.** O comportamento quando um lote cruza
    `starts_at` ou `ends_at` com a página aberta é o da P3, documentado no README em
    "Comportamentos que podem surpreender". Em nenhuma opção o relógio do navegador
    decide o estado.
14. **CA14 — Sem migration.** Nenhuma tabela, coluna, índice nem revisão Alembic nova;
    nenhuma coluna `status` (P3 da 2.4). Se o `bmad-spec` encontrar necessidade real de
    schema, ela volta para mim como questão.
15. **CA15 — Verificação e documentação.** Testes no mesmo commit, críticos em PostgreSQL
    real; `./verify.sh` completo com a saída real; README, `docs/uso_de_ia.md`, esta
    story e `sprint-status.yaml` atualizados; resolução da Q8 em `docs/ARQUITETURA.md`
    (questões e histórico, sem AD nova, salvo se a P9 exigir revisar o AD-22); a
    conferência documental da seção "Fechamento" antes de `done`. Paro na 2.5.

## Decisões herdadas (não reabro)

| Fonte | O que já está decidido |
| --- | --- |
| AD-6, AD-26 | A hora do PostgreSQL é a autoridade; um instante por operação; a regra recebe `now` por parâmetro. Numa leitura não há trava a adquirir: o instante é lido uma vez, no mesmo statement que lê os lotes. O front pode exibir horários, nunca decidir. |
| AD-12, AD-23 | Snapshot copiado no lote; nenhuma leitura de lote usa a AIC. |
| AD-15 | Catálogo de museu; estados nunca só por cor; tokens CSS próprios. |
| AD-19, AD-29 | GET/HEAD/OPTIONS nunca alteram estado; nenhuma leitura liquida; leitura de lote vencido e não liquidado representa "Encerrado, apurando resultado". |
| AD-22 (revisado) | Mídia pelo proxy same-origin público; bytes nunca armazenados no servidor; falha → placeholder. |
| AD-24 | Seed independente da vitrine; o demo é um lote como os outros. |
| AD-11, AD-30 | Papéis `AUCTIONEER`/`BIDDER`; rotas e campos em inglês, interface em português. |
| AD-4 | TypeScript simples; sem generics complexos. |
| 2.1 | Envelope único; 422 com `{loc, type}`; 500 genérico. |
| 2.2 | `api_route` como único registro; teste de política sem afrouxar o verificador; mensagens pelo `code`. |
| 2.3 | `image_url_for`; proxy público; placeholder; `ArtworkImage`. |
| 2.4 P3 | Sem coluna `status`; fase derivada; marcos não temporais nascem como colunas aditivas (3.6 `cancelled_at`, 4.3 liquidação). |
| 2.4 §7 | Definição única da fase temporal, inclusive as fronteiras; a função mora em `app/lots.py`. |
| 2.4 D6/P9 | `LotResponse` e "Meus lotes" são privados do leiloeiro; `is_demo` e `auctioneer_id` nunca saem. |
| 2.4 Q1 | `node --test` para lógica pura do front, sem dependência nova. |
| Blueprint §5 | Destaque: lote ao vivo com `ends_at` mais próximo; sem ao vivo, o próximo agendado ("Começa em…"); sem nenhum, estado vazio editorial. O desempate ficou para esta story (P4). |
| Blueprint (topo) | Classificação e tempo vêm sempre do servidor; o countdown no navegador nunca reclassifica o lote. |

## Política de acesso das rotas novas

| Rota | Método | Política | Anônimo | `BIDDER` | `AUCTIONEER` |
| --- | --- | --- | --- | --- | --- |
| `/api/lots` (vitrine) | `GET` | `PUBLIC` | 200 | 200 | 200 |
| `/api/lots/{lot_id}` (detalhe) | `GET` | `PUBLIC` | 200/404/422 | idem | idem |

Nenhuma rota existente muda de política. `GET /api/lots/mine` continua `AUCTIONEER`.
`PUBLIC` e não `OPTIONAL`: a resposta não depende de quem pede, então a leitura nem
consulta a sessão.

## Contrato proposto (a confirmar pelas P1, P2, P6 e P8)

```text
GET /api/lots            → 200, no-store
{
  "as_of": "2026-10-25T18:00:00.123456Z",        // o instante do banco usado (P1)
  "live":      [PublicLotSummary...],            // P1 (a): grupos; P4: ordem
  "scheduled": [PublicLotSummary...],
  "ended":     [PublicLotSummary...]
}

PublicLotSummary (P6 a)
  id, title, artist_display, date_display, image_url,
  starting_bid_cents, starts_at, ends_at,
  phase: "scheduled" | "live" | "ended",          // P2; não há segundo eixo (P8)

GET /api/lots/{lot_id}   → 200 PublicLotDetail, no-store; 404 not_found; 422 (P6)
PublicLotDetail = PublicLotSummary
  + external_id, medium_display, dimensions, department_title,
    artwork_type_title, credit_line, source_url, min_increment_cents
  (a resposta é {"as_of", "lot": PublicLotDetail}; contrato final em public-lot-dtos.md)
```

Fora de qualquer DTO público: `auctioneer_id`, `is_demo`, `created_at` (P6),
`image_id` cru (já está dentro de `image_url`; ver P6) e qualquer dado de usuário.

## Fase temporal e autoridade de tempo

- **Definição (herdada, 2.4 §7):** `scheduled` se `now < starts_at`; `live` se
  `starts_at <= now < ends_at`; `ended` se `now >= ends_at`. Coerente com o AD-5 (lance
  depois do fim nunca reabre) e com a 3.2 (`now >= ends_at` → encerrado).
- **Fim temporal ≠ liquidação.** `phase = "ended"` diz só que `ends_at <= now`. Se o lote
  foi liquidado (vencedor, débito, comprovante) é outro eixo, que nasce na 4.3. Esta
  story não grava, não calcula e não promete resultado; a resposta não representa
  "ainda não liquidado" (P8): a interface mostra "Encerrado, apurando resultado" para todo
  `ended`.
- **Um instante por leitura.** `clock_timestamp()` muda a cada chamada, inclusive entre
  linhas do mesmo `SELECT`. Avaliá-lo por linha (por exemplo, num `CASE` sem
  materializar) daria a dois lotes da mesma resposta instantes diferentes. O instante é
  lido uma vez, no mesmo statement que lê os lotes, e usado para todas as linhas (CTE
  `MATERIALIZED` + `LEFT OUTER JOIN`, D1).
- **Sem `FOR UPDATE`.** Leitura pública não trava o lote: um lance (3.4) ou um fechamento
  (4.3) com a trava não pode ficar esperando a vitrine, nem o contrário.
- **O navegador só apresenta.** Ele recebe `phase` e os horários e exibe. Não compara
  `starts_at`/`ends_at` com `new Date()` para trocar estado (blueprint, AD-6).

## Questões abertas (decidir no `bmad-spec`, antes do código)

Cada questão tem até três opções, consequências, recomendação, impacto e se é **local**
ou **arquitetural**. As recomendações são propostas; a decisão é minha.

> **Registro histórico.** Esta seção guarda as questões como eu as tinha antes de
> decidir, com opções e recomendações. As decisões finais (P1 a P9 e D1 a D20) estão em
> "Decisões fechadas"; onde divergem do texto abaixo (P2, P4, P7, P8, P9), vale a seção
> "Decisões fechadas".

### P1 — Forma da resposta da vitrine

**Problema.** A vitrine precisa de três grupos e de um destaque. Falta decidir se os
grupos vêm prontos do servidor ou se o front agrupa uma lista.

- **(a)** Objeto com três listas já classificadas e ordenadas: `{"as_of", "live",
  "scheduled", "ended"}`; cada item também traz `phase`, para um tipo único de item.
- **(b)** Lista plana `{"as_of", "items": [...]}`, cada item com `phase`, ordenada por
  grupo e chave; o front separa por `phase` (filtro simples, sem reclassificar).
- **(c)** Uma rota por grupo, ou `GET /api/lots?phase=live`.

`as_of` (em todas) é o instante do banco usado na classificação: torna a resposta
explicável ("classificado em X") e dá à sala (3.5) um ponto de referência do servidor
para o countdown, sem confiar no relógio do navegador. Proposta: incluir.

**Consequências.** (a) deixa o front sem lógica nenhuma (destaque = `live[0]`, senão
`scheduled[0]`), e a ordem por grupo é garantida e testada no servidor; um item aparece
num só grupo por construção. (b) é o formato mais comum e se estende melhor à busca e ao
filtro do OPT1, mas obriga o front a agrupar. (c) multiplica rotas e chamadas, e três
leituras teriam três instantes diferentes.

**Recomendação:** (a), com `as_of`. **Impacto:** contrato público, tipos do front,
testes; o OPT1 (6.5) acrescenta parâmetros sem mudar a forma. **Local.**

### P2 — Quem calcula a fase e como

**Problema.** O `epics.md` exige "usa a hora do banco, não a do navegador". Falta onde e
como.

- **(a)** Back-end, em Python: `now = database_now(session)` uma vez; um único `SELECT`
  de lotes; a função pura `lot_phase(starts_at, ends_at, now)` (em `app/lots.py`)
  classifica cada linha; agrupar e ordenar em Python. As duas instruções correm na mesma
  transação de leitura.
- **(b)** Back-end, em SQL: uma instrução só, com o instante materializado uma vez
  (subconsulta não correlacionada ou CTE `MATERIALIZED`) e `CASE` para a fase; `ORDER BY`
  no SQL.
- **(c)** Front-end, a partir de `starts_at`/`ends_at` com o relógio do navegador.

**Consequências.** (a) segue o AD-26 à letra: a regra recebe `now` e é testável com
`now` fixo, em microssegundos, sem banco; a mesma função serve à 3.2/3.4 e ao predicado
do seed; o serviço `list_public_lots(session, now)` pode ser chamado nos testes de
integração com um `now` fixo contra linhas reais. Lê todos os lotes de uma vez (sem
N+1); a ordenação em Python é trivial na escala do desafio. (b) é uma ida ao banco a
menos, mas põe a regra no SQL, onde só se testa pelo banco e é fácil errar o
`clock_timestamp()` por linha; duplicaria a definição que a 2.4 pediu para ficar numa
função. (c) contraria o AD-6 e o critério do `epics.md`; dois relógios divergem.
Descarto (c).

**Recomendação:** (a), com o nome do campo `phase` e os valores `scheduled`, `live`,
`ended`. **Impacto:** 3.2/3.4 reutilizam `lot_phase`; a 3.5 recebe `phase` pronto.
**Local** (aplica AD-6/AD-26 sem mudá-los).

### P3 — A página aberta quando o tempo cruza um limite

**Problema.** Um lote agendado começa, ou um ao vivo termina, com a vitrine ou a página
do lote aberta. Não há WebSocket nesta story, e o blueprint diz que a vitrine não é
atualizada por WebSocket se a arquitetura não pedir.

- **(a)** Retrato do momento: a fase só muda num novo `GET` (abrir outra vista, voltar,
  recarregar). Sem countdown na 2.5: horários absolutos com fuso ("Termina 26 de out.,
  18:00 BRT"). O README avisa.
- **(b)** Como (a), mais **um** novo `GET` agendado para o próximo limite: o front
  calcula a espera só com valores do servidor (`menor starts_at/ends_at futuro − as_of`),
  dispara um temporizador e pede de novo; quem reclassifica continua sendo o servidor.
- **(c)** Polling periódico (por exemplo, a cada 30 s) enquanto a aba está visível.

**Consequências.** (a) é a menor e a mais fácil de explicar; o rótulo "Ao vivo" pode
ficar velho até o próximo `GET`, sem efeito de domínio (lance é validado no servidor,
3.4). Sem countdown, nada chega a 00:00 com o rótulo errado. (b) corrige o rótulo na
hora certa sem polling e sem o relógio do navegador decidir, ao custo de um temporizador,
cancelamento ao trocar de vista e testes; o atraso do temporizador é alguns
milissegundos. (c) é tráfego constante no Render gratuito e contra o espírito do
"sem polling" desta story; a sala ganha tempo real na 4.1 de qualquer forma.

**Recomendação:** (a). O countdown nasce na sala (3.5), calculado a partir do servidor.
**Impacto:** README; a 3.5/4.1 decidem o tempo real da sala. **Local.**

### P4 — Ordenação e desempate

**Problema.** A vitrine precisa ser útil e determinística; o blueprint deixou o
desempate para esta story.

- **(a)** Ao vivo: `ends_at ASC, id ASC` (termina primeiro no topo). Agendados:
  `starts_at ASC, id ASC` (começa primeiro). Encerrados: `ends_at DESC, id DESC` (o que
  acabou de terminar primeiro). Destaque = primeiro ao vivo, senão primeiro agendado.
- **(b)** Como (a), mas encerrados por `created_at DESC`.
- **(c)** Todos por `created_at DESC` (mais novos primeiro), com a fase só como rótulo.

**Consequências.** (a) responde às perguntas do `EXPERIENCE.md` §3 (o que está ao vivo
agora, o que começa depois, o que terminou) e combina com a regra do destaque do
blueprint, que passa a ser só "o primeiro da lista"; o `id` torna a ordem total e
testável. (b) mistura quando o lote foi criado com quando terminou. (c) ignora a
urgência e enterra o lote que está terminando.

**Recomendação:** (a). **Impacto:** testes de ordem; a 4.1 e a 6.5 herdam. **Local.**

### P5 — Navegação, URL do lote e login sem React Router

**Problema.** A 2.2 (P15), a 2.3 (P10) e a 2.4 (P9) adiaram o roteador para a 2.5, "que
precisa dele de verdade". A página pública do lote precisa ser abrível por link,
recarregável e compatível com o botão "voltar"; a sala (3.5) e o comprovante (5.2) vão
apontar para ela.

- **(a)** Navegação mínima própria, com a History API e sem dependência nova: caminhos
  `/` (vitrine), `/lots/{lot_id}` (página do lote), `/login` e caminhos para "Criar lote"
  e "Meus lotes" (nomes no `bmad-spec`); um módulo pequeno com `parseRoute(pathname)` e
  `routePath(route)` (funções puras, testadas por `node --test`), `pushState` e
  `popstate`; links `<a href>` de verdade com o clique interceptado (abre em nova aba
  normalmente). `lot_id` que não é UUID vira a vista "Página não encontrada", sem
  chamar a API.
- **(b)** Estado em memória, como na 2.4: sem URL por lote, sem "voltar" do navegador,
  recarregar volta à vitrine.
- **(c)** React Router (dependência nova).

**Destino depois do login (sub-ponto).** (i) volta à página de onde a pessoa clicou
"Entrar" (guardada em memória, nunca por `?next=` livre); aberto direto em `/login`,
vai para a vitrine. (ii) destino por papel (`AUCTIONEER` → "Meus lotes"; `BIDDER` →
vitrine). Sessão expirada numa área do leiloeiro continua levando ao login com "Sua
sessão expirou." e, depois, de volta à mesma área. Depois de "Sair", a pessoa fica na
vitrine (ou na página pública em que estava).

**Consequências.** (a) entrega link direto, recarga e "voltar" com umas dezenas de
linhas explicáveis; o fallback da SPA (1.3) já serve `/lots/...` em produção e o Vite em
desenvolvimento; o parser é testável sem DOM; o risco é reimplementar mal o que um
roteador faz (foco, rolagem), coberto pela spec e pelo roteiro manual. (b) é a menor,
mas a página do lote não seria compartilhável e a 3.5/5.2 teriam de trocar tudo. (c)
resolve o mesmo com uma dependência e uma API maiores do que três ou quatro rotas pedem
(AD-4: preferir o simples).

**Recomendação:** (a) com (i). **Impacto:** `App.tsx`, `SiteHeader.tsx`, navegação do
leiloeiro da 2.4, login; 3.5 e 5.2 reutilizam as rotas. **Local** (decisão de front sem
AD; registro na story e no README).

### P6 — Campos do item e do detalhe, e o `lot_id` inválido

**Problema.** O que cada leitura pública expõe, e o que acontece com um `lot_id` ruim.

- **(a)** Dois DTOs públicos próprios: `PublicLotSummary` (o que o item da vitrine
  mostra: `id`, `title`, `artist_display`, `date_display`, `image_url`,
  `starting_bid_cents`, `starts_at`, `ends_at`, `phase` + o campo da P8) e
  `PublicLotDetail` (o resumo + `external_id`, `medium_display`, `dimensions`,
  `department_title`, `artwork_type_title`, `credit_line`, `source_url`,
  `min_increment_cents`). Sem `created_at` e sem `image_id` separado.
- **(b)** Um DTO público único, igual ao detalhe, também na lista.
- **(c)** Reaproveitar o `LotResponse` da 2.4 nas rotas públicas, acrescentando `phase`.

**`lot_id` inválido (sub-ponto).** Proposta: `lot_id: uuid.UUID` no caminho; formato
inválido → 422 `validation_error` com `details` `[{"loc": ["path", "lot_id"], "type":
"uuid_parsing"}]` (o tipo real do Pydantic fica fixado no teste), seguindo o precedente
da rota de imagem; UUID válido inexistente → 404 `not_found`; ambos `no-store`. A
alternativa é 404 para os dois (esconde a diferença, mas foge da convenção da 2.1).

**Consequências.** (a) separa o contrato público do privado: quando a 4.5 acrescentar
resultado e total ao "Meus lotes", nada vaza para a vitrine; a lista fica leve. (b) é
mais simples, mas leva para a vitrine dados que ela não mostra. (c) acopla o público ao
privado e expõe `created_at`. Em todas, `is_demo` e `auctioneer_id` nunca saem (D6 da
2.4).

**Recomendação:** (a) e 422 para formato inválido. **Impacto:** OpenAPI, tipos do front;
3.4/3.5 acrescentam `current_bid_cents` e similares como campos aditivos. **Local.**

### P7 — Paginação e limite

**Problema.** Sem paginação, a vitrine devolve todos os lotes. Os demos encerrados se
acumulam (um por boot a cada 72 h, no mínimo), e o `DESIGN.md` pede pensar em 50
encerrados.

- **(a)** API sem paginação e sem limite (todos os lotes, como o "Meus lotes" da A2); no
  front, "Encerrados" mostra os primeiros N (proposta: 12) e um botão "Mostrar mais
  encerrados" revela os próximos N, só localmente, sem nova chamada; ao vivo e
  agendados aparecem inteiros, em rails com imagem `lazy`.
- **(b)** API sem limite e front renderizando tudo.
- **(c)** Paginação ou limite de encerrados na API (por exemplo, os 50 mais recentes,
  com outra rota para o arquivo).

**Consequências.** (a) não cria contrato novo nem limite silencioso; o botão tem função
real; a resposta cresce com o tempo (risco aceito e registrado em `deferred-work.md`).
(b) monta dezenas de imagens que ninguém vê e dispara chamadas de mídia (P9). (c) é a
solução de escala, mas é endpoint e contrato que a 2.5 não pede.

**Recomendação:** (a). **Impacto:** README e `deferred-work.md`; o OPT1 (6.5) pode
trazer paginação junto com busca e filtro. **Local.**

### P8 — "Encerrado, apurando resultado" (Q8)

**Problema.** Q8 pede o nome do valor e do campo que representam o encerrado ainda não
liquidado, e o cálculo sem alterar estado nem travar o lote. A instrução desta sessão
pede para não misturar fim temporal e liquidação.

- **(a)** Dois eixos: `phase` (temporal: `scheduled`/`live`/`ended`) e um segundo campo
  só para o resultado, por exemplo `settlement_status`, que é `null` enquanto o lote não
  encerrou e `"pending"` quando `phase = "ended"`. Hoje ele é sempre `"pending"` nos
  encerrados (não existe liquidação); a 4.3 acrescenta `"settled"` (e o resultado) quando
  houver a coluna de liquidação. A interface mostra "Encerrado, apurando resultado" para
  `ended` + `pending`.
- **(b)** Só `phase` agora; a interface mostra "Encerrado, apurando resultado" para todo
  `ended`, porque nesta story nenhum lote pode estar liquidado; a 4.3 cria o campo de
  resultado e muda a regra da tela.
- **(c)** Um único campo com quatro valores (`scheduled`, `live`, `closing`, `closed`),
  em que `closed` só vale depois da liquidação.

**Consequências.** (a) representa o estado transitório na própria resposta, como o
AD-19 descreve, e mantém os eixos separados; o custo é um campo que hoje tem um só valor
e uma regra de cálculo trivial (`ended` → `pending`). (b) não cria campo agora, mas a
resposta não diz "apurando"; quem lê a API sem a interface vê só "encerrado", e a 4.3
muda o significado do que a tela mostra. (c) mistura o temporal com o financeiro
(rejeitado pela instrução desta sessão) e faz a 3.2 e a 3.4 dependerem de um valor que
não é temporal.

**Recomendação:** (a), com o nome do campo e dos valores fechados por mim no `bmad-spec`.
**Impacto:** resolve a Q8 (registro em `ARQUITETURA.md`, questões e histórico, sem AD
nova); 4.3, 4.5 e 5.3 herdam o eixo. **Arquitetural no efeito** (fecha uma questão da
arquitetura), sem alterar AD.

### P9 — Imagens da vitrine: chamadas à AIC e cache (D1 da 2.3)

**Problema.** Cada miniatura é uma chamada do servidor ao IIIF, `no-store`, em 843 px,
contra 60 req/min por IP da AIC. Abrir a vitrine, abrir um lote e voltar repete todas as
chamadas. Excedido o limite, a AIC responde 429, o proxy dá 503 e as imagens caem no
placeholder (o resto da página continua).

- **(a)** Manter o contrato da 2.3 (`no-store`, 843 px) e reduzir chamadas só no front:
  `loading="lazy"` fora do primeiro viewport e o limite de render de encerrados da P7.
- **(b)** Como (a), mais cache **do navegador** nas respostas 200 da rota de imagem
  (por exemplo, `Cache-Control: public, max-age=86400`), mantendo `no-store` nos 404/503
  e em todo JSON. O servidor continua sem guardar nada.
- **(c)** Como (b), mais uma segunda largura fixa para miniaturas (por exemplo, 400 px),
  escolhida por um valor fechado na rota (nunca tamanho livre).

**Consequências.** (a) não mexe em decisão já fechada; a navegação vitrine ↔ lote
continua refazendo as chamadas e o placeholder pode aparecer durante a avaliação. (b)
corta as repetições no mesmo navegador sem estado no servidor; revisa a P8 da 2.3 só
para a rota de imagem; a imagem IIIF de um `image_id` é estável; a falha temporária não
fica presa no cache. Preciso confirmar que o "sem cache" do AD-22 revisado fala do
servidor; se eu o ler como incluindo o navegador, (b) exige alterar primeiro o AD-22. (c)
reduz banda e tempo de carga, mas amplia o contrato do proxy e os testes da 2.3.

**Recomendação:** (b), com a confirmação da leitura do AD-22; medir o 429 real no teste
manual. **Impacto:** `app/catalog.py` (só cabeçalho) e seus testes, se (b) ou (c);
`deferred-work.md` (D1 da 2.3 resolvido ou mantido). **Local se o AD-22 fala só do
servidor; arquitetural se não.**

### Orientação técnica (não é decisão nova)

- **Módulo.** `lot_phase` e as leituras públicas ficam em `app/lots.py` (a 2.4 pediu a
  função única lá); as rotas novas entram em `register_lot_routes`, **depois** de
  `/api/lots/mine`, o que garante a ordem num só lugar. O `bmad-spec` pode separar os
  DTOs públicos num módulo próprio se `lots.py` ficar grande, sem mudar a ordem.
- **Handlers `def`** (threadpool, AD-25), `Session` curta de `get_session`, sem commit;
  a sessão fecha com rollback. Sem `get_artic_client` nas rotas públicas.
- **Consulta.** Um `SELECT` de lotes, sem `FOR UPDATE`/`FOR SHARE`, sem N+1. Sem índice
  novo: a leitura lê tudo e ordena (a escala do desafio cabe).
- **OpenAPI.** `GET /api/lots` com `response_model` da P1 e sem erros previstos além do
  500; `GET /api/lots/{lot_id}` com `error_responses(404, 422)`. Os caminhos entram na
  lista fixada de `test_openapi.py` depois de `/api/lots/mine`, só como acréscimo.
- **Front.** Reaproveitar `ArtworkImage`, `formatCents`, `formatDateTime`; um componente
  de estado do lote (`LotPhase`) com texto + marcador não dependente de cor; nada de
  `LotCard` universal (o blueprint desaconselha); mensagens pelo `code`.

## Tarefas e subtarefas

- [x] **T1 — Planejar comigo (todas as CAs).** `bmad-spec` (Opus) decidiu P1 a P9
  comigo; a spec final está em `_bmad-output/specs/spec-story-2-5-vitrine-publica/` e as
  decisões estão em "Decisões fechadas", em primeira pessoa e com a alternativa
  descartada.
- [x] **T2 — Regra pura da fase (CA3, P2).** `lot_phase(starts_at, ends_at, now)`, sem
  relógio, com `now` aware obrigatório. Sem campo de liquidação (P8).
- [x] **T3 — Leituras públicas (CA4–CA8, P1, P4, P6).** Um statement por leitura
  (`read_public_snapshot`, `read_public_lot_snapshot`); DTOs públicos; `GET /api/lots` e
  `GET /api/lots/{lot_id}` por `api_route(..., policy=AccessPolicy.PUBLIC)`, depois de
  `/api/lots/mine`; `no-store`; OpenAPI.
- [x] **T4 — Imagens (CA9, P9).** Nada no back-end: a estratégia da 2.3 ficou intacta;
  no front, a variante `card` de `ArtworkImage` (lazy).
- [x] **T5 — Testes do back-end (CA1–CA9, CA14).** Matriz abaixo, em PostgreSQL real;
  ajuste do teste da 2.4 que fixava `GET /api/lots` → 405 (agora 200).
- [x] **T6 — Navegação e header (CA1, CA11, P5).** `route.ts` com teste `node --test`;
  `navigation.ts`; `AppLink`; `App.tsx`; `SiteHeader.tsx`; login como ação explícita;
  áreas do leiloeiro da 2.4 integradas em `/auctioneer/lots[/new]`.
- [x] **T7 — Vitrine e página do lote (CA2, CA10, CA12, CA13, P3, P7).** Cliente tipado
  `src/api/publicLots.ts`; destaque, ao vivo, próximos, encerrados; página do lote;
  estados; sem controle de lance. Responsividade e acessibilidade implementadas por
  CSS/estrutura; a conferência no navegador é minha (roteiro manual).
- [x] **T8 — Verificar e documentar (CA15).** `./verify.sh` completo; README;
  `docs/uso_de_ia.md`; Q8 em `ARQUITETURA.md`; `deferred-work.md`; esta story;
  `sprint-status.yaml`. O roteiro manual no navegador e a conferência final antes de
  `done` são meus.

## Matriz de testes esperados

Toda contagem vem do `verify` desta story. Banco: PostgreSQL `_test` real; AIC pelo
`ArticClient` com `MockTransport`; a guarda de rede continua ativa. Nada de SQLite.

| Grupo | Casos |
| --- | --- |
| Fase (unitário, `now` fixo, microssegundos) | `now = starts_at − 1 µs` → `scheduled`; `now = starts_at` → `live`; `starts_at < now < ends_at` → `live`; `now = ends_at − 1 µs` → `live`; `now = ends_at` → `ended`; `now = ends_at + 1 µs` → `ended`; offsets diferentes comparados como instantes; `now` ingênuo → `ValueError`. Não há campo da P8 (decisão final). |
| Fase com o banco (integração) | Serviço chamado com `now` fixo contra linhas reais com `starts_at`/`ends_at` exatamente em `now` e a ±1 µs (o `TIMESTAMPTZ` guarda microssegundos); caminho real (rota) com margens em torno de `db_now`. |
| Um instante e um snapshot por leitura | Todos os itens classificados com o mesmo `as_of`; `as_of` entre o `db_now` antes e depois; exatamente **um** statement por rota, com um só `clock_timestamp()`, `MATERIALIZED` e `LEFT OUTER JOIN`; o valor de `as_of` é único nas linhas cruas; lote confirmado antes da leitura entra com `created_at <= as_of` (injeção determinística) e o não confirmado não entra; controle negativo de duas consultas no próprio teste. |
| Vitrine — acesso | Anônimo 200; `BIDDER` 200; `AUCTIONEER` 200; as três respostas iguais para o mesmo banco; cookie inválido ou expirado não muda nada (rota `PUBLIC`). |
| Vitrine — conteúdo | Banco sem lotes → 200 com os três grupos vazios; vários lotes em cada fase → cada um no grupo certo e só nele; lotes de dois leiloeiros aparecem; chaves exatas do item (P6); `image_url` = `/api/catalog/images/{image_id}`; timestamps com `Z`; valores em centavos exatos. |
| Ordenação (P4, D3) | Ao vivo `ends_at ASC, id ASC`; agendados `starts_at ASC, id ASC`; encerrados `ends_at DESC, id ASC`; desempate por `id` com horários iguais; o destaque esperado é o primeiro ao vivo, senão o primeiro agendado. |
| Detalhe | Existente → 200 com as chaves exatas da P6 e valores iguais à linha; inexistente (UUID válido) → 404 `not_found`; formato inválido (`abc`, `mine-x`, UUID truncado) → o código da P6; `phase` correta em cada fase; `no-store` também nos erros montados pela rota. |
| Ordem das rotas | `GET /api/lots/mine` continua `AUCTIONEER` (anônimo 401, `BIDDER` 403, `AUCTIONEER` 200 com os próprios); em `app.routes`, `/api/lots/mine` aparece antes de `/api/lots/{lot_id}`. |
| Métodos | `GET /api/lots` 200 (substitui o 405 da 2.4); `PUT`/`DELETE /api/lots` 405; `POST /api/lots` da 2.4 intacto; `HEAD`/`OPTIONS` sem efeito. |
| Leitura pura (AD-19) | `statement_recorder` nas duas rotas: só statements `SELECT`, nenhum `FOR UPDATE`/`FOR SHARE`, nenhum `INSERT`/`UPDATE`/`DELETE`; `lot_rows` idênticas antes e depois, inclusive de um lote vencido; contagem de lotes igual; o seed não é chamado. |
| Sem trava | Outra conexão segura `SELECT ... FOR UPDATE` e um `UPDATE` não confirmado num lote; as duas rotas terminam (rede de segurança de 5 s) e mostram o valor confirmado; nenhuma conexão fica `idle in transaction`. |
| Sem AIC | Com o transporte falso sempre levantando erro: respostas idênticas e `fake.requests == []`. |
| Nada exposto | Nenhuma resposta nem schema público contém `auctioneer_id`, `is_demo`, `created_at`, `email`, `password_hash`; o demo é indistinguível de um lote manual. |
| Seed e vitrine | Depois de `run_seed`, o demo aparece em `live` (`starts_at` = agora do banco); um demo antigo vencido inserido por SQL aparece em `ended`, intocado. |
| Imagem (P9) | Rota de imagem da 2.3 intacta, sem teste novo nem alterado. `image_url` derivada do `image_id`; nenhuma chamada de mídia nas rotas de lote. |
| OpenAPI | Caminhos novos depois de `/api/lots/mine`, com os schemas públicos e propriedades exatas; nenhum schema público com `is_demo`/`auctioneer_id`; `HTTPValidationError` ausente. |
| Política (D20) | `policy_by_route` indexado por `(path, method, kind)`; chave repetida levanta `ValueError`; `EXPECTED_POLICIES` ganha as duas rotas como `PUBLIC` e distingue `GET` e `POST` em `/api/lots`; `policy_problems` inalterado. |
| Front (`node --test`) | `parseRoute`/`routePath` (P5): `/`, `/lots/<uuid>`, `/lots/<não uuid>` → não encontrado, `/login`, áreas do leiloeiro, barra final, caminho desconhecido; ida e volta. Rótulo de estado por `phase` + campo da P8 (função pura). Se houver regra pura de seleção do destaque ou de "mostrar mais", também. Cada módulo novo com lógica no nível do módulo é executado por um teste (lição da 2.4). |
| Regressões | Os 985 testes da 2.4; `/health` sem banco; login/logout/`/api/me`; criação de lote e "Meus lotes"; catálogo e proxy; SPA e fallback (`/lots/qualquer-coisa` → SPA); WebSocket técnico; `npm test` existente; `docker build`. |
| Roteiro manual (meu) | Anônimo cai na vitrine; três grupos com estado em texto; destaque; abrir lote, voltar pelo botão e pelo navegador; recarregar a página do lote; link direto em aba nova; "Entrar" e o destino da P5; `BIDDER` e `AUCTIONEER` no header; criação de lote da 2.4 e o lote novo na vitrine; imagem quebrada e AIC fora; 320 px, 375 px e desktop largo; teclado e foco; ~50 encerrados (SQL local); comportamento da P3 com um lote que vence com a página aberta. Registro só o que eu observar. |

## Regressões que devem continuar verdes

- Os testes do último `verify` da 2.4 (985); a contagem nova vem só desta story.
- `test_lot_creation.py`: só a asserção `GET /api/lots → 405` muda (contrato novo,
  previsto pela 2.4); `PUT`/`DELETE` continuam 405.
- `test_openapi.py`, `test_access_policy.py` e `test_errors.py` só ganham acréscimos.
- Fluxo do leiloeiro da 2.4 na interface (busca, formulário, revisão, confirmação,
  "Meus lotes"), agora integrado à navegação da P5.
- Login, mensagens e sessão expirada da 2.2.
- Nenhuma asserção existente afrouxada.

## Persistência, seed e integrações

- **Migration: nenhuma.** A 2.5 só lê colunas que a `0003` já tem. Nenhuma coluna
  `status` (P3 da 2.4). Nenhum índice novo.
- **Seed:** sem mudança. O demo aparece na vitrine por ser um lote; a vitrine não chama o
  seed e o seed não conhece a vitrine.
- **Integração externa:** nenhuma chamada à AIC nas leituras de lote; a imagem continua
  pelo proxy da 2.3 (P9 pode mudar só cabeçalhos dele).
- **Segredos:** nenhum novo. **Deploy:** nenhuma variável nova.

## Arquivos prováveis

| Área | Arquivo | Ação |
| --- | --- | --- |
| Back-end | `backend/app/lots.py` | alterado: `lot_phase`, DTOs públicos, leitura em um statement, duas rotas depois de `/api/lots/mine` |
| Back-end | `backend/app/catalog.py` | intocado (P9 manteve a rota de imagem da 2.3) |
| Testes | `tests/test_lot_rules.py` (ou `test_lot_phase.py`) | acréscimos/novo: fase com `now` fixo |
| Testes | `tests/integration/test_public_lots.py` | novo: vitrine, detalhe, ordem, leitura pura, sem trava, sem AIC, seed |
| Testes | `tests/integration/test_lot_creation.py` | só a asserção do `GET /api/lots` |
| Testes | `test_openapi.py`, `test_access_policy.py`, `tests/lot_support.py` | acréscimos |
| Testes | testes da rota de imagem | só se P9 mudar cabeçalhos |
| Front-end | `src/route.ts` + `src/route.test.ts` | novos (P5) |
| Front-end | `src/api/publicLots.ts` | novo: tipos e cliente das rotas públicas |
| Front-end | `src/lotPhase.ts` + teste | novo: rótulo do estado (função pura) |
| Front-end | `VitrinePage.tsx` (e não `Vitrine.tsx`, que colide com `vitrine.ts` em sistema de arquivos sem distinção de maiúsculas), `FeaturedLot`, `LotRail`, `LiveLotItem`, `UpcomingLotItem`, `ClosedLots`, `ClosedLotRow`, `LotState`, `LotPage`, `LoginPage`, `NotFoundPage`, `AppLink`, `navigation.ts`, `asOf.ts`, `vitrine.ts`, `lotLabels.ts` | novos |
| Front-end | `src/App.tsx`, `src/SiteHeader.tsx`, `src/LoginForm.tsx`, `src/App.css` | alterados |
| Front-end | `src/LotCreation.tsx`, `src/MyLots.tsx` | só o necessário para a navegação da P5 |
| Docs | `README.md`, `docs/uso_de_ia.md`, `docs/ARQUITETURA.md` (Q8; AD-22 só se a P9 exigir) | alterados |
| Docs | `CLAUDE.md` | só o resumo da questão 8, se ficar desatualizado |
| BMAD | esta story, `sprint-status.yaml`, `deferred-work.md` | alterados |
| Sem mudança | migrations, `seed.py`, `artic.py`, `access.py`, `csrf.py`, `auth.py`, `db.py`, `spa.py`, `Dockerfile`, `compose.yaml`, `start.sh`, `pyproject.toml`, `uv.lock` | intocados |
| Alterados depois do teste manual (D21, 25/10/2026) | `package.json` e `package-lock.json` (`@playwright/test` 1.64.1 em `devDependencies`, scripts `test:e2e` e `typecheck` com `e2e/`), `verify.sh` (gancho opt-in `VERIFY_E2E=1`), `.dockerignore`, `.gitignore`, `playwright.config.ts`, `frontend/e2e/` | a lista original dizia `package.json` "sem mudança"; deixou de valer |

## Front-end

**Esta story tem front-end: SIM**, e é a Vitrine. A fase seguinte usa obrigatoriamente:

- `@docs/FRONTEND-WORKFLOW.md`
- `@_bmad-output/planning-artifacts/DESIGN.md`
- `@_bmad-output/planning-artifacts/EXPERIENCE.md`
- `@_bmad-output/planning-artifacts/VITRINE-BLUEPRINT.md`

Pontos que o `bmad-spec` precisa cobrir: destaque image-led (obra no primeiro viewport,
60–65% no desktop, um CTA "Ver lote"); densidade decrescente (ao vivo > próximos >
encerrados); rails horizontais no mobile com parte do próximo item visível; encerrados
como lista densa; o caso "1 ao vivo" sem repetir a mesma imagem grande; estados nunca só
por cor; nenhum controle sem função (sem "Ver todos", sem busca, sem "Dar lance"); obra
protagonista na página do lote, com a ficha e os valores ao lado no desktop e abaixo no
mobile; foco e headings ao trocar de vista; stress test do blueprint §15 (0/1/5/12 ao
vivo, 0/3/20 próximos, 0/8/50 encerrados, títulos longos, valores grandes, proporções
variadas, imagem indisponível).

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

- Dar lance, carteira, saldo, histórico de lances, posição do usuário, "você está
  ganhando" (3.x); anti-sniping (3.4); sala em tempo real, WebSocket e reconexão (4.1,
  4.2); encerramento, liquidação, catch-up, resultado e total recebido (4.3 a 4.5);
  auditoria e comprovante (5.x); cancelamento (3.6).
- Countdown ao vivo e polling (salvo decisão diferente na P3).
- Busca e filtro de lotes (OPT1, 6.5); paginação na API (salvo decisão diferente na P7);
  edição de lote; curadoria de destaque (`featured`).
- Cache de servidor, armazenamento de imagem, proxy genérico (AD-22).
- Testes de componente ou de DOM, ou ferramenta de teste nova no front. *(Escopo original; a D21 de 25/10/2026 acrescentou o Playwright como camada de navegador opt-in. Teste de componente/DOM continua fora.)*
- Dark mode (6.7); revisão visual global (6.2).
- Não crio a Story 3.1, não altero stories concluídas e não uso git.

## Riscos

- **Crescimento sem limite.** A vitrine devolve todos os lotes; os demos encerrados se
  acumulam a cada 72 h de boot. Mitigado no front pela P7; a resposta JSON continua
  crescendo.
- **Limite da AIC nas imagens.** Muitas miniaturas por visita podem levar a 429 → 503 →
  placeholder durante a avaliação (P9).
- **Rótulo velho com a página aberta.** Com a P3 (a), "Ao vivo" pode aparecer depois do
  fim até um novo `GET`; sem efeito de domínio, mas pode surpreender (README).
- **Ordem das rotas.** Registrar `/api/lots/{lot_id}` antes de `/api/lots/mine` quebraria
  "Meus lotes" (422 público no lugar do 401/403/200); coberto por teste.
- **`clock_timestamp()` por linha.** Um `CASE` com `clock_timestamp()` sem materializar
  daria instantes diferentes na mesma resposta; coberto pela P2 e por teste.
- **Regressão de navegação.** Trocar o estado do `App.tsx` por rotas (P5) toca o login e o
  fluxo do leiloeiro da 2.4; componentes não têm teste automatizado, então dependem do
  roteiro manual e do review.
- **"Cancelados não aparecem"** é vazio até a 3.6; se a 3.6 esquecer o filtro nas
  leituras públicas, lotes cancelados aparecerão (registro em `deferred-work.md`).

## Fechamento (regra de toda story)

Antes de `done`, confiro a coerência entre `docs/ARQUITETURA.md` (Q8; AD-22 se a P9
mexer), a spec e as decisões da 2.5, esta story, `docs/uso_de_ia.md`, `CLAUDE.md` (só o
resumo da questão 8), `epics.md` (só se um critério precisar de nota), `README.md` e
`deferred-work.md`. Preservo: decisão → motivo → alternativa descartada → evidência →
mudança → limitação/adiamento. Não altero AD para registrar detalhe local.

## Decisões fechadas (P1 a P9, D1 a D21)

Decidi tudo antes do código, com a spec em
`_bmad-output/specs/spec-story-2-5-vitrine-publica/` (`decisions.md` tem o detalhe de
cada uma). Registro aqui o que decidi e o que descartei. P1 a P9 foram aprovadas por mim
antes da spec e D3, D7, D13, D16 e D20 foram aprovadas explicitamente em 25/10/2026,
junto com o refinamento da P2.

| Questão | Decidi | Descartei |
| --- | --- | --- |
| P1 forma da vitrine | `GET /api/lots` → `{as_of, live, scheduled, ended}`, cada item com `phase`; `GET /api/lots/{lot_id}` → `{as_of, lot}` | lista plana agrupada no front; uma rota por grupo (três instantes para uma página) |
| P2 fase (refinada) | O back-end classifica com **um** `clock_timestamp()` por leitura, e `as_of` e as linhas saem do **mesmo statement** (`WITH clock AS MATERIALIZED … LEFT OUTER JOIN lots`); `lot_phase` pura recebe `now`; classificar e ordenar em Python | `CASE` no SQL; classificar no navegador; duas consultas independentes em `READ COMMITTED` (snapshots diferentes: um lote confirmado entre elas entraria numa resposta de `as_of` anterior à existência dele); `REPEATABLE READ` |
| P3 página aberta | A fase só muda num novo `GET`; sem countdown, polling, `setInterval` nem `Date.now()` de domínio | `GET` agendado para o próximo limite; polling |
| P4 ordem (D3) | ao vivo `ends_at ASC, id ASC`; agendados `starts_at ASC, id ASC`; encerrados `ends_at DESC, id ASC` | `id DESC` nos encerrados (UUID v4 não tem ordem temporal); `created_at DESC` |
| P5 navegação (D7, D8) | History API própria; `/`, `/lots/{uuid}`, `/login`, `/auctioneer/lots/new`, `/auctioneer/lots`; `returnTo` em `history.state`, validado contra as rotas conhecidas | React Router; estado em memória; `?next=` na URL |
| P6 DTO (D6) | `PublicLotSummary` e `PublicLotDetail` próprios; UUID inválido 422, inexistente 404 | reaproveitar `LotResponse`; DTO único; 404 para os dois |
| P7 sem paginação (D13) | A API devolve todos; no front, 6 encerrados iniciais e "Mostrar mais encerrados" de 6 em 6, sem nova chamada | paginação ou limite na API; 12 iniciais (dobra as miniaturas contra o limite da AIC) |
| P8 sem liquidação fake | Só `phase`; "Encerrado, apurando resultado" é cópia de interface para todo `ended`; resolve a Q8 | `settlement_status = pending`; campo único com `closing`/`closed` |
| P9 imagem | Estratégia da 2.3 intacta (proxy `no-store`, 843 px, sem cache novo); `loading="lazy"` no front | cache do navegador nos 200; segunda largura para miniaturas |
| D1 | Um statement por rota; o handler monta os DTOs e chama `session.rollback()` antes de responder (D2) | duas consultas; `commit` numa leitura |
| D4 | Ordem de registro: `POST /api/lots`, `GET /api/lots/mine`, `GET /api/lots`, `GET /api/lots/{lot_id}` | regex no parâmetro |
| D9, D10 | Anônimo em área do leiloeiro → `/login` com `returnTo`; `BIDDER` → "Área do leiloeiro"; "Sair" → `/`; `LotCreation` fica montado e oculto enquanto a sessão é `AUCTIONEER` | mandar o anônimo à vitrine; desmontar `LotCreation` |
| D11 | Um `h1` por vista com `tabIndex=-1`, focado só em navegação interna; no Back, o foco volta ao link do lote | só rolar ao topo |
| D12 | Destaque = `live[0]`, senão `scheduled[0]`, senão vazio editorial; o destaque não se repete no próprio rail | repetir o destaque no rail |
| D14 | Rails sem limite, `scroll-snap`, botões "Anterior"/"Próximo" só ≥ 64rem e só com overflow | grid que quebra linha; botões sempre visíveis |
| D16 | Linha "Situação atualizada às HH:mm" (ou "em DD/MM/AAAA às HH:mm") derivada do `as_of`, só apresentação | não exibir o `as_of`; relógio local |
| D20 | `policy_by_route` indexa por `(path, method, kind)`; chave repetida levanta `ValueError` | manter a chave e testar o POST à parte |
| D21 *(acrescentada em 25/10/2026, depois do teste manual; não estava na spec aprovada)* | Playwright (`@playwright/test` só em `devDependencies`, Chromium, API simulada) em `frontend/e2e/`, **opt-in** com `VERIFY_E2E=1 ./verify.sh`; `node --test` (D18) segue para lógica pura; `real-stack.spec.ts` só com `E2E_REAL_BASE_URL` | incluir o Playwright sempre no `verify` (browser como pré-requisito silencioso); só em CI; teste de componente com Testing Library |

**Tipo real do 422 de UUID inválido:** `uuid_parsing`, com `loc` `["path", "lot_id"]`
(conferido pelos testes; `abc`, `mine-x`, `123` e UUID truncado).

## Registro de implementação (25/10/2026)

Implementei a partir da spec final, sem git, sem deploy, sem migration e sem ler `.env*`.

**Back-end (`app/lots.py`).** `LotPhase` e `lot_phase`; `PublicLotSummary`,
`PublicLotDetail`, `PublicLotsResponse`, `PublicLotDetailResponse`; `_clock_cte`,
`public_snapshot_statement`, `read_public_snapshot`, `read_public_lot_snapshot`;
`public_lot_summary`, `public_lot_detail`, `build_public_lots`; as rotas `GET /api/lots`
e `GET /api/lots/{lot_id}` (`PUBLIC`, `no-store`), registradas depois de `/api/lots/mine`.
Nenhum outro módulo de produção mudou (`main.py`, `spa.py`, `catalog.py`, `seed.py`,
migrations e `access.py` intocados).

**SQL real emitido** (o SQLAlchemy 2.x emite o `MATERIALIZED` por `CTE.prefix_with`, como a
spec previa):

```sql
WITH clock AS MATERIALIZED (SELECT clock_timestamp() AS as_of)
SELECT clock.as_of, lots.id, lots.auctioneer_id, …, lots.created_at
FROM clock LEFT OUTER JOIN lots ON true
-- detalhe: … LEFT OUTER JOIN lots ON lots.id = %(id_1)s::UUID
```

**Front-end.** `route.ts`, `navigation.ts`, `AppLink.tsx`, `lotPhase.ts`, `vitrine.ts`,
`asOf.ts`, `lotLabels.ts`, `api/publicLots.ts`; `VitrinePage`, `FeaturedLot`, `LotRail`,
`LiveLotItem`, `UpcomingLotItem`, `ClosedLots`, `ClosedLotRow`, `LotState`, `LotPage`,
`LoginPage`, `NotFoundPage`; `App.tsx` e `SiteHeader.tsx` reescritos para as rotas;
`ArtworkImage` ganhou a variante `card`; `App.css` ganhou as seções da vitrine e do lote;
`main.tsx` define `scrollRestoration = 'manual'`. Sem dependência nova *na implementação original*; o Playwright (`devDependencies`) entrou depois do teste manual, pela D21.

### Verificação do que a spec afirmava

- **`main.py` e `spa.py` não precisam mudar:** conferido no código real. O fallback
  (`serve_spa`, registrado por último) devolve `index.html` a `/lots/<uuid>`, `/login` e
  `/auctioneer/lots[/new]` e recusa `/api` e `/health`. Fixei isso em `test_spa.py` e não
  alterei os dois arquivos.
- **Caminho `/api/lots/mine`:** continua `AUCTIONEER` (401, 403, 200 com os próprios) e
  vem antes de `/{lot_id}` em `app.routes` (teste).

### Divergências entre a spec e o código existente, e adaptações técnicas

- **`Vitrine.tsx` × `vitrine.ts`.** A spec previa os dois nomes; em sistema de arquivos
  sem distinção de maiúsculas (macOS) e para o `tsc` eles são o mesmo arquivo
  (`TS1149`/`TS1261`). Mantive `vitrine.ts` (lógica pura, como a spec e os testes) e
  chamei o componente de `VitrinePage.tsx`. Mudança só de nome.
- **Teste 1b.** A spec pedia que as 20 linhas cruas trouxessem um `as_of` "igual ao que
  `read_public_snapshot` devolveria". Duas execuções avaliam o relógio duas vezes, então
  a igualdade não existe; o teste afirma o que importa: um único valor distinto nas
  20 linhas de uma execução e `db_now(antes) <= as_of cru <= as_of da função <= db_now(depois)`.
- **Texto do statement.** O SQLAlchemy quebra linha depois de `MATERIALIZED`; os testes
  normalizam espaços antes de procurar `WITH clock AS MATERIALIZED`.
- **`CatalogSearch.tsx`.** A lista de intocados incluía este arquivo; acrescentei só
  `tabIndex={-1}` ao `h1` dele, para a regra de foco no `h1` valer também em "Criar lote"
  (D11). Nada mais mudou nele, nem em `LotCreation`, `MyLots`, `LoginForm`, `lotTime`,
  `money`, `lotDraft` ou `api/lots.ts`.
- **`navigate()` no mesmo caminho** troca a entrada (`replaceState`) em vez de empilhar
  uma igual; e a vitrine é remontada (`key`) a cada navegação, para cada visita fazer um
  `GET` novo (P3). Não estava escrito, é consequência das duas regras.
- **Nome acessível dos links** por `aria-label` (`lotLinkLabel`): título, estado e lance
  inicial; o encerrado não leva o valor, como a linha dele na tela.
- **`isAuctioneerRoute`** é um *type guard* (a spec dizia `boolean`), só para o
  `routePath` aceitar a rota já estreitada.
- **`source_url`** só vira link se começar com `https://` (defesa extra no front; o
  servidor já grava a URL fixa da AIC).
- **Testes antigos trocados por contrato novo** (nenhuma asserção afrouxada):
  `test_lot_creation.py` (`GET /api/lots` 405 → 200, `PUT`/`DELETE` seguem 405),
  `test_openapi.py` (`paths` ganha `/api/lots/{lot_id}`; `paths[-3:]`; `get` e `post` em
  `/api/lots`), `test_access_policy.py` e `test_catalog_image_route.py` (chaves de
  `policy_by_route` com o método).

### Evidências (comandos executados em 25/10/2026)

- `./verify.sh` completo, exit 0: Ruff check "All checks passed!"; `ruff format --check`
  "57 files already formatted"; **pytest: 1058 passed, 1 warning in 41.43s** (985 antes
  desta story; o aviso é a depreciação do `httpx` no `starlette.testclient`); ESLint e
  `tsc --noEmit` sem erro; **`npm test`: 84 testes, 84 passaram** (39 antes); build do Vite
  (56 módulos; CSS 20,06 kB, JS 279,21 kB); `docker build` ok; "verify.sh: todas as
  etapas passaram."
- Testes novos ou alterados do back-end: `test_lot_phase.py` 19, `test_public_lots.py` 40
  (PostgreSQL real), `test_access_policy.py` 27, `test_openapi.py` 23, `test_spa.py` 82.
- Testes novos do front: `route` 14, `lotPhase` 2, `vitrine` 11, `asOf` 6, `lotLabels` 4,
  `api/publicLots` 8.
- Mutação temporária (restaurada): um `SELECT … FOR UPDATE` no detalhe fez falhar 4 testes
  (statement único, 404, leitura pura e o do row lock).
- Renderização no servidor (script descartável, fora do repositório): `App` renderiza
  nas cinco rotas sem erro de importação, e `FeaturedLot`, `LotRail` e `ClosedLots`
  renderizam com títulos longos, `null` e o valor máximo, sem "Dar lance", "lance atual",
  "DEMO" nem campos internos. **Não é teste de navegador.**

### Não verificado (é meu) — versão da primeira rodada

> Atualizado pela rodada de 25/10/2026 (seção seguinte): parte disto passou a ter
> evidência automatizada do Playwright e parte foi observada por mim. Mantenho o texto
> original como registro do que faltava depois do primeiro build.

Nenhuma verificação em navegador foi feita: clique, `pushState`, Back/Forward, foco,
rails e botões, 320 px/375 px/desktop, teclado, imagem quebrada e o comportamento real do
Vite com deep-link. Também não executei smoke externo, deploy nem o roteiro com 50
encerrados. O roteiro está em `test-plan.md` §9 e resumido na resposta desta sessão.

### Riscos restantes

- Componentes sem teste unitário de DOM (Q10 da 2.4): depois da rodada de 25/10/2026, a
  navegação, o foco, o layout e a imagem quebrada têm testes de navegador (Chromium, API
  simulada); o visual de verdade segue dependendo do meu olhar e do code review.
- A resposta da vitrine cresce sem limite (P7) e cada imagem visível é uma chamada à AIC
  sem cache (P9): um 429 real pode mostrar placeholders; vira evidência, não mudança.
- Com a página aberta, "Ao vivo" pode ficar velho até o próximo `GET` (P3, deliberado).
- O fallback devolve 200 para qualquer caminho sem extensão (soft 404): a tela avisa.

## Rodada de 25/10/2026: teste manual, testes de navegador e densidade

O meu teste manual mostrou que a funcionalidade principal funciona e revelou duas
necessidades: testes de navegador (agora há justificativa real) e espaço morto nas seções
de coleção do desktop. A Story continua em `review`.

### Evidência manual do usuário (observada por mim)

Vitrine do `BIDDER` renderizando; detalhe do `BIDDER` renderizando; `BIDDER` sem os
controles do leiloeiro; vitrine anônima com "Entrar"; anônimo não forçado ao login;
`AUCTIONEER` com Vitrine, Criar lote e Meus lotes; criação da 2.4 e "Meus lotes" ainda
acessíveis; grupos Ao vivo, Próximos e Encerrados renderizando; detalhe com ficha,
valores e horários; sem botão "Dar lance"; "Situação atualizada" aparecendo; e o layout
desktop com espaço morto excessivo nas seções de coleção (refinado abaixo).

**Não observei manualmente:** 320 px, 375 px, teclado, Back/Forward, deep-link com
recarga, `returnTo`, placeholder, nem "Mostrar mais" com mais de 6 encerrados.

### Evidência automatizada Playwright (não é evidência manual)

`frontend/e2e/`, 66 testes em 5 arquivos (`npm run test:e2e`): `vitrine.spec.ts` 17,
`session.spec.ts` 12, `layout.spec.ts` 25, `keyboard.spec.ts` 7 e `real-stack.spec.ts` 5
(só com `E2E_REAL_BASE_URL`). Resultado: **61 passaram e 5 foram ignorados** no `verify`;
os 5 da pilha real passaram numa rodada à parte, contra o FastAPI servindo o build com o
banco de teste e o seed (5/5). Chromium apenas; API simulada por interceptação de rede,
sem tocar o banco de desenvolvimento nem a AIC.

| O que provam | Onde |
| --- | --- |
| `/` abre a vitrine sem login, com "Entrar", sem Criar lote nem Meus lotes; clicar num lote abre `/lots/{uuid}` | `vitrine.spec.ts` |
| Deep-link e recarga no lote; lote inexistente; `/lots/abc` sem chamar a API; nunca o catálogo da AIC | `vitrine.spec.ts` |
| Vitrine → detalhe → Back → vitrine → Forward → detalhe; "← Vitrine"; Ctrl+clique | `vitrine.spec.ts` |
| "Mostrar mais": 6 → 12 → 14, sem novo `GET /api/lots`; Back restaura os 12 e o foco | `vitrine.spec.ts` |
| Imagem quebrada: placeholder, título, estado e CTA continuam (vitrine e lote) | `vitrine.spec.ts` |
| Lote → Entrar → login → mesmo lote; Sair → `/`; `returnTo` externo ignorado; área do leiloeiro | `session.spec.ts` |
| Header do `BIDDER` e do `AUCTIONEER`; `aria-current`; sessão expirada | `session.spec.ts` |
| Sem rolagem horizontal, header dentro do viewport, hero em duas colunas (desktop) e empilhado (celular), rails legíveis, container centrado — em 1440×900, 375×812 e 320×812 | `layout.spec.ts` |
| Tab alcança os controles na ordem, com contorno visível; foco no `h1` ao navegar e não no primeiro carregamento; Back devolve o foco | `keyboard.spec.ts` |
| `/api/*` nunca cai no fallback da SPA; rotas públicas reais respondem JSON | `real-stack.spec.ts` |

Isto mostra o comportamento no Chromium com dados controlados; **não substitui** o meu
olhar sobre o visual (imagens reais, tipografia, respiro) nas três larguras.

**Decisão sobre o `./verify.sh`.** Não incluí o Playwright no `verify` padrão, e a decisão
é explícita, não silenciosa: ele exige o Chromium do Playwright (~100 MB, baixado por
`npx playwright install chromium`) e sobe um servidor, enquanto o `verify` hoje só pede
Docker e Node. Mantive `npm test` para a lógica pura, `npm run test:e2e` separado, e um
gancho **opt-in**: `VERIFY_E2E=1 ./verify.sh`. Descartei incluí-lo sempre (quebraria o
`verify` de quem não baixou o browser) e rodá-lo em CI sem browser instalado.

### Ajuste de densidade da vitrine (desktop)

Só nas coleções; hero, detalhe, header e a lista de encerrados não foram redesenhados
(na lista, só alarguei a coluna de estado para "BRT" não quebrar em terceira linha). O
RockHub foi referência de densidade, não de identidade; o blueprint (§6, §7, §9) não
proíbe nada disto, e a hierarquia (ao vivo > próximos > encerrados) foi mantida.

- **Ao vivo:** cartões maiores e dimensionados pela quantidade de itens do rail
  (`rail-n-1` a `rail-n-4`, com 4 = quatro ou mais): três itens ocupam as três colunas; dois dividem
  a faixa (cartão horizontal no desktop); com quatro ou mais o rail volta a rolar com parte
  do próximo à mostra (29% de largura, antes 23%).
- **Próximos lotes:** um item sozinho vira um cartão largo e horizontal (obra à esquerda,
  ficha à direita, até 46 rem), em vez de um cartão pequeno e isolado; vários itens seguem
  como rail (21%, antes 19%).
- **Espaço vertical:** gap entre seções de 2,5 para 2 rem e cabeçalho de seção mais
  justo; hero intacto.
- **Prova:** com o CSS antigo, os testes de densidade falham (rail de 3 itens ocupa 72%
  da faixa, de 2 itens 47%, próximo lote sozinho 24% da largura); com o novo passam
  (mutação temporária, restaurada). Screenshots foram usados só como artefato de
  depuração e ficaram fora do repositório.

### Verificação (25/10/2026)

`VERIFY_E2E=1 ./verify.sh`, exit 0: Ruff check e format, **pytest 1058 passed** (igual à
primeira rodada: nenhum código de back-end mudou), ESLint, `tsc` (agora também o `tsconfig`
de `e2e/`), **`npm test` 84 de 84**, build do Vite, **Playwright 61 passed e 5 skipped** e
`docker build`. Sem git, sem deploy e sem smoke externo.

## Rodada de 25/10/2026: rebranding ÁTRIO

Última rodada antes do code review. **Decidi** que o produto passa a se chamar **ÁTRIO —
Leilões de Arte** (nome de trabalho anterior: "Casa de Leilões"), com a identidade da
referência ÁTRIO que escolhi; a AURA fica só como inspiração complementar de densidade,
cards, hierarquia e acabamento. É mudança de **marca e direção visual**, não de escopo
funcional. A Story continua em `review`; `sprint-status` continua `review`.

**O que mudou na interface:** `brand.ts` (nome, descritor e `documentTitle`, sem
duplicar `ÁTRIO` quando a página já é o produto); `AtrioMark.tsx` (símbolo SVG inline,
decorativo); `public/favicon.svg` (antes era o ícone padrão do template do Vite);
header, títulos da aba (`Vitrine — ÁTRIO`, `{título} — ÁTRIO`, `Entrar — ÁTRIO`, `Criar
lote — ÁTRIO`, `Meus lotes — ÁTRIO`, `Página não encontrada — ÁTRIO`, `Lote — ÁTRIO`),
`index.html` (`ÁTRIO — Leilões de Arte` antes do JavaScript), texto do "não encontrado" e
o `title` do OpenAPI (`/docs`). **Não mudou:** repositório, bancos, tabela `lots`,
módulos, `/api/*`, migrations, rotas do front, vitrine, detalhe e navegação.

**Marca (primeira interpretação vetorial, não arte final; o símbolo foi refeito logo depois, ver "Correções do primeiro review"):** arco semicircular roxo com
uma abertura interna mais clara (lia como portal, mas parecia uma ferradura genérica), mais a palavra "ÁTRIO" como texto real
em fonte de UI, peso 500 e espaçamento largo. Descartei serifa na palavra (a referência
usa sans leve e espaçada; a serifa fica para obras e valores) e descartei o `<img>` do
favicon no header (o SVG inline é decorativo e não duplica o nome para o leitor de tela).
O link da marca se chamava "ÁTRIO — ir para a vitrine" (hoje "ÁTRIO — Leilões de Arte — ir para a vitrine"). "Leilões de Arte" só aparece a
partir de 64 rem; em 375 e 320 px ficam símbolo e nome, e nenhuma navegação sumiu.
Descartei mostrar o descritor também no tablet: apertaria o header do leiloeiro.

**Não antecipei** lance, contagem regressiva, favoritos, compartilhar, busca, filtros,
artistas, "Como funciona", criação de conta, carteira nem histórico, mesmo aparecendo nas
referências.

**Testes:** `brand.test.ts` (3, `node --test`) e `e2e/brand.spec.ts` (17: títulos por
rota, HTML inicial sem o nome antigo, favicon SVG local sem raster nem URL remota, nome
acessível único com SVG `aria-hidden`, e header em 1440, 375 e 320 px para anônimo,
`AUCTIONEER` e `BIDDER`, sem sobreposição nem rolagem horizontal). O único teste antigo
que dependia do nome (`keyboard.spec.ts`, nome do link da marca) foi atualizado; o
`test_openapi.py` passou a esperar o novo título. Nenhum teste foi afrouxado.

**Verificação (25/10/2026):** `VERIFY_E2E=1 ./verify.sh`, exit 0: Ruff check e format,
**pytest 1058 passed**, ESLint, `tsc` (app, node e e2e), **`npm test` 87 de 87**, build do
Vite, **Playwright 78 passed e 5 skipped** (os 5 da pilha real só com
`E2E_REAL_BASE_URL`; não fazem parte do `verify` normal) e `docker build`. Sem git, sem
deploy e sem smoke externo.

**Evidência:** a evidência manual registrada acima continua sendo a do teste anterior, com
o nome e o visual antigos; **não a reclassifico como ÁTRIO**. Esta rodada ainda **não foi
vista por mim no navegador**; o que há dela é evidência automatizada do Playwright
(Chromium, API simulada) e screenshots do header que a IA gerou e olhou (três deles) só como
depuração, fora do repositório e sem assert.

## Review Findings (primeiro code review, 25/10/2026)

Opus, sessão separada da implementação, sem git e sem correções. Os cinco revisores
paralelos pararam por limite de API (429) antes de relatar; o review foi feito inteiro
pela sessão principal (não houve review multiagente). `VERIFY_E2E=1 ./verify.sh` rodado
pelo reviewer: exit 0; pytest 1058 passed; `npm test` 84/84; Playwright 61 passed e 5
skipped (os 5 da pilha real não fazem parte deste comando); ESLint, `tsc`, build e
`docker build` ok. 0 BLOCKER, 0 HIGH, 1 MEDIUM, 4 LOW. Status mantido em `review`.

- [x] [Review][Decision] M1 *(corrigido em 25/10/2026, opção (a); ver "Correções do primeiro review")* — Playwright e `verify` opt-in fora da spec canônica, do
  `ARQUITETURA.md` e do `CLAUDE.md` — a spec (que a própria story declara prevalecente)
  ainda diz "ferramenta de teste nova no front" como non-goal (`SPEC.md:107`), D18 "só
  `node --test`" e D19/`implementation-map.md` com `package.json`, `verify.sh` e
  `.dockerignore` intocados; o AD-27 diz que o `verify` roda os "testes automatizados
  existentes" e a Q10 (ARQUITETURA e CLAUDE.md) só cita `node --test`; nenhum dos três
  menciona Playwright nem `VERIFY_E2E`. A story também tem linhas velhas ("Sem dependência
  nova", `package.json` em "Sem mudança"). Opções: (a) registrar na Q10 e no histórico do
  ARQUITETURA que o `verify` padrão cobre pytest + `node --test` e que o Playwright é
  opt-in, sem alterar AD; (b) alterar antes o texto do AD-27. Em ambas: adendo na spec
  (D21), D18/D19/non-goals/mapa, CLAUDE.md Q10 e as linhas velhas da story. Recomendo (a).
- [x] [Review][Patch] L1 *(corrigido; ver abaixo)* — Contorno de foco dos itens do rail cortado pelo
  `overflow-x: auto` (borda de cima sempre; a esquerda no primeiro item)
  [frontend/src/App.css:1255] — inferido do CSS, não reproduzido; o teste de teclado
  confere só o estilo computado (`keyboard.spec.ts:53`).
- [x] [Review][Patch] L2 *(corrigido; ver abaixo)* — O e2e de `returnTo` externo não tem controle positivo: se o
  `history.state` não sobrevivesse ao reload, passaria do mesmo jeito
  [frontend/e2e/session.spec.ts:75].
- [x] [Review][Patch] L3 *(corrigido; ver abaixo)* — Alvos de toque pequenos no header (itens de navegação, ~30 px
  de altura) e em "← Vitrine" no celular; atendem 24 px (WCAG 2.2 AA), não 44 px
  [frontend/src/App.css:574].
- [x] [Review][Patch] L4 *(registrado; ver abaixo)* — Falta registrar se o teste manual viu 429/503 na rota de imagem
  (P9 e D1 da 2.3 pedem a evidência, observada ou não)
  [_bmad-output/implementation-artifacts/deferred-work.md:33].

**Rejeitados:** `reuseExistingServer` do Playwright fora de CI (um servidor velho na 4173
quebraria os testes, não daria falso positivo; improvável); envelope do mock de
`/api/lots/mine` anônimo com `status` 403 num 401 (o front só lê o status HTTP); efeito do
`LotRail` refeito a cada render do pai (sem laço nem efeito visível); 401 em `/api/me` e
pedidos abortados (comportamento esperado: anônimo recebe 401 por desenho da 2.2; o
`AbortController` da vitrine e do lote, o `StrictMode` em desenvolvimento e o
cancelamento de imagens ao navegar explicam os 0 B; nenhum laço de pedidos).

## Correções do primeiro review e sincronização do branding (25/10/2026)

**O primeiro review não validou o branding.** Ele rodou sobre uma versão anterior ao ÁTRIO
(`npm test` 84 e Playwright 61 passados, contra 87 e 78 depois do branding) e antes da
correção de fidelidade do símbolo. Aproveitei M1 e L1 a L4; o delta ÁTRIO (marca, símbolo,
títulos, nome acessível, alvos de toque) **precisa ser examinado num re-review**. Esta
seção preserva a seção do review acima como foi escrita.

- **M1 (opção (a), aprovada por mim; AD-27 não foi alterado).** Registrei na Q10 e no
  histórico do `ARQUITETURA.md`, e no `CLAUDE.md`, que o `verify` padrão cobre `pytest`,
  Ruff, `node --test`, ESLint, `tsc`, build e `docker build`, e que o Playwright é camada
  de navegador **opt-in** (`VERIFY_E2E=1 ./verify.sh`), porque exige o Chromium instalado.
  Na spec, acrescentei a **D21** e anotei (sem apagar) o que ficou velho: `SPEC.md`
  (non-goal de ferramenta nova e linha de "sem dependência nova"), D18, D19,
  `implementation-map.md`, `frontend-navigation.md` e `test-plan.md`. Nesta story corrigi
  as linhas vigentes ("Sem mudança", "Sem dependência nova", fora de escopo) e a tabela de
  decisões. A spec original continua sendo a que aprovei **antes** do Playwright; a D21
  diz isso e não finge o contrário.
- **L1 (foco cortado no rail), reproduzido no navegador.** O contorno do primeiro item
  ficava **6 px cortado no topo e à esquerda** em 320, 375 e 1440 px (2 px de contorno + 4
  px de `outline-offset`, dentro de um `overflow-x: auto` que também corta na vertical).
  Corrigi com `padding: 0.5rem` no `.rail`, margem negativa de mesmo valor (a posição na
  tela não muda) e `scroll-padding-inline: 0.5rem` (o `scroll-snap` segue alinhado). O
  foco não foi removido. Os testes de `keyboard.spec.ts` passaram a medir se o contorno
  cabe nas quatro bordas do rail, no primeiro e no último item, nos rails "ao vivo" e
  "próximos"; falhavam antes do CSS e passam depois. A densidade (layout.spec) não mudou.
- **L2 (`returnTo` após reload).** Novo teste positivo em `session.spec.ts`: `history.state`
  com `returnTo = /lots/{id}`, reload em `/login`, login → volta ao lote, com uma
  asserção de controle de que o estado sobreviveu ao reload. O teste do `returnTo`
  externo ganhou o mesmo controle: o estado adulterado também sobrevive, então quem
  barra o destino é a validação (`safeReturnPath`), não a perda do estado.
- **L3 (alvos de toque).** Marca, itens da navegação, "Entrar", "Sair" e "← Vitrine"
  medem agora ~44 px de área acionável (antes: 32, 32,5, 36,5 e 18 px). A área extra é um
  pseudo-elemento transparente do próprio link/botão, sem mudar fonte nem caixa visual.
  O espaço entre linhas do header subiu de 0.5 para 0.75rem para as áreas vizinhas não se
  sobreporem: o header no desktop segue com 61,5 px; no celular cresceu 8 px (375 px: 142
  → 150; 320 px: 168,5 → 176,5, leiloeiro). Descartei aumentar o padding real (subiria o
  header e deslocaria o sublinhado do item atual). `touch-targets.spec.ts` mede o que o
  toque acerta (`elementFromPoint`) em 1440, 375 e 320 e confere que não há overflow.
- **L4 (429/503), registro exato.** **Story 2.5, teste manual:** *não* observei novo 429 da
  AIC e *não* observei novo 503 de imagem especificamente nesta rodada manual.
  **Evidência histórica (Story 2.3):** já houve observação manual de resposta 503 de imagem,
  e o placeholder funcionou. Não converto a evidência da 2.3 em evidência manual da 2.5; a
  P9 e a D1 da 2.3 continuam sem mudança de estratégia.
- **Nome acessível da marca (Label in Name).** O link da marca contém o texto visível
  "ÁTRIO" e, no desktop, "Leilões de Arte". O `aria-label` anterior ("ÁTRIO — ir para a
  vitrine") não continha o descritor visível. Passou a ser **"ÁTRIO — Leilões de Arte — ir
  para a vitrine"**: começa pelo texto visível e só acrescenta o destino, em qualquer
  largura (no celular, onde o descritor está oculto, o nome só é mais longo que o visível,
  o que é permitido). Descartei remover o `aria-label` e deixar o nome sair do conteúdo:
  o nome variaria com o descritor oculto por CSS. Teste: o texto visível do link
  (`innerText`) está contido no nome em 1440, 375 e 320.
- **Símbolo (correção de fidelidade, antes desta rodada).** A primeira versão era um arco
  semicircular simétrico (∩), o que não corresponde à referência. A atual tem silhueta alta
  e fina de **topo pontudo**, **duas faces** (esquerda lilás `#a77bf6`, direita violeta
  `#6c35e6`, divididas na vertical a partir do ápice) e **abertura interna assimétrica**
  (parede esquerda vertical, topo arredondado, lado direito em diagonal); só `path`, sem
  gradiente. `favicon.svg` repete os mesmos caminhos e cores (um teste compara os dois).
  O wordmark "ÁTRIO" ficou mais leve (`font-weight: 300`, espaçamento `0.18em`) e o
  descritor "Leilões de Arte" menor e regular, na cor `--color-muted` (não usei cinza mais
  claro: baixaria o contraste do texto de 11 px abaixo de AA). Sem fonte externa.
- **Verificação (25/10/2026, base pós-branding e pós-correções):** `VERIFY_E2E=1
  ./verify.sh`, exit 0: Ruff check e format, **pytest 1058 passed**, ESLint, `tsc` (app, node
  e e2e), **`npm test` 87 de 87**, build do Vite, **Playwright 96 passed e 5 skipped** (101
  testes em 7 arquivos; os 5 ignorados são a pilha real, que só roda com
  `E2E_REAL_BASE_URL` e **não** faz parte do `verify` padrão nem do `VERIFY_E2E=1`) e
  `docker build`. São 18 testes de navegador a mais que os 78 do início do branding:
  contorno do rail (2), `returnTo` positivo (1), alvos de toque (12) e símbolo/nome
  acessível (3). Sem git, sem deploy e sem smoke externo. Os números do review (84 e 61)
  são da base anterior e não valem mais.

## Re-review final (25/10/2026)

Opus, sessão separada da implementação, sem git, sem deploy e sem corrigir findings. Escopo:
M1 e L1 a L4, regressões das correções, **todo o delta ÁTRIO** (que o primeiro review não
cobriu) e a sincronização documental. O back-end de domínio não mudou desde o primeiro review
(só o `title` do OpenAPI e o teste dele) e não foi revisto de novo. **0 BLOCKER, 0 HIGH,
0 MEDIUM.**

**Verify rodado pelo reviewer:** `VERIFY_E2E=1 ./verify.sh`, exit 0: Ruff check "All checks
passed!"; `ruff format --check` "57 files already formatted"; **pytest 1058 passed, 1 warning**;
ESLint; `tsc` (app, node e e2e); **`npm test` 87/87**; build do Vite (58 módulos); **Playwright
96 passed e 5 skipped** (101 testes; os 5 são `real-stack.spec.ts`, só com
`E2E_REAL_BASE_URL`); `docker build` ok.

**Sonda descartável no navegador** (script fora do repositório, `vite preview` do build, API
simulada; não é teste do projeto), para o que os testes não medem diretamente:

- **L3:** em 1440, 375 e 320 px, para anônimo, `BIDDER` e `AUCTIONEER`, nenhum ponto da caixa
  visual de um alvo (nem de e-mail, papel, destaque, título e imagem do lote) é capturado pela
  área estendida de outro alvo (0 invasões). Área acionável real: marca 48–51 px, navegação,
  "Entrar" e "Sair" 43 px (visual 33–37), "← Vitrine" 44 px (visual 18). Um clique real 8 px
  acima da caixa visual de "← Vitrine" navegou para `/` nas três larguras: o pseudo-elemento
  aumenta a área de clique de fato. Sem rolagem horizontal.
- **L1:** em 1440, 375 e 320 px, nos rails "ao vivo" e "próximos", primeiro e último item
  focados, o contorno (6 px) tem 2 px de folga em todas as bordas do rail. Sem rolagem
  horizontal.

**Validação dos achados do primeiro review:**

- **M1:** ok. AD-27 intacto; Q10 e histórico do `ARQUITETURA.md`, `CLAUDE.md` e README
  separam o `verify` padrão do Playwright opt-in (`VERIFY_E2E=1`) e os 5 testes da pilha real;
  D21 na spec, D18/D19, non-goal, `implementation-map.md`, `frontend-navigation.md` e
  `test-plan.md` anotados sem apagar o texto original; esta story não afirma mais "Sem
  dependência nova" como estado vigente.
- **L1:** ok (CSS e sonda acima). Os testes medem o contorno contra a caixa do rail, não só a
  largura do contorno.
- **L2:** ok. O teste positivo tem controle de que o `history.state` sobrevive ao reload e
  terminaria em `/` se não sobrevivesse; o negativo tem o mesmo controle. `safeReturnPath` é
  lista fechada: só devolve `routePath` de uma rota conhecida (URL absoluta, `//host`,
  `/\host`, query, `/login` e área do leiloeiro para `BIDDER` viram `/`; forma codificada não
  casa com o UUID). Sem open redirect.
- **L3:** ok (sonda acima). `touch-targets.spec.ts` mede com `elementFromPoint`, ou seja, a
  área que o toque realmente acerta.
- **L4:** ok. Story, `deferred-work.md` e P9 separam: nenhum 429/503 manual novo na 2.5; o
  503 manual com placeholder é da 2.3.

**Delta ÁTRIO:** sem bug. Nenhuma ocorrência de "Casa de Leilões" na interface, no
`index.html`, no favicon nem no OpenAPI (só a constante `OLD_NAME` do teste); nomes técnicos
intactos (AD-30). `AtrioMark` e `favicon.svg` usam os mesmos dois `path` e as mesmas cores
(muda só o `viewBox`, quadrado no favicon), e o teste que compara os dois falharia em caso de
divergência. SVG `aria-hidden`/`focusable="false"`, sem `title` no DOM; o nome acessível
contém o texto visível em 1440, 375 e 320; o descritor (`--color-muted` sobre o fundo, cerca de
4,8:1) só aparece a partir de 64rem; `documentTitle` em todas as rotas, com "Lote — ÁTRIO" no
carregamento e nos erros do detalhe.

**LOWs restantes (não corrigidos; nenhum bloqueia):**

- [ ] [Re-review][Low] `brand.spec.ts` confere o título com `expect(await page.title())`, que não
  tenta de novo, logo depois de uma asserção de DOM; o título é gravado num `useEffect`, então
  existe uma janela teórica de flakiness. `await expect(page).toHaveTitle(...)` fecharia a
  janela.
- [ ] [Re-review][Low] Os testes do contorno do rail (`keyboard.spec.ts`) rodam só no viewport
  padrão (1280×720); 375 e 320 px não têm teste. A regra de CSS não depende de media query, e a
  sonda confirmou a folga.
- [ ] [Re-review][Low] `touch-targets.spec.ts` não tem asserção explícita de que uma área não
  invade outra (a sonda confirmou zero invasões); a área real é de 43 px, coberta pelo "~44 px"
  da documentação e pela tolerância do teste.
- [ ] [Re-review][Low] Texto: o adendo da AD-15 ("símbolo próprio em forma de arco/portal") e o
  `deferred-work.md` ("proporções do arco") podem ser lidos como o arco semicircular rejeitado;
  o `DESIGN.md` §2 descreve o símbolo atual com precisão.
- [ ] [Re-review][Low/nit] O ramo de `documentTitle` que evita repetir o nome nunca é usado pelo
  app; uma obra chamada exatamente "ÁTRIO" teria a aba "ÁTRIO".

## Registro e status

Status: **done** (25/10/2026, depois do re-review final acima). Story criada em 25/10/2026;
spec aprovada e implementada no mesmo dia; teste manual meu (evidência registrada na rodada de
teste manual, com o visual anterior ao ÁTRIO), primeiro `bmad-code-review`, correções de M1 e
L1 a L4, rebranding ÁTRIO com a logo corrigida e re-review final sem BLOCKER, HIGH ou MEDIUM.
O commit é meu; não houve deploy.
