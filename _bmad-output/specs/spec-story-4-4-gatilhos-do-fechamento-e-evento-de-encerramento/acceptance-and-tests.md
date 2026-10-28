# Critérios e testes finais — execução futura

Consolidei todos os oráculos conforme QH-01–16. Os IDs permanecem; CA11 e
T31/T32 agora exigem ausência de settlement no POST vencido. Nenhum teste,
mutação, SQL ou gate de aplicação foi executado nesta consolidação documental.

## Critérios de aceite

| ID / capacidade | Dado / quando / então |
| --- | --- |
| CA01 / CAP-1 | Processo acordado com vencido íntegro → ciclo chama só settle_lot → resultado sold/unsold e efeitos únicos da 4.3 |
| CA02 / CAP-1 | Futuro, cancelado ou candidato estendido → ignorado/recusado/not_due → zero encerramento indevido |
| CA03 / CAP-2 | Startup com vencidos pending → migrations/seed existentes, catch-up no lifespan → população inicial tentada antes do tráfego, sem mover seed |
| CA04 / CAP-3 | Nova transição → antes do commit zero terminal; só retorno confirmado agenda uma publicação lógica |
| CA05 / CAP-3 | Sold/unsold confirmado → lot_closed com nove chaves públicas exatas, as_of igual a settled_at, nulls corretos e zero dado privado |
| CA06 / CAP-3 | Evento perdido/offline/nova conexão → snapshot terminal do persistido antes de close 1000, sem liquidar; cancelado conserva semântica própria |
| CA07 / CAP-4 | Falha individual → log e cooldown/backoff → próximos lotes progridem; indisponibilidade sistêmica recua sem spin |
| CA08 / CAP-4 | Backlog/cooldowns → teto de 200 linhas consultadas/50 tentativas, cursor justo e wrap ao fim → sem scan ilimitado |
| CA09 / CAP-1 | Bid×closer e dois comandos deliberados → lock PG decide, um settlement/receipt sold e transferência, sem publicação operacional duplicada |
| CA10 / CAP-5 | Startup/stop/falha → owner único, guard SKIP, sleep interrompido, drenagem global 30 s e erro se exceder, sem abandono de worker/Session |
| CA11 / CAP-1 | POST recebe recusa de domínio por fim → preserva resposta, zero settle_lot/segunda transação de settlement/publicação por esse caminho |
| CA12 / CAP-3/5 | Regressões 4.1/4.2/AD-5 → heartbeat/gerações/cancelamento/slow client/anti-sniping preservados; leituras/handshake não liquidam |

## T01–T30 — cenários mínimos preservados

PG significa PostgreSQL real, migrations e banco dedicado _test, com observação
em conexão independente. WS exercita manager/ASGI reais; TS/E2E verifica consumo
no cliente. Relógios/esperas operacionais controlados não substituem lot lock,
saldo, commit ou clock crítico reais.

