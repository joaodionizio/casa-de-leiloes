# Contrato final de cadastro — Story 6.2A

Decidi as QH-01–06 por autorização humana em 29/10/2026: sem Nome/migration; ambos os papéis públicos; login manual; conflito explícito com enumeração conscientemente aceita; chave 6-2a-cadastro-de-usuarios; senha 8–1024 sem composição. Descartei autologin, nome descartado, privacidade fictícia em erro neutro e renumeração. Nenhuma decisão humana permanece aberta.

## 1. Estado comprovado antes do build

| Área | Evidência no código vivo | Consequência |
| --- | --- | --- |
| Usuário | `backend/app/users.py` e migration `0002_users.py`: `id UUID`, `email VARCHAR(254)`, `password_hash TEXT`, `role VARCHAR(16)`, todos NOT NULL; sem defaults de UUID | Não existe Nome, timestamp ou endpoint de cadastro. UUID de conta nova deve ser gerado no servidor. |
| Papéis | `UserRole`: exatamente `AUCTIONEER`, `BIDDER`; `ck_users_role` limita esses valores | Não há admin; proibir autoexpansão futura do contrato público. |
| E-mail | `uq_users_email`; `ck_users_email_lowercase`; login usa `strip().lower()` antes de validar comprimento 1–254 | Banco não garante trim nem formato; cadastro precisa normalizar. Não precisa migration para unicidade atual. |
| Senha | `security.hash_password` usa `PasswordHasher()` Argon2id; login aceita 1–1024 caracteres, sem política de força; seed chama o mesmo helper | Não existe política mínima de cadastro aprovada. Não aplicar nova política ao login de contas existentes. |
| Login | `POST /api/auth/login`, PUBLIC, resposta `CurrentUser={email,role}`; 401 `invalid_credentials` idêntico para senha errada/e-mail ausente, com hash de referência | Preservar login; nada de token/hash/UUID em resposta. |
| Sessão | JWT HS256, `sub/role/iat/exp`, 8 h; cookie HttpOnly/SameSite=Lax/Path=/, sem Domain; HTTPS usa Secure e `__Host-auction_session`, localhost HTTP `auction_session` | `/api/me` consulta banco e invalida papel divergente. Sem refresh/revogação nova. |
| Carteira | Migration `0004_wallets.py`: PK/FK `wallets.user_id → users.id`, RESTRICT; saldos BIGINT default zero e CHECKs | Carteira depende do usuário; não pode nascer primeiro. |
| Criação de carteira | `ensure_wallets(session)` insere carteiras faltantes de **todos** os usuários, sem filtrar papel; seed o chama sem commit intermediário | Ambos os papéis têm carteira. Helper atual é global e não é usado em requisições. |
| Recebimento | `backend/app/lot_settlement.py` trava carteiras do vencedor e do `lot.auctioneer_id`, ordenadas por user_id, para debitar/creditar | Leiloeiro novo também precisa de carteira; não lhe conceder GET/deposit, que continuam BIDDER. |
| Seed | `seed_users`: IDs fixos e ON CONFLICT(id) DO NOTHING; Argon2 só para ausentes; `run_seed` cria usuários/carteiras/demo na mesma transação | Não remover/alterar demos, nem pré-carregar saldo; seed não é o serviço de cadastro. |
| Erros | `errors.py`: `{status,code,message[,details]}`; 409 `conflict` já existe, mas código específico de e-mail não existe; 422 só loc/type | Não inventar catálogo já existente. Na 6.2A adiciono email_already_registered conforme QH-04 aprovada. |
| Logs | `db.py` usa `hide_parameters=True`, mas comenta que DETAIL do PostgreSQL pode conter valores | Não logar IntegrityError esperado nem corpo/parâmetros. SQL/stack nunca chegam à resposta. |
| Acesso/CSRF | `api_route` declara PUBLIC/OPTIONAL/AUTHENTICATED/AUCTIONEER/BIDDER; `ApiWriteGuardMiddleware` atua antes do roteamento de escritas `/api` | Nova rota PUBLIC continua protegida; nenhuma exceção. |
| Front | `App.tsx`, `route.ts`, `navigation.ts`: History API própria; LoginPage/LoginForm e api/auth.ts usam POST JSON same-origin, sessão só no cookie | Não existe `/register`; incluir rota, título, estado e links reais juntos. |
| Retorno | `returnTo` em history.state; `safeReturnPath` aceita só rotas conhecidas, normaliza via routePath e verifica papel; query/hash descartados | Estender a regra para rejeitar `/register` como destino, além de `/login`. Não usar URL recebida diretamente. |
| Visual | `App.css`: `.main-column` até 24rem, campos/divisores, tokens próprios, foco de 2px; demos usam trava síncrona inFlight antes do await | Reutilizar acabamento da 6.2; não reescrever login/demos. |

