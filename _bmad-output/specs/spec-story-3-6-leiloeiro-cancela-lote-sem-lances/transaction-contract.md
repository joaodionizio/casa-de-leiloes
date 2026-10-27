# Fluxo transacional, integridade e concorrência

## 1. Módulo e tipos previstos

Decidi criar somente `backend/app/lot_cancellation.py`, no padrão de módulos do
projeto. Descartei colocar o serviço em `lots.py`: `bids.py` já importa `lots.py`.

| Origem real | Imports do novo módulo |
| --- | --- |
| `app.lots` | `lock_lot`, `database_now`, `get_integrity_config` |
| `app.bids` | `read_history`, `authenticate_previous_state`, `IntegrityConflict` |
| `app.config` | `IntegrityConfig` |
| `app.access` | `api_route`, `AccessPolicy`, `require_auctioneer`, `NO_STORE` |
| `app.db` | `get_session` |
| `app.errors` | `error_response`, `error_responses`, `LOT_INTEGRITY_CONFLICT` |
| `app.users` | `User` |

Tipos locais simples: `CancelledLot` dataclass frozen com `id: UUID` e
`cancelled_at: datetime`; `CancellationRefusal` StrEnum com `FORBIDDEN="forbidden"`,
`LOT_HAS_BIDS="lot_has_bids"`, `LOT_ENDED="lot_ended"`; `CancelLotResponse` do contrato
HTTP. Serviço `cancel_lot(session: Session, *, lot_id: UUID, auctioneer_id: UUID,
integrity: IntegrityConfig)` retorna `CancelledLot | CancellationRefusal |
IntegrityConflict | None`. `None` é lote inexistente. Sem hierarquia de commands.

`main.create_app` importa/registra `register_lot_cancellation_routes` depois de
`register_bid_routes` e antes das rotas SPA. `lots.py` e `bids.py` não importam
`lot_cancellation` nem `main`. O grafo continua acíclico; o seed pode importar
`lots.py` sem carregar a aplicação. `/mine` continua antes de `/{lot_id}`.

## 2. Sequência obrigatória

Rota captura `auctioneer_id=user.id` e chama `session.rollback()` para encerrar a
leitura da autenticação, como o POST de lance. A próxima instrução abre a
transação de escrita implicitamente em READ COMMITTED.

| Passo | Operação real | Recusa/efeito |
| --- | --- | --- |
| 1 | `lot=lock_lot(session,lot_id)` | SELECT só em lots, FOR UPDATE e populate_existing; ausente retorna None |
| 2 | `now=database_now(session)` | Um único `clock_timestamp()` depois de adquirir o lock; UTC |
| 3 | Comparar `lot.auctioneer_id` com ID capturado da sessão | FORBIDDEN antes do gate |
| 4 | `rows=read_history(session,lot_id)` | Colunas de bids, histórico completo ordenado; statement posterior ao lock |
| 5 | `authenticate_previous_state(lot,rows,integrity=integrity,lot_id=lot_id)` | IntegrityConflict interrompe sem escrita |
| 6 | `lot.cancelled_at is not None` | CancelledLot com timestamp original; nenhuma atribuição/flush/UPDATE |
| 7 | `authenticated.bid_count > 0` | LOT_HAS_BIDS; nunca decidir com count cru |
| 8 | `now >= lot.ends_at` | LOT_ENDED; igualdade já encerrou |
| 9 | Atribuir somente `lot.cancelled_at=now`; `session.flush()` | Um UPDATE lots SET cancelled_at, sem outra coluna |
| 10 | Retornar CancelledLot; rota faz `session.commit()` | Só depois do commit retorna 200 |

Serviço não commita nem faz rollback. Em None, forbidden, IntegrityConflict e
recusa de negócio, rota faz rollback antes da resposta, liberando a trava. Sucesso
idempotente também encerra a transação com commit, sem DML. `expire_on_commit=False`
da factory real permite montar DTO depois. Exceção antes do commit enviado desfaz
a escrita pelo contexto de `get_session`; erro após envio do COMMIT tem resultado
indeterminado para o cliente. Não faço compensação ou retry automático.

Nenhum SELECT/lock em wallets, nenhum UPDATE/INSERT/DELETE em wallets ou bids,
nenhuma atribuição em `ends_at`, `current_bid_cents`, `current_leader_id`,
`bid_count`, `final_hash` ou `anchor_hmac`. O único instante do passo 2 também é
o persistido e respondido; nem hora Python, relógio do browser, now() transacional,
segundo clock_timestamp, default de coluna ou timestamp novo no re-cancelamento.

## 3. Gate obrigatório e limites

Reutilizo o gate completo: âncora/HMAC, cadeia para o lote, vínculo count/final_hash
e líder/lance atual ao último evento. O gate existente reconstrói `AnchorState`
e `CanonicalBid`; o cancelamento apenas fornece o lote travado, rows e config.
Não copio nem movo essa lógica. Falha estrutural tratada pelo gate, cadeia alterada,
truncamento, resumo falso ou âncora nula retornam o mesmo 409, sem repair, re-sign
ou bypass. Razão só no logger `uvicorn.error`, com lote e categoria, sem usuários,
alias, valores, hashes, HMAC ou segredo; recusa de negócio não exige log novo.

Âncora v1 continua somente `(v,lot_id,bid_count,final_hash)`. `cancelled_at` não é
autenticado; edição direta apenas dele pode esconder/reexibir um lote sem disparar
o gate, limitação aceita em D2/D6. “Cancelado adulterado → 409” significa alteração
detectável pelo gate, não uma promessa de autenticar o marcador. Ownership e
termos, incluindo `ends_at`, também não são autenticados pela v1. Legado sem
âncora continua incancelável, sem assinatura automática ou comando administrativo.

## 4. Serialização cancelar × primeiro lance

Os serviços disputam a mesma linha por `lock_lot`. Enquanto A não confirma, B
espera. Em READ COMMITTED, o FOR UPDATE de B retorna a versão confirmada mais
recente; `populate_existing` sobrescreve o objeto eventualmente carregado antes.
O `read_history` seguinte vê o commit anterior. Não uso um snapshot de histórico
anterior à espera nem libero lock antes de completar a operação.

| Ordem serial | Cancelamento | Lance | Estado final permitido |
| --- | --- | --- | --- |
| Cancelamento primeiro | 200, timestamp gravado | Gate íntegro, depois 422 lot_cancelled | cancelado; zero bids/count; líder/atual null; genesis/âncora original; carteiras originais |
| Lance primeiro | Gate autentica um bid, depois 422 lot_has_bids | 201 pelo serviço real | cancelled_at null; exatamente um bid; líder/atual do bid; count 1; âncora válida; comprometido incrementado só pelo lance |

Lote de teste ao vivo com fim distante, primeiro lance válido e carteira suficiente
isolam a disputa de recusas temporais/saldo/anti-sniping. Nunca aceito ambos os
sucessos, cancelado com bid, bid aceito sem comprometido ou contagem/âncora parcial.
Cancelar usa só a trava do lote, logo não adiciona ciclo de carteiras ao AD-8.
Fila de lock e ausência de timeout/retry do runtime permanecem limites da 3.4.
O teste determinístico e o oráculo completo estão em `test-plan.md`.
