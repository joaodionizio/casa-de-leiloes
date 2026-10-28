# Baseline e integração da Story 4.4

Retomei a memória e decisões humanas de 27/10/2026. A 4.3 está done;4.1/4.2
mantêm review no sprint. Epic 4 in-progress,4.5 backlog. Esta consolidação
prepara apenas a 4.4, sem código/testes de aplicação ou mudança de outras stories.

| Fonte real consultada | Evidência | Integração final |
| --- | --- | --- |
| backend/app/lot_settlement.py | Comando dono de Session/commit, quatro statuses e DTO imutável | Consumir confirmação, sem finanças/locks/commit duplicados |
| Readers 4.3 | Settlement/receipt por lote com coerência estrutural, sem escrita | Projeção pública coerente sem nova auditoria ou repair |
| backend/app/lots.py | ends_at/starts_at/cancelled_at; sem coluna active; lock força releitura | Seleção por predicados reais, autoridade final no comando |
| backend/app/bids.py | Rota reverte recusa e não chama settlement | Preservar por QH-14; alterar só read model compartilhado, sem novo gatilho/erro HTTP |
| backend/app/lot_room.py | Manager por app, coordenação por lote, fila 8, sender único, limiter 4 | Reusar terminalização/filas/isolamento e estender snapshot/evento |
| Mesmo módulo | lot_cancelled drena e fecha 1000, novos cancelados recusados | Settlement usa drenagem compatível; settled novo recebe snapshot antes de close |
| Mesmo módulo/4.2 | Ping sem SQL, silêncio 60 s, send/close 10 s | Preservar, sem timeout 2 s adicional |
| backend/app/main.py | Sem lifespan de settlement; rotas/manager registrados | Lifecycle assume catch-up/loop, nenhuma task em import/create_app |
| backend/scripts/start.sh | Migrations → seed → exec uvicorn, um processo | Preservar script e seed externos; catch-up só depois, no lifespan |
| backend/app/seed.py | Seed idempotente, advisory lock, fixture offline | Não mover/repetir/alterar regras |
| backend/app/db.py | Factory sync, engine lazy, pool_pre_ping/hide_parameters, sem limites explícitos do scheduler | Preservar limites existentes; Session nasce/fecha no worker, engine compartilhado não é descartado pelo scheduler |
| frontend/src/lotRoomSocket.ts | Parser desconhece lot_closed; igualdade count/as_of não inclui resultado | Estender tipos/igualdade/arbitragem para terminal com count igual |
| frontend/src/lotConnection.ts | Snapshot primeiro inicia ping, terminal só cancelamento/stop | Snapshot settled encerra antes de ping/reconnect, gerações 4.2 preservadas |
| frontend/src/LotPage.tsx | Cancelamento separado e stale público/privado | Sem nova UI de resultado; terminal não se transforma em cancelamento ou limpa erros privados |

Fontes retomadas: CLAUDE, ARQUITETURA, README, sprint, docs/uso_de_ia,
EVIDENCIA-ANTI-SNIPING-CUMULATIVO, stories 4.1/4.2/4.3 e spec 4.3 (SPEC,
transaction-contract, data-contracts, concurrency-model, implementation-evidence).
Usei também epics 4.4 e os documentos DESIGN/EXPERIENCE/FRONTEND-WORKFLOW já
adotados; o histórico de builds não é resultado executado nesta consolidação.
Testes de referência permanecem test_lot_room.py, test_lot_room_ws.py,
test_lot_settlement.py e test_lot_settlement_concurrency.py com barreiras PG reais.

## Revisões documentais explícitas

QH-02/13/14 substituem a ordem antes-do-seed e o gatilho de POST das antigas
Q4/Q9/AD-19. Registrei essa revisão em ARQUITETURA antes de derivar o contrato,
e sincronizei os resumos CLAUDE/épico/README. Não alterei stories 4.1–4.3 ou seus
contratos históricos; a direção normativa atual está na AD-19 revisada e nesta
spec. QH-04 acrescenta as_of derivado de settled_at; QH-16 rejeita limites novos.

## Mapa do build futuro, ainda não autorizado

| Área | Arquivos prováveis | Limite |
| --- | --- | --- |
| Orquestração | novo backend/app/settlement_scheduler.py e main.py | Catch-up/loop/seleção/retry/lifecycle; start.sh/seed existentes preservados |
| Settlement 4.3 | lot_settlement.py como dependência | Sem mudar regra, assinatura, commit/DTO ou finanças |
| Sala/read model | lot_room.py e leituras em bids.py | Whitelist pública/snapshot/terminal; rota de lance não passa a fechar |
| Cliente mínimo | api/bids.ts, lotRoomSocket.ts, lotConnection.ts, LotPage.tsx | Tipos/parser/terminal/cleanup; sem nova tela ou UX de resultado |
| Verificação | testes scheduler/lifecycle, PG/WS/TS/E2E existentes | Oráculos definitivos em acceptance-and-tests; nenhum teste executado agora |
| Documentação | README, story/spec, uso de IA | Distinguir contrato pronto de funcionalidade ainda não implementada |

Nenhum arquivo de código dessa tabela foi alterado nesta consolidação.
