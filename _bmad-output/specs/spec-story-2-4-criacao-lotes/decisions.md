# Decisões — Story 2.4

P1 a P9 foram aprovadas pelo Joaodionizio antes desta spec e **não são reabertas**.
D1 a D14 detalham essas aprovações sem criar regra de produto. Na aprovação final da
spec, o Joaodionizio aprovou a Q1 e impôs os ajustes A2 a A4 (§3); onde um ajuste
revisa um item anterior, o item diz isso. Nenhuma questão aberta. Na implementação,
cada item vai para a story em primeira pessoa, com a alternativa descartada.

## 1. Decisões aprovadas (P1 a P9)

### P1 — Fonte autoritativa do snapshot
- **Decisão.** O front envia só `external_id` e os termos do lote. O back-end chama
  `catalog.get_artwork(client, external_id)` (2.3), exige `LookupStatus.FOUND` e grava
  o `ArtworkDetail` que ele mesmo obteve. Título `null` é aceito (sub-ponto da story).
- **Motivo.** Com sessão de leiloeiro, editar o corpo no DevTools não pode virar
  snapshot oficial; o AD-23 passa a ser garantia do servidor, reconferida na hora da
  criação.
- **Alternativas descartadas.** (a) front envia os metadados e o servidor só valida
  tipos: AD-23 vira promessa da interface. (c) híbrido com 409 se o `image_id` mudou:
  mais um código e um estado para um caso raro.
- **Consequências.** O `POST` depende da AIC (até ~8 s no pior caso, uma requisição da
  cota de 60/min); AIC fora → 503 sem lote; depois de criado, nada do lote depende da
  AIC. O que o leiloeiro viu e o que foi gravado podem diferir se a AIC mudar a obra
  entre o detalhe e o envio; a confirmação mostra o que foi gravado.

### P2 — Campos do snapshot
- **Decisão.** Gravar os 11 campos de `ArtworkDetail` sem `image_url`: `external_id`,
  `title`, `artist_display`, `date_display`, `medium_display`, `dimensions`,
  `department_title`, `artwork_type_title`, `image_id`, `credit_line`, `source_url`.
- **Motivo.** `image_id` é o identificador IIIF ("referência IIIF" do AD-23) e a URL
  same-origin é derivável por `image_url_for`; não gravar o derivável mantém uma regra
  só de montagem.
- **Alternativas descartadas.** Coluna `iiif_image_url` (dado morto, obsoleto se a base
  mudar); gravar `image_url` (acopla o banco a uma rota nossa).
- **Consequências.** `is_public_domain` não é gravado: todo lote existente veio de obra
  elegível. Bytes de imagem nunca entram no banco.

### P3 — Estado do lote
- **Decisão.** Sem coluna `status`. Fase derivada de `starts_at`, `ends_at` e da hora
  do banco. Marcos não temporais nascem como colunas aditivas nas stories que os usam.
- **Motivo.** Estado persistido envelhece e, pelo AD-19, nenhuma leitura pode corrigi-lo.
- **Alternativas descartadas.** `status` com o ciclo completo atualizado por job;
  `status` não temporal com um único valor agora.
- **Consequências.** A 3.6 e a 4.3 garantem por CHECK a exclusão entre cancelado e
  liquidado. Nenhum `UPDATE` de esquema desmonta o que nasce aqui (`database-schema.md` §5).

### P4 — Horários
- **Decisão.** `starts_at` opcional: ausente/`null` = `now` do banco; presente = precisa
  de fuso, ser válido e `> now`. `ends_at` obrigatório, com fuso, `> início efetivo`.
  Sem duração mínima, sem horizonte máximo.
- **Motivo.** "Agora" é sempre a hora do banco (AD-6): o navegador nunca é a autoridade.
  (Revisão de 25/10/2026: a tela compara com `new Date()` só como validação preventiva de
  UX, sem valor de domínio; ver `frontend-lot-creation.md` §5.) Nenhuma regra além das ADs
  e do enunciado.
- **Alternativas descartadas.** `starts_at` obrigatório e livre (aceita passado, "agora"
  do navegador); duração mínima de 5 min e horizonte de 30 dias (regras de produto não
  pedidas).
- **Consequências.** Lote de 1 s é aceito e já nasce na janela de anti-sniping (README).
  Formato e códigos em D2, D4, D5.

