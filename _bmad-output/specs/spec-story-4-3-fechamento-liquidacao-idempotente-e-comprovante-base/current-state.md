# Estado atual e mapa do futuro build

## Fontes e autoridade

Retomei a memória canônica e o pacote draft e li o pedido de consolidação humana de 27/10/2026. Ele decide QH-01–10, substituindo recomendações do draft; CAP-1–5 permanecem estáveis. Na criação, li CLAUDE, ARQUITETURA, README, FRONTEND-WORKFLOW, DESIGN/EXPERIENCE, stories 4.1/4.2, evidência cumulativa, uso_de_ia e sprint; epics §4.3 e contratos/código do Epic 3 fundamentaram o estado observado.

Nesta consolidação reconferi CLAUDE, tracking, registros anteriores e identidade real de Bid e Session. Pedido/story > ADs > UX > protótipo; a AD-5 vigente continua E+2min cumulativa, sem teto. Os registros intermediários now+2min são históricos revogados. Não altero as stories 4.1/4.2 nem atribuo aprovação final nova aos seus status review.

## Brownfield relevante

| Fonte local | Estado existente | Contrato final 4.3 |
| --- | --- | --- |
| bids.py place_bid | Reserva só líder, libera superado na transação | Sem segunda liberação de perdedores ou cobrança do disponível |
| bids.py authenticate_previous_state/read_history | Gate completo, HMAC/count/hash, líder/alias/valor ligados ao último bid | Reutilizar antes de liquidar e na revalidação idempotente |
| bids.py Bid | PK composta lot_id/sequence, sem coluna id | winning_bid_id conceitual vira winning_bid_sequence + lot_id/FK composta; sem alterar bids |
| wallet.py Wallet/lock_wallet | T/C agregados, populate_existing, CHECK imediata | UPDATE conjunto T−F/C−F e crédito +F, mantendo reservas de outros lotes |
| wallet.py ensure_wallets/money.py | Carteira já existe para todos, inclusive AUCTIONEER; MAX=9007199254740991 | Não criar carteira na venda, não aumentar teto; conflito financeiro com rollback |
| lots.py/lot_time.py | Fase temporal; leader/price/count/âncora e cancelled_at | lot_settlements separado é autoritativo, sem mudar phase |
| lot_cancellation.py/Story 3.6 | Cancelado terminal, públicos 404 | Não converter em unsold; impedir recancelamento de terminal liquidado |
| lot_room.py/stories 4.1/4.2 | Reader curto/threadpool, manager em memória e heartbeat sem SQL | Sem nova publicação, payload, máquina ou UI |
| db.py | Session síncrona, expire_on_commit=False; dependência sem commit automático | Comando interno coordena Session própria/commit; helper compõe sem commit |
| Testes de concorrência do Epic 3 | Event/conexões/lock real e estado final | Testar comando diretamente; sem rota técnica ou mocks de locks |

Não existe nova contabilidade a inventar: settlement registra transferência do modelo atual; receipt separado apenas a representa com dados públicos. Persistência futura de ambos só significa liquidação depois do commit; esta sessão não cria tabelas nem registros no banco.

## Arquivos prováveis no build autorizado

| Área | Mudança necessária |
| --- | --- |
| backend/app/lot_settlement.py | Comando settle_lot e helper de preparo, modelos lot_settlements/receipts, DTOs/conflitos/readers internos; sem registro de rota |
| backend/migrations/versions/ | Próxima revisão após conferir head no build: IDs UUID, UNIQUE lot_id em ambas, UNIQUE settlement_id receipt, FKs compostas/CHECKs finais; sem backfill liquidando ou reassinando legado |
| backend/app/bids.py, lot_cancellation.py | Preservar gate/locks/canonical; proteção do terminal settlement contra reabertura/recancelamento; categorias de integridade necessárias, sem catch-up |
| backend/app/wallet.py, money.py | Reutilizar contratos/locks/teto; nenhuma API de leiloeiro, ledger ou criação de carteira no fechamento |
| backend/tests/integration/ e backend/tests/ | Serviço direto, schema/concorrência/falhas/privacidade/readers e regressões; adaptar limpeza às novas FKs sem CASCADE |
| main.py, frontend/, scripts/start.sh, manager WS | Nenhuma nova rota/gatilho/UI/evento por esta story; não mexer por conveniência de testes |
| Story/spec/sprint, docs/uso_de_ia.md e README no build | Registrar contrato consolidado e, só quando executadas, evidências de testes |

QH-01–10 fechadas, sem escolhas de API ou exposição pública remanescentes. O mecanismo operacional do teto/scheduler/evento continua na 4.4, não é impedimento pendente da 4.3. Ready-for-dev registra somente prontidão documental; testes de aplicação/verify aguardam build separado.
