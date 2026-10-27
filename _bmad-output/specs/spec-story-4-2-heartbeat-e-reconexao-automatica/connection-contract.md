# Contrato final de conexão e recuperação

## 1. Baseline e autoridade

Decidi consolidar somente a Story 4.2, pronta para desenvolvimento, sem implementar nesta sessão. QH-01–16 estão decididas em `human-decisions.md`. Preservo a 4.1: `/ws/lots/{lot_id}`, snapshot completo primeiro, bid_accepted pós-commit, lot_cancelled terminal, fila 8, limiter de leituras 4 e manager em memória de um processo. O frontend hoje conecta em onopen; o build da 4.2 mudará isso para snapshot.

A confirmação do dono de que a 4.1 está concluída/aprovada prevalece como pré-condição sobre seu tracking histórico em review. Não invento evidência de review/smoke e não altero a 4.1 nesta tarefa.

## 2. Invariantes e operações

- `pageEpoch`, lote e geração do socket identificam a autoridade; cada timer tem token. Antes de qualquer efeito, conferir identidade. Existe no máximo **uma geração autoritativa**, inclusive em StrictMode/remount. Close/message/open/error/pong antigos não afetam dados, conexão, contador ou retry.
- Substituir: invalidar primeiro a geração antiga, cancelar seus timers, desligar autoridade dos handlers, chamar close no antigo e criar nova geração sem esperar CLOSED. A eventual sobreposição física durante fechamento é aceita; nunca mantenho dois consumidores autoritativos. Cleanup tardio só toca o socket que capturou.
- No máximo um retry, um agendamento H, um deadline P e um deadline A por instância vigente. Retry e tentativa de abertura autoritativa são mutuamente exclusivos. `failed`/token garantem uma falha e uma progressão de k por tentativa.
- `fail`: invalidar autoridade, cancelar H/P/A, solicitar close, preservar dados e k, limpar manualFresh pela perda; se offline ficar unavailable, senão agendar um retry. Error seguido de close não faz isso duas vezes.
- `retry`: `cap(k)=min(30s,1s*2^k)` com saturação antes de overflow; delay=`cap/2+u*cap/2`, u uniforme [0,1] injetável. k começa em 0; uma falha reserva delay e incrementa k uma vez. Timer consome seu token antes de abrir. Online imediato não zera k; reset só snapshot+primeiro pong válido da nova geração.
- `stop`: invalidar página/geração/tokens, cancelar todos timers/listeners e leituras da instância, close no socket, zero reconstruções. Escrita REST pendente da 3.5 não é reenviada nem desfeita: callback só pode atualizar sua conta/lote/instância válidos.
- Máquina de conexão não reimplementa arbitragem pública: snapshot/evento/REST/201 passam pelo caminho existente de `shouldApplyRoom`. Bid_count primário, as_of desempate em microssegundos, terminal prevalente e sameRoomState permanecem intactos.
- Sala válida, detalhe, digitação, foco e feedback permanecem durante connecting/reconnecting/unavailable. Conexão e dados são eixos independentes; heartbeat não modifica nenhum dado de sala.

## 3. Estados

| Estado | Significado | Texto |
| --- | --- | --- |
| connecting | Primeira tentativa, opening/awaiting_snapshot; A ativo | Conectando à sala… |
| connected | Snapshot inicial válido recebido da geração atual; heartbeat ativo | Sala conectada |
| unavailable | Perda detectada ou offline; dados preservados | Sem atualizações ao vivo; offline: Sem conexão com a rede |
| reconnecting | waiting/opening/awaiting_snapshot; uma geração autoritativa | Reconectando à sala… |
| terminal | cancelled confirmado explicitamente ou not_found por REST 404 | Este lote foi cancelado / Lote indisponível ou não encontrado |
| disposed | Instância desmontada ou lote trocado; nenhum efeito | Não renderizado |

Não existe fase closing que bloqueie novas tentativas. Unavailable/failure pode ser passagem curta para reconnecting; offline persiste até online. Não há permanent derivado de onerror/close. Phase ended não encerra transporte nem liquida lote.

## 4. Transições T01–T25

Guardas globais: identidade/token válidos → não disposed/terminal → online para ações de rede → evento específico. Eventos processados serialmente; qualquer callback velho é inerte. Uma evidência REST terminal exige rodada/página/lote vigentes, não a geração de um socket que já foi invalidado.