### P5 — Dinheiro
- **Decisão.** `starting_bid_cents` e `min_increment_cents`, `BIGINT NOT NULL` com CHECK
  `> 0`; API em inteiros de centavos (`StrictInt`); front digita reais e converte por
  texto. Sem teto comercial.
- **Motivo.** AD-3; exatidão explicável.
- **Alternativas descartadas.** Teto de R$ 100.000.000,00 em CHECK (regra minha, não
  pedida); `<input type="number">` (vira `float` e depende da localidade); campo em
  centavos na interface.
- **Consequências.** Limite técnico (não comercial) em D3, sincronizado no banco pelo
  A4; parser em D13, com teste automatizado pela Q1; os nomes valem para 3.2/3.4 e o
  conversor para 3.1/3.5.

### P6 — Obra inelegível
- **Decisão.** Um só código, 422 `artwork_not_eligible`, para inexistente, fora do
  domínio público ou sem imagem. AIC indisponível → 503 `catalog_unavailable`.
- **Motivo.** Preserva o encapsulamento da 2.3 (o `LookupStatus` continua interno).
- **Alternativas descartadas.** Três códigos por motivo; 404 para obra inexistente.
- **Consequências.** O motivo interno vai só ao log (`reason=NOT_PUBLIC_DOMAIN` etc.) e
  aos testes do serviço; a mensagem da interface cita os critérios sem dizer qual falhou.

### P7 — Duplo envio e vários lotes da mesma obra
- **Decisão.** Sem `Idempotency-Key`. O front bloqueia novo envio enquanto há um pendente.
  A mesma obra pode originar vários lotes; sem `UNIQUE` em `external_id`.
- **Motivo.** Menor solução explicável; uma obra pode legitimamente voltar a leilão.
- **Alternativas descartadas.** Chave de idempotência com tabela; 409 para obra já em
  lote aberto (regra não pedida, exigiria trava consultiva).
- **Consequências.** Timeout depois do commit seguido de nova tentativa manual pode criar
  dois lotes; o front, em erro de rede, manda conferir "Meus lotes" antes de repetir
  (README, "Comportamentos que podem surpreender").

### P8 — Seed do lote demo
- **Decisão.** Fixture JSON versionada em `backend/app/seed_data/`, obra 27992, sem AIC;
  idempotente; nunca altera nem apaga demo antigo; `is_demo`; "demo aberto" =
  `is_demo = true AND ends_at > now`; existe aberto → não cria; senão cria. Início agora,
  72 h, R$ 100,00 (`10000`) e R$ 10,00 (`1000`). `pg_advisory_xact_lock` contra seeds
  concorrentes.
- **Motivo.** AD-24; a imagem de produção não contém `backend/tests`.
- **Fronteira (A3).** O seed compartilha `create_lot` com a criação manual e nunca
  `resolve_artwork_for_lot`, `catalog.get_artwork`, `ArticClient` ou `httpx`.
- **Alternativas descartadas.** Constantes Python com os dados da obra; reaproveitar a
  fixture de teste pelo parser da AIC (não chega à imagem e acopla o boot ao parser).
- **Consequências.** Q4 resolvida em parte (ordem migrations → seed → servidor; o
  catch-up da 4.4 entra antes do seed; a 3.6 acrescenta "e não cancelado"). Detalhe em
  `seed-plan.md`.

### P9 — Meus lotes
- **Decisão.** `GET /api/lots/mine`, `AccessPolicy.AUCTIONEER`, só `auctioneer_id` da
  sessão, sem parâmetro de dono, sem AIC. Depois de criar: confirmação e lista refeita.
  Sem React Router. Da opção (a) da story: lista densa sem coluna de estado, sem ações,
  sem paginação, mais recente primeiro (`created_at DESC, id DESC`). **Revisado pelo
  A2:** todos os lotes do dono, sem limite (o "até 100" da story foi retirado).
- **Motivo.** Critério do `epics.md` ("aparece na lista dos meus lotes no painel").
- **Alternativas descartadas.** `/api/me/lots` (proposta da story); seção na mesma página
  da busca; React Router agora.
- **Consequências.** A 2.5 registra `/api/lots/{lot_id}` **depois** de `/api/lots/mine`
  (senão "mine" cai no parâmetro). A 2.5/4.5 acrescentam estado e resultado.

## 2. Decisões de detalhamento (D1 a D14)

Cada uma resolve um "a spec deve definir" do pedido, dentro de P1 a P9.

