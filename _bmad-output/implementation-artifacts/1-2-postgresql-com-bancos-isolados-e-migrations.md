# Story 1.2: PostgreSQL com bancos isolados e migrations

Status: review

Chave do sprint: `1-2-postgresql-com-bancos-isolados-e-migrations`
Épico: 1 (Fundação e aplicação publicada), Dia 2 (23/10) do cronograma.
Decisões D1 a D8 e Python 3.13 fechadas por mim em 23/10/2026 (seção
"Decisões registradas").

## Story

Como desenvolvedor,
quero um PostgreSQL local com bancos de desenvolvimento e de teste separados,
conexão configurada pelo ambiente e esquema controlado por migrations,
para que toda story seguinte grave dados de forma rastreável e teste em
PostgreSQL real sem tocar nos dados de desenvolvimento.

## Objetivo e contexto

A Story 1.1 entregou o monorepo com FastAPI (`GET /health` estático), front-end
React + Vite + TypeScript e `verify.sh` fail-fast, mas sem banco. Esta story
acrescenta só a infraestrutura de persistência:

- PostgreSQL 18 local em Docker Compose (`compose.yaml` na raiz), com um único
  contêiner e dois bancos: `casa_de_leiloes_dev` e `casa_de_leiloes_test`
  (AD-17, AD-27);
- conexão por SQLAlchemy 2.x síncrono + psycopg 3, com a URL vinda de
  `DATABASE_URL` / `TEST_DATABASE_URL`, lidas por `pydantic-settings` (AD-2);
- Alembic em `backend/migrations/`, com uma revisão inicial vazia (as tabelas
  de domínio nascem nas stories que precisam delas);
- testes de integração em PostgreSQL real dentro do `verify.sh`, que sobe o
  banco e falha de forma explícita se ele não ficar pronto.

Ela é a base da Story 1.3 (o contêiner da aplicação aplica migrations antes do
tráfego) e da 1.4 (migrations no banco de produção do Render). Nada de domínio
entra aqui.

## Critérios de aceite

CA1 a CA6 vêm do `epics.md`; CA7 a CA10 explicitam as decisões desta story.

1. **CA1 – Bancos distintos.** Dado o repositório clonado e o Docker disponível,
   quando sigo o passo do `README.md` (`docker compose up -d --wait postgres`),
   então existem `casa_de_leiloes_dev` e `casa_de_leiloes_test` no mesmo
   contêiner, e nenhum teste escreve em `casa_de_leiloes_dev`.
2. **CA2 – Configuração pelo ambiente.** Dado o back-end, quando ele inicia ou os
   testes rodam, então a URL vem de `DATABASE_URL` (aplicação e migrations) ou
   `TEST_DATABASE_URL` (testes), lidas por uma configuração central com
   `pydantic-settings`; nenhum segredo ou credencial real está versionado;
   `backend/.env.example` contém só nomes e valores fictícios.
3. **CA3 – Migrations.** Dado um banco vazio, quando executo
   `uv run alembic upgrade head` em `backend/`, então o esquema chega à última
   revisão sem erro, e a revisão inicial é vazia (nenhuma tabela além de
   `alembic_version`).
4. **CA4 – Esquema de teste vindo das migrations.** Dada a suíte de integração,
   quando ela prepara o banco de teste, então o esquema vem de
   `alembic upgrade head` (nunca de `metadata.create_all()`); pelo menos um teste
   executa uma consulta real no PostgreSQL via `Session` síncrona + psycopg 3;
   nenhum teste usa SQLite.
5. **CA5 – `verify.sh`.** Dado `verify.sh`, quando o executo, então ele roda
   `docker compose up -d --wait postgres` antes dos testes, aplica as migrations
   num banco de teste limpo e roda a integração em PostgreSQL real; se Docker,
   Compose ou o PostgreSQL não ficarem prontos, falha com mensagem clara, sem
   pular testes em silêncio. O contêiner não é derrubado ao final.
6. **CA6 – `/health` preservado.** Dada a aplicação, quando chamo `GET /health`,
   então recebo 200 com exatamente `{"status": "ok"}`, sem consultar o
   PostgreSQL. Não existe `/health/db`.
