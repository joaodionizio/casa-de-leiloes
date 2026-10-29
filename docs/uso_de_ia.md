# Uso de IA no desenvolvimento — ÁTRIO (antes Casa de Leilões)

## Fechamento oficial do Epic 3 — registro em 27/10/2026

Registrei o review agregado do Epic 3, a correção de F-01 MEDIUM e o re-review
aprovado; aceitei o LOW opcional de cobertura do effect da sala como não
bloqueante. Os reviews retrospectivos de integração dos Epics 1/2 foram aprovados,
com LOW documental do Epic 2 resolvido. Não os apresento como reviews dos diffs
históricos originais nem reabri os findings nesta sessão.

A evidência final fornecida, pós-correção e anterior ao merge, é
`VERIFY_E2E=1 ./verify.sh`, exit 0: pytest 2036 passed, npm test 160 passed,
Playwright 189 passed/5 skipped; Ruff, format, ESLint, tsc, Vite e Docker build
passaram. A IA não reexecutou verify neste fechamento documental.

Fiz **manualmente** merge do Epic 3, push da `main`, configuração do Render,
deploy de recuperação 2+3, validação pública e smoke dos fluxos entregues.
Confirmei aplicação funcionando em <https://casa-de-leiloes-i1xr.onrender.com>,
branch `main`, commit publicado `3d3ea97`. **O deploy foi meu, não da IA.**
O deploy do Epic 2 foi tardio: não aconteceu no fechamento original e foi
recuperado agora conjuntamente com o Epic 3. Resultados individuais do checklist,
timestamp/ID/logs de deploy: **não individualizado na evidência manual**.

Autorizei Epic 3 `done`, com stories 3.1–3.6 `done`. Pedi à IA somente registro
e consistência documental; ela preservou código, migrations, secrets e os
findings históricos. Retrospectives continuam opcionais e Epics 4–6 em backlog.
Epic 4 pode ser iniciado após o commit administrativo manual deste fechamento.

## Evolução do processo — registro histórico de 26/10/2026

Os registros por story abaixo são cronológicos. Frases como "ficou em review",
"Epic 3 in-progress" ou "3.3 backlog" descrevem aquela sessão; fechamentos
posteriores não apagam a evidência original. O sprint e os arquivos vivos regem
o estado atual. Não reclassifico reviews por story como reviews agregados.

### Claude Code e Codex durante o Epic 3

Usei Claude Code anteriormente e durante o Epic 3 para planejamento,
implementação e reviews; Codex passou a assumir parte das implementações,
correções e revisões. Por exemplo, a correção da 3.2 registra Codex/GPT-6.1,
e as 3.4/3.5 registram build com Claude e review independente com modelos GPT.
Os relatos de cada sessão identificam o modelo quando há evidência, inclusive
quando diferiu do solicitado. Não atribuo retroativamente a um modelo uma
sessão sem confirmação.

Decidi separar implementação e review por modelo/sessão para reduzir viés,
combinar review adversarial, mutation testing direcionado, correções aprovadas
e re-review focado. Usei PostgreSQL real onde saldo, travas, concorrência e
integridade exigiam. As stories 3.1–3.6 registram os casos e resultados reais;
não extrapolo esses números para a auditoria atual. É metodologia de
desenvolvimento/revisão que escolhi, não requisito adicional da Verzel.
As decisões de produto, arquitetura, aceite de findings, Git e deploy
continuam sob minha responsabilidade humana.

### BMAD 6.12.4 e compatibility shims

Durante o Epic 3, skills como `bmad-create-story` não apareciam. O diagnóstico
registrado nas stories 3.2/3.3 e nesta auditoria foi mudança de distribuição,
não corrupção da instalação: esses comandos antigos passaram ao grupo
compatibility shims/deprecated, e a instalação estava com shims desabilitados.
`bmad-build` é o caminho atual de implementação; `create-story` permanece como
compatibilidade, sem precisar reescrever stories concluídas.

Conforme o histórico informado por mim para esta auditoria, usei o instalador
oficial com os shims habilitados, sem trocar a versão BMAD. A evidência viva em
`_bmad/_config/manifest.yaml` registra **6.12.4**, `installShims: true` e os IDEs
`claude-code` e `codex`. Os READMEs em `_bmad/core/v6-shims/` e
`_bmad/bmm/v6-shims/` explicam a compatibilidade. Na conferência desta sessão,
os conjuntos de nomes `bmad-*/SKILL.md` em `.claude/skills/` e `.agents/skills/`
foram iguais, sem diferenças. Não inventei uma contagem de skills nem reinstalei
ou alterei a configuração nesta tarefa.

### Auditoria administrativa antes do fechamento do Epic 3

Decidi corrigir documentação/status e centralizar os gates em
`docs/FECHAMENTO-DE-EPICO.md`, com checklist manual em
`docs/DEPLOY-RECUPERACAO-EPICS-2-3.md`. O Epic 2 foi concluído localmente e
incorporado à `main` (informação minha); seu deploy foi postergado por falha de
processo. Naquele momento, planejei a recuperação conjunta 2+3, agora concluída conforme
o registro de fechamento acima. Não existe evidência formal localizada
de reviews agregados originais dos Epics 1/2: os reviews por story permanecem
válidos, e preparei integração retrospectiva 1/2 e review normal do Epic 3.
Na auditoria inicial, os arquivos `code-review-epic-1/2/3.md` eram templates
sem execução; os reviews foram posteriormente executados e aprovados.

A Story 1.4 tinha evidências públicas e sprint `done`, mas cabeçalho `review`;
sincronizei o cabeçalho e Epic 1 `done`, sem fingir que o review agregado original
foi realizado. Preservei Epic 2 `done` histórico com a dívida operacional
explícita. Naquela sessão, mantive Epic 3 **`in-progress`** até todos os gates, mesmo com as
stories 3.x concluídas; não iniciei Epic 4. Retrospective BMAD é opcional.

A tarefa administrativa foi executada no Codex, modelo efetivo **GPT-6.1 Sol**
(informado pelo ambiente); o pedido citava GPT-6 Astra High. Registrei essa
limitação sem afirmar uma troca de modelo que não ocorreu. A IA inspecionou os
arquivos vivos, código de configuração/startup/rotas, migrations, specs e
registros históricos, e consultou a documentação oficial do Render para a
opção de deploy manual. O painel e o ambiente público não foram inspecionados.

Fiz apenas conferência estática/documental e comparação de arquivos locais;
não executei `verify`, pytest, Playwright ou mutações nesta tarefa. O harness
de integração recria o schema do banco de teste, e testes destrutivos estavam
fora da autorização desta auditoria. Naquela auditoria, o verify completo final e os smokes
ainda eram gates a executar (hoje concluídos), sem reutilizar números históricos como resultado
novo. Nenhum código de aplicação, migration, segredo ou regra de negócio foi
alterado; nenhum Git, PR ou deploy foi executado e nenhum `.env*` foi lido.

## Story 1.1 — Fundação mínima do monorepo

Usei o Claude Code com Opus para planejamento e revisão e Sonnet para implementação.

### O que a IA fez

- Durante a implementação apareceu uma incompatibilidade na forma como o preset do `eslint-plugin-react-hooks` estava sendo consumido pelo flat config. Após inspeção, a IA propôs `reactHooks.configs.flat.recommended`, que é a forma de consumo pensada para flat config nessa versão.
- Verificou em tempo real a disponibilidade da chave via `node -e` antes de aplicar a edição, evitando uma suposição sem confirmação.
- Criou `verify.sh` com `set -euo pipefail` e fail-fast na primeira etapa que falhar, conforme AD-27.
- Executou cada verificação individualmente e depois o `verify.sh` completo, mostrando a saída real de cada passo.

### O que eu decidi

- Manter ESLint 10 e os plugins nas versões atuais (sem downgrade).
- Usar `reactHooks.configs.flat.recommended` em vez de reescrever a configuração manualmente. Escolhi o preset `recommended` por ser suficiente e menos experimental para este projeto, e revisei a decisão antes da implementação.
- Escopo da story: apenas lint, typecheck, build e verify.sh — sem PostgreSQL, autenticação nem nenhuma feature de domínio.

### Alternativas descartadas

- Downgrade do `eslint-plugin-react-hooks` para uma versão compatível com o consumo anterior do preset: descartei porque aumentaria a dívida de atualização e contraria a decisão de manter as versões atuais.
- Configuração manual de regras do react-hooks em vez de usar o preset: descartei porque o preset cobre todos os casos corretamente e a configuração manual seria redundante e mais frágil.

### Limitações e observações

- O pytest emitiu um `StarletteDeprecationWarning` sobre uso de `httpx` com `starlette.testclient`; a correção recomendada (`httpx2`) não está no escopo desta story e será tratada quando o backend evoluir.
- A IA não tomou nenhuma decisão de arquitetura; todas as escolhas foram minhas ou já estavam nas ADs vinculantes.

## Story 1.2 — PostgreSQL com bancos isolados e migrations

Usei o Claude Code com Sonnet para implementar, a partir de uma story e de decisões (D1 a D8) que eu já tinha fechado com Opus.

### O que a IA fez

- Criou `compose.yaml` (PostgreSQL 18, volume em `/var/lib/postgresql`, healthcheck por TCP, porta só em `127.0.0.1`) e o script de criação dos bancos `casa_de_leiloes_dev` e `casa_de_leiloes_test` em `docker/postgres-init/`.
- Escreveu `app/config.py` (pydantic-settings, normalização da URL por componentes), `app/db.py`, a configuração do Alembic com revisão inicial vazia e os testes unitários e de integração.
- Criou a guarda do banco de teste (`tests/db_guard.py`) e o `conftest.py` que recria o schema `public` do `_test` e roda `alembic upgrade head` antes dos testes.
- Alterou `verify.sh` para checar Docker/Compose, subir o PostgreSQL e dar defaults locais fictícios às URLs sem sobrescrever o ambiente.
- Executou dois comandos em paralelo, e o `cd` de um deles fez arquivos novos (`compose.yaml`, `docker/`, `alembic.ini`, `migrations/`, `.env.example`) serem criados dentro de `backend/`. A IA moveu quase tudo para os lugares certos; só `backend/backend/.env.example` ficou de fora, porque a regra de proteção de `.env*` impediu o agente de movê-lo e de escrever `backend/.env.example`. Eu movi manualmente `backend/backend/.env.example` para `backend/.env.example` e removi `backend/backend/`. A pendência ficou resolvida antes do review.

### O que eu decidi

- Tudo o que está em D1 a D8, em Python 3.13, o script em `docker/postgres-init/` e os defaults fictícios no `verify.sh`.

### Alternativas descartadas

- As listadas em cada decisão da story (por exemplo `create_all()`, só `DATABASE_URL` e `/health/db`).

### Limitações e observações

- A regra de proteção de `.env*` impediu o agente de criar ou mover `.env.example`; resolvi isso manualmente, como descrito acima.

## Story 1.3 — SPA na mesma origem e imagem multi-stage

Usei o Claude Code com Sonnet para implementar, a partir de uma story e de decisões (D1 a D7) que eu já tinha fechado com Opus.

### O que a IA fez

- Escreveu `app/spa.py` e a fábrica `create_app` (fallback só para GET/HEAD, `/api` e `/health` fora do fallback, recusa de path traversal e de symlink para fora do `dist`), a configuração `SpaSettings`, a página de saúde em TypeScript, o proxy do Vite, o `Dockerfile` multi-stage, o `.dockerignore`, o `start.sh` e a etapa `docker build` no `verify.sh`.
- Escreveu 49 testes novos (`test_spa.py` e `test_openapi.py`; na primeira versão do texto, escreveu "50", contando também o `test_health.py` existente) e rodou o smoke test real da imagem contra o PostgreSQL do Compose, incluindo os dois negativos.
- Errou um teste: conferiu o corpo JSON de uma resposta a `HEAD /health`, que não tem corpo. Corrigiu para conferir `Content-Type` e `Allow`.
- Trocou um `Record<...>` por uma função simples no `App.tsx` para respeitar o AD-4, e tirou `--system` do `useradd` para eliminar um aviso de uid.
- No negativo A do smoke, a primeira captura (`tail`) cortou as linhas do Alembic e o contêiner já tinha sido removido; repetiu só esse caso para obter a prova da ordem. No `verify.sh` final, o `echo` do código de saída ficou vazio por erro de sintaxe do zsh, então só consta a mensagem final do script.

- Depois do review, corrigiu só os três findings que aprovei: `SPA_DIST_DIR` relativo passou a valer contra `BACKEND_DIR` (validador em `SpaSettings`, não contra o cwd); o fallback passou a normalizar o caminho com `posixpath` antes das guardas de `/api` e `/health` (`/health/` e `/lots/../api/x` deixaram de devolver `index.html`); e um teste fixa o fallback como última rota. Escreveu os testes antes das correções e confirmou que 9 falhavam no código anterior. Mais 28 testes (77 nos dois arquivos).

### O que eu decidi

- D1 a D7 e as decisões do planejamento (R1 a R3), incluindo `SPA_DIST_DIR` opcional em desenvolvimento e obrigatório na imagem, o proxy do Vite em vez de CORS e o `docker build` (sem `docker run`) no `verify.sh`.

### Alternativas descartadas

- As listadas em cada decisão da story (migration no `lifespan`, CORS em desenvolvimento, Alpine, `uv` em `latest`, devolver `index.html` para qualquer caminho).

### Limitações e observações

- O `StarletteDeprecationWarning` do `httpx` segue aparecendo no `pytest`; fora do escopo.
- O front-end ainda não tem ferramenta de teste (Q10); a página de saúde foi verificada por lint, typecheck, build e pelo smoke da imagem.
- O deploy no Render é da Story 1.4.


## Story 1.4 — Primeiro deploy no Render (fase local, antes do deploy)

Usei o Claude Code com Sonnet para implementar, a partir de um plano (P1 a P14) que eu já tinha fechado com Opus. A primeira parte cobre a fase local; a segunda, o deploy e a validação pública.

### O que a IA fez

- Corrigiu o `sprint-status.yaml` (Story 1.3 para `done`) antes de qualquer código e marcou a 1.4 como `in-progress` ao começar.
- Escreveu primeiro `tests/test_infra_check.py` e rodou só esse arquivo antes de implementar: a coleta falhou com `ImportError`, porque o módulo `app.infra_check` ainda não existia (não houve falhas por teste, e sim um erro de coleta).
- Criou `app/infra_check.py` (cookie técnico `__Host-infra_check`, WebSocket técnico de eco com checagem de `Origin` por host, função pura `origin_host`) e registrou o router em `main.py`, antes do fallback da SPA. Nenhum arquivo fora da lista combinada foi alterado; `verify.sh`, `Dockerfile`, `start.sh`, `config.py`, `spa.py` e os testes existentes ficaram intactos.
- Na primeira passada, o Ruff reprovou uma linha longa e a formatação de dois arquivos novos; a IA ajustou só esses dois arquivos.
- Escreveu o procedimento de deploy no README, as decisões P1 a P14 na story e a linha de pendência do `epics.md`.

### O que eu decidi

- P1 a P14 e a exceção de dois commits para esta story (A antes do deploy, B depois da validação pública).

### Alternativas descartadas

- As listadas em cada decisão da story (por exemplo `render.yaml`, `--forwarded-allow-ips='*'`, `APP_ENV` para o cookie e eco contínuo no WebSocket).

### Limitações e observações

- A IA não acessa o painel do Render, não vê a `DATABASE_URL` e não faz commit nem deploy.
- O `StarletteDeprecationWarning` do `httpx` continua aparecendo no `pytest`; fora do escopo.

### Deploy e validação pública

- Usei IA para planejar e implementar as duas verificações técnicas (cookie e WebSocket) e para redigir a documentação. Revisei o código antes do commit A e corrigi os findings LOW que aprovei no review (testes e documentação, sem código de produção).
- Configurei o Render manualmente, pelo painel: o PostgreSQL, o Web Service, a região, a branch, o Auto-Deploy Off e a variável `DATABASE_URL`. A IA nunca recebeu a `DATABASE_URL` nem credenciais, e não acessou o painel.
- Revisei pessoalmente o primeiro deploy (build, Alembic antes do uvicorn, serviço `Live`) e validei HTTP, cookie e WebSocket na URL pública. A IA só fez `GET` do `index.html` e dos assets para registrar o `Content-Type` real.
- O fechamento do WebSocket público resultou em `1006` nos dois clientes que testei (console do Edge e `websockets`), embora o código envie `close(1000)` e, localmente, o fechamento tenha sido `1000`. Optei por documentar o resultado real em vez de alterar o código sem evidência da causa. A causa continua não determinada.
- O redeploy manual do mesmo commit confirmou que a migration é idempotente: o Alembic rodou de novo sem reaplicar a `0001`.
- O cold start não foi observado nesta validação, e não fiz espera artificial; não há tempo registrado.
- O banco gratuito expira em 23/11/2026, data mostrada pelo painel.


## Story 2.1 — Formato de erros e validação de Origin

Usei o Claude Code com Sonnet para implementar, a partir de um plano (P1 a P8 e D1 a D6) que eu já tinha fechado com Opus no Plan Mode. A story ficou em `review`; não foi feito commit.

### O que a IA fez

- Leu a story, o código real e o plano antes de editar, e conferiu que não havia contradição entre story, código e arquitetura. Achou uma só divergência de fato: o proxy do Vite usa `changeOrigin: true` (troca o `Host`, mas não o `Origin`), contra o que a story supunha. Corrigi o registro na story; o desenho não mudou porque a comparação usa `APP_ORIGIN`.
- Criou `app/errors.py` (contrato `{status, code, message}`, três handlers separados), `app/csrf.py` (middleware ASGI puro, sem `BaseHTTPMiddleware`) e `OriginSettings` em `config.py`; integrou tudo em `create_app`.
- Escreveu `test_errors.py` e `test_csrf.py` com rotas sintéticas que só existem nos testes, ajustou as suítes existentes (`test_spa.py`, `test_infra_check.py`, `test_openapi.py`, `test_config.py`, `conftest.py`) para o contrato novo, sem remover garantias, e atualizou `verify.sh`, `vite.config.ts` (porta fixa) e o README.
- Em um comando de shell, incluiu um `git diff` por descuido; a permissão foi negada e ele refez sem git. Outro comando foi bloqueado por mencionar um `.env*`; nenhum arquivo `.env*` foi lido.
- O daemon do Docker estava parado; a IA abriu o Docker Desktop para rodar o `verify.sh`.
- Rodou o `verify.sh` completo (exit 0, 399 testes) e a verificação manual pelo proxy do Vite com `curl`.

### O que eu decidi

- P1 a P8 e D1 a D6, incluindo o middleware ASGI puro, `APP_ORIGIN` obrigatória (falha ao subir), 415 para conteúdo que não é JSON, `details` do 422 só com `loc` e `type`, e a porta fixa do Vite. Editei o `backend/.env.example` eu mesmo (D6).

### Alternativas descartadas

- As listadas na tabela de decisões da story (por exemplo `BaseHTTPMiddleware`, dependência global, `RENDER_EXTERNAL_URL`, aceitar `+json`, expor `detail`, liberar escrita sem `Origin`).

### Limitações e observações

- O Render passa a exigir `APP_ORIGIN` no painel antes do próximo deploy; a IA não acessou o Render nem fez deploy.
- Não rodei `fetch` no navegador nem `docker run` da imagem; só `docker build` pelo `verify.sh`.
- O `StarletteDeprecationWarning` do `httpx` continua aparecendo no `pytest`; fora do escopo.

### Code review e correções

- Usei o Claude Code com Opus para o code review (`bmad-code-review`, quatro revisores independentes em paralelo), sem git: a revisão foi feita sobre o estado atual dos arquivos. A IA confirmou cada achado no código e com sondas executadas fora do repositório.
- Os dois achados principais foram:
  - **Bypass latente por `root_path`:** a proteção olhava o caminho cru. Com `--root-path`, uma escrita estrangeira chegaria ao handler. Hoje nada configura `root_path`.
  - **Escrita válida em rota `/api` inexistente com a SPA montada:** recebe 405, não 404. O teste aceitava os dois status, e a evidência pelo proxy tinha sido feita sem SPA.
- Decidi aceitar o 405 sem mexer no fallback da 1.3. Conferi eu mesmo o diff de um arquivo de infraestrutura que não pertence à 2.1 e o deixei fora desta story e do commit.
- A IA corrigiu os achados 3 a 13:
  - a proteção passou a usar a mesma derivação de caminho do roteador;
  - escreveu testes de `root_path` e provou que 8 deles falham com a lógica antiga;
  - fixou o 405 real com SPA nos testes;
  - fortaleceu os testes estruturais, de métodos seguros, de `APP_ORIGIN` e do catálogo literal de mensagens;
  - corrigiu o README e limpou frases antigas da story.
- A IA executou a prova pelo proxy do Vite com uma rota de harness fora do repositório: escrita aceita chegando ao handler, recusas 403/415 sem executar o handler e um 500 real com um único registro no log do uvicorn. Na primeira tentativa, o script dela fez cada requisição duas vezes (uma para o status, outra para o corpo); ela percebeu pelo contador e pelo log e refez com uma requisição por caso.
- `verify.sh` completo depois das correções: exit 0, 413 testes. Os achados adiados ficaram em `_bmad-output/implementation-artifacts/deferred-work.md`.

### Ajuste final antes do commit

- Pedi a troca do import de `get_route_path` (`starlette._utils`, módulo privado) por um helper local. A IA escreveu `effective_path` em `app/csrf.py`, só com o `scope` ASGI (`route_path`, `path` e `root_path` removido apenas como prefixo por segmento), e acrescentou 9 testes unitários.
- Testes direcionados de `root_path` e `effective_path`: 18 passed. `verify.sh` completo: exit 0, 422 testes. Sem git, sem deploy.

## Direção visual e de UX do front-end

Discuti e defini a direção visual e de UX fora do Claude Code. Os documentos `DESIGN.md`, `EXPERIENCE.md` e `VITRINE-BLUEPRINT.md` foram preparados fora do Claude Code.

### O que eu decidi

- Escolhi a identidade roxa derivada da marca que já existia no repositório (`frontend/public/favicon.svg`), com a obra como protagonista.
- Usei Disney+, Mercado Livre, Catawiki e Superbid como referências de produto, cada uma para um problema específico de UX (composição e descoberta; busca e escala; clareza da decisão de lance; muitos lotes simultâneos), sem intenção de copiar a identidade visual delas.
- Considerei feedback externo para rejeitar uma direção que parecia demais um produto SaaS ou uma plataforma de cursos.
- Decidi a regra do destaque da Vitrine (lote ao vivo com `ends_at` mais próximo; sem ao vivo, o próximo agendado; sem lote elegível, estado vazio) e o rótulo "Próximos lotes" para a categoria de lotes agendados.

### O que a IA fez

- Nesta sessão, o Claude Code apenas inspecionou o pacote, verificou a compatibilidade com a arquitetura, organizou os arquivos em `_bmad-output/planning-artifacts/`, registrou no `VITRINE-BLUEPRINT.md` as decisões acima e integrou as referências ao `CLAUDE.md`. Não implementou front-end.

## Story 2.2 — Login, papéis e política de acesso

