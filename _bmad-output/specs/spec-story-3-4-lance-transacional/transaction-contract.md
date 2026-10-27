
> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.

# Contrato transacional do lance — Story 3.4

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

## 1. Tipos (`app/bids.py`)

```python
class IntegrityFailure(StrEnum):      # só log e testes; o cliente vê um código só
    MISSING_ANCHOR = "missing_anchor"
    MALFORMED_STATE = "malformed_state"
    CHAIN_MISMATCH = "chain_mismatch"
    ANCHOR_MISMATCH = "anchor_mismatch"
    SUMMARY_MISMATCH = "summary_mismatch"
    OPERATIONAL_MISMATCH = "operational_mismatch"

@dataclass(frozen=True)
class IntegrityConflict:
    reason: IntegrityFailure

@dataclass(frozen=True)
class AuthenticatedLot:               # só o gate o cria
    bid_count: int
    final_hash: str
    current: CurrentBid | None        # tipo da 3.2

@dataclass(frozen=True)
class PlacedBid:
    sequence: int
    bidder_alias: str
    amount_cents: int
    placed_at: datetime               # o `now` do passo 3, UTC
    ends_at: datetime                 # BidAccepted.ends_at
    anti_sniping_applied: bool
    wallet: Wallet                    # carteira travada do licitante, já atualizada

def place_bid(session, *, lot_id: UUID, bidder_id: UUID, amount_cents: int,
              integrity: IntegrityConfig) -> PlacedBid | BidRefusal | IntegrityConflict | None
```

`None` = lote inexistente (precedente: `read_public_lot_snapshot`). O serviço não faz
commit nem rollback; a rota decide (precedente: `deposit`). Imports por nome
(`from app.bid_rules import evaluate_pre_wallet, ...`), para os spies dos testes
substituírem `app.bids.<nome>`.

## 2. Algoritmo (mapa AD-7 → código)

| AD-7 | Código | Banco |
| --- | --- | --- |
| — | Rota: CSRF (middleware), corpo, `require_bidder`; `bidder_id = user.id`; `session.rollback()` (D5) | `ROLLBACK` da leitura do `User` |
| 1 | Autobegin na primeira instrução seguinte (`READ COMMITTED`, padrão) | `BEGIN` |
| 2 | `lot = lock_lot(session, lot_id)`; `None` → devolve `None` | `SELECT lots.* FROM lots WHERE lots.id = $1 FOR UPDATE` |
| 3 | `now = database_now(session)`; único | `SELECT clock_timestamp()` |
| 4 | `rows = read_history(session, lot_id)`; `auth = authenticate_previous_state(lot, rows, integrity=integrity, lot_id=lot_id)`; falha → `IntegrityConflict` | `SELECT lot_id, sequence, bidder_id, bidder_alias, amount_cents, placed_at, previous_hash, current_hash, canonical_version FROM bids WHERE lot_id = $1 ORDER BY sequence` |
| 5 | `state = LotBidState(starts_at, ends_at, starting_bid_cents, min_increment_cents, current=auth.current)` do `lot` travado; `eligible = evaluate_pre_wallet(state, BidAttempt(bidder_id=..., amount_cents=...), now)`; recusa → devolve | — |
| 6 | `ids = {bidder_id} ∪ {auth.current.leader_id se houver}` (o líder **autenticado**) | — |
| 7 | `wallets = {uid: lock_wallet(session, uid) for uid in sorted(ids)}` | `SELECT wallets ... FOR UPDATE` × 1 ou 2, `user_id` crescente |
| 8 | `accepted = evaluate_post_wallet(eligible, available_cents(w.total, w.committed))` da carteira do licitante; recusa → devolve | — |
| 9 | Se `auth.current`: `wallets[leader].committed_balance_cents -= auth.current.amount_cents` | — |
| 10 | `wallets[bidder].committed_balance_cents += amount_cents` | — |
| — | `session.flush()` (**F1**) | `UPDATE wallets` × 1 ou 2 |
| 11–12 | Locais: `new_leader = bidder_id`, `new_current = amount_cents`; `accepted.ends_at` e `accepted.anti_sniping_applied` guardados (nenhuma escrita no `Lot` ainda, D1) | — |
| 13 | `sequence = auth.bid_count + 1` | — |
| 14 | `alias = generate_bidder_alias(lot_id=lot_id, user_id=bidder_id, pseudonym_secret=integrity.pseudonym_secret)` | — |
| 15 | `canonical = CanonicalBid(v=1, lot_id=lot_id, sequence=sequence, bidder_alias=alias, amount_cents=amount_cents, timestamp=now, previous_hash=auth.final_hash)` | — |
| 16 | `current_hash = compute_bid_hash(canonical)`; `session.add(Bid(..., placed_at=now, canonical_version=1))`; `session.flush()` (**F2**) | `INSERT INTO bids` |
| 17 | `anchor = compute_anchor_hmac(AnchorState(v=1, lot_id=lot_id, bid_count=sequence, final_hash=current_hash), audit_hmac_secret=integrity.audit_hmac_secret)`; atribui ao `lot`, juntos, `current_bid_cents`, `current_leader_id`, `bid_count`, `final_hash`, `anchor_hmac` e, **só se** `accepted.anti_sniping_applied`, `ends_at = accepted.ends_at`; `session.flush()` (**F3**) | **um** `UPDATE lots SET current_bid_cents, current_leader_id, bid_count, final_hash, anchor_hmac [, ends_at]` |
| — | Devolve `PlacedBid` | — |
| 18 | Rota: `session.commit()`; 201 | `COMMIT` |

