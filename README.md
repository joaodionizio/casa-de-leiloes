# ÁTRIO — Leilões de Arte

## Projeto

Desenvolvi uma casa de leilões online para o Desafio Elite Dev (Verzel): o
leiloeiro escolhe uma obra de domínio público do Art Institute of Chicago (AIC),
cria o lote e acompanha seu resultado; licitantes depositam saldo simulado,
disputam lances ao vivo e compartilham o comprovante. Qualquer visitante consulta
vitrine, sala e auditoria pública do histórico. Dinheiro é fictício.

Decidi manter API, WebSocket e SPA na mesma origem e um único processo de aplicação.
Descartei serviços distribuídos na escala do desafio. O nome ÁTRIO substituiu
“Casa de Leilões” em 25/10/2026; repositório, bancos e módulos mantêm os nomes técnicos.

**Candidato local em 29/10/2026:** inclui WebSocket, liquidação, auditoria,
comprovante, Meus arremates, refinamento visual e cadastro dos dois papéis.
**Publicado:** a última evidência pública registrada é a recuperação dos Epics
2+3, `main`, commit `3d3ea97`, em <https://casa-de-leiloes-i1xr.onrender.com>.
Isso não comprova publicação das funcionalidades posteriores. A validação final
no ambiente publicado (6.4) e o review agregado do Epic 6 estão pendentes.

