# Testes necessários e mutation plan

Decidi concentrar os testes novos no cancelamento e nos pontos de integração.
Descartei repetir as matrizes financeiras, anti-sniping e criptográficas completas
da 3.4. Tudo abaixo é **plano para o build**, não execução desta rodada.

## 1. Migration e contratos

`backend/tests/integration/test_lots_cancellation_migration.py`, PostgreSQL dedicado:
partir explicitamente de 0005, inserir lote legado com SQL compatível com 0005,
upgrade 0006, inspecionar TIMESTAMPTZ, nullable=true e default ausente. Conferir
legado NULL e demais dados iguais; nenhuma CHECK/FK/índice novo. Downgrade 0005
remove só coluna e mantém dados anteriores; novo upgrade head restaura NULL.
Fixture finalmente restaura head mesmo após falha e descarta conexões conforme
os testes Alembic atuais. Não criar metadata.create_all nem SQLite.

OpenAPI/policy: rota POST cancel AUCTIONEER, sem requestBody, duas propriedades
obrigatórias de resposta, erros documentados pelo envelope. MyLots tem as_of e
item com 21 campos; criação 201 continua 18 campos. Preservar enum LotPhase de
três valores, detalhe público de 17 campos, `/mine` antes de `/{lot_id}` e SPA
depois das rotas. Ampliar EXPECTED_POLICIES sem modificar seu verificador.

## 2. Integração do cancelamento

Novo `test_lot_cancellation.py`, usando fixtures reais, `integrity()`/
`integrity_secrets()` de testes, helpers de lotes e autenticação. Não ler arquivos
de configuração secretos. SQL direto é somente preparo/adulteração no banco de
teste; o caminho de ação passa pelo serviço/HTTP real.

| ID | Cenário e assert principal |
| --- | --- |
| I01 | Owner cancela agendado vazio íntegro → 200, ID certo, timestamp UTC pós-lock |
| I02 | Owner cancela live vazio íntegro → 200; resposta exata de duas chaves, no-store |
| I03 | Sem bids e now>=ends_at → 422 lot_ended; igualdade exata coberta com now controlado delegando a leitura real |
| I04 | Um bid criado pelo serviço real → 422 lot_has_bids; carteira do líder intacta; com fim vencido continua has_bids |
| I05 | Outro AUCTIONEER → 403; gate não chamado, inclusive se lote adulterado/cancelado |
| I06 | BIDDER → 403 antes do serviço; anônimo/expirado → 401; zero DML. Com UUID malformado a policy também vem antes da validação do path: BIDDER → 403 e anônimo → 401, nunca 422 |
| I07 | UUID válido inexistente → 404; AUCTIONEER autorizado com UUID malformado → 422 uuid_parsing, sem serviço (o 422 só vale para quem passou pela policy; BIDDER e anônimo ficam no I06). Não altero a infraestrutura FastAPI para forçar 422 |
| I08 | Estado adulterado detectável pelo gate → 409 neutro, nenhuma escrita/assinatura nova; prevalece sobre fim/bids |
| I09 | anchor_hmac NULL, inclusive vazio → 409, sem repair |
| I10 | Re-cancelamento íntegro → mesmo timestamp original e resposta, inclusive depois do ends_at |
| I11 | Recorder no segundo cancelamento prova zero UPDATE/INSERT/DELETE; não basta comparar timestamps |
| I12 | Cancelado com âncora/histórico adulterado → 409 antes da idempotência; sem assinatura nova |
| I13 | Snapshot de todas as wallets antes/depois de sucesso/recusa/idempotência igual; nenhum wallet lock nem SELECT de carteira no cancelamento |
| I14 | Em sucesso só cancelled_at muda; comparar bids completos, bid_count, current_*, ends_at, final_hash e anchor_hmac; validar cadeia/âncora independentemente |
| I15 | Novo GET pós-commit: cancelado fora da vitrine, detalhe/bids e bids/mine (BIDDER) 404; caso só cancelados preserva as_of e listas vazias |
| I16 | MyLots contém cancelado do owner com campos exatos, as_of/fase coerentes, ordenação; vazio e só cancelados; sem DML/lock explícito/AIC |
| I17 | Demo cancelado não conta: seed cria outro se não há válido; não altera o antigo; novo boot não duplica; com outro válido não cria |
| I18 | POST bids em cancelado íntegro → 422 lot_cancelled sem wallet lock/DML; cancelado adulterado/anchor NULL → 409; mesmo se scheduled/ended |

Em I08 uso poucos ataques representativos: histórico real presente com resumo
zerado, truncamento e assinatura trocada. Não repito toda T-GATE. Para preparar
corruptos que violam CHECK, reutilizo suporte de teste de remoção/restauração
restrita de constraints; isso nunca entra no runtime.