7. **CA7 – Proteção contra o banco errado.** Dada a suíte de testes, antes de
   qualquer operação destrutiva, quando `TEST_DATABASE_URL` falta, é igual a
   `DATABASE_URL` ou aponta para um banco cujo nome não termina em `_test`, então
   a sessão de testes aborta com mensagem clara e nada é apagado.
8. **CA8 – Normalização da URL.** Dada uma URL `postgresql://...` (formato do
   Render), quando a configuração cria o engine, então o dialect usado é
   `postgresql+psycopg`, com usuário, senha, host, porta, banco e query
   parameters preservados; a conversão manipula a URL por componentes, nunca por
   substituição genérica de texto.
9. **CA9 – Versão alinhada ao Render.** Dado o `compose.yaml`, quando o inspeciono,
   então a imagem é `postgres:18` e o volume persistente está montado em
   `/var/lib/postgresql` (não em `/var/lib/postgresql/data`).
10. **CA10 – Hora do banco disponível.** Dado o teste de integração, quando ele
    executa `SELECT clock_timestamp()`, então recebe um `datetime` com fuso
    (base para AD-6/AD-26). Nenhuma função de domínio de hora é criada.

## Tarefas e subtarefas

- [x] **T1 – PostgreSQL local (CA1, CA9)**
  - [x] T1.1 `compose.yaml` na raiz com o serviço `postgres`, imagem `postgres:18`.
  - [x] T1.2 Volume nomeado montado em `/var/lib/postgresql`.
  - [x] T1.3 Script em `docker-entrypoint-initdb.d` que cria
        `casa_de_leiloes_dev` e `casa_de_leiloes_test`.
  - [x] T1.4 Healthcheck com `pg_isready` (necessário para o `--wait`); porta
        publicada só em `127.0.0.1`.
  - [x] T1.5 Credenciais do Compose fictícias, só para uso local, e iguais às do
        `backend/.env.example`; nenhuma credencial real.
- [x] **T2 – Dependências do back-end (AD-2, AD-28)**
  - [x] T2.1 `uv add sqlalchemy alembic "psycopg[binary]" pydantic-settings`
        (SQLAlchemy 2.x, psycopg 3.x).
  - [x] T2.2 `uv.lock` atualizado pelo próprio `uv`.
- [x] **T3 – Configuração e conexão (CA2, CA8)**
  - [x] T3.1 `backend/app/config.py`: `pydantic-settings` com `DATABASE_URL`
        (obrigatória para aplicação e migrations) e `TEST_DATABASE_URL` (usada só
        pelos testes); lê o ambiente e, se existir, `backend/.env`.
  - [x] T3.2 Função de normalização da URL por componentes (ver Notas): aceita
        `postgresql` e `postgresql+psycopg`; recusa qualquer outro driver com erro
        claro.
  - [x] T3.3 `backend/app/db.py`: `Engine` síncrono, `sessionmaker`/`Session`,
        `Base` declarativo com `MetaData(naming_convention=...)`. Sem modelos.
  - [x] T3.4 `backend/.env.example` com valores fictícios.
  - [x] T3.5 `.gitignore` já cobre `.env`/`.env.*` e libera `.env.example`;
        só conferir, nunca ler um `.env` real.
- [x] **T4 – Alembic (CA3)**
  - [x] T4.1 `alembic init` em `backend/migrations/`; `alembic.ini` em `backend/`
        sem URL fixa.
  - [x] T4.2 `env.py` usa a URL normalizada da configuração central e
        `target_metadata = Base.metadata`.
  - [x] T4.3 Revisão inicial vazia (`upgrade`/`downgrade` sem operações).
- [x] **T5 – Testes (CA4, CA5, CA7, CA8, CA10)**
  - [x] T5.1 `backend/tests/conftest.py`, no início da sessão de integração, nesta
        ordem: (1) validar o alvo (CA7); (2) `DROP SCHEMA public CASCADE` +
        `CREATE SCHEMA public`; (3) `alembic upgrade head` programático contra
        `TEST_DATABASE_URL`; (4) só então os testes.
  - [x] T5.2 Banco de teste inacessível falha a sessão com mensagem que indica o
        `docker compose up -d --wait postgres`; nunca `pytest.skip`.
  - [x] T5.3 Integração: `SELECT clock_timestamp()` por `Session` síncrona devolve
        `datetime` com `tzinfo`.
  - [x] T5.4 Integração: `alembic_version` está no head e `public` não tem outras
        tabelas.
  - [x] T5.5 Integração: o dialect/driver efetivo do engine é
        `postgresql`/`psycopg`.
  - [x] T5.6 Unitário: normalização preserva usuário, senha (inclusive com
        caracteres especiais codificados), host, porta, banco e query parameters;
        `postgresql+psycopg` passa intacto; outro driver é recusado.
  - [x] T5.7 Unitário: a guarda aborta com URL de teste ausente, igual à de dev ou
        sem sufixo `_test`.
  - [x] T5.8 `test_health.py` continua passando sem alteração.
