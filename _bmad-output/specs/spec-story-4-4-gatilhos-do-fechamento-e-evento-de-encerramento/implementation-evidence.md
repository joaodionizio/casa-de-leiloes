# Evidência de implementação — Story 4.4

Data: 28/10/2026. Implementei somente gatilhos do fechamento e evento terminal,
a partir de QH-01–16 aprovadas. Mantive o review independente para outra sessão;
não executei Git, não li `.env*` e não iniciei a Story 4.5.

## Arquitetura e lifecycle

Decidi seguir o contrato aprovado: `migrations → seed existente → lifespan/catch-up
→ scheduler → tráfego`. Preservei `backend/scripts/start.sh` e o seed byte a byte.
`main.py` cria o owner no lifespan; `create_app` e imports não iniciam tasks.
Catch-up termina sua passagem finita antes do yield. Start é idempotente; a task
periódica espera 2 s após catch-up/cada ciclo, com espera interrompível e guard
SKIP sem fila. Falha individual permite o próximo lote; falha sistêmica na
descoberta impede startup com cleanup.

Sessions síncronas nascem/fecham no worker. Registrei workers, ciclos, publicações,
leituras e handlers/coordenação da sala. Shutdown marca stopping antes de await,
impede admissão e acorda a espera; a janela global é 30 s. Se excedida, registra
pendências e continua acompanhando os recursos até cleanup seguro. Não cancelei
threads para afirmar rollback nem descartei engine em uso. O teste retém COMMIT
PostgreSQL real; apenas a janela operacional é reduzida no harness para observar
excesso sem esperar 30 s reais. Send/close continuam 10 s, limiter de leituras 4,
fila por socket 8, silêncio 60 s.

## Descoberta, cursor e falhas

`open_scan` captura cutoff PostgreSQL e fronteira superior `(ends_at,id)` em um
statement com clock materializado. `read_page` seleciona não cancelados, vencidos
e sem `lot_settlements`, por `(ends_at,id)`, sem OFFSET/locks e com até 50 linhas
por página. Cada ciclo lê até 200 linhas retornadas e tenta até 50 comandos;
cooldown não conta como tentativa. Cursor avança só sobre linhas examinadas,
incluindo skips/falhas; resto da página é reconsultado. No fim, a próxima rodada
renova a fronteira; catch-up não faz wrap na população inicial.

Usei somente `settle_lot(factory, lot_id=..., integrity=...)`, sem passar prazo ou
relógio da seleção. Preservei o arquivo 4.3 byte a byte: lock, clock pós-lock,
gate, dinheiro, receipt e commit continuam exclusivamente nele. `not_due` segue
normal sem cooldown/evento; `already_settled` não republica. Só statuses novos
sold/unsold com `transitioned=true`, validados após retorno confirmado, permitem
uma task de publicação. Não há transação financeira durante publicação.

Integridade, teto/conflito financeiro, carteira ausente e constraint persistente
recebem cooldown monotônico local 300 s. Falhas operacionais recebem backoff
2/4/8/16/30 s por ID; indisponibilidade global encerra rodada e aplica recuo global.
Não há retry imediato na transação, reparo ou evento por inferência de commit.
Logs seguros incluem source, status/categoria, contagens, SKIP, limite/backlog,
duração e excesso da drenagem, sem texto bruto de exceção/SQL/dados privados.

## Contratos e transporte

`lot_closed` tem exatamente nove campos obrigatórios:

```text
type, lot_id, outcome, winner_alias, final_amount_cents,
bid_count, final_hash, settled_at, as_of
```

`type="lot_closed"`, outcome sold/unsold e `as_of=settled_at` persistido, inclusive
microssegundos; builder não lê clock. Sold usa alias/valor persistidos; unsold usa
null/null, count 0/genesis e nenhum receipt. Não serializei DTO interno,
`winner_user_id`, e-mail, wallet, HMAC ou segredos.

