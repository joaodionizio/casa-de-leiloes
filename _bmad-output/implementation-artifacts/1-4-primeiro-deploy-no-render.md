# Story 1.4: Primeiro deploy no Render

Status: review

Chave do sprint: `1-4-primeiro-deploy-no-render`
Épico: 1 (Fundação e aplicação publicada), Dia 2 (23/10) do cronograma
("primeiro deploy no Render com PostgreSQL"). Story criada em 24/10/2026.
Escopo confirmado por mim em 24/10/2026: seguir o `epics.md` (D1 = A), ou seja,
o primeiro deploy valida também WebSocket e cookie, como verificação mínima de
infraestrutura. As perguntas P1 a P14 (abaixo) são decididas no planejamento,
antes de qualquer código.

## Story

Como avaliador,
quero abrir a aplicação numa URL pública que já comprove banco, migrations,
WebSocket e cookie na infraestrutura real,
para que o deploy obrigatório exista desde o primeiro dia e os riscos do Render
gratuito apareçam cedo.

## Objetivo e contexto

As Stories 1.1 a 1.3 entregaram uma imagem única (`Dockerfile` multi-stage na
raiz) que serve API, SPA e `GET /health` na mesma origem; o `start.sh` aplica
`alembic upgrade head` e só então executa o uvicorn na porta de `PORT`, como
usuário não root; `DATABASE_URL` no formato `postgresql://` do Render já é
normalizada para psycopg 3. A imagem foi validada localmente (smoke da 1.3).
Nada disso rodou ainda fora da minha máquina.

Esta story publica essa imagem pela primeira vez:

- um PostgreSQL gratuito e um Web Service gratuito (runtime Docker) no Render,
  conectados por `DATABASE_URL` (AD-14);
- a URL pública em HTTPS serve SPA, `/health`, OpenAPI e o 404 JSON sob `/api`;
- uma verificação de WebSocket e uma de cookie, mínimas, sem domínio, sem
  autenticação e sem banco, provam que o proxy do Render e o navegador aceitam
  o que as Stories 2.2 (cookie do JWT) e 4.1 (sala) vão precisar (D1 = A);
- um redeploy prova que as migrations são idempotentes;
- o README e o `docs/uso_de_ia.md` registram como o deploy foi feito, só com
  fatos observados.

O único código novo são as duas verificações (e seus testes). Nada mais do
`Dockerfile`, do `start.sh` ou da aplicação muda, a não ser que uma pergunta
abaixo seja decidida nesse sentido.

## Critérios de aceite

CA1 a CA6 e CA10 a CA12 vêm do `epics.md` (texto preservado, com detalhe). Os
demais explicitam o deploy mínimo pedido na criação da story.

1. **CA1 – Build pelo `Dockerfile` do repositório.** Dado o repositório
   conectado a um Web Service gratuito do Render com runtime Docker, quando o
   deploy roda, então a imagem é construída a partir do `Dockerfile` da raiz,
   sem alteração para o Render, sem Pre-Deploy Command e sem comando de
   inicialização diferente do `CMD` da imagem.
2. **CA2 – Inicialização.** Dado o primeiro deploy, quando o contêiner sobe,
   então o log do Render mostra as linhas do Alembic antes de
   "Uvicorn running on http://0.0.0.0:<PORT>", com `<PORT>` igual à porta
   que o Render forneceu (sem porta codificada no código ou no `Dockerfile`); o
   processo roda como o usuário não root da imagem; o serviço não usa disco
   persistente.
3. **CA3 – PostgreSQL do Render.** Dado um PostgreSQL gratuito do Render
   (PostgreSQL 18, D1 da 1.2), quando o serviço inicia, então `DATABASE_URL`
   chega só como variável de ambiente do serviço, é aceita pela normalização
   existente, e `alembic upgrade head` termina com sucesso no banco de produção
   antes de o uvicorn iniciar (o `start.sh` só executa o uvicorn depois da
   migration).
4. **CA4 – URL pública.** Dada a URL pública do serviço, em HTTPS, quando a
   chamo de fora (minha máquina, sem VPN nem túnel), então:
   - `GET /health` → 200, `application/json`, exatamente `{"status": "ok"}`;
   - `GET /` → 200 `text/html`, a SPA, e no navegador a página mostra
     "Serviço no ar";
   - `GET /lots/qualquer-coisa` → 200 `text/html`, o `index.html`;
   - `GET /api/docs` → 200, Swagger; `GET /api/openapi.json` → 200 JSON;
   - `GET /api/<inexistente>` → 404 JSON, nunca HTML;
   - um asset real de `/assets/...` → 200 com `Content-Type` adequado.
5. **CA5 – Mesma origem, sem CORS.** Dado o serviço publicado, quando a SPA
   chama `/health` e quando abro o WebSocket de verificação, então tudo usa o
   mesmo host da URL pública (`https://` e `wss://`), o back-end continua sem
   `CORSMiddleware` e nenhuma configuração de CORS existe no Render.
