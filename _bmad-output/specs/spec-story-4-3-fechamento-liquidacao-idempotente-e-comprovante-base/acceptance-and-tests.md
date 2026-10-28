# Critérios de aceitação e testes finais da Story 4.3

## Critérios do futuro build

Preservo CA01–18 e acrescento CA19–21; todos são obrigações futuras, não testes executados nesta consolidação.

| CA | Critério verificável | Capacidades | Provas planejadas |
| --- | --- | --- | --- |
| CA01 | Nova sold confirma débito/reserva, crédito, settlement e receipt juntos | CAP-1/2/3 | PG01, PG11, PG28 |
| CA02 | Nova unsold confirma settlement com quatro campos nulos, zero receipt/carteiras | CAP-1/3 | PG02, PG27 |
| CA03 | Ativo não fecha; igualdade now=ends_at elegível; clock só pós-lock | CAP-1/4 | U01, PG03/04 |
| CA04 | Fim cumulativo relido/preservado; não fechar antes do fim vigente | CAP-1/4 | PG04/05/35, R03 |
| CA05 | Lance primeiro estende e impede fechamento enquanto novo prazo futuro | CAP-4 | PG05/35 |
| CA06 | Close primeiro após prazo impede lance/reabertura | CAP-4 | PG06/24 |
| CA07 | Dois closers: uma transferência, um settlement, no máximo um receipt; segundo revalida | CAP-2/4 | PG07/08/28 |
| CA08 | Retry válido inclusive horas depois mantém saldos/IDs/vencedor/F/instante e transitioned=false | CAP-2/3/4 | PG08/23/34 |
| CA09 | Constraints reais: IDs próprios, UNIQUE lot_id em ambas e UNIQUE settlement_id receipt | CAP-3/4 | PG12/27/28 |
| CA10 | W A'=A, C'=C−F e reservas alheias intactas; S T'=T+F/C'=C; perdedores iguais; ΣT conservada | CAP-2 | PG09/19/25/26 |
| CA11 | Falha de qualquer etapa/INSERT receipt/COMMIT abortado reverte todas entidades | CAP-2/3 | PG11/20/22/30 |
| CA12 | Gate/adulteração/legado sem âncora bloqueiam sem reparo/reassinatura; v1 intacto | CAP-5 | PG13/14, R03 |
| CA13 | Settlement congela âncora validada/count/hash/bid; receipt copia apenas campos aprovados | CAP-3/5 | PG01/02/15/29 |
| CA14 | Receipt não contém identidade privada ou HMAC no schema, DTO, retorno ou log | CAP-5 | PG16/29, U02 |
| CA15 | Readers/GET/HEAD/OPTIONS/handshake não liquidam nem geram receipt | CAP-1/3/5 | PG17/18, U04 |
| CA16 | Somente novo commit confirmado libera transitioned=true; zero manager/evento 4.3 | CAP-4 | PG20/22/34, U03 |
| CA17 | 4.1/4.2, AD-5 cumulativa, auth, cancelamento e locks preservados | CAP-4/5 | R01–R03, PG19/21 |
| CA18 | QH-01–10 consolidadas/revalidadas antes de ready-for-dev; build depende autorização separada e verify real | Todas | D01/R04 |
| CA19 | Quatro statuses discriminados, falhas tipadas fora dos sucessos; crédito acima do teto aborta integralmente | CAP-2/4/5 | U03, PG03/10/30 |
| CA20 | Retry inconsistente falha sem repair/overwrite/recriação/reliquidação; sold sem receipt/unsold com receipt são conflitos | CAP-3/4/5 | PG23/31/32/33 |
| CA21 | Apenas serviço/readers internos, zero rota nova ou mudança de phase/WS/máquina/UI/painel | CAP-1/3/4 | D01, U04, R01/R05 |

## Harness, barreiras e oráculos

PostgreSQL 18 real com migrations reais no banco dedicado protegido `_test`; sem SQLite/create_all. Segredos/dados sintéticos de fixtures, sem ler .env* ou consultar dev/produção. Testes chamam **diretamente settle_lot(session_factory, ...)**; não registrar rota técnica, scheduler ou hook de produto para teste. Helpers internos podem ser exercitados isoladamente para lock/identity map, sem confundir preparação com sucesso confirmado.

