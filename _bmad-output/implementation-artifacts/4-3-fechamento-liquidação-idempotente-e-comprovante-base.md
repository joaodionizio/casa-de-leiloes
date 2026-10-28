# Story 4.3 — Fechamento, liquidação idempotente e comprovante base

Status: **done** — fechamento documental autorizado em 27/10/2026 após review e resolução dos LOWs de cobertura.

## Objetivo e fronteira

Como licitante vencedor e leiloeiro, quero apurar o lote expirado uma única vez, debitando vencedor, creditando leiloeiro e persistindo settlement/receipt, para que concorrência, repetição e falha não gerem cobrança duplicada ou liquidação parcial.

Decidi expor só serviço/readers internos chamados diretamente pelos testes, sem rota HTTP. Settlement próprio é o registro econômico autoritativo, receipt separado apenas se sold. Unsold registra apuração sem vencedor/preço/receipt. Descartei scheduler/catch-up/gatilho em lance/evento/publicação (4.4), painel (4.5), auditoria pública/link/meus arremates (5.1–5.3), nova contabilidade e alterações WS/UI/máquina 4.2.

## Contrato formal canônico

Leio [SPEC.md](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/SPEC.md) e todos os companions nele declarados:

- [Estado atual e mapa do build](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/current-state.md).
- [Transação, idempotência e falhas](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/transaction-contract.md).
- [Invariantes e tabela financeira](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/financial-invariants.md).
- [Schemas e contratos finais](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/data-contracts.md).
- [Concorrência](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/concurrency-model.md).
- [CA01–21 e testes PG01–35](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/acceptance-and-tests.md).
- [QH-01–10 decididas](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/human-decisions.md).
- [Revalidação](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/validation.md).

## Sequência e persistência finais

Lot lock → clock_timestamp pós-lock → reler ends_at → verificar settlement/terminal → gate/revalidação → carteiras por user_id se nova sold → consumir F reservado/debitar W/creditar S → INSERT settlement → INSERT receipt só sold → commit único → retorno confirmado. Nunca fechar now<ends_at ou decidir com prazo anterior ao lock. Novo commit confirmado é o único caminho com transitioned=true; a 4.3 não publica evento.

lot_settlements: id UUID PK, lot_id UNIQUE, outcome sold/unsold, winner_user_id/alias/winning_bid_sequence/final_amount_cents nullable só unsold, bid_count/final_hash/anchor_hmac/settled_at obrigatórios. Receipt separado: id UUID PK, lot_id UNIQUE, settlement_id UNIQUE, winning_bid_sequence, winner_alias/F/settled_at/count/hash. **Nenhum winner_user_id ou HMAC no schema do receipt**. FK composta une receipt ao settlement do mesmo lote.

winning_bid_id conceitual usa a PK existente (lot_id,sequence), com winning_bid_sequence/FK composta; não crio bids.id nem altero canonical bid v1. Metadados públicos continuam em lots; sem snapshot extra/link.

## Resultados, revalidação e finanças

Statuses finais: settled_sold/settled_unsold (true após commit), already_settled (false com registros persistidos/revalidados) e not_due (false sem liquidação). Integridade/financeiro são falhas tipadas, não sucessos; inexistente/cancelado continuam caminhos separados sem efeitos. Readers internos puros por lot_id recuperam settlement/receipt, sem API.

A=T−C; W vira (T−F,C−F,A), S vira (T+F,C,A+F); ΣT conservada. Outros compromissos e perdedores ficam intactos: Epic 3 já liberou superados. CHECK imediata requer UPDATE conjunto T/C do vencedor. Teto excedido causa conflito financeiro tipado e rollback total, sem settlement/receipt; a 4.4 cuidará da condição operacional sem retry quente infinito.

Retry confere lote/settlement/referências e receipt obrigatório em sold/ausente em unsold; incoerência retorna IntegrityConflict, sem reparar/sobrescrever/recriar/reliquidar/carteiras. Não exigir de novo a reserva já consumida. Falha de INSERT receipt ou COMMIT abortado reverte tudo; ACK perdido é ambíguo e retry em nova Session descobre commit sem duplicar transferência.

Settlement status pending/settled é separado de phase; outcome existe só settled. Fim alcançado sem settlement continua “Encerrado, apurando resultado”, com GET/HEAD/OPTIONS/handshake sem mutação. Não alterar room_snapshot/bid_accepted/máquina 4.2/UI/painel.

## Decisões humanas fechadas

| ID | Decisão final |
| --- | --- |
| QH-01 | Serviço interno, sem HTTP, gatilhos/evento futuros na 4.4 |
| QH-02 | lot_settlements autoritativo com ID próprio e UNIQUE lot_id, sold e unsold |
| QH-03 | Receipt seguro separado, ID próprio e UNIQUE lote/settlement; só sold |
| QH-04 | Readers internos por lot_id, nenhuma nova API |
| QH-05 | Resultado discriminado, true só pós-commit, retry revalidado sem escrita |
| QH-06 | HTTP não aplicável; orientação futura 200 novo/repetido |
| QH-07 | Eixo pending/settled e sold/unsold independente; sem WS/UI agora |
| QH-08 | Teto preservado e rollback/conflito tipado; mecanismo operacional na 4.4 |
| QH-09 | Âncora validada congelada internamente; receipt sem HMAC; v1 intacto |
| QH-10 | Revalidar repetição e falhar sem reparo/reliquidação se incoerente |