| ID | Decisão | Alternativa descartada | Origem |
| --- | --- | --- | --- |
| D1 | Fronteira: o handler guarda `user.id`, faz `session.rollback()` (encerra a leitura da autenticação e devolve a conexão) **antes** da AIC; a transação de escrita só abre depois: `clock_timestamp()` → regras → `INSERT` → `commit`. | Chamar a AIC com a transação da autenticação aberta; abrir a escrita antes da AIC. | P1, CA8 |
| D2 | Hora na API: string ISO 8601 `YYYY-MM-DDTHH:MM[:SS[.ffffff]](Z\|±HH:MM)` verificada por regex antes do `AwareDatetime`; número, timestamp Unix, data sem hora e espaço no lugar do `T` → 422 `datetime_format`; sem offset → `timezone_aware`; normalizo para UTC; respostas em UTC com `Z`. | `AwareDatetime` puro (o Pydantic aceita número como timestamp Unix). | P4 |
| D3 | Dinheiro: faixa técnica única `1..9007199254740991` (`Number.MAX_SAFE_INTEGER`), o que o consumidor JavaScript representa sem perda; não é regra comercial. API e serviço: `StrictInt`, `gt=0`, `le=MAX_CENTS`. **Revisado pelo A4:** o banco também impõe a faixa por CHECK. | Teto comercial de R$ 100 mi (recusado na P5); sem limite (o front perderia precisão acima de 2^53); limite só na API (versão anterior desta spec, trocada pelo A4). | P5, A4 |
| D4 | `details.type` próprios: `ends_at_not_after_start` (`loc ["body","ends_at"]`, com ou sem `starts_at`), `starts_at_not_in_future` (`loc ["body","starts_at"]`), `datetime_format`. O resto é o `type` do Pydantic. | Um código de erro por regra; tipos separados para "fim antes do agendado" e "fim antes de agora". | P4, P6, 2.1 |
| D5 | Precedência: proteção 2.1 (403/415) → 401 → 403 → 422 do corpo → 422 `ends_at_not_after_start` quando ambos vieram (sem AIC) → AIC (503 / 422 `artwork_not_eligible`) → 422 das regras com `now` → 201. | Validar `starts_at` no passado antes da AIC (exigiria um segundo instante, contra AD-6). | AD-6, CA8 |
| D6 | DTO único `LotResponse` no 201 e em cada item de `MyLotsResponse`; sem `is_demo` e sem `auctioneer_id`; `image_url` derivada; `no-store`. | DTO separado para lista e criação; devolver `is_demo`. | P2, P9 |
| D7 | CHECKs: lance e incremento em `> 0 AND <= 9007199254740991` (A4), `ends_at > starts_at`, `external_id > 0`, `image_id` no regex da 2.3 (espelham validações já existentes; nenhuma regra nova). Índice em `auctioneer_id`. Sem default de `id` e `created_at` no banco. | Teto comercial em CHECK; índice composto; default `now()` em `created_at` (segundo relógio). | P3, P5, A4, AD-6 |
| D8 | Seed: uma transação; `pg_advisory_xact_lock(7161131744880846180)` (bytes ASCII de `casaseed`) → `seed_users` → `now` → demo aberto? → `create_lot`. `READ COMMITTED` obrigatório. | `pg_try_advisory_lock` com desistência; trava de sessão; `SELECT ... FOR UPDATE` (não há linha para travar). | P8 |
| D9 | Fixture `backend/app/seed_data/demo_artwork.json` só com os 11 campos do snapshot; termos do demo como constantes em `seed.py`; a fixture passa pelo mesmo `ArtworkSnapshot` da criação manual. | Termos na fixture; fixture no formato da AIC. | P8 |
| D10 | A fase temporal **não aparece** em nenhuma resposta nem na tela desta story (story P9 a); a definição única fica em `backend-contract.md` §7 e o único uso executável é o predicado do demo aberto. | `phase` calculada no back-end já agora (anteciparia a Q8 da 2.5); cálculo no front (dois relógios). | P3, P9 |
| D11 | `clean_users` passa a `TRUNCATE lots, users` (um comando, sem `CASCADE`); novo `clean_lots`. Adaptação ao FK, não mudança da 2.2. | `TRUNCATE users CASCADE` (esconderia uma tabela nova que referencie `users` sem que o teste saiba). | FK |
| D12 | Front: navegação "Criar lote" / "Meus lotes" no `SiteHeader` só para `AUCTIONEER`; `LotCreation` com etapas `catalog → form → review → created`; a busca fica montada e oculta para não perder termo e resultados; revisão como etapa própria, sem modal. | Navegação dentro do painel; revisão como resumo vivo sob os campos; desmontar a busca. | P9, EXPERIENCE §6 |
| D13 | Reais → centavos: regex `^(\d{1,3}(\.\d{3})+\|\d+)(,\d{1,2})?$` após `trim`; centavos por concatenação de texto; limite por comparação de texto com `9007199254740991`; `formatCents` também textual. | `parseFloat`, `Number("12,34")`, `Intl` para parse. | P5 |
| D14 | Dois níveis de serviço (A3): `resolve_artwork_for_lot(client, external_id)` resolve e valida a obra na AIC, só para a criação manual; `create_lot(session, *, snapshot, terms, auctioneer_id, now, is_demo)` aplica a regra e persiste, sem rede e sem cliente HTTP na assinatura, usado pela criação manual e pelo seed. | Um único `create_lot` que recebe `external_id` e chama a AIC (o seed precisaria de um desvio); o seed com um cliente falso da AIC. | P1, P8, A3 |

