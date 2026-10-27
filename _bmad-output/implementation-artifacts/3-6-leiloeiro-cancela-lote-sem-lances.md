# Story 3.6 — Leiloeiro cancela lote sem lances

Status: done

Chave do sprint: `3-6-leiloeiro-cancela-lote-sem-lances`. Épico: 3, `in-progress`.
Criação: 26/10/2026. Consolidação: 26/10/2026.

> Escrita sobre o código **real** depois da 3.5 (`done`). **Decisões D1 a D7 consolidadas em
> 26/10/2026 (§12): todas `FECHADA`.** Nenhuma decisão bloqueante resta para `/bmad-spec`, que
> fecha schemas, nomes e imports exatos contra o código real. Nenhum código, Git, `.env*`,
> `/bmad-spec` ou `/bmad-build` foi executado ao criá-la nem ao consolidá-la.

## 1. Story

Como leiloeiro,
quero cancelar um lote meu que ainda não recebeu lances,
para que eu retire uma obra do leilão.

**ADs:** AD-6, AD-7, AD-8, AD-11 (e AD-13, AD-19, AD-24, AD-29, AD-30 por herança).
**Requisitos:** FR4 (cancelar), FR6 (cancelados fora da vitrine). Enunciado: "cancelar um lote
que ainda não recebeu lances". O estorno é o opcional 6.6, **fora** desta story.

## 2. Estado real encontrado (verificado no código)

| Peça | Estado real | Consequência para a 3.6 |
| --- | --- | --- |
| Coluna de cancelamento | **Não existe.** `Lot` (`app/lots.py`) e as migrations `0001`–`0005` não têm `cancelled_at` nem `status`. A 2.4 (P3) tirou `status` de propósito: a fase é derivada do tempo, e a migration `0003` diz que as colunas de cancelamento "nascem, aditivas, nas stories que as usam". | **Migration `0006` obrigatória** (Q10). O nome `cancelled_at` já está fixado em `ARQUITETURA.md` (questão 4) e no `deferred-work.md` (2.4 e 2.5). |
| Trava do lote | `lock_lot` (`app/lots.py`): `SELECT … FOR UPDATE` com `populate_existing`. Hora: `database_now` (`clock_timestamp()`). | Cancelar usa **as mesmas duas funções**, na mesma ordem do `place_bid`. |
| Gate da 3.4 | `authenticate_previous_state(lot, rows, integrity=, lot_id=)` e `read_history` em `app/bids.py`; devolve `AuthenticatedLot` (com `bid_count` autenticado) ou `IntegrityConflict`. Função de módulo; o `deferred-work.md` obriga 3.6/4.3/6.6 a **reutilizá-la**. | Cancelar chama o gate; não copia nada. `app/bids.py` importa `app/lots.py`, então o serviço de cancelamento **não pode** morar em `lots.py` (import circular). Ver D6. |
| Âncora v1 | `AnchorState(v, lot_id, bid_count, final_hash)` e HMAC sobre isso. Não cobre `ends_at`, `auctioneer_id`, termos, nem o estado de cancelamento. | Cancelar **não toca** `bids`, `bid_count`, `final_hash` nem `anchor_hmac` (Q6). |
| Fase | `lot_phase(starts_at, ends_at, now)`: `scheduled`/`live`/`ended`, derivada, sem estado "cancelado". `ended` = "Encerrado, apurando resultado" (AD-19). | Cancelado **não** vira quarto valor de `LotPhase` (contrato público fixado por teste). |
| Vitrine e leituras | `read_public_snapshot` (`outerjoin(Lot, true())`), `read_public_lot_snapshot` (`outerjoin(Lot, Lot.id == lot_id)`), `public_room_statement` (`outerjoin(Lot, Lot.id == lot_id)`), `my_bids_statement` (`where Lot.id == lot_id`). | Nas três leituras que partem do relógio (`LEFT JOIN`), o filtro `cancelled_at IS NULL` entra **na condição do JOIN**, nunca num `WHERE` (aviso do `deferred-work.md`, 2.5), para preservar o `as_of` e o caso vazio. `my_bids_statement` **não tem JOIN**: ali `WHERE … AND cancelled_at IS NULL` é o correto, e zero linhas vira 404. |
| Seed | `seed_demo_lot`: demo aberto = `is_demo AND ends_at > now AND anchor_hmac IS NOT NULL`. | Acrescentar `AND cancelled_at IS NULL` (já anunciado em `ARQUITETURA.md`, questão 4). |
| Papéis | `require_auctioneer` → 403 para `BIDDER`; 401 sem sessão. `AccessPolicy.AUCTIONEER`. Um teste reprova rota sem política. | A rota nova declara `AUCTIONEER` por `api_route`. |
| Escrita sem corpo | `POST /api/auth/logout` é POST sem corpo; `ApiWriteGuardMiddleware` exige `Origin` e `Content-Type: application/json` em toda escrita `/api`. | Cancelar segue o mesmo padrão: POST sem corpo, CSRF herdado, nada novo. |
| Painel do leiloeiro | `MyLots.tsx` (leitura pura, sem ações, comentário "sem estado do lote"); `GET /api/lots/mine` devolve `LotResponse` sem fase, sem contagem de lances, sem cancelamento. | Para o CTA ser honesto a lista precisa de dados novos (D7). |
| Erros | `errors.py`: catálogo de `MESSAGES` por código; recusas do lance são 422; integridade é 409 `lot_integrity_conflict` com mensagem que fala em "lance". | Códigos novos e a mensagem do 409 (D5). |

