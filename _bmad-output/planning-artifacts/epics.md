---
status: approved
approval: aprovado pelo Joaodionizio em 23/10/2026 (revisão 2, com D1=A, D2=A, D3 reorganizada e D4=A)
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories"]
inputDocuments:
  - docs/desafio-elite-dev.md
  - docs/ARQUITETURA.md
  - docs/CRONOGRAMA.md
  - CLAUDE.md
  - código atual (backend/, frontend/, verify.sh)
---

# casa-de-leiloes - Divisão em épicos

## Visão geral

Este documento divide o projeto casa-de-leiloes em épicos e stories. Não fiz PRD
porque o enunciado (`docs/desafio-elite-dev.md`) já é a especificação. As
decisões técnicas vêm de `docs/ARQUITETURA.md` (AD-1 a AD-30, vinculantes) e a
ordem temporal vem de `docs/CRONOGRAMA.md`. Não há documento de UX: a pasta
`ux-designs/` está vazia; a direção visual vem do AD-15.

Regras desta divisão:
- cada story é um commit coerente, com planejamento, implementação, `verify`,
  review técnico e commit próprios; tarefas fortemente acopladas que formam uma
  única entrega verificável ficam na mesma story;
- uma story só depende de stories anteriores;
- tabelas nascem na story que precisa delas;
- os critérios dizem o que precisa funcionar, não como implementar além das ADs;
- a arquitetura é vinculante: a divisão se ajusta às ADs, nunca o contrário.
  Por isso, todo lance nasce íntegro (AD-7 passo 15, AD-13, AD-20, AD-21) já no
  Épico 3;
- quando uma story depende de uma questão aberta (Q1 a Q10 de
  `docs/ARQUITETURA.md`) ou de um detalhe ainda não decidido, isso está indicado
  e é decidido por mim na criação da story, não aqui.

**Critério de saída de todo épico (do princípio do cronograma):** o `verify`
passa e o deploy está atualizado, com o fluxo do épico funcionando na URL
pública.

### Decisões já tomadas sobre a divisão

- **D1 = A:** o primeiro deploy (Story 1.4) valida também WebSocket e cookie,
  como validação mínima de infraestrutura (mitigação do AD-14), sem antecipar
  autenticação nem a sala de leilão.
- **D2 = A:** sem cadastro público no escopo obrigatório. Só as contas semeadas
  exigidas pelo desafio: 1 `AUCTIONEER` e 2 `BIDDER`. Não há story de cadastro.
- **D3:** descartei criar lances sem integridade e resetar o banco de produção
  depois. O motor de lances do Épico 3 já grava pseudônimo, representação
  canônica v1, `previous_hash`/hash atual, cadeia SHA-256 e âncora HMAC na mesma
  transação do lance. O Épico 5 fica com a verificação pública, a página de
  auditoria, os testes de adulteração e os fluxos finais. O comprovante base
  nasce na liquidação (Épico 4) com os dados de integridade já existentes.

## Inventário de requisitos

### Requisitos funcionais

FR1: Existem dois papéis distintos: leiloeiro (`AUCTIONEER`) e licitante (`BIDDER`), com login e logout. Sem cadastro público (D2): só contas semeadas.
FR2: O leiloeiro busca itens na API externa (Art Institute of Chicago), só obras de domínio público.
FR3: O leiloeiro cria um lote a partir de um item buscado, com imagem, título, atributos do item, início, fim, lance inicial e incremento mínimo.
FR4: O leiloeiro cancela um lote que ainda não recebeu lances.
FR5: O leiloeiro vê o resultado de cada lote encerrado (se foi arrematado e por quanto) e o total recebido.
FR6: A vitrine exibe os lotes separados em ao vivo, agendados e encerrados; lotes cancelados não aparecem.
FR7: O licitante vê na carteira o saldo total, o saldo comprometido e o saldo disponível.
FR8: O licitante faz depósito simulado na carteira.
FR9: A sala do lote exibe lance atual, histórico de lances, posição do usuário, contagem regressiva e indicador "você está ganhando" / "você foi superado", tudo atualizado sem recarregar.
FR10: Lance só em lote ao vivo; o primeiro deve ser >= lance inicial; os seguintes >= lance atual + incremento mínimo; o líder não cobre o próprio lance.
FR11: Todo lance recusado devolve o motivo exato: abaixo do mínimo, saldo insuficiente, você já está ganhando, lote ainda não iniciado, lote encerrado.
FR12: Saldo disponível = total - comprometido. O valor do líder fica comprometido; ao ser superado, volta ao disponível imediatamente. O lance só entra se couber no disponível.
FR13: Anti-sniping: lance aceito nos últimos 2 minutos estende o fim do lote (AD-5).
FR14: Ao encerrar, debita o vencedor, credita o leiloeiro e gera comprovante; lote sem lances fecha sem vencedor.
FR15: O vencedor recebe comprovante de arremate compartilhável por link.
FR16: Meus arremates: o licitante vê os itens em que deu lance e os lotes vencidos, com comprovante e link de compartilhamento.
FR17: Página de auditoria pública, sem login, mostra o histórico completo de um lote e informa se está íntegro ou adulterado; detecta alteração, remoção e inserção, mesmo direto no banco.
FR18: Auditoria e comprovante identificam licitantes sem expor dados pessoais.
FR19: Dados semeados: um leiloeiro, dois licitantes e ao menos um lote publicado com lances abertos.

Opcionais do enunciado (considerados na avaliação, cortáveis):
OPT1: Busca e filtro de lotes.
OPT2: Cancelamento de lote com estorno automático.
OPT3: Docker Compose.
OPT4: Testes automatizados.
OPT5: Dark mode.

### Requisitos não funcionais

NFR1: Deploy público obrigatório.
NFR2: Vitrine, sala, auditoria e comprovante continuam funcionando se a API externa cair (só a imagem pode falhar).
NFR3: README detalhado: configurar e executar a aplicação, configurar o banco e citar comportamentos que podem surpreender.
NFR4: Prazo: entrega até 29/10/2026.
NFR5: Stack: React no front-end, Python no back-end, PostgreSQL.
NFR6: Uso de IA descrito (onde, como, o que foi revisado).

### Requisitos adicionais (arquitetura)