Usei o Claude Code com Opus para especificar (spec aprovada por mim, com as decisões P1 a P16 e OQ-1 a OQ-3 já fechadas) e com Sonnet para implementar, em sessão separada da que especificou. O processo de front-end seguiu o `FRONTEND-WORKFLOW.md`.

### O que a IA fez

- Implementou o back-end a partir da spec: tabela `users` e migration `0002`, Argon2id, JWT HS256 em cookie HttpOnly, login, logout e `/api/me`, as cinco políticas de acesso com os helpers de registro de rota, o meta-teste que reprova rota sem política, o seed idempotente e o passo do seed no `start.sh`. Removeu o cookie técnico da 1.4 e manteve o WebSocket técnico como rota pública.
- Implementou a tela de login e o cabeçalho da conta, sem dependência nova, seguindo `frontend-login.md`, `DESIGN.md` e `EXPERIENCE.md`.
- Escreveu os testes do plano de testes, os de banco em PostgreSQL real. Os testes de seed pegaram um erro dela: o `rowcount` do `INSERT` multilinha do psycopg vinha `-1`; ela passou a contar as linhas do `RETURNING`.
- Rodou o servidor real com a SPA e a imagem Docker contra o banco `_test` para conferir login, cookie, `/api/me`, logout e a ordem migrations, seed, uvicorn, além do `verify.sh`.
- Percebeu e relatou três pontos em que a spec e a realidade divergiam (abaixo), em vez de afrouxar teste.

### O que eu decidi

- Todas as decisões de produto e de segurança: `JWT_SECRET` obrigatório, cookie derivado só da `APP_ORIGIN` (sem `APP_ENV`), `http` remoto impedindo o boot, `OPTIONAL` tratando sessão inválida como anônima, política como metadata nossa (descartei `iter_route_contexts`, que não é documentada), e as contas e a senha pública de demonstração. Configurei o `JWT_SECRET` local e a linha do `backend/.env.example` eu mesmo; o agente não leu `.env*`.

### Alternativas descartadas

- As listadas na tabela de decisões da story (por exemplo `APP_ENV`, `/api/session`, `ApiError`, `pwdlib`, token em `localStorage`, `react-router`).

### Limitações e observações

- O teste de `hide_parameters` da spec esperava um e-mail marcador fora da mensagem do erro de UNIQUE. O PostgreSQL escreve a chave duplicada no `DETAIL`, então o teste usa o marcador num parâmetro que não é a chave violada. Numa colisão de e-mail no seed, o e-mail (público) aparece no log.
- A spec previa o `test_errors.py` inalterado, mas ele fixa o catálogo de mensagens por igualdade exata; acrescentei só a entrada `invalid_credentials`.
- O Ruff já reprovava a ordem dos imports em `migrations/env.py` no estado anterior; corrigi só essa ordem.
- Não há teste automatizado do front-end (Q10 segue aberta). O teste manual no navegador e o `bmad-code-review` são meus e ainda não foram feitos; a story fica em `review`.
- `./verify.sh` completo: exit 0, 568 testes do back-end, saída registrada na story.

### Ajuste visual depois do meu teste manual

- Testei a story no navegador. O comportamento passou (login inválido, as três contas demo, papel em português, refresh, logout, `/health`), mas vi que o layout em desktop estava desproporcional: formulário deslocado para a esquerda, vazio excessivo e header, conteúdo e rodapé fora do mesmo grid. Esse achado do teste manual motivou o ajuste; o agente não tinha como vê-lo, porque só verificou lint, tipos, build e chamadas HTTP.
- A IA diagnosticou a causa (header em largura total, conteúdo e rodapé num container de 72rem, formulário alinhado à esquerda dele) e corrigiu só o CSS e a estrutura dos três blocos, com um container único e a coluna do login centralizada. Nada de back-end, de biblioteca ou de identidade visual nova mudou. `./verify.sh` completo: exit 0.
- Descartei card com sombra em volta do formulário, por contrariar o DESIGN.md. A conferência visual do ajuste continua sendo minha, no navegador.

### Code review e correções

- Rodei o `bmad-code-review` com Opus, em sessão separada da implementação. Ele revisou o estado atual dos arquivos contra a story, a spec, as ADs, o DESIGN.md e o EXPERIENCE.md, e reproduziu os achados com scripts descartáveis em vez de só afirmá-los. Não encontrou BLOCKER nem HIGH.
- O achado mais relevante (MEDIUM): o meta-teste de política confiava só na metadata da função, e um endpoint `AUCTIONEER` reaproveitado por `@app.get` virava uma rota aberta que o teste mostrava como protegida. Aprovei a estratégia de correção: manter a metadata e os helpers (P9) e fazer o verificador conferir também a dependência pública registrada na rota. A IA corrigiu e acrescentou as regressões.
- Os outros (LOW), também aprovados por mim: comentário de `hide_parameters` que prometia demais (o `DETAIL` do PostgreSQL pode conter valores), dois testes que não provavam o que diziam (hash de referência e seed independente de `app.main`), `aria-invalid` marcando os campos em erro de servidor e um parágrafo da story que citava `clamp`. O limite do `websocket_route` com política não pública ficou registrado para a 4.1, sem implementação agora.
- `./verify.sh` completo depois das correções: exit 0, 574 testes do back-end. A story continua em `review` até o re-review.

### Re-review final e sincronização da spec

- O re-review (Opus, sessão separada) validou o código das correções do M1 e dos LOW e rodou o `./verify.sh` por conta própria (exit 0). Encontrou uma divergência só documental (MEDIUM): `backend-contract.md` e `test-plan.md` ainda descreviam o verificador de política só pela metadata, prometiam que `hide_parameters` escondia o e-mail do log de uma colisão de UNIQUE e descreviam o teste com o marcador no e-mail. Como a spec é o contrato canônico, não aprovei a story com ela desatualizada.
- A IA (Sonnet) sincronizou a spec com o que já estava no código e na story: `route.dependencies` no verificador, o problema "política X sem a dependência", os 6 testes de regressão do M1, o limite real do `hide_parameters` (o `DETAIL` do PostgreSQL pode conter valores), o marcador no `password_hash` e a checagem de `'app.main' not in sys.modules` no seed. Nenhum código, teste ou decisão mudou; não rodei testes nesta etapa. A story e o `sprint-status.yaml` continuam em `review`.

## Story 2.3 — Busca de obras no Art Institute of Chicago

Usei o Claude Code com Opus para validar o contrato real da AIC e escrever a spec (aprovada por mim, com P1 a P11, P7.1, P7.2, P8.1 e C1 a C4 fechadas) e com Sonnet para implementar, em sessão separada. O processo de front-end seguiu o `FRONTEND-WORKFLOW.md`.

### O que a IA fez

- Na fase da spec, fez poucas chamadas reais e de leitura à AIC e trouxe três fatos que a story não previa: o Cloudflare devolveu 403 sem a identificação recomendada pela documentação, o parâmetro `q` não filtra (qualquer termo devolvia as 62119 obras de domínio público) e o firewall recusa alguns termos. Daí saíram a identificação nos cabeçalhos, a consulta `bool` montada no servidor e o 503 para o 403 externo.
- Implementou o cliente `httpx` síncrono (`app/artic.py`), o serviço e as duas rotas `AUCTIONEER` de dados (`app/catalog.py`; a rota pública de imagem veio depois, na correção abaixo), o código `catalog_unavailable`, as fixtures, os testes com `httpx.MockTransport`, a guarda que impede o `pytest` de resolver qualquer host fora de loopback, o smoke `backend/scripts/smoke_artic.py` e a tela de busca e detalhe (sem dependência nova).
- Conferiu as rotas com a AIC real, dentro do processo e com o banco `_test`: busca, lista vazia, detalhe, 404 e o 503 do termo recusado pelo firewall.

### O que eu decidi

- Todas as decisões de produto e de contrato (P1 a P11 e os conflitos C1 a C4): rotas em `/api/catalog`, 404 indistinguível para obra inexistente, fora do domínio público ou sem imagem, sem paginação, sem cache, a identificação com a URL pública do Render e sem e-mail pessoal, sem React Router e sem botão "Criar lote". O agente não leu `.env*`.

### Alternativas descartadas

- As listadas em cada item da story (por exemplo `urllib.request`, códigos 502/504, nova tentativa automática, cache com TTL, `pytest -m smoke`, montar a URL IIIF no front e usar `config.iiif_url`).

### Limitações e observações

- A guarda de rede reprova o teste que tentar resolver um host externo, mesmo que o código sob teste transforme a falha em 503. O libpq resolve em C e não passa por ela, e o `TestClient` não abre socket.
- Ajustei a fixture do detalhe 27992 aos valores que a chamada real devolveu (`artist_display` e `date_display`); a primeira versão, escrita à mão, estava diferente.
- O firewall da AIC recusa termos como `<script>`, que chegam à interface como "catálogo indisponível" (documentado no README).
- Não há teste automatizado do front-end (Q10 segue aberta). O meu teste manual no navegador e o `bmad-code-review` ainda não foram feitos; a story fica em `review`.
- Comandos executados (antes da correção das imagens): `./verify.sh` completo, exit 0, 707 testes do back-end; smoke real `uv run python -m scripts.smoke_artic`, exit 0, 6/6 PASS. Saídas na story. Sem git e sem deploy.

### Correção das imagens depois do meu teste manual

- No navegador, busca, detalhe, lista vazia, loading, offline e placeholder funcionaram, mas toda imagem IIIF falhou com HTTP 403 (Cloudflare). O agente não tinha como ver isso: o smoke dele passava porque o servidor envia `User-Agent` e `AIC-User-Agent`, e a tag `<img>` não envia. A suposição da spec e do AD-22 (o navegador carrega o IIIF direto) foi refutada pelo meu teste, não por teste automatizado.
- Eu decidi a correção: um proxy same-origin controlado, `GET /api/catalog/images/{image_id}`, público, que só aceita `image_id` validado, usa host/caminho/tamanho/formato fixos, não segue redirecionamento e não armazena nem faz cache dos bytes. Também decidi registrar a mudança como revisão da consequência técnica do AD-22, mantendo a motivação original, e não avançar para o code review antes do meu reteste.
- A IA implementou `ArticClient.get_image` e a rota, trocou `image_url` pelo caminho same-origin, escreveu os testes (cliente, rota pública, falhas, id inválido sem chamada ao upstream, política) e atualizou a spec, o AD-22, o README e a story. Conferiu a rota contra o IIIF real, em processo.
- Descartei: manter o hotlink, baixar e guardar as imagens, proxy genérico, cache no servidor.
- Limitação aberta, que é minha decisão: sem cache, uma busca com 20 resultados chama a AIC até 20 vezes (limite de 60 por minuto por IP); a rota também é pública. Registrado na story e no README.
- Comandos executados: `./verify.sh` completo, exit 0, 763 testes do back-end; smoke real `uv run python -m scripts.smoke_artic`, exit 0, 6/6 PASS (item 4 com `get_image`: 197727 bytes JPEG). Sem git e sem deploy. O reteste manual e o `bmad-code-review` ainda não foram feitos.

### Reteste manual e code review

- Refiz o teste manual depois do proxy. Registro só o que observei. Antes da correção: estado inicial do catálogo, loading em rede limitada, busca válida, 20 resultados, nenhum resultado, detalhe da obra e erro/offline de comunicação funcionavam, mas toda imagem `default.jpg` do IIIF dava 403 no navegador e o placeholder aparecia em todas as obras. Depois do proxy: as miniaturas e o detalhe carregaram imagens reais; a aba Rede mostrou `/api/catalog/images/{image_id}` com várias respostas 200 `image/jpeg`; pelo menos uma imagem deu 503 e o placeholder local apareceu corretamente, com os metadados disponíveis; `BIDDER` não teve acesso ao catálogo; atualizar a página manteve a sessão e voltou o catálogo ao estado inicial; no mobile, o fluxo lista → detalhe → "Voltar" funcionou.
- Não registro como observados a navegação por teclado, a largura exata de 320 px nem cada um dos dez estados do roteiro individualmente: faziam parte do roteiro, mas não tenho evidência explícita deles.
- Rodei o `bmad-code-review` com Opus, em sessão separada: 0 BLOCKER, 0 HIGH, 1 MEDIUM documental (M1), três LOW (L1 a L3) e um risco (D1). O reviewer rodou o `./verify.sh` por conta própria (exit 0, 763 passed).
- Aprovei: M1 (a story e o `implementation-map.md` ainda descreviam o IIIF direto do navegador, duas rotas `AUCTIONEER` e o proxy como fora de escopo; mandei reescrever o contrato principal, não só acrescentar nota), L2 (o aviso oculto "Imagem indisponível" da miniatura vinha antes do título no nome acessível do botão), L3 (registrar este reteste), e sincronizar o resumo do AD-22 no `CLAUDE.md` e a referência no `epics.md`.
- Decidi não corrigir L1 (a guarda de rede não trata `HTTPS_PROXY`/`ALL_PROXY`): risco teórico, sem bug atual; foi para o `deferred-work.md`. E decidi manter o D1: rota de imagem pública, sem cache, 843 px, sem miniatura alternativa. A limitação (uma busca de 20 resultados pode disparar várias chamadas de mídia; não sei se a cota do IIIF é compartilhada com a da API) também está no `deferred-work.md`.
- A IA reescreveu os trechos da story e do mapa de implementação, removeu o texto oculto da miniatura (a falha da miniatura fica só visual, com `alt=""`) e sincronizou os resumos. Não mexeu no proxy.
- Comandos executados: `npm run lint`, `npm run typecheck`, `npm run build` e `./verify.sh` completo, exit 0, 763 testes do back-end. Sem smoke novo, sem git e sem deploy. A story e o `sprint-status.yaml` continuam em `review`, esperando o re-review.

### Re-review final e aprovação

- O Opus fez o re-review final da Story 2.3, em sessão separada da implementação. Validou M1, L2 e L3, e confirmou que o `CLAUDE.md` e o `epics.md` estavam sincronizados com o AD-22 revisado. Não havia BLOCKER, HIGH nem MEDIUM pendente.
- O L1 (guarda de rede e `HTTPS_PROXY`/`ALL_PROXY`) permaneceu deferred e o D1 (chamadas repetidas de mídia à AIC, sem cache) permaneceu como limitação aceita, ambos no `deferred-work.md`.
- Aprovei a Story 2.3 e ela foi marcada `done`. Não houve nova execução de verify: vale o último resultado registrado, `./verify.sh` exit 0, 763 passed, 1 warning.

## Story 2.4 — Criação de lotes pelo leiloeiro e lote demo semeado

Usei o Claude Code com Opus para escrever a spec (P1 a P9 decididas por mim, mais a aprovação final com a Q1 e os ajustes A2 a A4) e com Sonnet para implementar, em sessão separada, pelo `bmad-build`. O processo de front-end seguiu o `FRONTEND-WORKFLOW.md`. Antes do build, dei uma orientação explícita: o enunciado do desafio avisa que as regras de lance e os requisitos de back-end são o que mais pesa, então esta story, que ainda não tem lance, devia tratar o schema, o dinheiro, o tempo e as transações como base das regras futuras.

### O que a IA fez

- Escreveu a migration `0003` (`lots`, FK `RESTRICT`, CHECKs de dinheiro, tempo, `external_id` e `image_id`), o módulo `app/lots.py` (modelo, regra pura que recebe `now`, `resolve_artwork_for_lot` para a AIC, `create_lot` sem rede, as duas rotas), o `artwork_not_eligible`, o seed do lote demo com trava consultiva e fixture offline, e o front (navegação, formulário, revisão, confirmação, "Meus lotes", `money.ts` e seu teste com `node --test`).
- Escreveu 206 testes novos no back-end (migration e tipos reais pelo `information_schema`, regra pura, criação, política, atomicidade, "Meus lotes", seed e concorrência do seed) e 14 no front.
- Provou que dois testes importantes não eram vazios, por mutação temporária (removeu o `rollback()` antes da AIC e a trava do seed, viu os testes falharem, restaurou e conferiu): o de `pg_stat_activity` e os de concorrência determinística.
- Conferiu a pilha real fora do `pytest`: o seed dentro da imagem Docker (a fixture está lá) e as rotas com uvicorn e login de verdade. Fez uma chamada real `POST /api/lots` à AIC, uma só, fora do `verify`.

### O que eu decidi

- Todas as decisões de produto e de contrato: o servidor reconsulta a AIC e é a única fonte do snapshot (P1), sem coluna de estado (P3), "começar agora" pela hora do banco e sem duração mínima (P4), dinheiro em centavos com a mesma faixa técnica na API, no serviço, no front e no banco (P5 e A4), um só código para obra inelegível (P6), sem `Idempotency-Key` (P7), seed offline e idempotente com 72 h, R$ 100,00 e R$ 10,00 (P8), `GET /api/lots/mine` sem limite (P9 e A2), e a separação entre resolver a obra na AIC e criar o lote, que o seed nunca cruza (A3). O agente não leu `.env*`.

### Alternativas descartadas

- As listadas em cada decisão da story: front enviando metadados da obra, `status` persistido, teto comercial de R$ 100 milhões, `Idempotency-Key`, limite de 100 em "Meus lotes", `TRUNCATE users CASCADE`, React Router e Vitest com Testing Library.

### Limitações e observações

- Não houve navegador nesta sessão: o formulário, a revisão, a confirmação, "Meus lotes", o foco entre etapas, 320 px e o teclado não foram vistos. Componentes não têm teste automatizado; só `money.ts` tem. O roteiro manual (`test-plan.md` §9) e o `bmad-code-review` são meus e ainda não foram feitos.
- Os testes de corrida livre do seed passam mesmo sem a trava; quem prova a trava são os dois deterministas. Registrado na story.
- Ajustei um detalhe da spec: o regex do horário aceita o offset como opcional, para "sem fuso" sair como `timezone_aware` e não como `datetime_format`, que é o que o plano de testes pedia. O comportamento é o do plano.
- Comandos executados: `./verify.sh` completo, exit 0, 969 testes do back-end (763 antes da story), `npm test` com 14 testes, ESLint, `tsc --noEmit` dos dois projetos, build do Vite e `docker build`. Sem git e sem deploy. A story e o `sprint-status.yaml` ficam em `review`.

### Bug de runtime no primeiro teste manual da 2.4 (tela branca)

- Meu primeiro teste manual abriu `http://localhost:5173` e a tela ficou toda branca. O console apontou `lotTime.ts:21` com `Uncaught TypeError: Invalid option : option`. Lint, `tsc --noEmit`, build do Vite e o `verify` completo tinham passado: nenhum deles executa o módulo, e a IA não tinha como ver isso sem navegador.
- Causa: a IA escreveu um `Intl.DateTimeFormat` com `dateStyle`, `timeStyle` e `timeZoneName` juntos, combinação que o `Intl` recusa. Como a construção ficava no nível do módulo, o erro estourava na importação, antes do React renderizar. Era a combinação que a própria spec descrevia, copiada sem ser executada.
- Eu pedi a correção mínima antes de continuar o roteiro manual, sem mexer na regra temporal do back-end, em P4 nem no fuso de persistência. A IA reproduziu o erro no Node, trocou as opções por campos explícitos (dia, mês abreviado, ano, hora, minuto e `timeZoneName`), mantendo o fuso e o visual, e escreveu `lotTime.test.ts` (`node:test`, sem dependência nova). Conferiu por mutação temporária que o teste pega o bug (com o código antigo, a execução falha com o mesmo `TypeError`) e restaurou a correção.
- Ao escrever o teste, a IA viu que o `Date` do V8 faz rollover de `2026-02-30T10:00` em vez de recusar; o `datetime-local` não emite essa data, então registrou como observação e não alterou a função.
- Comandos executados: `npm test` (22 testes, 22 passaram), `npm run lint`, `npm run typecheck`, `npm run build` e `./verify.sh` completo. Sem git e sem deploy. A story e o `sprint-status.yaml` continuam em `review`; o roteiro manual recomeça do passo 1.

### Ajustes depois do teste manual da 2.4 (25/10/2026)

- Observei no navegador, e registro só isso: a API local deu 500 ao criar lote porque meu banco de desenvolvimento estava na revisão `0002` e o `head` era `0003`; era ambiente desatualizado, não falha da migration, e depois de aplicar o schema o fluxo funcionou. Vi as validações de dinheiro, as de início e término no passado, a revisão, a criação real até "Lote criado", o celular a 375 px, o `BIDDER` sem controles do leiloeiro e o anônimo no login. Ainda não observei o HTTP 201 na aba Rede, o payload exato, 320 px, o teclado nem o refresh de "Meus lotes".
- Pedi à IA que investigasse uma captura em que a revisão mostrava um término de 23/10 num teste feito em 25/10. Resultado real: o bug existia. O "Revisar lote" já reexecutava a checagem com o valor atual, mas `checkDraft` nunca comparava com "agora", porque a spec dizia para o front não usar o relógio do navegador; a mensagem do formulário veio do servidor, depois da revisão. A IA provou isso com uma sonda antes de corrigir.
- Decidi que o front valide de forma preventiva, com o relógio do navegador (`now` injetado), mantendo o servidor como autoridade final; é uma revisão consciente da frase da spec. A IA implementou, escreveu `lotDraft.test.ts` com `now` fixo e conferiu por mutação temporária que os testes falham sem a comparação (8 falhas), e que passam restaurado. Também precisou acrescentar a extensão `.ts` aos imports de `lotDraft.ts` para ele rodar no Node.
- Pedi melhorias de UX sem biblioteca: uma confirmação explícita de data e hora (botão "Confirmar data e hora"; removida depois, veja a próxima seção) e, no dinheiro, "Digite o valor em reais.", exemplos e "Valor reconhecido". Não mudei layout, API, `MAX_CENTS` nem back-end.
- Limitações: o roteiro manual continua meu; a tela de confirmação, o foco depois de confirmar e o botão no celular só valem depois do meu reteste. Comandos executados: `npm test` (37 testes, todos passaram), lint, typecheck, build e `./verify.sh` completo (exit 0, 969 testes do back-end); detalhes na story. Sem git, sem deploy e sem smoke externo. A story e o `sprint-status.yaml` continuam em `review`.

### Último ajuste de UX da 2.4 (25/10/2026)

- Observei no reteste, e registro só isso: o `POST /api/lots` voltou HTTP 201 na aba Rede; a resposta mostrou valores em centavos coerentes com a interface; a validação preventiva passou a impedir data passada na revisão; o "Valor reconhecido" funcionou; a criação real continuou funcionando; o celular a cerca de 375 px seguiu utilizável. Não conferi o payload exato na aba Payload, nem 320 px, nem o teclado.
- Decidi remover o botão "Confirmar data e hora" que eu mesmo tinha pedido: era para contornar o desconforto do seletor nativo do Edge, e sem substituir o componente inteiro não dá para pôr um botão dentro dele; uma etapa artificial de confirmação não valia manter. "Revisar lote" passa a ser a confirmação natural. A IA removeu o botão, o estado de "confirmado" e a regra de exigi-lo, e preservou os testes do bug da data passada (refez a mutação: 9 falhas sem a comparação com `now`, 13 passando restaurado).
- Decidi que `655.3` seja recusado com uma dica, não reinterpretado: "Use vírgula para os centavos. Ex.: 655,30." A IA acrescentou o erro `dot_decimal` e os testes, e simplificou a ajuda dos campos para "Digite o valor em reais. Use vírgula para centavos. Ex.: 5,50 ou 1.250,00."; o "Valor reconhecido" continua confirmando a interpretação.
- Nada mudou no back-end. Comandos executados: ver a story. Sem git, sem deploy e sem smoke externo. A story e o `sprint-status.yaml` continuam em `review`.