| ID | Cenário | Camada e oráculo final |
| --- | --- | --- |
| T01 | Scheduler liquida sold | PG + adaptador: W T−F/C−F, S T+F/C igual, disponível W e reservas alheias preservados, um settlement/receipt e publicação após retorno confirmado |
| T02 | Scheduler liquida unsold | PG: settlement unsold, zero receipt/dinheiro, terminal sem alias/preço |
| T03 | Futuro/not_due | PG + unidade: futuro fora da seleção; candidato obsoleto direto retorna not_due/false, sem evento/efeito |
| T04 | Cancelado | PG: fora da seleção; cancelado após seleção é recusa sem unsold/lot_closed |
| T05 | Já settled | PG, parametrizar sold/unsold: seleção/catch-up excluem ambos; comando explícito already_settled/false mantém IDs/saldos/instantes e zero broadcast |
| T06 | Catch-up no startup | PG + lifespan: depois do seed existente, pendente expira/é apurado antes do yield; sem GET ou POST necessário |
| T07 | Restart com pending expirado | PG + apps sequenciais: nova app liquida uma vez pelo catch-up, task antiga encerrada, sem seed duplicado no lifespan |
| T08 | Bid primeiro | PG: A segura lot lock do bid, C observa B bloqueado por A; commit A confirma E+2min, B relê e retorna not_due/zero evento |
| T09 | Closer primeiro | PG: A liquida após prazo, B espera; commit A permite terminal, bid B recusado sem bid/reserva/prorrogação e sem outro settlement/publicação pela rota |
| T10 | Dois ciclos/chamadas concorrentes | Unidade guard SKIP; PG força dois comandos independentes, um novo/um idempotente; após aguardar tasks de publicação, um settlement/receipt sold/transferência/broadcast lógico e um frame por socket saudável |
| T11 | Falha por lote | PG + política: primeiro lote em falha permanente/inesperada não impede o seguinte saudável; não abortar loop inteiro |
| T12 | Integridade inválida | PG: adulteração/âncora inválida/legado é recusado sem reparar/assinar, zero novo settlement/receipt/transferência/terminal, cooldown 300 s e log seguro |
| T13 | Teto e cooldown | PG teto real + relógio operacional: rollback integral, erro operacional e cooldown 300 s; ciclos antes do prazo não tentam de novo; outro lote liquida; após prazo pode tentar uma vez |
| T14 | DB transitório | PG falha/rollback ou injeção classificada + política: zero estado parcial/falso terminal; retry só em ciclo futuro, Session nova, recuo 2–30 s; falha global encerra rodada |
| T15 | COMMIT falha | PG trigger diferida de teste aborta COMMIT real: snapshot econômico anterior íntegro e zero publicação/task terminal; barreira pré-commit também exige zero enqueue |
| T16 | Commit sim, publish falha | PG + WS: registro/saldos preservados; log e tentativa de terminalizar/invalidar sala/close recuperável, mesmo se fechamento também falhar; outro lote continua; sem refazer settlement/retry de evento |
| T17 | Restart commit sem publish | PG: pausar entre confirmação e agendamento/publicação; destruir manager/app, criar nova app; snapshot terminal recupera, catch-up não republica settled nem move dinheiro |
| T18 | Evento sold | PG + WS/TS: whitelist de nove chaves, valores persistidos, as_of == settled_at inclusive microssegundos; spy proíbe clock novo na montagem/publicação |
| T19 | Evento unsold | PG + WS/TS: nove chaves, alias/preço null, count 0/genesis, as_of == settled_at, sem receipt/vencedor fictício |
| T20 | Privacidade | Schema/WS/REST/log: whitelist exata e marcadores sintéticos de IDs/e-mail/wallet/HMAC/segredos ausentes; só final_hash público aprovado, sem DTO/receipt interno |
| T21 | Cliente online | WS dois sockets do lote recebem terminal uma vez cada, outro lote recebe zero; drena terminal antes de close 1000; cliente terminal sem reconnect |
| T22 | Offline/reconnect | PG + E2E: offline durante settlement, online cria uma tentativa deduplicada; snapshot terminal converge sem replay/reenvio e impede ping/reconnect adicionais |
| T23 | Nova conexão settled | WS/TS/E2E, sold e unsold: aceita, primeiro frame room_snapshot terminal, depois 1000; zero settle_lot/ping inicial/reconnect; não recusar antes do snapshot |
| T24 | Heartbeat/reconnect 4.2 | Unidade/WS/E2E: pending mantém ping 20/pong 10/silêncio 60/snapshot 30, send/close 10, reset snapshot+pong, gerações antigas inertes e stale privado preservado |
| T25 | Cancelamento 4.1 | PG/WS/E2E: lot_cancelled pós-commit drena/close 1000, retry não publica, novos cancelados recusados e GET404; sem unsold ou snapshot público novo |
| T26 | Cliente lento | WS: fila cheia/send retido isola só lento com deadline existente 10 s; demais recebem terminal; nenhum I/O de rede sob lock financeiro/distribuição |
| T27 | Shutdown | Unidade + PG: durante sleep/ciclo/SQL/COMMIT/publicação, stop impede novos trabalhos, interrompe sleep e acompanha tasks/worker; janela é global 30 s, excesso logado, sem presumir rollback ou abandonar Session |
| T28 | GET/HEAD/OPTIONS puros | PG SQL listener + spy: rotas de leitura sem escrita/FOR UPDATE/settlement, estado econômico idêntico |
| T29 | Handshake/reconnect puros | PG/WS: pending expirado continua pending/ended sem liquidação no handshake/ping; settled só lê/snapshot; zero chamada settle_lot |
| T30 | AD-5 cumulativa | Now fixo no limite 2min + PG real com margens: E+2/E+4, flagtrue na igualdade, depois do fim não reabre; scheduler respeita fim confirmado |

## T31–T40 — integração, justiça e lifecycle