Navegação: [Instalação](#instalacao) · [Execução](#execucao) ·
[Verificação](#verificacao) · [Avaliação](#avaliacao) · [Cadastro](#cadastro) ·
[Deploy](#deploy) · [Arquitetura](#arquitetura) · [Segurança](#seguranca) ·
[Surpresas e limites](#limites) · [Uso de IA](docs/uso_de_ia.md).

## Funcionalidades

React + TypeScript/Vite no frontend, FastAPI/Python no backend e PostgreSQL.
Implementei cadastro de BIDDER/AUCTIONEER, login/logout e contas demo; busca de
obras públicas da AIC, criação e cancelamento de lote próprio sem lances;
Vitrine, Sala ao vivo com WebSocket/reconexão, carteira e depósitos simulados,
lances transacionais e anti-sniping; settlement, resultado no painel, auditoria
pública, comprovante compartilhável e Meus arremates (participações e vitórias).
A identidade ÁTRIO e a responsividade acompanham esses fluxos. Busca/filtro de
lotes, cancelamento com estorno e dark mode não fazem parte desta entrega.

<a id="instalacao"></a>
## Instalação e ambiente

Todos os blocos de comandos abaixo partem da **raiz do repositório**; uso subshell
para que `cd` não altere os próximos comandos. Em terminais separados, repita os
exports de ambiente. Não coloque segredos em commits, logs ou capturas.

Pré-requisitos verificáveis:

| Ferramenta | Referência do projeto | Conferência |
| --- | --- | --- |
| Python | 3.13 na imagem; `requires-python >=3.13` | `python3 --version` |
| uv | 0.13.5 fixada na imagem | `uv --version` |
| Node.js/npm | Node 24 na imagem; npm acompanha a instalação | `node --version` e `npm --version` |
| Docker e Compose v2 | PostgreSQL 18 em `compose.yaml` | `docker info` e `docker compose version` |

As versões de dependências estão nos lockfiles; React/TypeScript/Vite no
[package.json](frontend/package.json) e dependências Python no
[pyproject.toml](backend/pyproject.toml). Não há chave da AIC para configurar.

```bash
( cd backend && uv sync --frozen )
( cd frontend && npm ci )
docker compose up -d --wait postgres
```

O Compose expõe PostgreSQL somente em `127.0.0.1:5432` e cria
`casa_de_leiloes_dev` e `casa_de_leiloes_test` em volume persistente. A criação dos
bancos roda apenas em volume novo. Para montar suas URLs locais, use os parâmetros
do Compose; abaixo **todos os valores entre `<...>` são placeholders a substituir**,
inclusive a senha do banco, que não reproduzo aqui.

```bash
export DATABASE_URL='postgresql://<usuario-local>:<senha-local>@127.0.0.1:5432/casa_de_leiloes_dev'
export TEST_DATABASE_URL='postgresql://<usuario-local>:<senha-local>@127.0.0.1:5432/casa_de_leiloes_test'
export APP_ORIGIN='http://localhost:5173'
export JWT_SECRET='<substitua-por-segredo-aleatorio-jwt>'
export AUDIT_HMAC_SECRET='<substitua-por-segredo-aleatorio-auditoria>'
export PSEUDONYM_SECRET='<substitua-por-segredo-aleatorio-pseudonimo>'
```

| Variável real | Contrato |
| --- | --- |
| `DATABASE_URL` | Obrigatória; PostgreSQL (`postgresql://` ou `postgresql+psycopg://`). |
| `TEST_DATABASE_URL` | Banco dedicado aos testes, distinto do desenvolvimento; a suíte recria seu schema. Nunca use produção. |
| `APP_ORIGIN` | Obrigatória; esquema, host e porta, sem caminho/query/credenciais. HTTPS fora de localhost/127.0.0.1/::1. |
| `JWT_SECRET` | Obrigatória; pelo menos 32 caracteres, aleatório forte. |
| `AUDIT_HMAC_SECRET` | Obrigatória; pelo menos 32 bytes UTF-8, aleatório forte, assina âncoras; exigida também pelo seed. |
| `PSEUDONYM_SECRET` | Obrigatória; pelo menos 32 bytes UTF-8, aleatório forte, pseudônimos por lote. |
| `SPA_DIST_DIR` | Opcional no dev; diretório com `index.html`. Relativo a `backend/`, independentemente do diretório do processo. Imagem define `/app/frontend-dist`. |
| `PORT` | Consumida pelo `start.sh`; padrão 8000, fornecida pelo Render em produção. |
| `VERIFY_E2E` | `1` inclui Playwright no verify; somente verificação. |
| `E2E_REAL_BASE_URL` | Opt-in dos cenários contra stack real; somente testes. |

Os três segredos precisam ser diferentes entre si. Gere cada um com um gerador
criptográfico e preserve os de integridade entre inicializações; tamanho não garante
entropia. A configuração também aceita `backend/.env` local, mas os exports têm
precedência. Não é necessário abrir ou copiar arquivos dotenv para seguir este roteiro.
Não existem variáveis de CORS, `APP_ENV` ou credencial AIC exigidas pelo código.

### Migrations e seed

```bash
( cd backend && uv run alembic upgrade head )
( cd backend && uv run alembic current )
( cd backend && uv run python -m app.seed )
```

Head do candidato: `0007` (baseline, usuários, lotes, carteiras, lances,
cancelamento e settlement/comprovantes). Alembic usa `DATABASE_URL`; para migrar
explicitamente o banco de teste, com as URLs já exportadas:

```bash
( cd backend && DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head )
```

O pytest prepara/recria o schema de teste automaticamente; uma migration manual não
preserva dados desse banco entre sessões de pytest. Não execute pytest enquanto
um smoke estiver usando o mesmo banco.

O seed é idempotente: cria somente contas ausentes, nunca troca senha/ID de conta
existente; completa carteiras ausentes com zero sem alterar saldos existentes;
insere demo somente se não houver demo futuro, não cancelado e com âncora não nula.
Usa trava consultiva para seeds concorrentes. Não altera/apaga/reativa lotes nem
reassina legado. A fixture é local, sem chamada à AIC, sem lances ou saldo inicial.
`DATABASE_URL` e `AUDIT_HMAC_SECRET` bastam para o seed; a aplicação exige as demais
configurações. Para apagar **os dois bancos locais** e recriar o volume, o comando
destrutivo é `docker compose down -v`; não faz parte da instalação normal.

<a id="execucao"></a>
## Executar em desenvolvimento e em uma origem

Dois terminais, ambos na raiz e com o ambiente acima:

```bash
# Terminal 1: migrations e seed já aplicados
( cd backend && uv run uvicorn app.main:app --port 8000 )
```

```bash
# Terminal 2
( cd frontend && npm run dev )
```

Abra <http://localhost:5173>. Vite usa porta fixa 5173 (`strictPort`) e faz proxy
`/api`, `/health` e `/ws` (WebSocket) para `http://127.0.0.1:8000`. Se a porta
estiver ocupada, falha; não troque host/porta sem ajustar `APP_ORIGIN`.
Swagger: <http://localhost:5173/api/docs>; schema: `/api/openapi.json`.
`GET /health` retorna `200 {"status":"ok"}` sem consultar o banco.

Para testar o build servido pelo próprio FastAPI, como na imagem:

```bash
( cd frontend && npm run build )
( cd backend && APP_ORIGIN=http://localhost:8000 SPA_DIST_DIR=../frontend/dist \
  uv run uvicorn app.main:app --port 8000 )
```

Abra <http://localhost:8000>. Sem `SPA_DIST_DIR`, só a API é servida; diretório
inválido ou sem `index.html` impede startup. API e SPA são publicadas juntas.

<a id="verificacao"></a>
## Verificação local e E2E opt-in

Com dependências instaladas e Docker ativo, na raiz:

```bash
./verify.sh
```

Roda Ruff/lint/formato, sobe PostgreSQL, pytest com integração real, ESLint,
TypeScript, testes puros (`node --test`), build Vite e build Docker; para na
primeira falha. Não executa a imagem nem comprova deploy. Fornece padrões locais
para URLs de banco e `APP_ORIGIN` quando ausentes; exports já definidos prevalecem.
Pytest gera segredos próprios, não usa os operacionais. Confira sempre que
`TEST_DATABASE_URL` aponta ao banco descartável e distinto de desenvolvimento.

```bash
# Focais, a partir da raiz
( cd backend && uv run pytest )
( cd frontend && npm test )
# Navegador Chromium (instalar uma vez)
( cd frontend && npx playwright install chromium )
( cd frontend && npm run test:e2e )
# Gate completo incluindo navegador
VERIFY_E2E=1 ./verify.sh
```

Playwright padrão usa API simulada por interceptação e `vite preview` na porta
4173. Prova navegação, foco, layout e interações, não integração com banco/AIC.
Cenários `real-stack.spec.ts` são opt-in por `E2E_REAL_BASE_URL`. Para executá-los,
use exclusivamente o banco `_test` preparado, sem pytest concorrente; o seed no
teste e o servidor real podem ser iniciados assim:

```bash
( cd backend && DATABASE_URL="$TEST_DATABASE_URL" uv run python -m app.seed )
( cd frontend && npm run build )
( cd backend && DATABASE_URL="$TEST_DATABASE_URL" APP_ORIGIN=http://localhost:8765 \
  SPA_DIST_DIR=../frontend/dist uv run uvicorn app.main:app --port 8765 )
```

Em outro terminal, na raiz:

```bash
( cd frontend && E2E_REAL_BASE_URL=http://localhost:8765 npm run test:e2e -- real-stack )
```

Estes são comandos para reprodução, não resultados novos desta entrega documental.
O [gate anterior da 6.2A](_bmad-output/specs/spec-story-6-2a-cadastro-de-usuarios/implementation-evidence.md)
registra verify com E2E e smoke local aprovados, distinguindo cenários não executados.

<a id="avaliacao"></a>
## Contas demo e roteiro de avaliação

Senha **pública**, igual para as três: `Demo123!`. O seed preserva senhas de contas
já existentes; contas compartilhadas podem ter saldo/estado diferente do inicial.

| Conta | Papel | Área |
| --- | --- | --- |
| `auctioneer@example.com` | `AUCTIONEER` | Criar lote e Meus lotes |
| `bidder1@example.com` | `BIDDER` | Carteira e Meus arremates |
| `bidder2@example.com` | `BIDDER` | Carteira e Meus arremates |

Use perfis de navegador distintos (duas abas normais compartilham cookie): um
leiloeiro e dois licitantes. Repita este roteiro na URL pública somente depois de
publicar e validar o candidato; a evidência antiga 2+3 não cobre o fluxo inteiro.

1. **Visitante:** abra `/`, entre em um lote e consulte a sala sem login. O demo
   nasce com 72 h, lance inicial R$ 100,00 e incremento R$ 10,00: serve para
   demonstrar lances, não para aguardar um encerramento rápido.
2. **Leiloeiro:** entre em `/login`; abra `/auctioneer/lots/new`, busque uma obra
   (por exemplo `Monet`), selecione, informe lance inicial/incremento e término
   futuro, revise e publique. Início omitido significa agora no banco. Não há
   duração mínima; deixe margem para preencher e operar o roteiro. A criação
   depende da AIC; o demo usa fixture e funciona sem a busca externa.
3. **Meus lotes:** em `/auctioneer/lots`, confira o novo lote, abra sua sala e
   copie o link. Para demonstrar cancelamento, crie outro lote sem lances e
   cancele-o antes do fim: continua no painel, some do público. Lote com lances
   não pode ser cancelado nesta entrega.
4. **Dois licitantes:** entre separadamente com bidder1 e bidder2. Em
   `/bidder/wallet`, deposite saldo simulado suficiente para os lances (por
   exemplo R$ 1.000,00 em cada, conforme o lote). Carteiras novas começam em zero.
5. **Disputa:** bidder1 oferece o mínimo; observe aceite, reserva/comprometido e
   posição. Bidder2 supera pelo incremento; observe atualização WS nas salas,
   posição de superado e liberação da reserva anterior. Teste abaixo do mínimo,
   saldo insuficiente e o líder tentar cobrir a si mesmo: a recusa explica o motivo.
6. **Prazo:** perto do fim, lance válido com `0 < restante <= 2 min` soma 2 min ao
   fim vigente, inclusive exatamente 2 min. É cumulativo, renovável e sem teto;
   pare os lances e aguarde o término efetivo para observar liquidação. O contador
   visual não decide aceite. Desconecte/reconecte para observar snapshot atualizado;
   nenhum lance é reenviado automaticamente.
7. **Resultado:** scheduler apura o lote íntegro vencido. Pode aparecer
   “Encerrado, apurando resultado” antes da liquidação. Atualize Meus lotes:
   vencedor por pseudônimo, valor e total recebido devem refletir o settlement.
   O vencedor tem total e comprometido debitados; o leiloeiro recebe o valor.
   Sem lances, resultado é sem arremate e não há comprovante.
8. **Vencedor:** abra `/bidder/wins` (Meus arremates), confira valor/data e siga o
   comprovante em `/lots/{uuid}/receipt`. Copie o link e abra sem login: mostra
   dados pseudonimizados, quantidade de lances e hash final, sem identidade real.
9. **Auditoria:** em `/lots/{uuid}/audit`, visitante verifica cadeia e âncora e vê
   histórico completo. “Integridade verificada” depende da verificação no servidor;
   os 50 lances recentes da sala não substituem esta auditoria. Não adultere o banco
   compartilhado para demonstrar falha; os testes críticos cobrem adulteração.
10. **Papéis e sessão:** leiloeiro não deposita/não dá lance, licitante não cria
    lote. Saia e confira o acesso público; áreas privadas voltam a pedir login.

Rotas REST correspondentes: `POST /api/lots`, `GET /api/lots/mine`,
`GET /api/wallet`, `POST /api/wallet/deposit`, `POST /api/lots/{lot_id}/bids`,
`GET /api/me/wins`, `GET /api/lots/{lot_id}/receipt` e
`GET /api/lots/{lot_id}/audit`. Não existe endpoint público para forçar liquidação.

<a id="cadastro"></a>
## Cadastro e autenticação

Em `/register`, escolha explicitamente Licitante (`BIDDER`) ou Leiloeiro
(`AUCTIONEER`), preencha e-mail e senha. Não há campo Nome. O cadastro público
`POST /api/auth/register` aceita apenas `email`, `password`, `role`; cria usuário
e carteira zero na mesma transação, para ambos os papéis. Carteira do leiloeiro
não libera acesso a depósito ou lances; ela recebe o produto dos seus lotes vendidos.

E-mail é normalizado com trim/lowercase, até 254 caracteres e formato mínimo;
não há confirmação de e-mail. Senha tem 8–1024 caracteres, sem regra de composição,
e hash Argon2id. Duplicidade retorna `409 email_already_registered`; aceitei
explicitamente essa enumeração na demonstração. Cadastro retorna `201 {email, role}`,
sem cookie/token, e leva ao login com confirmação. Não autentica automaticamente.
Não há troca/recuperação de senha, verificação de titularidade ou controle administrativo.

Login (`POST /api/auth/login`) põe JWT HS256 de 8 h em cookie HttpOnly,
SameSite=Lax, Path=/, sem Domain; nunca em URL, corpo ou localStorage. Em HTTPS,
usa `__Host-auction_session` com Secure; em HTTP local, `auction_session`.
`GET /api/me` identifica a sessão; `POST /api/auth/logout` apaga o cookie.
Não há revogação de JWT: token copiado continua válido até `exp` mesmo após logout.

<a id="deploy"></a>
## Imagem e deploy no Render

O [Dockerfile](Dockerfile) multi-stage gera o frontend com Node 24 e executa API
com Python 3.13/uv 0.13.5, usuário sem root. A imagem serve API, SPA e WS em uma
origem, sem dotenv nem testes. Para construir e rodar localmente, com os exports
já configurados e PostgreSQL Compose disponível:

```bash
docker build -t casa-de-leiloes .
# Configure esta URL com host postgres (rede Compose), sem divulgar a senha.
export DOCKER_DATABASE_URL='postgresql://<usuario-local>:<senha-local>@postgres:5432/casa_de_leiloes_dev'
docker run --rm --network casa-de-leiloes_default -p 127.0.0.1:9000:9000 \
  -e PORT=9000 -e APP_ORIGIN=http://localhost:9000 \
  -e JWT_SECRET -e AUDIT_HMAC_SECRET -e PSEUDONYM_SECRET \
  -e DATABASE_URL="$DOCKER_DATABASE_URL" casa-de-leiloes
```

O nome da rede pressupõe o nome padrão do projeto Compose; ajuste se executou com
outro nome. `DOCKER_DATABASE_URL` é somente uma variável auxiliar do shell deste
exemplo; a aplicação recebe `DATABASE_URL`.

A inicialização executa `alembic upgrade head` → seed existente → lifespan com
catch-up dos vencidos → scheduler → tráfego. Erro em migration/seed impede subir;
configuração inválida ou falha sistêmica no banco também bloqueia startup.
Falhas individuais de apuração têm cooldown e não impedem os demais lotes.
Uvicorn direto exige migrations/seed prévios. Use **um processo**, pois as salas
WS e os controles do scheduler são locais à memória, sem Redis/outbox.

A operação no Render é manual: Web Service Docker + PostgreSQL, branch `main`,
Auto-Deploy desabilitado no roteiro, health check `/health`. Configure
`DATABASE_URL` com a URL interna do banco, `APP_ORIGIN` com a origem HTTPS exata e
os três segredos distintos **antes** de publicar. `PORT` vem da plataforma;
`SPA_DIST_DIR` vem da imagem. Não exporte variáveis de teste para produção.
Preserve segredos de integridade existentes: rotação não é suportada.

Sigo os gates de [FECHAMENTO-DE-EPICO](docs/FECHAMENTO-DE-EPICO.md): candidato,
verify pertinente, review agregado independente e decisões humanas antes de
merge/push/deploy manuais; depois acompanho migrations/seed/startup e smoke
público de frontend/API/WS/cookies/papéis e do roteiro acima. `/health` sozinho
não prova acesso ao banco ou o funcionamento dos fluxos. Não faça downgrade ou
reassinatura de histórico em produção para contornar falha.

O [registro de recuperação 2+3](docs/DEPLOY-RECUPERACAO-EPICS-2-3.md) preserva a
confirmação humana do deploy antigo e os itens não individualizados. No primeiro
deploy, região Virginia/US East, plano Free e PostgreSQL 18 foram registrados;
a vigência atual do plano/banco exige conferência manual. Não houve nova inspeção do painel nesta entrega.
Cold start pode ocorrer no plano gratuito, sem duração medida/prometida.
Não realizei publicação nem smoke público na Story 6.3.

<a id="arquitetura"></a>
## Arquitetura e contratos principais

| Parte | Responsabilidade |
| --- | --- |
| `backend/app` | FastAPI, políticas de acesso, domínio e transações SQLAlchemy síncronas/psycopg 3; banco em worker/threadpool quando chamado de fluxo async. |
| `backend/migrations` | Schema PostgreSQL real versionado com Alembic. |
| `frontend/src` | React, TypeScript e Vite; History API própria, contratos HTTP/WS e tokens CSS. |
| `frontend/e2e` | Playwright com API simulada e cenários reais opt-in. |
| `docker/postgres-init` | Bancos de desenvolvimento e teste isolados no Compose. |
| `verify.sh` | Gate local que para na primeira falha. |

Dinheiro usa centavos inteiros (`BIGINT`, sufixo `_cents`), sem float; faixa de
1 a 9007199254740991 por valor positivo, com limite correspondente de saldo.
Disponível = total − comprometido. Lance trava lote antes de carteiras (por
`user_id` crescente), lê um `clock_timestamp()` PostgreSQL após a trava e confirma
histórico, saldo, líder, reserva e anti-sniping numa transação. O navegador nunca
decide fase ou aceite. Fase: agendado antes do início, ao vivo em
`starts_at <= now < ends_at`, encerrado a partir do fim.

Liquidação usa a mesma trava e revalida fim vigente/integridade; é idempotente,
com `UNIQUE(lot_id)` no comprovante. O scheduler espera 2 s após cada ciclo;
isso não promete apuração em 2 s sob banco lento/cooldown. Catch-up no startup
trata vencidos antes de liberar tráfego. **GET/HEAD/OPTIONS nunca liquidam**;
lance vencido só recusa, sem liquidar em outra transação.

WebSocket público `/ws/lots/{lot_id}` envia snapshot ao conectar/reconectar e
atualizações após commit; lances são exclusivamente POST REST. O cliente usa
heartbeat/reconexão e nunca reenvia lances. Painéis privados e vitrine são
fotografias de leitura, não têm a mesma atualização contínua da sala.

A obra tem snapshot essencial persistido no lote; dados de negócio, auditoria e
comprovante não dependem de nova consulta à AIC. Bytes da imagem continuam externos,
via proxy público same-origin `GET /api/catalog/images/{image_id}`, host/caminho
fixos e sem cache persistente; falha mostra placeholder local. Criar lote
reconsulta a AIC para validar domínio público e imagem; buscar não persiste lote.

As decisões, alternativas e limites completos estão em
[ARQUITETURA](docs/ARQUITETURA.md), [enunciado](docs/desafio-elite-dev.md),
[DESIGN](_bmad-output/planning-artifacts/DESIGN.md) e
[EXPERIENCE](_bmad-output/planning-artifacts/EXPERIENCE.md).

<a id="seguranca"></a>
## Segurança e integridade

Cada rota declara política; backend impõe autenticação e papel, além das guardas
do frontend. Sem sessão válida, áreas autenticadas retornam 401; papel errado, 403.
Escritas `/api` exigem `Content-Type: application/json` (inclusive logout/cancelar
sem corpo) e `Origin` correspondente a `APP_ORIGIN`; só na ausência de Origin usa
Referer. Sem ambos, 403; origem divergente, 403; mídia incorreta, 415. Não há
CORS permissivo. No WS, Origin presente precisa corresponder; ausente é aceito.

Erros usam envelope `{status, code, message}`; validação pode incluir
`details: [{loc, type}]`. 500 é genérico, sem stack/SQL/segredos para o cliente.
A revisão de segurança local está documentada na
[evidência da 6.1](_bmad-output/specs/spec-story-6-1-revisao-de-seguranca-e-de-erros/implementation-evidence.md);
a conferência no ambiente publicado continua pendente, sem alegação de aprovação pública.

Cadeia SHA-256 encadeia os lances; âncora HMAC autentica contagem/hash final com
segredo fora do banco. Auditoria pública verifica o histórico completo em snapshot
coerente e divulga somente pseudônimos por lote, valores, instantes e hashes,
sem ID/e-mail real ou HMAC. O histórico recente da sala é limitado a 50 e não
constitui auditoria. Comprovante público existe apenas para lote vendido apurado;
Meus arremates lista suas participações e vitórias; o comprovante aparece nas vitórias liquidadas.

A proteção detecta alteração, inserção, remoção e truncamento sem capacidade de
reassinar. **Não** prova imutabilidade absoluta: segredo comprometido permite
reassinar; rollback coordenado de cadeia e âncora antigas válidas não é detectado
sem âncora externa; controle total de aplicação/banco/segredos pode falsificar a
verificação. A âncora v1 não cobre todos os termos do lote, dono ou saldos. Não
prometo proteção contra controle total do sistema nem rotação de integridade.

<a id="limites"></a>
## Comportamentos que podem surpreender e limitações

- **Anti-sniping AD-5 vigente:** `0 < ends_at - now <= 2 min` soma 2 min ao fim
  vigente; exatamente 2 min também aplica. É cumulativo, renovável e sem teto;
  fim 15:00 + lance 14:59:20 → 15:02; novo lance 15:01:10 → 15:04. A decisão
  intermediária `now + 2 min` foi revogada em 27/10/2026. Recusa não estende e lote
  vencido nunca reabre; frontend/WS aplicam o `ends_at` persistido.
- **Liquidação tardia:** scheduler/catch-up fazem o fechamento, nunca GET. Queda
  do serviço adia resultado; retomada recupera os pendentes. Cooldown/integridade
  podem manter “Encerrado, apurando resultado”. Atualizar a página não liquida.
- **Commit e WS:** falha de publicação ou processo morto entre commit e evento
  não desfaz a escrita financeira. Reconnect/snapshot recupera o estado; não há
  outbox/replay. Publicação pós-commit pode atrasar o HTTP 201 e não tem prazo global.
- **Resultado incerto e duplicidade:** erro de rede após commit não comprova
  falha. Não há `Idempotency-Key`; confira saldo, sala e Meus lotes antes de repetir
  depósito, lance ou criação. O cliente não reenvia automaticamente.
- **Logout:** apaga cookie sem revogar JWT; token copiado vale até `exp` (8 h).
  Sem rate limiting de login/cadastro, bloqueio de força bruta, recuperação ou
  confirmação de e-mail; contas demo e papéis de cadastro são públicos.
- **Museu e imagem:** indisponibilidade externa impede busca/criação, sem afetar
  snapshot de lotes existentes. Cada imagem chama o proxy externo; pode falhar por
  indisponibilidade/cota e cair em placeholder. 
- **Histórico e segredos:** segredo comprometido, rollback coordenado e controle
  total limitam SHA-256/HMAC como explicado acima. Lote legado sem âncora não é
  reassinado automaticamente e operações protegidas recusam 409. Trocar
  `AUDIT_HMAC_SECRET` invalida âncoras; trocar `PSEUDONYM_SECRET` bloqueia lotes com
  lances; trocar JWT derruba sessões. Não há ferramenta de reparo/reautenticação.
- **Escala:** um processo, conexões WS públicas sem teto total, sem lock/statement
  timeout global, fila de trava e conferência O(n) do histórico; listas públicas,
  Meus lotes e Meus arremates sem paginação. Aceitos na escala do desafio.
- **Carteira:** saldo simulado, sem gateway ou histórico de movimentos; leiloeiro
  recebe settlement mas não tem tela de depósito. Contas demo são compartilhadas;
  seed não zera saldo e não substitui demo vencido até a próxima inicialização.
- **Vitrine/rotas:** fase reflete `as_of`; recarregue para renovar a fotografia.
  History API aceita rotas conhecidas; fallback SPA pode responder 200 para caminho
  desconhecido, exibindo página não encontrada; `/api/*` nunca deve servir HTML.
- **Render:** cold start sem duração inventada e vigência de banco/plano dependem
  da conta; `/health` verde não prova banco, autenticação ou WS.
- **Escopo final:** 6.5 busca/filtro de lotes, 6.6 cancelamento com estorno e 6.7
  dark mode foram cortadas da entrega; não são controles prometidos na interface.
  6.1 mantém pendência publicada, 6.2A e 6.3 aguardam agregado, Epic 6 segue
  in-progress e 6.4 não foi executada.

Registrei decisões, intervenções humanas, correções, gates e limites em
[uso_de_ia](docs/uso_de_ia.md). Pendências históricas e sua vigência estão em
[deferred-work](_bmad-output/implementation-artifacts/deferred-work.md);
o [sprint](_bmad-output/implementation-artifacts/sprint-status.yaml) distingue
implementação local, review e publicação.
