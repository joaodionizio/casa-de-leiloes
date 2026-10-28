# Review final da Story 4.3 — 27/10/2026

## Fechamento formal — gate aprovado

Os LOWs **F43-01 e F43-02 foram resolvidos por cobertura específica**, com
respectivas mutações focais detectadas. Não foi encontrado defeito funcional de
produção, nem achado HIGH ou MEDIUM. O **gate final está aprovado** e a Story
4.3 foi marcada como done por instrução humana. As conclusões e estados anteriores
abaixo permanecem como histórico do review; produção não mudou após o review.

## Ajuste posterior dos LOWs — 27/10/2026

F43-01 e F43-02 receberam testes de regressão em
`backend/tests/integration/test_lot_settlement.py`. O primeiro altera somente
`winner_user_id` de ALICE para BOB após settlement sold válido. O segundo
liquida um lote sem lances como unsold, altera somente `ends_at` para uma hora
após o settlement e testa tanto o retry quanto a tentativa de cancelamento.
Ambos exigem `settlement_mismatch`, ausência de escritas e snapshot preservado.

O pedido inicial mencionava um settlement válido de lote já cancelado; o serviço
recusa essa sequência. O usuário autorizou usar o cenário de cancelamento posterior
descrito neste review. Cada proteção foi removida separadamente em memória:
o teste de F43-01 detectou o retorno `already_settled` e o de F43-02 detectou
`CancelledLot`. Não houve edição de produção. Os resultados originais abaixo
permanecem como histórico do review; os LOWs de cobertura foram tratados, sem
nova decisão de aceite ou mudança de status da story.

Validação posterior: os dois testes isolados passaram; a suíte da Story 4.3
teve **83 passed, 1 warning in 12.05s**. `./verify.sh` terminou com exit 0:
backend **2166 passed, 1 warning in 117.98s**, frontend **175 passed**,
Ruff, lint, typecheck, build frontend e Docker aprovados. Playwright não foi
executado. O warning é a depreciação Starlette/httpx já conhecida.

## Resultado

**APROVADA COM LOWS.** Não confirmei defeito funcional, financeiro, transacional,
de concorrência, integridade, privacidade ou persistência no código atual que
impeça fechar a story. Confirmei duas lacunas de regressão, classificadas LOW:
as proteções existem e funcionam, mas podem ser removidas sem reprovar PG01–35.
Não equiparo esses mutantes ao comportamento da implementação entregue.

Revisei o estado atual sem Git, contra story/spec/companions e arquitetura,
com as cinco perspectivas da skill bmad-code-review e triagem própria.
Usei Astra/High nos revisores independentes. Uma consulta complementar ao
revisor documental terminou por limite de uso depois de seu parecer inicial;
não alego segunda passagem documental integral concluída por esse revisor.

## F43-01 — LOW — Retry não tem teste de vencedor interno adulterado

- **Arquivo/trecho:** `backend/tests/integration/test_lot_settlement.py:408`,
  PG23/31; proteção atual em `backend/app/lot_settlement.py:332`.
- **Problema concreto:** a matriz de adulterações não modifica somente
  `lot_settlements.winner_user_id`. A asserção de vencedor em PG01 cobre criação,
  mas não esse vínculo no retry.
- **Cenário reproduzível:** liquidar sold de ALICE; alterar apenas o vencedor do
  settlement para BOB, usuário existente diferente do leiloeiro; manter cadeia,
  âncora, receipt e demais campos. FK/CHECK continuam válidas. O código atual
  retorna `IntegrityConflict(settlement_mismatch)`, preservando o snapshot.
- **Impacto:** se a comparação com `last.bidder_id` regredir, o retry passa a
  devolver `already_settled` com identidade interna errada. Não há dupla
  transferência demonstrada nem defeito desse tipo no código atual.
- **Por que os testes não pegam:** PG23/31 adultera timestamp, valor do receipt,
  HMAC e bid, mas não o vencedor interno isoladamente. Removi essa comparação
  apenas em memória, junto do mutante F43-02: os 81 testes continuaram passando.
  Uma prova adicional do cenário retornou `already_settled` no mutante.