- AR1 (AD-1, AD-2): FastAPI; PostgreSQL com SQLAlchemy 2.x síncrono, Alembic e psycopg 3; nenhuma operação bloqueante de banco no event loop.
- AR2 (AD-3): dinheiro em centavos, `BIGINT`, sufixo `_cents`; CHECKs de não negativo e `committed_balance_cents <= total_balance_cents`; sem float.
- AR3 (AD-4): React + Vite + TypeScript simples; contratos HTTP e eventos WebSocket tipados.
- AR4 (AD-6, AD-26): hora do PostgreSQL (`clock_timestamp()`) lida depois da trava do lote, um instante por operação; o domínio recebe `now`.
- AR5 (AD-7, AD-8): lance em uma única transação de 16 passos, incluindo o registro de auditoria; travas: lote, depois carteiras em `user_id` crescente.
- AR6 (AD-9, AD-19): fechamento sob a mesma trava, idempotente, `UNIQUE(lot_id)` em `receipts`; scheduler + catch-up na inicialização e na tentativa de lance; leituras nunca liquidam; evento só depois do commit.
- AR7 (AD-10, AD-25): WebSocket só para a sala; lances por REST; heartbeat do cliente; snapshot completo ao (re)conectar; um processo; Session curta em threadpool.
- AR8 (AD-11, AD-29): JWT de 8 h em cookie HttpOnly, mesma origem; Argon2; CSRF por JSON + `Origin`/`Referer`; sem CORS permissivo; toda rota declara política de acesso.
- AR9 (AD-12, AD-22, AD-23): Art Institute of Chicago; só domínio público; snapshot mínimo copiado no lote; imagem direto do IIIF com placeholder local.
- AR10 (AD-13, AD-20, AD-21): pseudônimo por lote via HMAC; representação canônica v1; cadeia SHA-256; âncora HMAC com `AUDIT_HMAC_SECRET`.
- AR11 (AD-14, AD-28): monorepo, `uv`, Dockerfile multi-stage, FastAPI serve a SPA; Render gratuito (um Web Service + PostgreSQL); `GET /health`; primeiro deploy no épico 1 validando FastAPI, PostgreSQL, React, WebSocket, cookies e migrations.
- AR12 (AD-17, AD-27): testes críticos em PostgreSQL real, banco de teste isolado do de desenvolvimento; `verify` fail-fast.
- AR13 (AD-24): seed idempotente na inicialização, IDs fixos, lotes demo marcados, fixtures sem API externa.
- AR14 (AD-30): inglês em código, banco e API; interface e mensagens em português.
- AR15: erro em formato único; 500 genérico, sem stack.

### Requisitos de UX

Não há documento de UX. Requisitos visuais vêm do AD-15:
- UX1: identidade de catálogo de museu, com tokens CSS próprios.
- UX2: estados ("ganhando", "superado", "encerrado") nunca indicados só por cor.
- UX3: valores e cronômetro muito legíveis; layout responsivo.
- UX4: dark mode só depois dos fluxos obrigatórios (opcional).

### Mapa de cobertura

FR1: Épico 2 (2.2)
FR2: Épico 2 (2.3)
FR3: Épico 2 (2.4)
FR4: Épico 3 (3.6)
FR5: Épico 4 (4.5)
FR6: Épico 2 (2.5)
FR7: Épico 3 (3.1)
FR8: Épico 3 (3.1)
FR9: Épicos 3 e 4 (3.5, 4.1, 4.2)
FR10: Épico 3 (3.2, 3.4)
FR11: Épico 3 (3.2, 3.5)
FR12: Épico 3 (3.4)
FR13: Épico 3 (3.2, 3.4)
FR14: Épico 4 (4.3, 4.4)
FR15: Épico 4 (4.3, comprovante base) e Épico 5 (5.2, link público)
FR16: Épico 5 (5.3)
FR17: Épico 3 (3.3, 3.4, integridade gravada) e Épico 5 (5.1, verificação pública)
FR18: Épicos 3 e 5 (3.3, 3.5, 5.1, 5.2)
FR19: Épico 2 (2.2 usuários, 2.4 lote demo)
OPT1: Épico 6 (6.5)
OPT2: Épico 6 (6.6)
OPT3: Épico 1 (1.2; Q10 resolvida na story: `compose.yaml` na raiz com os bancos de dev e de teste)
OPT4: todas as stories (teste no mesmo commit)
OPT5: Épico 6 (6.7)
NFR1: Épico 1 (1.4) e critério de saída de todo épico
NFR2: Épicos 2 e 6 (2.3, 2.5, 6.1)
NFR3: Épicos 1 e 6 (1.4, 6.3)
NFR6: todas as stories; consolidado em 6.3

## Lista de épicos

| Épico | Dia (cronograma) | Resultado para o usuário | Stories |
| --- | --- | --- | --- |
| 1. Fundação e aplicação publicada | 22/10 e 23/10 | A aplicação existe numa URL pública, com banco, migrations, WebSocket e cookie validados | 1.1 a 1.4 |
| 2. Contas, lotes do museu e vitrine | 24/10 | Usuários semeados entram com seu papel; o leiloeiro cria lotes de obras reais; qualquer pessoa vê a vitrine | 2.1 a 2.5 |
| 3. Carteira e lances íntegros | 25/10 | O licitante deposita e dá lances com todas as regras e travas; cada lance já nasce encadeado e ancorado | 3.1 a 3.6 |
| 4. Sala ao vivo e encerramento | 26/10 | A sala atualiza sozinha; lotes fecham, liquidam e geram o comprovante base | 4.1 a 4.5 |
| 5. Auditoria pública, comprovante e meus arremates | 27/10 | Qualquer pessoa verifica o histórico; o vencedor compartilha o comprovante | 5.1 a 5.3 |
| 6. Entrega: robustez, documentação e opcionais | 28/10 e 29/10 | A entrega está documentada, revisada e validada no deploy | 6.1 a 6.7 |

Cada épico usa só o que os anteriores entregaram. A ordem segue o fluxo
vertical do AD-16 (criar lote → vitrine → sala → saldo → lance → tempo real →
encerramento → liquidação → comprovante → auditoria).

**Alinhamento com o cronograma (D4 = A):** pseudônimo, representação canônica
v1, cadeia SHA-256 e âncora HMAC entram no Épico 3 (Dia 4), por causa do AD-7 e
do AD-13; `docs/CRONOGRAMA.md` foi atualizado para refletir isso.

---

## Épico 1: Fundação e aplicação publicada

Ao fim do épico, a aplicação (FastAPI + SPA React) roda na mesma origem, com
PostgreSQL, migrations e `GET /health`, publicada no Render gratuito com
PostgreSQL, e o deploy confirma que WebSocket e cookie funcionam na
infraestrutura. Sem autenticação e sem domínio.

### Story 1.1: Fundação mínima do monorepo

**Situação:** concluída (registro retroativo).

Como desenvolvedor,
Quero a estrutura inicial do monorepo com back-end e front-end verificáveis,
Para que toda story seguinte comece de uma base que já passa no `verify`.

**ADs:** AD-1, AD-4, AD-27, AD-28.

**Critérios de aceite (entregues nos commits `5ecc0ba` e `28c2bfa`):**

**Dado** o repositório
**Quando** abro `backend/` e `frontend/`
**Então** existem um back-end FastAPI gerenciado com `uv` e um front-end React + Vite + TypeScript mínimo.

**Dado** o back-end rodando
**Quando** chamo `GET /health`
**Então** recebo 200 com `{"status": "ok"}`, coberto por teste `pytest`.

**Dado** o repositório
**Quando** rodo `verify.sh`
**Então** ele executa Ruff, `ruff format --check`, `pytest`, ESLint, typecheck e build do Vite, falhando na primeira etapa que falhar.