Fixtures: lote autenticado vazio, um lance, vários lances alternados e >50 lances reais via serviço. Preparar expiração isoladamente antes da disputa (ends_at não é autenticado pela âncora); nunca ajustar fim por SQL no meio da corrida. Anti-sniping usa clock real com margens e espera limitada; igualdade temporal exata fica no domínio com now injetado.

A mantém lot lock e estado provisório; B, em outra thread/conexão, chega ao SELECT real; Event/Barrier e observador C confirmam B bloqueado por A via pg_blocking_pids. Só então liberar A por commit/rollback. Identificar PIDs/banco exatos; não aceitar qualquer lock do servidor. Timeouts limitam travamento e finally limpa sessões/threads; sleep não é prova. No caso cumulativo, C espera E passar enquanto B bloqueia e libera A antes de E+2min com margem, verificando now_B e fim persistido.

Oráculo: conexão independente compara lots, bids ordenados, **todas** carteiras relevantes, lot_settlements e receipts antes/depois, equações financeiras e resultados dos dois chamadores. No sucesso, IDs/referências/cópias concordam; no conflito/rollback, snapshot inteiro anterior. Reservas de outros lotes precisam ser não zero para detectar liberação indevida.

## PG01–24 preservados e consolidados

| ID | Preparação e ação | Asserções decisivas |
| --- | --- | --- |
| PG01 | Expirado íntegro sold, fechar pelo comando | Uma transferência, settlement/receipt confirmados por outra conexão; IDs UUID, alias/F/data/count/hash iguais ao último bid; anchor_hmac somente settlement; status settled_sold e transitioned=true após commit |
| PG02 | Expirado sem bids, âncora 0/genesis válida | Settlement unsold com usuário/alias/bid/F NULL; zero receipt, carteiras iguais; status settled_unsold; retry already_settled/false |
| PG03 | Agendado/live, prazo futuro e sem settlement | not_due/false, sem carteiras/escrita; statement lot lock antes do clock; nenhuma nova entidade |
| PG04 | No teste do helper, pré-carregar lote em Session B; A prorroga/commit sob lock; B relê | populate_existing obtém fim atual e clock B pós-lock; B não fecha futuro. No comando completo, Session própria impede herdar transação/objeto do chamador |
| PG05 | Lance A primeiro na janela; B closer aguarda; ultrapassar E antes do commit de A | A confirma E+2min; clock de B depois da espera, now_B<novo fim; not_due e zero settlement/receipt; não simular lock/hora |
| PG06 | Closer A após prazo, B lance bloqueado; A commit | Uma liquidação; B lot_ended, zero bid/reserva/fim novo; terminal preservado |
| PG07 | Dois closers com barreiras antes de commit, sold e unsold; variante A rollback | Commit A: B revalida e already_settled/false; só um settlement/transferência e receipt se sold. Rollback A: B pode produzir a única transição |
| PG08 | Retry confirmado em novas sessões e referência temporal antiga válida | IDs/instante/vencedor/F/âncora/count/hash mantidos, zero escrita; passagem exata de horas no domínio não substitui prova real do serviço |
| PG09 | Vários bids, perdedor e vencedor com compromissos em outro lote | Apenas F alvo consumido; perdedor intacto; reserva alheia não zero permanece; soma total preservada |
| PG10 | Crédito exato M, M+1, reserva insuficiente e carteira ausente | Exato M aceito; demais rollback integral; conflito financeiro tipado para teto/reserva; MissingWalletError ausente, sem criação |
| PG11 | Falhas pós-lock/cálculo/UPDATE W/UPDATE S/INSERT settlement/INSERT receipt/pré-commit | Snapshot anterior integral, sem novo settlement/receipt; falha no receipt não pode confirmar dinheiro; nova tentativa legítima funciona |
| PG12 | Inspecionar catálogos PG e violar PK/UNIQUE/FK/CHECK por inserts diretos isolados | IDs próprios, UNIQUE lot_id em lot_settlements/receipts, UNIQUE settlement_id, FK settlement_id+lot_id, bid composto, BIGINT/TIMESTAMPTZ e CHECK NULL explícitas; nenhum CHECK falso entre tabelas |
| PG13 | Alterar/inserir/remover/truncar/recalcular cadeia sem segredo, adulterar âncora/count/hash/líder/valor/vínculo de usuário | IntegrityConflict antes de efeitos, sem nova HMAC ou reparo; restaurar intervenção de teste/constraints com fixture restrita |
| PG14 | Legado anchor_hmac NULL com/sem bids e vazio assinado para lote diferente | Todos bloqueados sem reassinar; vazio autenticado do lote correto é controle positivo |
| PG15 | >50 bids reais; fechar íntegro e variante que adultera primeiro bid fora da janela recente | Positivo count/hash total corretos; negativo bloqueado pelo gate integral. Último bid sempre corresponde a sequence=count, não apenas à janela |
| PG16 | Marcadores sintéticos de dados privados/segredos nas entidades e logs novos | ReceiptRecord whitelist exata, nenhum join serializa usuário/carteira/âncora; SettlementRecord fica interno; erros/logs sem mensagens SQL/valores privados |
| PG17 | Expirado pendente, GET lista/detalhe/sala/mine e HEAD/OPTIONS existentes | Banco idêntico, sem fechamento/escrita/FOR UPDATE de negócio; preservar semântica real (não exigir 200 de método não suportado) e apurando resultado |
| PG18 | Handshake/reconexão WS de expirado pendente | Snapshot existente, zero liquidação e novo evento; heartbeat continua sem SQL; protocolo e máquina intactos |
| PG19 | Dois lotes mesmo dono, reserva compartilhada em outro lote e depósito concorrente | Locks ordenados/releitura, soma exata dos créditos/depósito, reservas alheias intactas; teto faz lote excedente falhar inteiro |
| PG20 | Reter comando antes do COMMIT real, observar outra conexão; variantes liberar ou abortar | Antes: só estado antigo e nenhum sucesso/transitioned true retornado. Commit: tudo visível; aborto: nada. Zero signal_committed/publicação em todos os ramos |
| PG21 | Cancelado antes; cancel × close sem bids nas ordens válidas | Cancelado não vira unsold/settlement; terminal close impede cancel posterior; públicos cancelados continuam 404; sem dinheiro/estorno |
| PG22 | COMMIT realmente abortado pelo banco (ex. constraint trigger diferida só no teste) e ACK perdido após COMMIT real | Aborto deixa nada; ACK perdido deixa tudo, mas sem sucesso confirmado ao chamador; nova Session retry não duplica. Não usar mock pré-commit como prova de confirmação perdida |
| PG23 | Settlement/receipt/histórico adulterados depois do sucesso; repetir | IntegrityConflict, zero escrita/repair/overwrite/reliquidação; validação de retry não exige a reserva F já consumida |
| PG24 | Terminal settlement com ends_at temporalmente contraditório, fixture isolada | Nunca not_due cego/reabertura/lance aceito; conflito conserva terminal/carteiras; nenhum ajuste via browser |

