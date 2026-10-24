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