REST `/api/lots/{id}/bids` e WS compartilham `settlement_status` pending/settled e
`settlement` null ou seis campos públicos do resultado. `phase` continua temporal;
`room.as_of` é da leitura. Um statement lê lote, janela de 50 bids e par
settlement/receipt; reaproveita coerência estrutural 4.3, sem lock/escrita/auditoria
criptográfica ou repair. Cancelado continua REST404/handshake recusado.

Conectados recebem terminal na fila, drenam e fecham 1000. Nova conexão settled
recebe snapshot terminal primeiro, depois 1000, sem settlement no handshake.
Publicação falha preserva finanças, loga e tenta invalidar a sala/fechar de forma
recuperável; marcador considera subscribe antigo em andamento. Não há outbox,
replay periódico ou republicação em already_settled.

O cliente valida whitelist/outcome, conserva terminal contra pending tardio,
contagem igual e resultado divergente; `sameRoomState` inclui settlement.
`shouldApplyRoom` continua arbitragem pública, sem estado de conexão. Terminal
cancela heartbeat/pong/retry e autoridade da geração; callbacks antigos permanecem
inertes. Evento esparso preserva a janela conhecida e pede uma leitura pública
final, sem condicionar terminal a ela nem limpar erro privado. Ajustei apenas
supressão do formulário e avisos de conexão em terminal; nenhuma UI de resultado,
link, painel ou fluxo 4.5 foi criado.

## Testes e comandos

Usei PostgreSQL 18 dedicado `_test`, migrations existentes e guardas externas
Python/Node/uv/Compose para impedir dotenv implícito. Os testes legados substituem
somente o adaptador de lifecycle da app; testes `settlement_lifecycle` exercitam
catch-up/startup reais. Não introduzi switch de produção para desligar scheduler.
Não executei suítes PG em paralelo sobre o mesmo schema.

A suíte consolidada 4.4 + 4.1/4.2/4.3 + AD-5 executou **551 passed, 1 warning in
35.29s**. A prova adicional de restart sem publicação executou **2 passed, 1
warning in 0.53s**. A camada operacional isolada executou **14 passed, 1 warning
in 4.95s**, incluindo 10 casos concorrentes, justiça real com 225 lotes e 3
ordens/falhas de shell. Esses números se sobrepõem e não devem ser somados como
cobertura independente. A suíte nova tem 40 execuções backend; os 40 cenários
semânticos abaixo também usam regressões e provas TS/E2E.

A rodada final exclusiva da 4.4 executou **40 passed, 1 warning in 7.47s**;
as 40 execuções incluem parametrizações e complementam a matriz semântica.

### Matriz T01–40

Todos os testes citados são executados pelo verify final; não trato um teste
apenas planejado ou skip como prova. Prefixos: U=`backend/tests/test_settlement_scheduler.py`,
P=`backend/tests/integration/test_settlement_scheduler.py`,
C=`backend/tests/integration/test_settlement_scheduler_concurrency.py`,
R=`backend/tests/integration/test_settlement_restart_recovery.py`.