Adiciono testes focados de guard 403 csrf/415 sem corpo e sem efeito; falha injetada
após flush do cancelamento e antes de COMMIT → 500 e cancelled_at NULL em nova
sessão. Um recorder delegante verifica ordem `FOR UPDATE lots → clock_timestamp →
SELECT bids → UPDATE lots → commit`, um clock por operação e apenas uma coluna no
SET. Recusas liberam lock antes de retornar. Provo com chamada posterior em outra
sessão, sem lock pendente. Teste de relógio envolve `database_now` real: registra o
instante retornado e exige igualdade com persistido/respondido; a fronteira exata
usa wrapper controlado, separada da prova de PostgreSQL real.

Testes pinados existentes recebem mudanças explícitas: catálogo MESSAGES,
mensagem INTEGRITY_BODY dos lances, BidRefusal incluindo lot_cancelled, schemas
OpenAPI, MyLots vazio/chaves, listas de colunas/constraints/FKs. Alguns testes de
leitura atuais só aceitam statements começando SELECT; passam a reconhecer WITH
clock SELECT, continuando a rejeitar DML e FOR UPDATE. Não remover essas asserções.
Revisar testes de downgrade antigos para fixar 0005 onde sua expectativa é 0005;
não usar head com lista de colunas de uma revisão anterior. `LOT_COLUMNS` em
lot_support e comparações `[:-5]` da 0005 exigem ajuste consciente com a nova coluna.

## 3. C1/C2/C3 — PostgreSQL real

Reutilizo `hold_bid`, `run_bid`, `watch_statement`, `before_statement`,
`db_snapshot`, `lot_state`, `bid_rows`, `assert_authenticated`, `assert_invariants`
e `wallet_row`. Crio somente helper local `hold_cancel`/`run_cancel` no teste novo.
Um live lot novo e assinado por rodada, fim +1h, primeiro bid válido e saldo
suficiente tornam os dois resultados possíveis. Nenhum mock substitui o lock ou
gate na prova de concorrência.

**Sincronização robusta.** Cada worker tem Session/conexão própria; evento registra
que B chegou ao statement do lock. Identifico PIDs A/B via `pg_backend_pid()` na
conexão de cada worker antes da operação. Observador em terceira conexão consulta
`pg_blocking_pids(B)` contendo A, `pg_stat_activity.wait_event_type='Lock'` e
`pg_locks` para espera não concedida. Só libero A após essas condições e B ainda
vivo. O helper atual `wait_for_blocked_lock` detecta “alguém esperando”; sozinho
não prova qual worker, então o complemento local restringe pelos PIDs. Polling
curto do catálogo com deadline é observação, não sleep usado como prova.
Timeouts finitos (padrão atual 10s para eventos e join 15s), exceções retornadas ao
teste, finalmente commit/rollback de A e join/cleanup de B; timeout reprova em
vez de pular. Não instalo timeout/retry no serviço produtivo.

| Caso | Arranjo e execução | Resultado exigido |
| --- | --- | --- |
| C1 | A chama cancel_lot real e mantém transação sem commit; B chama place_bid e espera comprovadamente o mesmo lock; confirmar A | A CancelledLot/HTTP 200; B LOT_CANCELLED/HTTP 422 |
| C2 | A chama hold_bid real sem commit; Session B já carregou Lot vazio antes de A; B chama cancel_lot e espera comprovadamente; confirmar A | A PlacedBid/HTTP 201; B LOT_HAS_BIDS/HTTP 422; releitura ignora identity map antigo |
| C3 | Dois workers liberados por threading.Barrier(2) imediatamente antes de executar os serviços reais, em cinco rodadas independentes | Só os pares de C1 ou C2, nenhum erro/500 ou par híbrido |

C1/C2 determinam ambas as ordens; não exijo que a corrida livre observe as duas
por sorte. Capture response HTTP ao menos uma vez para cada ordem, além dos
outcomes de serviço. Terceira conexão não lê estado final até ambos terminarem.

**Oráculo completo por lote e carteiras**, nunca só status:

- Vence cancelamento: cancelled_at não nulo, rows de bids vazias, count 0, líder e
  atual NULL; final_hash genesis e anchor_hmac iguais ao original; todas wallets
  totais/comprometidos/disponíveis iguais ao snapshot; lance recusado lot_cancelled.
- Vence lance: cancelled_at NULL; um único bid sequence 1, leader e current iguais
  ao bidder/amount; count 1; genesis como previous_hash, final_hash igual ao hash
  desse bid, HMAC validada com segredo sintético correto; total de cada wallet
  intacto, committed do bidder anterior + amount e demais intactas. Cancelamento
  lot_has_bids, sem DML dele.