### Feedback monetário inválido (25/10/2026)

- O meu reteste manual mostrou que `333.55` fazia sumir o "Valor reconhecido", mas sem nenhum erro específico: parecia só "sem reconhecimento". Pedi feedback vermelho no mesmo lugar do verde.
- A IA ajustou o UX: um único espaço de feedback, com "✓ Valor reconhecido" quando válido e "✕" com a mensagem quando inválido, e a dica da vírgula só para o formato de ponto decimal, com o exemplo vindo do que foi digitado (`333.55` → `333,55`). O ponto como milhar válido continua aceito. Lógica financeira, API e `MAX_CENTS` não mudaram.
- A IA avisou que `10.999` é milhar válido em pt-BR (R$ 10.999,00) e manteve aceito, recusando `10,999`; fica para eu confirmar. Sem evidência manual nova até o meu reteste final. Comandos executados: ver a story. Sem git, sem deploy e sem back-end. A story e o `sprint-status.yaml` continuam em `review`.

### Primeiro code review da 2.4 (25/10/2026)

- O primeiro `bmad-code-review` (Opus) achou 0 BLOCKER, 0 HIGH e 0 MEDIUM, mais L1 (bug LOW), L2 (acessibilidade LOW), L3 (documentação LOW) e D1 (contradição documental). O reviewer rodou o `./verify.sh` (exit 0, 969 testes do back-end, 39 do front). Os subagentes do review não rodaram por limite 429: o Opus principal fez o review completo e executou o `verify`. Não houve review multiagente.
- Aprovei corrigir L1, L2, L3 e decidi corrigir o D1 antes do fechamento. L1: um horário com offset que não cabe em UTC (`9999-12-31T23:00:00-05:00`) virava 500 depois da chamada à AIC; a IA reproduziu, moveu a invariante para o tipo `ApiDatetime` (recusa com `datetime_format`, 422, sem chamar a AIC) e provou os testes por mutação temporária (8 falhas com o `OverflowError` real sem o validador). Um dos casos de teste que a própria IA escreveu tinha a conta errada (`19:00:01-04:59` cabe em UTC), e ela corrigiu a entrada, não o comportamento. L2: removeu o `aria-live` do feedback monetário e conferiu o render real de `333.33` (vermelho, com a dica da vírgula e `aria-describedby`). L3 e D1: atualizou README, `ARQUITETURA.md` e a spec (a comparação com o relógio do navegador é só preventiva; o PostgreSQL é a autoridade final) e achou na spec mais trechos que os ajustes anteriores tinham deixado velhos, inclusive o `Intl.DateTimeFormat` do bug da tela branca.
- A IA afirmou que não havia nada em `deferred-work.md` para L1, L2, L3 ou D1; o re-review mostrou que a entrada do D1 da 2.4 estava lá (veja abaixo). Comandos executados: ver a story. Sem git, sem deploy e sem smoke externo. A story e o `sprint-status.yaml` continuaram em `review`.

### Re-review final da 2.4 (25/10/2026)

- Pedi um re-review direcionado (Opus, sessão nova), só de L1, L2, L3, D1, das regressões e da sincronização documental, sem refazer o review inteiro, sem git, sem deploy e sem alterar código. Resultado: 0 BLOCKER, 0 HIGH, 0 MEDIUM.
- O que a IA conferiu: L1 no tipo `ApiDatetime` (recusa no Pydantic, antes da AIC, sem `try/except` no handler; os 16 testes novos cobrem a recusa nos dois campos, `fake.requests == []`, zero linhas e os extremos que ainda cabem); L2 sem `aria-live`, com `aria-describedby`, `aria-invalid` e texto além da cor, e o parser no Node (`333.33` com a dica da vírgula; `10.999` válido como R$ 10.999,00 e `10,999` recusado, como eu decidi); L3 no README e no `ARQUITETURA.md`; D1 na spec, com o AD-6 intacto. Rodou o `./verify.sh` de novo: exit 0, 985 testes do back-end, 39 do front, build e `docker build`.
- A IA achou resíduos só de documentação, LOW, e corrigiu no fechamento: a entrada do D1 da 2.4 ainda pendente em `deferred-work.md` (marcada como resolvida, sem apagar; o D1 da 2.3 ficou intacto), a linha de testes de componentes que dizia "só `money.ts`", os itens do "Review Findings" da story ainda abertos, a atribuição errada do caso de teste neste arquivo e a dica antiga do campo de dinheiro na spec.
- Evidência manual: considerei só o que vi (listado na story). Não observei o payload exato do POST, 320 px, o teclado nem o refresh de "Meus lotes".
- Story 2.4 e a linha dela no `sprint-status.yaml` marcadas como `done`. A 2.5 não foi tocada. O commit é meu; sem deploy.


## Story 2.5 — Vitrine pública e página do lote

Usei o Claude Code com Opus para especificar (spec aprovada por mim, com P1 a P9 e D1 a D20 fechadas, e um refinamento da P2 e da D20 antes do código) e com Sonnet para implementar, em sessão separada, pelo `bmad-build`. O processo de front-end seguiu o `FRONTEND-WORKFLOW.md`; a Vitrine também seguiu o `VITRINE-BLUEPRINT.md`.

### O que eu decidi

- P1 a P9 e D1 a D20. Duas decisões mudaram o desenho em relação à primeira versão da spec: a leitura pública passou a ser **um único statement** (CTE `MATERIALIZED` com `clock_timestamp()` e `LEFT OUTER JOIN` a partir dele), porque duas consultas em `READ COMMITTED` têm snapshots diferentes e um lote confirmado entre elas entraria numa resposta de `as_of` anterior à existência dele; e o mapa de política do teste passou a ser indexado por `(path, method, kind)`, porque `GET /api/lots` (público) sobrescreveria `POST /api/lots` (leiloeiro) em silêncio.
- Sem `settlement_status`, sem coluna de estado, sem cache novo de imagem, sem paginação na API e sem React Router. "Encerrado, apurando resultado" é só texto de interface.
- 6 encerrados iniciais com "Mostrar mais encerrados" local (a proposta da story era 12), `id ASC` como desempate nos três grupos, "Sair" leva à vitrine e a linha "Situação atualizada…" derivada do `as_of`.

### O que a IA fez

- Leu a spec, as stories 2.2 a 2.4 e o código real antes de editar. Conferiu no código que `main.py` e `spa.py` não precisavam mudar (o fallback já servia `/lots/<uuid>`) e provou isso em `test_spa.py` em vez de só afirmar.
- Implementou `lot_phase`, os DTOs públicos, a leitura em um statement e as duas rotas; conferiu o SQL que o SQLAlchemy de fato emite (`WITH clock AS MATERIALIZED … LEFT OUTER JOIN lots ON true`) antes de seguir, em vez de presumir que `prefix_with("MATERIALIZED")` funcionava.
- Escreveu os testes em PostgreSQL real: um statement e um `clock_timestamp` por rota, injeção determinística antes do statement (lote confirmado entra, não confirmado não entra), controle negativo de duas consultas, row lock e `UPDATE` não confirmado sem bloqueio, `idle in transaction`, leitura pura, nenhum uso do cliente da AIC, ordem das rotas e os testes do mapa de política.
- Provou por mutação temporária (um `SELECT … FOR UPDATE` no detalhe) que os testes de statement único, de leitura pura e do row lock falham quando deveriam, e restaurou o arquivo.
- Escreveu o front: `route.ts`, navegação própria, vitrine, página do lote, header por papel e login explícito, com testes `node --test` de lógica pura. Fez uma renderização no servidor de `App` e dos componentes da vitrine, num script descartável fora do repositório, para pegar erro de importação e de render inicial (como o `Intl` da 2.4).

### Onde a IA errou ou divergiu da spec

- A spec previa `Vitrine.tsx` e `vitrine.ts`; no macOS e para o `tsc` os dois nomes são o mesmo arquivo. O `tsc` acusou (`TS1149`), e o componente virou `VitrinePage.tsx`.
- O primeiro teste de "um `as_of` por linha" comparava o valor cru com o de uma segunda execução, o que nunca é igual (cada execução avalia o relógio de novo). O erro era do teste; a IA corrigiu a asserção para o que a spec realmente quer provar.
- Um `lotLinkLabel` incluía o lance inicial do lote encerrado, que a linha da tela omite de propósito (pareceria preço final); a IA percebeu ao ler o HTML renderizado e corrigiu com teste.
- Acrescentou `tabIndex={-1}` ao `h1` de `CatalogSearch.tsx`, arquivo que a spec listava como intocado, para o foco no `h1` valer em "Criar lote". Está registrado como divergência na story.
- Um comando de teste foi rodado sem as variáveis de ambiente do banco de teste e o `pytest` encerrou com "Unsafe test database"; a IA passou a usar os mesmos valores locais fictícios do `verify.sh`. Nenhum `.env*` foi lido.

### Limitações e observações

- **Não houve navegador nesta sessão.** Clique, `pushState`, Back/Forward, foco, rails e botões, 320 px, 375 px e desktop largo, teclado e imagem quebrada não foram vistos. Componentes seguem sem teste automatizado. O roteiro manual (`test-plan.md` §9) e o `bmad-code-review` são meus e ainda não foram feitos; a story fica em `review`.
- Comandos executados: `./verify.sh` completo, exit 0, 1058 testes do back-end (985 antes da story) e 84 do front (39 antes), ESLint, `tsc --noEmit`, build do Vite e `docker build`. Sem git, sem deploy e sem smoke externo.

### Testes de navegador e densidade da vitrine (25/10/2026)

**Evidência manual minha (observada por mim no navegador):** a vitrine do `BIDDER` e o detalhe do `BIDDER` renderizam; o `BIDDER` não vê controles do leiloeiro; a vitrine anônima mostra "Entrar" e o anônimo não é forçado ao login; o `AUCTIONEER` vê Vitrine, Criar lote e Meus lotes; a criação da 2.4 e "Meus lotes" continuam acessíveis; os grupos Ao vivo, Próximos e Encerrados renderizam; o detalhe mostra ficha, valores e horários e não tem "Dar lance"; a linha "Situação atualizada" aparece. Vi também que o layout desktop tinha espaço morto excessivo nas seções de coleção. Não observei manualmente 320 px, 375 px, teclado, Back/Forward, deep-link com recarga, `returnTo`, placeholder nem "Mostrar mais" com mais de 6.

**Decisões minhas:** o teste manual deu justificativa real para testes de navegador, então pedi o Playwright, pequeno e separado, sem screenshot como assert; e pedi um ajuste moderado de densidade, só nas coleções, usando o RockHub apenas como referência de densidade (não de identidade).

**O que a IA fez (Sonnet):**
- Adicionou `@playwright/test` (versão exata, só em `devDependencies`) e baixou o Chromium pelo comando documentado. Escreveu 66 testes em 5 arquivos: 61 rodam sempre, com a API simulada por interceptação de rede, e 5 (pilha real) só com `E2E_REAL_BASE_URL`.
- Rodou o spec da pilha real uma vez, contra o FastAPI servindo o build com o banco de teste e o seed offline (não o de desenvolvimento), e parou o servidor.
- Provou por mutação de CSS (restaurada) que os testes de densidade falham com o layout antigo: o rail com 3 itens ocupava 72% da faixa, com 2 itens 47% e o próximo lote sozinho 24%.
- Ajustou a densidade: rails com 1, 2 ou 3 itens ocupam a faixa (cartão horizontal para o item único, divisão para dois, três colunas para três), 4 ou mais voltam a rolar com parte do próximo visível; gap entre seções de 2,5 para 2 rem. Hero, detalhe e header não mudaram. Tirou screenshots só para conferir o resultado (artefato de depuração, fora do repositório e sem assert).

**Evidência automatizada Playwright (não é evidência manual):** deep-link com recarga, vitrine → lote → Back → Forward, login com `returnTo` e logout, `returnTo` externo ignorado, header por papel, `aria-current`, "Mostrar mais" com 14 encerrados sem novo `GET /api/lots`, imagem quebrada com placeholder, Tab e foco visível, foco no `h1`, foco devolvido no Back, e layout em 1440×900, 375×812 e 320×812. Isso mostra o comportamento no Chromium com a API simulada; **não substitui** o meu olhar sobre o visual nas três larguras.

**Onde a IA errou ou escorregou:**
- Dois testes falharam na primeira rodada por seletor ambíguo do próprio teste (um `h1` oculto de "Criar lote" e dois links de nome parecido), não por defeito do app; foram corrigidos no teste.
- Registrou a rota de falha antes da simulação; o Playwright consulta primeiro a rota mais recente, então a ordem foi invertida.
- Num comando acabou incluindo um `git diff --stat` (somente leitura, saída descartada), contra a regra do projeto. Não se repetiu.

**Limitações:** só Chromium (nada de Firefox/WebKit); a API é simulada, então o contrato real está nos testes do `pytest` e no spec opcional da pilha real; o visual de verdade (imagens reais, tipografia, respiro) continua dependendo do meu olhar. Comandos executados: `VERIFY_E2E=1 ./verify.sh` completo, exit 0, 1058 testes do back-end, 84 do front (`node --test`), 61 testes de navegador passando e 5 ignorados, ESLint, `tsc` (inclui o `tsconfig` do `e2e`), build e `docker build`. Sem git, sem deploy e sem smoke externo.

### Rebranding ÁTRIO (25/10/2026)

**Decisão minha:** o produto passa a se chamar **ÁTRIO — Leilões de Arte**, com a identidade da referência ÁTRIO que escolhi; a AURA é só inspiração de densidade, cards, hierarquia e acabamento. Pedi marca e direção visual, sem antecipar funcionalidade (lance, contagem, favoritos, busca, carteira) e sem refatoração técnica: repositório, banco, módulos e `/api/*` ficam.

**O que a IA fez (Sonnet):**
- Procurou as ocorrências reais de "Casa de Leilões" antes de trocar (nada de search/replace cego): header, título da aba, `index.html`, "não encontrado", o título do OpenAPI e um teste. Preservou o texto histórico (enunciado, cronograma, specs e stories antigas, descrição do pacote Python).
- Criou `brand.ts` (nome, descritor, `documentTitle`), `AtrioMark.tsx` (SVG inline decorativo) e trocou `favicon.svg`, que era o ícone padrão do template do Vite. Fez uma interpretação vetorial inicial (arco com abertura interna), sem raster, sem imagem remota, sem dependência; o refinamento fino fica para a Story 6.2.
- Ajustou o header: nome acessível "ÁTRIO — ir para a vitrine" (depois corrigido, abaixo), SVG fora da árvore de acessibilidade, descritor só ≥ 64 rem.
- Escreveu `brand.test.ts` (3) e `e2e/brand.spec.ts` (17) e atualizou só o seletor da marca em `keyboard.spec.ts` e o título esperado em `test_openapi.py`.
- Atualizou README, CLAUDE.md, ARQUITETURA (adendo sob a AD-15, sem mudar AD), DESIGN.md §2, spec e story da 2.5 e o `deferred-work.md`, sem reescrever o passado.

**Evidência:** a evidência manual anterior é do visual antigo e não foi reclassificada. Esta rodada ainda não foi vista por mim no navegador; o que existe é evidência automatizada do Playwright e screenshots do header gerados e olhados pela IA (só depuração, fora do repositório).

**Onde a IA escorregou ou divergiu:** nada falhou nos testes novos na primeira rodada. Houve uma divergência de escolha: o nome acessível do link não contém o descritor "Leilões de Arte" visível no desktop (WCAG 2.5.3, rótulo no nome); segui o formato que pedi ("ÁTRIO — ir para a vitrine") e deixei o risco registrado.

**Limitações:** logotipo é uma primeira interpretação; wordmark em fonte do sistema; favicon só em SVG; o Playwright é Chromium com API simulada. Comandos executados: `VERIFY_E2E=1 ./verify.sh` completo, exit 0, 1058 testes do back-end, 87 do front (`node --test`), 78 testes de navegador passando e 5 ignorados (pilha real, só com `E2E_REAL_BASE_URL`), ESLint, `tsc`, build e `docker build`. Sem git, sem deploy e sem smoke externo.

### Correção de fidelidade da logo e correções do primeiro review (25/10/2026)

**Decisões minhas:** (1) a primeira logo da IA **não foi aprovada**: parecia um arco semicircular simétrico (∩), e a referência tem topo pontudo, duas faces e abertura interna assimétrica; (2) o primeiro code review rodou **antes** do branding (registrou `npm test` 84 e Playwright 61, contra 87 e 78 já com o ÁTRIO) e não valida a marca, então pedi correções dos achados M1 e L1 a L4 e um re-review que examine também o delta ÁTRIO; (3) M1 pela opção (a): documentar o Playwright como opt-in, sem mexer no AD-27.

**O que a IA fez (Sonnet):**
- Ampliou a referência e refez o símbolo: silhueta alta e fina de topo pontudo, duas faces (`#a77bf6` e `#6c35e6`) e vazio assimétrico, só com `path`; o favicon repete os mesmos caminhos. Renderizou o símbolo ampliado, achou duas falhas (um "quebra" na perna esquerda e um ombro no topo do vazio) e corrigiu as curvas antes de seguir. Deixou a palavra mais leve (peso 300) e o descritor menor.
- Reproduziu o L1 no navegador antes de corrigir (contorno do rail cortado em 6 px no topo e à esquerda) e escreveu os testes antes das correções: eles falhavam com o CSS antigo e passam com o novo. Corrigiu o rail com padding e margem negativa, o L3 com áreas de toque em pseudo-elemento (medidas por `elementFromPoint`) e o L2 com um teste positivo de `returnTo` (com controle de que o estado sobrevive ao reload).
- Corrigiu o nome acessível da marca para conter o texto visível ("ÁTRIO — Leilões de Arte — ir para a vitrine") e testou o Label in Name em 1440, 375 e 320.
- Sincronizou ARQUITETURA (Q10 e histórico), CLAUDE.md, spec (D21 e anotações em SPEC, D18, D19, mapa, plano de testes), story, README, DESIGN.md e `deferred-work.md` (registro exato de 429/503), sem reescrever o passado.

**Onde a IA errou ou divergiu:**
- A primeira geometria da logo era genérica e a descrição dela na documentação ("arco com abertura interna mais clara") chegou a soar fiel; só a comparação com a referência ampliada mostrou o erro.
- O primeiro nome acessível omitia o descritor visível (Label in Name); a IA já tinha deixado o risco registrado, mas só corrigiu depois do meu pedido.
- A correção de alvos de toque exigiu subir o espaço entre linhas do header de 0.5 para 0.75rem (celular: +8 px); no desktop o header segue com 61,5 px.

**Limitações:** o símbolo e o wordmark ainda são uma interpretação inicial (fonte do sistema); só Chromium com API simulada; os alvos de toque foram medidos por teste, não com um dedo; o visual de verdade continua dependendo do meu olhar. Comandos executados: `VERIFY_E2E=1 ./verify.sh` completo, exit 0, 1058 testes do back-end, 87 do front (`node --test`), 96 de navegador passando e 5 ignorados (pilha real, só com `E2E_REAL_BASE_URL`; não fazem parte do verify padrão nem do opt-in), ESLint, `tsc`, build e `docker build`. Sem git, sem deploy e sem smoke externo.

### Re-review final e aprovação (25/10/2026)

- Pedi um re-review final (Opus, sessão separada da implementação), sem git, sem deploy e sem corrigir findings, cobrindo M1, L1 a L4, as regressões das correções, **todo o delta ÁTRIO** (que o primeiro review não viu) e a sincronização documental. O back-end de domínio não mudou desde o primeiro review e não foi revisto de novo. Resultado: **0 BLOCKER, 0 HIGH, 0 MEDIUM.**
- A IA rodou o `VERIFY_E2E=1 ./verify.sh` por conta própria: exit 0, Ruff e format ok, 1058 testes do back-end, 87 do front (`node --test`), 96 de navegador passando e 5 ignorados (a pilha real, que só roda com `E2E_REAL_BASE_URL`), ESLint, `tsc` (app, node e e2e), build e `docker build`.
- Para o que os testes não medem diretamente, a IA escreveu uma sonda descartável, fora do repositório (build servido pelo `vite preview` e API simulada). Ela mostrou zero invasões entre áreas de toque em 1440, 375 e 320 px, para os três tipos de sessão; área real de 43 a 51 px; um clique real fora da caixa visual de "← Vitrine" navegando; e 2 px de folga no contorno de foco dos rails nas três larguras, sem rolagem horizontal. É evidência automatizada de depuração, não teste do projeto nem evidência manual minha.
- Confirmou que M1, L1, L2, L3 e L4 foram resolvidos (L4: nenhum 429/503 manual novo na 2.5; o 503 com placeholder é da 2.3), que a interface não mostra mais "Casa de Leilões", que `AtrioMark` e o favicon usam a mesma geometria e que o nome acessível da marca contém o texto visível nas três larguras.
- Ficaram cinco LOWs não corrigidos, listados na story: o título conferido sem nova tentativa em `brand.spec.ts`; o contorno do rail testado só no viewport padrão; nenhuma asserção explícita de não sobreposição dos alvos; "arco" no adendo da AD-15 e no `deferred-work.md`; e um ramo não usado de `documentTitle`.
- Story 2.5 e a linha dela no `sprint-status.yaml` marcadas como `done`; o `epic-2` continua `in-progress`. O Epic 3 não foi iniciado. O commit é meu; sem deploy.

## Story 3.1 — Carteira e depósito simulado

Usei o Claude Code com Opus para criar a story e a spec (P1 a P8 decididas por mim antes da spec, D1 a D16 detalhadas dentro delas, e dois refinamentos meus na revisão final) e com Sonnet para implementar, em sessão separada, pelo `bmad-build`. A IA implementou direto, sem subagente, a partir da spec. O Git foi meu, como sempre.

### O que eu decidi

- P1 a P8: `wallets.user_id` como PK e FK com `ON DELETE RESTRICT`, sem `id` nem timestamps; backfill na migration e garantia genérica no seed (todo usuário sem carteira); `app/money.py` como fonte única do teto e 422 com `code` próprio `balance_limit_exceeded`; depósito sob `SELECT ... FOR UPDATE`; `GET /api/wallet` e `POST /api/wallet/deposit` só para `BIDDER`; saldo inicial zero; `/bidder/wallet` sem React Router; sem `Idempotency-Key`, sem retry automático e com uma única releitura em erro ambíguo.
- Dois refinamentos da revisão final, que prevalecem sobre a spec: (1) o log do seed **não afirma** nada antes do commit, então a spec D10 (`seed: %d wallet(s) inserted` dentro de `run_seed`) não foi implementada; (2) o teste de concorrência **não pode depender só de `pg_locks`**: a prova é a sincronização controlada de duas transações reais e o estado final no PostgreSQL, e o `pg_locks` é evidência auxiliar.
- Sem ledger, sem histórico de movimentos, sem lógica de lance: `committed_balance_cents` existe e fica `0`.

