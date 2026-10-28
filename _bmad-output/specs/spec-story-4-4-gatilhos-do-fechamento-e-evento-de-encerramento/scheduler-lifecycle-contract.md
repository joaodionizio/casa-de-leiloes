# Contrato final de scheduler e lifecycle

Consolidei QH-01/02/03/11/13/14/16. O componente orquestra o serviço confirmado
4.3; não implementa liquidação, tempo crítico ou política financeira própria.

## Owner e cadência

Decidi um componente interno por processo de produção, associado à app/lifespan,
no mesmo loop do manager. Start é idempotente: task viva não cria outra; o guard
local é compartilhado pelas entradas operacionais desse processo. Em testes,
apps isoladas possuem owners isolados; não acrescento coordenação distribuída.
Não inicio task no import, em create_app, GET, handshake ou tentativa de lance.

O loop executa um ciclo e só então espera 2 s, de forma interrompível por stop.
A espera após erro respeita max(2 s, backoff vigente), até 30 s quando aplicável;
não somo sleeps independentes nem reproduzo ticks perdidos. Entrada concorrente
com guard ocupado retorna SKIP, sem esperar em fila. Libero guard em finally.
PostgreSQL permanece a defesa transacional mesmo se duas chamadas forem
forçadas em teste. Um ciclo admite no máximo 200 linhas consultadas e 50
chamadas efetivas, sequenciais; cooldown/skip não contam como tentativa.

Não imponho orçamento de ciclo de 5 s, novos limites DB ou timeout de settlement.
A duração depende de lock/SQL/histórico reais: frequência de 2 s não promete
fechamento em 2 s. Erro individual que retorna é isolado e permite o próximo;
indisponibilidade sistêmica encerra a rodada e aplica backoff, sem spin.

## Startup e catch-up

A ordem final preserva o start.sh real:

1. Shell atual executa alembic upgrade head e seed existente; só depois executa um uvicorn. Não movo seed, não o repito no lifespan, não crio preflight paralelo.
2. Lifespan prepara owner/factory/integrity e manager, sem liberar tráfego ou iniciar loop periódico.
3. Catch-up imediato captura cutoff PostgreSQL e fronteira superior (ends_at,id) da população inicial pending vencida. Usa a mesma seleção, comando e classificação de outcomes do ciclo normal.
4. Percorre essa população finita em batches do mesmo mecanismo, cada batch respeitando 200 linhas/50 tentativas, sem wrap para retentar falhas na mesma passagem. Session de seleção fecha antes de chamar settle_lot.
5. Falha individual registra/cooldown e avança; não derruba startup. Falha sistêmica que impeça catch-up confiável, como PostgreSQL indisponível, falha startup com log e cleanup. Migrations/seed já executados não são revertidos nem repetidos.
6. Concluída a passagem inicial, inicia uma task periódica com próxima espera de 2 s e libera tráfego. Não duplica catch-up no primeiro tick; lotes que venceram durante a passagem entram na próxima varredura periódica.

Não trato uma página como recuperação completa se ainda há população inicial
por examinar. Cada ID é tentado no máximo uma vez nessa passagem; falhas podem
permanecer pending com política operacional. Sem tempo total de boot prometido.
Uvicorn direto também executa catch-up no lifespan, mas migrations/seed continuam
pré-requisitos operacionais externos, como hoje; lifespan não os executa sozinho.

## Query, batch e cursor

Modelo SQL documental para uma página; não executado nesta sessão:

```sql
SELECT l.id, l.ends_at
FROM lots AS l
WHERE l.cancelled_at IS NULL
  AND l.ends_at <= :cutoff
  AND NOT EXISTS (
    SELECT 1 FROM lot_settlements AS s WHERE s.lot_id = l.id
  )
  AND (:cursor_is_null OR (l.ends_at, l.id) > (:cursor_end, :cursor_id))
  AND (l.ends_at, l.id) <= (:upper_end, :upper_id)
ORDER BY l.ends_at, l.id
LIMIT :page_size;
```

Cutoff e fronteira superior são obtidos do PostgreSQL com clock_timestamp()
avaliado uma vez na abertura de cada varredura (CTE materializado); páginas
reutilizam esses valores. Nenhum relógio de aplicação decide elegibilidade.
É observação paginada READ COMMITTED, sem transação longa; a validação econômica
só ocorre sob lock dentro do comando. População vazia encerra a varredura.

Cada consulta retorna até 50 linhas e nunca mais que o saldo do teto de 200
linhas **consultadas** do ciclo. Somo todas as linhas retornadas, mesmo quando
o ciclo termina antes de examinar a página inteira. Cursor só avança até a
última linha efetivamente examinada, incluindo cooldown/erro; linhas ainda não
examinadas serão reconsultadas no próximo ciclo, sem saltá-las. Encerro após
50 tentativas, 200 linhas retornadas, fim da varredura ou stopping.