Consultei CLAUDE.md, ARQUITETURA.md (AD-11/22/29 e AD-2/3/4/17/19/24/27/30), desafio, epics, DESIGN, EXPERIENCE, FRONTEND-WORKFLOW, FECHAMENTO-DE-EPICO e deferred-work. Consultei stories 2.1/2.2/6.1/6.2, SPECs 6.1/6.2 e reviews `code-review-story-6-1.md`/`code-review-story-6-2.md`. A aprovação e aceitação do LOW 6.2 informadas neste pedido prevalecem sobre os status antigos ainda em review; não os altero.

Inspecionei auth/security/users/seed/wallet/access/csrf/errors/main/db, migrations de usuários/carteiras e recebimento na liquidação; testes `test_security.py`, `test_csrf_auth.py`, `test_csrf.py`, `test_access_policy.py`, `test_errors.py`, integrações auth/users/seed/wallet; App/route/navigation/LoginPage/LoginForm/api-auth/App.css e session/layout/touch/keyboard, mockApi, Playwright config e real-stack. A inspeção é estática, com sonda isolada da gramática BMAD, sem importar a app nem executar testes do produto.


## Contrato aprovado

POST /api/auth/register, AccessPolicy.PUBLIC, handler def via api_route existente, JSON same-origin e Cache-Control:no-store. Request extra=forbid com email, password, role; sem UUID, nome, saldo, claims, hash ou admin. role é Literal["BIDDER", "AUCTIONEER"], não string arbitrária/enum expansível. UUID gerado no servidor.

Email strip/lower antes de validar comprimento 1–254; exatamente um @, local/domínio não vazios e nenhum whitespace interno. Sem DNS, sem remover pontos/+tag, sem mudar login. Password 8–1024 caracteres, sem composição, trim, normalização ou truncamento. Reusar security.hash_password Argon2id.

201 Created com somente {email,role}, sem token/ID/hash/senha ou Set-Cookie. 409 email_already_registered com envelope existente e mensagem frontend “Este e-mail já está cadastrado. Entre para continuar.”; nenhum dado da conta existente. 422 validation_error com loc/type; 403 csrf_origin_mismatch/missing; 415 unsupported_media_type; 500 internal_error genérico. Cache no-store coerente. Mapear UI por code, nunca message do backend.

## Transação e segurança

User+Wallet na mesma Session/unidade: hash antes da escrita, inserir User, flush, criar Wallet direcionada, commit único na rota. Carteira zero por defaults existentes para BIDDER e AUCTIONEER; leiloeiro precisa receber settlement. Extrair/reutilizar helper mínimo compartilhado sem chamar ensure_wallets global para tocar terceiros. Não duplicar regra de saldo nem fazer commit intermediário.

uq_users_email é a autoridade concorrente; duas requisições normalizadas iguais produzem um User/Wallet, um 201 e um 409. Capturar somente SQLSTATE 23505 com constraint uq_users_email como duplicidade, por atributos estruturados, não texto. Rollback completo em falha de Wallet/flush/commit anterior à confirmação. Outros erros não viram duplicidade. Provar por outra Session. Não logar payload/senha/hash/SQL/DETAIL; hide_parameters sozinho não resolve DETAIL do PostgreSQL. Tratar falhas de persistência no boundary com resposta segura e log de metadados, sem representação bruta da exceção.

Middleware, políticas, JWT/login/cookies/CSRF/Origin/Content-Type/envelope permanecem. Não emitir sessão no cadastro. GET/HEAD/OPTIONS nunca cadastram nem criam carteira. Sem retry automático; timeout depois do commit não garante rollback do que já confirmou. Seed/demos, senhas e login rápido/manual intactos; conta existente nunca recebe update de credenciais/papel.

## UX aprovada

/register pela History API existente; marca/tokens/fontes ÁTRIO, campos/divisores sem card decorativo excessivo, sem copiar identidade/ativos de referência. H1 Cadastro; eyebrow Nova conta discreto; fieldset/legend Como você quer participar?; radios nativos sem preseleção:

- Licitante — “Deposite saldo simulado, dê lances e arremate obras.”
- Leiloeiro — “Crie e gerencie seus lotes de arte.”

Depois E-mail, Senha, hint “Use pelo menos 8 caracteres.”, toggle Mostrar senha/Ocultar senha type=button, CTA Criar conta e “Já tem conta? Entrar”. Sem Nome, indicador de força ou confirmação de senha. autocomplete username/new-password, paste/password manager permitidos. Toggle não altera valor/foco nem submete.