**Fora desta story (ainda não entregue):** PostgreSQL, migrations, Docker,
servir a SPA pelo FastAPI, deploy, autenticação, domínio.

### Story 1.2: PostgreSQL com bancos isolados e migrations

Como desenvolvedor,
Quero um PostgreSQL local com bancos de desenvolvimento e de teste separados, conexão configurada pelo ambiente e esquema controlado por migrations,
Para que toda story seguinte grave dados de forma rastreável e teste em PostgreSQL real sem tocar nos dados de desenvolvimento.

**ADs:** AD-2, AD-17, AD-27, AD-28. **Q10 e detalhes resolvidos na criação da story (23/10/2026):** D1 a D8 e Python 3.13, incluindo local do Compose, versão do PostgreSQL e se `GET /health` verifica o banco; ver `_bmad-output/implementation-artifacts/1-2-postgresql-com-bancos-isolados-e-migrations.md`.

**Critérios de aceite:**

**Dado** o repositório clonado e o Docker disponível
**Quando** sigo o passo documentado para subir o PostgreSQL local
**Então** existem um banco de desenvolvimento e um banco de teste distintos
**E** nenhum teste escreve no banco de desenvolvimento.

**Dado** o back-end
**Quando** ele inicia ou os testes rodam
**Então** a URL do banco vem de variável de ambiente
**E** nenhum segredo ou credencial real está versionado; existe um exemplo de configuração só com valores fictícios.

**Dado** um banco vazio
**Quando** executo o comando documentado de migração (Alembic)
**Então** o esquema chega à última revisão sem erro
**E** a migration inicial não cria tabelas de domínio (elas nascem nas stories que precisam delas).

**Dado** a suíte de testes de integração
**Quando** ela prepara o banco de teste
**Então** o esquema vem das migrations, não de criação direta pelos modelos
**E** pelo menos um teste executa uma consulta real no PostgreSQL via SQLAlchemy síncrono + psycopg 3
**E** nenhum teste usa SQLite.

**Dado** `verify.sh`
**Quando** o executo
**Então** ele inclui os testes de integração em PostgreSQL real, com as migrations aplicadas num banco de teste limpo
**E** falha (não pula em silêncio) se o banco de teste não estiver disponível.

**Dado** a aplicação
**Quando** chamo `GET /health`
**Então** continua respondendo 200.

### Story 1.3: SPA na mesma origem e imagem multi-stage

Como desenvolvedor,
Quero uma única imagem que sirva a API e a SPA na mesma origem, com as migrations aplicadas antes do tráfego,
Para que o mesmo artefato rode localmente e no Render, como base dos cookies do AD-11.

**ADs:** AD-4, AD-11, AD-14, AD-28, AD-29, AD-30.

**Critérios de aceite:**

**Dado** o build de produção do front-end
**Quando** acesso `/`
**Então** o FastAPI devolve a SPA, com uma página mínima em português que mostra o estado do `GET /health`.

**Dado** uma rota do cliente (por exemplo, `/lots/qualquer-coisa`)
**Quando** a acesso diretamente
**Então** recebo a SPA, não um 404.

**Dado** um caminho inexistente sob `/api/`
**Quando** o chamo
**Então** recebo um 404 da API, nunca o HTML da SPA
**E** `/health` não é capturado pelo fallback.

**Dado** o ambiente de desenvolvimento
**Quando** o front-end chama a API
**Então** funciona sem habilitar CORS permissivo.

**Dado** a raiz do repositório
**Quando** construo a imagem com o `Dockerfile`
**Então** um estágio gera o build do Vite e outro prepara o Python com `uv` e copia o `dist`.

**Dado** o contêiner iniciado com a URL de um PostgreSQL
**Quando** ele sobe
**Então** as migrations são aplicadas antes de a aplicação atender tráfego, por um mecanismo documentado
**E** `GET /health` e a SPA respondem
**E** ele escuta na porta fornecida pelo ambiente.

**Dado** a imagem
**Quando** a reviso
**Então** nenhum segredo está embutido
**E** nenhum estado persistente é gravado no filesystem do contêiner.

**Dado** `verify.sh`
**Quando** o executo
**Então** há testes para a entrega da SPA, o fallback de rotas do cliente e o 404 sob `/api/`.

### Story 1.4: Primeiro deploy no Render

Como avaliador,
Quero abrir a aplicação numa URL pública que já comprove banco, migrations, WebSocket e cookie na infraestrutura real,
Para que o deploy obrigatório exista desde o primeiro dia e os riscos do Render gratuito apareçam cedo.

**ADs:** AD-10, AD-11, AD-14, AD-28, AD-29. **Decisão D1 = A.** **A decidir na criação da story:** rotas e nomes das verificações de WebSocket e cookie, e o destino delas depois (removidas ou mantidas) quando as stories reais de autenticação e da sala chegarem; nome do segredo do JWT não se aplica aqui (não há JWT nesta story).

**Critérios de aceite:**

**Dado** um Web Service gratuito e um PostgreSQL gratuito no Render
**Quando** o deploy termina
**Então** a URL pública em HTTPS serve a SPA
**E** `GET /health` responde 200
**E** as migrations estão aplicadas no banco de produção.

**Dado** o serviço publicado
**Quando** abro uma conexão WebSocket de verificação e troco mensagens
**Então** a conexão funciona através do proxy do Render
**E** essa verificação não lê nem grava dados de domínio, não tem autenticação e não antecipa a sala de leilão.

**Dado** o serviço publicado
**Quando** recebo um cookie de verificação
**Então** ele chega com `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain` e, se possível, com prefixo `__Host-`
**E** essa verificação não emite JWT nem identifica usuário
**E** obter o cookie não altera estado no servidor.

**Dado** a configuração de produção
**Quando** a reviso
**Então** segredos e a URL do banco existem só nas variáveis de ambiente do Render, nunca no repositório.

**Dado** o serviço parado por inatividade
**Quando** o acesso de novo
**Então** registro o cold start observado (número só de medição real).

**Dado** o README
**Quando** um avaliador o lê
**Então** encontra como subir o banco local, aplicar migrations, rodar o `verify`, rodar a aplicação e como o deploy é feito
**E** `docs/uso_de_ia.md` registra o que a IA fez nesta story e o que eu revisei.

---

## Épico 2: Contas, lotes do museu e vitrine

Ao fim do épico, os usuários semeados entram com o seu papel, o leiloeiro busca
obras de domínio público e cria lotes, existe um lote demo aberto e qualquer
pessoa vê a vitrine separada em ao vivo, agendados e encerrados, sem depender
da API externa para os dados.

### Story 2.1: Formato de erro e validação de origem

Como usuário da aplicação,
Quero que toda falha da API chegue num formato previsível, sem detalhes internos, e que requisições de outra origem não alterem estado,
Para que a interface mostre mensagens claras, nenhum stack trace vaze e a base contra CSRF exista antes das rotas que alteram estado.

