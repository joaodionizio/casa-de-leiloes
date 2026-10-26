# Estado atual (código lido em 26/10/2026) — Story 3.4

Leitura de arquivos, sem execução de teste, banco ou deploy. Sem `.env*`.

## 1. O que existe e é reusado sem mudança

| Peça | Arquivo | Uso na 3.4 |
| --- | --- | --- |
| `database_now(session)` | `app/lots.py` | Único `clock_timestamp()` da operação, em UTC |
| `lock_wallet`, `available_cents`, `wallet_response`, `MissingWalletError` | `app/wallet.py` | Trava `FOR UPDATE` + `populate_existing`; disponível; DTO da carteira; carteira ausente = 500 |
| `evaluate_pre_wallet`, `evaluate_post_wallet`, `LotBidState`, `CurrentBid`, `BidAttempt`, `BidRefusal`, `BidAccepted` | `app/bid_rules.py` | Regras e anti-sniping (intocado) |
| `GENESIS_HASH`, `CanonicalBid`, `AnchorState`, `VerifiableBid`, `generate_bidder_alias`, `compute_bid_hash`, `compute_anchor_hmac`, `verify_anchor_hmac`, `verify_bid_chain` | `app/bid_integrity.py` | Gate e nova âncora (intocado) |
| `Cents`, `MAX_CENTS` | `app/money.py` | Corpo e literais da migration |
| `api_route`, `AccessPolicy.BIDDER`, `require_bidder`, `NO_STORE` | `app/access.py` | Política da rota |
| `error_response`, `error_responses`, `MESSAGES` | `app/errors.py` | Envelope; ganha 6 códigos |
| `ApiWriteGuardMiddleware` | `app/csrf.py` | 403/415 antes da rota, sem mudança |
| `get_session` | `app/db.py` | `Session` por requisição, sem commit; o `with` desfaz em exceção |
| `pg_advisory_xact_lock` | `app/seed.py` | Serializa seeds |

## 2. O que muda

| Peça | Hoje | Depois |
| --- | --- | --- |
| `Lot` | 19 colunas, sem estado de lance | +5 colunas e 8 CHECKs, +1 FK (`database-schema.md`) |
| `create_lot` | sem âncora | exige `audit_hmac_secret`, grava âncora vazia |
| `seed.run_seed`/`seed_demo_lot` | só `DATABASE_URL`; predicado `is_demo AND ends_at > now` | exige `audit_hmac_secret`; predicado `+ anchor_hmac IS NOT NULL` |
| `create_app` | origem, JWT | + `IntegrityConfig` em `app.state`; registra a rota de lance |
| `config.py` | `AuthSettings` | + `AuditSettings`, `IntegritySettings`, `IntegrityConfig` |
| `bids` | não existe | tabela, ORM, serviço, rota |

## 3. Fatos do código que condicionam o desenho

- A política (`require_bidder`) carrega o `User` pela mesma `Session` da rota antes
  do handler: a transação já começou (autobegin). D5 faz `rollback()` antes do
  serviço.
- `app/main.py` executa `app = create_app()` no import: os testes precisam dos dois
  segredos no ambiente **antes** de importar `app.main` (como o `JWT_SECRET`).
- `create_session_factory` usa `expire_on_commit=False`: os objetos travados
  continuam legíveis depois do commit para montar a resposta.
- `create_db_engine` usa `hide_parameters=True`; o `DETAIL` de uma CHECK ainda pode
  levar a linha ao log do servidor (precedente da 2.2, P16).
- `MESSAGES` é catálogo fechado: `error_response` com código ausente levanta
  `KeyError` (500). Os seis códigos novos precisam estar nele.
- `tests/conftest.py` faz `TRUNCATE wallets, lots, users` e `TRUNCATE lots` sem
  `CASCADE`: com `bids` referenciando `lots` e `users`, os dois falham até incluir
  `bids`.
- `test_lots_migration.py` desempacota uma única FK de `lots` e fixa nulabilidade e
  nomes de CHECKs: muda com a `0005`.
