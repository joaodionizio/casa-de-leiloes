# Arquivos previstos, critérios refinados e limites

## 1. Estado real e mapa da mudança futura

Inspecionei arquivos em 26/10/2026, sem banco/deploy, Git ou arquivos de segredos.
A última revisão encontrada é `0005_bids.py`; Lot não tem cancelled_at; cancel_lot
e rota cancel não existem. MyLots atual é uma lista somente de leitura; API mine
tem só items e usa LotResponse. `place_bid` já tem gate/lock/clock e rota com
commit/rollback; leituras públicas usam clock CTE, participação própria usa WHERE.

| Arquivo previsto | Mudança autorizada no build futuro |
| --- | --- |
| `backend/migrations/versions/0006_lot_cancellation.py` (novo) | Coluna e downgrade descritos em database-and-reads |
| `backend/app/lot_cancellation.py` (novo) | Tipos locais, cancel_lot, schema e registro da rota; imports do gate existente |
| `backend/app/lots.py` | Campo ORM, docstring de escritores, filtros públicos, DTO/leitura própria MyLots; não muda LotResponse de criação |
| `backend/app/bids.py` | Recusa após gate; filtros das duas leituras; gate permanece no lugar e inalterado |
| `backend/app/bid_rules.py` | Somente membro LOT_CANCELLED no enum; regras puras não mudam |
| `backend/app/errors.py` | Dois códigos e textos, neutralização D5; sem importar domínio para formar catálogo |
| `backend/app/seed.py` | Predicado e docstring excluem cancelados; restante do algoritmo preservado |
| `backend/app/main.py` | Import e chamada register_lot_cancellation_routes antes da SPA |
| `backend/tests/integration/test_lots_cancellation_migration.py`, `test_lot_cancellation.py`, `test_lot_cancellation_concurrency.py` (novos) | Migration, serviço/HTTP e C1/C2/C3 |
| `backend/tests/integration/test_public_lots.py`, `test_bid_reads.py`, `test_my_lots.py`, `test_seed.py`, `test_bid_routes.py` | Filtros, as_of, DTO, seed, lance cancelado e texto neutro |
| `backend/tests/test_openapi.py`, `test_access_policy.py`, `test_errors.py`, `test_bid_rules.py` | Contratos pinados, enum/catálogo, política |
| `backend/tests/lot_support.py`, `tests/integration/test_lots_migration.py`, `test_bids_migration.py`, `test_database.py` | Ajustar apenas expectativas reais de nova coluna/revisão e suporte ao recorder; não afrouxar schema anterior |
| `frontend/src/api/lots.ts`, `lotCancellation.ts` (novo), respectivos `.test.ts` | Read model próprio, cancelLot e lógica pura |
| `frontend/src/MyLots.tsx`, `App.css` | Selo, CTA, confirmação inline, envio/feedback/refetch/foco; CSS mínimo |
| `frontend/src/api/bids.ts`, `bidFeedback.ts`, respectivos testes | Único novo código/mensagem da sala |
| `frontend/e2e/my-lots.spec.ts` (novo), `lot-room.spec.ts`, `support/mockApi.ts` | DOM/requests, mock contratos/estado e nova recusa |
| README, `docs/uso_de_ia.md`, story 3.6, sprint-status | Documentação/evidências no build; nenhum deles é alterado nesta rodada |

`wallet.py`, `bid_integrity.py`, `lot_time.py`, `LotPage.tsx`, countdown, runRound,
barreira da sala, arquitetura, dependências e configuração de segredos não precisam
de alteração. Não escrevo implementação nem abro arquivo `.env*` para confirmar isso.

No build, README explica: cancelar só sem bids antes do fim; cancelado público
404 e dono mantém lista; legado sem âncora incancelável; demo cancelado permite
novo demo no boot; cancelled_at fora da âncora; sala aberta sem aviso automático. Nota junto a essa limitação: após `lot_cancelled` a mensagem imediata é “Este lote foi cancelado.”; uma leitura posterior responde 404 (D3) e a UI pode mostrar “Lote não encontrado.”, sem indicar falha do cancelamento; sem `phase=cancelled`, sem mudança em `LotPage`.
Registro IA e resultados reais, mantendo story/sprint coerentes. `deferred-work.md`
só recebe dívida concreta surgida; não invento trabalho Epic 4 nem mudo AD.

## 2. Critérios refinados