No periódico, mantenho cursor entre ciclos. Ao alcançar o fim, faço wrap e
renovo cutoff/fronteira para a próxima varredura no próximo ciclo, após a espera;
não volto infinitamente ao início na mesma rodada. Cooldown de um grupo antigo
não impede chegar aos IDs seguintes. No catch-up, fim significa passagem
inicial concluída, sem wrap antes do tráfego. Memória de resultados limita-se à
página, cursor e estados operacionais necessários, sem lista completa de lotes.

Não existe coluna active: candidato significa não cancelado, sem settlement e
vencido. Futuros e settled sold/unsold ficam fora; não filtro anchor nula para
ocultar legados. Não uso receipt como evidência de settlement, OFFSET,
FOR UPDATE ou SKIP LOCKED na descoberta. A query não garante correção: após
seleção o lote pode ser estendido, cancelado ou liquidado por outra chamada.

## Chamada exata e fronteira de confirmação

Chamo somente settle_lot(session_factory, *, lot_id, integrity), síncrono, em
worker que mantém a posse da Session criada/fechada pelo próprio comando. Não
passo now/ends_at da seleção, ORM entre threads, transação externa ou helper
prepare_settlement. O comando 4.3 relê sob lot lock, lê seu clock crítico,
autentica, liquida e confirma; não acrescento commit, transferência ou reparo.

| Resultado real | Ação final |
| --- | --- |
| settled_sold / settled_unsold, transitioned=true | Validar variante e settlement confirmado, construir whitelist e solicitar uma única publicação terminal pós-retorno |
| already_settled, false | Zero republicação/efeito novo; dados persistidos serão lidos por snapshots |
| not_due, false | Normal para candidato estendido/obsoleto, zero terminal, seguir outro lote |
| IntegrityConflict | Falha de integridade, cooldown 300 s, zero sucesso/evento/reparo |
| SettlementRefusal.LOT_CANCELLED / None | Descartar candidato obsoleto/ausente, sem unsold ou terminal |
| Exceções financeiras/DB/carteira/inesperadas | Política de falha, sem evento por suposição ou rollback fictício |

Combinação inválida de status/transitioned/settlement é erro interno. O DTO
interno nunca é serializado inteiro. Só depois de retorno confirmado o loop
pode publicar. Não uso from_thread.run diretamente no loop nem asyncio.run em
outro loop; a ponte existente de rotas síncronas não é novo gatilho de settlement.

## Publicação e progresso

Para não reter processamento financeiro aguardando socket/coordenação de uma
sala, cada nova transição agenda uma única publicação async interna, possuída
pelo componente e identificada por lote/transição. Ela usa o mesmo manager,
coordenação por sala e filas/sender existentes. Registro tasks, consumo erros
em finalização e acompanho todas no shutdown; nenhuma task órfã, retry periódico,
novo processo/worker de serviço ou fila persistente. Duplicata idempotente não
agenda outra publicação. Task pending não significa frame entregue.

A publicação não faz SQL: projeta o resultado confirmado. Falha tenta
terminalizar/invalidar o manager e fechar conexões afetadas de modo recuperável.
Nenhum I/O de rede ocorre com lock SQL/lock de distribuição retido. A espera
assíncrona de coordenação continua sujeita às limitações existentes, sem novo
deadline de 2 s; a task não bloqueia os lotes financeiros seguintes. Não crio
timer que mate settle_lot ou descarte worker de leitura do manager.

## POST vencido e leituras

Decidi preservar a rota de lance: recusa de domínio existente e rollback da
própria tentativa; zero segunda transação de settle_lot, zero terminal por esse
caminho e zero código HTTP novo de settlement. Não consulto/furo cooldown pelo
POST. GET/HEAD/OPTIONS/handshake/reconnect/ping apenas leem/transportam; nunca
servem de compensação operacional por downtime.

## Shutdown e janela global de drenagem

Stopping é marcado antes de await; impede novas seleções, lotes, ciclos e
agendamentos. Acordo/cancelo sleep e aguardo a task do loop. Para worker sync
já iniciado, mantenho posse protegida até concluir/encerrar a Session nele;
cancelar await não prova cancelamento SQL ou rollback. Publicação já agendada,
senders/close e leituras iniciadas do manager entram na drenagem acompanhada.
Resultado confirmado sem publicação durante shutdown converge por snapshot.

A drenagem cooperativa tem **uma janela global de até 30 s**, contada desde
stopping, não 30 s por recurso. Send/close preservam seus deadlines de 10 s
onde aplicáveis. Se exceder 30 s, registro erro operacional de drenagem excedida,
recursos pendentes por categoria e estado de confirmação conhecido, sem dados
privados. Não inicio trabalho novo nem volto a repetir janelas silenciosamente.

O esgotamento não autoriza soltar thread, fechar Session de outro thread,
descartar engine em uso ou anunciar shutdown completo. Recursos ainda ativos
mantêm owner/supervisão para cleanup quando terminarem; se o supervisor externo
encerrar o processo, o banco/snapshot recuperam, sem certificação local de commit
ou rollback. Preservo limites DB existentes; não prometo shutdown total de 30 s
ou teto de espera SQL que o projeto não possui. Engine compartilhado não é
descartado pelo scheduler; qualquer recurso próprio só fecha após seus usuários.
