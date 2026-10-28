# Modelo final de concorrência

Preservo AD-5/6/8/9/26 e o serviço 4.3: lote → clock PostgreSQL pós-lock →
releitura/gate → carteiras ordenadas por user_id → commit. Scheduler/WS não
acrescentam lock de negócio ou movem finanças. Guard local reduz overlap;
PostgreSQL garante idempotência mesmo com duas chamadas deliberadas.

## Bid primeiro

A aceita lance válido sob lot lock e mantém a transação. B tenta fechar o ID
pré-selecionado e espera; observador C comprova B bloqueado por A. A confirma
extensão cumulativa E→E+2min. B adquire lock depois e lê seu clock/novo fim;
com margem antes do novo prazo retorna not_due/false, zero lot_closed/settlement/
receipt/transferência. Não usa tempo da seleção. Um segundo lance na janela
produz E+4min. Se espera de B ultrapassar também o novo fim, fechamento será
legítimo; o teste escolhe margens para distinguir esses cenários.

## Closer primeiro

A adquire lot lock depois do prazo, autentica e liquida; B lance espera. Após
COMMIT A, retorno confirmado permite uma publicação terminal. B relê e recusa
sem bid/reserva/extensão/reabertura. A rota mantém essa recusa: não dispara um
segundo settle_lot ou publica outro terminal. Se A reverte, B decide com seu
próprio clock e estado confirmado, sem herdar resultado provisório.

## Dois ciclos e duas chamadas

Teste de guard local: duas entradas no mesmo processo → uma executa, outra
SKIP imediato, sem fila. Teste transacional separado força duas chamadas por
ID contornando apenas guard no harness, com factories/Sessions/conexões
independentes. A segura lot lock; B espera comprovadamente; após commit A,
A retorna novo/true e B already_settled/false. Exijo um settlement, receipt
sold=1/unsold=0, transferência única e um agendamento lógico de lot_closed.
Cada socket saudável recebe um frame no cenário sem falha, após aguardar as
tasks de publicação possuídas pelo componente.

Repito ordens invertidas e rollback A: somente quem confirmou a transição
publica. Não uso ON CONFLICT DO NOTHING ou guard Python para mascarar débito
duplicado. Com publish/crash falhando pode haver zero/entrega parcial, sem
prometer entrega exatamente uma vez. A publicação não tenta novamente porque
outro comando retornou already_settled.

## Manager, subscribe e mensagens tardias

Coordenação local serializa leitura/inscrição/enqueue por lote, sem envolver
transação financeira. Inscrição vê snapshot pending e depois terminal ou já
snapshot terminal. Nunca registrar pending depois de publicação concluída
normalmente. Em falha viva, invalidação local também cobre subscribe pendente;
worker mantém posse da Session mesmo se cliente desistiu.

Sinal de bid com commit anterior ao settlement pode chegar depois: a releitura
mostra estado atual e o cliente conserva terminal. Mesmo bid_count/as_of maior
não faz REST pending atrasado substituir settled. Duplicata idêntica é inerte;
callback de geração aposentada não aplica dados/reabre transporte. room.as_of
é relógio da leitura; lot_closed.as_of deriva de settled_at, sem ordenar commits.
Cancelamento conserva sua corrida: cancel primeiro → closer recusado;
settlement primeiro → cancel recusado, sem converter cancelado em unsold.

## Publicação e shutdown

Cada transição confirmada cria no máximo uma task de publicação interna,
registrada/supervisionada, sem prender o avanço do ciclo financeiro. A task não
possui transação financeira e usa coordenação/filas do mesmo manager. Não há
worker externo, retry periódico, timeout 2 s ou alteração de send/close 10 s.

Stopping impede novo trabalho; sleep é interrompido. Se há SQL/COMMIT síncrono
em curso, aguardo sob posse protegida; fim do await/cancelamento não prova fim
da transação. Drenagem global 30 s cobre scheduler, workers e publicações; excesso
é logado sem abandonar Session/engine em uso. Resultado confirmado que não
pôde publicar continua recuperável por snapshot; indeterminado exige descoberta
pela 4.3. Teste retém COMMIT real, pede shutdown e só depois libera para comprovar
ownership e cleanup. Não transforma prazo operacional em timeout financeiro.

## Prova com PostgreSQL real

Uso A/B em conexões distintas e observador C no banco dedicado _test.
Barreiras indicam A com lock e B no SQL; C verifica pg_blocking_pids com o
PID exato de A bloqueando B antes de liberar commit/rollback. Não concluo
concorrência por duas threads que apenas terminaram. Tempo real com margens
nas corridas; now injetado somente em limites puros/políticas operacionais.

Oráculo final compara lote, bids, todas as carteiras/outros compromissos,
settlement/receipt e IDs/instantes/hash/alias originais em Session independente.
Conta publicação lógica e frames por socket separadamente. ACK perdido é
injeção sintética depois de COMMIT real, sem alegar queda física de rede.
Finally libera barreiras, aguarda threads/tasks e fecha sessões em falha;
nenhuma suíte concorrente recria o mesmo banco durante essas provas.
