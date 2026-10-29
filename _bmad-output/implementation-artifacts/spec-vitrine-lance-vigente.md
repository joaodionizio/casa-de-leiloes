---
title: 'Corrigir lance vigente na Vitrine pública'
type: 'bugfix'
created: '2026-10-29'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Corrigir exclusivamente o valor de lance apresentado na Vitrine usando sua listagem pública atual. Acrescentar `current_bid_cents` obrigatório e anulável ao DTO público (resumo e detalhe herdado), preenchido diretamente de `Lot.current_bid_cents`, sem expor líder ou identidade privada. Contrato TypeScript e validação runtime devem aceitar `null` e centavos inteiros válidos.

Dado um lote sem lance, quando a Vitrine apresenta o snapshot, então exibe “Lance inicial” e `starting_bid_cents`. Dado um lote com lance, quando apresenta o snapshot, então exibe “Lance atual” e `current_bid_cents`, inclusive no texto acessível, sem anunciar o inicial como vigente. Dado um aumento confirmado, quando a listagem é novamente carregada pelo fluxo existente, então o novo snapshot apresenta o novo valor. Busca e filtros continuam locais, sem requests por lote, polling ou WebSocket novo.

Preservar detalhe público, privacidade e todas as regras de lance, carteira, reservas, settlement, auditoria e persistência financeira. Nenhuma migração, refatoração ampla, mudança visual alheia, operação Git ou deploy. Adicionar testes do contrato, serialização, apresentação dos componentes, atualização por snapshot e ausência de consultas extras; executar testes focais e `VERIFY_E2E=1 ./verify.sh`. Se houver falha, não declarar concluído.

</frozen-after-approval>

## Implementation Notes

- Escopo pequeno, reversível, sem questões de intenção abertas ou efeito externo. Implementação autorizada pelo pedido detalhado do usuário.
- `backend/app/lots.py`: `PublicLotSummary` e `public_lot_summary`; detalhe já reaproveita o resumo. A consulta pública já lê o modelo completo, dispensando consultas adicionais.
- `frontend/src/api/publicLots.ts`: contrato obrigatório `number | null` com validação de inteiro seguro positivo ou null.
- `frontend/src/FeaturedLot.tsx`, `LiveLotItem.tsx`, `UpcomingLotItem.tsx` e `lotLabels.ts`: condicional explícita por null para valor/rótulo visível e acessível. Encerrados continuam sem preço, pois não se trata de resultado de liquidação.
- Testes/fixtures: `backend/tests/test_lot_phase.py`, `backend/tests/integration/test_public_lots.py`, `frontend/src/api/publicLots.test.ts`, `frontend/src/lotLabels.test.ts`, `frontend/src/vitrine.test.ts`, `frontend/e2e/support/mockApi.ts`, `frontend/e2e/vitrine.spec.ts`.
- Registro obrigatório do projeto: `docs/uso_de_ia.md`. Verificação focal de public lots, contratos, rótulos e Vitrine; gate completo com E2E.

- O primeiro gate identificou `backend/tests/integration/test_lot_cancellation.py` como consumidor adicional do detalhe público: sua contagem fixa de 18 campos deve passar a 19 e verificar `current_bid_cents = null`. Ajuste exclusivo da expectativa do contrato exigido pelo pedido; nenhuma lógica de cancelamento alterada.

## Review Triage Log