### O que a IA fez

- Leu a story e a spec inteira, conferiu o código real (a próxima revisão era mesmo a `0004`, `MAX_CENTS` e `Cents` moravam em `lots.py`, `docs/deferred-work.md` não existe e o arquivo real é `_bmad-output/implementation-artifacts/deferred-work.md`) e seguiu a ordem da spec: `app/money.py` e refatoração de `lots.py`; migration `0004` com backfill; módulo `app/wallet.py` (modelo, regra pura, serviço, rotas); seed; testes; front; Playwright; documentação.
- Preservou o contrato do `run_seed` (`(users, created)`) e a propriedade de só logar depois do commit: `ensure_wallets` roda na mesma transação, e a contagem de carteiras simplesmente não é registrada. Um teste confere que `run_seed` não loga nada sobre carteira antes do commit e que o subprocesso do seed não menciona carteira no log.
- Escreveu os testes de concorrência em PostgreSQL real com duas sessões e conexões: a sessão A trava a carteira e segura a trava; B (thread própria) chega ao `SELECT` da carteira (aviso pelo evento `before_cursor_execute`, sem `sleep`); só então A confirma. Cobre dois depósitos que se somam, perto do teto com recusa e com aceite (decididos sobre o saldo que A confirmou), o mesmo pelo HTTP, corrida livre com `Barrier`, controle negativo (padrão ler-somar-gravar perde um depósito) e leitura que não espera a trava. `pg_stat_activity`/`pg_locks` entram só como evidência auxiliar de que B esperou.
- Provou por mutação temporária que os testes pegam o problema: tirar `.with_for_update()` fez falhar os testes C1 a C5 (por exemplo, total final `1500` em vez de `1800`, e `MAX − 6` em vez de `MAX`) e o de serviço do `FOR UPDATE`; tirar só o `populate_existing` fez falhar apenas o teste de serviço que pré-carrega a carteira na `Session` (os de concorrência usam sessões novas e não o detectam). Os dois arquivos foram restaurados e conferidos com `diff`.
- Escreveu o front: `route.ts` (`/bidder/wallet`, `isBidderRoute`, `isRestrictedRoute` como type guard, `safeReturnPath`), `api/wallet.ts` (guarda de resposta e classificação conhecido × ambíguo), `walletFeedback.ts` (textos puros), `WalletPage.tsx`, `BidderOnly` no `App.tsx`, link "Carteira" no header e a seção de CSS; o duplo envio é barrado por uma `ref` síncrona, além do botão `disabled`. Olhou as capturas de tela em 1440 e 375 px (spec temporária descartável, removida).
- Atualizou conscientemente só o que o contrato mudou: `clean_users` (`TRUNCATE wallets, lots, users`, sem `CASCADE`), tabelas do `test_database.py`, paths do OpenAPI, `MESSAGES`, `EXPECTED_POLICIES`, o teste "as seis rotas" do front e a asserção `/carteira/i` de `session.spec.ts` (agora escopada ao `main`, com a asserção positiva do link no header).

### Onde a IA errou ou divergiu da spec

- Divergência deliberada: sem o log `wallet(s) inserted` (D10), por decisão minha acima; o teste do subprocesso passou a afirmar a ausência do log em vez da presença.
- `wait_for_blocked_lock` devolve `bool` em vez de levantar `AssertionError` como previa o plano: o teste decide, e o `pg_locks` fica como auxiliar.
- O primeiro observador de trava contava `FOR UPDATE` a partir do segundo statement, mas só era ligado depois de A travar; os testes esperaram 15 s e falharam. A IA corrigiu a contagem e depois trocou o gatilho para o primeiro `SELECT` de `wallets` de B (com ou sem `FOR UPDATE`), para a mutação falhar pelo **estado final** e não por um passo de sincronização.
- Os casos de CHECK do plano esperavam uma CHECK específica, mas o PostgreSQL informa a primeira que falha e um total negativo também deixa `committed > total`; os testes passaram a aceitar o conjunto de CHECKs ligadas à regra violada.
- Outros tropeços corrigidos na hora: variáveis do banco de teste esquecidas num comando (`Unsafe test database`; nenhum `.env*` foi lido), cópia do baseline com `for` no zsh (sem divisão de palavras), leitura de atributo expirado depois do `rollback` num teste, `RequestInfo` inexistente no `tsconfig` do app, ordem dos botões (header antes do formulário) e `isRestrictedRoute` que precisava ser type guard.
- `fetchWallet` ganhou um `AbortSignal` opcional (a spec previa sem argumentos) para a tela abortar a leitura ao desmontar.
- Acessibilidade do aviso do depósito: erros conhecidos usam `role="alert"`; sucesso e incerteza usam `role="status"` (a spec previa `status` para todos).

### Limitações e observações

- **Teste manual ainda é meu**, como no roteiro do `test-plan.md` §10: depositar como `bidder1`, valores inválidos, duplo clique, servidor parado, `AUCTIONEER` sem "Carteira", 375 e 320 px, teclado. Os testes de navegador usam API simulada e só Chromium; o visual real e o servidor parado de verdade não foram observados por mim nesta sessão. O `bmad-code-review` também é meu e não foi rodado; a story fica em `review`.
- Idempotência continua fora: uma nova tentativa **manual** depois de um timeout pós-commit pode duplicar o depósito (`deferred-work.md` e README).
- Comandos executados (saída real nesta sessão): `./verify.sh` e `VERIFY_E2E=1 ./verify.sh`, ambos com exit 0: Ruff e `ruff format --check` ok (66 arquivos), 1174 testes do back-end (1058 registrados ao fim da 2.5), ESLint, `tsc` (app, node e e2e), 107 testes do front com `node --test`, build do Vite e `docker build`; no opt-in, 123 testes de navegador passando e 5 ignorados (pilha real, só com `E2E_REAL_BASE_URL`). Sem git, sem deploy e sem smoke externo.

### Code review e correções (25/10/2026)

- **Review.** Rodei o `bmad-code-review` com sete camadas (Blind Hunter e Edge Case Hunter em back-end e front-end, Verification Gap, Acceptance Auditor e Project Auditor). Cinco camadas caíram por limite da API e foram retomadas depois. Resultado: nenhum BLOCKER ou HIGH, e um MEDIUM (F-08): a `WalletPage` remonta a cada navegação (`key={where.id}`), e o bloqueio do depósito pendente vivia na instância. Outro clique em "Carteira" ou Back/Forward durante o `POST` trazia o botão ativo de novo e permitia um segundo depósito. Os demais achados eram LOW (F-01 a F-07, F-09 a F-13).
- **O que eu decidi.** Corrigir F-08 com o depósito em andamento **fora da página e escopado por conta**, nunca uma promessa global sem dono. Corrigir também F-01 a F-03, F-05 a F-07 e F-09 a F-13. Ficou de fora F-04 (expansão opcional de cobertura e2e).
- **O que a IA fez.**
  - Criou `src/walletDeposit.ts`: um registro de depósito por conta (o e-mail da sessão), com o envio e a releitura única do erro ambíguo. A página, ao montar com um depósito da mesma conta pendente, nasce com "Depositando…" e o campo travado e mostra o resultado daquele `POST`. A conta B nunca herda o bloqueio nem o resultado da conta A. Uma leitura que começou antes de um saldo vindo do depósito não o sobrescreve.
  - **F-01:** acrescentou `readOnly` opcional no `MoneyField` e apagou o "confirmado" antigo ao editar o valor.
  - **F-02:** colocou a região `status` sempre montada.
  - **F-12:** deixou o `dl` válido.
  - **F-03:** completou os casos do classificador.
  - **F-09:** pôs a guarda `ValueError` em `apply_deposit` para valor que não é `Cents`.
  - **F-11:** escreveu os testes de política antes do corpo.
  - **F-06:** passou a evidência de espera de trava para `pg_blocking_pids`, restrita a este banco.
  - **F-05 e F-07:** limpou testes e corrigiu nomes de teste.
  - **F-10:** acrescentou uma linha no README sobre as contas demo no teto.
  - **F-13:** sincronizou os trechos desatualizados da story e da spec.
- **Mutação do F-08.** Com a página voltando a nascer com `pending=false` ao remontar (o comportamento anterior), o novo teste de navegador falhou ("Depositando…" não encontrado). O arquivo foi restaurado e conferido com `cmp`.
- **Onde divergiu.** A spec previa `depositFailureNotice('ambiguous') === 'reread'`. A decisão de reler passou para `sendDeposit`, e o teste correspondente mudou de lugar (`walletDeposit.test.ts`), sem afrouxar. O erro de campo vindo do servidor continua sem reanúncio quando o foco já está no campo: é o padrão do `MoneyField` da 2.4, que eu não quis mudar aqui.
- **Processo.** O `CLAUDE.md` pede Sonnet para implementar. Esta rodada de correções rodou no Opus, na mesma sessão que fez o review; registro isso para decidir se as correções pedem uma revisão independente antes do `done`.
- **Comandos executados (saída real):** `./verify.sh` e `VERIFY_E2E=1 ./verify.sh`, ambos com exit 0. Ruff e `ruff format --check` ok (66 arquivos), 1187 testes do back-end, ESLint, `tsc`, 114 testes do front com `node --test`, build do Vite e `docker build`. No opt-in, 127 testes de navegador passando e 5 ignorados (pilha real). Sem git e sem deploy.

### Re-review independente e aprovação final (25/10/2026)

- **Por quê.** As correções foram implementadas no Opus, na mesma sessão do review, e não no Sonnet que o `CLAUDE.md` prevê; quem corrigiu não podia aprovar a própria correção. Fiz antes o roteiro manual do F-08.
- **Como.** Pedi uma re-review em sessão nova do Opus, só das correções, das regressões e principalmente do F-08, sem refazer o review inteiro, sem git, sem deploy e sem alterar código.
- **Resultado.** F-08 confirmado como corrigido, F-01 a F-03 e F-05 a F-13 também; nenhum BLOCKER, HIGH ou MEDIUM introduzido. A re-review achou dois LOWs novos: LOW-1 (ao voltar pelo login com o `POST` pendente, o botão pode ficar em "Depositando…" até a próxima navegação, sem segundo `POST`) e LOW-2 (na remontagem, a confirmação pode não ser anunciada pelo leitor de tela). Comandos executados por ela: `npm test` (114 pass) e o `wallet.spec.ts` do Playwright três vezes (84 passed).
- **O que eu decidi.** Aceitar F-04, LOW-1 e LOW-2 como LOWs opcionais, sem corrigir agora e sem nova story, e aprovar o fechamento: a Story 3.1 ficou `done`.

## Story 3.2 — Regras de aceitação do lance com hora injetada

Usei o Claude Code com Opus para criar a story e a spec (P1 a P13 e C1 decididas por mim antes da spec, D1 a D14 detalhadas dentro delas) e com Sonnet para implementar, em sessão separada, pelo `bmad-build`. A IA implementou direto, sem subagente, a partir da spec. O Git foi meu, como sempre.

### O que eu decidi

- P1 a P13 e C1: domínio puro (sem banco, HTTP, transação nem relógio próprio), dataclasses congeladas, cinco códigos de recusa fora do `errors.py`, precedência do AD-7 (período → mínimo → líder → saldo) como contrato, mínimo `int | None` sem clamp, `lot_phase` extraída para um módulo puro com defesa de fuso e de janela, e o saldo fora da tentativa (C1).
- Nada de HTTP, migration, tabela de lances, trava, `clock_timestamp()` real nem PostgreSQL novo: isso é da 3.4 e da 3.5.

### O que a IA fez

- Leu a story e os cinco arquivos da spec e seguiu a ordem do `implementation-map.md`: `lot_time.py` e a reexportação em `lots.py` (testes de fase, OpenAPI e vitrine continuaram verdes sem editar nenhum), depois `bid_rules.py`, os três arquivos de teste e as mutações.
- Implementou a composição pré/pós-carteira como na spec: `evaluate_bid` só valida o saldo e encadeia `evaluate_pre_wallet` e `evaluate_post_wallet`; a prova de "cada regra roda uma vez" é por espião (`monkeypatch`) em `lot_phase`, `minimum_bid_cents` e `evaluate_post_wallet`.
- Escreveu a tabela de precedência de 36 linhas à mão, com o esperado digitado em cada linha, e os oito testes nomeados; a mesma tabela alimenta os testes da pré-carteira e da composição. A guarda de relógio é por AST, com um teste que prova que o detector encontra `datetime.now()` e `time.monotonic()`.
- Executou M1 a M11 com um script temporário (cópia, mutação, testes, restauração por cópia e `cmp`), todas derrubaram os testes previstos e todas voltaram idênticas; o resultado está na story.

### Onde a IA errou ou divergiu da spec

- Nenhum desvio de comportamento. A primeira versão do `bid_rules.py` passou do limite de 88 colunas do Ruff em comentários e docstrings; foi só ajuste de redação.
- Tropeço de ambiente: o primeiro `pytest` focado falhou com `Unsafe test database` por falta de `TEST_DATABASE_URL` no shell (os valores locais fictícios são os do `verify.sh`; nenhum `.env*` foi lido).
- A M6 (`<` → `<=` no mínimo) derrubou muito mais testes do que o previsto (53), porque o auxiliar `eligible_bid()` usa o mínimo exato; os testes-alvo (`test_first_bid_minimum` e `test_next_bid_minimum`) estão entre os que falharam.

### Limitações e observações

- `EligibleBid` impede uso acidental (construção direta e `dataclasses.replace` levantam `ValueError`), mas não é fronteira de segurança contra código Python arbitrário.
- `app.money` importa `pydantic`, então `bid_rules` o carrega de forma transitiva; a allowlist trata dos imports diretos.
- Não há teste manual específico: a story não cria UI nem endpoint. O `bmad-code-review` é meu e não foi rodado; a story fica em `review`.
- Comandos executados (saída real nesta sessão): `./verify.sh` e `VERIFY_E2E=1 ./verify.sh`, ambos com exit 0: Ruff e `ruff format --check` ok (71 arquivos), 1553 testes do back-end, ESLint, `tsc`, 114 testes do front com `node --test`, build do Vite e `docker build`; no opt-in, 127 testes de navegador passando e 5 ignorados (pilha real). Sem git, sem deploy.


### Correções aprovadas do code review — F-01 a F-03 (26/10/2026)

Decidi corrigir somente F-01, F-02 e F-03 e manter a Story 3.2 em `review`, sem nova
rodada de code review. Esta sessão executou no Codex com GPT-6.1, e não no Sonnet
solicitado no texto inicial; registro essa diferença de processo.

- **F-01:** a IA acrescentou um teste com dois objetos UUID distintos de mesmo valor,
  verificando `==`, `is not` e `ALREADY_WINNING` nas avaliações pré-carteira e completa.
  A mutação temporária `==` → `is` produziu **1 failed** (exit 1): retornou
  `EligibleBid` em vez da recusa. A restauração ocorreu em `finally`, e `cmp`
  confirmou conteúdo idêntico (exit 0), sem Git.
- **F-02:** o detector AST passou a reconhecer referências de atributos de relógio,
  inclusive `field(default_factory=datetime.now)`, `datetime.utcnow` e `time.time`.
  O autoteste cobre chamadas e factories. Casos válidos continuam aceitos: `now`
  injetado, `eligible.now`, data fixa e factory `list`. O primeiro reforço capturou
  indevidamente `eligible.now`; a IA restringiu as referências aos qualificadores
  de relógio e acrescentou um teste de regressão para esse dado de domínio.
- **F-03:** a IA qualificou a equivalência da composição para entradas estruturalmente
  válidas e explicitou D8: saldo separado validado antecipadamente, com `ValueError`
  para corrupção antes de qualquer recusa de negócio. Só docstrings foram alteradas
  no módulo produtivo; a comparação das ASTs sem docstrings confirmou comportamento
  executável idêntico.
- **Resultados reais:** focados após restauração, **355 passed em 0,16 s**, exit 0;
  `./verify.sh`, exit 0: Ruff, formatação (71 arquivos), **1563 passed, 1 warning em
  50,59 s**, ESLint, typecheck, **114 testes do front-end**, Vite e Docker build ok.
  O aviso de depreciação é de `httpx` no `starlette.testclient`. Não repeti o E2E
  opt-in, conforme solicitado.
- **Ambiente:** cache temporário do `uv` por bloqueio do cache padrão; banco e origem
  fictícios locais do `verify.sh` nos testes focados; acesso ao PostgreSQL fora do
  sandbox. Nenhum `.env*` foi lido. Duas linhas longas interromperam o primeiro
  `verify`; a formatação foi corrigida antes da execução completa aprovada.
- **Estado:** arquivo de sprint idêntico ao inicial; 3.2 `review`, Epic 3
  `in-progress`, 3.3 `backlog`. Sem Git, deploy, nova revisão ou início da 3.3.


### Correção N-01 após re-review independente (26/10/2026)

A re-review confirmou F-01 e F-03, classificou F-02 como parcial e apontou N-01
(MEDIUM): o guardrail aceitava `field(default_factory=dt.now)` com alias normal.
Decidi corrigir somente esse guardrail e sincronizar a redação de D8 na spec,
mantendo a Story 3.2 em `review` e sem nova revisão nesta sessão.

- A IA passou a montar o mapa de aliases a partir de `import` e `from ... import ...`
  absolutos de `datetime`/`time`, resolvendo cadeias AST até nomes canônicos. A guarda
  encontra chamadas e referências a callable pelo dono e pelo nome proibido, em vez
  de depender de nomes literais ou classificar qualquer `.now` como relógio.
- Preservou os testes anteriores e acrescentou as formas normais com e sem aliases,
  inclusive factories `dt.now`, `dt.utcnow`, `clock.time` e função importada com alias.
  Os controles negativos cobrem objetos de domínio, nomes locais, imports de outros
  módulos, data fixa e factory `list`.
- Ignorar temporariamente `alias.asname` em `ImportFrom` fez o teste explícito de
  `default_factory=dt.now` falhar: `[] != ['now']`, **1 failed em 0,03 s**, exit 1.
  Restauração em `finally`, conferida com `cmp` (exit 0).
- Sincronizou apenas a docstring ilustrativa e as garantias do `domain-contract.md`
  com D8: composição equivalente para entradas estruturalmente válidas e saldo
  separado validado antes de recusas de negócio, com `ValueError` para corrupção.
  Todos os módulos Python de `backend/app` permaneceram byte a byte idênticos.
- Resultados reais: pureza **52 passed em 0,04 s**; domínio da 3.2 após restauração
  **405 passed em 0,22 s**; `./verify.sh` exit 0: Ruff, formatação (71 arquivos),
  **1592 passed, 1 warning em 49,75 s**, lint, typecheck, **114 testes do front-end**,
  Vite e Docker build aprovados. Mantive o warning herdado de Starlette/httpx.
- Ambiente: cache temporário do `uv`, valores locais fictícios do `verify.sh` nos
  testes e acesso ao PostgreSQL fora do sandbox, sem leitura de `.env*`. Duas linhas
  longas foram formatadas com Ruff antes do verify. Sem desvio funcional e sem E2E
  opt-in, conforme o escopo solicitado.
- Sprint idêntica ao início: 3.2 `review`, Epic 3 `in-progress`, 3.3 `backlog`.
  Sem Git, deploy, nova revisão ou início da Story 3.3.


### Re-review independente final e fechamento da Story 3.2 (26/10/2026)

A revisão independente final confirmou F-01, F-02, F-03 e N-01 corrigidos,
D8/documentação sincronizada, nenhum novo finding real e compatibilidade com a Story
3.4 pronta sem redesenho. Com a recomendação **APROVADA PARA DONE**, decidi concluir
a Story 3.2 e atualizar seu status para `done`.

Este fechamento usou as evidências já registradas da última correção (52 testes de
pureza, 405 de domínio, verify exit 0, 1592 testes do back-end e 114 do front-end),
sem repetir testes ou nova revisão. O warning herdado Starlette/httpx segue fora do
escopo. Alterei somente documentação/status, preservando o histórico, o Epic 3 em
`in-progress` e a Story 3.3 em `backlog`. Sem Git, commit, push, deploy ou início da 3.3.


## Story 3.3 — Integridade histórica pura (26/10/2026)

Decidi implementar somente a Story 3.3 a partir da spec aprovada e dos companions,
preservando P1–P20/A1–A5 e os ajustes S-01/S-02. Autorizei testes, mutações e
verify completo; reservei a revisão independente para outra etapa. A entrega fica
em `review`, sem `bmad-code-review` e sem `done`.

A IA criou o módulo puro `bid_integrity.py`: três dataclasses congeladas com
construtores nomeados e validação estrita, pseudônimo HMAC-SHA-256, bytes JSON v1,
SHA-256 por lance, HMAC completo da âncora, compare_digest e verificação ordenada
de cadeia. Acrescentou a matriz em `test_bid_integrity.py` (95 casos coletados)
e ampliou a guarda de pureza existente sem alterar o detector de relógio da 3.2.
Os nove golden vectors foram copiados como literais independentes da spec; os
spies delegam à implementação real de HMAC, JSON e compare_digest.

Exigi a receita de autenticar e vincular o estado anterior antes de extensão.
A IA a demonstrou em composição local de teste: recálculo de histórico com
assinatura antiga, alteração de count/hash, truncamento, resumo antigo sobre
cadeia alterada e replay de âncora vazia de outro lote bloqueiam a extensão e
não emitem nova âncora. Vazio do lote correto exige assinatura válida; ausência
dela dá ValueError. Controles positivos emitem uma nova âncora válida. Isto não
implementa a transação da 3.4 nem prova adulteração no PostgreSQL da 5.1.

Resultados reais desta sessão:

- Focados com regressões 3.1/3.2: **573 passed em 0,35 s**, exit 0; após as
  mutações e restauração, **573 passed em 0,34 s**, exit 0.
- **M1–M13** executadas isoladamente e mortas: ordenação/separadores JSON,
  SHA-512, previous_hash ausente, aceitar uppercase, alias de 8 hex, igualdade
  comum no HMAC, count omitido, microssegundos opcionais, secret vazio, bool,
  sequência e links ignorados. Também executei as mutações pedidas de **ignorar
  lot_id** e **genesis incorreto**. Todas geraram falha de comportamento (exit 1),
  sem sintaxe/coleta; restauração em finally e cmp exit 0 em cada caso.
  A tabela da seção 13 da story identifica os testes que mataram cada mutante.
- `./verify.sh` **exit 0**: Ruff, formato de **73 arquivos**, PostgreSQL real de
  teste, **1719 passed, 1 warning em 49,42 s**, ESLint, typecheck, **114 testes
  frontend**, Vite e Docker build. O warning herdado de Starlette/httpx permanece.
  Não houve E2E opt-in, pois não mudou interface.

O primeiro comando focado parou por bloqueio de PostgreSQL no sandbox; com acesso
local autorizado, a tentativa anterior à criação do módulo falhou na coleta por
ModuleNotFoundError. Não apresento essa coleta como teste vermelho comportamental.
As falhas comportamentais registradas são as mutações realmente executadas. Ruff
apontou linhas longas no rascunho e removeu `.encode("utf-8")` no auto-fix UP012;
a IA formatou os arquivos e restaurou a expressão explícita normativa com um
noqa local antes da verificação final. Não houve alteração funcional do contrato.