**ADs:** AD-19, AD-29, AD-30.

**Critérios de aceite:**

**Dado** qualquer erro previsto (validação, não encontrado, não autorizado, proibido)
**Quando** a API responde
**Então** o corpo segue um formato único, com código em inglês, e o front-end consegue exibir uma mensagem em português.

**Dado** um erro inesperado no servidor
**Quando** a API responde
**Então** recebo 500 com mensagem genérica, sem stack trace nem detalhe interno
**E** o erro fica registrado no log do servidor.

**Dado** uma requisição que altera estado
**Quando** chega com `Origin` diferente da origem configurada (ou sem `Origin` e com `Referer` diferente), ou sem corpo JSON
**Então** é rejeitada no formato único
**E** GET, HEAD e OPTIONS não são afetados e continuam sem efeito colateral.

**Dado** `verify.sh`
**Quando** o executo
**Então** há testes para erro previsto, 422 de validação, 500 genérico e rejeição por origem e por conteúdo.

### Story 2.2: Login, papéis e política de acesso

Como leiloeiro ou licitante semeado,
Quero entrar e sair com a minha conta e ter acesso só ao que o meu papel permite,
Para que o leiloeiro nunca dê lances, o licitante nunca crie lotes e nenhuma rota fique aberta por esquecimento.

**ADs:** AD-11, AD-24, AD-29, AD-30. **Decisão D2 = A** (sem cadastro público). **Depende de:** Q10 (nome da variável do segredo do JWT).

**Critérios de aceite:**

**Dado** a aplicação iniciando
**Quando** o seed roda
**Então** existem exatamente as contas exigidas: um `AUCTIONEER` e dois `BIDDER`, com IDs fixos
**E** rodar o seed de novo não duplica nem altera esses usuários
**E** as senhas ficam armazenadas com Argon2
**E** não existe rota de cadastro.

**Dado** credenciais válidas
**Quando** faço login
**Então** recebo um JWT de 8 h em cookie `HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain` (`Secure` e prefixo `__Host-` em produção, quando possível)
**E** o token não contém dados pessoais desnecessários.

**Dado** credenciais inválidas
**Quando** tento login
**Então** recebo erro no formato único, sem revelar se o e-mail existe.

**Dado** estar logado
**Quando** consulto o endpoint do usuário atual
**Então** recebo meu papel (`AUCTIONEER` ou `BIDDER`); na interface aparece "Leiloeiro" ou "Licitante".

**Dado** estar logado
**Quando** faço logout
**Então** o cookie é apagado.

**Dado** todas as rotas registradas na aplicação
**Quando** o teste de política roda
**Então** ele reprova qualquer rota sem política de acesso declarada (pública, autenticada ou por papel).

**Dado** uma rota autenticada ou restrita a um papel
**Quando** um visitante sem login ou um usuário do outro papel a chama
**Então** recebe 401 ou 403, respectivamente, no formato único.

**Dado** a interface
**Quando** acesso a tela de login
**Então** consigo entrar e sair, com mensagens em português.

**Dado** `verify.sh`
**Quando** o executo
**Então** os testes de login e de papel rodam em PostgreSQL real.

### Story 2.3: Busca de obras no Art Institute of Chicago

Como leiloeiro,
Quero buscar obras no catálogo do Art Institute of Chicago,
Para que eu escolha a obra que vai virar lote.

**ADs:** AD-12, AD-22, AD-23. **Depende de:** Q7 (como simular "API indisponível" no smoke test).

**Critérios de aceite:**

**Dado** estar logado como leiloeiro
**Quando** busco por um termo no painel
**Então** vejo apenas obras com `is_public_domain=true`, com título, artista e imagem IIIF (ou placeholder local se a imagem falhar).

**Dado** uma obra da lista
**Quando** abro o detalhe
**Então** vejo os campos do snapshot mínimo do AD-23.

**Dado** a API externa indisponível ou lenta
**Quando** busco
**Então** recebo uma mensagem clara em português e o restante da aplicação continua funcionando.

**Dado** um licitante ou visitante
**Quando** tenta usar a busca
**Então** é recusado pela política de acesso.

**Dado** os testes
**Quando** rodam no `verify`
**Então** não dependem da API real (usam fixtures ou falha simulada)
**E** existe um smoke test separado da integração real cobrindo os itens do AD-23, documentado e fora do `verify`.

### Story 2.4: Criação de lotes pelo leiloeiro e lote demo semeado

Como leiloeiro, e como avaliador que chega à aplicação,
Quero criar lotes a partir de obras buscadas e encontrar um lote demo já aberto,
Para que obras entrem em leilão pelas mesmas regras, com ou sem intervenção manual.

**ADs:** AD-3, AD-6, AD-12, AD-22, AD-23, AD-24, AD-30. **Depende de:** Q4 (ordem na inicialização e definição de "lote demo realmente aberto").

**Critérios de aceite:**

**Dado** estar logado como leiloeiro e uma obra de domínio público
**Quando** crio o lote com lance inicial, incremento mínimo, início e fim
**Então** o lote é salvo com o snapshot mínimo do AD-23 copiado para o nosso banco
**E** os valores ficam em centavos (`BIGINT`, sufixo `_cents`), com CHECK de não negativo
**E** o lote fica associado a mim e aparece na lista dos meus lotes no painel.

**Dado** uma obra sem `is_public_domain=true`
**Quando** tento criar o lote
**Então** a criação é recusada com motivo claro.

**Dado** dados inválidos (fim antes do início, valores não positivos onde não cabem, campos ausentes)
**Quando** tento criar
**Então** recebo erro de validação no formato único.

**Dado** um licitante
**Quando** tenta criar um lote
**Então** recebe 403.

**Dado** o lote criado
**Quando** a API externa fica indisponível
**Então** os dados do lote continuam disponíveis (só a imagem pode falhar).

**Dado** a aplicação iniciando sem lote demo realmente aberto
**Quando** o seed roda
**Então** cria um lote demo a partir de fixtures versionadas, sem consultar a API externa, com horários relativos ao momento atual, pelas mesmas regras de validação da criação manual
**E** o lote fica marcado como demo.

**Dado** já existir um lote demo realmente aberto
**Quando** o seed roda de novo
**Então** nenhum lote novo é criado
**E** o histórico de lotes demo antigos nunca é alterado nem apagado.

**Dado** os testes
**Quando** rodam em PostgreSQL real
**Então** cobrem a criação, as recusas e a idempotência do seed de lotes.

### Story 2.5: Vitrine pública e página do lote

Como visitante,
Quero ver os lotes separados em ao vivo, agendados e encerrados e abrir cada um,
Para que eu encontre o que está em disputa agora.

**ADs:** AD-6, AD-15, AD-19, AD-22, AD-29. **Depende de:** Q8 (nome e cálculo do estado "Encerrado, apurando resultado").

**Critérios de aceite:**

**Dado** lotes em vários estados
**Quando** abro a vitrine sem login
**Então** vejo três seções: ao vivo, agendados e encerrados
**E** lotes cancelados não aparecem.

