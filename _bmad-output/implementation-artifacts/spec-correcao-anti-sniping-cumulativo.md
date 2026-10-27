---
title: 'Correção isolada da AD-5 cumulativa'
type: 'bugfix'
created: '2026-10-27'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="decisão humana explícita no pedido de 27/10/2026">

## Intent

Decidi voltar à extensão cumulativa: lance válido em `0 < ends_at - now <= 2 min`
soma 2 min ao término vigente; exatamente 2:00 também estende e sinaliza true.
Lance em `now >= ends_at` permanece recusado, sem reabertura. A decisão humana
revoga a fórmula intermediária a partir de `now`. Atualizar primeiro AD-5, depois
apoio histórico sem reescrever o passado, e só então código, mocks e testes.
Usar o mesmo now autoritativo; preservar locks/transação, canonicalização v1,
SHA/HMAC/final_hash, pseudônimo e regras financeiras. Frontend e WS aplicam só
ends_at confirmado. Não alterar máquina WS, dados, schema, .memlog.md nem iniciar
4.3. Não executar Git ou ler .env*. Sem commit; review independente posterior.
Validar limites, sequência 15:00→15:02→15:04→15:06, perto do novo fim, recusas,
concorrência com PostgreSQL real, mutação para fórmula revogada, verify padrão e
VERIFY_E2E=1. Registrar resultados reais e arquivos em nota de evidência.

</frozen-after-approval>

## Implementation Notes

Sem lacunas de intenção ou ações irreversíveis. Correção pequena na regra pura;
documentação sincronizada mecanicamente. Mapa: backend/app/bid_rules.py (evaluate_post_wallet),
backend/tests/test_bid_rules.py, integration/test_bid_routes.py e test_bid_concurrency.py;
frontend/src/bidFeedback.ts e seu teste, frontend/e2e/support/mockApi.ts e lot-room.spec.ts.
Reutilizo a trava real de overlapped e clock_timestamp do PostgreSQL. Docs ativas:
ARQUITETURA, CLAUDE, README, DESIGN; históricos 3.2/3.4/3.5/4.1 e review/deploy,
com nota adicional preservando original. Evidência e uso_de_ia registram validação.

Incluí também backend/tests/integration/test_lot_room_ws.py: a asserção de
transporte ainda comparava o fim com placed_at + 2 min. Atualizo apenas a
expectativa para fim persistido anterior + 2 min; nenhuma lógica WS muda.

## Review Triage Log

Revisão interna somente leitura: nenhum defeito funcional. LOW opcional sobre
concorrência imediatamente fora da nova janela: incorporado ao mesmo teste
PostgreSQL parametrizado; garante aceite sem nova extensão e sem perder a anterior.
O review independente solicitado pelo dono permanece posterior a esta entrega.

Validação parcial: direcionados finais 470 passed (PostgreSQL real, WS,
concorrência nas duas janelas); Playwright focal 2 passed; mutação 3 failed
esperado e implementação restaurada. Falha antiga de DST e expectativa WS
corrigidas dentro do escopo. Verify padrão completo em repetição e variante
E2E ainda pendente; resultados finais em docs/EVIDENCIA-ANTI-SNIPING-CUMULATIVO.md.
Auditoria detectou nota acidental nos três .memlog.md dos companions 3.2/3.4/3.5;
a inserção exata foi removida e o conteúdo histórico restaurado antes da entrega.

Conclusão: verify padrão exit 0 (2083 backend / 175 frontend); verify com E2E
exit 0 (2083 backend / 175 frontend / 222 Playwright passed, 5 skipped).
Ruff/format/lint/tsc/Vite/Docker aprovados. Review interno encerrado sem achados
abertos. Evidência e logs preservados; review independente externo ainda pendente.
Nenhuma migration, mudança de integridade ou início da 4.3. Sem Git/commit.