Regras obrigatórias:

- **Gate antes de qualquer regra de negócio (P1).** Nenhuma chamada a
  `evaluate_pre_wallet`, nem construção de `LotBidState` com líder ou lance atual,
  antes de o gate devolver `AuthenticatedLot`. Consequência observável: lote
  adulterado ou legado responde 409 mesmo quando a regra pura daria `lot_ended`,
  `below_minimum` ou `already_winning` (G9b, G10b, G11b).
- Recusa (5 ou 8) e 409 (4): a rota faz `session.rollback()` antes de responder
  (libera travas). Recusa em 5 e 409 não travam carteira.
- **Um único `UPDATE lots` final e coerente.** Num aceite ele sempre grava
  `current_bid_cents`, `current_leader_id`, `bid_count`, `final_hash` e
  `anchor_hmac`; grava também `ends_at` **somente** quando
  `anti_sniping_applied = True`. Sem extensão, `ends_at` não é atribuído e não aparece
  no `SET`; não usar `flag_modified` nem outro artifício para forçar valor idêntico.
  O que importa é um statement final coerente, não o número de colunas.
- O `lot` só é mutado imediatamente antes de F3; antes disso nenhum `SELECT` pode
  disparar autoflush de um `UPDATE` parcial (que a CHECK reprovaria).
- `placed_at` (atribuído explicitamente no `INSERT`), `CanonicalBid.timestamp` e a
  resposta usam o mesmo objeto `now` (§6.1).
- Guarda interna inalcançável: se `auth.current` e `auth.current.leader_id ==
  bidder_id` depois do aceite da pré-carteira, `RuntimeError` (500).

SQLAlchemy das duas leituras novas (padrão de `lock_wallet`):

```python
def lock_lot(session: Session, lot_id: uuid.UUID) -> Lot | None:   # app/lots.py
    return session.scalars(
        select(Lot).where(Lot.id == lot_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()

def read_history(session: Session, lot_id: uuid.UUID) -> list[Row]:  # app/bids.py
    return session.execute(
        select(Bid.lot_id, Bid.sequence, Bid.bidder_id, Bid.bidder_alias,
               Bid.amount_cents, Bid.placed_at, Bid.previous_hash,
               Bid.current_hash, Bid.canonical_version)
        .where(Bid.lot_id == lot_id).order_by(Bid.sequence)
    ).all()
```

## 3. Gate do passo 4 (P1, P2, receita §9 da 3.3)

Entradas: `lot` travado (lido no passo 2), `rows` (passo 4, statement posterior à
trava), `lot_id` da rota, `integrity`. Nada foi escrito ainda.

Ordem fixa (a categoria registrada é a primeira que falha):

1. `lot.anchor_hmac is None` → `MISSING_ANCHOR`. Sem fallback "zero lances = confiável".
2. Dentro de `try/except ValueError` → `MALFORMED_STATE` (só aqui):
   - `state = AnchorState(v=1, lot_id=lot_id, bid_count=lot.bid_count, final_hash=lot.final_hash)`
     (o `lot_id` é o da **rota**: âncora copiada de outro lote não confere, S-02);
   - `records = tuple(VerifiableBid(bid=CanonicalBid(v=r.canonical_version,
     lot_id=r.lot_id, sequence=r.sequence, bidder_alias=r.bidder_alias,
     amount_cents=r.amount_cents, timestamp=r.placed_at,
     previous_hash=r.previous_hash), current_hash=r.current_hash) for r in rows)`;
   - `chain_ok = verify_bid_chain(records, lot_id=lot_id)`;
   - `hmac_ok = verify_anchor_hmac(state, lot.anchor_hmac, audit_hmac_secret=integrity.audit_hmac_secret)`
     (estado **anterior**, `compare_digest`).
   Os dois resultados são calculados antes de combinar (3.3 §9.1).