6. **CA6 – WebSocket de verificação.** Dado o serviço publicado, quando abro uma
   conexão `wss://` de verificação e troco mensagens, então a conexão funciona
   através do proxy do Render, nos dois sentidos; essa verificação não lê nem
   grava dados de domínio, não usa o banco, não tem autenticação, não antecipa a
   sala de leilão nem os eventos do AD-10, e o handshake não altera estado no
   servidor (AD-29).
7. **CA7 – Cookie de verificação.** Dado o serviço publicado, quando recebo o
   cookie de verificação, então ele chega com `HttpOnly`, `Secure`,
   `SameSite=Lax`, `Path=/`, sem `Domain` e, se possível, com prefixo `__Host-`
   (AD-29); essa verificação não emite JWT nem identifica usuário; obter o
   cookie não altera estado no servidor; o navegador guarda o cookie na URL
   pública.
8. **CA8 – Segredos.** Dada a configuração de produção, quando a reviso, então a
   URL do banco (e qualquer segredo) existe só nas variáveis de ambiente do
   Render, nunca no repositório, na imagem, no README, na story ou em logs da
   aplicação; nenhum `.env*` é enviado; não há endpoint de debug nem rota que
   exponha variáveis de ambiente; o `Dockerfile` não ganha `ENV`/`ARG` de
   segredo.
9. **CA9 – Redeploy e reinício.** Dado o serviço já publicado, quando faço um
   novo deploy (ou reinicio o serviço), então ele volta a responder CA4, o
   Alembic roda de novo sem aplicar revisão (o banco já está no head) e nenhum
   dado é destruído.
10. **CA10 – Cold start medido, nunca estimado.** Dado o serviço parado por
    inatividade, quando o acesso de novo, então registro na story e no README o
    tempo observado, só a partir de medição real (comando e saída). Se eu não
    observar o serviço parado durante a story, registro isso, sem número.
11. **CA11 – `verify` e testes.** Dado o código novo das verificações, quando
    rodo `./verify.sh`, então ele passa, com testes no mesmo commit para a
    verificação de WebSocket e a de cookie; os testes existentes continuam
    passando sem alteração, inclusive o que exige o fallback da SPA como última
    rota.
12. **CA12 – Documentação.** Dado o README, quando um avaliador o lê, então
    encontra como subir o banco local, aplicar migrations, rodar o `verify`,
    rodar a aplicação e como o deploy é feito: serviço e banco usados, nomes
    (nunca valores) das variáveis, fluxo de deploy, como validar `/health`, SPA,
    OpenAPI, WebSocket e cookie, e só as limitações do plano gratuito que
    observei de fato. `docs/uso_de_ia.md` registra o que a IA fez nesta story e
    o que eu revisei.

## ADs aplicáveis

- **AD-14:** um único Web Service gratuito (FastAPI + API + WebSocket + SPA) e
  PostgreSQL gratuito do Render; `GET /health`; primeiro deploy no Épico 1,
  validando FastAPI, PostgreSQL, React, WebSocket, cookies e migrations.
- **AD-28:** a imagem multi-stage da 1.3, sem estado no filesystem do contêiner.
- **AD-2:** PostgreSQL, SQLAlchemy síncrono, Alembic, psycopg 3 (URL normalizada).
- **AD-10:** WebSocket só como transporte; nesta story, só a verificação de
  infraestrutura, sem sala, eventos, heartbeat nem reconexão.
- **AD-11 / AD-29:** mesma origem; atributos do cookie de produção; GET, HEAD,
  OPTIONS e o handshake do WebSocket sem efeito colateral; sem CORS permissivo.
  Sem JWT nesta story.
- **AD-30:** rotas e identificadores em inglês, sob `/api`; textos ao usuário em
  português.
- **AD-27:** `verify.sh` inalterado em etapas; os testes novos entram no `pytest`.

Nenhuma AD é alterada.

## Estado real herdado (lido no código em 24/10/2026)

- `Dockerfile`: estágio `node:24-slim` (`npm ci`, `npm run build`) e estágio
  `python:3.13-slim` com `uv` 0.13.5 fixo, `uv sync --frozen --no-dev`,
  `ENV SPA_DIST_DIR=/app/frontend-dist`, usuário `app` (uid 10001), sem
  `VOLUME`, `CMD ["./scripts/start.sh"]`.
- `backend/scripts/start.sh`: `set -eu`; `alembic upgrade head`; `exec uvicorn
  app.main:app --host 0.0.0.0 --port "${PORT:-8000}"`. Sem `--proxy-headers`
  nem `--forwarded-allow-ips` (avaliação adiada pela 1.3 para esta story, P8).
- `backend/app/config.py`: `DATABASE_URL` obrigatória para quem usa o banco
  (`get_settings`), `normalize_database_url` aceita `postgresql://` e
  `postgresql+psycopg://`, mensagens de erro sem a URL; `SpaSettings` separado.
- `backend/app/main.py`: `create_app()` registra `/health` (sem banco), OpenAPI
  em `/api/docs` e `/api/openapi.json`, Redoc desligado, e a SPA por último.