| ID | Origem/evento | Guarda | Destino/efeito |
| --- | --- | --- | --- |
| T01 | Montagem online | Instância/lote elegível | connecting/opening; criar geração/socket único autoritativo, A=30 s desde construtor |
| T02 | Montagem offline | onLine false | unavailable/offline; zero sockets/timers de recuperação |
| T03 | connecting/reconnecting: open | Geração vigente | awaiting_snapshot na mesma categoria; não conectar nem resetar A/k |
| T04 | Primeiro room_snapshot válido | Geração/lote certos; antes do vencimento A | connected; cancelar A, arbitrar snapshot por shouldApplyRoom, primeiro ping imediato e P=10 s; não resetar k |
| T05 | Pong correspondente | Geração/ID pendentes, antes de P | connected; cancelar P; primeiro pong após snapshot zera k. Não deslocar H |
| T06 | H devido | connected, OPEN, sem ping pendente | Enviar um ping; P=10 s e próximo H=20 s desde envio atual; nenhum tick acumulado |
| T07 | P ou A vencido | Token vigente; prazo atingido | fail uma vez → unavailable; T10 se online. Snapshot/pong tardios não reanimam geração |
| T08 | Error, exceção no construtor ou send | Tentativa vigente | fail uma vez, sem esperar close; recuperação T10 |
| T09 | Close atual sem terminal | Tentativa ainda vigente | Falha recuperável → T10. 1000 sem terminal também não comprova fim do lote; close antigo cai em T25 |
| T10 | unavailable/failure | Montado/online, sem terminal | reconnecting/waiting; único timer com backoff+jitter; uma confirmação REST se necessária conforme §6 |
| T11 | Retry devido | Token atual, elegível, sem tentativa autoritativa em curso | Consumir token, invalidar geração anterior/close se ainda existir, criar substituto e A; reconnecting/opening; não aguardar CLOSED |
| T12 | Online durante espera de retry | Elegível, sem tentativa ativa | Cancelar token de retry, uma abertura imediata por T11; antigo timer torna-se inerte; k preservado |
| T13 | Online repetido durante tentativa/connected | Já existe geração ativa saudável ou em abertura | Sem efeito; não cria socket/timer paralelo |
| T14 | Offline em qualquer estado ativo | Instância vigente | unavailable/offline; invalidar geração, close, cancelar H/P/A/retry, preservar dados/k |
| T15 | Online após offline | Elegível, onLine true | Uma tentativa imediata em reconnecting/opening, sem esperar close físico; k preservado |
| T16 | Bid_accepted válido após snapshot | Geração/lote vigentes | Permanece connected; shouldApplyRoom decide dados; não renova P nem substitui pong |
| T17 | Lot_cancelled válido ou cancelamento explícito confirmado por REST | Evento atual inicializado ou resposta REST autorizada vigente | terminal/cancelled; invalidar gerações, cancelar H/P/A/retry e leituras, close, foco h1; nenhum retry |
| T18 | REST 404 confirmado | Página/lote/rodada vigentes | terminal/not_found; stop de recuperação; texto genérico, não inferir cancelamento |
| T19 | GET manual/sala ou 201 | Conta/lote/rodada válidos; sem terminal | Estado WS inalterado; arbitragem/feedback existentes; rede/5xx preserva dados, não torna permanente |
| T20 | Frame malformado/de outro lote/não snapshot inicial | Geração vigente | Ignorar como evidência de saúde/estado; A/P continuam; não conectar nem resetar k. Snapshot duplicado após inicial passa pela arbitragem sem reiniciar heartbeat |
| T21 | Pong duplicado/id incorreto/atrasado | Não corresponde à pendência válida | Ignorar; não renovar prazo. Se P venceu, T07; geração antiga sempre T25 |
| T22 | Unmount/navegação | Instância vigente | disposed; stop total, invalidar página/gerações, fechar; novo lote tem instância independente |
| T23 | Visible ou callback atrasado | Instância vigente | Reavaliar prioridades §5, no máximo uma ação imediata; tokens impedem repetição por visibility e timer concorrentes |
| T24 | Evento tardio em terminal/disposed | Qualquer | Sem efeitos; nada reabre conexão ou substitui terminal |
| T25 | Callback/token de geração antiga ou evento não aplicável | Guarda falha | Ignorar inclusive open/message/error/close/pong/retry; zero efeitos sobre geração nova |

Snapshot válido recebido em T04 pode ser mais antigo que um GET/201 atual: comprova inicialização do transporte, mas não substitui dados se shouldApplyRoom recusar. Só pong adicional reseta k. Cancelamento recebido de socket aposentado não fura a guarda: será ignorado; recuperação pode confirmar 404 genérico. Terminal válido cancela qualquer intenção defensiva de retry de forma atômica.

## 5. Relógios, heartbeat e suspensão

H=20 s entre envios efetivos; P=10 s da chamada send ao pong correspondente; A=30 s do construtor ao snapshot; S=60 s sem atividade válida do cliente; E=10 s por send/close backend. Usar relógios monotônicos para intervalos, nunca as_of/clock PostgreSQL. Prazo é vencido quando now >= deadline; só frame processado antes do vencimento satisfaz a pendência. Ordem de callbacks não revive uma tentativa cujo prazo venceu.