**Dado** um lote com `ends_at` vencido e ainda não liquidado
**Quando** a vitrine ou a página do lote o lê
**Então** ele aparece como "Encerrado, apurando resultado"
**E** a leitura não altera estado nem trava o lote.

**Dado** a classificação dos lotes
**Quando** ela é calculada
**Então** usa a hora do banco, não a do navegador.

**Dado** a página de um lote
**Quando** a abro
**Então** vejo imagem (ou placeholder local), título, artista, atributos, lance inicial, incremento, início e fim, com valores em reais legíveis.

**Dado** a API externa indisponível
**Quando** abro a vitrine e a página do lote
**Então** tudo funciona, exceto possivelmente a imagem.

---

## Épico 3: Carteira e lances íntegros

Ao fim do épico, o licitante deposita saldo e dá lances com todas as regras,
travas, hora do banco e anti-sniping, recebendo aceite ou o motivo exato da
recusa. Cada lance aceito já nasce com pseudônimo, representação canônica v1,
hash encadeado e âncora HMAC atualizada, na mesma transação (AD-7 completo). A
sala ainda não atualiza sozinha (isso vem no Épico 4) e a verificação pública
da integridade vem no Épico 5.

**Segredos novos no deploy deste épico:** `PSEUDONYM_SECRET` e
`AUDIT_HMAC_SECRET`, só em variáveis de ambiente, diferentes entre si.

### Story 3.1: Carteira e depósito simulado

Como licitante,
Quero ver meus saldos e depositar um valor simulado,
Para que eu tenha saldo para dar lances.

**ADs:** AD-3, AD-8, AD-11, AD-30.

**Critérios de aceite:**

**Dado** qualquer usuário existente, inclusive os semeados
**Quando** a story é aplicada
**Então** ele tem carteira com `total_balance_cents` e `committed_balance_cents`
**E** o banco impõe por CHECK valores não negativos e `committed_balance_cents <= total_balance_cents`.

**Dado** estar logado como licitante
**Quando** abro a carteira
**Então** vejo saldo total, comprometido e disponível (disponível = total - comprometido).

**Dado** um valor positivo em centavos
**Quando** deposito
**Então** o total aumenta exatamente nesse valor.

**Dado** valor zero, negativo ou não inteiro
**Quando** tento depositar
**Então** recebo erro de validação no formato único.

**Dado** dois depósitos simultâneos na mesma carteira
**Quando** ambos terminam
**Então** o total reflete os dois (teste em PostgreSQL real).

**Dado** um leiloeiro
**Quando** tenta depositar
**Então** recebe 403.

### Story 3.2: Regras de aceitação do lance com hora injetada

Como licitante,
Quero que meu lance seja avaliado por regras claras e sempre iguais,
Para que eu saiba exatamente por que ele foi aceito ou recusado.

**ADs:** AD-5, AD-26. **Depende de:** Q5 (limite exato dos 2 minutos com `now` fixo).

**Critérios de aceite:**

**Dado** o estado do lote, o lance, o saldo disponível e um `now` recebido por parâmetro
**Quando** a regra de domínio avalia o lance
**Então** devolve aceito ou um dos motivos: abaixo do mínimo, saldo insuficiente, já está ganhando, lote não iniciado, lote encerrado.

**Dado** nenhum lance anterior
**Quando** o valor é >= lance inicial
**Então** a regra aceita; abaixo disso, recusa como abaixo do mínimo.

**Dado** um lance atual
**Quando** o novo valor é >= atual + incremento
**Então** a regra aceita; abaixo disso, recusa como abaixo do mínimo.

**Dado** um lance aceito com `0 < restante <= 2 min`
**Quando** a regra calcula o novo fim
**Então** o novo fim é o fim atual + 2 minutos; com restante maior que 2 minutos, o fim não muda.

**Dado** `now >= ends_at`
**Quando** a regra avalia
**Então** recusa como lote encerrado (nunca reabre).

**Dado** os testes unitários
**Quando** rodam
**Então** usam `now` fixo e cobrem cada motivo e os limites exatos (no início, no fim, exatamente 2 minutos).

### Story 3.3: Fundamentos de integridade do histórico

Como qualquer pessoa que vá auditar um lote,
Quero que existam funções determinísticas de pseudônimo, serialização canônica, hash encadeado e assinatura da âncora,
Para que o motor de lances grave cada lance íntegro desde o primeiro.

**ADs:** AD-13, AD-20, AD-21. **Depende de:** Q3 (`bidder_alias` persistido na linha do lance ou recalculado; define os dados de entrada do hash e o que a story 3.4 grava).

**Critérios de aceite:**

**Dado** um `lot_id` e um `user_id`
**Quando** o pseudônimo é calculado
**Então** é `HMAC(PSEUDONYM_SECRET, "{lot_id}:{user_id}")` truncado (por exemplo, `Licitante-A83F19C2`): o mesmo no mesmo lote, diferente entre lotes, sem nome, e-mail nem ID real.

**Dado** a mesma entrada de lance (`v`, `lot_id`, `sequence`, `bidder_alias`, `amount_cents`, `timestamp`, `previous_hash`)
**Quando** é serializada pela representação canônica v1
**Então** produz sempre os mesmos bytes (UTF-8, chaves ordenadas, sem espaços, UUID em minúsculas, UTC com 6 casas e `Z`) e o mesmo SHA-256 (teste com bytes e hash esperados fixos).

**Dado** o primeiro lance de um lote
**Quando** o hash é calculado
**Então** `previous_hash` é o genesis de 64 zeros.

**Dado** os dados da âncora (ID do lote, quantidade de lances, hash final)
**Quando** são serializados de forma canônica versionada e assinados com `AUDIT_HMAC_SECRET`
**Então** a mesma entrada gera sempre a mesma assinatura
**E** uma assinatura calculada sem o segredo correto não confere.

**Dado** `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET`
**Quando** reviso repositório, logs e respostas
**Então** os segredos vêm só do ambiente, são diferentes entre si e nunca aparecem.

### Story 3.4: Lance transacional com travas e anti-sniping

Como licitante,
Quero dar um lance que reserve meu saldo, devolva o do líder anterior, aplique o anti-sniping e grave a cadeia de integridade na mesma operação,
Para que o leilão nunca fique inconsistente, mesmo com lances simultâneos, e todo lance seja auditável.

**ADs:** AD-3, AD-5, AD-6, AD-7, AD-8, AD-10, AD-13, AD-17, AD-20, AD-21, AD-26, AD-30. **Depende de:** Q3 (decidida na 3.3), Q5 (margens no caminho real), Q9 (só depois, na 4.4: aqui o lance em lote vencido apenas recusa).

**Critérios de aceite:**

**Dado** estar logado como licitante
**Quando** envio `POST /api/lots/{lot_id}/bids`
**Então** recebo, na resposta, aceito ou recusado com o motivo exato.