Usei cache uv temporário, valores locais fictícios publicados em verify.sh e o
harness PostgreSQL existente. Nenhum `.env*`, credencial ou segredo operacional
foi lido pelo agente. Logs temporários em `/private/tmp/atrio-3-3-verify.log` e
`/private/tmp/atrio-3-3-mutations-dgnokzg3/`. Sem Git ou deploy, sem dependências,
migration, endpoint, frontend ou persistência nova. A 3.4 não foi iniciada.

Registrei a sincronização de Q3/P7/A1 em ARQUITETURA/CLAUDE/epics como pendência
antes da integração 3.4: alias histórico persistido por evento, nunca recalculado
na auditoria, formato de 16 hex e rotação transparente não suportada. Esses
documentos foram preservados. Alias pode colidir; segredo comprometido e rollback
integral de cadeia/âncora antigas válidas permanecem limites do desenho aprovado.
A revisão independente continua pendente por minha instrução explícita.

### Code review, correção do F-01 e fechamento da Story 3.3 (26/10/2026)

A revisão independente apontou um único finding, F-01 (LOW): os testes não
distinguiam `type(x) is int` de `isinstance(x, int)` com tratamento separado de
`bool`, então uma subclasse de `int` passaria numa regressão futura. O código
produtivo já estava correto. Aprovei corrigir só isso; a IA acrescentou testes com
subclasses locais de `int`, `str` e `bytes` (a spec exige tipos exatos) e provou
por mutação temporária que a suíte passa a falhar. Restaurou o módulo por cópia,
sem alterar produção e sem Git.

Re-review final: F-01 corrigido, nenhuma regressão, qualidade dos novos testes
adequada, `test_bid_integrity.py` com 105 passed, subclasses em 10 testes / 13
asserções, mutações de int/str/bytes mortas e nenhum arquivo produtivo alterado.
Último `./verify.sh` completo após a correção: 1729 passed no back-end, 114 no
front-end, Ruff, typecheck, build do Vite e Docker build aprovados, com 1 warning
herdado de Starlette/httpx. Com a recomendação **APROVADA PARA DONE**, decidi
concluir a Story 3.3. Este fechamento alterou só documentação e status, sem rodar
testes, sem Git e sem iniciar a 3.4. A sincronização de Q3/P7/A1 continua pendente
antes da integração da 3.4.

## Story 3.4 — Lance transacional com travas e anti-sniping (26/10/2026)

Decidi implementar somente a Story 3.4, a partir da spec aprovada (`/bmad-spec`, review
adversarial, SR-01 a SR-09 corrigidos) e do `/bmad-build`. Pedi para não redesenhar, não
tocar em `backend/.env.example`, não rodar Git e parar em `review`, sem `/bmad-code-review`.

A IA (Claude Sonnet 5.5 nesta sessão; o pedido citava outro modelo) escreveu a migration
`0005`, `app/bids.py` (modelo, gate, serviço, rota), as configurações de integridade, a âncora
vazia em `create_lot` e no seed, e a matriz de testes em PostgreSQL real: migration, serviço,
rota, concorrência (inclusive o controle negativo que provoca `40P01`), 23 adulterações
G1–G23 mais G9b/G10b/G11b e a fixture `drop_checks`, que recusa CHECK fora de `lots` e `bids` e
recria exatamente o que removeu.

Verificações realmente executadas: `pytest` com 1970 testes passando e `./verify.sh` completo
com exit 0. Executei 37 mutações dirigidas, uma por vez e restauradas; 35 morreram. As duas
que sobreviveram foram analisadas, não escondidas: uma é equivalente (o ORM não inclui no
`UPDATE` um atributo que não mudou) e a outra é defesa sem efeito observável hoje (o
`rollback()` antes do serviço).

Registro de um erro: a IA escreveu por engano um comando com `git status`; ele foi bloqueado e
nada de Git foi executado. Não foi testado: PostgreSQL com carga real, falha de conexão depois
do envio do `COMMIT` (indeterminada por natureza) nem o deploy no Render.

### Review independente e fechamento da Story 3.4 (26/10/2026)

O build foi feito com Claude Sonnet 5.5. Iniciei o review independente com
GPT-6 Astra High; ele atingiu o limite de uso antes da consolidação, depois de
encontrar um LOW, sem concluir toda a auditoria. Fiz a revisão focada complementar
com um modelo mais econômico, cobrindo writers, HTTP/security, qualidade dos testes
e mutation spot-check. Nenhuma falha MEDIUM+ foi encontrada; o único finding,
F-01 LOW documental, foi corrigido no exemplo Docker do README. Resultado
consolidado: 0 BLOCKER, 0 HIGH, 0 MEDIUM, nenhum LOW técnico; recomendação final:
aprovada. Fechei a 3.4 como `done`, mantendo o Epic 3 `in-progress` e a 3.5 em `backlog`.

Essa experiência me levou a reservar modelos High para tarefas de alto risco real
e usar modelos Medium para verificações focadas e consolidação, em vez de usar
High em todas as etapas.

## Story 3.5 — Dar lance pela sala do lote (26/10/2026)

- **Preparação:** create-story e revisão da spec com Claude Sonnet 5.5; elaboração
  da spec com GPT-6.1 Sol Medium.
- **O que a IA fez:** com a story e a spec já aprovadas por mim (D1–D5 fechadas), o Claude
  Sonnet 5.5 implementou os dois read models (`GET /bids` e `GET /bids/mine`) em `bids.py`, a
  sala no front (contrato HTTP, feedback por `code`, posição, contagem, envio pendente por
  conta e lote, painel, formulário e histórico), o ajuste do retorno ao lote em 401, os testes
  e a nota do README. Não alterou o motor da 3.4 nem tocou em Git ou em `.env*`.
- **O que revisei/decidi:** as decisões vinham da spec; a revisão do código é minha, antes do
  commit. O build não abriu decisão nova.
- **Onde a IA errou e foi corrigida durante o trabalho:** um `Countdown.tsx` e um
  `countdown.ts` na mesma pasta colidem em sistemas de arquivos que ignoram caixa (o `tsc`
  acusou); o componente virou `CountdownTimer.tsx`. Alguns testes meus tinham aritmética
  errada ou cenários impossíveis (um licitante dando lances seguidos recebe `already_winning`)
  e foram corrigidos no teste, não no código. Um teste da 3.4 que exigia 405 em `GET` no
  caminho do lance ficou obsoleto por decisão da spec e perdeu só essa linha.
- **Review e correções:** o code review independente com GPT-6.1 Sol Medium encontrou
  6 MEDIUM (F-01 a F-06) e 1 LOW opcional (F-07). F-01 a F-06 foram corrigidos e F-07
  recebeu cobertura adicional. O re-review focado e independente com GPT-6.1 Sol Medium
  confirmou as correções, considerou a cobertura suficiente e não encontrou regressão
  concreta: **APROVADA PARA DONE**. A Story 3.5 foi fechada como `done`.
- **Verificação após as correções:** `VERIFY_E2E=1 ./verify.sh`, exit 0; pytest 1987,
  npm test 147 e Playwright 168 passaram; Ruff/format, ESLint, tsc, Vite build e docker
  build OK. O re-review posterior executou apenas teste focado, sem alterar código.
  O fechamento documental não repetiu essas verificações.
- **Estratégia atual:** modelos High ficam reservados para problemas realmente críticos;
  tarefas normais e reviews focados usam Medium/Sonnet quando suficientes. Implementador
  e reviewer são independentes quando possível.

## Story 3.6 — Leiloeiro cancela lote sem lances (26/10/2026)

- **Preparação:** story e spec aprovadas por mim antes do build (D1 a D7 fechadas).
- **O que a IA fez:** o Claude Sonnet 5.5 implementou a migration `0006`, o módulo
  `app/lot_cancellation.py` (reusa a trava, a hora e o gate da 3.4 por import), o
  `lot_cancelled` no lance, os filtros de cancelado nas leituras públicas e no seed, o novo
  read model de `GET /api/lots/mine`, o painel "Meus lotes" com confirmação inline, o único
  novo código da sala, os testes (integração, concorrência C1/C2/C3, migration, `node --test`
  e Playwright) e a nota do README. Não tocou em Git nem em `.env*`.
- **O que revisei/decidi:** as decisões vinham da spec; a revisão do código é minha, antes do
  commit. O build não abriu decisão nova.
- **Onde a IA errou durante o trabalho:** o primeiro `verify` falhou no Ruff por duas linhas
  longas na docstring da migration (eu só tinha checado `app/`); o primeiro C3 reutilizava o
  mesmo licitante entre rodadas e quebrava o invariante de carteira por causa do reset do
  próprio teste, então passou a usar um licitante novo por rodada.
- **Mutações executadas** (uma por vez, restauração conferida com `cmp`): M1 (decidir
  `lot_has_bids` com o `bid_count` lido antes do `FOR UPDATE`), M2 (sem trava), M3 (sem gate),
  M4 (ignora `lot_has_bids`), M5 (sem dono), M6 (sem `lot_ended`), M7 (relógio do Python, duas
  variantes), M8 (já cancelado antes do gate), M9 (filtro movido para `WHERE` ou removido, em
  quatro variantes, só nas consultas com `LEFT JOIN`) e uma extra (`lot_cancelled` antes do
  gate). Todas reprovaram ao menos um teste.
- **Verificação:** `VERIFY_E2E=1 ./verify.sh`, exit 0: pytest 2036 passaram, `npm test`
  158 passaram, Playwright 189 passaram; Ruff, format, ESLint, `tsc`, build do Vite e docker
  build OK.
- **Code review e correção:** o review independente não encontrou HIGH/MEDIUM. O LOW F-01
  (C2 e C3 sem o snapshot de todas as carteiras) foi corrigido só nos testes, sem tocar em
  código produtivo. O arquivo `test_lot_cancellation_concurrency.py` rodou 3 vezes depois
  do ajuste: 5 passaram em cada uma. O `verify` completo não foi repetido (só assertions de
  teste mudaram).
- **Status:** Story 3.6 `done`; Epic 3 segue `in-progress`. Sem Git, sem deploy.

## Protótipo navegável de referência do front-end (26/10/2026)

Esta etapa não criou identidade nem alterou código de aplicação. Registro como cheguei até
ela e o que a IA fez.

### Como a direção visual foi formada

- Usei o Figma Make no início para prototipar os principais fluxos. Revisei e ajustei esse
  primeiro protótipo e descartei parte da direção visual inicial, que parecia produto SaaS
  ou plataforma de cursos.
- Depois defini uma identidade própria para o produto, baseada na marca roxa do projeto, com
  a obra como protagonista (hoje ÁTRIO — Leilões de Arte).
- Usei IA como apoio para comparar alternativas, organizar feedback, identificar problemas e
  formalizar as decisões. As decisões que aprovei viraram `DESIGN.md`, `EXPERIENCE.md` e
  `VITRINE-BLUEPRINT.md`.
- Como referências de leilão, destaco as três que o próprio desafio indica: Catawiki,
  LiveAuctioneers e Superbid. Também observei padrões consolidados de descoberta e
  organização de catálogos para validar decisões de escala e navegação. Não usei
  exclusivamente as referências do desafio e não copiei identidade de nenhuma.

### O que a IA fez nesta etapa

- Usei a skill `bmad-ux` depois, para transformar essas decisões **já aprovadas** em um
  protótipo navegável, e não para criar uma identidade nova. A IA leu os documentos
  vinculantes, propôs o mapa de telas e as decisões abertas e parou para eu decidir antes de
  gerar qualquer arquivo.
- Gerou o protótipo em `ux-designs/casa-de-leiloes/`, em HTML, CSS e JavaScript simples:
  **9 telas mais um hub de avaliação** (Vitrine, Login, Meus lotes, Criar lote, Sala,
  Carteira, Meus arremates, Comprovante e Auditoria). O hub escolhe tela, cenário, papel e
  larguras, e concentra a indicação de qual story entrega cada elemento, que não aparece nas
  telas.
- Baixou 10 obras reais de domínio público do Art Institute of Chicago, **apenas como assets
  do protótipo**, registradas em `SOURCES.md`. A regra de produção do AD-22 não mudou: a
  aplicação usa o IIIF por proxy e não armazena imagens de obras.
- Usei o protótipo para testar estados, escala (por exemplo 12 ao vivo, 20 próximos, 50
  encerrados, 120 lances), responsividade e acessibilidade básica.

### O que eu decidi

- D1 a D5 da etapa: posição do usuário na Sala (estado, último lance, quantidade e "Você" no
  histórico, sem definir endpoint nem payload); `00:00` com "Confirmando encerramento com o
  servidor…" e botão desabilitado; obras reais no protótipo; sem página de arquivo e sem
  link sem destino; produto planejado até a Story 5.3, com informação de story só no hub.
- Na aprovação final: formato do cronômetro só como apresentação (`MM:SS`, `HH:MM:SS`,
  `2 d 04 h`); lote em destaque fora do rail "Ao vivo"; sem histórico de movimentos na
  Carteira; auditoria adulterada sem apontar o lance divergente; sans com numerais tabulares
  para valores dinâmicos; Sala em duas colunas no tablet como referência; conteúdo fictício
  não vinculante. Estão em `ux-designs/casa-de-leiloes/PROTOTIPO.md`.

### Verificações realmente executadas

- Um script Playwright (Chromium) fez **284 carregamentos, de 71 combinações de tela e
  cenário, em 320, 390, 820 e 1280 px**, verificando erros de console, requisições que
  falham, rolagem horizontal, `alt`, rótulos, alvos de toque de 44 px e contraste calculado.
- A primeira rodada encontrou problemas reais de layout e de alvo de toque (estouro
  horizontal em 320 px, tabela de "Meus lotes" em 820 px, rail colado na borda, título
  espremido nas linhas de encerrados, link com 21 px de altura), que foram corrigidos. A
  rodada final **não reportou problemas dentro das verificações implementadas**.
- **Não foram testados:** leitor de tela completo, navegação integral por teclado, Firefox,
  Safari, impressão física nem dispositivo real.

### Limites

- O protótipo **não é código de produção** e não deve ser copiado para `frontend/`. Nenhuma
  lógica simulada de API, autenticação, WebSocket, tempo ou regra de leilão foi transferida
  para a aplicação real. Estados, textos, rotas, hashes e valores do protótipo são fictícios e
  não vinculantes; as stories definem os contratos reais.
- Não rodei `verify` nesta etapa: ela só adicionou documentação e o protótipo. Não houve Git.

## Criação BMAD da Story 4.1 — 27/10/2026

- Usei GPT-6.1 Sol Medium para criar a story documental de sala ao vivo por
  WebSocket, com snapshot inicial e atualização somente após commit, a partir do
  pedido explícito de create-story. Não iniciei spec nem implementação.
- Confrontei stories/specs 3.4 e 3.5 com backend e frontend vivos, testes,
  infraestrutura de echo do Epic 1 e documentos vinculantes de UX. Usei uma
  análise auxiliar de frontend, conforme a instrução de paralelização da skill.
- Registrei D1–D10 como recomendações, contrato público mínimo, concorrência,
  integração REST/WS/201, critérios de aceite, riscos e plano de testes. Mantive
  a 4.2 fora do escopo, inclusive heartbeat, timeout e reconexão automática.
- Identifiquei duas decisões reservadas a mim por CLAUDE/arquitetura ainda
  abertas: Q2 (Origin no handshake) e Q10 (rota WS). A story ficou
  **PRECISA DE DECISÕES** e `backlog`; acrescentei comentário no sprint sem
  iniciar Epic 4, sem marcar ready-for-dev e sem alterar ADs.
- Validei a completude documental com o checklist de create-story. Os resolvers
  BMAD rodaram com cache uv em `/tmp` após o cache padrão não permitir escrita.
  Consultei documentação primária de FastAPI, AnyIO e Vite para as APIs propostas.
  Não executei testes, verify, banco ou deploy; nenhum resultado histórico foi
  apresentado como nova execução. Não executei Git, não li `.env*` e não alterei
  secrets. Os únicos arquivos editados foram a nova story, este registro e o
  comentário de tracking.

## Correção do F-01 (MEDIUM) do review agregado do Epic 3 — 26/10/2026

- O review agregado apontou que a sala podia ficar bloqueada: o `POST` pendente terminava
  entre a renderização e o efeito da remontagem, e o efeito, ao consultar de novo o
  registro, não achava a entry e abandonava a promise.
- Corrigi só na sala: `LotPage` captura a entry na primeira renderização e o efeito segue a
  capturada (`bidToFollow`, que exige a mesma conta e o mesmo lote). `WalletPage` não foi tocada.
- Teste focado (`bidSubmission.test.ts`): registro já liberado, a capturada ainda é
  acompanhada, um único envio, e nunca vale para outra conta/lote. É teste puro: não há
  infraestrutura de componente no projeto, então o efeito em si não é exercitado.
- `VERIFY_E2E=1 ./verify.sh` posterior à correção: exit 0; 2036 backend, 160 front, 189
  Playwright (5 skipped); Ruff, format, ESLint, tsc, Vite e docker build passaram.
- Sem Git, sem backend naquela correção. Epic 3 ficou `in-progress` e o re-review
  foi realizado depois: F-01 aprovado com LOW opcional, conforme relatório e
  fechamento oficial acima.

> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.

## Revisão da AD-5 (anti-sniping) antes da Story 4.1 — 27/10/2026

- Decisão minha: reli o enunciado e mudei a interpretação do anti-sniping de
  `ends_at + 2 min` para `novo fim = now + 2 min` (mesmo `clock_timestamp()` lido sob a
  trava). A janela continua `0 < restante <= 2 min`; com exatamente 2 min o fim não muda
  e `anti_sniping_applied` fica falso; o lote nunca reabre.
- A IA implementou só essa mudança: `backend/app/bid_rules.py` (constante renomeada para
  `ANTI_SNIPING_RENEWAL`), testes unitários e de integração, e a sincronização
  documental (`ARQUITETURA.md` com a decisão nova e a anterior descartada, `CLAUDE.md`,
  README, DESIGN.md, nota datada nos artefatos das Stories 3.2/3.4, em `epics.md` e no
  roteiro de deploy 2+3). A nota administrativa do Epic 3 em `CLAUDE.md` foi corrigida
  para `done`. Nada retroativo em lotes ou lances; a representação canônica v1 e a
  cadeia SHA/HMAC não mudaram.
- Não implementei a Story 4.1. A IA não executou Git e não leu `.env*`.

## Build da Story 4.1 — sala ao vivo por WebSocket — 27/10/2026

- A IA (Claude Sonnet 5.5) implementou a 4.1 a partir da story consolidada e das decisões
  D1–D10 que eu aprovei; não decidiu nada novo. Continuou o trabalho já iniciado na sessão
  anterior (manager, endpoint, sinais pós-commit, cliente e testes) e fechou a verificação.
- Smoke local com duas conexões reais pelo proxy WS do Vite, banco descartável e segredos
  fictícios só no ambiente do processo (nenhum `.env*` lido). Resultado e comandos reais
  estão na seção 13 da story.
- O `VERIFY_E2E=1 ./verify.sh` falhou na primeira execução por erro no próprio teste novo
  da IA (esperava `0:01`, formato real `00:01`). Foi corrigida só a expectativa, repetida
  5× e o verify completo passou. Nenhum teste foi afrouxado.
- Sem Git; não iniciei a 4.2; review independente e prova no Render ainda não feitos.

## Correção do finding do teste manual da Story 4.1 (conexão perdida) — 27/10/2026

- Meu teste manual (Network → Offline) mostrou que a sala seguia "conectada" e que um
  "Atualizar sala" falho derrubava a página inteira para "Não foi possível carregar o lote".
- A IA diagnosticou: socket morto sem evento de close (sem heartbeat, que é da 4.2), e
  `loadDetail` sobrescrevia o lote já exibido ao falhar. Corrigiu só isso: evento `offline`
  marca a conexão como indisponível, falha de releitura preserva o lote, mensagem local de
  desatualização e nova tentativa. Sem reconexão automática, backoff ou heartbeat.
- Testes novos no Playwright (cinco cenários pedidos). Limitação registrada: rotas do
  Playwright não simulam rede caída de verdade, então o refresh falho usa 503 injetado.
- Sem Git; não iniciei a 4.2.

## Correções do 1º code review da Story 4.1 — 27/10/2026

- O code review independente (Opus, 5 camadas, sessão separada da implementação) deu "correção necessária".
  Eu decidi: corrigir M1 e L1–L10; manter o comportamento da publicação pós-commit e só documentar a limitação
  (D-A, sem timeout nem teto de conexões agora, que ficam para a 4.2 com a Q1); e fechar o socket no evento
  `offline` sem reconectar (D-B).
- A IA (Claude Sonnet 5.5) aplicou só isso. Para não confiar em teste que "passa sempre", reverteu de propósito
  cada correção e confirmou que os testes novos falham (captura de `CancelledError`, guarda `transitioned`,
  M1/L1/L2/L3/D-B), restaurando o código depois. Dois dos testes antigos passavam pelo motivo errado (Origin
  num lote inexistente; repetição de cancelamento sem assinantes) e foram refeitos.
- O primeiro `./verify.sh` falhou no Ruff por linhas longas nos testes novos da própria IA; corrigido só o
  formato. Números finais (2057 backend, 163 front, Playwright 200 passed e 5 skipped) estão na seção 15 da story.
- Sem Git; não iniciei a 4.2; nenhum `.env*` lido. Aguardo re-review independente e meu teste manual.


## Spec da Story 4.2 — heartbeat e reconexão automática (27/10/2026)

Pedi ao Codex somente criar e validar a especificação com `bmad-spec`, sem código.
Confirmei no pedido que a 4.1 está concluída/aprovada; a IA registrou que os arquivos
históricos ainda dizem review, sem inventar evidência nova nem alterar a 4.1.

A IA criou a story 4.2 e o pacote `spec-story-4-2-heartbeat-e-reconexao-automatica`,
com memória append-only, kernel, contrato de conexão, questões humanas, critérios/testes
e autovalidação em duas passagens. Formalizou estados/transições, corridas REST/WS/201,
cleanup, snapshot de recuperação e preservação de shouldApplyRoom. Consultou WHATWG
WebSockets e AnyIO para as limitações de ping/pong no browser e cancelamento de threads.

Não decidi os parâmetros ou as políticas propostas: QH-01–16 seguem abertas, inclusive
tetos de conexões e D-A; recomendar adiamento não significa que eu o aprovei. A story
ficou draft e o sprint permaneceu backlog com comentário equivalente, sem ready-for-dev.

Os resolvers BMAD falharam inicialmente por escrita no cache padrão do uv; rodaram com
cache em /tmp. Foram feitas conferências documentais de referências, IDs e tracking;
não houve review independente, pytest, Playwright, verify, consulta ao banco, smoke ou
deploy. Não houve Git, leitura de .env*, alteração de código ou início da 4.3.


## Consolidação humana da spec 4.2 — 27/10/2026

Decidi QH-01–16 e pedi somente consolidação documental. Mudei duas recomendações do
draft: descartei esperar CLOSED em favor de geração/token com sobreposição física
curta; no retorno visible, heartbeat devido sem pendência envia um ping, sem rajada.
Fixei ping a cada 20 s entre envios, pong 10 s, silêncio 60 s, snapshot 30 s,
backoff exponencial 1–30 s com equal jitter, reset só snapshot+pong e send/close 10 s.
Adiei explicitamente tetos de conexões e timeout pós-commit D-A.