- `backend/app/spa.py` + `tests/test_spa.py`: fallback só GET/HEAD; `/api`,
  `/api/*` e `/health` fora dele; um teste exige que `SPA_FALLBACK_PATH` seja a
  última rota de `app.routes`. As rotas novas precisam ser registradas antes da
  SPA.
- `uvicorn[standard]` já está nas dependências de runtime: o suporte a
  WebSocket não exige dependência nova.
- `frontend/vite.config.ts`: proxy de `/api` e `/health` para
  `127.0.0.1:8000`, sem `ws: true` (P12).
- `verify.sh`: Ruff → format → Docker/PostgreSQL → `pytest` → lint →
  typecheck → build do Vite → `docker build`. Sem `docker run`.
- `.dockerignore`: exclui `**/.env*`, `.git`, `docs`, `_bmad*`, testes, caches.
- Story 1.3: smoke real da imagem registrado (ordem Alembic → uvicorn, porta de
  `PORT`, usuário `app`, negativos de SPA e de banco).

## Decisões herdadas (não reabrir)

- Render gratuito, um Web Service + PostgreSQL gratuito (AD-14).
- PostgreSQL 18 também em produção (D1 da Story 1.2).
- `DATABASE_URL` como nome da variável; formato `postgresql://` aceito sem
  edição manual (D3/D4 da 1.2).
- `GET /health` não consulta o banco (1.2): o banco gratuito lento não deve
  fazer o Render considerar o serviço doente.
- Migrations pelo `start.sh`, não no `lifespan` nem em Pre-Deploy Command
  (D1 da 1.3).
- `SPA_DIST_DIR` definido no `Dockerfile` (D3 da 1.3); OpenAPI em `/api`
  (D5 da 1.3); sem CORS, nem em desenvolvimento (D2 da 1.3).
- Imagem `node:24-slim` + `python:3.13-slim`, `uv` fixo, não root (D7 da 1.3).
- Escopo D1 = A do `epics.md`, confirmado por mim nesta criação: WebSocket e
  cookie de verificação entram nesta story.

## Perguntas abertas (decido no planejamento, antes de qualquer código)

Para cada uma, deixei as opções e uma recomendação; a decisão é minha.

- **P1 – Nome do Web Service.** Define o subdomínio `*.onrender.com` da URL
  pública (o Render pode acrescentar sufixo se o nome estiver tomado).
  Recomendação: um nome curto em inglês derivado do projeto.
- **P2 – Região.** O Web Service e o banco precisam estar na mesma região para
  usar a URL interna do banco. Recomendação: a mesma região para os dois,
  escolhida por mim no painel.
- **P3 – Nome da instância e do banco PostgreSQL.** Recomendação: nomes em
  inglês, sem relação com credenciais; o usuário e a senha são gerados pelo
  Render.
- **P4 – Como `DATABASE_URL` chega ao serviço.** (a) copiar a Internal Database
  URL do banco para uma variável `DATABASE_URL` do serviço no painel; (b)
  `fromDatabase` num `render.yaml` (só com P5 = Blueprint). Nos dois casos, o
  valor nunca passa pelo agente nem pelo repositório. Recomendação: (a) se P5
  for painel.
- **P5 – `render.yaml` (Blueprint) ou configuração manual pelo painel.**
  Blueprint versiona a configuração (sem segredos) e torna o deploy
  reproduzível; painel é mais rápido e não acrescenta arquivo. Recomendação:
  painel nesta story, com os passos exatos no README; reavaliar na 6.3.
- **P6 – Health check do Render.** Configurar o Health Check Path como
  `/health`, ou deixar o padrão. Recomendação: `/health`, que não depende do
  banco.
- **P7 – Branch e auto-deploy.** Eu trabalho em `epic-1`; o Render publica a
  partir de uma branch. (a) publicar de `epic-1` agora e trocar para `main`
  depois do merge; (b) publicar só de `main` (exige merge antes do deploy); (c)
  auto-deploy desligado e deploy manual. Consequência: com auto-deploy ligado,
  todo push na branch escolhida republica. Outras configurações do Docker
  Service (contexto e caminho do `Dockerfile` na raiz, sem Docker Command
  próprio) ficam no padrão, salvo decisão contrária.
- **P8 – `--proxy-headers` / `--forwarded-allow-ips` no uvicorn.** Sem isso, a
  aplicação pode ver `http` como esquema atrás do proxy do Render. Nesta story
  nada depende do esquema (o cookie recebe `Secure` explicitamente; não há
  redirecionamento). (a) não mudar o `start.sh` e registrar o que observei; (b)
  acrescentar as opções agora. Recomendação: (a), a não ser que alguma
  verificação falhe por isso.
- **P9 – WebSocket de verificação.** Caminho (sob `/api`, em inglês), protocolo
  (eco de texto, ou um `ping`/`pong` fixo), limite de tamanho de mensagem e
  fechamento. Também: o handshake valida `Origin` (Q2 da arquitetura, aplicada
  só a esta verificação)? Recomendação: eco de texto curto, com tamanho
  limitado, sem estado; a resposta da Q2 para a sala continua na 4.1.