- **Recomendação:** acrescentar a variante isolada a PG23/31, comprovar gate
  íntegro e exigir conflito, zero escrita e snapshot preservado.
- **Encaminhamento:** **corrigir agora**, como reforço pequeno de testes;
  recomendação não bloqueante. Nenhuma correção aplicada.

## F43-02 — LOW — Cancelamento não testa terminal unsold com prazo futuro

- **Arquivo/trecho:** `backend/tests/integration/test_lot_settlement_concurrency.py:348`
  e `backend/tests/integration/test_lot_settlement.py:483`; proteção atual em
  `backend/app/lot_cancellation.py:88`.
- **Problema concreto:** PG21 cancela depois do fechamento com prazo já vencido.
  A recusa temporal antiga basta para fazê-lo passar sem a guarda de settlement.
  PG24 altera o prazo, mas só verifica retry de settlement e lance.
- **Cenário reproduzível:** liquidar unsold; mover `ends_at` para uma hora após
  `settled_at`; tentar cancelar como dono. O código atual retorna
  `IntegrityConflict(settlement_mismatch)`, sem mudança no snapshot.
- **Impacto:** sem a guarda terminal, o serviço aceita `CancelledLot` e grava
  `cancelled_at` apesar do settlement. A rota existente confirmaria e publicaria
  o cancelamento. Essa regressão exige prazo inconsistente; não ocorre hoje.
- **Por que os testes não pegam:** a fixture de PG21 mantém a proteção temporal
  suficiente; não há a combinação terminal unsold + prazo futuro + cancelamento.
  Removi a guarda somente em memória junto de F43-01: os 81 testes passaram.
  A prova adicional confirmou `CancelledLot` persistido no mutante.
- **Recomendação:** adicionar a variante unsold a PG24, tentar cancelamento e
  exigir conflito, zero escrita e snapshot completo preservado.
- **Encaminhamento:** **corrigir agora**, como reforço pequeno de testes;
  recomendação não bloqueante. Nenhuma correção aplicada.

## Auditoria dos pontos solicitados

| Pontos | Conclusão e evidência |
| --- | --- |
| 1, 12, 16 — sequência e tempo | `lock_lot` usa FOR UPDATE/populate_existing; clock PostgreSQL depois do lock; prazo vem do objeto relido. Mesmo now em settlement/receipt. Sem datetime.now local ou autoridade pré-lock no comando. |
| 2 — bid × close | PG05/35 prova E+2min e depois E+4min; closer espera além de E e retorna not_due. PG06 prova close primeiro, lance posterior recusado. Sessions/PIDs independentes, observador de pg_blocking_pids e sobreposição real. |
| 3 — dois closers | PG07 cobre sold/unsold e commit/rollback de A. O lock serializa antes de consultar o terminal; UNIQUE é defesa adicional. Carteiras são travadas por UUID crescente, como nos bids; não há aquisição posterior de outro lote. |
| 4 — dinheiro | W recebe T−F/C−F num UPDATE conjunto; S recebe T+F/C constante. PG01/09/19 verificam disponível, reservas alheias, perdedor e conservação; PG10/30 cobre teto exato e excesso com rollback. Nenhuma dupla liberação. |
| 5, 6 — estados impossíveis e retry | Gate autentica histórico e vínculo operacional; ramo terminal compara outcome, winner, alias, bid, F, count/hash/HMAC, prazo e receipt. Sold sem receipt e unsold com receipt são conflitos. Constraints cobrem nulidade/FKs locais; igualdade entre tabelas é responsabilidade explícita do serviço. F43-01 é lacuna de teste, não ausência da proteção. |
| 7 — ACK versus aborto | PG22 instala trigger de constraint diferida e o PostgreSQL aborta COMMIT. PG34 chama super().commit() real antes de lançar falha sintética; nova Session vê tudo e retry não altera snapshot. Não é prova de queda física de rede. |
| 8 — rollback | PG11 injeta falhas antes dos statements e pré-commit, incluindo depois do primeiro efeito financeiro e depois do settlement; snapshot independente de lote/bids/carteiras/settlement/receipt permanece anterior. PG20 retém sucesso até confirmação real. |
| 9 — integridade | Gate completo SHA-256/HMAC e vínculo do último lance antes das carteiras, também no retry. PG13/14/15 cobrem adulterações, legado e histórico além de 50 bids; nenhum reparo/reassinatura. |
| 10, 13 — receipt/readers | ReceiptRecord e tabela têm whitelist pública exata, sem winner_user_id/HMAC/email/carteira. Reader retorna DTO congelado, usa projeção única e autoflush=False; não retorna ORM nem SettlementRecord como receipt. Readers detectam coerência estrutural, sem prometer auditoria criptográfica. |
| 11 — migration | 0007 segue 0006; UUIDs, uniques, FKs compostas, nulidade explícita e CHECKs coerentes com modelos. RESTRICT, sem cascata de exclusão. Downgrade remove receipt antes de settlement; perda dos registros sem estorno financeiro é limite destrutivo já documentado no README, não rotina de recuperação. |
| 14, 15 — pureza e fronteira | PG17/18 confirmam GET/refresh/HEAD/OPTIONS/handshake/reconexão/heartbeat sem liquidação. Nenhuma integração nova com scheduler, startup, catch-up, manager/evento de encerramento ou painel. |
| 17 — qualidade PG01–35 | Revisei casos e oráculos, além de executá-los. Bloqueio comprovado por PID, snapshots independentes e fault injection distinguem preparação/commit/ACK. As duas lacunas acima sobrevivem a mutações adicionais. |
| 18 — cinco mutações anteriores | M3 e M4 serem barradas por CHECK/NOT NULL não invalida sua detecção: os testes exigem retry/unsold bem-sucedidos. Não classifiquei o oráculo indireto como finding. As cinco mutações anteriores não foram reexecutadas nesta rodada. |
| 19 — schema estrito | `test_database.py` continua comparando lista exata: alembic_version, bids, lot_settlements, lots, receipts, users, wallets. Apenas as duas tabelas novas foram acrescentadas. |
| 20 — regressões | Backend completo passou. Comparação local do auditor confirmou preservação de bid_integrity, bid_rules, wallet, lots, lot_room, main e migrations anteriores. Frontend/Playwright não foram reexecutados nesta rodada; os números anteriores permanecem evidência histórica. |

