---
title: 'Story 5.1 — Auditoria pública do lote'
type: feature
created: '2026-10-28'
status: done
route: dispatch
context:
  - CLAUDE.md
  - docs/ARQUITETURA.md
  - _bmad-output/planning-artifacts/DESIGN.md
  - _bmad-output/planning-artifacts/EXPERIENCE.md
---

> Estado final em 28/10/2026: **aprovada e concluída** após review independente
> dos 14 riscos críticos, sem HIGH/MEDIUM ou LOW funcional. Decidi encerrar a 5.1
> conforme autorização humana e manter Epic 5 in-progress; descartei repetir gates
> sem suspeita concreta. Os relatos anteriores permanecem como histórico.
> [Review final](../../implementation-artifacts/code-review-final-story-5-1.md).

<frozen-after-approval reason="Intenção autorizada pelo usuário no fluxo enxuto">

## Intent

Decidi entregar a Story 5.1 de `epics.md`: qualquer pessoa abre a auditoria de um lote sem login, consulta todos os lances e recebe um veredito textual de integridade. Reutilizo exclusivamente bids, lotes, settlement e comprovante base persistidos nos Epics 3 e 4. Descartei nova fonte de verdade e dependência do catálogo externo.

## Boundaries & Constraints

- Nunca executar Git nem ler `.env*`, credenciais ou segredos. Não fazer code review, mutações amplas, deploy ou Stories 5.2/5.3.
- Canonical bid v1, SHA-256 e HMAC existentes permanecem inalterados. Auditoria nunca recalcula pseudônimos: usa aliases persistidos. Validar cadeia, HMAC, quantidade/hash final, vínculo operacional e settlement/comprovante antes de declarar integridade.
- Leitura síncrona sem trava, escrita, reparo, liquidação ou commit. Uma consulta SQL com snapshot consistente para lote, hora PostgreSQL, histórico, settlement e receipt; sem usuários, wallets ou N+1.
- Resposta pública por DTO explícito. Nunca IDs privados (incluindo bidder_id/winner_user_id), email, nome privado, wallets, saldos, JWT, HMAC/assinaturas ou campos ORM internos. Dados privados podem ser lidos internamente para comparar vínculos, jamais serializados.
- Só testes focais durante implementação. O agente principal executará ao final um único gate `VERIFY_E2E=1 ./verify.sh`; não o executar no handoff.

## Contrato e estados

`GET /api/lots/{lot_id}/audit`, política PUBLIC, `Cache-Control: no-store`.
200: `lot_id`, `as_of`, `integrity` (`verified` | `adulterated`), `phase` (`scheduled` | `live` | `ended` | `cancelled`, ou null em conflito), `settlement_status` (`pending` | `settled` | `not_applicable`, ou null em conflito), `settlement` (PublicSettlement existente ou null), `bid_count`, `final_hash`, `bids`.
Cada bid: apenas `sequence`, `bidder_alias`, `amount_cents`, `placed_at`, `canonical_version`, `previous_hash`, `current_hash`. Ordem crescente de sequência, sem limite da sala.
`placed_at` representa o `timestamp` da canonical v1; documentar JSON UTF-8 ordenado, sem espaços, UTC seis casas e Z, genesis de 64 zeros e SHA-256 para reprodução pública. HMAC é validação interna do servidor, não prova pública independente.
404 padrão para inexistente; 422 padrão para UUID inválido; 500 padrão para falha operacional, nunca falso veredito de adulteração.
Se adulterado, responder 200 tipado com `integrity=adulterated`, `phase/settlement_status/settlement/bid_count/final_hash=null`, `bids=[]`: oculto conteúdo não confiável (inclusive aliases adulterados que poderiam conter email), mantendo somente lot_id/as_of. UI explica explicitamente a retenção de dados, sem inventar resultado. Lote legado sem âncora também não recebe veredito íntegro.

| Cenário | Resultado |
| --- | --- |
| Ativo/agendado autenticado | verified, phase temporal, pending, settlement null |
| Expirado sem settlement | verified, ended, pending, sem inferir vencedor |
| Sold/unsold persistido e coerente | verified, ended, settled, resultado persistido |
| Cancelado vazio autenticado | verified, cancelled, not_applicable, sem confundir com unsold |
| Cadeia/âncora/resumo/settlement/receipt inválido | adulterated, dados retidos, nenhuma escrita |
| Inexistente | 404 sem informação privada |

Frontend: `/lots/{id}/audit` pública antes do bloqueio de sessão no App; link funcional na sala inclusive cancelada; documento editorial simples, título, estado, veredito em texto, resumo e lista cronológica completa. BRL via money.ts e datas via lotTime.ts. Hashes longos em detalhes técnicos, quebrando linhas; renderizar 50–100 eventos sem scroll horizontal global a 320px. Loading, vazio, erro/retry e 404; ignorar respostas após desmontagem e mudanças de lote. Sem painel, PDF, download ou compartilhamento.