- [x] **T6 – `verify.sh` (CA5)**
  - [x] T6.1 Depois de Ruff e `ruff format --check`, executar
        `docker compose up -d --wait postgres` a partir da raiz; em falha,
        mensagem clara e saída não zero.
  - [x] T6.2 `pytest` com `TEST_DATABASE_URL` disponível; manter
        `set -euo pipefail` e a ordem fail-fast; não derrubar o contêiner.
- [x] **T7 – Documentação**
  - [x] T7.1 `README.md` mínimo na raiz: só subir o banco, aplicar migrations,
        rodar os testes e o `verify.sh`, e recriar o volume
        (`docker compose down -v`). O README completo é de story futura.
  - [x] T7.2 Atualizar `docs/uso_de_ia.md` com a Story 1.2.
- [ ] **T8 – Fechamento**
  - [x] T8.1 Rodar `verify.sh` completo e mostrar a saída real.
  - [ ] T8.2 Registrar uma execução real com o banco parado, mostrando a falha
        clara (CA5).
  - [x] T8.3 Parar e avisar. Sem git.


## ADs aplicáveis

- **AD-2:** PostgreSQL; SQLAlchemy 2.x síncrono (`Session`); Alembic; psycopg 3.
- **AD-17:** testes críticos em PostgreSQL real; banco de teste isolado.
- **AD-27:** `verify` fail-fast com integração em PostgreSQL real; PostgreSQL de
  teste em Docker/Compose; nunca SQLite.
- **AD-28:** monorepo, `uv`; sem estado no filesystem do contêiner da aplicação
  (o volume do Compose é só do banco local).
- **AD-14 (indireto):** PostgreSQL 18, igual ao padrão do Render; `GET /health`
  segue como liveness.
- **AD-6/AD-26 (indireto, só CA10):** `clock_timestamp()` chega como `datetime`
  com fuso; nenhuma regra de hora é implementada.
- **AD-30:** nomes de código, banco e variáveis em inglês.
- **AD-25 (restrição):** nenhuma operação bloqueante de banco no event loop; nesta
  story nenhuma rota HTTP usa o banco.

## Dependências da Story 1.1

Estado real lido no código:

- `backend/pyproject.toml`: Python `>=3.13`; deps `fastapi`, `uvicorn[standard]`;
  dev `pytest`, `httpx`, `ruff`; Ruff `E,F,I,UP,B`, `line-length=88`;
  `testpaths = ["tests"]`. `backend/.python-version` = `3.13`.
- `backend/app/main.py`: `GET /health` → `{"status": "ok"}`, sem banco.
- `backend/tests/test_health.py`: um teste com `TestClient`.
- `verify.sh` (raiz): Ruff check → `ruff format --check` → `pytest` → ESLint →
  typecheck → build do Vite; `set -euo pipefail`; não sobe Docker.
- `.gitignore`: ignora `.env` e `.env.*`, libera `.env.example`.
- Não existem Compose, Dockerfile, `README.md` na raiz, Alembic nem módulo de
  banco.
- Herdado: `StarletteDeprecationWarning` do `httpx` com o `TestClient` (fora de
  escopo).

## Arquivos e áreas afetados