Trava síncrona inFlight antes do await, não só setState; durante request “Criando conta…”, campos legíveis e controles pertinentes indisponíveis; um POST mesmo no mesmo turno JS. Falha libera controles e foca primeiro erro de campo ou resumo global. role=alert, aria-invalid/describedby pertinentes, seleção semântica com indicação além de cor, setas/Space/Tab, foco visível/alvos ~44px; sem overflow a 320px ou overflow-x:hidden para mascarar.

201 → limpar senha → /login pelo mecanismo existente com confirmação acessível “Conta criada com sucesso. Entre para continuar.” e returnTo seguro. Nenhuma senha/token no state/URL/storage/log. Não é necessário prefill de e-mail. Login recebe “Não tem conta? Criar conta”; preservar 3 demos/manual. Usuário já autenticado em /register segue padrão /login e vai a destino seguro sem trocar conta.

Login↔Cadastro preserva só estado seguro; AppLink/navigate/replaceRoute/Back/Forward/reload/deep-link existentes. safeReturnPath recusa absoluto, //host, desconhecido, /login, /register e áreas incompatíveis com papel efetivo, inclusive query/hash; retorna caminho canônico ou /. Evitar segundo roteador.

## Impacto obrigatório CA1 / Story 6.1

Inventário bruto independente da política descobre W7 POST /api/auth/register; sete escritas no candidato, lista antiga falha antes de atualizar expectativa. Atualizar REAL_WRITES/EXPECTED_POLICIES/OpenAPI; não mudar middleware. Mutações de sétima inesperada tornam-se oitava, mantendo regressões documentais/Route/APIRoute/mounts/métodos/política inválida.

Register com/sem SPA: Origin divergente→403 csrf_origin_mismatch; Content-Type ausente→415 unsupported_media_type; não JSON→415 unsupported_media_type. Em todos handler não executado, zero User/Wallet/cookie. Provar sentinela com controle positivo e banco real; assegurar header realmente ausente. Substituir teste de ausência de signup por único cadastro permitido sem aliases/users gerais. Renovar somente evidência CA1 local invalidada; 6.1 continua review por CA2 publicado pendente, inalterado.

## Identificação e processo

Parser de planejamento captura 6.2A mas gera 6-2A que não passa na gramática minúscula de status. Decidi heading técnico “Story 6.2a: Cadastro de usuarios”, chave 6-2a-cadastro-de-usuarios e nome humano Story 6.2A. Resolver de build descreve comparação numérica sem suporte garantido a sufixo: usar esta SPEC/pasta/chave explicitamente, confirmar chave única exata no sprint, sem resolução aproximada para 6.2. Não alterar skill nem renumerar 6.3–6.7.

Sincronizar 6.2 done por aceite humano técnico/visual e LOW R6.2-01 conscientemente aceito; não corrigir LOW. Atualizar D2/FR1 como ampliação aprovada, preservando 2.2 sem cadastro como histórico. Nova story ready-for-dev→in-progress→review; SPEC ready-for-dev→in-progress→in-review. Épico 6 segue in-progress. Sem bmad-code-review nesta sessão; review independente posterior. Autorização presente dispensa nova aprovação entre SPEC/build.

## 8. Critérios e matriz backend