## 3. Escopo

**Backend**
- Migration `0006`: `lots.cancelled_at TIMESTAMPTZ NULL`. Sem `status`, sem CHECK ligando a
  `bid_count` (a 6.6 cancela lote **com** lances; um CHECK a bloquearia). Aditiva, sem tocar
  dados, `downgrade` simétrico.
- `Lot.cancelled_at` no modelo.
- Módulo `app/lot_cancellation.py` (serviço `cancel_lot`, schema da resposta e o registro da
  rota `POST /api/lots/{lot_id}/cancel`), ligado em `app/main.py` (§4, §7, D6).
- `place_bid` passa a recusar lote cancelado com `lot_cancelled`, depois do gate (§5, D4).
- Leituras públicas e seed filtram cancelado (§2, D3).
- `GET /api/lots/mine` passa a devolver um read model próprio da lista administrativa (D7).
- Mensagem do 409 de integridade generalizada (D5) e códigos `lot_has_bids`, `lot_cancelled`.

**Frontend** — painel "Meus lotes" (§9) e **uma** adaptação mínima da sala da 3.5: o texto do
novo código `lot_cancelled` (sem redesenhar a 3.5 nem mudar seu protocolo de sincronização).

**Testes** — §10. **Documentação** — §11.

**Fora de escopo (confirmado):** estorno e liberação de saldo; cancelar lote com lances (6.6);
liquidação, fechamento e marcador terminal (4.3, SR-08 A); WebSocket e evento de cancelamento
(4.1); resultado no painel (4.5); busca/filtro (6.5); comando administrativo para autenticar
lote legado; Épico 4.

## 4. Fluxo transacional final

Mesma autoridade da 3.4: transação → trava do lote → hora do banco → ownership → gate →
regras → escrita.

```text
request AUCTIONEER
→ lock lot FOR UPDATE
→ PostgreSQL clock_timestamp()
→ ownership
→ authenticate_previous_state
→ if already cancelled: 200 original timestamp
→ if authenticated bid_count > 0: 422 lot_has_bids
→ if now >= ends_at: 422 lot_ended
→ UPDATE cancelled_at = database_now
→ COMMIT
```

1. Rota: `require_auctioneer` (401/403 de papel); guarda `user.id` e `rollback()` da leitura de
   autenticação (D5 da 3.4). A identidade é **sempre** a da sessão; não há corpo.
2. `lock_lot(session, lot_id)` → `None` ⇒ **404**. Só `lots`, sem JOIN.
3. `now = database_now(session)` (um instante, depois da trava; AD-6/AD-26). Nunca relógio do
   Python nem do navegador.
4. Ownership: `lot.auctioneer_id != user.id` ⇒ **403**, sem efeito. Vem **antes** do gate para não
   expor o estado de integridade de um lote alheio.
5. `rows = read_history(...)` e `authenticate_previous_state(...)` (**o gate da 3.4**). Falha ⇒
   `IntegrityConflict` ⇒ **409** `lot_integrity_conflict`, zero efeitos, categoria só no log.
   Lote legado (`anchor_hmac` nulo) cai aqui (`MISSING_ANCHOR`): não se cancela estado não
   autenticado (§6). **A idempotência não ignora integridade:** lote cancelado e adulterado
   responde 409, não 200.
6. `lot.cancelled_at is not None` (e íntegro) ⇒ **200** com o `cancelled_at` **original**; nenhum
   `UPDATE`, nenhum timestamp novo (D2).
7. `authenticated.bid_count > 0` ⇒ **422** `lot_has_bids`. A decisão "sem lances" usa a contagem
   **autenticada**, nunca `lot.bid_count` cru.
8. `now >= lot.ends_at` (`lot_phase(...) is ENDED`) ⇒ **422** `lot_ended` (D1). Lote encerrado não
   é cancelado retroativamente; pertence ao fluxo de resultado/fechamento.