## PG25–35: onze provas adicionais explícitas do pedido humano

| ID | Prova adicional | Oráculo que detecta regressão |
| --- | --- | --- |
| PG25 | Vencedor não é cobrado duas vezes do disponível | W (T=50000,C=12000,A=38000), F=12000 → (38000,0,38000). Asserir **A_after=A_before**, além de T−F/C−F; implementar A−F ou débito extra falha |
| PG26 | Reserva de outro lote do vencedor preservada | W (80000,32000,48000), F_L=12000 e C_K=20000 → (68000,20000,48000); K permanece sem settlement e com seu líder/valor intactos |
| PG27 | Unsold exige settlement e nenhum receipt | Lote vazio íntegro: COUNT settlement=1, outcome unsold e quatro NULL, COUNT receipt=0; retry mantém ID/data e zero escrita. Um teste que verificasse só ausência de receipt seria insuficiente |
| PG28 | Sold exige exatamente um receipt | Após comando: COUNT settlement=1, COUNT receipt=1 e IDs/FKs/cópias coerentes; dois closers/retry mantêm ambos; falha no INSERT receipt reverte settlement/dinheiro |
| PG29 | Receipt não contém winner_user_id nem HMAC | Catálogo information_schema de receipts **e** lista exata de campos ReceiptRecord/resultado: ausência de winner_user_id/bidder_id/anchor_hmac/secret/JWT/carteira; presença da cópia interna em settlement é controle positivo |
| PG30 | Teto de crédito gera rollback total | T_S=M−5, F=10, C_W>=10: SettlementFinancialConflict(credit_limit_exceeded); T/C de todos iguais antes, COUNT novos settlement/receipt=0; não aceitar retorno already_settled, crédito parcial ou reserva liberada |
| PG31 | Settlement adulterado impede retry sem repair | Depois de sold, adulterar só campo copiado não autenticado por CHECK (ex. settled_at ainda >=ends_at e diferente do receipt), deixando gate/lote íntegros. Retry deve falhar **pela comparação de coerência**, não por outro gate; snapshot adulterado permanece byte a byte |
| PG32 | Sold sem receipt é inconsistência | Sold íntegro confirmado; retirar só receipt em fixture isolada; gate/settlement válidos. Retry IntegrityConflict, nenhuma recriação, UPDATE ou nova transferência; mantém ausência |
| PG33 | Unsold com receipt é inconsistência | Unsold vazio/âncora íntegros; inserir receipt intruso em fixture que suspende **somente FK necessária de bid do receipt** no banco de teste (não gate/estado do lote). Retry deve rejeitar a existência incompatível sem apagar/reparar; cleanup remove intruso e restaura FK exata antes de outros casos |
| PG34 | COMMIT confirmado com ACK perdido + retry não duplica | Wrapper de teste delega ao commit PostgreSQL real e só então lança erro de confirmação; primeira tentativa não entrega transitioned true, nova conexão prova settlement/receipt/dinheiro completos; retry já revalidado retorna already_settled/false e mesmos IDs/saldos |
| PG35 | AD-5 cumulativa impede closer antes do novo fim | Reusar corrida real PG05 e exigir novo fim **E+2min**, não now_A+2min, incluindo continuidade de extensões; B clock pós-lock entre E e novo fim, not_due sem novas linhas |