## 3. Aprovação final: Q1 e ajustes A2 a A4

### Q1 — Teste automatizado do conversor de dinheiro (aprovada: `node --test`)
- **Decisão.** `frontend/src/money.test.ts` com `node:test` e `node:assert/strict`,
  rodado por `npm test` (`node --test "src/**/*.test.ts"`) pelo type stripping do Node 24,
  como etapa "Frontend: test" do `verify.sh`, entre "typecheck" e "build". Casos em
  `test-plan.md` §8.
- **Motivo.** Lógica financeira pequena, crítica e reutilizada (3.1, 3.5); o Node 24 já
  roda TypeScript apagável; nenhuma dependência nem framework novo.
- **Alternativa descartada.** Só roteiro manual (padrão anterior desta spec); Vitest com
  Testing Library (dependência nova, 2.2 P15 e 2.3 P10).
- **Consequências.** O arquivo de teste fica fora do `tsconfig.app.json` (`exclude`) e
  dentro do `tsconfig.node.json` (`include`, que já tem `types: ["node"]`);
  `npm run typecheck` passa a checar os dois projetos. Fecha a parte "ferramenta de
  teste do front" da Q10 só para lógica pura sem DOM (registrar em `ARQUITETURA.md`,
  Questão 10). Componentes continuam sem teste automatizado.

### A2 — "Meus lotes" sem limite
- **Decisão.** `GET /api/lots/mine` devolve todos os lotes do `AUCTIONEER` da sessão,
  `created_at DESC, id DESC`, sem paginação e sem limite silencioso.
- **Motivo.** Um limite de 100 sem paginação tornaria lotes antigos inacessíveis, e não
  estava em P1 a P9.
- **Alternativa descartada.** Limite de 100 (versão anterior, vindo da opção (a) da
  story); paginação agora.
- **Consequências.** Resposta cresce com o número de lotes (aceitável na escala do
  desafio); paginação fica para quando houver necessidade (`deferred-work.md`).

### A3 — Resolução externa separada da persistência
- **Decisão.** D14. Criação manual: política e corpo → `resolve_artwork_for_lot` (AIC)
  → snapshot → transação → `create_lot` → commit. Seed: fixture local → `ArtworkSnapshot`
  → trava consultiva → hora do banco → `create_lot` → commit.
- **Motivo.** Compartilhar a regra de criação sem compartilhar a dependência externa.
- **Alternativa descartada.** Um serviço único que recebe `external_id`.
- **Consequências.** Um teste prova que o seed roda com `resolve_artwork_for_lot`,
  `catalog.get_artwork`, `ArticClient` e `httpx.Client` trocados por funções que falham.

### A4 — Faixa do dinheiro também no banco
- **Decisão.** CHECK `> 0 AND <= 9007199254740991` em `starting_bid_cents` e
  `min_increment_cents`; mesma faixa na API e no serviço (D3, D7).
- **Motivo.** Nenhuma escrita interna pode colocar no PostgreSQL um valor que a API e o
  front não representam com segurança.
- **Alternativa descartada.** Faixa só na API (versão anterior desta spec).
- **Consequências.** Não é teto comercial (a P5 continua sem teto de produto). Teste no
  PostgreSQL real: 1 e o máximo entram; 0, negativo e máximo + 1 são recusados.