9. `lot.cancelled_at = now`; `session.flush()`: **um** `UPDATE lots` de uma coluna, com o
   `database_now` do passo 3. Nenhuma carteira, nenhum `bids`, nenhuma âncora.
10. Rota: `session.commit()`; em qualquer recusa, `session.rollback()` antes de responder (libera
    a trava). O serviço não faz commit nem rollback, como `place_bid`.

**Nenhuma trava de carteira, nenhuma mutação de carteira, nenhuma mudança de âncora (AD-8):** o
cancelamento trava **só o lote**; não cria ciclo com lance, depósito nem liquidação.

**Precedência das respostas:** 401 → 403 (papel) → 404 → 403 (não dono) → 409 integridade →
200 já cancelado → 422 `lot_has_bids` → 422 `lot_ended` → sucesso. Com lance **e** encerrado, vale
`lot_has_bids`.

## 5. Concorrência cancelar × primeiro lance

Os dois disputam a mesma linha com `SELECT … FOR UPDATE` (`lock_lot`), em `READ COMMITTED`.

**Ordem A, cancelamento primeiro.** Cancelar trava, lê o lote, passa por ownership, pelo gate
(autenticado com 0 lances) e por `bid_count == 0`, grava `cancelled_at`, confirma. O lance, que esperava na trava, acorda; o
`FOR UPDATE` devolve a **versão confirmada mais recente** da linha (`populate_existing` força a
releitura mesmo com o objeto no identity map). Ele passa pelo gate (nada mudou nos lances) e, no
novo passo "cancelado", logo depois do gate e antes das regras pré-carteira, é recusado com
`422 lot_cancelled` (D4). `cancelled_at` não substitui a autenticação do estado anterior. Não
chega às carteiras: zero efeitos. Resultado: lote cancelado, zero lances, carteiras intactas.

**Ordem B, lance primeiro.** O lance trava, aceita, grava `bids` + carteiras + o `UPDATE lots`
único, confirma. Cancelar acorda; `lock_lot` relê `bid_count = 1`, `read_history` (statement
posterior, novo snapshot do `READ COMMITTED`) vê o lance confirmado, o gate autentica
`bid_count = 1` e o passo 7 recusa com `lot_has_bids`. Resultado: não cancelado, exatamente um
lance, nada escrito pelo cancelamento.

**Por que não há terceiro resultado:** toda escrita em `bids` e no estado de lance passa pela
trava do lote (premissa da 3.4, §8; hoje só `place_bid` e `create_lot`). `cancelled_at` só muda
sob a mesma trava. Cada transação vê o resultado confirmado da outra por inteiro; não existe
lote cancelado com lance aceito, lance perdido nem estado parcial (cada lado grava num `UPDATE`
de lote só, e o cancelamento não escreve em mais nada). O resultado equivale a uma ordem serial.

## 6. Integridade (Q4, Q5, Q6)

