# Modelo final de concorrência

## Ordem e durabilidade

Defino a aquisição efetiva do lock da linha lots como ordem de decisão; o resultado só é durável após commit. Quem obtém lock e reverte não produz transição econômica. Todas as escritas em lance/cancelamento/fechamento seguem lot lock → carteiras em user_id crescente; nenhum wallet lock antes do lot lock. Não usar mutex Python/manager WS em lugar do PostgreSQL, nem adquirir outro lote depois das carteiras.

No READ COMMITTED existente, SELECT FOR UPDATE após espera obtém estado confirmado atualizado; o ORM força releitura e o clock é capturado depois da aquisição, conforme AD-6/26. Os fundamentos PostgreSQL 18 já consultados constam em [isolamento](https://www.postgresql.org/docs/18/transaction-iso.html), [locks](https://www.postgresql.org/docs/18/explicit-locking.html) e [clock_timestamp](https://www.postgresql.org/docs/18/functions-datetime.html); os testes abaixo provarão a aplicação real do protocolo.

## Lance primeiro

| Ordem | A: lance | B: closer |
| --- | --- | --- |
| 1 | Adquire lot lock enquanto válido e lê now real | Eventual pré-seleção não decide nada |
| 2 | Gate/regras aceitam, aplica AD-5 E→E+2min e mantém lock | Inicia SELECT FOR UPDATE e espera A |
| 3 | Commit confirma extensão, reserva/histórico | Só depois adquire lock, lê clock e relê ends_at |
| 4 | — | Se now_B<E+2min, not_due; zero settlement/receipt/efeito financeiro |

A pode ter iniciado antes de E e ainda segurar a trava depois do fim original. B pode parecer tratar expirado durante a espera; isso não invalida a extensão confirmada por A. Se a espera ultrapassar também o novo fim, B decide elegibilidade pelo prazo vigente; não recusa apenas por detectar uma extensão.

## Fechamento primeiro

| Ordem | A: closer | B: lance |
| --- | --- | --- |
| 1 | Adquire lot lock após prazo; clock>=ends_at e gate íntegro | Tenta mesma trava e espera |
| 2 | Liquida, INSERT settlement e receipt sold; commit único | Nenhum efeito enquanto aguarda |
| 3 | Retorna novo resultado confirmado/transitioned=true | Relê estado, recusa lance no terminal; nenhum bid/reserva/extensão/reabertura |

Estado temporal consistentemente encerrado recusa lot_ended no lance; terminal persistido também impede reabertura sob termos/relógio inconsistentes (conflito quando necessário). Se A reverter, B decide do estado anterior com seu próprio clock pós-lock; não herda resultado provisório.

## Dois closers e repetição

A segura lot lock e prepara efeitos; B chega ao lock real e espera. Após commit A, B relê settlement, autentica histórico e confere lote/settlement/receipt ou ausência em unsold; retorna already_settled/transitioned=false. Exigir uma transferência, um settlement e exatamente um receipt para sold, zero para unsold. UNIQUE(lot_id) em ambas as tabelas e UNIQUE(settlement_id) em receipts são defesa adicional, sem substituir a trava.

Se A aborta, B pode realizar a única liquidação; não pode descobrir settlement provisório. Retry horas depois mantém IDs, instante, vencedor/F/count/hash e saldos. Se settlement adulterado, sold sem receipt ou unsold com receipt, B falha com IntegrityConflict, sem reparo/INSERT/UPDATE econômico. Não usar ON CONFLICT DO NOTHING no receipt para esconder novo débito.

## Confirmação perdida de COMMIT

A confirma no PostgreSQL, mas perde confirmação ao retornar: não há transitioned=true observável dessa tentativa. B/retry em nova Session por lot_id descobre settlement confirmado, revalida e retorna already_settled com false; transferência/IDs não se repetem. Se o commit não ocorreu, B pode liquidar. Não criar compensação ou retry automático quente no comando; a futura publicação 4.4 continua sujeita à limitação commit/publicação AD-25.

## Outras carteiras e terminais

- Dois lotes do mesmo leiloeiro: serialização na carteira S soma créditos sem perda; se próximo ao teto, o que não cabe falha integralmente, sem novo settlement/receipt. Tratamento operacional anti-retry quente é da 4.4.
- Vencedor em vários lotes ou lance em outro lote: saldo é relido após wallet lock, consumo só de F alvo e reserva restante preservada.
- Depósito concorrente: trava só carteira e nunca pede lote depois; fechamento relê total confirmado, preservando ambos os efeitos válidos.
- Cancelamento: cancelado permanece separado sem settlement de fechamento; closer terminal primeiro impede recancelamento. Sem estorno/cancelamento com lances.

## Prova com PostgreSQL real

Sessões e conexões independentes A/B, observador C. Event/Barrier marca A com lock e a tentativa SQL de B; C confirma PID B bloqueado por A via pg_blocking_pids no banco dedicado. Só então liberar A por commit/rollback. Não compartilhar Session, fingir locks via mocks ou concluir corrida por duas threads que apenas terminaram.

Para extensão, A aceita com clock real antes de E e mantém transação; B bloqueia. C espera relógio PostgreSQL ultrapassar E com prazo limitado, liberando A com margem antes de E+2min. Registrar now_B/E/novo fim; não mudar ends_at por SQL durante a disputa. Espera temporal prepara o caso; barreira/lock real e estado final são a prova.

O comando interno é chamado diretamente pelos testes; instrumentação retém execução antes de commit/SQL real para sobrepor transações, sem criar rota ou hook de produto. Testes do helper com Session pré-carregada verificam populate_existing separadamente. Timeouts limitam travamento, não provam correção; finally encerra sessões/threads e restaura intervenções. Oráculo final compara todas as carteiras, bids, lote, settlement e receipt, junto aos retornos dos dois chamadores.