- **P10 – Cookie de verificação.** Caminho (sob `/api`, GET, sem efeito
  colateral), nome com `__Host-`, valor fixo que não identifica ninguém,
  `Max-Age`. Em desenvolvimento, o AD-29 prevê `Secure=false` no localhost, mas
  a aplicação não tem noção de ambiente (a 1.3 evitou criar `APP_ENV`), e
  `__Host-` exige `Secure`. Opções: (a) cookie sempre `Secure` com `__Host-`
  (o comportamento em `http://localhost` depende do navegador e precisa ser
  conferido); (b) criar agora uma configuração de ambiente; (c) a verificação
  só existe para o deploy e não precisa funcionar no Vite. Também: só conferir
  o `Set-Cookie` e o armazenamento no navegador, ou ter uma segunda chamada que
  confirme que o cookie voltou. Recomendação: (a) com conferência do
  `Set-Cookie` e do armazenamento; (b) fica para a 2.2.
- **P11 – Destino das verificações depois.** Removê-las quando a 2.2 (cookie
  real) e a 4.1 (WebSocket real) chegarem, ou mantê-las como diagnóstico
  público. Consequência: a 2.2 exige política de acesso declarada em toda rota;
  se ficarem, entram como públicas nessa política. Recomendação: remover na
  story que entregar o equivalente real, registrando isso nelas.
- **P12 – Cliente da verificação do WebSocket.** (a) um comando local único
  com o pacote `websockets` que já vem com `uvicorn[standard]`, sem arquivo
  novo versionado; (b) console do navegador na URL pública; (c) um bloco na
  página de saúde da SPA. A opção (c) tornaria necessário `ws: true` no proxy
  do Vite. Recomendação: (a), com a saída real colada na story; (b) como prova
  adicional de mesma origem.
- **P13 – Quem executa cada passo.** O agente não tem acesso ao painel do
  Render e não pode ver valores de segredos. Proposta: eu crio o banco e o
  serviço, configuro as variáveis e disparo os deploys; o agente escreve o
  código, os testes e os documentos, e roda as verificações públicas (`curl`,
  WebSocket) contra a URL pública, que não exigem segredo. Confirmar se o
  agente pode fazer requisições à URL pública e se eu colo os trechos de log
  do Render.
- **P14 – Medição do cold start.** Como e quando: esperar o serviço parar por
  inatividade (sem supor o tempo) e medir o primeiro acesso com
  `curl -w '%{time_total}'`, uma ou mais vezes. Se não houver janela durante a
  story, o CA10 registra "não observado" e a medição vai para a 6.4.

## Tarefas e subtarefas

Marcadas com **[eu]** as que dependem do painel do Render ou de segredos, e
**[agente]** as que o agente executa (sujeito à P13).

- [x] **T0 – Planejamento.** Decidir P1 a P14 e registrar as decisões nesta
      story (seção "Decisões registradas", em primeira pessoa, com a
      alternativa descartada).
- [x] **T1 – Verificação de WebSocket (CA5, CA6) [agente]**
  - [x] T1.1 Rota WebSocket conforme P9, registrada antes do fallback da SPA,
        assíncrona, sem banco, sem estado, sem autenticação.
  - [x] T1.2 Nenhum log com conteúdo de mensagens ou cabeçalhos sensíveis.
- [x] **T2 – Verificação de cookie (CA7) [agente]**
  - [x] T2.1 Rota GET conforme P10, sob `/api`, registrada antes do fallback,
        sem efeito colateral no servidor, sem JWT, sem identificar usuário.
  - [x] T2.2 Atributos: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem
        `Domain`, nome com `__Host-` se possível.
- [x] **T3 – Testes (CA11) [agente]** — ver "Testes esperados".
- [x] **T4 – `verify` local (CA11) [agente]:** `./verify.sh` completo, com a
      saída real e o código de saída capturado.
- [x] **T5 – PostgreSQL no Render (CA3) [eu]:** criar a instância gratuita,
      PostgreSQL 18, nomes e região de P2/P3; anotar a data de expiração que o
      painel mostrar (ponto de atenção do `ARQUITETURA.md`), sem copiar
      credenciais para nenhum arquivo.
- [x] **T6 – Web Service no Render (CA1, CA2, CA8) [eu]:** runtime Docker,
      repositório e branch conforme P7, `Dockerfile` da raiz, plano gratuito,
      sem disco, sem Pre-Deploy Command, sem Docker Command próprio; variável
      `DATABASE_URL` conforme P4; Health Check Path conforme P6. Nenhuma outra
      variável é necessária nesta story (`PORT` vem do Render; `SPA_DIST_DIR`
      vem da imagem).
- [x] **T7 – Primeiro deploy (CA1, CA2, CA3) [eu + agente]:** acompanhar o
      build e a inicialização; registrar na story o trecho do log com a ordem
      Alembic → uvicorn e a porta, com qualquer valor sensível mascarado.