| ID | Prova executada |
| --- | --- |
| T01 | P `persisted_result`, variante sold; C duas chamadas com carteiras/receipt únicos |
| T02 | P `persisted_result`, variante unsold; smoke sem receipt |
| T03 | P `candidates_recheck`; U só transição confirmada; C bid-first |
| T04 | P `candidates_recheck`; R startup misto cancelado |
| T05 | P retry/comando explícito sem publicação; R exclui settled na retomada |
| T06 | P lifespan com 53 pendentes; R startup misto sold/unsold |
| T07 | P apps sequenciais; R expiração durante downtime |
| T08 | C bid-first, terceiro observador confirma PID bloqueado e E+2min |
| T09 | C closer-first, bid espera lock, recusa sem reabertura |
| T10 | U guard SKIP; C dois owners deliberados, commit/rollback e sold/unsold, um frame por assinante |
| T11 | P falha financeira/integridade seguida de lote saudável |
| T12 | P âncora ausente sem reparo; U cooldown 300 s |
| T13 | P teto real e zero escrita; U retry somente após 300 s |
| T14 | U backoff 2–30/global; C falha transacional e nova Session |
| T15 | C barreira antes de commit e trigger diferida abortando COMMIT PostgreSQL real |
| T16 | P falha viva preserva commit/invalida só sala; U próxima liquidação progride com publicação retida |
| T17 | R commit confirmado sem publish, owner anterior encerrado, nova app não tenta/republica e snapshot converge |
| T18 | U/P whitelist sold/as_of persistido; parser TS |
| T19 | U/P whitelist unsold/nulls/genesis; smoke receipt zero |
| T20 | Whitelists exatas backend/TS, projeção explícita e M06 |
| T21 | P dois WS reais recebem frame igual e close 1000; TS cleanup; E2E terminal |
| T22 | E2E offline durante settlement, online deduplicado e snapshot terminal; TS offline inicial |
| T23 | P/R sold/unsold snapshot primeiro e1000; E2E zero ping/retry |
| T24 | Regressões `test_lot_room.py`, `lotConnection.test.ts` e E2E WS de heartbeat/gerações/stale |
| T25 | Regressões PG/WS cancelamento, close 1000, retry sem evento e público404 |
| T26 | Regressões fila cheia/send-close10s e isolamento lento em `test_lot_room*` |
| T27 | U owner/sleep; C stop durante COMMIT real, sem nova admissão/Session abandonada |
| T28 | P listener GET/HEAD/OPTIONS sem escrita/lock; regressões readers4.3 |
| T29 | P handshake/ping expired pending puros e settled snapshot puro; M07 |
| T30 | C E+2/E+4 sob lock real; regras339 e concorrência AD-5 com igualdade pura |
| T31 | P POST expired preserva422 lot_ended/economia/cooldown; M09 |
| T32 | P três variantes pending/teto financeiro/integridade: POST repetido não consome cooldown nem chama serviço; preserva422/409 e economia |
| T33 | `test_settlement_scheduler_fairness.py`:225 lotes reais/205 cooldown, tetos200/50, cursor/wrap e progresso único; U página parcial |
| T34 | P seleção obsoleta seguida de extensão/cancelamento/settlement; C recheck pós-lock |
| T35 | P/R lifespan antes do tráfego; `test_settlement_startup_order.py` executa shell com ordem migration→seed→uvicorn |
| T36 | P/R estados mistos/problema individual/startup global falho; shell seed falho impede servidor |
| T37 | C COMMIT real seguido de exceção sintética de ACK, nova Session already_settled/sem efeito |
| T38 | P subscribe retido×invalidate; TS pending count igual/as_of maior e geração velha inerte; E2E REST tardio |
| T39 | C worker/Session retidos além de janela operacional reduzida; U publicação não bloqueia próximo lote e owner drena |
| T40 | P read model único/coerência receipt; TS equality/arbitragem/parser e quatro E2E novos; sem UI4.5 |

### Mutações

Executei uma alteração temporária por vez. Cada alvo falhou por asserção
comportamental, exit 1 esperado; erro de sintaxe/coleta não foi contado. Restaurei
bytes originais em `finally` e conferi SHA-256/igualdade antes de seguir.

| ID | Mutação e detecção |
| --- | --- |
| M01 | Agendar resultado provisório antes do COMMIT; C T15 detecta pedido antes da confirmação externa |
| M02 | Publicar terminal em not_due; U exige zero task/evento |
| M03 | Cooldown permanente zero; U reprova prazo/repetição antes de 300 s |
| M04 | Publicar already_settled; U reprova segundo agendamento |
| M05 | Remover catch-up do lifespan; P exige settlement antes do yield |
| M06 | Adicionar winner_user_id ao evento; U reprova whitelist |
| M07 | Executar settlement no handshake; P reprova pending puro |
| M08 | Remover precedência terminal da arbitragem; TS reprova pending tardio substituindo settled |
| M09 adicional | Executar settlement no POST vencido; P reprova alteração econômica/snapshot, preservando códigoHTTP original |