| ID | Cenário adicional | Prova final |
| --- | --- | --- |
| T31 | POST vencido não fecha | PG HTTP real com admissão do scheduler isolada no harness: resposta de domínio existente, spy settle_lot proibida, zero segunda transação de settlement/publicação, sem alterar auth/CSRF/precedência de erros |
| T32 | POST não contorna política operacional | PG + HTTP: repetir POST vencido com lote pending/teto/integridade e cooldown não causa fechamento nem muda cooldown/agendamentos; sem novos códigos HTTP settlement; só ciclo operacional produz tentativa |
| T33 | Batch/cursor/justiça | PG + contadores: >200 linhas, lote/cooldown nos primeiros IDs, demais alcançados em ciclos seguintes; soma retornada por consultas<=200 e tentativas<=50 por ciclo; cursor não salta linhas retornadas mas não examinadas, wrap/cutoff renovado ao fim |
| T34 | Candidato obsoleto | PG: pré-seleção seguida por extensão/cancelamento/settlement concorrente; comando decide estado atual, não timestamp inicial |
| T35 | Ordem startup preservada | Harness start.sh/lifespan + PG: migrations → seed existente → catch-up paginado inteiro → task única → tráfego; seed não movido/repetido; uvicorn direto tem catch-up e mantém pré-requisitos externos |
| T36 | Falhas e estados no startup | PG/unidade, fixtures sold/unsold persistidos, futuro/cancelado/problemático: nenhum duplica ou fecha indevido; falha individual permite próximo/tráfego após passagem; DB sistêmico impede yield/loop; seed falho no shell impede aplicação |
| T37 | ACK perdido | PG: COMMIT real seguido de exceção sintética, zero terminal da tentativa sem confirmação; outra Session vê persistência; nova chamada explícita retorna already_settled/false e snapshot converge sem repetir finanças |
| T38 | Subscribe/sinais/terminal tardio | WS/TS: subscribe retido×publish/invalidar, bid_accepted tardio, REST pending com count igual/as_of maior, callback de geração velha; terminal não regride nem inscrição pending escapa após invalidação conhecida |
| T39 | Ownership sem timeouts inventados | PG/unidade: worker retido além da janela global 30 s gera erro claro e continua possuído até liberar/cleanup; sem fechamento prematuro de Session/engine, sem novos limites DB ou 2 s; publicação retida por coordenação não bloqueia liquidação de outro lote, tasks observadas/drenadas |
| T40 | Contrato compartilhado/escopo | TS/E2E: REST/WS com settlement, count igual pending→settled deixa de ser sameRoomState; room.as_of da leitura distinto do as_of terminal; snapshot antes de ping; nenhuma tela/UX/link de resultado nova, abas legadas documentadas |

## Instrumentação e evidência futura

Para testar pureza de GET/POST/handshake, congelo **somente no harness** a
admissão do scheduler já iniciado, ou crio alvo expirado depois do startup.
Sem isso, um fechamento concorrente poderia ser atribuído à requisição. T06/
T35/T36 cobrem startup real sem desligar lifecycle; não mascaro mutações de produto.

PG usa A/B com Sessions/conexões independentes, observador C verificando
pg_blocking_pids exato e barreiras reais. Oráculos comparam todas as carteiras,
lote/bids/settlement/receipt e IDs/instantes originais em nova Session. Spy de
status prova roteamento, não commit/lock. Conto agendamento lógico e frames
separados; aguardo tasks pós-commit antes de concluir duplicação/ausência de evento.
Triggers/injeções só em _test, restauradas em finally; nenhuma execução nesta sessão.

## Mutações planejadas

| ID | Mutante | Detecção comportamental exigida |
| --- | --- | --- |
| M01 | Publicar/agendar antes do commit | T15 vê enqueue/task antes de outra conexão confirmar estado |
| M02 | Tratar not_due como terminal | T03/T08 falham por evento/fechamento indevido |
| M03 | Tirar cooldown/espera de falha permanente | T12/T13 detectam nova tentativa antes 300 s sem sleep longo |
| M04 | Publicar em already_settled ou duplicar transferência | T05/T10 detectam segundo broadcast ou efeito financeiro |
| M05 | Remover catch-up ou mover seed depois dele | T06/T35 exigem ordem seed→catch-up→tráfego e apuração anterior ao yield |
| M06 | Serializar winner_user_id/anchor_hmac | T20 reprova whitelist/marcadores privados |
| M07 | Settlement no handshake | T29 chama spy proibida/observa escrita indevida |
| M08 | Ignorar settlement na igualdade/arbitragem | T38/T40 conservam pending com count igual ou reabrem terminal |

No build autorizado, uma mutação por vez, restauração em finally e conferência
byte a byte; erro de sintaxe/coleta não conta como detecção. Os oito IDs foram
preservados, com M05 atualizado para a ordem humana final. Não executei mutações.

## Gates futuros

No build autorizado: suites focadas de scheduler/lifecycle/PG/WS; regressões
4.3/4.1/4.2/AD-5; ./verify.sh e VERIFY_E2E=1 ./verify.sh com saídas reais.
Pilha real opt-in/smoke Render são evidências separadas. Roteiro humano: duas
abas no mesmo lote, sold/unsold, offline antes do fim, restart após commit antes
do publish, abrir settled diretamente, sem heartbeat/reconnect terminal,
cancelamento intacto e nenhuma UI antecipada. Review independente é posterior;
esta validação documental não o substitui.