A IA rederivou SPEC/companions/story da memória append-only, reavaliou T01–25,
atualizou CA01–18 e testes de gerações antigas, suspensão, reset, recuperação,
cleanup, zero SQL e cliente lento. Sincronizou a parte de Q1 em CLAUDE/arquitetura,
sem mudar AD-10/25 ou antecipar scheduler. Por meu pedido, a chave do sprint ficou
ASCII `4-2-heartbeat-e-reconexao-automatica: ready-for-dev`, sem duplicar a story;
o arquivo de story existente conserva seu nome acentuado.

Nenhuma questão humana ficou aberta; ready-for-dev significa especificação pronta,
não build iniciado. Autovalidação de coerência/preservação e conferências documentais
não são review independente ou testes de aplicação. Sem Git, .env*, código, banco,
verify, Playwright, deploy ou início da 4.3.

## Build da Story 4.2 — heartbeat e reconexão automática (27/10/2026)

Autorizei o Codex a implementar somente a 4.2 com `bmad-build`, a partir da spec
aprovada e de QH-01–16 fechadas. A skill despachou um subagente de implementação;
o coordenador conferiu os critérios de aceite e executou os gates finais. Não pedi
code review nesta sessão. Mantive o Git sob minha responsabilidade e a 4.3 fora.

A IA implementou ping/pong de aplicação sem SQL, watchdog de silêncio e deadlines
de transporte no backend; no frontend, os seis estados, gerações e timers
invalidados, backoff/jitter, snapshot obrigatório, reset só após pong, offline/online
e retorno visible sem rajada. Preservou `shouldApplyRoom`, regras financeiras,
manager de um processo, publicação pós-commit e os adiamentos de tetos/D-A.
Descartei esperar CLOSED e redefinir arbitragem pública, conforme decisões já aprovadas.

Os testes focados exercitaram relógio/RNG controlados, callbacks e timers aposentados,
70 casos backend em PostgreSQL real, 175 frontend e a suíte WS simulada. A conferência
final de aceite identificou dois caminhos REST que precisavam do terminal aprovado:
POST com `lot_cancelled` e POST 404. A IA unificou o cleanup com WS e acrescentou testes.
Corrigiu a fixture nova para usar o envelope real e HTTP 422 para `lot_cancelled`,
sem alterar o classificador HTTP. A suíte antiga de rodadas REST passou a iniciar com
WS offline simulado para controlar somente essas rodadas; a suíte WS cobre saúde e
recuperação separadamente. A repetição focada de ambas passou: 66 testes Chromium,
mais ESLint e TypeScript. Isso não é prova de rede offline real.

O primeiro `./verify.sh` terminou exit0: 2079 backend, 175 frontend, Ruff/format,
ESLint, TypeScript, Vite e imagem Docker passaram. O segundo verify com E2E e o smoke
real ficam registrados no relatório de implementação após sua execução. Primeiras
chamadas sem acesso ao loopback foram bloqueadas pelo sandbox; os testes autorizados
rodaram com acesso elevado e banco dedicado `_test`, sem remover guardas.

Não houve Git, leitura de `.env*`/credenciais, alteração de decisões humanas, deploy
ou code review. Evidências e matriz de testes em
`_bmad-output/specs/spec-story-4-2-heartbeat-e-reconexao-automatica/implementation-evidence.md`.


Fechei os gates da 4.2: `VERIFY_E2E=1 ./verify.sh` final exit0, 2079 backend (um
warning preexistente), 175 frontend e 213 E2E; Ruff/format, ESLint, tsc, Vite e Docker
passaram. Os 5 testes de pilha real, skipped no verify por opt-in, passaram em chamada
separada contra a instância de smoke via Vite. A primeira execução E2E completa
apontou duas expectativas antigas de título 404; sincronizei brand/vitrine e a de
real-stack com o texto genérico aprovado, sem retirar asserções, e repeti o gate.

O smoke usou duas abas Chromium, Vite 15173, backend 18000 e banco novo descartável
*_test: snapshot/ping/pong; offline preserva sala e falha REST local; lance de outra
aba recuperado por snapshot; online repetido cria uma só tentativa; callbacks antigos
ignorados; processo backend derrubado/reiniciado; ambas as abas recebem novos lances;
cliente silencioso expulso após 60 s enquanto saudáveis recebem pong; 320 px sem overflow.
A primeira tentativa do observador confundiu WS HMR do Vite com a sala; a IA corrigiu
o filtro do harness, não o produto. Banco e processos próprios foram removidos.
Suspensão física do SO e wss/Render não foram testados. Story 4.2 ficou review para
meu teste manual e review posterior; Epic 4 in-progress, 4.3 backlog. Nenhuma divergência
funcional conhecida ou nova decisão humana. Relatório completo no companion acima.

## Correção do finding manual da Story 4.2 (27/10/2026)

Observei no teste manual que uma recuperação WebSocket podia mostrar sala
conectada e conservar os avisos de refresh falho/histórico desatualizado.
Autorizei corrigir somente esse problema e preparar a story para re-review focal.

A IA separou a marcação pública de stale do resultado agregado das leituras,
que inclui participação e carteira. Snapshot válido da conexão atual limpa os
avisos públicos mesmo com dados iguais, preservando erros privados legítimos.
Descartei apagar todas as mensagens ao reconectar, pois ocultaria falhas reais
de `/mine` e carteira. Mantive arbitragem, heartbeat, backoff, geração e reconexão.

Os testes novos reproduziram o finding antes da alteração: dois casos com
snapshot igual falharam por aviso persistente; dois com snapshot mais novo
passaram. A matriz inclui visitante e licitante com leituras privadas falhando.
A checagem interna também apontou a ordem REST retido → snapshot igual → falha
REST tardia: estendi a época pública a cada snapshot, sem cancelar leituras
privadas, e acrescentei regressão dessa ordem. O teste existente de falha privada
passou a exigir mensagem privada sem aviso público indevido; não retirei as
garantias sobre resultado ambíguo do POST.

Mantive o Git sob minha responsabilidade, a story em review e a 4.3 fora do
escopo. Não li `.env*`, não fiz deploy nem declarei aceite humano final.

Concluí a validação: direcionados de sala/WS `71 passed (16.8s)`; `./verify.sh`
exit 0 com `2079 passed, 1 warning in 105.05s` e frontend 175/175;
`VERIFY_E2E=1 ./verify.sh` exit 0 com `2079 passed, 1 warning in 98.36s`,
frontend 175/175 e `218 passed (25.7s)`, `5 skipped`. Ruff/format, ESLint, tsc,
Vite e Docker passaram em ambos os gates. O warning Starlette/httpx é
preexistente; os 5 opt-in de pilha real não foram reexecutados nesta correção.

A execução usou proteções temporárias fora do produto para impedir dotenv em
Python/uv/Compose e leitura de `.env*` no Node. O sandbox recusou a primeira
abertura do Vite no loopback; os testes autorizados rodaram com acesso elevado.
Não alterei verify nem configuração da aplicação. A checagem interna final não
encontrou defeito concreto restante na correção. Registrei os detalhes e logs na
story e na nota focal `spec-4-2-correcao-stale-publico.md`; o Playwright regenerou
`frontend/test-results/.last-run.json`. Parei pronta para re-review focal.


## Correção focal MEDIUM da Story 4.2 (27/10/2026)

Recebi no re-review focal o finding de que saldo e participação previamente
carregados podiam ficar silenciosamente antigos depois da recuperação pública.
Autorizei somente essa correção. A IA explicitou confirmação de `/mine` e erro
de carteira separados de `publicStale`, preservando dados conhecidos e avisos
privados até sucesso privado vigente. Descartei inferir atualização privada de
`ready`, pareamento isolado ou snapshot público. A posição anterior fica oculta
enquanto aguarda ou falha a revalidação (M1).

Acrescentei regressões para `/mine`, carteira e ambos falhando depois de sucesso
inicial, snapshot idêntico, recuperação privada individual e resposta antiga
substituída. A checagem interna focal não apontou outro defeito concreto. Uma
expectativa inicial da fixture foi ajustada para respeitar o pareamento M1;
não alterei comportamento de transporte ou backend. O teste de mutação que
limpava erros privados no snapshot falhou no cenário principal, como exigido;
o fonte foi restaurado automaticamente. Os gates finais passaram, conforme resultados abaixo.
Mantenho a story em review e a 4.3 fora do escopo, sem Git, leitura de `.env*`
ou deploy.


Validação já concluída desta correção privada: direcionados finais
`75 passed (18.8s)`; `./verify.sh` exit 0 com
`2079 passed, 1 warning in 100.57s`, frontend `tests 175`, `pass 175`, `fail 0`.
Ruff/format, ESLint, TypeScript, Vite e Docker passaram. A mutação teve exit 1
com `1 failed` no cenário principal após snapshot; fonte original restaurado.
A checagem interna focal final não encontrou defeito concreto aberto.
`VERIFY_E2E=1 ./verify.sh` exit 0: `2079 passed, 1 warning in 99.41s`,
frontend `tests 175`, `pass 175`, `fail 0`, Playwright `222 passed (26.9s)` e
`5 skipped` (opt-in de pilha real). Ruff/format, ESLint, TypeScript, Vite e Docker
passaram; ambos os gates terminaram com `verify.sh: todas as etapas passaram.`
O warning backend Starlette/httpx continua preexistente. Não reexecutei pilha
real nem smoke Render nesta correção.

Usei as proteções temporárias externas já existentes contra dotenv em
uv/Python/Compose e leitura de `.env*` no Node; o sandbox bloqueou loopback na
primeira tentativa dos direcionados, que rodei com acesso elevado. Não alterei
verify nem configuração da aplicação. O Playwright regenerou somente
`frontend/test-results/.last-run.json` fora dos seis arquivos previstos;
nenhum arquivo de segredo alterado foi detectado pela checagem de nomes.
Não executei Git, não li `.env*`, não fiz deploy e não iniciei a 4.3.
Parei com a correção pronta para novo re-review focal, sem declarar aceite final.


## Cobertura focal — sucesso privado superseded realmente entregue (27/10/2026)

Corrigi somente a lacuna de cobertura apontada no re-review: o teste anterior
abortava os GETs antigos, portanto sua liberação não provava descarte de sucesso
privado pela lógica de aplicação. Descartei usar aborto de fetch como evidência
de sucesso superseded entregue. Não alterei produção: comparei `LotPage.tsx`
e `LotBidPanel.tsx` byte a byte com a partida após restaurar a mutação.

Substituí o caso no spec WS por uma sequência determinística A/B/C. Um adaptador
de fetch instalado só neste teste remove o signal unicamente das duas chamadas
HTTP de A, preservando os sinais e gerações originais usados por `loadPrivate`.
A requisição continua sendo HTTP real interceptado pelo Playwright; não simulei
`fetchMyBids`, `fetchWallet`, os validadores nem o resultado de `isCurrent`.
Espero os dois handlers de A entrarem na barreira antes de iniciar B. B responde
503 e o teste espera os dois avisos privados e o fim da rodada. Só então libero
A com HTTP 200 e corpos válidos de participação/carteira. Registro dentro de
`Response.json` os corpos consumidos, status 200 e sinais originais já abortados,
provando que o transporte de A entregou sucesso mesmo após a substituição lógica.
Depois de ambos os JSONs resolvidos, espero dois frames para as continuações da
aplicação e o commit do React. Exijo avisos presentes, posição antiga oculta,
saldo conhecido de R$ 4.890,00 preservado contra R$ 890,00 de A, preço/histórico
públicos mantidos. C vigente tem sucesso, mostra posição/saldo atuais de
R$ 6.000,00 e remove ambos os avisos.

Mutação executada: permiti que resultados privados bem-sucedidos ignorassem a
guarda `round.isCurrent()`. O teste passou pelas comprovações de entrega dos dois
HTTP 200 e falhou depois porque o aviso de carteira havia sido removido:
Playwright exit 1, `1 failed`. Restaurei automaticamente o fonte em `finally` e
conferi igualdade byte a byte. A checagem interna independente do teste não
encontrou defeito concreto de cobertura. Nenhum defeito funcional foi revelado.
Somente o spec de testes e os três documentos desta correção foram editados;
validação final concluída. Mantenho a Story 4.2 em review para novo re-review,
sem aceite final, Git, leitura de `.env*`, backend ou início da 4.3.


Validação final da cobertura superseded:

| Gate | Resultado real |
| --- | --- |
| `npx playwright test e2e/lot-room-ws.spec.ts --workers=2` | exit 0; `33 passed (8.0s)` |
| `./verify.sh` | exit 0; `2079 passed, 1 warning in 102.63s`; frontend `tests 175`, `pass 175`, `fail 0` |
| `VERIFY_E2E=1 ./verify.sh` | exit 0; `2079 passed, 1 warning in 100.04s`; frontend 175/175; `222 passed (23.9s)`, `5 skipped` |

Ruff/format, ESLint, TypeScript, Vite e Docker passaram em ambos os gates,
encerrados com `verify.sh: todas as etapas passaram.` Os cinco skips são opt-in
de pilha real, não reexecutados nesta tarefa; o warning backend Starlette/httpx
é preexistente. Mantive as proteções externas já existentes contra leitura de
`.env*` em uv/Python/Compose/Node, sem mudar verify ou configuração da aplicação.
A mutação terminou com exit 1 e `1 failed`, como esperado; o fonte foi restaurado.

Entrega: somente `frontend/e2e/lot-room-ws.spec.ts`, story 4.2,
`docs/uso_de_ia.md` e nota focal; o Playwright regenerou
`frontend/test-results/.last-run.json` fora da lista prevista. A comparação
final de `LotPage.tsx` e `LotBidPanel.tsx` com a partida confirmou conteúdo
idêntico. Não detectei arquivo de segredo alterado pela checagem de nomes.
Nenhum finding interno aberto. Parei pronta para novo re-review focal.

## Correção isolada da AD-5 cumulativa — 27/10/2026

Recebi uma nova decisão humana vinculante antes da Story 4.3: voltar a somar
2 minutos ao término vigente para cada lance válido na janela inclusiva. Descartei
novamente a renovação a partir de `now`. Atualizei primeiro a AD-5 e depois a
documentação de apoio; só então alterarei código e testes. Preservarei os textos
históricos com nota datada e não alterarei `.memlog.md`.

Escopo aprovado: regra pura, feedback, mocks e expectativas/testes da regra,
integração e concorrência PostgreSQL. Sem migration ou alteração de dados; sem
mudanças em canonical bid v1, SHA-256, HMAC, `final_hash`, pseudônimo, carteira,
compromisso financeiro, relógio autoritativo e ordem de locks. A Story 4.2 não
contém descrição concreta da fórmula: mantenho sua spec e máquina de conexão.
A Story 4.3 não será iniciada. Evidência: `docs/EVIDENCIA-ANTI-SNIPING-CUMULATIVO.md`.

Na auditoria desta correção, detectei e desfiz uma inserção acidental da nota em
três `.memlog.md`: removi exclusivamente a nota inserida, restaurando o conteúdo
anterior. O glob usado na documentação incluía arquivos ocultos; o resultado final
preserva os logs históricos. A nota de evidência registra a ocorrência e os testes.

### Resultados finais da correção cumulativa (27/10/2026)

Executei os direcionados finais: **470 passed, 1 warning in 26.90s**, incluindo
PostgreSQL real, concorrência dentro/fora da nova janela e transporte WebSocket.
Playwright focal: **2 passed (4.0s)**. A mutação para `now + 2 minutos` produziu
**3 failed in 0.26s** como esperado; restaurei integralmente a regra cumulativa.

`./verify.sh`: **exit 0**, backend **2083 passed in 105.06s**, frontend **175 pass**.
`VERIFY_E2E=1 ./verify.sh`: **exit 0**, backend **2083 passed in 103.10s**,
frontend **175 pass**, Playwright **222 passed (24.3s), 5 skipped**. Ambos
terminaram com `verify.sh: todas as etapas passaram.`; lint, format, tipos,
Vite e Docker aprovados. O warning do pytest é de depreciação do TestClient.
As falhas anteriores corrigidas e os logs reais estão na nota de evidência.

Um revisor interno separado não confirmou defeitos; incorporei sua sugestão LOW
sobre B fora da nova janela e ele reconferiu os ajustes. O review independente
solicitado pelo dono permanece para antes do commit. Confirmei ausência de
migration nova e de alteração de dados históricos, canonical bid v1, SHA-256,
HMAC, final_hash, pseudônimo, carteira, compromisso financeiro e ordem de locks.
`ends_at` continua fora do canônico. Não iniciei nenhuma parte da Story 4.3;
não executei Git nem fiz commit. Arquivos alterados e históricos anotados estão
listados em `docs/EVIDENCIA-ANTI-SNIPING-CUMULATIVO.md`.

## Especificação da Story 4.3 — 27/10/2026

Pedi ao Codex usar `bmad-spec` somente para criar e validar a especificação do
fechamento, liquidação idempotente e comprovante base. Não autorizei código.
A IA leu as fontes obrigatórias e confrontou a arquitetura com o modelo vivo do
Epic 3: só o líder reserva saldo e cada perdedor já foi liberado ao ser superado.
Mantive o débito definitivo do vencedor e crédito ao leiloeiro previstos na
Story 4.3; descartei inventar ledger ou liberar todos os lances novamente.

A IA criou a story draft e o pacote
`_bmad-output/specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/`,
com memória append-only via writer oficial, kernel e contratos de transação,
concorrência, dinheiro, resultado/receipt, questões, critérios/testes e validação.
Explicitou clock pós-lock, releitura do fim cumulativo, UPDATE que respeita CHECK,
um commit único, vazio sem receipt e falha segura de integridade sem reassinatura.
Separou rollback certo de COMMIT com confirmação perdida e preservou o consumo
apenas da reserva do lote alvo, incluindo cenários de múltiplos lotes.

QH-01–10 continuam abertas: invocação manual, persistência do resultado, campos do
comprovante, consulta, outcomes, HTTP condicional, representação pública, crédito
acima do teto, referências de integridade e revalidação na repetição. Não aprovei
nenhuma recomendação implicitamente. A story permanece draft e o sprint backlog;
não houve scheduler/catch-up, evento WS, painel, link ou início da 4.4/4.5/5.x.

Executei somente resolução de configuração/customização BMAD, escrita documental
e conferências estáticas de referências/IDs/tracking. O cache uv padrão foi
bloqueado; os resolvers passaram com cache em `/private/tmp`. Consultei as fontes
primárias do PostgreSQL 18 para locks, isolamento e clock (links no companion de
concorrência). A autovalidação em coerência/preservação não é review independente
nem aprovação para desenvolvimento; o plano PG real permanece a executar no build.
Não houve pytest, verify, Playwright, SQL, migrations, smoke ou deploy nesta sessão.
Não executei Git, não li `.env*` e não alterei código ou as decisões arquiteturais.

## Consolidação humana da especificação 4.3 — 27/10/2026

Decidi QH-01–10 e pedi somente consolidar a especificação com `bmad-spec`,
revalidar e depois promover story/sprint a ready-for-dev. Não autorizei código.
Descartei novas rotas HTTP e fixei serviço/readers internos; settlement próprio
é o registro econômico autoritativo para sold/unsold e receipt é separado, só
sold. Ambos têm ID próprio e UNIQUE por lote; receipt também tem settlement_id
UNIQUE e não contém winner_user_id ou HMAC nem no schema. A âncora validada fica
congelada somente no settlement interno. Não congelo metadados extras da obra.

A IA retomou a memória append-only e rederivou kernel, companions e story com as
decisões, preservando CAP-1–5. Adaptou a referência conceitual winning_bid_id à
PK real (lot_id,sequence) por winning_bid_sequence/FK composta, sem alterar bids
ou canonical v1. Explicitou o comando interno dono da confirmação transacional,
helper provisório sem transitioned, quatro statuses e falhas tipadas separadas.
Ready-for-dev significa contrato pronto, não autorização para começar build.

Fixei consumo da reserva F sem segundo débito no disponível, conservação dos
totais e preservação de perdedores/outros lotes. Teto excedido falha integralmente;
a 4.4 tratará a condição operacional sem retry quente infinito, sem resolver esse
mecanismo na 4.3. Repetição revalida lote/settlement/receipt/referências, sem repair,
recriação ou nova transferência; sold sem receipt e unsold com receipt são conflitos.
A confirmação perdida de commit segue distinta do rollback conhecido.

A IA preservou PG01–24 e acrescentou PG25–35, um por cada prova adicional que pedi,
além de CA19–21. Retirou as alternativas e testes condicionais de nova API; registrou
HTTP 200 novo/repetido somente como orientação futura. Manteve phase, WS, máquina
4.2, UI da sala, painel, gatilhos/eventos 4.4 e stories 5.x fora do escopo.

As duas passagens de autovalidação de coerência/preservação e a conferência estática
pré-promoção passaram; só então story/SPEC/sprint foram promovidos. Foram conferidos
referências, IDs, schemas/privacidade/outcomes, tracking, preservação do corpo anterior
da memória e hashes de arquivos de aplicação/testes selecionados na partida.
Isso não é review independente nem execução dos testes planejados. Não rodei pytest,
verify, Playwright, SQL, migrations, navegador, smoke ou deploy. Não executei Git,
não li .env* e não iniciei código ou Story 4.4. Todas QH-01–10 estão fechadas.

## Build autorizado da Story 4.3 — 27/10/2026

Autorizei o Codex a implementar somente a Story 4.3 usando `bmad-build`, a partir
da SPEC e das decisões QH-01–10 já fechadas. Mantive serviço/readers internos,
settlement autoritativo sold/unsold e receipt separado só para sold. Descartei
nova contabilidade, rota HTTP, gatilhos/scheduler/catch-up, publicação WS, UI e
início da 4.4. O review independente fica para meu aceite posterior.

A IA iniciou story/SPEC/sprint em in-progress e preservou baseline local sem Git.
Leu o contrato aprovado e confirmou no Epic 3 a liberação da reserva de cada líder
superado: o fechamento deve consumir apenas F do vencedor, preservando outras
reservas. O workflow delegou a implementação a um agente; verificação e evidência
final permanecem sob coordenação do agente principal. PostgreSQL dedicado de
teste preparado com Docker; resultados serão registrados após execução real.

Concluí o build da 4.3: migration `0007`, modelos/DTOs/readers e comando com
Session própria, um commit e sucesso confirmado só após ele. A implementação
consome T−F/C−F do vencedor e credita T+F ao leiloeiro; preserva disponível,
reservas alheias, perdedores e teto. Retry autentica/revalida sem carteiras ou
reparo. Protegi o terminal em lance/cancelamento, sem gatilhos ou publicação.

Os PG01–35 foram executados em **81 casos: 81 passed, 1 warning in 11.82s**.
Concorrência usa PostgreSQL real e PID bloqueado especificamente por outro PID.
Aborto real de COMMIT foi provocado por trigger diferida só de teste; perda
sintética de confirmação foi lançada depois de COMMIT real e o retry não
repetiu transferência. Cinco mutações foram detectadas (débito extra, fim
pré-lock, reliquidação, receipt unsold e gate ignorado), restauradas em finally
e conferidas byte a byte. Smoke transacional exit 0: W 80000/32000 → 68000/20000
(disponível 48000 constante), S 5000/0 → 17000/0; F=12000; reserva alheia 20000;
receipt sold=1/unsold=0; retries already_settled/false.

