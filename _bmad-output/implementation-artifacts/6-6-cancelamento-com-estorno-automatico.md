---
title: 'Story 6.6 — Cancelamento com estorno automático'
type: feature
created: '2026-10-29'
status: review
route: dispatch
context:
  - CLAUDE.md
  - docs/ARQUITETURA.md
  - _bmad-output/planning-artifacts/DESIGN.md
  - _bmad-output/planning-artifacts/EXPERIENCE.md
---

<frozen-after-approval reason="escopo e regras transacionais aprovados explicitamente pelo usuário">

## Intent

Decidi ampliar o cancelamento existente para lotes próprios agendados/ao vivo com lances, liberando exatamente o compromisso do líder atual. Descartei fluxo paralelo, ledger, migration e rota nova. 6.5–6.7 foram inicialmente cortadas por prazo após a entrega obrigatória e posteriormente reativadas por decisão humana para implementar os opcionais.

## Boundaries & Constraints

Ordem obrigatória na mesma transação: lock_lot → clock_timestamp único após trava → dono → read_history → authenticate_previous_state → settlement terminal → cancelamento idempotente → fim → lock_wallet do líder do estado autenticado → invariantes financeiras → subtrair só current.amount_cents do committed → cancelled_at → flush → commit na rota → sinal apenas pós-commit e transitioned. Total inalterado; disponível derivado. Sem lances, nenhuma carteira. Verificar committed >= amount e limites existentes; exceção interna/genérica coerente com settlement, rollback sem detalhes financeiros no cliente. Não alterar/apagar bids, sequência, hashes, final_hash, anchor_hmac, current_bid_cents, current_leader_id ou bid_count. Integridade precede idempotência, que não duplica refund/sinal/timestamp. Ended/settled recusam. Auditoria pública deve aceitar histórico íntegro de cancelado com lances, preservando detecção de adulteração e cancelado+settlement inválido.

Frontend permite cancelamento scheduled/live próprio com/sem lances, nunca ended/cancelled ou BIDDER. Com lances confirmar: “Este lote possui lances. Ao cancelar, o saldo comprometido do licitante líder será liberado automaticamente.” CTA “Cancelar lote”. Sem identidade do líder; sucesso atualiza painel/cancelado e Vitrine exclui. Proteger double submit e não anunciar falso sucesso. Manter rota POST /api/lots/{lot_id}/cancel e sete escritas.

Nunca executar Git, gh, deploy, review independente ou gate integral neste bloco; nunca ler .env*, credenciais ou segredos. Não pedir nova aprovação. Testes reais usam só PostgreSQL dedicado de teste; não alterar banco de desenvolvimento. Se precisar subir Docker/loopback e sandbox bloquear, usar escalation justificada. Segredos de teste gerados em memória sem impressão. Não mudar precedência de lances AD-7.

## I/O & Edge-Case Matrix

| Cenário | Entrada | Saída |
| --- | --- | --- |
| Cancelar | scheduled/live, com/sem lances | sucesso, reserva exata liberada, total imóvel, histórico íntegro |
| Repetir | já cancelado íntegro | mesmo sucesso/timestamp, sem novo efeito ou sinal |
| Negar | não dono/BIDDER/ended/settled/adulterado | 403/403/422/422/409; zero efeitos |
| Falha | wallet inconsistente ou erro entre refund e cancel | rollback integral, erro genérico |
| Cancel × bid | cancel ganha / lance ganha | serial: lance recusado / novo líder autenticado estornado |
| Cancel × settlement | cancel válido antes do fim / settlement devido ganha | cancelado não liquida / terminal não é desfeito |

</frozen-after-approval>

## Code Map

- `backend/app/lot_cancellation.py`: remover recusa por bid_count; reutilizar `app.wallet.lock_wallet` e estado autenticado de `app.bids`.
- `backend/app/lot_audit.py:_verified`: antiga proibição cancelado+bids deve permitir bids, mantendo cancelado+settlement inválido.
- `backend/tests/integration/test_lot_cancellation.py`, `test_lot_cancellation_concurrency.py`, `test_lot_settlement_concurrency.py`, `test_lot_room_ws.py`: ampliar contratos antigos, corridas reais com pg_locks e sinais pós-commit.
- `backend/tests/bid_support.py`, `cancel_support.py`, `wallet_support.py`: helpers de transações/SQL; `test_csrf.py` e `test_access_policy.py`: inventário/guardas.
- `frontend/src/lotCancellation.ts`, `MyLots.tsx`, `lotCancellation.test.ts`, `frontend/e2e/my-lots.spec.ts`, `support/mockApi.ts`: elegibilidade, confirmação/refund, mocks coerentes.
- `frontend/src/api/audit.ts`, `audit.test.ts`: retirar exigência antiga de bid_count=0 no cancelado sem permitir settlement.

## Tasks & Acceptance

- [x] Serviço: refund transacional, invariantes, idempotência e publicação pós-commit sem nova escrita HTTP.
- [x] Auditoria backend/frontend: cancelado com cadeia autêntica permanece verified e íntegro.
- [x] Painel: elegibilidade e confirmação, sem regressão de cancelamento vazio ou erro/double submit.
- [x] PostgreSQL real: matriz inteira, reserva em outro lote preservada, total/disponível, histórico/hash/âncora, rollback, corrupt wallet, scheduled com histórico, autorizações e corridas em ambas as ordens.
- [x] Testes focais Node/Playwright e regressão `test_csrf.py`/`test_access_policy.py`; registrar resultados reais neste artefato e deixá-lo em review.

