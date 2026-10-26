# Uso de IA no desenvolvimento — ÁTRIO (antes Casa de Leilões)

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
