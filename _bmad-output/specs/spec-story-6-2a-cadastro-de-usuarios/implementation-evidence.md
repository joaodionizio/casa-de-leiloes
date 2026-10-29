# Evidência de implementação — Story 6.2A

Data: 29/10/2026, America/Maceio. Estado: **implementada e verificada; pronta para review independente**. Usei bmad-spec para consolidar decisões e bmad-build para implementar, com um agente de implementação e verificação coordenada. Descartei execução de revisão independente nesta sessão por instrução humana. Não atribuo nome exato de modelo sem confirmação de ferramenta.

## Decisões e contrato implementado

QH-01=B (sem Nome/migration), QH-02=A (BIDDER/AUCTIONEER explícitos), QH-03=B (sem sessão no cadastro), QH-04=A (409 email_already_registered/enumeração aceita), QH-05=6-2a-cadastro-de-usuarios, QH-06=B (8–1024 sem composição). Email trim/lower, 254, formato mínimo sem DNS/pontos/+tag removidos. Sem alteração do login.

POST /api/auth/register PUBLIC, extra=forbid, request email/password/role. 201 {email,role}, no-store, sem cookie/token/ID/hash. Novo código 409 no envelope único; 403/415/422/500 preservados. User+Wallet na mesma transação; helper create_wallet usa defaults existentes e inserção direcionada compartilhada com seed, sem tocar usuários alheios. Argon2id existente. UniqueViolation 23505+uq_users_email é o único conflito mapeado como duplicidade; outras falhas de banco são 500 sanitizado com rollback. Não logar payload/SQL/DETAIL.

Ambos os papéis recebem carteira zero. AUCTIONEER continua sem lance/depósito/GET wallet e gerencia próprios lotes; BIDDER não cria lote. Nenhum privilégio admin. Login manual e três demos preservados.

/register tem radios sem preseleção, descrições aprovadas, e-mail/senha, toggle local acessível, hint simples, trava síncrona e foco/erros por campo. 201 leva ao login com confirmação acessível e sem transportar senha. AppLink/History/Back/Forward/reload e retorno canônico por papel preservados. SiteHeader oculta CTA redundante em register para não sobrescrever returnTo.

## Ambiente e comandos reais

Usei cópia isolada /private/tmp/atrio62a-validation, fontes permitidas idênticas por SHA-256, sem dotenv/credenciais, dependências locais reutilizadas. Não modifiquei verify.sh ou infraestrutura do produto. PostgreSQL isolado em container/projeto próprio, porta 55432 e volume próprio; testes em casa_de_leiloes_test, smoke em atrio62a_smoke_test. DATABASE_URL de teste dos focais aponta para alvo fictício não utilizado, diferente do alvo de teste; smoke usa somente seu *_test. Não conectei banco de desenvolvimento. O PostgreSQL original permaneceu em operação.

Scripts temporários de reprodução: /private/tmp/atrio62a-tools/{sync.py,run.py,server.py,check-smoke-db.py,screenshots.mjs}; wrappers usam ambiente filtrado e valores locais fictícios. Não imprimi configuração privada. Executei:

```sh
python3 -B /private/tmp/atrio62a-tools/run.py backend tests/integration/test_registration.py tests/test_csrf.py tests/test_csrf_auth.py tests/test_access_policy.py tests/test_openapi.py tests/test_errors.py tests/test_security.py tests/integration/test_auth_flow.py tests/integration/test_roles.py tests/integration/test_wallet_service.py tests/integration/test_seed.py -q
python3 -B /private/tmp/atrio62a-tools/run.py browser registration.spec.ts session.spec.ts keyboard.spec.ts touch-targets.spec.ts layout.spec.ts
python3 -B /private/tmp/atrio62a-tools/run.py node
python3 -B /private/tmp/atrio62a-tools/run.py gate
python3 -B /private/tmp/atrio62a-tools/run.py smoke real-stack.spec.ts --grep 'cadastro real|deep-link' --workers=1 --trace=off
/private/tmp/atrio62a-validation/backend/.venv/bin/python -B /private/tmp/atrio62a-tools/check-smoke-db.py
node /private/tmp/atrio62a-tools/screenshots.mjs
```