O script inicial interpretou incorretamente o formato de saída do Node em M08:
o teste já falhava com AssertionError. Corrigi somente o leitor externo e
reexecutei M08/M09. Resultado final: **9 mutações detectadas**, arquivos restaurados.

### Smoke controlado

ASGI/WS reais com PostgreSQL dedicado, lifecycle e loop reais, sem mock financeiro:

```text
PASS live sold: lot_closed, settlement=1 receipt=1 close=1000
PASS live unsold: lot_closed, settlement=1 receipt=0 close=1000
PASS restart: startup catch-up settled offline expiry before traffic
PASS reconnect: missed terminal recovers sold/unsold via first snapshot and close=1000; no replay
PASS cleanup: owners drained; sessions returned
```

Exit 0. O cliente TS/E2E complementa a prova de ausência de reconnect loop;
o smoke ASGI não é execução em Render nem inspeção manual de navegador.

## Limitações preservadas e regressões

Descartei outbox/replay/novas regras: crash entre commit/publicação pode perder
frame. Snapshot/reconnect é a recuperação; invalidação viva é best-effort, sem
garantia de entrega exatamente uma vez. Sem hard timeout SQL, bloqueios podem
alongar ciclo/startup e cleanup além de 30 s; exceder a janela gera log e mantém
ownership. Cooldown é memória local e reinicia com processo; problemas permanentes
podem permanecer pending. Topologia continua um processo.

Contratos frontend/backend devem publicar juntos; abas antigas podem precisar
refresh. A janela pública segue50 e não vira auditoria. Não houve deploy ou smoke
público; os cinco E2E de pilha real existentes continuam opt-in. O warning conhecido
é de depreciação Starlette TestClient/httpx. Não houve code review nesta sessão.

Primeiras rodadas encontraram expectativas antigas de whitelist, fixture usando
factory errada e observador que filtrava thread externa em vez do worker AnyIO;
corrigi fixtures/observador sem afrouxar produto. Um pytest exploratório preso em
WS foi interrompido pelo implementador (exit130); nenhum gate final usa essa rodada.
O wrapper externo de uv também foi corrigido antes de executar smoke, pois
`--no-env-file` pertence a `uv run`. Nenhuma dessas falhas foi omitida como sucesso.

## Arquivos criados/alterados