3. `not chain_ok` → `CHAIN_MISMATCH`.
4. `not hmac_ok` → `ANCHOR_MISMATCH`.
5. `state.bid_count != len(records)` ou `state.final_hash != (records[-1].current_hash
   if records else GENESIS_HASH)` → `SUMMARY_MISMATCH`.
6. Vínculo operacional → `OPERATIONAL_MISMATCH`:
   - `bid_count == 0`: `lot.current_bid_cents is None` **e** `lot.current_leader_id is
     None`. (O vazio exato `0`/genesis com HMAC válida já saiu de 2, 4 e 5.)
   - `bid_count > 0`, com `last = records[-1]` e `last_row = rows[-1]`:
     `last.bid.sequence == bid_count`; `lot.current_bid_cents == last.bid.amount_cents`;
     `lot.current_leader_id is not None`; `lot.current_leader_id == last_row.bidder_id`;
     `generate_bidder_alias(lot_id=lot_id, user_id=lot.current_leader_id,
     pseudonym_secret=integrity.pseudonym_secret) == last.bid.bidder_alias`.
     Só o alias **do líder atual** é recalculado; nenhum alias histórico.
7. Sucesso → `AuthenticatedLot(bid_count, final_hash, current=None ou
   CurrentBid(amount_cents=lot.current_bid_cents, leader_id=lot.current_leader_id))`.
   `CurrentBid`/`LotBidState` inválidos depois do gate são `ValueError` → 500. O gate
   autentica a cadeia, o resumo e o vínculo de líder/lance atual; **não** autentica os
   termos do lote (`starting_bid_cents`, `min_increment_cents`, `starts_at`,
   `ends_at`), que a âncora v1 não cobre. Incoerência entre esses termos e o lance
   atual vinculado só nasce de bug ou de CHECK removida (G18).

Por que fecha S-01: nenhuma escrita acontece antes de 7; a nova âncora (passo 17) só
é calculada sobre `auth.bid_count`/`auth.final_hash`, que só existem depois do
sucesso. Não há caminho que repare, reassine ou continue.

## 4. Sequência (P8)

`sequence = auth.bid_count + 1`, `int` do Python, `BIGINT` no banco, `>= 1` (CHECK e
`CanonicalBid`), sem teto artificial (3.3 D12). Relações provadas antes do `INSERT`:
cadeia contínua `1..n` (`chain_ok`), `n == bid_count` (5), último `== bid_count` (6),
então `n + 1` não colide com a PK. PK e UNIQUE são defesa: se dispararem depois do
gate, é `IntegrityError` → 500 (violação interna, nunca recusa de negócio). A nova
âncora assina `(lot_id, sequence, current_hash)`: `bid_count` novo = `sequence`.

## 5. Carteiras (AD-3, FR12)

Notação: carteira do licitante `(T_b, C_b)`, do líder anterior `(T_l, C_l)`, lance
atual autenticado `c`, novo valor `a`. Ambas travadas e relidas (`populate_existing`).

- Saldo: `evaluate_post_wallet` aceita só se `a <= T_b − C_b`.
- Com líder: `C_l' = C_l − c`; `C_b' = C_b + a`. Sem líder: só `C_b' = C_b + a`.
- Limites: `C_b' <= T_b <= MAX_CENTS` e `C_b' >= C_b >= 0`. Se I3 vale antes
  (`C_l >= c`), `0 <= C_l' <= C_l <= T_l`. Se não vale (carteira adulterada),
  `ck_wallets_committed_range` reprova F1 → 500, rollback, nada é "consertado"
  (saldos não são autenticados, limitação do AD-13).
- Mesma carteira: impossível. `already_winning` (pré-carteira, sobre o líder
  **autenticado**) recusa `bidder_id == leader_id` antes de identificar carteiras; o
  conjunto tem dois `user_id` distintos ou um só (sem líder). Isso elimina o caso
  "liberar e comprometer a mesma linha" e a questão de ordem entre `−c` e `+a`.
- Compromissos em outros lotes: `committed` é global; subtrair `c` e somar `a`
  preserva o resto. Nunca atribuir `committed = a` nem `committed = 0`.