**Dado** um lance aceito
**Quando** a transação confirma
**Então**, na mesma transação, o lance fica registrado com número de sequência, pseudônimo, `previous_hash` e hash próprio; o lote passa a ter novo líder e novo lance atual; o saldo do novo líder fica comprometido e o do líder anterior volta ao disponível; e a âncora do lote (quantidade, hash final, HMAC) é atualizada.

**Dado** um lance aceito com `0 < restante <= 2 min`
**Quando** a transação confirma
**Então** `ends_at` passa a ser o fim anterior + 2 minutos, cumulativamente e sem teto.

**Dado** a operação de lance
**Quando** ela roda
**Então** trava o lote antes das carteiras, e as carteiras em `user_id` crescente
**E** usa um único `clock_timestamp()` lido depois da trava do lote, que também é o timestamp do lance na cadeia.

**Dado** dois lances simultâneos no mesmo lote
**Quando** ambos são processados
**Então** o resultado é igual ao de alguma ordem sequencial, sem saldo negativo, sem dois líderes e sem saldo comprometido perdido
**E** a sequência fica contínua, com cada `previous_hash` apontando para o lance imediatamente anterior (teste em PostgreSQL real).

**Dado** qualquer falha no meio da operação
**Quando** ela ocorre
**Então** nada fica parcialmente aplicado (nem lance, nem saldo, nem âncora).

**Dado** um lance recusado
**Quando** a operação termina
**Então** nenhum registro de lance é criado e a cadeia e a âncora não mudam.

**Dado** um leiloeiro
**Quando** tenta dar lance
**Então** recebe 403.

**Dado** os testes de integração
**Quando** rodam em PostgreSQL real
**Então** cobrem saldo insuficiente, líder superado (saldo liberado), líder tentando cobrir o próprio lance, extensão do anti-sniping e lance depois do fim pelo caminho real com `clock_timestamp()`, e a consistência entre a cadeia gravada e a âncora.

### Story 3.5: Dar lance pela sala do lote

Como licitante,
Quero dar lance na página do lote e ver o resultado na hora,
Para que eu participe do leilão pela interface.

**ADs:** AD-4, AD-10, AD-15, AD-20, AD-30.

**Critérios de aceite:**

**Dado** estar logado como licitante num lote ao vivo
**Quando** abro a sala
**Então** vejo o lance atual, o mínimo para o próximo lance, a contagem regressiva calculada a partir dos dados do servidor e o histórico de lances com pseudônimo, valor e hora.

**Dado** estar logado na sala
**Quando** consulto meu estado autenticado
**Então** descubro meu próprio pseudônimo naquele lote.

**Dado** um lance recusado
**Quando** recebo a resposta
**Então** vejo uma mensagem clara em português para cada motivo: abaixo do mínimo, saldo insuficiente, você já está ganhando, lote ainda não iniciado, lote encerrado.

**Dado** um lance aceito
**Quando** recebo a resposta
**Então** a sala mostra o novo lance atual e meu saldo disponível atualizado.

**Dado** o histórico público da sala
**Quando** é exibido
**Então** não mostra nome, e-mail nem ID real de nenhum licitante.

**Dado** um leiloeiro ou visitante
**Quando** abre a sala
**Então** vê o lote, mas não o formulário de lance.

### Story 3.6: Leiloeiro cancela lote sem lances

Como leiloeiro,
Quero cancelar um lote meu que ainda não recebeu lances,
Para que eu retire uma obra do leilão.

**ADs:** AD-6, AD-7, AD-8, AD-11.

**Critérios de aceite:**

**Dado** um lote meu sem lances
**Quando** o cancelo
**Então** ele passa a cancelado e some da vitrine.

**Dado** um lote com ao menos um lance
**Quando** tento cancelar
**Então** recebo recusa com motivo claro (o estorno automático é o opcional 6.6).

**Dado** um cancelamento e um primeiro lance simultâneos
**Quando** ambos são processados sob a trava do lote
**Então** ou o lote é cancelado sem lances, ou o lance entra e o cancelamento é recusado (teste em PostgreSQL real).

**Dado** um lote de outro leiloeiro, ou um licitante
**Quando** tenta cancelar
**Então** recebe 403.

---

## Épico 4: Sala ao vivo e encerramento

Ao fim do épico, a sala atualiza sem recarregar, os lotes fecham sozinhos com
liquidação idempotente, o comprovante base é gerado com os dados de integridade
já existentes e o leiloeiro vê o resultado e o total recebido.

### Story 4.1: Sala ao vivo por WebSocket: snapshot e atualizações

Como licitante ou visitante da sala,
Quero receber o estado completo do lote ao conectar e ver novos lances, o novo líder e o novo fim sem recarregar,
Para que eu acompanhe a disputa e reaja a tempo.

**ADs:** AD-4, AD-5, AD-10, AD-11, AD-15, AD-19, AD-20, AD-25, AD-29. **Depende de:** Q2 (validar `Origin` no handshake), Q10 (rota do WebSocket). **Detalhe a decidir na criação da story:** significado exato de "posição do usuário nos lances".

**Critérios de aceite:**

**Dado** um lote
**Quando** abro a conexão WebSocket da sala, com ou sem login
**Então** recebo um snapshot completo com apenas dados públicos (pseudônimos, nunca dados pessoais).

**Dado** o snapshot
**Quando** é montado
**Então** a leitura do banco roda em threadpool com Session curta, nunca no event loop
**E** o handshake não altera estado nem liquida lote.

**Dado** dois navegadores na mesma sala
**Quando** um lance é aceito
**Então** o outro recebe novo lance, novo líder e, se houver, o novo fim, sem recarregar.

**Dado** a publicação de eventos
**Quando** um lance é aceito
**Então** o evento sai só depois do commit; um lance recusado ou desfeito não gera evento.

**Dado** estar logado como licitante na sala
**Quando** o estado muda
**Então** vejo de forma clara "você está ganhando" ou "você foi superado", por texto ou ícone, nunca só por cor
**E** vejo minha posição nos lances, obtida por endpoint autenticado.

**Dado** os eventos
**Quando** o front-end os recebe
**Então** eles são tipados em TypeScript.

**Dado** o deploy
**Quando** abro a sala na URL pública
**Então** a conexão WebSocket e as atualizações funcionam pelo Render.

### Story 4.2: Heartbeat e reconexão automática

Como licitante,
Quero que a sala continue funcionando após quedas de rede ou restart do servidor,
Para que eu não perca o leilão sem perceber.

**ADs:** AD-10, AD-14, AD-25. **Depende de:** Q1 (intervalo do heartbeat, tempo limite e espera crescente).

**Critérios de aceite:**

**Dado** uma sala aberta
**Quando** a conexão está ativa
**Então** o cliente envia heartbeat periodicamente e conexões sem heartbeat são encerradas pelo servidor depois do tempo limite.

**Dado** a conexão caiu
**Quando** o cliente percebe
**Então** reconecta com espera crescente, mostra que está reconectando e, ao voltar, aplica o snapshot completo.