- Nos dois: `assert_authenticated` e `assert_invariants` independentes, nenhum
  comprometido perdido, nenhum UPDATE cancelado de âncora/ends_at. Snapshots por
  conexão só após commit evitam falso positivo por leitura intermediária.

## 4. Mutation/adversarial pequeno

Uso a numeração do **pedido desta sessão**, diferente do plano histórico da story.
Uma alteração temporária por vez no build futuro, seleção focada deve falhar por
comportamento (não syntax/coleta), restauração conferida e seleção verde novamente.
Sem ferramenta/framework novo. Relatar apenas mutações efetivamente executadas.

| Mutação | Teste que deve matar e evidência |
| --- | --- |
| M1 Decidir `lot_has_bids` com o `bid_count` lido ANTES de `lock_lot`, sem usar o valor recarregado depois do lock (não vale mutante que só lê antes e descarta o valor, por ser equivalente) | C2 preloaded: o bid confirma enquanto o cancelamento espera e o mutante cancela com bid (200), então o teste falha; I04 e o recorder provam que nenhum SELECT de `lots` nem decisão sobre `bid_count` ocorre antes do `FOR UPDATE`, e que a decisão usa só `authenticated.bid_count` |
| M2 Remover lot lock | Recorder falha ausência de FOR UPDATE; C1/C2 não obtêm espera B→A e reprovam com cleanup; não depender só de corrida livre |
| M3 Pular gate | I08/I09/I12 recusam corruptos e legacy com 409; spy delegante confirma gate real precede regra |
| M4 Ignorar lot_has_bids | I04/C2 veem cancelamento indevido; snapshot wallets/estado exige nada cancelado com bid |
| M5 Remover ownership | I05 recebe 200/409 em vez de 403 e/ou chama gate alheio |
| M6 Remover lot_ended | I03 para ended e igualdade deve recusar, sem UPDATE |
| M7 Usar relógio Python | I01/I02 com captura do database_now real exigem mesmo instante gravado/respondido; recorder exige um clock pós-lock. Variante troca database_now por now Python também falha recorder |
| M8 Retornar already-cancelled antes do gate | I12 exige 409 e prova chamada do gate; I10 controle íntegro continua 200 |
| M9 extra: remover o filtro ou colocá-lo no WHERE, **só** nas três consultas com LEFT JOIN/relógio (vitrine, detalhe, sala); `/bids/mine` não tem JOIN e seu WHERE é o correto, fora da mutação | I15 com só cancelados detecta vazamento/perda de as_of; I17 detecta seed sem novo demo |

Não adiciono mutação do core criptográfico ou financeira já coberta pela 3.4.

## 5. Frontend

`node --test`: `lotCancellation.test.ts` para matriz eligibility (live/scheduled
vazio, ended, com bid, cancelado, cancelado+ended), classificação status+code sem
usar message, ambíguo e textos; `api/lots.test.ts` para contrato MyLots/200 cancel
válido e inválido/ID divergente/nullable; testar request cancel sem body e sem
retry. Estender `api/bids.test.ts` e `bidFeedback.test.ts` com 422 lot_cancelled e
texto exato; demais recusas continuam com testes existentes.

Playwright agrega confiança de DOM/requisições que lógica pura não prova:
`e2e/my-lots.spec.ts`, mock API stateful com contratos distintos para criação,
lista e cancelamento. Casos: CTA só elegível; Cancelado precede fase; inline
Confirmar/Voltar e foco correto; clique+Enter durante POST atrasado emitem um POST;
200 causa um refetch e item permanece com selo; has_bids/ended exibem texto e
refetch; 409 neutro; 403 e 401 callback; network/500/200 inválido emitem uma
releitura sem segundo POST e sem afirmar resultado. Incluir sucesso com refetch
falho e ambíguo com releitura falha. Resposta antiga não substitui snapshot novo
ou tela desmontada. Contar requests, não só procurar texto.

Um cenário no `lot-room.spec.ts` existente comprova texto lot_cancelled sem mudar
sincronização; mock mode novo. Checar teclado, alvos/foco e 320px com título longo,
50 lotes e imagem quebrada no MyLots; demais testes visuais da sala são herdados.
Playwright continua opt-in `VERIFY_E2E=1`, Chromium; nenhuma biblioteca de teste
de componente nova. No build executar verify e E2E pertinente, registrar saídas
reais e limitar evidências ao que foi executado. Roteiro humano curto: cancelar
agendado/live, conferir selo/vitrine/link 404, tentar lote com lance e revisar erro
ambíguo simulado. Esta rodada não executa verify, build ou testes de produto.