- **Q4:** sim, o gate roda antes de decidir "sem lances". Sem ele, quem tem acesso direto ao banco
  zeraria `bid_count`/`current_bid_cents` e o cancelamento deixaria o líder real com saldo
  comprometido preso num lote cancelado, sem lance visível. Fontes: AD-7 passo 4;
  `deferred-work.md` ("3.6 … decide 'sem lances' com o `bid_count` autenticado pelo gate" e "o
  **mesmo** gate"). Reuso por **import** de `authenticate_previous_state` e `read_history`, sem
  copiar e sem mover código da 3.4 (D6).
- **Legado (Q5):** o gate já é fail-closed para `anchor_hmac IS NULL`, e o `ARQUITETURA.md` (AD-13)
  diz que assinatura ausente nunca vale como confiável e que "âncora nula + zero lances =
  confiável" foi descartado. Cancelar não pode reabrir isso por outra porta; recuso com 409, sem repair, sem
  reassinar e sem bypass administrativo.
  **Consequência operacional, que registro:** lotes legados não autenticados **não podem ser
  cancelados pela Story 3.6**; o lote permanece na vitrine até encerrar. Hoje isso atinge no máximo o demo antigo do
  deploy (o seed cria outro demo assinado). A saída futura é o comando administrativo já
  descrito no `deferred-work.md`; não entra na 3.6.
- **Q6:** a âncora **não** muda. Ela autentica o histórico de lances (quantidade e hash final),
  que o cancelamento sem lances não altera; reassinar seria "reassinar estado do banco" (proibido
  em AD-13). `cancelled_at` fica **fora** da âncora, como `ends_at` e `auctioneer_id`
  (limitação já declarada: a âncora v1 não autentica os termos do lote). Quem editar
  `cancelled_at` direto no banco só esconde/reexibe o lote; isso não move saldo e fica na mesma
  classe da limitação existente (a registrar no README).
- Nenhum detalhe de integridade chega ao cliente: código e mensagem únicos (D5); categoria só no
  log, como na 3.4.

## 7. Contrato HTTP

`POST /api/lots/{lot_id}/cancel` (Q1: sub-recurso de ação, como `/bids` e `/auth/logout`; sem
`DELETE`, porque o lote não é apagado, e sem `PATCH {status}`, porque não existe `status`).

- Política `AUCTIONEER`; **sem corpo**; `Content-Type: application/json` e `Origin` exigidos
  pelo guard existente. `lot_id` malformado ⇒ 422 de validação pela infraestrutura existente.
- **200** `{ "id": "<uuid>", "cancelled_at": "<UTC>" }`, `Cache-Control: no-store`. A repetição
  idempotente devolve **a mesma resposta**, com o `cancelled_at` original. 200, não 201: nada é
  criado. O painel relê a lista para ver o estado completo.
- Erros (envelope único da 2.1):

| Status | `code` | Quando |
| --- | --- | --- |
| 401 | `unauthorized` | sem sessão |
| 403 | `forbidden` | `BIDDER`, ou `AUCTIONEER` que não é o dono |
| 404 | `not_found` | lote inexistente |
| 409 | `lot_integrity_conflict` | gate falhou (inclui legado sem âncora e cancelado adulterado) |
| 422 | `lot_has_bids` (novo) | "Este lote não pode ser cancelado porque já recebeu lances." |
| 422 | `lot_ended` (existente) | lote já terminou (D1) |
| 422 | `validation_error` | `lot_id` malformado (infraestrutura existente) |

- `errors.py` (`MESSAGES`) ganha `lot_has_bids` e `lot_cancelled` ("Este lote foi cancelado.", 422
  só no `POST …/bids`). O teste de igualdade de conjuntos entre `BidRefusal` e o catálogo é
  atualizado **para incluir `lot_cancelled`**, sem afrouxar.
- **Mensagem do 409 (D5):** o código e o status não mudam; o texto vira "Não foi possível concluir
  a operação porque a integridade do lote não pôde ser confirmada." (sem HMAC, hash, cadeia, âncora,
  campo ou motivo técnico). Os testes da 3.4 (e da 3.5, se citarem) que fixam o texto antigo de
  lance são atualizados **explicitamente**.

## 8. Premissas e invariantes (herdadas e novas)

- Toda escrita em `bids` e no estado de lance **e agora em `cancelled_at`** passa por `lock_lot`.
  Registrar na docstring de `Lot` e do novo módulo; 4.3 e 6.6 herdam.
- `cancelled_at` só é escrito pelo serviço de cancelamento (e lido por leituras/seed). Nada
  "descancela": não há rota nem serviço para isso.
- Cancelar não escreve em `wallets`, `bids`, `anchor_hmac`, `final_hash`, `bid_count`,
  `current_*` nem `ends_at`.

## 9. Frontend (mínimo, sem redesign)

Antes de editar: ler `DESIGN.md` e `EXPERIENCE.md` (regra do `CLAUDE.md`). `EXPERIENCE.md` §2
exige "sem cancelamento se endpoint/política não existem": o front só entra depois do back.

- **Read model da lista (D7):** `GET /api/lots/mine` devolve `{as_of, items}`; cada item mantém os
  campos atuais e ganha `cancelled_at`, `bid_count` e `phase` (calculada com o `as_of`, lido do
  banco, sem relógio do navegador). `bid_count` é só dica não autenticada. Modelo próprio da
  lista administrativa: o 201 de `POST /api/lots` e o read model público não mudam.
- **Público × dono (D3):** o lote cancelado deixa de existir para o público (404) e **continua
  visível para o dono** em "Meus lotes", com o selo textual **"Cancelado"** (nunca só cor).
- **CTA "Cancelar lote":** só quando aparentemente elegível: sessão de leiloeiro, `cancelled_at ==
  null`, `bid_count == 0` e `phase` ≠ `ended`. É só UX: o servidor é a autoridade e um estado
  antigo pode resultar em recusa.
- **Confirmação inline** na própria linha ("O lote sai da vitrine e não pode ser reaberto."; botões
  "Confirmar cancelamento" e "Voltar"), sem modal nem biblioteca nova. Foco no botão de confirmação
  e de volta ao CTA ao voltar.
