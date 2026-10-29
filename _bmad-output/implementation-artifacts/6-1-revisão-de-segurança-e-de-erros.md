---
title: 'Story 6.1 — Revisão de segurança e de erros'
status: done
created: '2026-10-28'
story_key: 6-1-revisão-de-segurança-e-de-erros
---

# Story 6.1 — Revisão de segurança e de erros

> Estado vigente em 29/10/2026: **done**. R6.1-01 resolvido pelo re-review
> independente; CA2 publicado já comprovado na execução anterior da 6.4
> (cookie HTTPS/Origin/CORS/login/logout). Fechamento autorizado após a
> revalidação focal de R6.4-01, sem repetir CA2. SHA Render não autenticado.
> [Fechamento e limites](../../docs/FECHAMENTO-EPICO-6.md).
> As pendências de review/publicação abaixo são históricas.

Decidi completar as provas dos contratos existentes com minimum diff;
descartei reimplementar segurança ou refatorar configuração sem defeito
concreto. Nenhum código de produto foi alterado.

- [x] CA1: matriz executável das seis escritas, com inventário real, origem divergente e Content-Type ausente/não JSON, antes do despacho.
- [x] CA2 local: preservar provas de cookie HTTPS/login/logout e ausência de CORS permissivo.
- [x] CA3: ampliar REST/WS local sob falha AIC determinística e controle da mídia; fallback no navegador sem perder dados.
- [x] CA4: envelope 500 completo, debug falso e ausência de rotas sintéticas no app real.
- [x] Focais originais: 477 + 197 + 234 backend; 115 Playwright. Todos exit 0; evidência CA1 renovada abaixo após R6.1-01.
- [x] Gate original `./verify.sh`: exit 0; 2314 pytest, 192 Node; substituído pelo novo gate da correção abaixo.
- [x] CA2 publicado: cookie realmente emitido e aceito/enviado/removido, borda/proxy/CORS e fluxo HTTPS comprovados na 6.4; identidade do SHA Render não autenticada, conforme limite registrado no fechamento.

[SPEC](../specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/SPEC.md) ·
[Evidência](../specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/implementation-evidence.md)

O candidato inicial foi confirmado externamente como
`8a460d26bb280e5a35379254a82b73c3224813a1`; essa confirmação não é atribuída
ao usuário e não comprova deploy. Não executei Git, publicação ou code review.
Épico 6 permanece in-progress; não iniciei a Story 6.2.

Implementação pronta para **review independente**; SPEC in-review e sprint
review. Esse estado não declara CA2 publicado aprovado nem aceite integral.

## Review Findings — revisão independente de 28/10/2026

- [x] **R6.1-01 — MEDIUM (RESOLVIDO pelo re-review; relato original abaixo):** o inventário CA1 deixa passar nova escrita sem
  política em `/api/docs` ou `/api/openapi.json`, pois a exceção do framework
  é só por caminho. Reprodução com o factory real: sete POSTs, mas os 36
  casos permanecem verdes. Local: `backend/tests/test_csrf.py:572`;
  causa auxiliar: `backend/tests/access_policy.py:60`. Recomendação: fechar
  a exceção documental ou descobrir escritas independentemente da política,
  com regressão nos dois caminhos. **Correção autorizada e implementada;
  aguardando re-review independente**, sem aprovação pelo implementador.
  [Review e registro da correção](code-review-story-6-1.md).

Decidi manter a 6.1 em **review**: o MEDIUM foi corrigido pelo implementador,
mas aguarda re-review independente. Descartei tratar teste verde como aprovação
do reviewer. CA2 publicado continua pendente para deploy/6.4; não alterei sprint
ou status da SPEC.

## Correção R6.1-01 — evidência renovada

Descubro escritas diretamente das rotas HTTP reais e de todos os seus métodos,
sem consultar política nem excluir caminhos documentais. Depois confronto
W1–W6 e verifico políticas separadamente. As regressões exigem sétima escrita
no inventário e falha da validação CA1 em `/api/docs`, `/api/openapi.json` e
caminho inesperado, com/sem SPA e `Route`/`APIRoute`. Preservei os 36 casos
CA1 e controles positivos; nenhuma mudança em produção ou frontend.

- [x] Primeiro focal de regressão: 29 passed, 256 deselected, exit 0.
- [x] Suítes CSRF/política/autenticação/escritas CA1: 533 passed, exit 0.
- [x] Novo `./verify.sh`: exit 0; 2343 pytest, 192 Node; Ruff/formato, ESLint, TypeScript, Vite e Docker aprovados. Evidência CA1 anterior substituída pela execução após a correção.

Playwright CA3 anterior permanece independente desta correção e não foi
repetido. Não executei code review nem iniciei outra story nesta retomada.