| CA / testes | Prova mínima planejada |
| --- | --- |
| CA01 / B01 | BIDDER válido → sucesso aprovado, uma linha User, e-mail/papel exatos, sem campos privados; login posterior e `/api/me` corretos. |
| CA01 / B02 | AUCTIONEER válido; cria/gerencia somente lotes próprios; não deposita/não dá lance; BIDDER não cria lote.  |
| CA01 / B03 | Hash real começa $argon2id$, verifica senha correta e recusa outra; salts distintos; senha/hash não aparecem em response, erro, logs ou token. Não provar hashing só com mock. |
| CA01 / B04 | Trim+lower antes de validação/persistência; maiúsculas/espaços e duplicidade equivalente; limites normalizados 254/255 e formato; não remover +tag/pontos. |
| CA07 / B05 | E-mail já existente (inclusive demo) → 409 email_already_registered, sem alteração de hash/papel/carteira e sem autenticar conta existente. Banco continua autoridade. |
| CA07 / B06 | Duas Sessions/requisições concorrentes no mesmo e-mail normalizado, barreira determinística e timeout limitado: uma criação, um 409 email_already_registered, uma carteira; nenhuma stack/SQL. PostgreSQL real, teste necessário pela nova garantia de corrida. |
| CA01 / B07 | Ausentes, vazio, null, tipos errados, extras, senha 8–1024 caracteres, papel ADMIN/enum futuro/string/lista e JSON malformado→422 sanitizado; nenhum User/Wallet novo. |
| CA02 / B08 | Ambos os papéis aprovados com carteira 0/0 e disponível 0, uma por usuário; nenhuma carteira/saldo alheio tocado, seed idempotente mantém demos e usuários novos. |
| CA02 / B09 | Injetar falha após flush User, durante Wallet e no commit antes de confirmar: rollback visto por outra Session; ausência de cookie e 500 literal genérico. Constraint/FK/restrições em PostgreSQL real. |
| CA06 / B10 | Três negativos obrigatórios register com payload válido e PG real: 403 origem, 415 ausência e 415 não JSON; sem usuário/carteira/cookie, handler não executado; controles positivos. |
| CA06 / B11 | Inventário bruto descobre W7 com/sem SPA, lista antiga falha e mapa aprovado tem sete; nova escrita inesperada é a oitava e reprova mesmo sem política em caminho documental. |
| CA06 / B12 | PUBLIC explícita e dependência coerente, OpenAPI request/response/erros reais; sem signup/users alternativos e sem fallback SPA em POST. |
| CA05 / B13 | Sucesso 201 sem cookie e /api/me anônimo até login normal; cookie/JWT do login continuam preservados. |
| CA06/07 / B14 | Origin ausente/Referer válido e divergente, Origin prioritário, root_path, media type +json/ambíguo; métodos seguros sem mutação, 405/Allow e HEAD sem corpo; zero CORS permissivo. Reusar cobertura existente onde suficiente. |
| CA07 / B15 | Erro único status=HTTP, message português, details só loc/type; sentinelas em valores de senha/nome/e-mail não ecoadas. Campos extras em loc podem refletir chave maliciosa: dívida D1 existente não autoriza adicionar input/ctx nem alegar sigilo de nomes de chaves. |
| CA01 / B16 | Nome ausente e name extra recusado; schema/migrations/User intactos. |

Apoiar em tests/auth_support, wallet_support, fixture clean_users e Session factory existente. Não usar SQLite para constraints/transação/corrida. Não executar seed/DB de desenvolvimento nem depender de internet. Provas anteriores são regressões, não resultados atuais desta SPEC.

## 9. Matriz frontend/E2E

| CA / testes | Prova mínima planejada |
| --- | --- |
| CA03 / F01 | Cadastro em **1440×900**, **375×812**, **320×812**, com textos/erros longos: campos, radios, toggle, links e CTA dentro do viewport; medir scrollWidth e descendentes, sem screenshot pixel-perfect. |
| CA04 / F02 | Tab/Shift+Tab/setas/Space/Enter: selecionar cada papel permitido, checked/texto anunciável, foco visível não cortado e ordem; papel vazio leva foco ao grupo/primeiro radio. |
| CA04 / F03 | Toggle conserva exatamente senha/value, foco e autocomplete; label muda, não gera request nem submit; alvos de toque reais sem sobreposição. |
| CA03 / F04 | Submit manda JSON exato e papel efetivo; response válida segue fluxo aprovado; 422/duplicado/403/415/rede/500 mostram erro pertinente em português e foco; nenhum sucesso fictício em erro. |
| CA03 / F05 | Duplo clique/Enter/combinações no mesmo turno JS e durante promessa pendente resultam em **um POST**; indicador Criando conta…, controles bloqueados e liberação após falha. |
| CA05 / F06 | Login↔Cadastro com links reais, reload/deep-link, Back/Forward, clique modificado; returnTo interno sobrevive e externo/rota auth/papel errado cai em `/`; rejeição deve ser provada com estado realmente preservado. |
| CA05 / F07 | Confirmação acessível sem autenticação em /login, login posterior normal, papel/header/reload e destino seguro. |
| CA05 / F08 | Três demos e login manual da 6.2, inclusive exclusão mútua/destino/erro, continuam passando. Conta nova não entra na lista demo. |
| CA01/04 / F09 | Nome ausente no DOM e payload; não coletar dado descartado. |
| CA08 / F10 | Smoke local integrado com FastAPI servindo build + PostgreSQL de teste e dados fictícios: criar, entrar/reload, papel/carteira e `/register` deep-link. Distinguir esta prova do mock e da validação pública futura. |