Nenhuma questão humana aberta desta story. Alternativas descartadas registradas no companion de decisões; recomendações anteriores incompatíveis foram substituídas no contrato, sem apagar a memória histórica.

## Critérios e tarefas

CA01–18 preservados e CA19–21 acrescentados: outcomes/teto tipado, retry inconsistente e fronteira interna sem mudanças públicas. PG01–24 preservados e PG25–35 acrescentados, um por prova adicional humana: disponível W constante, reserva alheia, unsold com settlement, sold com receipt exclusivo, privacidade no schema, teto rollback, adulteração, sold sem receipt, unsold com receipt, ACK perdido/retry e AD-5 cumulativa.

- [x] Ler fontes e retomar memória/capacidades do draft.
- [x] Consolidar QH-01–10 por decisão humana e rederivar SPEC/companions.
- [x] Formalizar transação/schemas/outcomes/concorrência/invariantes/testes finais.
- [x] Revalidar coerência/preservação, conferir arquivos e registrar IA; promover ready-for-dev sem autorizar código.
- [x] Obter autorização separada de implementação; build autorizado em 27/10/2026.
- [x] No build, implementar só 4.3, executar PG01–35, mutações, dois verifies e smoke transacional com saída real.
- [x] Review independente do código e aceite humano; não iniciar 4.4 automaticamente.

## Resultado documental e tracking

Coerência e preservação revalidadas; contrato pronto para desenvolvimento, sem autorização de código. Após a conferência final, promovi story e sprint para ready-for-dev por instrução humana explícita. Nenhum teste de aplicação/verify/SQL/migration/navegador/smoke/deploy executado nesta sessão; nenhum Git ou .env*; código e testes preservados. 4.1/4.2 mantêm review, Epic 4 in-progress e 4.4/4.5 backlog.

## Build autorizado e concluído — 27/10/2026

Implementei somente serviço/readers internos, `lot_settlements` sold/unsold e
`receipts` somente sold, com migration `0007_lot_settlement.py`. Mantive canonical
v1, SHA-256/HMAC, pseudônimo persistido, AD-5 cumulativa e ordem das travas.
Vencedor T−F/C−F (disponível igual), leiloeiro T+F/C igual, soma dos totais
conservada; reserva alheia preservada, teto e falhas revertem toda a operação.
Retorno transitioned=true só após commit confirmado; repetição revalidada sem
escritas. Protegi o terminal contra novo lance e recancelamento.

Resultados reais: **81 passed, 1 warning in 11.82s** nos PG01–35; cinco mutações
executadas e detectadas, código restaurado. `./verify.sh` exit 0, **2164 passed**,
frontend **175/175**; `VERIFY_E2E=1 ./verify.sh` exit 0, **2164 passed**, frontend
**175/175**, Playwright **222 passed (25.0s), 5 skipped**. Ambos encerraram com
`verify.sh: todas as etapas passaram.`. Primeiro verify teve somente expectativa
antiga de tabelas, corrigida sem afrouxar a enumeração.

Smoke PostgreSQL real exit 0: sold e unsold, retries already_settled/false, um
receipt só sold. W `(80000,32000,48000)` → `(68000,20000,48000)` e leiloeiro
`(5000,0,5000)` → `(17000,0,17000)`; F=12000 e reserva alheia=20000 intacta.

[Relatório completo, matriz PG01–35, arquivos, comandos, limites e falhas iniciais](../specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/implementation-evidence.md).
Primeira rodada exploratória sem guarda contra dotenv implícito; finais
protegidos, sem abertura direta de `.env*`. Nenhum Git ou deploy.
Não executei code review nem criei rota/gatilho/publicação/WS/UI.
Story 4.4 não iniciada. Esta story fica review para nosso aceite/review.

### Review Findings — gate final independente (27/10/2026)

Concluí o review final com **APROVADA COM LOWS**, sem defeito funcional bloqueante
confirmado. Mantive o status em review e o sprint intacto. Relatório e cenários:
[code-review-final-story-4-3.md](code-review-final-story-4-3.md).

- [x] [Review][Patch][LOW][F43-01] Cobertura de adulteração isolada de winner_user_id no retry adicionada e mutação focal detectada.
- [x] [Review][Patch][LOW][F43-02] Cobertura de unsold terminal com ends_at adulterado e tentativa de cancelamento adicionada e mutação focal detectada.

Reexecutei PG01–35 (**81 passed**) e backend completo (**2164 passed**).
Confirmei as duas lacunas por mutações em memória e provas isoladas, sem editar
código ou testes. Descartei bloquear o gate por esses LOWs: são lacunas de
regressão e ambos os cenários são recusados corretamente pela implementação atual.

## Fechamento formal — 27/10/2026

Após o review independente, os dois LOWs foram resolvidos por testes específicos;
nenhum HIGH, MEDIUM ou defeito funcional de produção foi encontrado. O gate final
foi aprovado e a story concluída por instrução humana. Suíte da story: 83 passed,
1 warning conhecido; `./verify.sh`: exit 0, backend 2166 passed e frontend 175
passed. O código de produção permaneceu inalterado após o review. Os relatos de
estados anteriores acima são históricos. Epic 4 permanece in-progress e a 4.4 não
foi iniciada.