| Área | Arquivo | Ação |
| --- | --- | --- |
| Banco local | `compose.yaml` (raiz) e script de init dos dois bancos | novo |
| Configuração | `backend/.env.example` | novo |
| Dependências | `backend/pyproject.toml`, `backend/uv.lock` | alterado |
| Config | `backend/app/config.py` | novo |
| Conexão | `backend/app/db.py` | novo |
| Migrations | `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/<rev>_baseline.py` | novo |
| Testes | `backend/tests/conftest.py`, testes unitários de config/guarda, `backend/tests/integration/test_database.py` | novo |
| Verify | `verify.sh` | alterado |
| Docs | `README.md` (raiz, mínimo), `docs/uso_de_ia.md` | novo / alterado |
| Sem mudança | `backend/app/main.py`, `backend/tests/test_health.py` | intocados (D6) |

## Testes esperados

| Teste | Tipo | Prova |
| --- | --- | --- |
| `GET /health` → 200 `{"status": "ok"}` | unitário (existente, intocado) | CA6 |
| `SELECT clock_timestamp()` por `Session` síncrona devolve `datetime` com fuso | integração, PostgreSQL real | CA4, CA10 |
| `alembic_version` no head; `public` sem outras tabelas | integração | CA3, CA4 |
| Dialect/driver efetivo `postgresql`/`psycopg` | integração | CA4, CA8 |
| Normalização preserva componentes; recusa outro driver | unitário | CA8 |
| Guarda aborta (ausente, igual a dev, sem `_test`) | unitário | CA1, CA7 |
| Banco parado → `verify.sh` falha com mensagem | execução manual registrada com saída real | CA5 |

Nenhum teste de domínio, de concorrência ou de travas: eles nascem nas stories
3.x e 4.x.

## Como a story entra no `verify.sh`

```
Backend: Ruff check
Backend: Ruff format --check
Infra:   docker compose up -d --wait postgres   ← falha clara se Docker/Compose/PostgreSQL faltarem
Backend: pytest (unitários + integração; schema public recriado + alembic upgrade head no banco _test)
Frontend: lint → typecheck → build
```

O contêiner fica de pé ao final. Os testes de integração nunca usam `skip` por
falta de banco: o `conftest.py` falha a sessão com mensagem, inclusive quando o
`pytest` roda fora do `verify.sh`.

## Fora de escopo

- Qualquer tabela ou modelo de domínio (`users`, `wallets`, `lots`, `bids`,
  `receipts`), CHECKs de dinheiro, seed (AD-24).
- Autenticação, papéis, lotes, carteira, lances, WebSocket, scheduler, catch-up.
- Checagem do banco no `/health` e rota `/health/db` (D6).
- Dockerfile multi-stage, servir a SPA, migrations na inicialização do contêiner
  (Story 1.3).
- Deploy no Render, banco de produção, README completo (Stories 1.4 e 6.3).
- Formato único de erro e validação de `Origin` (Story 2.1).
- Isolamento por teste (rollback ou truncamento) para testes que gravam dados:
  decidido quando o primeiro deles chegar.
- A aplicação dentro do Compose: só o PostgreSQL fica nele.
- Correção do `StarletteDeprecationWarning`.

## Decisões registradas

Todas tomadas por mim em 23/10/2026.

### D1 – PostgreSQL 18
**Decidi** usar PostgreSQL 18, a mesma versão principal em desenvolvimento, teste
e produção.
**Por quê:** é a versão padrão do Render para bancos novos, então não há escolha
manual que eu possa esquecer na Story 1.4 e os ambientes não divergem.
**Descartei:** 17 (exigiria escolher a versão manualmente no Render, com risco de
divergência) e 16 (mais antiga, sem ganho).
**Consequência:** a imagem oficial 18 exige o volume em `/var/lib/postgresql`, não
no antigo `/var/lib/postgresql/data`.

### D2 – `compose.yaml` na raiz e `README.md` mínimo
**Decidi** pôr o `compose.yaml` na raiz do repositório e criar um `README.md`
mínimo na raiz, só com as instruções do banco local desta story.
**Por quê:** fica ao lado do `verify.sh` e do futuro `Dockerfile` (AD-28), e o
README é onde o avaliador procura o passo documentado do CA1.
**Descartei:** `backend/compose.yaml` (exigiria `-f` ou `cd` no `verify.sh` e no
README) e `infra/compose.yaml` (pasta que a AD-28 não prevê). Também descartei
deixar o passo documentado só em `docs/`.