## Execução independente desta rodada

- PG01–35, implementação original: **81 passed, 1 warning in 12.08s**, exit 0.
- Backend completo, implementação original: **2164 passed, 1 warning in 120.13s**, exit 0.
- Dois mutantes adicionais simultâneos, exclusivamente em memória:
  **81 passed, 1 warning in 11.79s**, exit 0. Isso confirma a lacuna dos dois
  predicados; não é resultado de validação da implementação original.
- Provas isoladas em PostgreSQL: original recusou ambos com settlement_mismatch;
  mutantes aceitaram vencedor incoerente e cancelamento terminal, respectivamente.
- Warning herdado de Starlette/httpx. Não executei verify completo, frontend,
  Playwright nem deploy nesta rodada.
- PostgreSQL dedicado `_test`, com guards de destino; dotenv desativado no
  Pydantic e abertura de `.env*` bloqueada por audit hook externo em `/tmp`.
  Uma proposta agrupada foi rejeitada pela revisão automática por não reconhecer
  proteção explícita em todas as invocações; não executou. As execuções separadas,
  com flags explícitas e o mesmo bloqueio de arquivo, foram autorizadas.
- Provas encerradas e schema de teste restaurado a head. Comparei novamente os
  dez arquivos de código/migration/testes com o snapshot inicial: idênticos.
- Evidência temporária: `/tmp/story43-final-review-pt8cxygx/` (XMLs, log backend,
  plugin de mutação, guardas e reproducer). Nenhum segredo real foi lido.

## Gate final da Story 4.3

Na minha avaliação, **sim**: a implementação atual está segura para mudar a
story para `done`, atualizar sua entrada do sprint para `done` e receber o commit
único contendo story + spec + migration + código + testes + docs. Os dois LOWs
são reforços de cobertura recomendados, sem bloqueio funcional demonstrado.

Não alterei esses statuses nem executei Git; a decisão e o commit permanecem
com o usuário. Não corrigi código/testes/configuração nem iniciei a Story 4.4.
Registrei apenas este parecer e os itens de review na story.

**APROVADA COM LOWS**
