# ÁTRIO — Leilões de Arte

Casa de leilões de obras de arte de domínio público do Art Institute of Chicago,
com lances em tempo real, carteira simulada, anti-sniping, liquidação, auditoria
de integridade e comprovante compartilhável. Todos os valores são fictícios.

**Aplicação publicada: [abrir o ÁTRIO](https://casa-de-leiloes-i1xr.onrender.com).**

**Requisitos obrigatórios e opcionais concluídos e validados em produção.**

| Autoria | Desafio | Stack principal |
| --- | --- | --- |
| João Luís Dionízio | Elite Dev — Verzel | Python/FastAPI · React/TypeScript/Vite · PostgreSQL |

## Comece por aqui — roteiro de avaliação

Acesse a aplicação publicada, sem instalar nada. No Render gratuito, a primeira
carga pode demorar por cold start; aguarde a inicialização.

Senha pública das três contas demo: **`Demo123!`**.

| Conta | Papel | Acesso principal |
| --- | --- | --- |
| `auctioneer@example.com` | Leiloeiro | Criar lote e Meus lotes |
| `bidder1@example.com` | Licitante | Carteira e Meus arremates |
| `bidder2@example.com` | Licitante | Carteira e Meus arremates |

Use três perfis de navegador ou sessões isoladas: **abas normais compartilham
cookie**, e janelas anônimas do mesmo perfil também podem compartilhar sessão.
As contas são compartilhadas; saldos e lotes podem ter mudado com outros testes.

1. **Visite a Vitrine sem login.** Abra uma obra e sua Sala; auditoria e
   comprovantes de lotes vendidos também são públicos.
2. **Busque e filtre.** Combine título, artista ou data textual com Todos,
   Ao vivo, Próximos e Encerrados. Caixa e acentos não impedem a busca; filtrar
   usa o snapshot carregado, sem requests extras. Experimente também o tema escuro.
3. **Crie um lote como leiloeiro.** Em Criar lote, busque `Monet` na AIC,
   selecione uma obra, defina inicial de R$ 100,00 e incremento de R$ 10,00.
   Deixe o início omitido para começar agora e o término cerca de 5 minutos à
   frente, com margem para operar. Copie o link da Sala em Meus lotes.
4. **Deposite como cada licitante.** Na Carteira, deposite saldo simulado
   suficiente, por exemplo R$ 1.000,00 em cada conta. Confira total,
   comprometido e disponível; as ajudas explicam a diferença.
5. **Dispute entre as duas sessões.** Bidder1 oferece o mínimo; bidder2 supera
   pelo incremento. A reserva passa ao novo líder e a anterior volta ao disponível.
6. **Observe o tempo real.** Mantenha as Salas abertas: valor, histórico e posição
   “Você está ganhando” / “Você foi superado” mudam por WebSocket sem reload.
   Uma tentativa abaixo do mínimo ou do próprio líder recebe motivo de recusa.
7. **Demonstre o anti-sniping.** Um lance válido com até 2 minutos restantes
   soma 2 minutos ao término vigente. É cumulativo: novos lances na janela
   prorrogam novamente. Pare de lançar para permitir o encerramento.
8. **Confira a liquidação.** Aguarde o fim efetivo e a apuração automática;
   “Encerrado, apurando resultado” pode aparecer nesse intervalo. Recarregue
   Meus lotes/Carteira: o vencedor é debitado e o leiloeiro recebe o valor.
9. **Compartilhe o comprovante.** Como vencedor, abra Meus arremates e copie o
   link do comprovante. Em sessão sem login, veja obra, valor, pseudônimo e hash
   final. Lote sem lances encerra sem vencedor nem comprovante.
10. **Audite o histórico.** Pelo link da Sala, abra a auditoria pública: ela
    confere todos os lances e a âncora de integridade. Os 50 lances recentes da
    Sala são apenas uma visualização parcial do histórico.
11. **Teste cancelamento e estorno em outro lote.** Antes do fim, dê um lance e
    cancele como dono em Meus lotes. O total do líder permanece igual, o
    comprometido é liberado e o histórico continua auditável. O lote sai da
    Vitrine; lotes encerrados/liquidados não podem ser cancelados.
12. **Confira sessão e papéis.** Leiloeiro não deposita nem dá lance; licitante
    não cria lote. Faça logout e confira que as áreas privadas pedem login.

O seed oferece um lote demo com janela inicial de 72 h, sem saldo ou lances
iniciais. Use-o para explorar a disputa; crie o lote curto do passo 3 para ver a
liquidação. Vitrine e painéis privados precisam de recarga para renovar seus dados.

## O que foi entregue

Os itens abaixo atendem ao [enunciado do desafio](docs/desafio-elite-dev.md).

| Requisito obrigatório | Implementação entregue |
| --- | --- |
| Dois papéis e autenticação | Login/logout com cookie; permissões de leiloeiro e licitante impostas no backend. |
| Integração com API pública | Busca de obras AIC de domínio público e criação com imagem, atributos e condições do lote. |
| Vitrine e painel do leiloeiro | Ao vivo, agendados e encerrados; cancelados fora da Vitrine; gestão de lotes próprios, resultado e total recebido. |
| Sala em tempo real | WebSocket, histórico recente, contador, posição do licitante e reconexão. |
| Carteira e lances | Depósito simulado; saldo total, comprometido e disponível; mínimo/incremento e recusas com motivo. |
| Anti-sniping | Extensão cumulativa de 2 minutos sobre o término vigente. |
| Liquidação | Débito/crédito e comprovante idempotentes; fechamento sem vencedor quando não há lances. |
| Auditoria e privacidade | Histórico público completo, SHA-256 encadeado, âncora HMAC e pseudônimos por lote. |
| Comprovante e Meus arremates | Link público compartilhável; participações e vitórias na área do licitante. |
| Deploy e dados demo | Aplicação publicada; um leiloeiro, dois licitantes e lote aberto semeados no boot. |

| Opcional | Implementação entregue |
| --- | --- |
| Busca e filtro de lotes | Filtro local combinável por termo/estado, sem nova consulta à AIC. |
| Cancelamento com estorno automático | Liberação transacional da reserva do líder, preservando total e auditoria. |
| Docker Compose | PostgreSQL 18 com bancos isolados de desenvolvimento e teste. |
| Testes automatizados | Regras, integração com PostgreSQL real, concorrência e navegador. |
| Dark mode | Tema por tokens, preferência inicial do sistema e escolha manual persistida. |

Acrescentei **refinamentos além dos requisitos**: cadastro público dos dois
papéis, senha forte no frontend/backend, confirmação de senha só na interface,
ajuda contextual acessível, contexto de saldo do líder e footer institucional.
Novas senhas exigem 8–1024 caracteres e pelo menos três grupos entre minúsculas,
maiúsculas, números e símbolos. O cadastro cria carteira zero e leva ao login.

## Decisões técnicas que fazem diferença

- **Concorrência financeira:** dinheiro em centavos inteiros (`BIGINT`), sem
  float. Cada lance trava o lote antes das carteiras, ordenadas por `user_id`,
  e lê `clock_timestamp()` do PostgreSQL após a trava. Histórico, reserva,
  líder e prazo mudam em uma transação; os testes disputam sessões reais.
- **Anti-sniping cumulativo:** `0 < restante <= 2 min` leva a
  `ends_at vigente + 2 min`, inclusive exatamente 2 minutos, sem teto de
  prorrogações. O relógio do navegador não decide se o lance é aceito.
- **Integridade verificável:** cada lance incorpora o hash anterior; HMAC
  autentica a contagem e o hash final do lote com segredo fora do banco.
  A auditoria pública recalcula o histórico; pseudônimos variam entre lotes.
- **Independência da AIC:** um snapshot essencial da obra sustenta Vitrine,
  Sala, auditoria e comprovante sem nova consulta ao museu. Imagens continuam
  externas, por proxy de destino fixo, com placeholder local se falharem.
- **Comandos e atualizações separados:** lance por REST, atualização por
  WebSocket e snapshot no reconnect. O cliente não reenvia lances automaticamente.
- **Liquidação recuperável:** mesma trava do lote, revalidação do término,
  operação idempotente e comprovante único por lote. Scheduler e catch-up no
  startup apuram vencidos; GET nunca liquida.
- **Verificação em camadas:** regras puras, transações/rollback/concorrência em
  PostgreSQL real, Playwright para interação e smoke publicado. Os limites de
  cada prova estão explícitos na seção de testes.

## Stack e arquitetura

| Camada | Tecnologias e organização |
| --- | --- |
| Backend | Python 3.13, FastAPI, SQLAlchemy síncrono, PostgreSQL, Alembic e psycopg 3 em `backend/`. |
| Frontend | React, TypeScript, Vite e tokens CSS próprios em `frontend/`. |
| Infraestrutura | Docker multi-stage, Compose para banco local e Render; SPA/API/WS na mesma origem. |

Escolhi um monólito com um processo de aplicação: era suficiente para o desafio,
concentra transações no PostgreSQL e simplifica cookie, publicação e comunicação.
As salas WS e o scheduler usam memória local; múltiplos workers exigiriam outra
coordenação. Descartei microservices nessa escala. Decisões e alternativas em
[docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## Instalação e execução local

Pré-requisitos: **Python 3.13+, uv, Node.js 24/npm, Docker e Compose v2**.
A imagem fixa Python 3.13 e uv 0.13.5; dependências estão nos lockfiles.
Todos os comandos partem da **raiz do repositório**; os parênteses preservam o
diretório do terminal. Não há chave da AIC a configurar.

```bash
( cd backend && uv sync --frozen )
( cd frontend && npm ci )
docker compose up -d --wait postgres
```

O Compose expõe o banco em `127.0.0.1:5432` e cria `casa_de_leiloes_dev` e
`casa_de_leiloes_test` em volume persistente. As credenciais abaixo são
**fictícias e públicas, exclusivas do Compose local**. Substitua os três
placeholders de segredo por valores aleatórios criptográficos distintos de ao
menos 32 caracteres ASCII; preserve esses valores entre inicializações e
repita os mesmos exports nos demais terminais.

```bash
export DATABASE_URL='postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_dev'
export TEST_DATABASE_URL='postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_test'
export APP_ORIGIN='http://localhost:5173'
export JWT_SECRET='<seu-segredo-jwt-aleatorio>'
export AUDIT_HMAC_SECRET='<seu-segredo-de-auditoria-aleatorio>'
export PSEUDONYM_SECRET='<seu-segredo-de-pseudonimos-aleatorio>'

( cd backend && uv run alembic upgrade head )
( cd backend && uv run python -m app.seed )
```

`APP_ORIGIN` é a origem exata, sem caminho; HTTPS fora do ambiente local. O seed
é idempotente e usa fixture offline: cria contas/carteiras ausentes e demo futuro
quando necessário, sem zerar saldos, trocar senhas ou apagar histórico.
O pytest recria o schema de **teste**; nunca use produção nem o banco de dev em
`TEST_DATABASE_URL`. Não rode pytest junto de um smoke no mesmo banco.

Em dois terminais, com o ambiente exportado:

```bash
# Terminal 1
( cd backend && uv run uvicorn app.main:app --port 8000 )
```

```bash
# Terminal 2
( cd frontend && npm run dev )
```

Abra <http://localhost:5173>. Vite usa porta fixa 5173 e proxy de `/api`,
`/health` e `/ws` para o backend. Swagger em <http://localhost:5173/api/docs>;
OpenAPI em `/api/openapi.json`. `/health` retorna `200 {"status":"ok"}` e não
consulta o banco.

### Build single-origin e imagem

Pare o backend anterior e sirva o build pelo FastAPI:

```bash
( cd frontend && npm run build )
( cd backend && APP_ORIGIN=http://localhost:8000 SPA_DIST_DIR=../frontend/dist \
  uv run uvicorn app.main:app --port 8000 )
```

Abra <http://localhost:8000>. `SPA_DIST_DIR` relativo é resolvido a partir de
`backend/`; sem essa variável, só a API é servida.

```bash
docker build -t casa-de-leiloes .
export DOCKER_DATABASE_URL='postgresql://casa:casa_local_dev@postgres:5432/casa_de_leiloes_dev'
docker run --rm --network casa-de-leiloes_default -p 127.0.0.1:9000:9000 \
  -e PORT=9000 -e APP_ORIGIN=http://localhost:9000 \
  -e JWT_SECRET -e AUDIT_HMAC_SECRET -e PSEUDONYM_SECRET \
  -e DATABASE_URL="$DOCKER_DATABASE_URL" casa-de-leiloes
```

A rede acima pressupõe o nome padrão do projeto Compose. A imagem roda sem root
e inicia migrations → seed → catch-up → scheduler → tráfego. No Render, um Web
Service Docker usa `DATABASE_URL` do PostgreSQL, `APP_ORIGIN` HTTPS e os três
segredos definidos no provedor; `PORT` vem da plataforma e `SPA_DIST_DIR` da
imagem. Preserve os segredos de integridade: não há rotação suportada.

## Testes e alcance da verificação

| Camada | Comando na raiz | O que verifica |
| --- | --- | --- |
| Gate rápido, sem banco/navegador | `( cd backend && uv run ruff check . && uv run ruff format --check . )` e `( cd frontend && npm run lint && npm run typecheck && npm test )` | Análise estática e regras puras do frontend. |
| Gate completo padrão | `./verify.sh` | Ruff, PostgreSQL/pytest, lint, tipos, Node, Vite e build Docker; para na primeira falha. |
| E2E simulado | `( cd frontend && npm run test:e2e )` | Interação, foco, navegação, reconexão simulada e layout no Chromium. |
| Gate completo com E2E | `VERIFY_E2E=1 ./verify.sh` | Gate padrão mais Playwright. |
| Real-stack opt-in | Comandos abaixo | FastAPI + build React + PostgreSQL reais, incluindo cadastro/sessão e contratos públicos. |

Instale o navegador uma vez: `( cd frontend && npx playwright install chromium )`.
O Playwright padrão intercepta a API e usa `vite preview` em 4173: **não substitui
integração com PostgreSQL nem comprova a stack publicada**. Os sete cenários
real-stack ficam skipped sem `E2E_REAL_BASE_URL`.

Para o opt-in, com PostgreSQL ativo e ambiente local acima, prepare o banco de
teste e mantenha o servidor em um terminal dedicado:

```bash
( cd backend && DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head )
( cd backend && DATABASE_URL="$TEST_DATABASE_URL" uv run python -m app.seed )
( cd frontend && npm run build )
( cd backend && DATABASE_URL="$TEST_DATABASE_URL" APP_ORIGIN=http://localhost:8765 \
  SPA_DIST_DIR=../frontend/dist uv run uvicorn app.main:app --port 8765 )
```

Em outro terminal:

```bash
( cd frontend && E2E_REAL_BASE_URL=http://localhost:8765 npm run test:e2e -- real-stack )
```

**Evidência final registrada:** 2.446 testes backend, 206 Node e 355 Playwright
aprovados no gate com E2E; sete real-stack aprovados separadamente, sem contá-los
como execução do gate padrão. O [re-review final dos opcionais](_bmad-output/implementation-artifacts/code-review-r6-opt-01-rereview.md)
confere o gate após a última correção; o [fechamento](docs/FECHAMENTO-EPICO-6.md)
registra o opt-in e o [smoke público final](_bmad-output/implementation-artifacts/smoke-publico-final-6-5-6-7.md)
comprova os fluxos publicados no recorte descrito. São resultados anteriores a
esta revisão documental, sem nova execução funcional.

## Segurança e integridade

Senhas usam Argon2id. JWT de 8 h fica em cookie HttpOnly, SameSite=Lax e Path=/;
em HTTPS, `__Host-auction_session` tem Secure e não define Domain. O token não
vai para localStorage ou URL. Backend aplica papéis; escritas exigem JSON e
Origin compatível com `APP_ORIGIN` (Referer somente se Origin faltar), sem CORS
permissivo. Erros internos são genéricos, sem SQL, stack ou segredos ao cliente.

Auditoria e comprovante expõem pseudônimos por lote, valores, horários e hashes,
sem e-mail, ID real do licitante ou HMAC. A cadeia detecta alterações, inserções,
remoções e truncamentos sem capacidade de reassinar. **Não promete imutabilidade
absoluta:** segredo comprometido permite reassinatura; rollback coordenado para
cadeia/âncora antigas válidas exige âncora externa para detecção. A âncora v1
cobre contagem/hash final, não todos os termos do lote ou saldos. Detalhes na
[arquitetura](docs/ARQUITETURA.md).

## Limitações e comportamentos esperados

- **Hospedagem:** Render gratuito pode ter cold start. `/health` verde não prova
  banco, autenticação ou WS. Queda do serviço adia a liquidação até a retomada;
  scheduler/catch-up não prometem prazo fixo de apuração.
- **Tempo real e escala:** um processo, sem outbox/replay. Falha entre commit e
  publicação pode perder o evento; reconnect/snapshot recupera o estado. Há
  leituras O(n) do histórico e listagens sem paginação no servidor.
- **Resultado incerto:** timeout após commit não prova falha. Sem
  `Idempotency-Key`, repetir manualmente depósito/criação pode duplicar o efeito;
  confira o estado antes de tentar de novo. Não há reenvio automático de lance.
- **Autenticação:** logout apaga o cookie, mas não revoga JWT copiado antes de
  expirar. Sem rate limit, recuperação de senha ou confirmação de e-mail;
  cadastro público permite os dois papéis e informa duplicidade de e-mail.
- **AIC:** busca/criação e bytes das imagens dependem do museu; os dados dos lotes
  existentes permanecem disponíveis. No smoke final, o destino oficial do link
  da coleção apresentou Cloudflare/403: ressalva LOW externa, sem defeito do
  ÁTRIO confirmado; busca e criação pela API continuaram funcionais.
- **Integridade:** sem rotação de segredos ou proteção contra controle total de
  aplicação/banco/segredos. Trocar segredos de integridade afeta lotes existentes.
- **Demonstração e navegador:** sem dinheiro real, gateway ou ledger de movimentos.
  Contas demo são compartilhadas; o seed não zera seu uso. Validação de navegador
  concentrou-se em Chromium, com verificações desktop/mobile até 320 px.

## Documentação

- [Arquitetura e decisões](docs/ARQUITETURA.md).
- [Onde e como usei IA](docs/uso_de_ia.md).
- [Fechamento e trilha de validação final](docs/FECHAMENTO-EPICO-6.md).
- [Planejamento, specs, stories e reviews](_bmad-output/).