### D3 – Um contêiner, dois bancos
**Decidi** usar um único contêiner PostgreSQL com `casa_de_leiloes_dev` e
`casa_de_leiloes_test`. Os testes nunca escrevem no banco de desenvolvimento.
**Por quê:** cumpre o banco de teste dedicado e isolado do AD-27 com o menor custo
(um contêiner, uma porta).
**Descartei:** dois serviços (mais configuração sem ganho agora) e um banco com
dois esquemas (isolamento fraco, contraria o AD-27).

### D4 – `DATABASE_URL`, `TEST_DATABASE_URL`, `pydantic-settings`, normalização e guarda
**Decidi:**
- variáveis `DATABASE_URL` e `TEST_DATABASE_URL`;
- configuração central com `pydantic-settings`;
- `backend/.env.example` só com valores fictícios;
- psycopg 3 explícito: a URL `postgresql://...` do Render é normalizada para o
  dialect `postgresql+psycopg` antes de criar o engine, por componentes da URL e
  preservando usuário, senha, host, porta, banco e query parameters, nunca por
  substituição genérica de texto;
- antes de qualquer operação destrutiva de teste, `TEST_DATABASE_URL` precisa ser
  diferente de `DATABASE_URL` e o nome do banco precisa terminar em `_test`; caso
  contrário, os testes abortam com mensagem clara.

**Por quê:** `DATABASE_URL` é o nome convencional no Render; uma variável própria
para os testes torna explícito o alvo e permite a guarda dupla. A normalização
evita editar a URL à mão no painel do Render.
**Descartei:** só `DATABASE_URL` sobrescrita pelos testes (guarda frágil); `APP_ENV`
escolhendo URLs (indireção sem ganho); ler só `os.environ` sem
`pydantic-settings`; normalizar com `str.replace`.

### D5 – Banco de teste limpo no início da sessão
**Decidi** que, no início da sessão de testes de integração: (1) valido que o alvo
é o banco `_test`; (2) recrio o schema `public`; (3) executo
`alembic upgrade head`; (4) só então rodo os testes. O esquema vem das
migrations, nunca de `metadata.create_all()`.
**Por quê:** sempre parte do zero e pelo mesmo caminho da produção.
**Descartei:** recriar o banco inteiro (exige permissão de `CREATE DATABASE` sem
necessidade) e rodar `upgrade head` sem limpar (estado sujo passaria
despercebido).

### D6 – `GET /health` não consulta o PostgreSQL
**Decidi** manter `GET /health` como liveness simples, com exatamente o contrato
da Story 1.1. Não crio `/health/db` nesta story.
**Por quê:** a integração com o PostgreSQL já é provada pelas migrations, pelos
testes de integração e, depois, pelo fluxo de deploy. Reabro só se aparecer uma
necessidade concreta no deploy.
**Descartei:** `SELECT 1` dentro do `/health` (muda o contrato e faria uma oscilação
do banco gratuito parecer o serviço doente para o Render) e uma rota separada de
prontidão agora (sem necessidade concreta).

### D7 – Revisão inicial vazia com naming convention
**Decidi** criar uma revisão inicial vazia, sem tabela de domínio, com `MetaData`
usando naming convention para as migrations futuras, em `backend/migrations/`.
**Por quê:** a "última revisão" existe e é testável (CA3), e os nomes das
constraints futuras (CHECKs do AD-3, `UNIQUE(lot_id)` do AD-9) ficam
determinísticos.
**Descartei:** baseline sem convenção (nomes gerados pelo banco dificultam reverter
migrations) e nenhuma revisão até a primeira tabela (CA3 não verificável). Também
descartei `backend/alembic/` como pasta.

### D8 – `verify.sh` garante o PostgreSQL
**Decidi** que o `verify.sh` executa `docker compose up -d --wait postgres` antes
dos testes de integração; se Docker, Compose ou PostgreSQL não ficarem prontos,
falha com mensagem clara, sem pular testes. Não derrubo o contêiner ao final.
**Por quê:** um único comando para mim e para o avaliador.
**Descartei:** só checar e pedir que eu suba o banco à mão (passo manual a mais) e
subir e derrubar a cada execução (mais lento e, com D3, derrubaria também o banco
de dev).

### Python 3.13
**Decidi** confirmar Python 3.13 como versão do projeto (`backend/.python-version`
e `requires-python = ">=3.13"`). Fecha esse item da Q10.
**Descartei:** não registrei alternativa; a versão já estava em uso desde a 1.1.