- [x] **T8 – Validação pública (CA4 a CA7) [agente]:** roteiro de "Validação
      pública", com a saída real.
- [x] **T9 – Redeploy (CA9) [eu + agente]:** novo deploy ou reinício; log do
      Alembic sem revisão aplicada; repetir as chamadas do CA4.
- [x] **T10 – Cold start (CA10) [eu + agente]:** conforme P14.
- [x] **T11 – Documentação (CA12) [agente]**
  - [x] T11.1 `README.md`: seção de deploy (serviço, banco, nomes das
        variáveis, passos, como validar, limitações observadas); conferir que
        banco local, migrations, `verify` e execução local continuam descritos.
  - [x] T11.2 `docs/uso_de_ia.md`: Story 1.4.
  - [x] T11.3 Conferência de segredos: nenhuma URL de banco, senha ou valor de
        variável no diff, na story ou no README.
- [x] **T12 – Fechamento:** status da story e do `sprint-status.yaml` para
      `review`; parar e avisar. Sem git.

## Arquivos que provavelmente serão alterados

| Área | Arquivo | Ação |
| --- | --- | --- |
| App | `backend/app/main.py` | alterado (registrar as verificações antes da SPA) |
| App | um módulo novo para as verificações (nome no planejamento) | novo |
| Testes | um arquivo novo de testes das verificações | novo |
| Docs | `README.md`, `docs/uso_de_ia.md` | alterado |
| Story | este arquivo, `sprint-status.yaml` | alterado no fechamento |
| Só se decidido | `backend/scripts/start.sh` (P8), `render.yaml` (P5), `frontend/vite.config.ts` e página de saúde (P12) | condicional |
| Sem mudança | `Dockerfile`, `.dockerignore`, `compose.yaml`, `verify.sh`, migrations, `config.py`, `spa.py`, testes existentes, `pyproject.toml`, `uv.lock`, `package*.json` | intocados |

## Testes esperados

Só para o código novo, com `TestClient`, sem banco e sem rede externa:

| Teste | Prova |
| --- | --- |
| Conectar ao WebSocket de verificação, enviar e receber conforme P9, fechar | CA6 |
| Mensagem fora do limite de P9 é recusada ou fecha a conexão, sem erro 500 | CA6 |
| `GET` do cookie → `Set-Cookie` com `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain`, nome conforme P10 | CA7 |
| A resposta do cookie não contém JWT nem dado de usuário | CA7 |
| Métodos de escrita na rota do cookie → 404/405 JSON, nunca `index.html` | CA7, AD-29 |
| Com a SPA montada, as rotas novas continuam respondendo e o fallback segue como última rota | CA11 |
| Testes existentes (`test_spa.py`, `test_openapi.py`, `test_health.py`, `test_config.py`, integração) sem alteração | CA11 |

Nenhuma suíte nova para o Render. A evidência do deploy é a validação pública.

## Validação pública (CA4 a CA7, CA9)

Executada contra a URL pública, com a saída real colada nesta story:

1. `curl -i https://<url>/health` → 200 JSON `{"status":"ok"}`.
2. `curl -i https://<url>/` e `https://<url>/lots/qualquer-coisa` → 200
   `text/html`.
3. `curl -i` de um asset real de `/assets/...` (nome lido do `index.html`
   publicado) → 200 com o `Content-Type` adequado.
4. `curl -i https://<url>/api/docs` → 200 HTML; `/api/openapi.json` → 200 JSON.
5. `curl -i https://<url>/api/nao-existe` → 404 JSON.
6. Cabeçalhos de CORS: nenhuma resposta traz `Access-Control-Allow-Origin`.
7. WebSocket: cliente conforme P12 em `wss://<url>/<rota de P9>`; mensagens nos
   dois sentidos.
8. Cookie: `curl -i` da rota de P10 mostra o `Set-Cookie` completo; no
   navegador, o cookie aparece guardado para o host da URL pública.
9. Navegador: a página inicial mostra "Serviço no ar".
10. Depois do redeploy (T9): repetir 1, 2 e 5.

## Segurança

- Nenhuma senha, URL de banco ou valor de variável em código, `Dockerfile`,
  README, story, `docs/uso_de_ia.md` ou logs da aplicação.
- Nenhum `.env*` lido, impresso, copiado ou enviado (o `.dockerignore` já os
  exclui; não muda).
- Sem CORS, sem endpoint de debug, sem rota que exponha ambiente ou
  configuração.
- Ao colar logs do Render na story, mascarar hosts internos e qualquer valor
  sensível.
- As verificações não leem nem gravam nada no servidor e não identificam
  ninguém.

## Fora de escopo

- Autenticação, usuários, JWT, cookie de sessão real (2.2).
- Lotes, Art Institute of Chicago, seed, carteira, lances, scheduler, catch-up,
  auditoria, comprovantes.
- Sala ao vivo: eventos, snapshot, heartbeat, reconexão (4.1, 4.2); Q1 e Q2 para
  a sala.
