# Uso de IA no desenvolvimento — Casa de Leilões

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