**Dado** o processo reiniciou entre um commit e a publicação
**Quando** o cliente reconecta
**Então** o snapshot mostra o estado correto.

### Story 4.3: Fechamento, liquidação idempotente e comprovante base

Como licitante vencedor e como leiloeiro,
Quero que o lote vencido feche uma única vez, debitando o vencedor, creditando o leiloeiro e gerando o comprovante,
Para que o resultado seja correto mesmo se o fechamento rodar mais de uma vez.

**ADs:** AD-3, AD-6, AD-8, AD-9, AD-13, AD-17, AD-20, AD-26.

**Critérios de aceite:**

**Dado** um lote vencido com lances
**Quando** o serviço de fechamento roda
**Então** trava o lote, lê `clock_timestamp()` depois da trava, relê `ends_at` e o estado e liquida: debita o total e libera o comprometido do vencedor sem violar a CHECK em nenhum UPDATE e credita o leiloeiro.

**Dado** a liquidação de um lote com vencedor
**Quando** o comprovante é gerado
**Então** ele registra o vencedor (por pseudônimo, nunca dados pessoais), o valor, a data, a quantidade de lances e o hash final da âncora existentes no momento da liquidação.

**Dado** um lote vencido sem lances
**Quando** o serviço roda
**Então** o lote fecha sem vencedor e sem comprovante.

**Dado** um lote que foi prorrogado depois de ser selecionado para fechamento
**Quando** o serviço o trava e relê `ends_at`
**Então** não fecha.

**Dado** o serviço rodando duas vezes, inclusive em paralelo
**Quando** ambas terminam
**Então** não há débito, crédito ou comprovante duplicado nem troca de vencedor
**E** o banco impõe no máximo um comprovante por lote (`UNIQUE(lot_id)`).

**Dado** os testes
**Quando** rodam em PostgreSQL real
**Então** cobrem fechamento concorrente, idempotência, lote sem lances, prorrogação relida e os dados de integridade no comprovante.

### Story 4.4: Gatilhos do fechamento e evento de encerramento

Como avaliador,
Quero que lotes vencidos fechem sozinhos, inclusive depois de um cold start,
Para que o resultado apareça sem ninguém precisar agir.

**ADs:** AD-9, AD-10, AD-14, AD-19, AD-25. **Depende de:** Q1 (intervalo do scheduler), Q4 (ordem na inicialização), Q6 (quem publica o encerramento), Q9 (lance em lote vencido).

**Critérios de aceite:**

**Dado** o processo acordado
**Quando** um lote vence
**Então** um scheduler interno simples o fecha pelo serviço da 4.3.

**Dado** a aplicação iniciando com lotes vencidos e não liquidados
**Quando** sobe
**Então** executa o catch-up desses lotes antes do funcionamento normal.

**Dado** uma tentativa de lance num lote vencido e não liquidado
**Quando** chega
**Então** o lote é fechado pelo serviço idempotente e a resposta é "lote encerrado".

**Dado** um fechamento que de fato liquidou o lote
**Quando** o commit confirma
**Então** o evento de encerramento/resultado é publicado na sala; uma execução que não fez nada não publica.

**Dado** qualquer GET, HEAD, OPTIONS ou o handshake do WebSocket
**Quando** encontra um lote vencido
**Então** não liquida (teste).

### Story 4.5: Resultado dos lotes no painel do leiloeiro

Como leiloeiro,
Quero ver se cada lote meu encerrado foi arrematado, por quanto, e o total recebido,
Para que eu acompanhe minhas vendas.

**ADs:** AD-3, AD-11, AD-19.

**Critérios de aceite:**

**Dado** lotes meus encerrados e liquidados
**Quando** abro o painel
**Então** vejo para cada um se foi arrematado e por quanto, ou "sem lances".

**Dado** lotes vencidos ainda não liquidados
**Quando** abro o painel
**Então** aparecem como "Encerrado, apurando resultado".

**Dado** o painel
**Quando** o abro
**Então** vejo o total recebido, igual à soma dos lotes liquidados com vencedor.

**Dado** outro leiloeiro
**Quando** abre o painel dele
**Então** não vê os meus lotes nem o meu total.

---

## Épico 5: Auditoria pública, comprovante e meus arremates

Ao fim do épico, qualquer pessoa verifica a integridade do histórico de um lote
a partir dos dados gravados desde o Épico 3, e o vencedor compartilha o
comprovante por link.

### Story 5.1: Verificação pública da integridade do lote

Como qualquer pessoa, sem login,
Quero ver o histórico completo de um lote e saber se ele está íntegro ou foi adulterado,
Para que eu confie no resultado.

**ADs:** AD-13, AD-19, AD-20, AD-21, AD-30.

**Critérios de aceite:**

**Dado** um lote
**Quando** abro a página de auditoria sem login
**Então** vejo todos os lances (pseudônimo, valor, hora, sequência, hashes) e o veredito "íntegro" ou "adulterado", por texto e não só por cor.

**Dado** um histórico sem adulteração
**Quando** a auditoria recalcula a cadeia pela representação canônica v1 e confere a âncora HMAC
**Então** o veredito é "íntegro".

**Dado** um lance alterado, um lance inserido, um lance removido do meio, o último lance removido (truncamento) ou a cadeia recalculada sem o segredo, direto no banco
**Quando** a auditoria verifica
**Então** o veredito é "adulterado" (um teste em PostgreSQL real para cada caso, adulterando o banco diretamente).

**Dado** a auditoria
**Quando** é consultada
**Então** não altera estado nem liquida lote
**E** funciona com a API externa indisponível
**E** não expõe nome, e-mail nem ID real.

### Story 5.2: Comprovante de arremate compartilhável por link

Como licitante vencedor,
Quero um link público para o meu comprovante de arremate,
Para que eu comprove a compra a qualquer pessoa.

**ADs:** AD-9, AD-13, AD-20, AD-22. **Depende de:** Q10 (rotas do comprovante e do link compartilhável).

**Critérios de aceite:**

**Dado** um lote liquidado com vencedor (comprovante base gerado na 4.3)
**Quando** abro o link do comprovante, com ou sem login
**Então** vejo a obra, o valor, a data, o pseudônimo do vencedor, a quantidade de lances, o hash final e o acesso à auditoria do lote.

**Dado** o comprovante público
**Quando** o inspeciono
**Então** não contém nome, e-mail nem ID real.

**Dado** a API externa indisponível
**Quando** abro o comprovante
**Então** ele funciona (só a imagem pode falhar).

### Story 5.3: Meus arremates

Como licitante,
Quero ver os lotes em que dei lance e os que venci, com comprovante e link,
Para que eu acompanhe minha participação.

**ADs:** AD-11, AD-19, AD-30.

**Critérios de aceite:**

**Dado** estar logado como licitante
**Quando** abro "Meus arremates"
**Então** vejo os lotes em que dei lance, com o estado de cada um, e os lotes vencidos com o link do comprovante e opção de copiar o link.

