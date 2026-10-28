---
title: 'Story 5.2 — Comprovante de arremate compartilhável por link'
type: feature
created: '2026-10-28'
status: done
route: dispatch
context: []
---

<frozen-after-approval reason="Fluxo enxuto autorizado pelo usuário">

## Intent

Decidi expor o comprovante persistido da 4.3 em uma página pública estável por lote, com obra, resultado e acesso à auditoria 5.1. Descartei criar token, PDF ou ação de copiar (prevista na 5.3).

## Boundaries & Constraints

A leitura usa receipt persistido e settlement coerente, mais snapshot local da obra, sem API externa. Não liquida, repara, escreve, publica ou acessa wallet. Não muda canonical v1, hashes, HMAC, settlement nem receipt. DTO público explícito não inclui ID de pessoa, email, dados financeiros privados, HMAC ou segredo. A verificação existente da auditoria pode ser reutilizada, sem reconstruir o resultado a partir dos lances: os campos exibidos vêm do receipt.

## I/O & Edge-Case Matrix

| Estado | Resultado |
| --- | --- |
| Sold com receipt e vínculos coerentes | 200 com receipt público e snapshot da obra |
| Sold inconsistente ou receipt/settlement incoerente | 409 seguro, sem dados nem reparo |
| Unsold, pendente, agendado, ativo ou cancelado sem receipt | 404 sem comprovante vazio |
| Lote inexistente | 404; UUID inválido 422 |
| Falha operacional | 500 genérico |

</frozen-after-approval>

## Code Map

- `backend/app/lot_audit.py`: `audit_statement`, `_project`, `_verified` leem snapshot único e verificam vínculos e cadeia; reutilizar sem modificar a auditoria.
- `backend/app/lot_settlement.py`: `Receipt`, `LotSettlement`, `_structural_conflict`; receipt é fonte dos campos públicos.
- `backend/app/catalog.py`: `image_url_for` constrói URL local sem buscar imagem.
- `backend/app/main.py`: registrar rota pública; `backend/tests/test_access_policy.py` e `test_openapi.py` guardam contratos.
- `frontend/src/route.ts`, `App.tsx`, `LotPage.tsx`: navegação e página públicas; `AuditPage.tsx`, `money.ts`, `lotTime.ts` e CSS fornecem padrões.
- `backend/tests/integration/test_lot_audit.py`, `tests/settlement_support.py` e `frontend/e2e/audit.spec.ts`: fixtures para testes focais.

## Tasks & Acceptance

- [x] `backend/app/lot_receipt.py`, `backend/app/main.py`: GET público `/api/lots/{lot_id}/receipt`, no-store, DTO explícito e falha segura.
- [x] `backend/tests/integration/test_lot_receipt.py`, `backend/tests/test_access_policy.py`, `backend/tests/test_openapi.py`: matriz, privacidade, persistência, leitura pura e independência externa.
- [x] `frontend/src/api/receipt.ts`, `frontend/src/ReceiptPage.tsx`, `frontend/src/route.ts`, `frontend/src/App.tsx`, `frontend/src/LotPage.tsx`, `frontend/src/App.css`: rota pública `/lots/{id}/receipt`, documento responsivo, link de auditoria e acesso a partir de lote vendido.
- [x] `frontend/e2e/receipt.spec.ts`, `frontend/src/route.test.ts`: página, BRL/data, falhas, navegação e mobile.
- [x] Story, SPEC/evidence, sprint e registro de IA: atualizar ao final, após o gate.

Dado sold coerente, quando uma pessoa anônima abre a URL, então vê o comprovante persistido, obra e auditoria. Dado um estado sem venda, quando consulta, então não há comprovante. Dada inconsistência, quando consulta, então falha sem expor dados nem modificar estado. Dada API externa indisponível, quando consulta, então a página continua funcional; imagem pode falhar. Dada tela de 320px, quando abre, então dados e hash permanecem legíveis sem rolagem horizontal.

## Implementation Notes

Autovalidei a SPEC contra a story e decisões fornecidas; não há lacuna ou conflito arquitetural. Ready-for-dev autorizado na solicitação. Testes focais durante implementação; somente `VERIFY_E2E=1 ./verify.sh` como gate final, repetir apenas após falha e correção. Sem review, Git, segredos ou 5.3.

## Verification

Testes focais de backend e browser; gate final `VERIFY_E2E=1 ./verify.sh` e smoke local. Story e sprint para review, Epic 5 in-progress.

## Evidência final

Gate `VERIFY_E2E=1 ./verify.sh`: exit 0; 2269 testes backend, 188 Node e 259 Playwright passaram; cinco testes real-stack foram ignorados. Ruff, formatação, ESLint, TypeScript, build e Docker passaram. A primeira tentativa falhou no acesso ao cache uv e a segunda na ordenação de import; corrigi e conferi com Ruff antes do gate aprovado. Smoke automatizado em Chromium com API simulada: receipt público, valores, link da auditoria, 320 e 1280 px e falhas 404/409/500. Não houve smoke da stack real em navegador.

## Review final — 28/10/2026

Decidi concluir a SPEC após review funcional curto sem HIGH/MEDIUM. Descartei repetir testes sem suspeita concreta; nenhum teste ou verify foi executado nesta revisão. Story e sprint 5.2 done; Epic 5 in-progress. Evidência em `../../implementation-artifacts/code-review-final-story-5-2.md`.