- Totais intocados. CHECKs são por linha; a ordem entre as duas linhas em F1 não
  importa.

## 6. Anti-sniping (AD-5)

Reuso de `evaluate_post_wallet`: `eligible.ends_at` = `lot.ends_at` lido sob a
trava; `accepted.ends_at` = esse valor `+ 2 min` se `0 < ends_at − now <= 2 min`,
senão o mesmo. A 3.4 só persiste `accepted.ends_at`; nunca calcula `now + 2 min`.
`now >= ends_at` → `lot_ended`, sem extensão, sem reabrir, sem liquidar (Q9 fica para
a 4.4). Serialização: o segundo lance lê o `ends_at` que o primeiro confirmou.

### 6.1 Instante: canônico × persistido × HTTP

- **Fonte única:** o `now` devolvido por `database_now` no passo 3. O `INSERT` grava
  `placed_at = now` explicitamente; proibido `server_default`, `now()` ou um segundo
  `clock_timestamp()` no `INSERT`.
- **Persistido:** `TIMESTAMPTZ` com microssegundos. Reler do banco devolve o mesmo
  instante (o fuso do objeto pode diferir; o instante não).
- **`CanonicalBid` (3.3):** `timestamp` normalizado para UTC e serializado sempre como
  `YYYY-MM-DDTHH:MM:SS.ffffffZ`, com seis casas, inclusive quando a fração é zero.
  Reconstruído do `placed_at` relido, produz os mesmos bytes e o mesmo hash.
- **HTTP:** `placed_at` e `ends_at` saem pelo serializer de `datetime` do Pydantic,
  em ISO 8601 UTC. O número de casas da fração **não** é contrato (fração zero pode
  sair sem fração). O cliente compara instantes, nunca strings com bytes canônicos.

## 7. Falhas e rollback

| Momento | Estado no banco | Resultado |
| --- | --- | --- |
| Antes de F1 (recusa, 409, 404, exceção) | Nenhuma escrita | Rollback; resposta |
| Entre F1 e F2 | `UPDATE wallets` pendente | Exceção → `with` de `get_session` desfaz → 500 |
| Entre F2 e F3 (antes da nova âncora) | + `INSERT bids` pendente | Idem |
| Depois de F3, falha **antes de o `COMMIT` ser enviado** | Tudo pendente | Idem; nada persiste (testado em A3) |
| Falha de conexão **depois de o `COMMIT` ser enviado** | Indeterminado para o cliente: o commit pode ter sido efetivado | O cliente recebe 500 ou erro de conexão. Limitação aceita nesta entrega; uma nova tentativa pode receber `already_winning`. Sem chave de idempotência nesta story |

Atomicidade é a da transação PostgreSQL; nenhuma compensação manual.

## 8. Taxonomia de erros

| Classe | Exemplo | HTTP | Onde |
| --- | --- | --- | --- |
| Entrada malformada | corpo inválido, `lot_id` não UUID, campo extra | 422 `validation_error` | FastAPI + handler existente |
| CSRF | origem ausente/diferente, não JSON | 403 / 415 | middleware |
| Autenticação/papel | sem sessão / `AUCTIONEER` | 401 / 403 | política |
| Lote inexistente | — | 404 `not_found` | rota (após rollback) |
| Recusa de negócio | `BidRefusal` | 422 `<código>` | rota |
| Integridade | `IntegrityConflict` | 409 `lot_integrity_conflict` | rota |
| Violação interna | CHECK/PK/UNIQUE depois do gate, `ValueError` fora do gate, `MissingWalletError`, deadlock, `DataError` | 500 `internal_error` | handler genérico; rollback pelo `with` |

Nenhuma exceção de banco vira recusa de negócio ou 409. A mensagem nunca carrega
detalhe criptográfico.

## 9. Observabilidade (logger `uvicorn.error`, como `lots.py`)

- 409: `logger.warning("bid refused: integrity conflict lot_id=%s reason=%s", lot_id, reason)`.
- Aceite (depois do commit): `logger.info("bid accepted: lot_id=%s sequence=%d anti_sniping=%s", ...)`.
- Recusa de negócio: sem log. Erro de banco/deadlock: traceback do caminho 500
  existente (`hide_parameters=True`; o `DETAIL` do PostgreSQL pode citar a linha,
  limitação herdada da 2.2).
- Nunca: segredos, HMAC, hashes, alias, `user_id`, e-mail, valores de carteira.