**Critérios:** Dado lote cancelável com líder autenticado, quando cancelo, então só sua reserva vigente é liberada sob lote→carteira e auditoria permanece íntegra. Dadas operações concorrentes, quando esperam a trava, então equivalem à ordem serial sem saldo preso/negativo, duplicação ou liquidação desfeita.

## Implementation Notes

Implementação autorizada como segundo bloco. Não executar review independente ou gate integral; coordenação fará um único gate combinado final. Usar banco Docker isolado se necessário, documentando comandos e sem tocar dev. Alterações além do mapa necessárias a estes critérios devem ser relatadas. Preservar mudanças prévias do usuário e story 6.5.

## Verification

PostgreSQL isolado já preparado: DATABASE_URL=postgresql://atrio_test:atrio_local_test@127.0.0.1:55436/atrio_optionals_dev TEST_DATABASE_URL=postgresql://atrio_test:atrio_local_test@127.0.0.1:55436/atrio_optionals_test APP_ORIGIN=http://localhost:5173. São valores fictícios do container descartável atrio-optionals-test-20261029, sem vínculo com dev. Usar esses valores ao executar pytest em backend; sandbox pode exigir escalation para loopback. Não iniciar outra instância nem parar o container compartilhado desta rodada.

Ruff focais, pytest PostgreSQL dos arquivos afetados e segurança de sete escritas, Node de cancelamento/auditoria e Playwright painel/auditoria/WS pertinentes. Cobrir todos os cenários da matriz com testes executados, não skips. Reportar limites materiais, comandos e arquivos.


### Implementação e verificação executadas — 29/10/2026

Implementei a liberação exata de `authenticated.current.amount_cents` na carteira
travada do líder autenticado, preservando o total, os compromissos de outros lotes e
todos os campos do histórico/âncora. Reutilizei os conflitos financeiros internos do
settlement para falhas genéricas com rollback. Mantive a ordem aprovada, a rota
existente e a publicação pós-commit apenas quando `transitioned` é verdadeiro.

A auditoria backend/frontend agora aceita cancelado com cadeia autêntica e continua
recusando cancelado com settlement e adulteração. No painel habilitei lotes próprios
agendados/ao vivo com lances, com a confirmação aprovada e CTA “Cancelar lote”.
Preservei a proteção contra envio repetido e os estados de erro/incerteza.

Além do Code Map original, alterei `frontend/src/api/lots.ts` e `lots.test.ts` para
retirar a recusa obsoleta `has_bids`, e `frontend/e2e/audit.spec.ts` para comprovar a
cadeia pública do cancelado com lances. Não criei migration, ledger ou escrita HTTP.

Resultados finais, sem skips:

- PostgreSQL real dedicado `atrio_optionals_test` na porta 55436: **451 passed**,
  em **34.88 s**, com um aviso preexistente de depreciação Starlette/httpx. Executei
  `tests/integration/test_lot_cancellation.py`,
  `test_lot_cancellation_concurrency.py`, `test_lot_settlement_concurrency.py`,
  `test_lot_room_ws.py`, `test_lot_audit.py`, `tests/test_csrf.py` e
  `tests/test_access_policy.py` com `.venv/bin/python -m pytest ... -q`.
  Usei as URLs descartáveis explícitas desta seção e
  `PYTHONPATH=/private/tmp/atrio-optionals-noenv`, que desabilita instrumentalmente
  a fonte dotenv sem alterar o produto. As execuções finais não leem `.env*`.
- Node: `node --test src/lotCancellation.test.ts src/api/audit.test.ts
  src/api/lots.test.ts` → **19 passed**.
- Playwright: `npm run test:e2e -- my-lots.spec.ts audit.spec.ts
  lot-room-ws.spec.ts --workers=4` → **89 passed**, em **10.8 s**;
  o comando também executou o build de produção para o preview local.
- `npm run typecheck` e ESLint dos dez arquivos TypeScript/TSX alterados → verdes.
- Ruff check e format check dos sete arquivos Python alterados → verdes.

Cobri cada linha da matriz com testes executados: scheduled/live com e sem
histórico; repetição sem nova escrita/timestamp/sinal; dono, papel, fim, settlement
terminal e histórico/ponteiros adulterados; carteira ausente, compromisso insuficiente
e invariantes inválidas; rollback após UPDATE de carteira/lote e antes do commit;
primeiro lance e troca de líder concorrentes em ambas as ordens; dois cancelamentos;
cancelamento antes do fim com closer efetivamente devido após esperar a trava,
e settlement vencedor sem reversão. As corridas de reserva/terminal usam conexões
reais com bloqueio observado em `pg_blocking_pids`, além da corrida livre existente.

As primeiras rodadas encontraram o helper antigo somando reservas de cancelados e
seletores Playwright ambíguos após a troca do CTA; corrigi ambos antes dos resultados
finais acima. Não executei Git, gh, deploy, review independente ou gate integral.
O gate combinado e o smoke real complementar permanecem com a coordenação; a
limitação existente entre commit e publicação (sem outbox) permanece aceita.


Gate conjunto final: VERIFY_E2E=1 ./verify.sh exit 0; 2446 backend, 206 Node,
355 Playwright, Docker aprovado. Real-stack separado 7 passed e smoke financeiro
real aprovado. Resultado e limites em [FECHAMENTO-EPICO-6.md](../../docs/FECHAMENTO-EPICO-6.md).
Estado review; review agregado independente dos opcionais pendente.