`./verify.sh` final exit 0: **2164 passed, 1 warning in 116.14s**, frontend
**175/175**. `VERIFY_E2E=1 ./verify.sh` exit 0: **2164 passed, 1 warning in
115.82s**, frontend **175/175**, Playwright **222 passed (25.0s), 5 skipped**.
Ruff/format (96 arquivos), ESLint, tsc, Vite e Docker aprovados em ambos, com
`verify.sh: todas as etapas passaram.`. Os cinco skips existentes da pilha
real continuam opt-in; não os apresentei como executados. Primeiro verify:
1 failed/2163 passed por enumeração antiga das tabelas; atualizei somente a
lista exata e repeti o gate completo. Falhas exploratórias de fixture WS e
harness de concorrência também foram corrigidas sem alterar o contrato.

Nenhum agente abriu `.env*` diretamente. A primeira rodada exploratória começou
sem a guarda externa contra dotenv; não certifico ausência de leitura implícita
nessa rodada. As posteriores/finais usaram as guardas externas de Python/Node,
uv e Compose sem modificar produto/verify. O sandbox bloqueou Docker na partida;
a execução autorizada usou PostgreSQL dedicado e cache uv em /private/tmp.
A checagem final trata segredos só por nomes. Nenhum Git, deploy ou code review.

Story 4.3/sprint ficaram **review**, SPEC **in-review**, Epic 4 **in-progress**;
4.4 **backlog**, sem início de implementação. Arquivos/resultados/limites em
`_bmad-output/specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/implementation-evidence.md`.
`frontend/test-results/.last-run.json` foi regenerado pelo Playwright; nenhum
código de UI/WS/máquina 4.2 mudou. Review e aceite finais continuam meus.

## Ajuste de cobertura após review da Story 4.3 — 27/10/2026

Solicitei somente os dois testes para os LOWs do review, sem alterar produção,
Git, dotenv ou iniciar a Story 4.4. A IA identificou que não há settlement válido
para lote previamente cancelado; confirmei o cenário do review para F43-02:
settlement unsold, prazo adulterado e tentativa de cancelamento. O teste também
exige conflito no retry do settlement. F43-01 altera somente o vencedor de um
sold válido. Ambos verificam conflito, ausência de escritas e snapshot preservado.

Os dois testes passaram isoladamente e detectaram as respectivas mutações focais
executadas separadamente em memória. A suíte da story passou com 83 testes. As
execuções usaram PostgreSQL dedicado e proteções externas contra leitura de
dotenv. A story não foi marcada como done; evidência detalhada está no relatório
final e em `implementation-evidence.md`.

O `./verify.sh` final passou: backend **2166 passed, 1 warning in 117.98s**,
frontend **175 passed**, lint/typecheck/build e imagem Docker aprovados.
Playwright não foi reexecutado, pois não houve mudança de frontend ou E2E.

## Fechamento formal da Story 4.3 — 27/10/2026

Autorizei o fechamento documental após o review aprovado e a cobertura dos dois
LOWs. Story, entrada do sprint e SPEC passam a **done**; Epic 4 permanece
**in-progress**. Não solicitei novas execuções de testes ou mudanças de produção;
a Story 4.4 não foi iniciada.

## Especificação da Story 4.4 — 27/10/2026

Pedi ao Codex usar `bmad-spec` somente para criar e validar a especificação dos
gatilhos do fechamento e evento terminal. Sol/High eram recomendações do pedido;
não atribuo uma troca de modelo não confirmada. Não autorizei implementação,
Git, leitura de `.env*` nem início da 4.5.

A IA confrontou os contratos/evidências da 4.3 com o código atual de settlement,
lotes, sala/manager, publicação pós-commit, startup/seed, cliente e testes. Criou
story draft e pacote `spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento`,
com memória append-only via script oficial, CAP-1–6 e companions de lifecycle,
evento, recuperação, falhas/retry, concorrência, critérios/testes, questões e
validação. Os resolvers BMAD passaram com cache uv em `/private/tmp` após o cache
padrão ser bloqueado; nenhuma alteração no produto/configuração foi necessária.

Preservei as decisões já vinculantes: catch-up antes de seed/tráfego, somente
quem transicionou publica e snapshot/reconnect recupera crash entre commit e
publicação, sem outbox. A IA não escolheu republicar em already_settled nem
esconder a incompatibilidade dessa alternativa com Q6. Incluiu o gatilho em POST
vencido do épico/Q9, após rollback e em transação própria, sem nova regra de lance.

QH-01–16 seguem pendentes: as doze solicitadas e quatro lacunas concretas de
integração (posição do seed/falha no boot, resposta do POST, snapshot/cliente e
limites DB/shutdown). Recomendações de cadência, batch, cooldown, evento/close e
compatibilidade não são decisões minhas. Descartei implicitamente autorizar
build por existir especificação: story continua draft e sprint backlog; Epic 4
in-progress, demais stories preservadas.

Planejei CA01–12, T01–40 (trinta mínimos com IDs próprios) e M01–08, sem executar
testes de aplicação. Autovalidação de coerência/preservação e conferências
estáticas não são review independente nem execução PostgreSQL/WS/E2E. Não
rodei pytest, verify, SQL, migrations, navegador, smoke ou deploy; não executei
Git, não li `.env*` e não alterei código de aplicação/testes.

Conferência documental final: exit 0, sem links/companions quebrados; IDs de 6
capacidades, 16 questões, 12 critérios, 40 cenários e 8 mutações planejadas
conferidos. Comparei hashes de 204 arquivos da baseline: 203 idênticos e somente
o sprint alterado por dois comentários, sem mudar status. Registrei os vereditos
de coerência/preservação na memória pelo script oficial. A spec continua draft
para minhas decisões; isso não é teste de aplicação ou review independente.


## Consolidação humana da spec 4.4 — 28/10/2026

Decidi QH-01–16 e pedi somente consolidar/revalidar documentos, promovendo
story/sprint a ready-for-dev depois do gate. Mantive a proibição de código,
testes de aplicação, Git, .env* e início da 4.5. A retomada final ocorreu por
meu pedido para terminar; ready-for-dev não é autorização de build.

Revisei duas direções anteriores: migrations/seed existentes continuam antes
do lifespan/catch-up, e POST vencido só recusa sem settlement/segunda transação/
publicação. A IA atualizou primeiro AD-19/Q4/Q9 e os resumos CLAUDE/épico/README,
depois rederivou os contratos da memória append-only. CAP-6 foi aposentada sem
reutilizar o ID; CAP-1–5 permanecem. Os registros do draft acima são históricos.

Fixei evento lot_closed com nove campos públicos, incluindo as_of copiado de
settled_at persistido; snapshot mantém room.as_of da leitura e settlement
separado de phase. Conectado drena terminal e fecha 1000; novo settled recebe
snapshot terminal antes de fechar. Cliente não inicia heartbeat/reconnect após
terminal. Publicação perdida converge por snapshot, sem outbox, replay de
already_settled ou desfazer/refazer liquidação.

Preservei ciclo seguido de espera 2 s, SKIP local, 200 linhas/50 tentativas por
ciclo, cursor justo/wrap, cooldown 300 s e backoff transitório 2–30 s. Descartei os
novos timeouts de 2 s/DB do draft; send/close 10 s e limites DB existentes continuam.
Shutdown acompanha recursos numa janela global 30 s e loga excesso sem abandonar
worker/Session ou afirmar rollback pelo timeout. Nenhuma nova tela/UX de resultado.

A revalidação de coerência e preservação passou; CA01–12, T01–40 e M01–08
continuam planejados com oráculos atualizados, especialmente ausência de efeito
no POST. Conferência estática pré-promoção exit 0/errors[]: 201 arquivos de
código/testes intactos, memória append-only, 16 decisões fechadas, IDs e links/
companions válidos. Só então promovi SPEC/story/sprint para ready-for-dev,
preservando Epic 4 in-progress, 4.3 done, 4.5 backlog e estados das demais stories.

Não executei pytest, Playwright, verify, SQL, migrations, navegador, smoke,
deploy ou review independente. Não executei Git nem li .env*. Somente
resolução BMAD, escrita documental e conferências estáticas; modelo recomendado
no pedido não é evidência de troca de modelo efetivo.

## Build autorizado da Story 4.4 — 28/10/2026

Autorizei somente a Story 4.4 pelo `bmad-build`, com QH-01–16 fechadas. Mantive
scheduler/catch-up como únicos gatilhos operacionais, `settle_lot` como dono da
liquidação e confirmação, evento público pós-commit e recuperação por snapshot.
Descartei nova lógica financeira/bidding, settlement no POST/handshake, outbox,
replay de already_settled, UI da 4.5 e code review nesta sessão.

A IA registrou baseline local sem Git e iniciou story/SPEC/sprint em in-progress.
O workflow determinou a delegação da implementação a um agente sem histórico;
a coordenação principal prepara e executa gates, mutações, smoke e evidência.
Sol/High são recomendações do pedido, sem alegar troca de modelo efetivo.
Preparei PostgreSQL dedicado e guardas externas contra dotenv implícito para
Python/Node/uv/Compose, sem alterar produto ou verify. O primeiro acesso Docker
foi bloqueado pelo sandbox; a execução autorizada confirmou o contêiner saudável.
Os testes legados controlam a admissão pelo adaptador de lifecycle apenas no
harness; testes marcados settlement_lifecycle exercitam startup real, sem um
switch de produção para ocultar catch-up. Resultados serão registrados após
execução; não confundo implementação planejada com prova executada.

Concluí o build 4.4 e deixei Story/sprint em **review**, SPEC **in-review** e
Epic 4 **in-progress**. Não marquei done nem iniciei4.5. O comando 4.3, finanças,
bidding, integridade, lotes/seed/start.sh e verify.sh ficaram byte a byte iguais
à baseline; a extensão pública está só no read model/transportes. O ajuste de
LotBidPanel limita-se à ausência de ação/aviso recuperável no terminal, sem
nova UI de resultado. README precisou corrigir afirmações antigas de ausência
de scheduler/resultado público e declarar contrato/limites operacionais.

Executei 40 casos backend novos (**40 passed, 1 warning in 7.47s**) e a matriz
T01–40 com regressões. Suíte consolidada anterior:551 passed/35.29s; prova
adicional commit sem publish/restart:2 passed/0.53s. Provas PG usam conexões
independentes e observador de pg_blocking_pids; justiça usa 225 candidatos.
As 8 mutações da spec e uma adicional de settlement no POST vencido foram
detectadas; cada arquivo foi restaurado byte a byte em finally. O leitor de
saída Node de M08 foi corrigido e a mutação reexecutada, sem alegar erro de
coleta/sintaxe como detecção.

Smoke ASGI/WS+PG: sold settlement=1/receipt=1/lot_closed/close 1000; unsold
settlement=1/receipt=0/terminal 1000; restart catch-up antes do tráfego; reconnect
via snapshot terminal sem replay; owners drenados/pool devolvido. Quatro E2E
novos cobrem snapshot terminal, cleanup, REST tardio e offline durante settlement.

Os verifies finais passaram, exit0: backend **2206 passed, 1 warning in126.82s**
e **2206 passed, 1 warning in125.59s**, frontend **179/179** em ambos;
Playwright **226 passed (24.8s),5 skipped**. Lint/formatação (103 arquivos),
tipos, Vite e imagem Docker aprovados. Ambos encerraram com
`verify.sh: todas as etapas passaram.`. Repeti os gates após reforçar T32, sem
alterar produção. Os 5 skips de pilha real continuam opt-in; warning Starlette
conhecido. Primeiro harness teve whitelist/factory/observador a corrigir e uma
execução WS interrompida; os resultados finais não usam essa rodada.

Evidência completa em
`_bmad-output/specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/implementation-evidence.md`.
Sem outbox/replay; SQL pode prolongar ciclo/startup/cleanup além da janela
operacional. Checagem separada somente por nomes:zero .env* alterados; conteúdo
não lido nem comparado. Não houve Git, deploy ou code review nesta sessão.

### Correções LOW da Story 4.4 — F44-01 e F44-02

A IA acrescentou cobertura E2E para a reconciliação pública final após `lot_closed`, inclusive GET bem-sucedido com histórico defasado e falha 503 com aviso existente. No scheduler, limitou a limpeza a 50 IDs de retry por ciclo, removendo somente IDs com settlement persistido e preservando o backoff dos demais. Uma regressão com COMMIT real e confirmação perdida verifica persistência financeira e ausência de duplicações.

As duas mutações focais falharam como esperado e foram revertidas. A suíte 4.4 passou com 41 testes; regressões direcionadas 4.1–4.3, com 153; `./verify.sh` passou com 2207 testes backend e 179 frontend. A primeira tentativa protegida do verify revelou um erro de lint no teste, corrigido antes da rodada final. A Story 4.4 permanece em review; a 4.5 não foi iniciada.

O verify completo com E2E também passou: 2207 backend, 179 frontend, 227 Playwright e 5 skips existentes. Os dois verifies finais usaram as guardas locais contra dotenv.

### Correções de cobertura após re-review da Story 4.4

A IA reforçou o E2E para conferir o preço em `.bid-current` e a permanência do estado terminal. O teste de ACK perdido passou a verificar a identidade do retry pending e a preservação exata do prazo; outro teste cobre a rotação de 60 IDs. As mutações de preço, identidade e prazo foram detectadas nas asserções respectivas, e os arquivos de produção temporariamente modificados foram restaurados byte a byte.

Os três testes focais passaram isoladamente; a suíte 4.4 passou com 42 testes e as regressões 4.1–4.3 com 153. O verify padrão passou com 2208 backend e 179 frontend; o verify com E2E passou com 2208 backend, 179 frontend, 227 Playwright e 5 skips. Repeti o verify padrão para registrar os totais após truncamento da coleta inicial. Usei as guardas contra dotenv; a Story 4.4 permanece em review e não iniciei a 4.5.


### Fechamento final da Story 4.4 — 28/10/2026

Autorizei o fechamento documental: review inicial aprovado com LOWs, sem HIGH
ou MEDIUM; F44-01, F44-02, F44-R01 e F44-R02 resolvidos e rotação acima de 50
retries comprovada. Os gates finais passaram: 42 testes 4.4, 153 regressões,
2208 backend, 179 frontend, 227 Playwright e 5 skips preexistentes. Story,
sprint e SPEC `done`; Epic 4 permanece `in-progress` e 4.5 `backlog`. Nenhuma
suíte foi executada nem código ou teste alterado no fechamento documental.


## Especificação da Story 4.5 — 28/10/2026

Pedi ao Codex somente criar e validar a especificação com bmad-spec, sem código,
testes de aplicação, Git, leitura de .env* ou início do Epic 5. Sol/High constavam
como recomendações do pedido; não atribuo uma troca de modelo não comprovada.

A IA inspecionou as fontes obrigatórias e o código vivo do painel, API privada,
Lot/LotSettlement/Receipt, readers, autenticação/policy, React/formatadores e testes.
Confirmou que /api/lots/mine é uma lista completa por proprietário, sem paginação,
com ordem por criação, snapshot único e sem resultado. Os readers individuais da
4.3 não devem ser chamados em loop: propôs composição estrutural em lote, seguindo
o precedente público da 4.4, sem chamar serviço financeiro ou publicar evento.

Criei story draft e pacote spec-story-4-5-resultado-dos-lotes-no-painel-do-leiloeiro,
com memória append-only via writer oficial, kernel CAP-1–6 e oito companions de
estado atual, dados/API, autorização, UX, refresh, testes, decisões e validação.
QH-01–12 continuam abertas; recomendações não foram aprovadas silenciosamente.
Descobri que o épico original exige total recebido e recebi a questão adicional
QH-13: escolhi **manter uma soma simples de vendidos**, superando a recomendação
da IA de retirar o agregado. A especificação incorpora a soma dos próprios sold,
sem ler wallet ou criar analytics. As demais decisões continuam sob minha revisão.

Planejei CA01–CA12, B01–B24, F01–F22 e E01–E08, incluindo estados, conflitos,
queries constantes, autorização/privacidade, ausência de efeitos e total coerente.
Não executei nenhum desses testes. Fiz somente autovalidação documental em duas
passagens e conferência estática de referências/IDs/tracking/hashes. Isso não é
review independente, prova PG/E2E ou aceite de produto.

Os resolvers BMAD falharam inicialmente por lock no cache padrão do uv e passaram
com cache em /private/tmp, sem necessidade de escalada. Mantive story/SPEC draft,
sprint 4.5 backlog e Epic 4 in-progress. Não reconciliei estados review históricos
das 4.1/4.2: registrei diferença em relação à conclusão informada no pedido.
Não executei código de aplicação, testes, verify, SQL, migrations, navegador, smoke,
deploy ou Git; não li .env*. Código/testes e demais stories foram preservados.

Conferência documental final: exit 0, errors[]; links e companions existentes,
IDs e tracking conferidos. Comparei 213 arquivos da baseline: somente sprint
foi alterado por comentários, sem mudança de status; código/testes e arquivos
protegidos capturados permaneceram idênticos. QH-01–12 abertas, QH-13 decidida;
sem ready-for-dev. Vereditos de coerência/preservação registrados na memória.


## Consolidação e build autorizado da Story 4.5 — 28/10/2026

Decidi QH-01–13 e autorizei consolidação/revalidação e implementação sequenciais,
sem nova confirmação. A IA rederivou a especificação pela memória append-only,
preservou CAP-1–6 e as matrizes B01–24/F01–22/E01–08 e não encontrou conflito AD.
Após o gate documental, promoveu ready-for-dev e iniciou o build autorizado.

A skill bmad-build delegou a implementação; a coordenação conferiu tarefas e
critérios e executou gates e smoke. Não solicitei code review nesta sessão.
Somente lots.py, api/lots.ts, MyLots.tsx e App.css mudaram como produção. Mantive
fonte 4.3, scheduler 4.4, carteira, lances, autenticação e migrations intactos.
A entrega tem resumo persistido, total próprio no mesmo snapshot e montagem/manual/
foco sem polling. Identidade privada, hash, HMAC e receipt ficam fora da resposta.

Resultados reais: 108 testes backend focados passaram em 13.35s; Node, 182;
Chromium focado, 34 em 8.2s. Verifies finais exit 0: 2237 backend em 131.20s e
2237 em 147.69s, frontend 182 em ambos; Playwright 241 em 34.1s, com 5 skips
existentes. Ruff/formato, ESLint, tsc, Vite e Docker passaram. O primeiro par de
gates também passou (2235/182/241+5); repeti os dois após reforçar a prova privada
de unsold+receipt, receipt órfão e ausência de publicação. As FKs de teste foram
restauradas exatamente em finally. O warning Starlette/httpx é preexistente.

Smoke com API real, PostgreSQL exclusivo e Chromium: estados mistos, total de
13000 para 30000, alias/valor, unsold sem vencedor, GET/manual sem efeitos,
settlement externo seguido de manual/foco, stale após 503 e recuperação, 401/403,
e segundo leiloeiro somente com seu lote/total de 7000. Conferi capturas desktop
1440 px e mobile 320 px. Imagens foram interceptadas com 503 para testar fallback.
O navegador integrado não conectou; usei Chromium local. Corrigi imports e a
sincronização do harness antes da prova final; a primeira corrida de sinais não
foi usada como evidência de pureza. O banco exclusivo foi removido. A primeira
rodada E2E também revelou perda de foco do Atualizar, corrigida antes dos gates.
Não validei Render, dispositivo físico ou outros navegadores nesta sessão.

Usei guardas contra dotenv em uv/Python/Node/Compose e execução local elevada
quando o sandbox exigiu. Não executei Git, não li .env*, não fiz deploy nem iniciei Epic 5.
Story/sprint ficam review, SPEC in-review e Epic 4 in-progress. Review independente
da story e agregado do Epic 4 continuam posteriores. A evidência completa fica no
pacote 4.5; frontend/test-results/.last-run.json foi regenerado fora da lista prevista.

Conferência estática final exit 0/errors[]: 27 arquivos alterados, quatro de produção,
links/companions e tracking válidos. Corpo anterior da memória preservado; o timestamp
updated do writer não é parte do conteúdo append-only. Financeiro, contratos públicos,
scheduler, auth, migrations, verify e ADs idênticos à baseline. Nenhum arquivo de
segredo alterado na checagem por nomes; conteúdo não lido nem comparado.


### Fechamento documental da Story 4.5 e do Epic 4 — 28/10/2026

Autorizei o fechamento com review final da Story 4.5 aprovado, 0 HIGH / 0 MEDIUM / 0 LOW, e Epic 4 aprovado para fechamento. A IA registrou Story, sprint e SPEC 4.5 como `done` e Epic 4 como `done`, preservando o histórico. Nesta etapa não alterou código ou testes, não executou testes nem Git, não leu .env* e não iniciou Epic 5.


## Story 5.1 — Auditoria pública — 28/10/2026

Autorizei SPEC, implementação e testes nesta mesma sessão pelo fluxo enxuto,
sem Git, leitura de `.env*`, code review ou checkpoints de aprovação intermediários.
A skill bmad-build foi aplicada com as restrições humanas; a implementação foi
delegada a Sol (`gpt-6.1-sol`, raciocínio medium). A coordenação consolidou a SPEC,
conferiu aceite e executou o gate. Descartei nova fonte de verdade e consulta à AIC.

Entreguei endpoint e página públicos com histórico completo, aliases persistidos,
canonical v1/SHA-256, HMAC interno e validação do settlement/comprovante. Em conflito,
retive todo conteúdo não confiável antes de serializar, inclusive alias privado
injetado. Mantive cancelado distinto de unsold e expirado sem settlement como pending.
Leitura em statement único, sem N+1, escrita, reparo ou liquidação.

Resultados focais reais: PostgreSQL 22 passed (4.29s), contrato/rotas Node 23,
Playwright 13 (3.6s). O gate revelou quatro expectativas de rotas/políticas antigas;
acrescentei audit e a checagem exata do contrato público e confirmei 58 testes
focais (1.56s). Repeti o gate somente por essa falha. A primeira tentativa no
sandbox parou antes dos checks por acesso ao cache uv; a execução autorizada local
resolveu. Uma chamada focal sem banco configurado foi recusada pela guarda.

Gate final `VERIFY_E2E=1 ./verify.sh`, exit 0: 2260 backend (135.04s), 187 Node,
254 Playwright (30.2s), cinco real-stack opt-in ignorados; Ruff/formato, ESLint,
TypeScript, Vite e Docker passaram. Não rodei verify sem E2E nem mutation testing.
O warning Starlette/httpx é preexistente. O Playwright regenerou
frontend/test-results/.last-run.json fora da lista prevista.

Não validei Render, stack real no navegador, dispositivos físicos ou outros
browsers. HMAC continua dependendo da confiança no servidor; histórico completo
não foi paginado. Não alterei ADs, canonical v1, migrations ou regras financeiras.
Não executei Git, deploy ou code review; não li arquivos de segredos. Story/SPEC/
sprint 5.1 ficaram review e Epic 5 in-progress. Não iniciei 5.2/5.3 nem marquei done.
Evidência: `_bmad-output/specs/spec-story-5-1-auditoria-publica/implementation-evidence.md`.