</frozen-after-approval>

## Code Map

- `backend/app/bid_integrity.py`: CanonicalBid, VerifiableBid, verify_bid_chain, AnchorState, verify_anchor_hmac; reutilizar sem modificar formato.
- `backend/app/bids.py`: Bid e PublicSettlement; authenticate_previous_state recalcula alias do líder, portanto não usar esse recálculo na auditoria. Comparar vínculo privado ao último bid internamente.
- `backend/app/lots.py`: Lot, _clock_cte, get_integrity_config; padrão snapshot em statement único.
- `backend/app/lot_settlement.py`: LotSettlement, Receipt e _structural_conflict; reutilizar validação estrutural e conferir vínculo com lote/histórico/âncora e settled_at >= ends_at.
- `backend/tests/settlement_support.py`, `bid_support.py`, `lot_support.py`, `auth_support.py`: fixtures reais, adulteração e observação SQL; reusar sem copiar grandes helpers.
- `frontend/src/route.ts`, `App.tsx`, `LotPage.tsx`, `App.css`: integrar rota e navegação pública sem refazer sala.
- `frontend/e2e/support/mockApi.ts`: padrões existentes para Playwright.

## Tasks & Acceptance

- [x] `backend/app/lot_audit.py` (novo), `backend/app/main.py`: implementar leitura consistente, verificação e contrato público.
- [x] `backend/tests/integration/test_lot_audit.py` (novo): cenário feliz e matriz, sequência/aliases/valores/timestamps/hashes, cinco adulterações SQL distintas (alteração, inserção, remoção do meio, truncamento, recálculo sem HMAC), inconsistência settlement/receipt, privacidade, consulta constante e zero escrita, AIC indisponível e 404. Usar PostgreSQL real para essas propriedades.
- [x] `frontend/src/api/audit.ts`, `frontend/src/AuditPage.tsx` (novos), `frontend/src/route.ts`, `App.tsx`, `LotPage.tsx`, `App.css`: integrar contrato validado e tela pública.
- [x] `frontend/src/api/audit.test.ts`, `frontend/e2e/audit.spec.ts` (novos), `frontend/src/route.test.ts`: testes focais de contrato, navegação anônima, vereditos, estados finais, erro/retry, responsividade com muitos eventos.
- [x] Story, SPEC/evidence, sprint-status e `docs/uso_de_ia.md`: atualização única ao final pelo agente principal.

Dado um lote íntegro, quando consulto sem login, então recebo toda sequência canônica e campos públicos persistidos, sem depender da AIC.
Dada cada linha da matriz, quando consulto, então recebo o estado/veredito especificado sem alterar nenhum registro.
Dado histórico adulterado ou settlement inconsistente, quando consulto, então não vejo resultado confiável nem conteúdo privado injetado.
Dada a página em 320px ou desktop com 100 eventos, quando consulto e navego, então histórico, estado e integridade permanecem legíveis com controles semânticos.

## Implementation Notes

Autovalidei a SPEC contra a story/ADs e autorizei ready-for-dev conforme instrução explícita do usuário de implementar imediatamente. Não há conflito arquitetural, decisão material aberta nem alteração irreversível. Descartei checkpoints intermediários e review nesta sessão por solicitação humana. Evidências finais serão registradas após o gate.

## Verification

Testes focais de backend/contrato/browser durante desenvolvimento. Gate final exclusivo pelo agente principal: `VERIFY_E2E=1 ./verify.sh`. Corrigir causa e repetir somente se falhar. Ao concluir: Story/SPEC/sprint 5.1 review; Epic 5 in-progress. Não done.


## Evidência final — 28/10/2026

Concluí implementação e testes pelo fluxo enxuto autorizado. A implementação foi
delegada a Sol (`gpt-6.1-sol`, raciocínio medium), com SPEC como fonte de verdade.
Conferi tarefas/aceite e o diff sem Git; não executei code review.

Incluí `backend/tests/test_access_policy.py` e `backend/tests/test_openapi.py` na
verificação do contrato público: o primeiro gate detectou quatro expectativas
antigas que não enumeravam a rota nova. Copiei esses arquivos para a baseline
antes de ajustá-los; preservei os guards, acrescentando a política PUBLIC e os
campos públicos exatos da auditoria. Os 58 testes focais passaram antes da repetição.

Gate final `VERIFY_E2E=1 ./verify.sh`: exit 0, 2260 backend, 187 Node e 254
Playwright passaram; cinco real-stack opt-in foram ignorados. Ruff/formatação,
ESLint, TypeScript, Vite e Docker passaram. A tentativa inicial no sandbox parou
antes dos checks por permissão no cache do uv; a execução local autorizada resolveu.

Detalhes e cobertura da matriz: [implementation-evidence.md](implementation-evidence.md).
Story e sprint 5.1: review; Epic 5: in-progress. Não promovi done, não iniciei 5.2,
não executei Git, deploy, mutações amplas ou leitura de arquivos de segredos.