- Formato único de erro e validação de `Origin` nas rotas da API (2.1).
- CI/CD além do auto-deploy do próprio Render; domínio customizado;
  observabilidade além dos logs do Render; Redis ou qualquer serviço extra;
  disco persistente.
- Refatorações da Story 1.3; mudanças no `Dockerfile`, no `.dockerignore` ou no
  `verify.sh`.
- README completo e roteiro de avaliação (6.3); validação final no deploy (6.4).

## Questões da arquitetura (Q1 a Q10) nesta story

- **Q2** (Origin no WebSocket) aparece só na P9, restrita à verificação; a
  resposta para a sala continua aberta para a 4.1.
- **Q4** (ordem na inicialização) pede para verificar no primeiro deploy se o
  catch-up atrapalha a inicialização do Render; ainda não há catch-up, então
  só registro o tempo de inicialização observado como referência.
- **Q10:** a rota do WebSocket da sala continua aberta; a rota de verificação
  (P9) não a define.

## Decisões registradas

Decididas por mim em 24/10/2026, no planejamento, antes de qualquer código.

- **P1 – Nome do Web Service.** Decidi `casa-de-leiloes`. Se estiver ocupado, escolho
  a variação no painel na hora. O nome não aparece no código. Descartei um nome em
  português ou mais longo, sem ganho.
- **P2 – Região.** Decidi `Virginia (US East)` para o serviço e para o banco. Descartei
  regiões diferentes, porque perderia a URL interna do banco.
- **P3 – Banco.** Decidi PostgreSQL `casa-de-leiloes-db`, versão 18, plano Free, com
  database e usuário gerados pelo Render. Descartei escolher usuário e senha à mão.
- **P4 – `DATABASE_URL`.** Decidi usar a Internal Database URL, colada por mim só no
  painel do serviço. A normalização existente já a aceita; a camada de banco não
  muda. Descartei a External URL e o `fromDatabase` de um `render.yaml`.
- **P5 – `render.yaml`.** Decidi não criar nesta story; os passos manuais ficam no
  README. Reavalio na 6.3. Descartei o Blueprint agora.
- **P6 – Health check.** Decidi `/health` como Health Check Path, sem alterar a rota
  (liveness sem banco). Descartei o padrão do Render e um health que consulte o banco.
- **P7 – Branch e auto-deploy.** Decidi publicar de `epic-1` com Auto-Deploy **Off** e
  deploys manuais ("Deploy latest commit"). Ao fazer o merge em `main`, no fim do
  épico, troco a branch no painel (fora desta story). Descartei On Commit e publicar
  só de `main`.
- **P8 – Cabeçalhos do proxy.** Decidi **não** mudar o `start.sh`. Nada depende de
  esquema ou host vindos de `X-Forwarded-*`: o cookie recebe `Secure` explícito, a
  checagem de `Origin` compara só o host, a documentação usa caminho relativo e não
  há redirect de barra final. Descartei `--proxy-headers --forwarded-allow-ips='*'`
  preventivo: confiar em qualquer IP é pior do que não confiar.
- **P9 – WebSocket de verificação.** Decidi `/api/infra-check/ws`: uma troca e fecha.
  Aceita um texto de até 64 bytes e devolve `echo:<texto>`. Espera a mensagem por no
  máximo 10 s. `Origin` ausente é aceito (cliente que não é navegador); `Origin`
  presente só passa se o host for o do cabeçalho `Host`; `Origin` malformado é
  recusado, nunca vira 500. `Origin` recusado antes de `websocket.accept()` encerra o
  handshake com HTTP 403 (o navegador não recebe um close 1008; o `TestClient` o vê
  como `WebSocketDisconnect` com código 1008). Depois da conexão aceita: 1000
  (normal), 1003 (binário), 1008 (tempo esgotado) e 1009 (acima de 64 bytes). A Q2 da sala continua
  aberta para a 4.1. Descartei eco contínuo, `ping`/`pong` fixo, não checar `Origin`
  e `Origin` por configuração.
- **P10 – Cookie de verificação.** Decidi `GET /api/infra-check/cookie` com
  `__Host-infra_check=1`, `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain`
  e `Max-Age=600`. Resposta `{"cookie_received": bool}`, sempre reemitindo o cookie, com
  `Cache-Control: no-store`. A segunda chamada no mesmo cliente é a única forma de
  provar que um cookie `HttpOnly` voltou. O cookie é sempre `Secure`, sem noção de
  ambiente; os testes usam `https://testserver`. Descartei `APP_ENV` e `Secure=false`
  local (fica para a 2.2).
- **P11 – Destino depois.** Decidi manter as duas verificações até a story real:
  o cookie técnico sai na 2.2 e, depois dela, só o WebSocket técnico continua
  temporariamente; a 2.2 o classifica como rota pública na política de acesso até a
  4.1 removê-lo ou substituí-lo. Registrei isso na docstring do módulo, nesta story
  e no `epics.md`. Descartei uma flag para desligá-las e mantê-las como diagnóstico
  permanente.