## Notas para o desenvolvedor

- Sessão síncrona: `sqlalchemy.orm.sessionmaker`, `Session`; nada de
  `create_async_engine` nem `psycopg2`.
- Normalização por componentes: `sqlalchemy.engine.make_url(url)` e
  `url.set(drivername="postgresql+psycopg")` quando `drivername == "postgresql"`;
  `postgresql+psycopg` passa intacto; outro `drivername` gera erro claro (isso
  também impede SQLite e psycopg2, coerente com AD-2 e AD-27). Ao gerar a string
  para o Alembic, usar `render_as_string(hide_password=False)`, nunca `str(url)`,
  que mascara a senha. Nunca registrar a URL com senha em log.
- `alembic.ini` sem `sqlalchemy.url`; `env.py` lê da configuração central. Nos
  testes, o `upgrade head` programático recebe a URL de teste, nunca a de dev.
- `postgres:18`: volume em `/var/lib/postgresql`. O script de
  `docker-entrypoint-initdb.d` só roda com volume vazio; recriar com
  `docker compose down -v`.
- `docker compose up --wait` depende do healthcheck do serviço.
- Nunca ler, imprimir nem copiar `.env*` reais.

## Referências

- `_bmad-output/planning-artifacts/epics.md`, Story 1.2 e Pendências.
- `docs/ARQUITETURA.md`: AD-2, AD-14, AD-17, AD-27, AD-28; questão 10 (itens
  resolvidos por esta story).
- `docs/CRONOGRAMA.md`: Dia 2.
- Render: [PostgreSQL 18 disponível](https://render.com/changelog/postgresql-18-is-now-available-for-render-postgres-databases),
  [Create and Connect to Render Postgres](https://render.com/docs/postgresql-creating-connecting),
  [Upgrading Your Render Postgres Version](https://render.com/docs/postgresql-upgrading).

## Registro do agente de desenvolvimento

### Modelo usado

Claude Sonnet 5.5.

### Log de depuração

- Dois comandos em paralelo fizeram o `cd` de um deles criar arquivos novos dentro de `backend/`; foram movidos para os lugares certos. `app/config.py` e `app/db.py` não chegaram a ser criados nessa corrida e foram recriados.
- A regra de proteção de `.env*` impediu o agente de mover e de escrever `backend/.env.example`. Eu movi manualmente `backend/backend/.env.example` para `backend/.env.example` e removi `backend/backend/`. A pendência de CA2/T3.4 está resolvida.
- `alembic.ini` ganhou `path_separator = os` para remover um DeprecationWarning.
- Após o review, `reset_test_database` passou a confirmar `current_database()` pela própria conexão que executa o DROP, antes de qualquer operação destrutiva (teste `test_reset_refuses_non_test_database_before_dropping`).

### Notas de conclusão

- `verify.sh` completo foi executado no fechamento; ver o resultado da execução final na resposta da sessão.
- Verificações específicas: banco parado dá "PostgreSQL de teste inacessível. Suba o banco com: docker compose up -d --wait postgres" (executado com o `pytest`, não com o `verify.sh`, por isso T8.2 segue sem marcar); guardas (ausente, igual a dev, sem `_test`) abortam a sessão; downgrade/upgrade rodados só em `casa_de_leiloes_test`; `alembic upgrade head` rodado em `casa_de_leiloes_dev` (só upgrade).
- O `README.md` documenta que o `verify.sh` fornece URLs locais padrão quando as variáveis não estão no ambiente, sem ler `backend/.env`.

### Lista de arquivos

Novos: `compose.yaml`, `docker/postgres-init/01-create-databases.sql`, `README.md`, `backend/.env.example`, `backend/alembic.ini`, `backend/app/config.py`, `backend/app/db.py`, `backend/migrations/{env.py,script.py.mako,versions/0001_baseline.py}`, `backend/tests/{conftest.py,db_guard.py,test_config.py,test_db_guard.py}`, `backend/tests/integration/{__init__.py,test_database.py}`.
Alterados: `backend/pyproject.toml`, `backend/uv.lock`, `verify.sh`, `docs/uso_de_ia.md`, esta story, `sprint-status.yaml`.
