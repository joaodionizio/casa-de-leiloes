---
title: 'Story 5.1 — Verificação pública da integridade do lote'
status: done
created: '2026-10-28'
story_key: 5-1-verificação-pública-da-integridade-do-lote
---

# Story 5.1 — Verificação pública da integridade do lote

Como qualquer pessoa, sem login, quero consultar todos os lances de um lote e
saber se o histórico está íntegro ou adulterado, para confiar no resultado.

Decidi reutilizar os registros dos Epics 3 e 4, com uma leitura consistente sem
escrita e aliases persistidos; descartei nova fonte de verdade, recálculo de
pseudônimos e consulta ao catálogo externo. A página pública é exigida pela story.

- [x] Endpoint PUBLIC `GET /api/lots/{lot_id}/audit`, contrato explícito e no-store.
- [x] Histórico completo por sequência, canonical v1, SHA-256 e HMAC interno.
- [x] Estados scheduled/live/ended-pending/sold/unsold/cancelled distintos.
- [x] Settlement/comprovante conferidos contra histórico e âncora.
- [x] Em adulteração, veredito tipado e dados não confiáveis retidos, sem reparo.
- [x] Página `/lots/{id}/audit`, BRL, datas conforme política atual, hashes em detalhes.
- [x] PostgreSQL real: cinco adulterações SQL, privacidade, zero escrita, consulta
  constante, indisponibilidade AIC, lote inexistente e histórico de 100 lances.
- [x] Contrato, navegação anônima, loading/retry/404 e responsividade em Playwright.
- [x] Gate final `VERIFY_E2E=1 ./verify.sh` aprovado após corrigir listas de rotas.

[SPEC](../specs/spec-story-5-1-auditoria-publica/SPEC.md) ·
[Evidência](../specs/spec-story-5-1-auditoria-publica/implementation-evidence.md)

Concluí o fechamento documental autorizado em 28/10/2026 após review independente
final: 0 HIGH / 0 MEDIUM / 0 LOW funcional nos 14 riscos críticos. Decidi marcar
story/sprint/SPEC como done e manter Epic 5 in-progress; descartei repetir os gates
sem suspeita concreta. Não alterei código ou testes nem iniciei 5.2/5.3.

[Review final](code-review-final-story-5-1.md). Nenhum teste foi reexecutado no
review; usei a evidência existente. Não executei Git nem li `.env*`.