- **P12 – Cliente do WebSocket.** Decidi: localmente, `TestClient.websocket_connect`;
  na validação pública, (a) o console do navegador na própria URL pública (prova a
  mesma origem e o `Origin` real) e (b) um comando único com o `websockets` já
  instalado, sem arquivo versionado, que também prova a recusa de `Origin`
  estrangeiro. Descartei um bloco na SPA, `ws: true` no Vite e dependência nova.
- **P13 – Quem faz o quê.** Eu faço o que depende do painel do Render, de segredos, de
  commits e de push. O agente escreve código, testes e documentos, e roda `curl` e o
  WebSocket contra a URL pública se a rede permitir (senão eu rodo e colo a saída).
  O agente nunca vê o painel nem a `DATABASE_URL`.
- **P14 – Cold start.** Decidi medir só se o serviço dormir naturalmente durante o
  fluxo. Sem espera artificial. Se não ocorrer, registro "não observado nesta
  validação". Descartei benchmark e esperar 15 min de propósito.

### Exceção à regra de um commit por story (só para a 1.4)

Esta story tem dois commits, feitos por mim: o **A**, depois do review local e antes do
deploy (código, testes e documentação pré-deploy; é o commit que o Render publica), e o
**B**, depois da validação pública (somente documentação e evidências factuais, e o status
final). Fiz a exceção porque o Render só publica código que já está no GitHub e as
evidências só existem depois. Descartei amend, force-push, branch temporária e registry
de imagens, que aumentariam risco e complexidade sem benefício. O B não exige novo deploy:
o `Dockerfile` não copia README, `docs/` nem `_bmad-output/`. As próximas stories voltam
ao processo padrão.

O commit A publicado no Render foi `0736ec1c536bef0fee3fe1072778fc859dc9de1a`. O commit B
(este fechamento) é só documentação e status; como o Auto-Deploy está Off, ele não
republica nada.

## Evidências da fase local (24/10/2026)

- `uv run pytest tests/test_infra_check.py` antes de existir `app/infra_check.py`: erro de coleta
  (`ImportError: cannot import name 'infra_check' from 'app'`), 0 testes coletados.
- Depois de implementar: 39 testes passaram em `test_infra_check.py`; com `test_spa.py` e
  `test_openapi.py`, 116 passaram.
- `ruff check .`: All checks passed. `ruff format --check .`: 19 files already formatted.
- `./verify.sh` (uma execução): código de saída 0; `pytest` com 136 passed e 1 warning (o
  `StarletteDeprecationWarning` do `httpx`); lint, typecheck, build do Vite e `docker build` passaram.
- Depois das correções LOW do review pré-deploy (só testes e documentação),
  `uv run pytest tests/test_infra_check.py`: 52 passed e 1 warning; `ruff check .` e
  `ruff format --check .` limpos. O `./verify.sh` não foi repetido porque nenhum código de
  aplicação mudou.

## Evidências da fase pública

Registradas a partir do que eu observei no painel, no navegador e no terminal. Não colei os
logs brutos do Render: o resumo abaixo é o que conferi neles. Nenhuma credencial, usuário,
host interno do banco, IP interno nem a `DATABASE_URL` aparece aqui.

### Banco e Web Service (T5, T6)

- PostgreSQL `casa-de-leiloes-db`: plano Free, PostgreSQL 18, Virginia (US East), status
  `Available`. **Data de expiração mostrada pelo painel: 23/11/2026.**
- Web Service: URL pública `https://casa-de-leiloes-i1xr.onrender.com`, runtime Docker,
  branch `epic-1`, Virginia, plano Free, Auto-Deploy Off, Health Check Path `/health`.
- `DATABASE_URL` configurada só no painel. Sem `PORT` nem `SPA_DIST_DIR` manuais, sem CORS,
  sem disco, sem Pre-Deploy Command e sem Docker Command próprio (CA1, CA8).
- Commit publicado (A): `0736ec1c536bef0fee3fe1072778fc859dc9de1a`.

### Primeiro deploy (T7; CA1 a CA3)

- O build Docker terminou; o Alembic conectou com `PostgresqlImpl` e aplicou
  `Running upgrade -> 0001, baseline`, antes do uvicorn (CA3).
- O uvicorn subiu em `0.0.0.0:10000`; o serviço ficou `Live` e `/health` respondeu 200 (CA2).
- Usuário não root e ausência de disco: o plano Free não oferece shell, então não os
  inspecionei no Render. Ficam garantidos por `USER app` no `Dockerfile` e pelo smoke da 1.3.
- Tempo de inicialização (Q4): não medi.

### Validação HTTP pública (T8; CA4, CA5)

Conferidas por mim no navegador e no terminal:

- `/health` → 200 JSON `{"status":"ok"}`.
- `/` e `/lots/qualquer-coisa` → SPA; a página mostrou "Serviço no ar".
- `/api/docs` → Swagger funcional; `/api/openapi.json` → JSON, só `/health` no schema.
- `/api/nao-existe` → 404 JSON, não a SPA.
- O navegador carregou os assets JS e CSS com sucesso. Depois, o agente fez `GET` do
  `index.html` e dos dois assets citados nele (sem efeito colateral):

  ```
  / ........................... status=200 content-type=text/html; charset=utf-8
  /assets/index-Du5uwTvN.js ... status=200 content-type=text/javascript; charset=utf-8
  /assets/index-Bd_ia25c.css .. status=200 content-type=text/css; charset=utf-8
  ```

- Não capturei, nesta etapa, uma checagem de cabeçalhos `Access-Control-*` por `curl`. Não
  há `CORSMiddleware` no código nem configuração de CORS no Render, e a SPA, a API e o
  WebSocket usam o mesmo host.

### Cookie público (CA7)

- 1ª chamada em `/api/infra-check/cookie`, no navegador: `{"cookie_received": false}`.
- 2ª chamada no mesmo navegador: `{"cookie_received": true}`. O round-trip funcionou.
- `document.cookie.includes('__Host-infra_check')` → `false`, coerente com `HttpOnly`.
- Conferi visualmente no navegador: `__Host-infra_check`, `Secure`, `HttpOnly`,
  `SameSite=lax` (o Starlette emite em minúsculas; equivale a `Lax`), `Path=/`, sem `Domain`
  e `Max-Age=600`.
- Nenhum JWT nem usuário; o servidor não guarda nada. Não capturei o `Set-Cookie` por
  `curl` nesta etapa.

### WebSocket público (CA5, CA6)

Endpoint `wss://casa-de-leiloes-i1xr.onrender.com/api/infra-check/ws`.

- **Console do Edge:** a conexão abriu, o handshake apareceu como HTTP 101, enviei `ping`,
  recebi `echo:ping` e o cliente observou o fechamento com código `1006`.
- **Terminal, com a biblioteca `websockets`** (segundo teste independente): recebi
  `echo:ping`; código de fechamento observado `1006`, motivo vazio.
- **Comprovado:** o handshake `wss://` funciona atrás do proxy do Render, e o tráfego
  funciona nos dois sentidos (cliente → servidor e servidor → cliente).
- **Ponto em aberto:** o código publicado envia `close(1000)` logo depois do eco, e nos
  testes locais o fechamento foi `1000`; no caminho público, dois clientes independentes
  observaram `1006`. **Não determinei a causa** dessa diferença e não a apresento como
  comportamento garantido do Render. Decidi documentar o resultado real em vez de alterar
  o código sem evidência da causa; nada foi alterado para esconder o resultado.
- Não executei, nesta etapa, o teste público com `Origin` estrangeiro; a recusa de `Origin`
  é coberta pelos testes locais.

### Redeploy (T9; CA9)

Validação confirmada por mim, com um redeploy manual do mesmo commit: o serviço voltou
normalmente, o Alembic executou de novo, a migration `0001` não foi reaplicada, o uvicorn
voltou a subir e o serviço continuou funcional. Isso mostra que a migration é idempotente
no redeploy. Não colei as linhas de log nesta story.

### Cold start (T10; CA10)

Cold start não observado nesta validação. Não houve espera artificial (P14), então não há
tempo medido. A medição fica para a Story 6.4.

### Limitações observadas

- O PostgreSQL gratuito expira em 23/11/2026 (data do painel).
- O encerramento do WebSocket público foi observado como `1006` (ponto em aberto acima).
- Cold start não observado.

## Notas para o desenvolvedor

- Registrar as rotas novas antes de `register_spa_routes`; o teste existente
  reprova se o fallback deixar de ser a última rota.
- Uma rota WebSocket não é capturada pelo fallback HTTP da SPA, mas o caminho
  deve ficar sob `/api` (AD-30) para nunca colidir com rotas do cliente.
- O cookie recebe `Secure` explicitamente; não depender do esquema visto pela
  aplicação atrás do proxy (P8).
- O `PORT` vem do Render; não codificar valor nem registrá-lo como fato antes
  de vê-lo no log.
- Nunca logar `DATABASE_URL`; a normalização já esconde a URL nos erros.
- Nenhuma dependência nova é esperada (`uvicorn[standard]` já traz suporte a
  WebSocket).
- Números (tempos de build, de inicialização, de cold start) só de medição
  real, com o comando usado.

## Referências

- `_bmad-output/planning-artifacts/epics.md`: Story 1.4 e D1 = A.
- `docs/ARQUITETURA.md`: AD-2, AD-10, AD-11, AD-14, AD-27, AD-28, AD-29, AD-30;
  questões 2, 4 e 10; pontos de atenção do banco gratuito e das horas
  gratuitas.
- `docs/CRONOGRAMA.md`: Dia 2.
- `_bmad-output/implementation-artifacts/1-2-postgresql-com-bancos-isolados-e-migrations.md`
  (D1, D3, D4; `/health` sem banco).
- `_bmad-output/implementation-artifacts/1-3-spa-na-mesma-origem-e-imagem-multi-stage.md`
  (D1 a D7; smoke da imagem; itens adiados para a 1.4).