PG31–33 isolam o predicado de coerência que querem provar; não permitir falha anterior irrelevante como evidência. Intervenções/constraints só em banco de teste, nunca migrations ou gatilhos de produto; restaurar tudo em finally. Se técnica de falha for simulada, registrar a limitação; PG34 exige commit real antes do erro, não promessa baseada em spy. Isso é plano de testes, nenhuma intervenção executada nesta sessão.

## Regras puras, serviço e regressões

- **U01:** now injetado antes/igual/depois do fim; sem relógio interno. Exatamente 2:00 da AD-5 continua na regra cumulativa existente.
- **U02:** DTOs imutáveis e whitelist exata, inteiros/null/fuso/alias/hash, referência composta do bid; nenhum ORM ou SettlementRecord serializado como receipt.
- **U03:** statuses settled_sold/settled_unsold/already_settled/not_due; transitioned só após commit; IntegrityConflict/SettlementFinancialConflict fora dos sucessos; ausência e cancelamento distintos; helper provisório sem transitioned.
- **U04:** readers internos por lot_id sem escrita/lock de negócio; recuperar dados originais; sold sem receipt/unsold com receipt/órfão são conflitos estruturais. Não certificar auditoria criptográfica por leitura simples.
- **H01/H02 — retirados do plano de implementação:** testes condicionais de novas rotas do draft não se aplicam, pois QH-01/04/06 decidiram nenhuma HTTP. IDs registrados como retirados; não ficam pendentes nem autorizam criar API.
- **R01:** regressões backend/frontend sala/WS, snapshot e ordem, callbacks aposentados, ping/pong sem SQL, backoff/cleanup, avisos públicos/privados e zero evento de encerramento novo. Não alterar máquina 4.2 ou UI.
- **R02:** lances/depósitos/cancelamento, CHECK/ordem/deadlock, acesso/Origin/CSRF existentes preservados.
- **R03:** AD-5 E+2min, inclusive exatamente 2min, extensões cumulativas/fim nunca diminui e novo bid fora da nova janela; golden bytes/hash v1 intactos. Suíte deve detectar regressão now+2min.
- **R04:** futuro build executa ./verify.sh com saída real; VERIFY_E2E=1 continua opt-in, pilha real E2E_REAL_BASE_URL separada; nenhum gate afrouxado ou número histórico reaproveitado.
- **R05:** inventário de rotas e contratos públicos WS/phase/frontend antes/depois confirma nenhuma nova API nem campo/payload/UI/máquina alterado. Não testar status HTTP de fechamento inexistente.
- **D01:** QH-01–10 decididas, referências/IDs e preservação conferidos antes da promoção; ready-for-dev não é autorização de build/4.4.

## Evidência e alcance

No build autorizado, registrar comandos/resultados reais, bloqueio real nos cenários críticos, estado final e limites simulados versus reais. Nenhum PG/U/R executado nesta consolidação; nenhum pytest, verify, SQL, migration, navegador, smoke ou deploy. Esta fase revalida a especificação, sem implementar testes ou produto.
