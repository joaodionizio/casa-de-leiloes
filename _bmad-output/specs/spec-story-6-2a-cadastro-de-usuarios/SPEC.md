---
id: SPEC-story-6-2a-cadastro-de-usuarios
title: 'Story 6.2A — Cadastro de usuários'
status: in-review
story: '6.2a'
story_key: 6-2a-cadastro-de-usuarios
date: '2026-10-29'
context:
  - registration-contract.md
  - ../../../CLAUDE.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
companions:
  - registration-contract.md
  - ../../../CLAUDE.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/desafio-elite-dev.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../../docs/FECHAMENTO-DE-EPICO.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
sources: []
---

# Story 6.2A — Cadastro de usuários

Decidi, por autorização humana de 29/10/2026, permitir cadastro próprio sem Nome nem migration, com papéis BIDDER/AUCTIONEER e login manual posterior. Descartei coleta sem uso, autologin e identidade paralela. QH-01–06 estão resolvidas no contrato; build autorizado na mesma sessão. Esta SPEC e seu companion são o contrato completo.

## Why

Quero criar minha própria conta em ÁTRIO — Leilões de Arte sem depender das demos, preservando o refinamento aprovado da 6.2. Executo depois de 6.2 e antes de 6.3; não renumero stories.

## Capabilities

- **CAP-1**
  - **intent:** Criar conta como Licitante ou Leiloeiro.
  - **success:** CA01: POST válido persiste User com papel permitido, e-mail normalizado e Argon2id; login posterior e /api/me funcionam.
- **CAP-2**
  - **intent:** Começar com carteira consistente para licitar ou receber.
  - **success:** CA02: User+Wallet 0/0 na mesma transação para ambos; falhas fazem rollback e concorrência deixa uma conta/carteira.
- **CAP-3**
  - **intent:** Preencher e corrigir cadastro com clareza por teclado e tela estreita.
  - **success:** CA03/04: 1440/375/320 sem overflow; papel sem preseleção, toggle local, erros acessíveis e POST único.
- **CAP-4**
  - **intent:** Entrar pelo fluxo normal após cadastrar.
  - **success:** CA05: 201 sem cookie, confirmação acessível em /login, senha não transportada, returnTo seguro e demos preservados.
- **CAP-5**
  - **intent:** Cadastrar sem escritas indevidas ou vazamento de dados.
  - **success:** CA06/07: inventário bruto com W7, três negativos 403/415 antes do handler, duplicidade 409 sanitizada e oitava inesperada reprovada.

## Constraints

- Inglês no domínio/API, português na UI; identidade ÁTRIO e padrões existentes; sem Nome, migration ou alteração do modelo User.
- Reutilizo Argon2id, políticas, envelope, middleware, navegação e carteira. Sem exceção CSRF, algoritmo ou sessão paralelos.
- Conta existente não muda; constraint uq_users_email é a autoridade concorrente; não logar payload/senha/DETAIL SQL.
- 6.2 encerrada administrativamente pelo aceite humano e LOW R6.2-01 conscientemente aceito; não corrigir o finding. 6.1 continua review por CA2 publicado pendente.
- Chave exata 6-2a-cadastro-de-usuarios. Resolver numérico não garante sufixo: uso explicitamente esta pasta/SPEC/chave, nunca 6-2; sem modificar a skill.
- Não executar Git/gh/publicação/deploy, ler .env* ou usar credenciais privadas. Não fazer bmad-code-review nesta sessão; entregar in-review para sessão independente.

## Non-goals

- Nome/migration/perfil/edição/exclusão/admin, recuperação/troca de senha, confirmação de e-mail, OAuth/MFA/CAPTCHA, rate limit geral, refresh token, ledger/moeda real/idempotency-key.
- Stories 6.3–6.7, redesign 6.2, correção R6.2-01 ou alteração de CA2 publicado 6.1.

## Success signal

Crio conta real nos dois papéis, vou ao login com confirmação e entro/recarrego com papel e carteira corretos. Focais, smoke integrado PostgreSQL e VERIFY_E2E=1 ./verify.sh passam; entrego screenshots temporárias e evidência para review independente.

## Tasks & Acceptance

- [x] T1 — Backend em backend/app/auth.py, wallet.py, errors.py: request estrito, hash existente, transação User+Wallet direcionada, duplicidade estrutural e resposta segura. CA01/02/07 do companion.
- [x] T2 — Frontend em frontend/src/App.tsx, route.ts, api/auth.ts, LoginPage.tsx, RegisterPage.tsx, RegisterForm.tsx, App.css: cadastro e links reais, confirmação em login, retorno seguro, foco/teclado/toggle e barreira síncrona. CA03/04/05.
- [x] T3 — Testes backend/integration/test_registration.py e regressões test_csrf.py/test_access_policy.py/OpenAPI; frontend API/route e E2E registration/session/layout/keyboard/touch: matriz completa do companion. CA01–07.
- [x] T4 — Focais e correções no escopo, smoke real com build+FastAPI+PostgreSQL de teste e gate final VERIFY_E2E=1 ./verify.sh. CA08.
- [x] T5 — Screenshots temporárias Cadastro 1440/375/320 e Login atualizado; evidência/story/sprint/uso de IA e extensão CA1 local 6.1. Encerrar in-review/review, sem revisão independente nesta sessão.

A implementação delegada executa T1–T3 e verificações estáticas sem abrir .env*. A coordenação cuida de documentos/status, prepara execução isolada sem .env*, executa T4–T5 e verifica o diff contra baseline local. Não iniciar outro workflow nem code review independente. Decisões humanas já autorizam execução; não pedir nova aprovação.

## Verification

Focais backend com PostgreSQL real, testes Node/Playwright pertinentes e smoke integrado com dados fictícios e banco de teste; depois VERIFY_E2E=1 ./verify.sh no candidato final. Ambiente isolado sem dotenv/credenciais, sem tocar banco de desenvolvimento. Registrar comandos reais, exit codes e limitações. Screenshots são apoio visual temporário, não golden files. Nenhum gate já é considerado executado por escrever esta seção.

## Open Questions

Nenhuma. Contradição real impeditiva com arquitetura/código interrompe a execução; preferência diferente não reabre decisões.

## Entrega para revisão independente

Implementei e verifiquei CA01–08 conforme evidência em [implementation-evidence.md](implementation-evidence.md). Mantenho SPEC in-review e story/sprint review. As decisões humanas estão aplicadas; não executei bmad-code-review nem declaro aceite visual humano desta implementação. As capturas estão disponíveis na evidência. Não inicio a 6.3 nem concluo o épico.
