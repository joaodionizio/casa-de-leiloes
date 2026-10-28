# Política final de falhas e retry

Consolidei QH-09/10/12/16 e o tratamento humano de falhas transitórias. Retry
operacional sempre usa comando 4.3 em Session nova, só em ciclo futuro; nenhum
laço de retry dentro da transação ou falha de transporte vira falha financeira.

| Categoria | Terminal | Retry/política final | Log/progresso |
| --- | --- | --- | --- |
| not_due | Zero | Normal; candidato obsoleto/estendido, aguarda nova elegibilidade | Contador/debug, próximo lote segue |
| already_settled | Zero republicação | Nenhuma nova liquidação; snapshots leem resultado | Contador/info agregado, próximo segue |
| None / LOT_CANCELLED | Zero lot_closed | Descartar ID/estado local obsoleto | Contador/debug, próximo segue |
| IntegrityConflict | Zero settlement novo/evento/reparo | Cooldown local 300 s, uma nova tentativa automática somente depois | Erro operacional com categoria/lot_id, sem bloquear demais |
| SettlementFinancialConflict, inclusive teto/reserva/invariante | Zero terminal | Cooldown local 300 s; sem bypass ou nova regra financeira | Erro operacional, sem valores privados; próximo segue |
| MissingWalletError | Zero terminal | Violação de invariante financeira, cooldown 300 s; não criar carteira | Erro categórico; próximo segue |
| DB transitório reconhecido, deadlock/serialização/erro de comunicação | Zero sem confirmação | Backoff operacional 2,4,8,16,30 s por ID quando aplicável; tentativa apenas em ciclo futuro | Log seguro, Session descartada/encerrada; próximo segue se DB saudável |
| PostgreSQL/conexão global indisponível | Zero sucesso presumido | Encerra rodada, backoff global 2–30 s; no startup falha sistêmica pode impedir tráfego | Erro claro, sem testar página inteira contra banco caído |
| COMMIT ambíguo | Zero terminal por inferência | Não presumir rollback; idempotência/revalidação 4.3 em tentativa futura e snapshot persistido | Erro de confirmação; sem compensação |
| Constraint/incoerência persistente identificada | Zero | Tratar como integridade/invariante com cooldown 300 s, sem transformar UNIQUE em already_settled | Erro seguro, não reparar/repetir financeiramente |
| Erro inesperado sem classificação permanente | Zero | Isolar ID/ciclo; backoff operacional 2–30 s e investigação, sem retry imediato | Erro só classe/categoria/lot_id; não deixar loop morrer silenciosamente |
| Publish WS falha depois do commit | Resultado econômico intacto | Sem retry periódico do evento; tentar terminalizar/invalidar sala e close recuperável best-effort | Erro e eventual falha de invalidação; tasks supervisionadas não prendem demais lotes |
| Shutdown | Nenhum novo trabalho | Interrompe sleep/admissão, acompanha workers/publicação, drenagem global 30 s | Erro operacional se exceder, sem presumir transação encerrada |

Classificação transitória usa informações conhecidas do driver, sem registrar
SQL/DETAIL/parâmetros ou considerar toda exceção transitória. Erros financeiros
e de integridade não viram backoff curto. Timeouts/erro de comunicação não
provam rollback; o comando existente continua a fronteira de confirmação.

## Cooldown, justiça e logs

Cooldown 300 s e next_attempt_at/backoff vivem em memória por ID com relógio
monotônico operacional. O tempo crítico do settlement continua PostgreSQL
pós-lock. Scheduler e catch-up compartilham política, não POST. Restart pode
apagar cooldown e tentar novamente uma vez na passagem inicial; isso foi aceito.
Não persisto quarentena nem acrescento endpoint administrativo.

Cursor avança em cooldown/erro e alcança IDs seguintes; estado local não altera
resultado econômico ou garante que condição permanente ficou corrigida. Removo
entradas ao resolver/expirar ou descobrir ausência/cancelamento. Lote no teto
pode continuar pending até intervenção, sem promessa de solução automática.

Logs de início/fim de catch-up/ciclo incluem source startup|scheduler, lot_id
público se individual, categoria/status, contagens, duração monotônica, SKIP,
limite atingido/backlog e drenagem. Registro tentativas efetivas/falhas, não erro
a cada tick de cooldown. Sucesso só após confirmação; enqueue não prova recepção.
Não registrar usuário, e-mail, wallet/saldo, alias privado, HMAC/segredo, DSN,
cookie, receipt, DTO interno ou texto bruto de exceção. hide_parameters não
protege sozinho DETAIL PostgreSQL. Sem sistema externo de observabilidade.

## Limites preservados e shutdown

Uso mecanismos/limites DB existentes do projeto. O db.py atual configura
pool_pre_ping/hide_parameters e não declara lock_timeout/statement_timeout do
scheduler; não invento valores 5 s/2 s nem factory/engine dedicado para impô-los.
Uma espera SQL ainda pode alongar ciclo/boot; isolamento de erros que retornam
não é garantia de prazo SQL total. Não abandono thread para obter latência artificial.

Preservo send/close 10 s da 4.2; não introduzo enqueue/isolamento 2 s ou hard timeout
em settle_lot. D-A da publicação de lances e tetos de conexão permanecem adiados.
Task de publicação pós-commit tem owner, erro consumido e drenagem própria dentro
da janela global; sem bloquear o ciclo financeiro nem soltar task órfã.

No shutdown, uma janela global de até 30 s acompanha tudo já iniciado; nenhum novo
ciclo/lote entra e sleep é interrompido. Ao exceder, erro operacional explícito;
recursos sync ainda ativos continuam possuídos até cleanup seguro ou término
externo do processo. Não fecho Session/engine debaixo de worker ativo, não trato
cancelamento como rollback, não declaro shutdown limpo se há recursos pendentes.
Read/worker abandonado pelo cliente mantém lease/Session até finalizar, conforme 4.2.

## Fronteira HTTP preservada

POST vencido permanece com recusa de domínio atual; não chama settle_lot, não
publica terminal, não abre segunda transação e não acrescenta códigos HTTP de
settlement. GET/HEAD/OPTIONS/handshake/ping não liquidam. A recuperação financeira
não depende de nenhum desses caminhos.