O modo gate executa **VERIFY_E2E=1 ./verify.sh** intacto na raiz da cópia; não substitui etapas. O modo smoke define E2E_REAL_BASE_URL para FastAPI real servindo o build em 127.0.0.1:8026; nenhum mock de dados de negócio, apenas aborta imagens para evitar AIC.

## Resultados reais

| Execução final | Resultado | Exit |
| --- | --- | --- |
| Focais backend ampliados | 589 passed, 1 warning | 0 |
| Focais Playwright após correção de navegação | 107 passed | 0 |
| Node completo focal | 197 pass, 0 fail/skipped | 0 |
| Smoke Playwright real | 3 passed (deep-link + BIDDER + AUCTIONEER) | 0 |
| Conferência direta PostgreSQL smoke | 2 User, 2 Wallet, ambos papéis, saldos zero, Argon2id | 0 |
| Ruff/formato gate | All checks passed; 111 files already formatted | 0 |
| pytest gate | 2408 passed, 1 warning in 141.37s (0:02:21) | 0 |
| ESLint/TypeScript/Vite gate | Aprovados | 0 |
| Node gate | 197 pass, 0 fail/skipped | 0 |
| Playwright gate | 317 passed (31.9s); 7 skipped opt-in real-stack | 0 |
| Docker build gate | Aprovado | 0 |
| VERIFY_E2E=1 ./verify.sh completo | verify.sh: todas as etapas passaram. | **0** |

Os sete real-stack são ignorados por design no gate padrão; três pertinentes foram executados separadamente contra stack real. Os quatro demais real-stack não foram executados nesta sessão. Um warning preexistente Starlette/httpx não afetou aprovação.

Logs brutos temporários: backend-first.log (410 testes iniciais), backend-focal-final.log, browser-focal-final.log, node.log, smoke.log, smoke-db.log e verify-final.log em /private/tmp/atrio62a-tools/. Resultado final do script literalmente:

```text
verify.sh: todas as etapas passaram.
VALIDATION_EXIT_CODE=0
```

## Falhas diagnosticadas e correções

A rodada backend ampliada inicial teve 1 failed/588 passed: o teste literal do catálogo de mensagens ainda não incluía o novo código aprovado. Atualizei a expectativa, sem enfraquecer os demais códigos; 589 passed na repetição. Ruff detectou import/formatação no código novo; organizei/formatei antes dos gates finais.

Um primeiro gate completo passou, mas foi invalidado pela correção do CTA de header que perdia returnTo. Acrescentei regressão, repeti focais e executei novamente todo o gate; só verify-final.log comprova o candidato final. verify-before-navigation.log é histórico anterior, não gate atual.

Primeira tentativa do smoke foi recusada pela CLI por --screenshot=off não suportado, antes de executar testes; a conferência de banco ainda vazio também falhou. Retirei essa opção, mantive traces desligados e repeti: três cenários e conferência PostgreSQL aprovados. Não houve mudança de produto para contornar o smoke.

O navegador integrado não pôde conectar; gerei/inspecionei capturas com Playwright local após tentar a skill de browser. Não alego que as capturas foram aprovadas visualmente pelo usuário.

## Rastreabilidade CA01–08

- CA01: test_registration cadastro nos dois papéis, normalização/+tag/254, senha 7/8/1024/1025, hashing/salt, entrada estrita, login posterior e /api/me; E2E JSON/papel e smoke real.
- CA02: Wallet 0/0 para ambos; helper direcionado não repara demos sem carteira; falhas flush/wallet antes/depois/commit verificadas por outra Session; corrida com duas requisições e barreira no INSERT real.
- CA03/04: registration.spec valida teclado/setas/Space/foco, toggle sem mudança de valor, toque real/hit-test, erros locais/remotos, requests simultâneos no mesmo turno, controle pendente, 1440/375/320 sem overflow global/descendentes; regressões session/layout/keyboard/touch.
- CA05: 201 sem sessão, confirmação acessível em login, senha ausente do state/storage/URL, retorno por papel e rejeição de destinos externos/auth/desconhecidos, Back/Forward/reload/clique modificado; login manual/demos existentes passam. Header sem CTA que sobrescrevia o retorno.
- CA06: inventário bruto detecta sete, expectativa antiga seis reprova, oitava inesperada reprova sem política em caminhos documentais; matriz com/sem SPA e três negativos por escrita. Cadastro também prova zero User/Wallet/cookie e hash/handler não alcançado nos três bloqueios, com controle positivo.
- CA07: duplicidade por constraint real; pk_users forçada produz 500, não 409; log/response sem sentinelas privadas; política/OpenAPI/aliases e envelope literal. Origem/media type/métodos seguros preservados.
- CA08: focais/gate integral/smoke e capturas acima. Não substituo review independente ou validação publicada.