### Review independente final e fechamento da Story 5.1 — 28/10/2026

Autorizei review com Sol (`gpt-6.1-sol`, raciocínio medium) restrito aos 14 riscos
críticos e fechamento imediato sem HIGH/MEDIUM. A IA usou a skill bmad-code-review
com as restrições deste pedido e revisores independentes de backend e frontend/
guards. Resultado: 0 HIGH / 0 MEDIUM / 0 LOW funcional. As quatro expectativas
antigas só incorporaram a rota pública, sem enfraquecer asserções.

Decidi encerrar Story/SPEC/sprint 5.1 como done e manter Epic 5 in-progress;
descartei repetir gates sem suspeita concreta. Nesta etapa não executei testes,
verify, mutation testing ou Git, não li `.env*` nem alterei código/testes.
Não iniciei 5.2/5.3. Registro em
`_bmad-output/implementation-artifacts/code-review-final-story-5-1.md`.

## Story 5.2 — Comprovante compartilhável — 28/10/2026

Autorizei SPEC, implementação e testes pelo fluxo enxuto, sem revisão na sessão, Git ou leitura de segredos. A skill bmad-build foi aplicada respeitando essas restrições; deleguei a implementação a um agente e consolidei a evidência. Decidi reutilizar receipt, settlement e verificação existente; descartei token, PDF e ação de copiar da 5.3.

Testes focais: 67 backend, 20 rotas e 5 Playwright; lint e typecheck passaram. O gate `VERIFY_E2E=1 ./verify.sh` passou com 2269 backend, 188 Node e 259 Playwright, cinco real-stack ignorados; Ruff, formatação, ESLint, TypeScript, build e Docker passaram. Tentativa inicial bloqueada no cache uv; segunda detectou ordem de imports, corrigida e verificada antes da execução aprovada. Smoke de navegador usou API simulada; não validei stack real ou deploy. Story e sprint 5.2 ficaram review, Epic 5 in-progress; não iniciei 5.3 nem executei code review. Detalhes em `_bmad-output/specs/spec-story-5-2-comprovante/implementation-evidence.md`.

### Review curto da 5.2 e definição do escopo da 5.3 — 28/10/2026

Autorizei um fluxo contínuo com review funcional curto da 5.2 e implementação da 5.3, sem Git ou leitura de `.env*`. A IA aplicou bmad-review e iniciou bmad-build. Review estático com leitura independente por agente: sem achados funcionais HIGH/MEDIUM nos 12 riscos solicitados. Decidi concluir Story/SPEC/sprint 5.2 como done e manter Epic 5 in-progress; descartei executar testes sem suspeita concreta. Registro em `_bmad-output/implementation-artifacts/code-review-final-story-5-2.md`. Não houve nova execução de testes ou verify.

A leitura da definição real da 5.3 revelou conflito material: os critérios existentes pedem participações e lotes em apuração, enquanto o fluxo anexado restringe aos sold vencidos pelo usuário. A IA pediu decisão de escopo antes de implementar. Escolhi seguir a story existente: participações e vitórias, comprovante/cópia somente nas vitórias liquidadas. O registro acima corresponde à primeira etapa, antes dessa decisão.

### Implementação da Story 5.3 — 28/10/2026

Autorizei continuar com a story existente após resolver o conflito material. A IA aplicou bmad-build e delegou a implementação a Sol (`gpt-6.1-sol`, raciocínio medium), com SPEC curta e sem nova aprovação para decisões já autorizadas. Decidi reutilizar auth, settlement/receipt, auditoria e snapshot local; descartei reconstruir vitória por bids, backend de compartilhamento, token e PDF.

Entreguei `GET /api/me/wins` BIDDER e `/bidder/wins` com participações/estados e vitórias persistidas, comprovante e cópia do link público com fallback. Focais reais: 68 backend (PostgreSQL/políticas/OpenAPI), 24 Node e 6 Playwright; Ruff, ESLint focal e TypeScript aprovados. O PostgreSQL local exigiu execução autorizada fora do sandbox.

Executei uma vez `VERIFY_E2E=1 ./verify.sh`, exit 0: 2278 backend (139.79s), testes Node aprovados, 265 Playwright (28.6s), cinco real-stack opt-in ignorados; Ruff/formato, ESLint, TypeScript, Vite e Docker passaram. Não executei verify separado, mutações, Git, review da 5.3 ou leitura de segredos. Conferi tarefas/aceites por diff sem Git; Playwright regenerou `frontend/test-results/.last-run.json` fora da lista prevista.

Story/sprint 5.3 em review, SPEC in-review, Epic 5 in-progress. E2E com API simulada, sem UI contra stack real ou deploy; lista sem paginação e validação estrutural como 4.5. Evidência: `_bmad-output/specs/spec-story-5-3-meus-arremates/implementation-evidence.md`.

### Review independente 5.3, agregado e fechamento documental Epic 5 — 28/10/2026

Autorizei uma única sessão de revisão curta 5.3, seguida do agregado se não houvesse HIGH/MEDIUM e fechamento somente documental se ambos fossem aprovados. Modelo/raciocínio solicitados: Sol/Medium; a sessão não aferiu identificador efetivo do runtime. A IA aplicou bmad-review com foco nos riscos funcionais listados e segunda leitura independente por agente em cada etapa. Ambos os reviews: 0 HIGH / 0 MEDIUM / 0 LOW funcional, sem achados reais de integração. Descartei ampliar cobertura ou repetir gates sem suspeita concreta.

Decidi concluir Story/sprint 5.3 done, SPEC final e Epic 5 done, conforme meu pedido explícito. O done do épico registra exceção documental ao processo canônico; não prova merge, deploy ou smoke público. Aprovação técnica de commits 5.2/5.3 e merge limitada aos arquivos vivos inspecionados, sem Git ou diff histórico. Nenhum código/teste foi alterado; não houve execução de testes, verify ou mutações, nem leitura de `.env*`. Preservei a evidência anterior e seus limites. Não iniciei Epic 6. Registros: `_bmad-output/implementation-artifacts/code-review-final-story-5-3.md` e `code-review-epic-5.md`.

## Preparação da Story 6.1 — Revisão de segurança e de erros — 28/10/2026

Solicitei exclusivamente a especificação com `bmad-spec`, sem implementação.
A IA confrontou fontes vivas, registradores HTTP, proteções, fluxos e testes
existentes. A extração estática dos registradores confirmou seis POST e nenhum
PUT/PATCH/DELETE; não houve import da aplicação nem leitura de `.env*`.
Decidi preservar as ADs e reaproveitar middleware, sessão, erros, snapshots,
proxy e provas atuais; descartei refatoração geral e duplicação de suítes.

A spec propõe completar as células de Content-Type sem evidência por rota,
provar sala REST/WS sob falha externa explícita e ampliar os casos existentes
de fallback no navegador. Q7 continua resolvida pelo smoke da 2.3; a 6.1
complementa a prova de continuidade dos fluxos. Mantive separadas a produção
histórica `3d3ea97`, a base atual informada `8a460d26bb280e5a35379254a82b73c3224813a1`
e a futura publicação a confirmar. A inspeção pública de cookie/CORS e a
validação final do candidato continuam pendentes, também para a 6.4.

Não houve código/teste alterado, execução de pytest/Playwright/verify/smoke,
Git/gh ou deploy. Não invoquei `bmad-build` nem promovi o sprint. Não foi
identificada decisão humana técnica pendente; a revisão/aprovação da spec e a
liberação de código continuam comigo. Artefatos em
`_bmad-output/specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/`.

## Implementação da Story 6.1 — Revisão de segurança e de erros — 28/10/2026

Autorizei exclusivamente a implementação da spec consolidada com `bmad-build`,
minimum diff e revisão independente posterior. A IA trabalhou como Codex,
com delegação de implementação exigida pelo workflow; não atribuo um modelo
específico ao runtime sem confirmação. Autorizei runtime exclusivo da 6.1
para preservar integralmente a baseline histórica da 4.2.

Decidi centralizar as provas de Origin/Content-Type no app real, com matriz
exata das seis escritas, controle positivo e sentinela de despacho antes das
dependências/handler. Descartei espalhar complementos equivalentes por várias
suítes. Preservei os testes autenticados/transacionais existentes, sessão,
CSRF, 422 e código de produção. Ampliei as provas REST/WS sem AIC, controle de
mídia 503, fallback de vitrine/sala/comprovante e navegação à auditoria;
reforcei igualdade do 500 e debug falso sem criar endpoint de crash.

O candidato inicial `8a460d26bb280e5a35379254a82b73c3224813a1` veio de
confirmação externa recebida no pedido; não atribuo a confirmação ao usuário
nem a trato como prova de deploy. A validação usou cópia isolada sem `.env*`,
credenciais ou Git, fontes conferidas por SHA-256, valores locais fictícios e
PostgreSQL `_test`; não alterei conftest/configuração para dotenv. A primeira
tentativa focal parou antes do pytest por lock do cache do uv no sandbox
(exit 2); a reexecução autorizada passou.

Resultados efetivamente executados: três comandos `uv run pytest` focais
com 477, 197 e 234 testes aprovados, todos exit 0; Playwright focal das cinco
suítes vitrine/sala/WS/auditoria/comprovante com 115 passed, exit 0; gate
`./verify.sh` completo exit 0, 2314 pytest e 192 Node, Ruff/formato,
ESLint/TypeScript, Vite e Docker aprovados. Não repeti verify com E2E, pois
executei o browser focal exigido. Preservei os avisos existentes no registro,
sem correção oportunista. Nenhum defeito de produto foi revelado.

Deixei Story/sprint 6.1 em **review**, SPEC **in-review** e Épico 6
**in-progress**. CA2 local está comprovado; cookie emitido pelo deploy,
borda/proxy/CORS publicado e commit efetivamente implantado seguem pendentes.
Playwright usa API simulada, complementada por ASGI/PostgreSQL; não executei
real-stack opt-in, deploy, Git/gh ou code review, nem aleguei auditoria completa
dos logs. Não iniciei 6.2. Comandos completos, arquivos e limites em
`_bmad-output/specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/implementation-evidence.md`.

## Correção R6.1-01 da Story 6.1 — 28/10/2026

Autorizei exclusivamente `bmad-build` para corrigir o MEDIUM apontado pelo
review independente. A IA delegou a implementação do teste conforme o workflow;
não executou code review. Decidi descobrir escritas pela estrutura HTTP real,
antes da validação de políticas, e descartei alterar produto ou criar exceção
por caminho. O mapa anterior omitia rotas sem política efetiva; a tolerância
documental de `policy_problems` permitia que sete escritas parecessem seis.

Alterei somente `backend/tests/test_csrf.py` entre os arquivos executáveis.
O inventário bruto agora independe de `AccessPolicy`/`policy_by_route`, mantém
todos os métodos de escrita e reprova superfícies não inspecionáveis. A
regressão injeta POST sem política em `/api/docs`, `/api/openapi.json` e caminho
inesperado, com/sem SPA e Route/APIRoute: exige descoberta da sétima escrita e
falha da mesma validação CA1. Preservei os 36 negativos e controles positivos.

Executei primeiro o focal de regressão: **29 passed**, exit 0; depois suítes
CSRF/políticas/autenticação e escritas CA1: **533 passed**, exit 0. Renovei o
`./verify.sh` completo, exit 0: **2343 pytest** (138.38s), **192 Node**, Ruff,
formatação, ESLint, TypeScript, Vite e Docker aprovados. Usei cópia isolada sem
dotenv/credenciais, PostgreSQL `_test` e hashes das 250 fontes reconferidos.
Restaurei o bind mount original do PostgreSQL após o gate, exit 0/Healthy,
preservando o volume. Playwright CA3 anterior permaneceu independente e não
foi repetido. O único warning foi o já existente de Starlette/httpx.

Atualizei SPEC, auditoria, evidência, story, adendo de correção do review e
este registro. R6.1-01 está **corrigido pelo implementador/aguardando re-review**,
sem aprovação pelo reviewer. Mantive Story/sprint `review`, SPEC `in-review`,
Épico 6 `in-progress` e CA2 publicado pendente. Não alterei produto, frontend,
configuração ou `conftest.py`, nem iniciei 6.2 ou fiz deploy.

Registrei uma violação de processo: a IA executou `git status --short` antes
de ler o anexo com o pedido. A consulta foi somente de leitura e não alterou
arquivos; depois disso não executou Git/gh. Não houve leitura de `.env*`,
credenciais ou exposição de segredos/cookies/tokens reais. Evidência completa:
`_bmad-output/specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/implementation-evidence.md`.

## Especificação da Story 6.2 — 28/10/2026

Usei Codex com a skill local `bmad-spec` para preparar exclusivamente identidade
visual e responsividade. Decidi auditar o frontend vivo antes de propor mudanças;
descartei reescrever telas já conformes ou usar referências como autorização para
funcionalidades novas. Contrato completo em
`_bmad-output/specs/spec-story-6-2-identidade-visual-e-responsividade/`:
kernel, estado atual, mudanças mínimas e matrizes/plano de provas.

A IA leu as fontes obrigatórias, componentes/tokens, testes frontend e artefatos
das telas. Inspecionou as seis telas e login em Chromium a 1440/768/375/320, com
API simulada, volumes e textos adversos; também percorreu a criação e conferiu
três proporções de imagem com arquivos locais existentes. Não apareceu overflow
global nas amostras; isso não comprova aceite visual de todos os estados. Foram
identificados gaps de hierarquia do timer/títulos, links com estilo padrão do
navegador, alvos em arremates, microcopy e provas faltantes. Nenhum código de
produto ou teste foi implementado/alterado.

Autorizei incluir a correção de apresentação da Sala: ended+pending mantém
“Encerrado, apurando resultado”; ended+settled mostra “Encerrado”, preservando
resultado recebido. Descartei mudar genericamente phaseStatusText(ended) ou alterar
backend/settlement. A SPEC registra a expectativa legada da 4.4 desatualizada e
exige provar os dois estados no futuro build, mantendo as regressões terminais.
Enviei também a imagem ÁTRIO com o hero marcado; ela confirma a composição e o
fade, sem autorizar copiar ativos ou controles da referência.

A IA confirmou as três contas públicas no seed/README e a ausência de endpoint
real de cadastro. Especificou login demo pelo fluxo existente, sem sessão paralela;
cadastro ficou apenas como candidata funcional separada, sem tela/link morto.
Dos benchmarks públicos, Vercel e Railway abriram e foram usados somente para
responsividade; Render mostrou apenas 503/Application loading. Não houve login
nesses serviços nem cópia de sua identidade/conteúdo.

Baseline realmente executada: lint e typecheck exit 0, npm test 192 pass/0 fail,
npm run build exit 0, Playwright 265 passed/5 skipped em 34,9 s, exit 0. Os skips
são real-stack opt-in. A primeira tentativa Playwright parou por bind EPERM;
a reexecução permitida passou. O navegador integrado não conectou; as sondas
usaram Playwright já instalado e dados simulados, com evidências temporárias.
Não executei verify completo/backend/PostgreSQL/Docker, real-stack ou deploy
nesta especificação. Esses resultados são baseline, não prova do futuro build.

Mantive a 6.1 intocada em review, com o gate publicado reservado a deploy/6.4,
e a 6.2 em backlog no sprint. Não iniciei 6.3, não chamei bmad-build, não executei
Git/gh/commit/push/merge/deploy nem li .env* ou credenciais privadas. A SPEC aguarda
minha revisão integral e autorização posterior de implementação.


## Build da Story 6.2 — 28/10/2026

Autorizei Codex com `bmad-build` para implementar exclusivamente a SPEC aprovada
com minimum diff. Decidi refinar o hero ÁTRIO, antecipar o único timer da Sala,
corrigir QH-01 nas duas regiões visíveis, explicar os campos monetários e oferecer
três contas demo pelo login existente. Descartei redesign geral, cadastro,
autenticação alternativa, backend novo e funcionalidades de outras stories.

A implementação foi delegada conforme a skill. O subagente atingiu limite de uso
após os focais; o agente principal conferiu o diff sem Git, completou um ajuste de
foco do login manual após falha demo e executou a verificação final. Preservei a
baseline da 4.2 e autorizei uma pasta exclusiva de baseline para a 6.2. Nenhum
code review independente foi executado.

Implementei hero 40/60 com branco e fade estreito condicionado a imagem paisagem
carregada; retrato/quase quadrada/fallback/mobile ficam sem efeito. A obra continua
em contain, sem alteração de bytes nem download decorativo. Mantive o h1 integral
da Sala, a mesma anchor/onZero e a lógica REST/WS. Pending diz “Encerrado, apurando
resultado”; settled sold/unsold diz “Encerrado” nas duas regiões, sem “apurando”.
MoneyField acumula descrição+dica+feedback, e manual/demos compartilham uma guarda
síncrona. Carteira/Painel ficaram estruturalmente intactos.

Resultados reais: focal inicial 174 passed/4 falhas de seletor novo de criação,
corrigidas sem mudar a interface; focal final 240 passed; focal de sessão após
ajuste final 25 passed, exit 0. `VERIFY_E2E=1 ./verify.sh` final exit 0: 2343 pytest,
192 Node, 291 Playwright passed/5 skipped real-stack opt-in, Ruff/formato,
ESLint/TypeScript, Vite e Docker aprovados. Executei em cópia isolada sem dotenv,
com PostgreSQL de teste e fontes conferidas por SHA-256 (256 arquivos, zero
divergências). Restaurei o mount original do PostgreSQL, Healthy/exit 0.

A sonda estrutural mediu 28 cenários sem overflow global/descendentes críticos fora
do viewport. Preparei screenshots temporárias do hero 1440/768/375/320, Sala,
login e criação com obras locais e API simulada. O navegador integrado não
conectou; usei Playwright existente. Os focais tiveram bloqueio inicial EPERM na
porta local, superado pela execução permitida; a primeira captura teve seletor
incorreto do searchbox, corrigido apenas no script temporário.

Mantenho a 6.2 in-progress aguardando meu aceite visual; não declaro done nem pronta
para review independente. Preservei 6.1 review, Épico 6 in-progress e 6.3 backlog.
Não executei Git/gh/commit/push/merge/deploy nem li dotenv/credenciais privadas.
Não houve regressão funcional nos gates; produção e aceite humano não são
inferidos deles. Evidência completa, arquivos e limites em
`_bmad-output/specs/spec-story-6-2-identidade-visual-e-responsividade/implementation-evidence.md`.


### Story 6.2 — polimento das seções antes do aceite visual

Solicitei indicadores decorativos discretos na Vitrine: ponto roxo respirando
em 1,8s apenas em Ao vivo, relógio lilás estático em Próximos lotes e ponto
avermelhado estático em Encerrados. Decidi usar CSS com markup mínimo e
aria-hidden; descartei glow, biblioteca de ícones e animação contínua no relógio.
A preferência de movimento reduzido remove a animação mantendo indicador/textos.

Codex alterou App.css, LotRail.tsx, ClosedLots.tsx e o focal vitrine.spec.ts.
Lint/typecheck passaram (exit 0); Playwright vitrine/layout/keyboard: 60 passed
em 6.9s, exit 0. O teste novo prova nomes acessíveis, decoração oculta da árvore
acessível, ausência de mudança da caixa e desligamento da animação em reduced motion.
Screenshots novas em 1440×900,375×812,320×812 usam API simulada/obras locais e
não mostram overflow global. Versões completas incluem as três seções.

Não repeti verify completo nesta rodada, conforme solicitei para avaliar primeiro
a estética. O gate anterior não comprova este novo candidato; após meu aceite
visual será necessário renová-lo antes do code review independente. Mantenho
Story/SPEC/sprint in-progress e não iniciei review ou outra story. Evidências e
caminhos temporários no adendo de implementation-evidence.md da 6.2.

### Story 6.2 — refinamento final dos indicadores

Aprovei o primeiro polimento e solicitei a respiração roxa em todas as ocorrências
Ao vivo da Vitrine, incluindo hero/itens, e vermelho mais evidente com fade lento
em Encerrados. A instrução nova substituiu minha preferência anterior por vermelho
estático. Codex alterou apenas App.css e o focal vitrine.spec.ts, além dos registros.
Decidi reaproveitar os marcadores aria-hidden e o token danger, sem novo markup,
dependência ou cor neon. Ao vivo respira em 1,8s; Encerrados varia só opacidade
entre 1 e 0,85 em 2,8s. O relógio lilás permanece estático e reduced motion remove
ambas as animações. A Sala não recebe a animação restrita à Vitrine.

Lint/typecheck exit 0; Playwright vitrine/layout: 51 passed,7.0s,exit 0.
O teste cobre todos os pontos ao vivo da fixture, ritmo lento de Encerrados,
movimento reduzido e isolamento da Sala. Screenshots novas do primeiro viewport
e página completa em 1440/375/320 não apresentam overflow global. Registrei os
caminhos no adendo de implementation-evidence.md da 6.2. Não repeti verify completo
nem iniciei review; aguardo meu aceite visual final antes de renovar os gates.


### Story 6.2 — aceite visual FINAL e gate pós-build

Concedi o aceite visual humano FINAL de hero ÁTRIO, responsividade, Sala,
microcopy, login demo e indicadores finais. Aprovei a respiração roxa de 1,8s
em todas as ocorrências pertinentes de Ao vivo na Vitrine, o vermelho mais
evidente com fade contido de 2,8s em Encerrados e o relógio lilás estático em
Próximos. A preferência reduced motion desliga as animações decorativas, com
textos/indicadores preservados. Proibi novos ajustes visuais por iniciativa da IA.

Codex executou novamente `VERIFY_E2E=1 ./verify.sh` completo após esse aceite,
sem corrigir ou alterar código/testes. Resultado real: **exit 0**, **2343 pytest
passed** (um warning preexistente, 138.46s), **192 Node pass/0 fail/0 skipped** e
**292 Playwright passed/5 skipped** (30.6s). Ruff e formatação (110 arquivos),
lint, typecheck, build Vite e Docker passaram. Nenhuma regressão foi observada.
O teste dos indicadores/reduced motion integrou essa execução completa.

Decidi manter a execução na raiz de uma cópia isolada idêntica sem dotenv/
credenciais, como no gate anterior, para evitar os loaders automáticos. Foram
conferidos 256 arquivos por SHA-256, sem divergência entre o candidato original
e a cópia. Usei PostgreSQL de teste e valores locais fictícios documentados;
restaurei depois o bind mount original, Healthy/exit 0, preservando o volume.

Atualizei somente SPEC/evidência/artefato/sprint da 6.2 e este registro. Deixei
Story/sprint **review**, SPEC **in-review**, pronta para review independente;
não executei esse review nem marquei done. Mantive 6.1 review, Épico 6 in-progress
e 6.3 backlog. Os cinco real-stack opt-in não executados e a ausência de prova
publicada continuam limitações explícitas. Não executei Git/gh/commit/push/merge/
deploy ou leitura de dotenv. Evidência vigente no adendo final de
`_bmad-output/specs/spec-story-6-2-identidade-visual-e-responsividade/implementation-evidence.md`.