- `test_bid_rules.py` afirma que os códigos de recusa **não** estão em `MESSAGES`
  ("o contrato HTTP nasce com o endpoint"); `test_errors.py` fixa `MESSAGES` literal.

## 4. Mapa de escritores (premissa "toda escrita passa pela trava do lote")

Busca por `UPDATE`, `DELETE`, `insert(`, `session.add` e atribuições em `Lot` em
`backend/app`: hoje nenhum caminho atualiza `lots`; nenhum toca `bids` (não existe).

| Dado | Escritor depois da 3.4 | Sob a trava do lote? |
| --- | --- | --- |
| `bids` (`INSERT`) | só `app.bids.place_bid` | Sim (passo 2) |
| `bids` (`UPDATE`/`DELETE`) | nenhum | — |
| `lots.bid_count`, `final_hash`, `anchor_hmac` | `create_lot` (`INSERT` de lote novo, id `uuid4` do servidor) e `place_bid` | `INSERT` de linha nova não tem concorrente; `place_bid` sim |
| `lots.current_bid_cents`, `current_leader_id` | só `place_bid` | Sim |
| `lots.ends_at` | `create_lot` (`INSERT`) e `place_bid` | Sim |
| `wallets.committed_balance_cents` | só `place_bid` | Lote, depois carteiras (AD-8) |
| `wallets.total_balance_cents` | `deposit` (trava só a carteira) | Não precisa: não toca lote nem comprometido |
| Migration `0005` | `ADD COLUMN` com default | DDL (`ACCESS EXCLUSIVE`), antes do servidor (`start.sh`) |
| Testes | SQL direto em `bid_support`/`lot_support` para montar e adulterar | Só testes |

**Nenhum caminho existente viola a premissa: sem BLOCKER.**

## 5. Obrigações futuras (fora do escopo da 3.4; registrar em `deferred-work.md` no build)

Nada abaixo é implementado nem desenhado na 3.4; são condições para as stories
citadas não reabrirem os riscos fechados aqui.

- **Gate compartilhado (SR-08 B).** 3.6, 4.3 e 6.6 reutilizam a **mesma**
  implementação do gate da 3.4 (ou uma extração compartilhada feita quando a
  primeira delas for implementada). Não duplicar a lógica. Na 3.4 o gate fica em
  `bids.py`, sem API pública prematura.
- **3.6 (cancelar sem lances):** trava o lote; decide "sem lances" com `bid_count`
  autenticado pelo gate; só escreve a coluna de cancelamento; acrescenta
  `cancelled_at IS NULL` ao predicado do seed (já registrado).
- **4.3 (liquidação):** trava o lote, roda o gate antes de usar líder/lance atual,
  trava carteiras (vencedor, leiloeiro) em `user_id` crescente; nunca escreve em
  `bids`; comprovante usa `bid_count`/`final_hash` autenticados.
- **Estado terminal (SR-08 A), 4.3 e 6.6:** definir marcador terminal persistido (ou
  equivalente) para que, depois de liquidar ou estornar, nenhum `place_bid` posterior
  libere de novo o comprometido do líder. A 3.4 não cria coluna terminal.
- **`auctioneer_id` (SR-08 D), 4.3:** a liquidação credita o leiloeiro por
  `lots.auctioneer_id`, que a âncora v1 não cobre. Risco a tratar no desenho da 4.3;
  `CanonicalBid` v1 não muda.
- **6.6 (estorno):** mesmo gate antes de liberar o comprometido do líder; mesma ordem
  de travas; histórico intocado.
- **4.4 (Q9):** se fechar dentro da tentativa de lance, fecha em transação própria
  antes; nunca trava carteira antes de lote.
- **5.1 (auditoria pública, SR-08 C):** ler lote e `bids` num snapshot coerente. Em
  `READ COMMITTED`, dois statements separados podem ver um lance confirmado entre
  eles e acusar falso positivo. Usar um statement único, uma transação
  `REPEATABLE READ` somente leitura, ou solução equivalente.