- `frontend/test-results/.last-run.json`
- `frontend/e2e/lot-room-ws.spec.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/src/LotBidPanel.tsx`
- `frontend/src/lotRoomSocket.ts`
- `frontend/src/bidPosition.test.ts`
- `frontend/src/LotPage.tsx`
- `frontend/src/api/bids.test.ts`
- `frontend/src/api/bids.ts`
- `frontend/src/lotRoomSocket.test.ts`
- `frontend/src/lotConnection.test.ts`
- `frontend/src/lotConnection.ts`
- `_bmad-output/specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/implementation-evidence.md`
- `_bmad-output/specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/SPEC.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-4-gatilhos-do-fechamento-e-evento-de-encerramento.md`
- `backend/app/bids.py`
- `backend/app/lot_room.py`
- `backend/app/settlement_scheduler.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `backend/tests/test_csrf.py`
- `backend/tests/conftest.py`
- `backend/tests/test_settlement_scheduler.py`
- `backend/tests/test_lot_room.py`
- `backend/tests/integration/test_settlement_scheduler.py`
- `backend/tests/integration/test_lot_room_ws.py`
- `backend/tests/integration/test_settlement_scheduler_fairness.py`
- `backend/tests/integration/test_settlement_restart_recovery.py`
- `backend/tests/integration/test_settlement_scheduler_concurrency.py`
- `backend/tests/integration/test_bid_reads.py`
- `backend/tests/test_openapi.py`
- `backend/tests/test_settlement_startup_order.py`
- `docs/uso_de_ia.md`
- `README.md`

Comparei conteúdo com a baseline sem Git. `lot_settlement.py`, `wallet.py`,
`bid_rules.py`, `bid_integrity.py`, `lots.py`, `seed.py`, `start.sh` e `verify.sh`
permaneceram byte a byte idênticos; nenhuma migration/dependência nova.

**Alterados fora da lista literal de caminhos do mapa provável:**
`frontend/src/LotBidPanel.tsx` (somente impedir lance/aviso recuperável em terminal),
`backend/pyproject.toml`/`tests/conftest.py` (marker e controle do harness),
whitelists/fixtures de `test_bid_reads.py`, `test_csrf.py`, `test_openapi.py`,
`api/bids.test.ts`, `bidPosition.test.ts` e `e2e/support/mockApi.ts`. Esses ajustes
são necessários ao contrato compartilhado e às regressões aprovadas, sem
mudança de escopo. `frontend/test-results/.last-run.json` é artefato regenerado
pelo Playwright. Não tratei o mapa provável como autorização para iniciar 4.5.

A conferência separada somente por nomes encontrou **zero `.env*` alterados**;
conteúdo de segredos não foi lido nem comparado. Baseline/diff/logs/guardas de
execução permanecem na área local `_bmad/.runtime/bmad-build/` desta story.
Review interno/independente não foi executado, por restrição explícita do pedido;
não existem achados de review produzidos nesta sessão.

## Critérios de aceite

CA01/02: T01–05/08/09/30/34; CA03: T06/07/35/36; CA04: T15/37 e M01;
CA05: T18–20; CA06: T17/21–23/29; CA07: T11–16/36; CA08: T33;
CA09: T08–10; CA10: T27/35/36/39; CA11: T31/32 e M09;
CA12: T24–26/28–30/38/40. A matriz acima aponta os testes concretos.
Preservei CAP-1–5 e CAP-6 aposentada. Não reabri QH-01–16.

## Gates finais e tracking

Executei os dois comandos autorizados na raiz, com guardas externas contra
dotenv e sem modificar verify.sh. Saídas finais reais, ambos **exit0**:

```text
./verify.sh
2206 passed, 1 warning in 126.82s
frontend: 179 tests / 179 pass / 0 fail
verify.sh: todas as etapas passaram.