| Critério | Demonstração exigida |
| --- | --- |
| AC1 / CAP-1 | Owner cancela scheduled/live íntegro sem bids e antes do fim; 200 exato, instante pós-lock, um UPDATE somente cancelled_at |
| AC2 / CAP-2 | Policy barra BIDDER/visitante; outro owner 403 antes do gate; UUID/not-found seguem infraestrutura; matriz de precedência preservada |
| AC3 / CAP-2 | Gate obrigatório antes de count e idempotência; legado/adulterado 409 neutro, zero efeitos, nenhum repair |
| AC4 / CAP-2 | Repetição íntegra mantém timestamp e faz zero DML, inclusive após fim; adulterada nunca retorna 200 |
| AC5 / CAP-1 | Com bids 422 lot_has_bids; sem bids ended/igualdade 422 lot_ended; wallets e chain intactas |
| AC6 / CAP-3 | C1/C2 provam espera real em ambas as ordens; C3 só deixa estados permitidos; oráculo completo consistente |
| AC7 / CAP-4 | Cancelado some da vitrine e recebe 404 nas três leituras; as_of existe quando todos são cancelados; GET puro |
| AC8 / CAP-4 | MyLots mantém cancelado e todos campos atuais, adiciona cancel/time/count, sem quarta fase; 201 de criação intacto |
| AC9 / CAP-5 | CTA visual correto, inline e teclado, sem double submit/retry, sucesso/refetch/selo; business por código e ambíguo conservador |
| AC10 / CAP-6 | Seed ignora cancelado sem reativá-lo, cria somente quando falta outro demo válido e não duplica em boot repetido |
| AC11 / CAP-6 | POST bids cancelado após gate retorna 422 lot_cancelled e zero efeitos; sala mapeia só a nova recusa |
| AC12 / transversal | 0005→0006→0005→0006 correto, sem índice/default/backfill; schema/políticas pinados e M1–M8 cobertos por testes que falham no mutante |

## 3. Edge cases fechados

- `now==ends_at`: primeiro cancelamento recusa; instante lido depois da espera,
  não quando request chegou. Scheduled válido também pode cancelar.
- Já cancelado íntegro e agora ended: 200 original. Já cancelado com count/histórico
  íntegros mas bids injetados e assinados validamente: segue precedência D2; não
  invento CHECK de estado nem outra regra antes da idempotência. O runtime atual
  não cria esse estado; alterações fora do modelo de ameaça não são reparadas.
- Outro owner + adulterado/cancelado: 403, sem revelar integridade. BIDDER recebe
  403 antes do serviço mesmo se o lote inexiste.
- Legacy sem âncora e zero bids: 409, não se cancela nem recebe bootstrap. Público
  continua podendo vê-lo enquanto não cancelado; o gate não é aplicado aos GETs.
- Cancelado adulterado só no timestamp: âncora não cobre esse campo; o gate não
  promete detectar isso. Anchor/chain adulteradas: 409 nos dois POSTs.
- Lista administrativa vazia ou composta só de cancelados: as_of válido; cancelado
  pode ter phase scheduled/live/ended, selo Cancelado prevalece.
- Erro antes de commit: rollback integral. Erro após envio de commit: resultado
  ambíguo para cliente, uma releitura e nenhuma repetição automática.
- Read model antigo pode exibir CTA enquanto um lance entra: backend recusa
  lot_has_bids, a UI relê; botão não substitui a trava/gate.
- Somente demo cancelado aberto no tempo: não conta, outro pode nascer no boot;
  cancelar não aciona seed nem muda o lote antigo.
- Leitura iniciada antes do commit pode ver snapshot anterior; sala aberta não é
  avisada automaticamente; não acrescento transporte ou polling.

## 4. Decisões restantes e escopo

**Decisões abertas restantes: nenhuma.** Nomes, tipos, imports, timezone, posição
dos filtros e sincronização dos testes estão fechados pelos companions dentro
das D1–D7 e do código real. Não há suposição de produto pendente para build.

Incluo apenas Story 3.6. Excluo cancelamento com bids/estorno, wallet mutation,
liquidação/fechamento/resultado, auditoria pública, busca/filtro, WebSocket e
Epic 4. A menção a limitações/dependências futuras não cria tarefas dessas stories.
Nenhuma state machine, service framework, repository nova ou commands genéricos.

**Veredito: PRONTA PARA BUILD.** Significa contrato pronto para implementação
futura autorizada, não código pronto nem autorização implícita para iniciar build.