## Capturas temporárias finais

- Cadastro 1440×900: /private/tmp/atrio62a-tools/screenshots/cadastro-1440.png
- Cadastro 375×812: /private/tmp/atrio62a-tools/screenshots/cadastro-375.png
- Cadastro 320×812: /private/tmp/atrio62a-tools/screenshots/cadastro-320.png
- Login atualizado: /private/tmp/atrio62a-tools/screenshots/login-1440.png

Capturas do build final, formulário vazio/sem senha visível; não são golden files. Inspeção de layout não encontrou defeito visual óbvio; sem aceite visual humano novo presumido.

## Escopo, arquivos e estado

- `_bmad-output/implementation-artifacts/6-2-identidade-visual-e-responsividade.md`
- `_bmad-output/implementation-artifacts/6-2a-cadastro-de-usuarios.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/implementation-evidence.md`
- `_bmad-output/specs/spec-story-6-2-identidade-visual-e-responsividade/.memlog.md`
- `_bmad-output/specs/spec-story-6-2-identidade-visual-e-responsividade/SPEC.md`
- `_bmad-output/specs/spec-story-6-2a-cadastro-de-usuarios/.memlog.md`
- `_bmad-output/specs/spec-story-6-2a-cadastro-de-usuarios/SPEC.md`
- `_bmad-output/specs/spec-story-6-2a-cadastro-de-usuarios/implementation-evidence.md`
- `_bmad-output/specs/spec-story-6-2a-cadastro-de-usuarios/registration-contract.md`
- `backend/app/auth.py`
- `backend/app/errors.py`
- `backend/app/wallet.py`
- `backend/tests/integration/test_registration.py`
- `backend/tests/test_access_policy.py`
- `backend/tests/test_csrf.py`
- `backend/tests/test_errors.py`
- `backend/tests/test_openapi.py`
- `docs/uso_de_ia.md`
- `frontend/e2e/real-stack.spec.ts`
- `frontend/e2e/registration.spec.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/src/App.css`
- `frontend/src/App.tsx`
- `frontend/src/LoginPage.tsx`
- `frontend/src/RegisterForm.tsx`
- `frontend/src/RegisterPage.tsx`
- `frontend/src/SiteHeader.tsx`
- `frontend/src/api/auth.test.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/route.test.ts`
- `frontend/src/route.ts`

Arquivo adicional à lista inicial: frontend/src/SiteHeader.tsx, correção mínima do requisito aprovado de navegação/returnTo. Nenhuma alteração fora do objetivo da story. Segredos alterados: nenhum nome detectado na varredura por mtime; conteúdos não lidos. User/migrations/security/csrf/access/seed/main/settlement/LoginForm/navigation preservados por comparação com baseline; AST do login/logout/me/LoginRequest/CurrentUser também idêntica. Não executei Git, gh, commit/push/merge/deploy ou bmad-code-review.

Mantenho 6.2A story/sprint review e SPEC in-review, pronta para revisão independente. 6.2 done por autorização humana e LOW aceito sem correção; 6.1 review por CA2 público pendente; épico 6 in-progress, 6.3–6.7 sem implementação iniciada. Sem camada de review interno/independente executada ou findings de reviewer nesta sessão; fiz somente verificação de implementação/aceite e correções no escopo. Limitações: Chromium, ambiente local, demais real-stack não executados, sem prova pública ou novo aceite visual humano.

## Encerramento do ambiente temporário

Após gates e capturas, encerrei FastAPI de smoke e parei somente o container atrio62a-validation-postgres-1, exit 0, preservando o volume de teste e as evidências. O PostgreSQL original casa-de-leiloes-postgres-1 continuou healthy. Nenhum banco de desenvolvimento foi utilizado.