VERIFY_E2E=1 ./verify.sh
2206 passed, 1 warning in 125.59s
frontend: 179 tests / 179 pass / 0 fail
Playwright: 226 passed (24.8s), 5 skipped
verify.sh: todas as etapas passaram.
```

Ruff/lint, format (103 arquivos), ESLint, tsc, Vite e Docker passaram em ambos.
Os 5 skips são os testes existentes de pilha real, que exigem E2E_REAL_BASE_URL;
não foram apresentados como executados. O warning é o conhecido TestClient.

Antes do último reforço de dois cenários POST, os gates também passaram com
2204 backend/179 frontend e 226 E2E/5 skips. Repeti os dois após ampliar T32 para
pending/teto/integridade; as saídas acima correspondem ao estado final.

Story 4.4 e sprint: **review**. SPEC: **in-review**. Epic 4: **in-progress**.
Story 4.5: **backlog**, não iniciada. Não marquei4.4 done nem executei review,
Git ou deploy. Nenhum trabalho de implementação aprovado ficou pendente.

## Correções F44-01 e F44-02

F44-01 foi resolvido por cobertura E2E: no fechamento SOLD, o cliente parte de um lance, perde eventos e reconcilia os três lances, preço e contagem pelo GET final; o cenário 503 exige o aviso de histórico desatualizado e terminal sem reconexão. Os dois cenários focados passaram (2/2). Retirar temporariamente a leitura final fez o caso SOLD falhar com `1 lance`, esperado `3 lances`; o código foi restaurado.

F44-02 foi resolvido no scheduler e coberto em PostgreSQL: após COMMIT real e perda simulada do ACK, a entrada settled sai do mapa sem nova transferência, settlement, receipt ou publicação; lote pendente preserva o backoff de 2 s e o aumenta para 4 s na próxima falha. O pruning consulta no máximo 50 IDs por ciclo, rotaciona os sobreviventes e só remove IDs com settlement persistido. Ao impedir temporariamente a remoção, a regressão falhou na presença do retry órfão; o código foi restaurado.

A suíte backend direcionada da 4.4 passou com **41 testes**; regressões direcionadas de sala, WebSocket e liquidação 4.1–4.3 passaram com **153 testes**. O primeiro verify protegido passou nos 2207 testes backend, mas falhou no lint por espaço não separável no teste novo; após a correção, `./verify.sh` completo passou com **2207 backend e 179 frontend**. Ambas as mutações foram restauradas. A execução inicial do verify foi interrompida ao perceber a necessidade das guardas contra dotenv; as execuções posteriores usaram as guardas locais existentes.

`VERIFY_E2E=1 ./verify.sh` também passou: **2207 backend, 179 frontend, 227 Playwright e 5 skips**; os skips são os casos existentes de pilha real. Ambos os verifies finais usaram as guardas existentes contra dotenv.

## Correções do re-review F44-R01 e F44-R02

Reforcei o E2E SOLD para verificar `R$ 130,00` diretamente em `.bid-current` e confirmar que a sala segue encerrada após 90 segundos simulados. Ao impedir temporariamente apenas a atualização de `current_bid_cents` no GET final, mantendo o histórico correto, o teste falhou na nova asserção: recebeu R$ 110,00. Restaurei o arquivo de produção byte a byte. O E2E focal passou: **1 passed**.

No teste de ACK perdido, capturei o objeto `Retry`, seu `delay` e `next_attempt_at` antes do ciclo seguinte; o teste exige o mesmo objeto e os mesmos valores depois da inspeção pending, e confirma separadamente o backoff de 4 segundos após nova falha. Mutações que recriaram o objeto ou alteraram o prazo foram detectadas nas respectivas asserções; restaurei o scheduler byte a byte. O teste focal passou: **1 passed**.

Um teste determinístico com 60 IDs verifica a primeira janela de 50, a inclusão dos 10 restantes no ciclo seguinte, a remoção de dois settled e a preservação das instâncias, valores e prazos pending. Passou isoladamente: **1 passed**. A suíte 4.4 passou com **42 testes**, e as regressões direcionadas 4.1–4.3 com **153 testes**. Ambas tiveram o warning conhecido do TestClient.

Com as guardas contra dotenv, `./verify.sh` passou com **2208 backend e 179 frontend**; `VERIFY_E2E=1 ./verify.sh` passou com **2208 backend, 179 frontend, 227 Playwright e 5 skips**. O verify padrão foi repetido para registrar os totais, pois a coleta da primeira saída foi truncada. A Story permanece em review e a Story 4.5 não foi iniciada.


## Fechamento final aprovado — 28/10/2026

O review inicial foi aprovado com LOWs, sem HIGH ou MEDIUM. F44-01, F44-02,
F44-R01 e F44-R02 estão resolvidos; rotação de mais de 50 retries comprovada
com 60 IDs. Os três testes focais passaram e as mutações focais foram detectadas;
os arquivos de produção usados nas mutações foram restaurados byte a byte.
Nenhuma alteração de produção permaneceu após a última rodada de cobertura.

Evidência final: **42 testes 4.4**, **153 regressões 4.1–4.3**. Ambos os
verifies terminaram com exit 0: `./verify.sh` com **2208 backend e 179 frontend**;
`VERIFY_E2E=1 ./verify.sh` com **2208 backend, 179 frontend, 227 Playwright e
5 skips preexistentes**. Lint, typecheck e builds passaram.

Gate final aprovado: Story e sprint `done`, SPEC `done`, Epic 4 `in-progress`;
Story 4.5 permanece `backlog`. Os registros anteriores representam suas respectivas
rodadas e preservam os incidentes de processo; não são findings funcionais.

Incidentes de processo preservados no histórico: execução acidental de `git status --short`
e primeira tentativa de verify interrompida antes das guardas contra dotenv.
Nenhum dos dois é finding funcional da Story 4.4.