- **Enviando:** botão desabilitado ("Cancelando…"), sem duplo envio e sem reenvio automático.
- **Sucesso:** relê `GET /api/lots/mine`; aviso `role="status"` "Lote cancelado."; foco no título.
- **Erro por `code`/status (nunca pelo `message`):** `lot_has_bids` ("Este lote não pode ser
  cancelado porque já recebeu lances.") e `lot_ended` mostram o motivo e releem a lista; 403
  ("Você não pode cancelar este lote."); 409 integridade (texto neutro, sem afirmar cancelamento);
  404; 401 ⇒ sessão expirada (mesmo callback do painel). Rede/5xx/corpo fora do contrato ⇒
  **ambíguo**: não afirma sucesso nem falha e faz **uma** releitura da lista.
- **Sala (3.5), adaptação mínima:** `lot_cancelled` vira mais um código de recusa conhecido em
  `api/bids.ts` e `bidFeedback.ts`, com o texto "Este lote foi cancelado." Sem mudar o formulário,
  o protocolo de sincronização nem o layout.
- Arquivos previstos: `api/lots.ts` (`cancelLot`, tipos do read model), `lotCancellation.ts`
  (+ `.test.ts`, texto e classificação puros), `MyLots.tsx`, `api/bids.ts`, `bidFeedback.ts` (+ teste),
  CSS mínimo no existente, `e2e/my-lots.spec.ts` e `mockApi.ts`.

## 10. Testes

Em PostgreSQL real; sem `sleep` como prova de sincronização (padrão `hold_*` +
`wait_for_blocked_lock` + `pg_locks` da 3.4). Só o que a 3.6 acrescenta.

**Migration** `test_lots_cancellation_migration.py`: coluna `cancelled_at` (tipo, nulável, sem
default), lotes existentes ficam `NULL`, nenhum CHECK novo, `downgrade`.

**Integração** `test_lot_cancellation.py`:
1. dono cancela lote sem lances (agendado e ao vivo): 200, `cancelled_at` = `clock_timestamp` da
   operação, resposta com 2 chaves, `no-store`; **`wallets`, `bids`, `anchor_hmac`, `final_hash`,
   `ends_at`, `bid_count` idênticos** antes/depois (snapshot);
2. outro `AUCTIONEER` ⇒ 403, nada muda;
3. `BIDDER` ⇒ 403; sem sessão ⇒ 401; CSRF (origem/Content-Type) herdado: 403/415;
4. lote inexistente ⇒ 404; `lot_id` inválido ⇒ 422;
5. lote com 1 lance (pelo serviço real) ⇒ 422 `lot_has_bids`, nada muda, carteira do líder intacta;
6. já cancelado e íntegro ⇒ 200 com o **mesmo** `cancelled_at` original (comparado com o valor do
   banco), nenhum segundo `UPDATE` (recorder), nenhum timestamp novo; já cancelado **e
   adulterado** ⇒ 409, não 200; já cancelado por outro `AUCTIONEER` ⇒ 403 (ownership antes do
   gate, sem expor integridade);
7. encerrado sem lances ⇒ 422 `lot_ended` (D1); `now == ends_at` ⇒ encerrado e sem efeito; hora do
   banco, lida depois da trava;
8. gate: adulteração direta com histórico real (`bid_count`/`current_*` zerados com lance em `bids`;
   lance removido do fim; âncora trocada) ⇒ 409 `lot_integrity_conflict`, mensagem genérica
   idêntica e neutra (D5), **não cancelado**, nenhuma HMAC nova; legado `anchor_hmac NULL` ⇒
   409, sem repair nem reassinatura;
9. persistência: falha injetada depois do `UPDATE` e antes do commit ⇒ `cancelled_at` continua
   `NULL` (sem parcial);
10. leituras: lote cancelado some de `GET /api/lots` (o `as_of` continua presente, inclusive com
    **só** cancelados), e `GET /api/lots/{id}`, `GET …/bids` e `GET …/bids/mine` ⇒ 404 (D3); o
    contrato de `phase` e as 17 chaves públicas seguem intactos (nenhuma `phase = cancelled`);
    `GET /api/lots/mine` lista o cancelado com `cancelled_at`, `bid_count`, `phase` e `as_of`; o 201
    de `POST /api/lots` não muda; nenhuma leitura escreve (AD-19);
11. `POST …/bids` em lote cancelado ⇒ 422 `lot_cancelled`, zero efeitos (nenhum `bids`, nenhuma
    carteira) (D4); cancelado com histórico adulterado ou `anchor_hmac` nulo ⇒ 409 (o gate vem
    antes do `cancelled_at`); testes da 3.4 com o texto antigo do 409 atualizados (D5);
12. seed: demo cancelado não conta como aberto ⇒ novo demo no boot; boot repetido não duplica.

**Concorrência** `test_lot_cancellation_concurrency.py` (cancelar × primeiro lance):
- **A:** a sessão do cancelamento segura a trava sem confirmar; o lance (outra conexão/thread)
  bloqueia em `lock_lot` (provado por `pg_locks`); o cancelamento confirma; o lance devolve
  `lot_cancelled`. Estado final: cancelado, **0** lances, carteiras iguais às iniciais.
- **B:** o lance segura a trava; o cancelamento bloqueia; o lance confirma; cancelamento devolve
  `lot_has_bids`. Estado final: `cancelled_at IS NULL`, **exatamente 1** lance, cadeia e âncora
  válidas (`assert_authenticated`), invariantes de carteira (`assert_invariants`).
- **Corrida livre** (barreira, várias rodadas): o estado final está **sempre** em exatamente um
  de dois conjuntos {cancelado ∧ 0 lances ∧ lance recusado} ou {não cancelado ∧ 1 lance ∧
  cancelamento recusado}; nunca cancelado com lance, nunca lance sem efeito aceito.
- Ordem das travas por recorder: o cancelamento emite `FOR UPDATE` em `lots`, **antes** de
  `clock_timestamp()`, e **nenhum** `FOR UPDATE` em `wallets`.

**Frontend:** `lotCancellation.test.ts`, o teste de `bidFeedback` para `lot_cancelled` (`node --test`: texto por `code`, classificação de
falha, ambíguo nunca afirma sucesso) e `e2e/my-lots.spec.ts` (Playwright, API simulada, só com
`VERIFY_E2E=1`): CTA só nas linhas elegíveis, selo "Cancelado" para o dono, confirmação inline,
enviando sem duplo envio, sucesso, `lot_has_bids`, `lot_ended`, 403, 401, erro ambíguo (uma
releitura), foco, alvo de toque, teclado.

**Mutações úteis (uma por vez, restaurada e conferida; relatar só as executadas):**
M1 decidir `lot_has_bids` com o `bid_count` lido **antes** de `lock_lot` (sem usar o valor recarregado depois); M2 pular o gate; M3 ignorar `lot_has_bids`; M4 remover a
checagem de dono; M5 remover `lot_ended`; M6 mover `cancelled_at IS NULL` do `JOIN` para `WHERE`
ou removê-lo (só nas três consultas com `LEFT JOIN`/relógio; nunca em `/bids/mine`); M7 gravar `cancelled_at` com relógio do Python; M8 decidir "já cancelado" antes do gate. Cada uma deve reprovar pelo menos um
teste acima. Sem framework novo.

## 11. Documentação

- Esta story; `sprint-status.yaml` (3.6 → `ready-for-dev`, já feito).
- `docs/uso_de_ia.md`: entrada da 3.6.
- `README` ("Comportamentos que podem surpreender"): lote cancelado some das leituras públicas
  (404); cancelar só sem lances e antes do fim; lote anterior à 3.4 (legado, não autenticado) não é cancelável pela 3.6; cancelar o
  demo faz o próximo boot criar outro; `cancelled_at` fora da âncora; nota curta, junto à limitação da sala sem atualização automática: após `lot_cancelled` a mensagem imediata é “Este lote foi cancelado.” e uma leitura posterior pode mostrar “Lote não encontrado.” (404 por D3), sem significar falha do cancelamento.
- `deferred-work.md` **somente** se surgir dívida real no build (candidatas: evento/snapshot de
  cancelamento para a 4.1; `cancelled_at` fora da âncora). `ARQUITETURA.md` não muda por detalhe
  de implementação.

## 12. Decisões fechadas (26/10/2026)

| ID | Decisão | Situação |
| --- | --- | --- |
| D1 | Cancelar só com `now < ends_at` (agendado ou ao vivo sem lances). `now >= ends_at` ⇒ 422 `lot_ended`; sem cancelamento retroativo. Hora do PostgreSQL lida **depois** da trava. | **FECHADA** |
| D2 | Idempotente: lote já cancelado **e íntegro** ⇒ 200 com o `cancelled_at` original, sem segundo `UPDATE` nem novo timestamp. Ordem: lock → hora → ownership → gate → já cancelado → lances → encerramento → cancelar. Cancelado adulterado ⇒ 409. | **FECHADA** |
| D3 | Cancelado inexistente para o público: fora da vitrine; `GET /api/lots/{id}`, `GET …/bids` (e `…/bids/mine`) ⇒ 404. Sem `phase = cancelled`. O dono continua vendo o lote em "Meus lotes" com o selo "Cancelado". | **FECHADA** |
| D4 | Novo `422 lot_cancelled` no lance, checado **depois** do gate (`cancelled_at` não substitui a autenticação). Adaptação mínima da sala: texto "Este lote foi cancelado." | **FECHADA** |
| D5 | Mantém `lot_integrity_conflict`/409; mensagem pública neutra e reutilizável; testes da 3.4 que fixam o texto antigo atualizados de forma explícita. | **FECHADA** |
| D6 | Módulo dedicado `app/lot_cancellation.py` (serviço, schema da resposta, registro da rota); importa `lock_lot`, `database_now`, `authenticate_previous_state`, `read_history`; **sem** copiar nem mover o gate; `lots.py` não importa o módulo novo; ligação em `main.py`. A spec fecha os imports reais. | **FECHADA** |
| D7 | Read model próprio de `GET /api/lots/mine` com `cancelled_at`, `bid_count`, `phase` e `as_of` além dos campos atuais; 201 da criação e read model público inalterados. Botão só quando aparentemente elegível, como UX; o servidor decide. | **FECHADA** |

**Demais questões:** Q1 `POST /api/lots/{lot_id}/cancel` sem corpo. Q4 gate obrigatório. Q5 legado
⇒ 409. Q6 âncora inalterada. Q7 `lot_has_bids`. Q8 `{id, cancelled_at}`. Q9 confirmação inline.
Q10 migration `0006`: `cancelled_at` nulável, `TIMESTAMPTZ`, **sem default de relógio**, valor
escrito explicitamente com o `database_now` pós-trava, **sem backfill**; índices só se a spec provar
necessidade.

## 13. Riscos

- **R1 Lote legado incancelável** (Q5): aceito e documentado (§6).
- **R2 `cancelled_at` fora da âncora:** editável por quem tem o banco; não move saldo (§6).
- **R3 Sala aberta não é avisada** (sem WebSocket até a 4.1): o cancelamento aparece ao recarregar
  ou ao tentar lance (`lot_cancelled`, D4). Comportamento a documentar. Após `lot_cancelled`, a mensagem imediata é “Este lote foi cancelado.”. Numa leitura pública posterior (atualização ou reentrada), o lote cancelado segue a D3 e responde 404, e a UI pode mostrar “Lote não encontrado.”; isso não significa que o cancelamento falhou. Aceito: não crio `phase=cancelled` nem exceção pública para preservar a mensagem, e `LotPage` não muda.
- **R4 Fila na trava do lote:** sem `lock_timeout` (D13 da 3.4), aceito na escala do desafio.
- **R5 Predicado do seed:** um demo cancelado deixa de contar; o boot seguinte cria outro (AD-24).

## 14. Tarefas (build, depois de D1–D7 fechadas e da spec)

- [x] T1 Migration `0006` (`cancelled_at` nulável, sem default, sem backfill) + `Lot.cancelled_at` + teste de migration.
- [x] T2 `app/lot_cancellation.py`: `cancel_lot` + schema + rota (`AUCTIONEER`) ligada em `main.py`;
  `errors.py` (`lot_has_bids`, `lot_cancelled`, mensagem neutra do 409, D5).
- [x] T3 `place_bid`: recusa `lot_cancelled` depois do gate (D4).
- [x] T4 Filtros nas leituras públicas e no seed; read model de `my_lots` (D7).
- [x] T5 Testes de integração e de concorrência (§10).
- [x] T6 Frontend: `api/lots.ts`, `lotCancellation.ts`, `MyLots.tsx`, `bidFeedback.ts` (texto do
  `lot_cancelled`), testes `node --test` e Playwright.
- [x] T7 Mutações M1–M8; documentação (§11); `verify`.

## Dev Notes

### Arquivos previstos
`backend/migrations/versions/0006_lot_cancellation.py` (novo) · `backend/app/lots.py` ·
`backend/app/lot_cancellation.py` (novo) · `backend/app/bids.py` · `backend/app/bid_rules.py`
(só o enum) · `backend/app/errors.py` · `backend/app/seed.py` · `backend/app/main.py` (ligação do módulo novo) ·
testes em `backend/tests/` · `frontend/src/{api/lots.ts,api/bids.ts,MyLots.tsx,lotCancellation.ts,bidFeedback.ts}` ·
`frontend/e2e/{my-lots.spec.ts,support/mockApi.ts}`.

### Armadilhas
- Nas leituras que partem do relógio (`LEFT JOIN`), o filtro `cancelled_at IS NULL` vai **no `JOIN`**, não no `WHERE` (perderia o `as_of`). Em `my_bids_statement`, sem JOIN, o `WHERE` é o correto; não inventar JOIN ali.
- `lock_lot` usa `populate_existing`: não trocar por `session.get`.
- O serviço não faz commit/rollback; a rota faz, e **antes de responder** uma recusa.
- Registrar a rota nova sem quebrar a ordem `/api/lots/mine` antes de `/api/lots/{lot_id}`; o
  `/cancel` tem segmento extra e não colide, mas o teste de ordem de rotas deve continuar passando.
- Todo teste que fixa a lista de chaves de `mine` ou o conjunto de códigos de erro muda **de forma
  explícita**, nunca afrouxado.
- Nunca ler `.env*`; segredos de teste vêm de `integrity()` / `integrity_secrets()`.

### Referências
`docs/ARQUITETURA.md` AD-6 a AD-9, AD-11, AD-13, AD-19, AD-24, questão 4 · `deferred-work.md`
(2.4, 2.5, "spec e build da 3.4") · `epics.md` Story 3.6 e 6.6 · `backend/app/bids.py`
(`authenticate_previous_state`, `place_bid`) · `backend/app/lots.py` (`lock_lot`, `database_now`) ·
`3-4-lance-transacional-com-travas-e-anti-sniping.md` §8–§10 · `3-5-dar-lance-pela-sala-do-lote.md`.

## Dev Agent Record

### Agent Model Used
Sonnet 5.5 (implementação, 26/10/2026).

### Completion Notes List
- Implementado a partir da story e da spec aprovadas (D1–D7 `FECHADA`), sem reabrir decisão.
- Migration `0006` (`lots.cancelled_at TIMESTAMPTZ NULL`, sem default, sem backfill, sem
  CHECK nem índice). `app/lot_cancellation.py` (`cancel_lot`, `CancelLotResponse` e a rota
  `POST /api/lots/{lot_id}/cancel`, política `AUCTIONEER`) ligado em `main.py`. O gate da 3.4
  é importado, não copiado nem movido.
- Ordem: trava do lote → `database_now` → dono → gate → já cancelado (200 original, sem
  `UPDATE`) → `bid_count` autenticado (`lot_has_bids`) → `now >= ends_at` (`lot_ended`) →
  `UPDATE cancelled_at`. Sem carteira, sem âncora, sem lances.
- `place_bid` devolve `lot_cancelled` depois do gate e antes das regras (D4). Mensagem do 409
  neutra (D5). Filtro de cancelado na condição do `JOIN` nas três leituras que partem do
  relógio e em `WHERE` em `/bids/mine`. `GET /api/lots/mine` virou `{as_of, items}` com
  `cancelled_at`, `bid_count` e `phase` (D7). Seed ignora demo cancelado.
- Front: `api/lots.ts` (`cancelLot`, `classifyCancelResponse`, read model), `lotCancellation.ts`,
  `MyLots.tsx` (CTA, confirmação inline, envio único, releitura, selo "Cancelado") e o único
  novo código da sala (`lot_cancelled`).
- Mutações executadas (uma por vez, restauração conferida): M1, M2, M3, M4, M5, M6, M7 (duas
  variantes), M8, M9 (a–d) e uma extra (`lot_cancelled` antes do gate); todas reprovaram
  pelo menos um teste. Detalhes e saídas no relatório da sessão.
- Code review independente: nenhum HIGH/MEDIUM. O LOW F-01 (C2 e C3 não comparavam o
  snapshot de todas as carteiras) foi corrigido só nos testes: `assert_cancelled_with_no_bids`
  e `assert_not_cancelled_with_one_bid` agora comparam `wallet_rows` completo com o snapshot
  anterior à corrida (no lance vencedor, só o `committed` do licitante sobe o valor aceito).
- O Ruff acusou duas linhas longas na docstring da migration no primeiro `verify`; corrigidas.

### File List
- `_bmad-output/implementation-artifacts/3-6-leiloeiro-cancela-lote-sem-lances.md` (este arquivo).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (3.6 → `done`).
- Novos: `backend/migrations/versions/0006_lot_cancellation.py`, `backend/app/lot_cancellation.py`,
  `backend/tests/cancel_support.py`, `backend/tests/integration/{test_lot_cancellation,
  test_lot_cancellation_concurrency,test_lots_cancellation_migration}.py`,
  `frontend/src/{lotCancellation.ts,lotCancellation.test.ts,api/lots.test.ts}`,
  `frontend/e2e/my-lots.spec.ts`.
- Alterados: `backend/app/{lots,bids,bid_rules,errors,seed,main}.py`;
  `backend/tests/{lot_support,test_openapi,test_access_policy,test_errors,test_bid_rules}.py`;
  `backend/tests/integration/{test_bid_integrity_gate,test_bid_routes,test_bids_migration,
  test_lots_migration,test_my_lots,test_seed}.py`;
  `frontend/src/{api/lots.ts,api/bids.ts,api/bids.test.ts,MyLots.tsx,bidFeedback.ts,
  bidFeedback.test.ts,App.css}`; `frontend/e2e/{support/mockApi.ts,lot-room.spec.ts}`;
  `README.md`; `docs/uso_de_ia.md`.