Reutilizar `frontend/playwright.config.ts`: Chromium, Vite preview do build, interceptação mockApi, sem internet; adicionar mock de cadastro com estado de conta separado das demos. Node testa parsing/API/returnTo; Playwright testa DOM/layout/foco. Infra `real-stack.spec.ts` é opt-in por E2E_REAL_BASE_URL e **não roda automaticamente** no verify com E2E; executar o cenário integrado separadamente em ambiente isolado, sem `.env*`, e registrar seu comando real. Disponibilizo capturas para inspeção visual humana antes do review independente, sem pausa adicional antes dos gates por autorização expressa. Não constituem aceite visual humano nem baseline pixel-perfect e não guardam senha visível.


## Code Map e arquivos autorizados

Backend auth.py (request/rota/transação), wallet.py (helper direcionado compartilhado), errors.py (novo código); testes integration/test_registration.py, test_csrf.py, test_access_policy.py, test_openapi.py e regressões de auth/wallet/seed pertinentes. Nenhuma mudança em User, migrations, security/JWT/login/csrf/access/config/seed ou settlement necessária.

Frontend App.tsx, SiteHeader.tsx (CTA de auth oculto em register para não perder returnTo; arquivo adicional à lista inicial), route.ts/route.test.ts, navigation existente reutilizada, LoginPage.tsx/LoginForm.tsx para link/aviso, novos RegisterPage.tsx/RegisterForm.tsx, api/auth.ts e testes de client, App.css local; E2E registration.spec.ts e support/mockApi.ts/session/layout/keyboard/touch/real-stack quando necessário.

Coordenação: SPEC/companion/memlog, story 6-2a, 6.2/sprint/epics D2/FR1, uso_de_ia, evidência afetada CA1 6.1, implementation-evidence. A implementação delegada limita-se a produto/testes; coordenação executa gates em cópia isolada sem dotenv. Não alterar verify/config/infra por conveniência.

## Tasks & Acceptance (Given/When/Then)

CA01: dado visitante e payload permitido, quando POST válido, então 201 com User/papel/e-mail normalizado e senha Argon2 verificável, sem informações privadas, e login posterior funciona.
CA02: dado cadastro, quando User/Wallet/flush/commit falha antes de confirmar, então nenhuma entidade parcial; em sucesso ambos os papéis possuem 0/0. Concorrência dup produz exatamente um User/Wallet e 201+409.
CA03: dado formulário, quando envio inválido/duplicado/rede/servidor ou submit simultâneo, então mensagem/foco pertinente e um POST por tentativa.
CA04: dado viewport 1440/375/320 e teclado/toque, quando opero radios/toggle/campos/links, então seleção semântica, valor preservado, foco/labels legíveis e sem overflow.
CA05: dado 201, quando continuo, então vejo confirmação em /login sem nova sessão/senha transportada; login normal/reload/returnTo seguro funcionam e demos permanecem.
CA06: dado nova rota com/sem SPA, quando inventário/negativos CA1 rodam, então W7 é encontrada sem política, 403/415 não executam handler nem criam dados/cookie, oitava inesperada reprova e CA2 público permanece pendente.
CA07: dado entrada/erro de persistência, quando respondo, então contrato único sem SQL/hash/senha/dado alheio; duplicidade só constraint correta.
CA08: dado candidato final, quando focais/smoke real/VERIFY_E2E=1 ./verify.sh rodam, então todos passam exit 0 e screenshots temporárias ficam disponíveis antes de review independente.

## Fora de escopo e riscos aceitos

Sem Nome/migration/perfil/admin/recuperação/troca/confirmar e-mail/OAuth/MFA/CAPTCHA/rate limit geral/refresh/ledger/moeda real/idempotency-key, sem 6.3–6.7. Aceitei enumeração de conta explicitamente; papéis públicos não verificam identidade. Argon2/endpoint público tem risco de volume, sem evidência crítica que autorize ampliar escopo. Sem Git/gh/commit/push/merge/deploy, .env* ou credenciais privadas. Screenshots temporárias sem senhas visíveis, não golden files. Referências antigas não foram reanexadas; estrutura textual e ÁTRIO aprovado são base visual.

## Verification

Focais necessários, PostgreSQL real para constraints/transação/concorrência; smoke local FastAPI+build+PostgreSQL de teste (cadastro→User/Wallet→login→auth→reload→me/papel). Playwright mock não comprova isso. Candidato final passa VERIFY_E2E=1 ./verify.sh, exit 0, em isolamento sem dotenv, sem DB de desenvolvimento. Capturar Cadastro 1440/375/320 e Login atualizado. Não alegar deploy ou review independente nesta sessão; entregar story review/SPEC in-review com resultados reais e limitações. A aprovação humana desta SPEC e autorização de build já foram fornecidas.
