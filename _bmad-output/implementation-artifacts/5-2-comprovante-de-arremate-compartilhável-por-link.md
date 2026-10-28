---
title: 'Story 5.2 — Comprovante de arremate compartilhável por link'
status: done
created: '2026-10-28'
story_key: 5-2-comprovante-de-arremate-compartilhável-por-link
---

# Story 5.2 — Comprovante de arremate compartilhável por link

Decidi usar `/lots/{lot_id}/receipt` como link público estável e o receipt persistido como fonte do resultado. Descartei token adicional, PDF e botão de copiar, previsto na Story 5.3. A página apresenta obra, pseudônimo, valor, data, quantidade de lances, hash e acesso à auditoria.

- [x] Endpoint público com DTO restrito e validação coerente do lote, settlement e receipt; leitura sem escrita e independente da AIC.
- [x] Ausência retorna 404; inconsistência retorna 409 sem reparo ou dados do comprovante.
- [x] Página pública responsiva e navegação a partir da sala de lote vendido.
- [x] Testes focais em PostgreSQL e Chromium; gate final com E2E aprovado.

[SPEC](../specs/spec-story-5-2-comprovante/SPEC.md) · [Evidência](../specs/spec-story-5-2-comprovante/implementation-evidence.md)

Review funcional curto aprovado em 28/10/2026, sem HIGH/MEDIUM. Story e sprint estão em done; Epic 5 permanece in-progress. Registro: [review final](code-review-final-story-5-2.md).
