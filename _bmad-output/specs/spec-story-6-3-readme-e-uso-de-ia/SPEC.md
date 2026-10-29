---
id: SPEC-story-6-3-readme-e-uso-de-ia
title: 'Story 6.3 — README completo e registro de uso de IA'
status: in-review
route: dispatch
story: '6.3'
story_key: 6-3-readme-completo-e-registro-de-uso-de-ia
date: '2026-10-29'
context: []
companions:
  - audit-and-sources.md
sources: []
---

# Story 6.3 — README completo e registro de uso de IA

## Why

Como avaliador, quero entender como rodar, avaliar e o que pode surpreender sem adivinhar. Decidi completar README e NFR6 no candidato local; descartei refactor de produto para atender documentação. Pedido humano já autoriza SPEC + BUILD nesta sessão.

## Capabilities

- **CAP-1**
  - **intent:** Instalar, executar, verificar e avaliar o projeto com orientação reproduzível.
  - **success:** Dado o repositório, quando sigo o README, encontro pré-requisitos verificáveis, configuração, migrations/seed, comandos reais e roteiro dos dois papéis até comprovante/auditoria.
- **CAP-2**
  - **intent:** Entender onde usei IA e quais decisões, correções e verificações sustentam a entrega.
  - **success:** Dado uso_de_ia, quando consulto planejamento e stories 1.1–6.3, encontro rastreabilidade, evidência e distinção entre aceite humano, gates locais, reviews existentes e pendências.

<frozen-after-approval reason="pedido humano autoriza SPEC e BUILD na mesma sessão">

## Intent

Completar documentação do candidato real, sem atribuir ao deploy existente funcionalidades ainda não validadas publicamente. Preservar decisões históricas e explicar a vigência de cadastro 6.2A e AD-5 cumulativa.

## Constraints

- Documentação somente; não alterar backend/frontend/testes/config executável. Não executar Git/gh/commit/push/merge/deploy, ler .env* (inclusive exemplos), credenciais ou segredos.
- README cobre projeto/funcionalidades, pré-requisitos, instalação backend/frontend, ambiente, PostgreSQL/Alembic dev/test, seed idempotente, execução dev/build single-origin, verify padrão e E2E opt-in, contas demo, roteiro, cadastro, deploy, arquitetura, segurança, surpresas e limitações.
- Documentar nomes reais das variáveis, sem valores de segredos nem senha de banco; placeholders explícitos. Credenciais públicas demo são permitidas. Versões só de fontes verificáveis.
- Cadastro em /register e POST /api/auth/register aceita BIDDER e AUCTIONEER, sem Nome; senha 8–1024 sem composição, e-mail trim/lower, sem confirmação de e-mail, duplicidade explícita; carteira zero para ambos, sem liberar lance/depósito ao leiloeiro; cadastro não autentica e leva ao login.
- Surpresas obrigatórias: cold start sem duração inventada; liquidação por scheduler/catch-up e nunca GET; commit permanece mesmo se WS falhar; logout apaga cookie sem revogar JWT até exp; snapshot essencial local e imagem externa/proxy/placeholder; limites SHA-256/HMAC incluindo segredo comprometido/rollback coordenado/controle total; anti-sniping 0 < ends_at-now <= 2 min soma 2 min ao fim vigente, cumulativo/renovável/sem teto, inclusive exatamente 2 min.
- Uso IA preserva histórico, cobre todas as stories e registra 6.2 refinamento/aceite visual humano/review/LOW R6.2-01 aceito; 6.2A decisão humana/gates e review individual DEFERIDO ao agregado por prazo; 6.3 documental e sem review novo.
- 6.3 termina review/in-review pronta para agregado; 6.2A permanece review, 6.1 permanece pendência publicada, epic 6 in-progress, 6.4 não executada. 6.5–6.7 cortadas, mantendo chaves backlog comentadas por compatibilidade do schema.

## Non-goals

Code review de qualquer espécie, deploy/6.4, opcionais, correção funcional oportunista, gate completo repetido apenas por ritual, métricas empíricas novas ou supostas.

</frozen-after-approval>

## Code Map

- README.md: parcial, com comandos de cd encadeados incorretamente e negação de cadastro; reestruturar para avaliação completa.
- docs/uso_de_ia.md: histórico amplo; preservar e acrescentar síntese/índice por fase e atualização vigente.
- backend/app/{config,auth,seed,security,lots,bid_rules,main}.py: nomes de variáveis, contas, senha, horários, limites, startup e contratos. Somente leitura estática; não importar aplicação/loaders.
- Dockerfile, compose.yaml, backend/scripts/start.sh, verify.sh, frontend/package.json e vite.config.ts: comandos, versões, proxy /ws, build e startup. Somente leitura.
- frontend/src/route.ts: caminhos públicos/privados reais. Somente leitura.
- sprint-status.yaml/deferred-work.md e docs/FECHAMENTO-DE-EPICO.md: registrar exceção de processo sem apagar pendências.

## Tasks & Acceptance

- [x] T1 README.md: completar todas as seções e navegação com contratos vivos.
- [x] T2 docs/uso_de_ia.md: índice/síntese rastreável e adendo 6.3, preservando histórico.
- [x] T3 sprint/deferred/story/FECHAMENTO-DE-EPICO: registrar entrega para agregado, cortes e exceção 6.2A/6.3.
- [x] T4 implementation-evidence.md: comandos focais/resultados, fontes e limitações reais.
- Dado README novo, quando verifico links relativos e âncoras, então apontam a arquivos/seções existentes, sem /Users.
- Dado código/config vivo, quando comparo comandos, variáveis, rotas e seed, então concordam sem leitura de dotenv nem valores privados.
- Dado histórico conflitante, quando leio documentação atual, então cadastro e AD-5 vigentes ficam explícitos sem reescrever decisões antigas.
- Dado status final, quando consulto sprint e registros, então review agregado futuro fica pendente sem afirmar publicação do candidato.

## Verification

Executar somente checks documentais baratos: links/caminhos/âncoras, sintaxe dos snippets shell, conferência estática de variáveis/rotas/seed/startup/scripts e arquivos alterados contra baseline sem Git. Gate completo anterior está em implementation-evidence da 6.2A e não será renovado sem mudança executável. Não medir testes/performance.

## Success signal

Entrego documentação que permite executar e avaliar fluxo completo local e após futuro deploy, com limites explícitos; 6.3 pronta para review agregado e nenhuma ação de publicação realizada.

## Implementation Notes

Nenhuma decisão humana bloqueante remanescente. Auditoria detalhada e fontes no companion. Autovalidação de SPEC é conferência de coerência/preservação, não code review.


Entrega implementada e validada documentalmente; ver implementation-evidence.md. Review agregado independente ainda pendente. Não houve code review nesta sessão.