Primeiro ping imediatamente após snapshot; H seguinte nasce no envio. Pong apenas limpa P, não agenda H contando da resposta. Há no máximo uma pendência: não enviar ping para substituir outro pendente. Mensagens exatas ping/pong JSON com ID inteiro seguro positivo sequencial por socket; não misturar com parser/arbitragem de room. ID e geração juntos correlacionam resposta, mesmo quando novo socket reinicia IDs.

Ao voltar visible, recalcular, não reproduzir intervalos perdidos. Processar apenas a primeira regra aplicável:

| Prioridade | Situação | Uma ação imediata |
| --- | --- | --- |
| 1 | terminal/disposed | Nenhuma |
| 2 | onLine false | Aplicar cleanup offline se necessário, nenhuma rede |
| 3 | A vencido em abertura ou P pendente vencido | Falhar uma vez e agendar recuperação; não mandar novo ping para esconder P perdido |
| 4 | connected, sem P pendente e H devido | Um ping imediato com P normal; H seguinte relativo a esse envio |
| 5 | reconnecting/waiting e retry devido | Uma tentativa; consumir token antes do construtor |
| 6 | Prazo futuro ou ping/abertura em curso | Nenhuma; preservar a espera restante |

Não pausar deliberadamente a saúde por aba oculta. Timers podem ser suspensos pelo browser; servidor pode remover cliente por S. A volta reavalia realidade: ping falho/sem pong recupera por snapshot. Não garantir periodicidade física enquanto JS não executa.

## 6. Falhas, REST e cancelamento

Falha de transporte, error, 1006, close sem terminal, timeout de A/P e erro de rede são recuperáveis. Códigos de violação de entrada no servidor não autorizam concluir cancelamento/404 no frontend. Não introduzo classificação permanente por 1003/1008: aplico retry e confirmação pública, sem contornar Origin.

Após falha sem snapshot, quando precisar confirmar existência, usar GET público existente `/api/lots/{lot_id}/bids`, uma vez por episódio de recuperação; coalescer GET equivalente já em curso. Reservar flag antes de disparar, mantendo-a entre falhas até snapshot; zero timer REST periódico, nenhuma consulta a cada ping/retry. Retry WS não espera esse GET: uma resposta terminal vigente pode encerrá-lo; invalidar leitura diagnóstica pendente ao recuperar snapshot, terminal ou desmontar, impedindo erro antigo de encerrar nova rodada. Rede/5xx apenas mantém recuperação; GET manual continua disponível.

404 confirmado termina como indisponível/inexistente. Os read models públicos atuais ocultam cancelamento via 404: **não fornecem confirmação explícita de cancelled**. Se um resultado REST existente autorizado confirmar explicitamente o cancelamento (por exemplo, resposta da ação do dono já em curso), aplicar T17, sem criar endpoint, chamar endpoint privado pelo visitante ou tratar 404 como confirmação. Lot_cancelled atual é a prova explícita WS.

## 7. Backend e limpeza

| Fase/evento | Efeito |
| --- | --- |
| Handshake | Mesma política pública/Origin da 4.1 em toda tentativa; recusas antes do aceite; sem JWT na URL |
| Subscribe/snapshot | Leitura em Session curta no threadpool; serialização local da sala; snapshot primeiro item e primeiro frame; nenhuma escrita/liquidação |
| Accept / atividade válida | Iniciar relógio S ao aceite; ping JSON válido renova S. Nenhum outro comando de aplicação é aceito; pong de controle/bytes inválidos não contam |
| Ping válido | Enfileirar pong correlacionado no mesmo sender após snapshot; sem query, Session, estado da sala ou snapshot novo |
| S vencido | Parar subscriber, cancelar tarefas, close genérico 1011 recuperável, remover registros; sem esperar próximo lance |
| Fila cheia, inclusive pong | Isolar só cliente lento, fila 8 preservada, 1011; não criar fila auxiliar ilimitada |
| Send bloqueado | E=10 s limita send; parar sender/receiver/watchdog, isolar; close também com E independente |
| Entrada inválida/binária | Preservar 1008/1003 de rejeição da 4.1, exceto ping agora permitido; não executar domínio ou eco de payload arbitrário |
| Cancelamento | Preservar ordem snapshot/eventos/terminal; fechar após entrega, parar heartbeat; send/fila falha pode impedir entrega, não prometer replay |
| Disconnect/cancelamento/shutdown | finally idempotente, cancelar/aguardar tarefas próprias, remover subscriber/room quando sem users/subscribers; CancelledError propaga após cleanup |