**Dado** um lote vencido ainda não liquidado
**Quando** aparece na lista
**Então** é mostrado como "Encerrado, apurando resultado", sem liquidar na leitura.

**Dado** outro licitante
**Quando** abre a lista dele
**Então** não vê os meus lotes.

---

## Épico 6: Entrega: robustez, documentação e opcionais

Ao fim do épico, a entrega está revisada, documentada e validada no deploy.
As stories 6.5 a 6.7 são opcionais e só entram se o obrigatório estiver verde
(regra de corte do cronograma). O dia 29/10 é buffer: só a 6.4 e correções
pequenas.

### Story 6.1: Revisão de segurança e de erros

Como responsável pela entrega,
Quero confirmar que as proteções da arquitetura valem em todas as rotas e no deploy,
Para que não haja brecha esquecida.

**ADs:** AD-11, AD-12, AD-19, AD-22, AD-29. **Depende de:** Q7 (falha simulada da API).

**Critérios de aceite:**

**Dado** todas as rotas que alteram estado
**Quando** os testes rodam
**Então** cada uma rejeita `Origin` divergente e corpo que não seja JSON.

**Dado** o deploy
**Quando** inspeciono o cookie de sessão
**Então** tem `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain` (e `__Host-`, se possível)
**E** não há CORS permissivo.

**Dado** a API externa simulada como indisponível
**Quando** uso vitrine, sala, auditoria e comprovante
**Então** tudo funciona, exceto a imagem, que cai no placeholder.

**Dado** um erro inesperado em produção
**Quando** acontece
**Então** a resposta é 500 genérico, sem stack.

### Story 6.2: Identidade visual e responsividade

Como usuário,
Quero uma interface com cara de catálogo de leilão de arte, legível no celular,
Para que a experiência seja clara e própria.

**ADs:** AD-15.

**Critérios de aceite:**

**Dado** as telas centrais (vitrine, sala, carteira, painel do leiloeiro, auditoria, meus arremates)
**Quando** as abro
**Então** usam os tokens CSS próprios, com valores e cronômetro muito legíveis.

**Dado** uma tela estreita de celular
**Quando** abro cada tela central
**Então** o conteúdo é utilizável, sem rolagem horizontal.

**Dado** os estados "ganhando", "superado", "encerrado" e "apurando resultado"
**Quando** são exibidos
**Então** têm texto ou ícone, nunca só cor.

### Story 6.3: README completo e registro de uso de IA

Como avaliador,
Quero um README que explique como rodar, avaliar e o que pode surpreender,
Para que eu avalie sem adivinhar.

**ADs:** AD-5, AD-13, AD-14, AD-18, AD-22, AD-25, AD-29.

**Critérios de aceite:**

**Dado** o README
**Quando** o leio
**Então** encontro: configuração e execução local (banco, migrations, `verify`), deploy, roteiro de avaliação com as contas semeadas, e a seção "Comportamentos que podem surpreender": cold start do Render, liquidação tardia, limitação commit/publicação, logout (token vale até `exp`), imagem externa, limites do histórico (segredo HMAC e rollback completo do banco) e anti-sniping sem teto.

**Dado** `docs/uso_de_ia.md`
**Quando** o leio
**Então** cobre todas as stories: onde e como a IA foi usada e o que eu revisei ou ajustei.

**Dado** qualquer número citado no README ou no registro de IA
**Quando** o confiro
**Então** veio de comando realmente executado.

### Story 6.4: Validação final no ambiente publicado

Como avaliador,
Quero que o roteiro de avaliação funcione na URL pública,
Para que eu percorra o fluxo completo sem erros.

**ADs:** AD-14, AD-16, AD-24.

**Critérios de aceite:**

**Dado** a URL pública depois de um cold start
**Quando** sigo o roteiro do README
**Então** completo o fluxo do AD-16: leiloeiro cria lote, lote na vitrine, licitante deposita e dá lance, outro navegador vê sem recarregar, lote encerra e liquida, vencedor abre o comprovante, auditoria diz "íntegro".

**Dado** o banco de produção
**Quando** confiro o seed
**Então** há um leiloeiro, dois licitantes e ao menos um lote demo aberto.

**Dado** o resultado da validação
**Quando** termino
**Então** registro os problemas encontrados e só corrijo os pequenos (regra do buffer).

### Story 6.5: Busca e filtro de lotes

Como visitante,
Quero buscar e filtrar lotes na vitrine,
Para que eu encontre obras de interesse.

**ADs:** AD-19, AD-30.

**Critérios de aceite:**

**Dado** a vitrine
**Quando** busco por texto ou filtro por estado
**Então** vejo só os lotes que atendem, usando apenas o nosso banco, sem cancelados.

### Story 6.6: Cancelamento com estorno automático

Como leiloeiro,
Quero cancelar um lote que já recebeu lances, com o saldo do líder devolvido automaticamente,
Para que eu retire uma obra sem prejudicar o licitante.

**ADs:** AD-3, AD-7, AD-8, AD-13.

**Critérios de aceite:**

**Dado** um lote meu ao vivo ou agendado, com lances
**Quando** o cancelo
**Então** o saldo comprometido do líder volta ao disponível na mesma transação, sob a trava do lote e das carteiras na ordem do AD-8
**E** o histórico de lances é preservado e a auditoria continua dizendo "íntegro".

**Dado** um cancelamento e um lance simultâneos
**Quando** ambos são processados
**Então** o resultado é consistente (teste em PostgreSQL real).

### Story 6.7: Dark mode

Como usuário,
Quero alternar entre tema claro e escuro,
Para que eu use a aplicação com conforto.

**ADs:** AD-15.

**Critérios de aceite:**

**Dado** os tokens CSS
**Quando** alterno o tema
**Então** todas as telas centrais mudam de tema, mantendo contraste legível e estados não dependentes só de cor.

---

## Pendências

Decididas na criação da story indicada, não aqui:
- 1.2: fechada em 23/10/2026 (D1 a D8 e Python 3.13); as decisões ficam no
  arquivo da própria story,
  `_bmad-output/implementation-artifacts/1-2-postgresql-com-bancos-isolados-e-migrations.md`.
- 1.4: resolvida em 24/10/2026; decisões P1 a P14 no arquivo da própria story,
  `_bmad-output/implementation-artifacts/1-4-primeiro-deploy-no-render.md`.
  Rotas técnicas: `GET /api/infra-check/cookie` (cookie `__Host-infra_check`) e
  `/api/infra-check/ws` (WebSocket), ambas fora do OpenAPI. O cookie técnico será
  removido na 2.2 (cookie real do JWT). Depois da 2.2, só o WebSocket técnico continua
  temporariamente; a 2.2 o classifica como rota pública na política de acesso até ele
  ser removido ou substituído na 4.1 (sala ao vivo).
- 3.3: Q3 (`bidder_alias` persistido ou recalculado), agora necessária até 25/10.
- 4.1: significado exato de "posição do usuário nos lances".
- Demais Q1 a Q10: indicadas em cada story.