- low, rejeitado — cobertura adicional de `UpcomingLotItem` com lance preenchido: oportunidade de proteção futura, sem erro constatado; um agendado válido não recebe lances. Os testes existentes cobrem agendados sem lances. Acrescentar cenário sintético não é necessário à correção mínima.
- low, rejeitado — valores distintos por lote no E2E: oportunidade para regressões hipotéticas de reutilização entre cards; os componentes usam exclusivamente suas próprias props e os cenários verificam promoção pela busca, sem defeito atual. A mudança exigiria ampliar os cenários além da correção simples.
- low, rejeitado — teste de omissão na construção direta do DTO Python: o campo é obrigatório sem default; a construção pública sempre o preenche. Omissão é rejeitada no runtime TypeScript já testado. Não há entrada pública de construção desse DTO que torne a lacuna um erro atual.
- low, rejeitado — encerrado com lance preenchido no nome acessível: retorno antecipado por fase preservado e verificado estaticamente; não há caminho que apresente valor nessa linha. Novo cenário seria cobertura adicional de ramo inalterado, sem defeito constatado.
- false — ausência do registro de IA: o primeiro diff antecedeu a atualização de `docs/uso_de_ia.md`; a revisão complementar confirmou o registro e seu link para esta spec.
- Revisão complementar de `backend/tests/integration/test_lot_cancellation.py`: ajuste exclusivamente da expectativa do contrato público e de `null`, sem problema encontrado.
- Nenhum achado funcional aberto e nenhuma mudança de regra financeira ou de cancelamento.

- O gate inicial terminou com 2448 testes aprovados e 2 falhas de expectativas antigas do contrato: contagem de campos do detalhe em cancelamento e lista de campos OpenAPI (`backend/tests/test_openapi.py`). Atualizo somente as expectativas, incluindo obrigatoriedade e tipo inteiro/null no OpenAPI.

- Revisão complementar de `backend/tests/test_openapi.py`: ajuste de campos, privacidade, obrigatoriedade e tipo inteiro/null conferido sem problemas. A oportunidade de cobertura de obrigatoriedade do backend ficou atendida pelo schema OpenAPI.

## Verification

- `uv run --no-cache pytest tests/test_lot_phase.py tests/integration/test_public_lots.py`: **68 passed**, 1 warning de depreciação do Starlette/httpx.
- `node --test src/api/publicLots.test.ts src/lotLabels.test.ts src/vitrine.test.ts`: **29 passed**, 0 falhas. `npm run typecheck`: aprovado.
- `npm run test:e2e -- e2e/vitrine.spec.ts`: **28 passed**; inclui renderização de FeaturedLot/LiveLotItem sem/com lance, texto acessível, aumento na próxima listagem, snapshot estável, filtros sem requests extras e ausência de WebSocket na Vitrine.
- `uv run --no-cache pytest tests/test_openapi.py tests/integration/test_lot_cancellation.py::test_other_lots_stay_public_and_no_phase_is_cancelled`: **35 passed**, 1 warning de depreciação, após ajustar as expectativas antigas.
- `VERIFY_E2E=1 ./verify.sh`: **exit code 0** na execução final; Ruff aprovado, **111 files already formatted**, PostgreSQL saudável, **2450 passed**, **207 testes Node aprovados / 0 falhas**, lint, typecheck, build Vite, **357 E2E passed / 7 skipped**, build Docker aprovado.

Saída real final do gate:

```text
================= 2450 passed, 1 warning in 154.96s (0:02:34) ==================
ℹ tests 207
ℹ pass 207
ℹ fail 0
  7 skipped
  357 passed (42.2s)
verify.sh: todas as etapas passaram.
```

Os 7 E2E pulados pertencem a `real-stack.spec.ts`, que exige `E2E_REAL_BASE_URL` e fica fora do gate usual conforme a configuração existente. Os testes backend de integração rodaram em PostgreSQL real e isolado. Avisos preexistentes de depreciação do cliente Starlette e de cores do Node não impediram o gate.

Nenhum achado funcional aberto. O valor continua sendo uma fotografia: só muda na próxima leitura pública existente. O frontend novo exige a API com o campo obrigatório; a publicação coordenada do monorepo permanece pendente. Nenhum commit, push ou deploy realizado.

Arquivo gerado fora da lista prevista: `frontend/test-results/.last-run.json` (artefato local ignorado do Playwright). Os dois arquivos de expectativas adicionais do contrato foram `backend/tests/integration/test_lot_cancellation.py` e `backend/tests/test_openapi.py`. Nenhum arquivo de segredo alterado detectado; conteúdos de segredos não foram lidos nem comparados.