Enviar/fechar nunca segura lock financeiro ou room.lock. Sinalizar stopped e retirar autoridade de transporte sem esperar leitura SQL em progresso; remoção do registro precisa respeitar Room.users e ser idempotente. Abandono durante subscribe não pode criar subscriber órfão quando a leitura retorna: resultado tardio é descartado, Session fecha no próprio worker e coordenação é liberada. E é por operação, não prazo global de toda a finalização nem timeout de SQL.

QH-11/12 adiadas: sem teto de conexões e sem timeout da publicação pós-commit. Preservo threadpool/limiter e coordenação da 4.1. O 201 pode esperar lock/limiter/leitura após commit; falha de transporte não desfaz escrita. Não uso tarefa solta de publicação como atalho.

## 8. Corridas obrigatórias

| Corrida | Resultado |
| --- | --- |
| Morte após commit antes do evento | Escrita permanece; recuperação lê snapshot confirmado, sem repetir POST |
| Evento perdido no intervalo desconectado | Snapshot completo substitui janela, sem cursor/replay, pode saltar contagens |
| GET manual e reconexão | Rodadas e shouldApplyRoom escolhem dados; GET não comprova saúde WS |
| 201 N após snapshot N+1 | Confirmação da tentativa preservada; overlay antigo não regride sala/fim/âncora; carteira revalidada pelo fluxo existente |
| Close/message/pong de socket velho após novo | Guarda de geração ignora tudo; não altera saúde/dados/k nem agenda retry |
| Múltiplos timers / retry antigo | Token consumido/inválido impede segunda abertura, mesmo se callback cancelado for executado |
| Navegação com retry | disposed e nova pageEpoch; nada do lote antigo altera novo ou reabre transporte |
| Offline→online rápido | Invalida/close antigo, uma tentativa imediata sem esperar TCP; callbacks velhos inertes |
| Cancelamento durante retry | Confirmação válida stop total; velho socket não tem autoridade; 404 posterior encerra genericamente |
| Mesmo count e as_of mais novo | shouldApplyRoom normal; sameRoomState reancora sem leitura privada se só as_of mudou |
| Duas reconexões | Uma geração autoritativa; sobreposição física durante close aceita inclusive em remount/StrictMode |

## 9. UX, privacidade e limites aceitos

Textos de estado em região acessível, anúncio somente na mudança, não por pong. Dados válidos permanecem; refresh manual com falha de rede/5xx mostra aviso local; sucesso indica leitura manual, não conexão recuperada. Preservo digitação/foco, pending POST e feedback, revalidação privada coalescida e posição da 4.1. Não desabilito lances somente por WS indisponível; servidor REST continua decidindo. Não altero DESIGN/EXPERIENCE ou conto encerramento como regra local.

Origin presente igual à APP_ORIGIN (esquema/host/porta), ausente aceito; malformado/null/repetido/estrangeiro recusado. URL ws/wss same-origin sem JWT; nenhum retry usa origem alternativa. Logs podem ter lot_id, categoria e classe de exceção, nunca mensagem privada, corpo, cookies, identidade, carteira, hash/HMAC.

Aceito explicitamente: um processo/memória volátil, sem outbox/entrega garantida; janela de 50 não é auditoria; heartbeat não prova frescor de domínio nem saúde PostgreSQL. Evento perdido com socket saudável só converge em próximo snapshot/GET/evento completo. Sem teto de conexões há risco de exaustão; 201 pós-commit sem deadline continua podendo demorar; retry indefinido consome recursos. Suspensão pode causar remoção/reconexão. Sobreposição física de sockets antigos em fechamento é possível, mas só a geração atual age; órfãos remotos expiram por S/E quando o servidor executa. Nenhum deadline garante execução durante suspensão do JS/event loop.

Fora do escopo: fechamento/liquidação, scheduler/catch-up, resultado/comprovante, Redis/broker/outbox/múltiplos workers, replay, migrações, alterações financeiras e reenvio de comandos.

## 10. Arquivos prováveis do build posterior

`backend/app/lot_room.py`: heartbeat/watchdog/deadlines/cleanup; main.py somente se lifecycle exigir. `frontend/src/lotRoomSocket.ts`, módulo simples `lotConnection.ts` (nome técnico sugerido), LotPage.tsx e LotBidPanel.tsx: geração, timers, integração e textos. Testes existentes de lot_room, integração WS, lotRoomSocket, novo teste puro de máquina e e2e lot-room-ws. README/uso_de_ia/story/sprint para evidências futuras. ShouldApplyRoom, migrations, domínio financeiro, auth e versões não precisam mudar.

## 11. Referências técnicas

[WHATWG WebSockets](https://websockets.spec.whatwg.org/): ping/pong de controle não é exposto à API JS e handshake pode ocultar causa HTTP. [AnyIO — threads](https://anyio.readthedocs.io/en/stable/threads.html): cancelar espera não encerra thread SQL. Referências verificadas na criação da spec em 27/10/2026; decisões humanas acima prevalecem sobre recomendações anteriores.
