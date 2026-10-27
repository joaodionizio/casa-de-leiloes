# Registro de arquitetura: ÁTRIO (nome de trabalho anterior: Casa de Leilões)

> Nome do produto desde 25/10/2026: **ÁTRIO — Leilões de Arte**. Mudança só de
> interface e documentação; nenhuma AD muda (AD-30 mantém repositório, banco, módulos
> e `/api/*` como estão). O texto abaixo, escrito antes do rebranding, preserva
> "Casa de Leilões" onde descreve decisões anteriores.

Fase: **ARQUITETURA CONCLUÍDA; IMPLEMENTAÇÃO EM ANDAMENTO**. O estado original
pré-código foi superado: há implementação das stories dos Epics 1, 2 e 3.
As ADs abaixo preservam suas decisões e alternativas históricas; o estado vivo
de entrega fica no sprint e o fechamento operacional segue
`docs/FECHAMENTO-DE-EPICO.md`. Questões restantes são de implementação.
Esta atualização de cabeçalho (26/10/2026) não declara o Epic 3 encerrado.

Todas as decisões abaixo (AD-1 a AD-30) são **vinculantes**: código que as
contraria está errado. Para mudar uma, altero primeiro este documento. Toda
decisão tem a alternativa descartada; onde eu não registrei uma, está escrito.
As decisões AD-19 a AD-30 correspondem às antigas perguntas Q1 a Q12 (AD-18 + n).

## Quadro-resumo

| AD | Decisão | Alternativa descartada | Consequência técnica principal |
| --- | --- | --- | --- |
| AD-1 | Python + FastAPI | Node.js + Express | Handlers `def` rodam em pool de threads; `async def` só onde precisar (WebSocket) |
| AD-2 | PostgreSQL, SQLAlchemy 2.x síncrono (Session), Alembic, psycopg 3 | MongoDB; MySQL; SQLAlchemy assíncrono | Garantias no banco; o WebSocket assíncrono lê o banco em threadpool (AD-25) |
| AD-3 | Dinheiro em inteiros, em centavos, BIGINT, sufixo `_cents` | float | CHECK é imediata por UPDATE: a ordem das atualizações na liquidação não pode violar `committed_balance_cents <= total_balance_cents` |
| AD-4 | React + Vite + TypeScript simples | JavaScript puro | Contratos HTTP e eventos do WebSocket tipados |
| AD-5 | Anti-sniping: renovação do prazo (lance válido em `0 < restante <= 2 min` leva o fim a `momento do lance + 2 min`). **Revisada em 27/10/2026** | `fim atual + 2 min` (minha decisão original, descartada em 27/10/2026) | O fim pode subir sem teto enquanto houver lances na janela; com exatamente 2 min restantes não há mudança; documentar no README |
| AD-6 | Autoridade de hora: PostgreSQL, `clock_timestamp()` lido depois da trava do lote | Relógio do navegador; relógio da aplicação; hora lida antes da trava | Um único instante por operação |
| AD-7 | Lance = uma única transação (18 passos desde a Story 3.4: autentica o estado anterior antes das regras) | Etapas como operações ou commits independentes, ou só validação na aplicação | Falha em qualquer passo desfaz tudo; histórico não autenticado não aceita lance |
| AD-8 | Travas: lote, depois carteiras em `user_id` crescente | Líder antigo primeiro; novo líder primeiro | Mesma ordem em lance e liquidação |
| AD-9 | Fechamento e liquidação sob a mesma trava do lote, relendo `ends_at`; idempotente; `UNIQUE(lot_id)` em `receipts` | Decidir o encerramento com estado ou hora lidos antes da trava | Rodar duas vezes não repete débito, crédito, comprovante nem vencedor |
| AD-10 | **Reaberta.** WebSocket para atualizações da sala; comandos por REST (`POST /api/lots/{lot_id}/bids`); heartbeat do cliente; snapshot completo ao (re)conectar; 1 processo, connection manager em memória | SSE para esta hospedagem específica | Mensagens do cliente contam como tráfego de entrada no Render gratuito; a reconexão passa a ser do cliente |
| AD-11 | JWT em cookie HttpOnly, mesma origem; Argon2; papéis técnicos `AUCTIONEER` e `BIDDER`; stream da sala público | Token em localStorage; JWT na URL; sessão no banco; nomes técnicos em português | Sem revogação no servidor |
| AD-12 | Art Institute of Chicago; snapshot no lote; seed offline com fixtures | Scryfall; Open Library | Dados de negócio leem só o nosso banco |
| AD-13 | Cadeia SHA-256 + âncora HMAC (`AUDIT_HMAC_SECRET`) | Só SHA-256; só HMAC sem âncora; trigger como mecanismo principal | Auditoria detecta 5 tipos de adulteração |
| AD-14 | Um Web Service gratuito no Render (FastAPI + API + WebSocket + SPA) e PostgreSQL gratuito; `GET /health`; primeiro deploy no épico 1 | Railway Hobby pago; Render pago; Fly.io; front e back separados | Cold start e limites do banco gratuito aceitos |
| AD-15 | Identidade de catálogo de museu / casa de leilões de arte; tokens CSS próprios; dark mode depois | "Mesa de pregão"; UI kit genérico | Estados não dependem só de cor |
| AD-16 | Fluxo vertical completo primeiro | Desenvolver todas as camadas em paralelo antes de fechar um fluxo ponta a ponta | Cortar opcionais sem comprometer o obrigatório |
| AD-17 | Testes críticos em PostgreSQL real | Não informada | Cobrem concorrência e adulteração |
| AD-18 | Git manual; `docs/uso_de_ia.md` contínuo | Não informada | Histórico reflete o meu processo |
| AD-19 | Fechamento em estratégia dupla: scheduler interno simples + catch-up na inicialização e em operações que já alteram estado (tentativa de lance), sempre pelo serviço do AD-9; leituras nunca liquidam; evento só após commit | Depender só de timer em memória; depender só de uma requisição específica; liquidar em GET por ser derivada do tempo | Depois de um cold start, a inicialização liquida os atrasados; leituras mostram "Encerrado, apurando resultado" |
| AD-20 | Pseudônimo por lote: `HMAC(PSEUDONYM_SECRET, "{lot_id}:{user_id}")`, exibindo parte do resultado | Pseudônimo global | Mesmo alias no mesmo lote, alias diferente entre lotes |
| AD-21 | Representação canônica v1 do lance e da âncora (JSON canônico, UTC, 6 casas, sufixo Z, genesis de 64 zeros) | Não registrei | Mesmos bytes e mesmo hash para a mesma entrada, com teste |
| AD-22 | Imagem: não armazenar bytes; guardar `image_id` e referência IIIF; placeholder local se falhar. **Transporte revisado em 24/10/2026:** proxy same-origin controlado (`GET /api/catalog/images/{image_id}`) em vez do hotlink direto do navegador | Baixar e armazenar os bytes; hotlink direto (refutado: 403 do Cloudflare) | Só a imagem depende do museu; o resto não |
| AD-23 | `is_public_domain=true` é filtro obrigatório; snapshot mínimo definido; smoke test com 6 itens | Domínio público apenas como preferência | Só obras de domínio público viram lote |
| AD-24 | Seed idempotente no boot, IDs fixos, lotes demo marcados, novo lote demo só se todos estiverem encerrados; fixtures versionadas | Não registrei | Cold start não duplica usuários nem altera lotes usados |
| AD-25 | WebSocket assíncrono sobre SQLAlchemy síncrono em threadpool, Session curta; publicar só após o commit; sem outbox agora | Outbox agora | Morte do processo entre commit e publicação é corrigida pelo snapshot ao reconectar |
| AD-26 | A regra de domínio recebe `now` por parâmetro; a aplicação lê `clock_timestamp()` após a trava | Não registrei | Domínio sem relógio próprio; testes de integração no caminho real |
| AD-27 | `verify`: pytest, Ruff, `ruff format --check`, integração em PostgreSQL real; ESLint, `tsc --noEmit`, testes existentes e build do Vite no front; PostgreSQL de teste em Docker/Compose | SQLite para comportamento transacional | Docker necessário para testar |
| AD-28 | Monorepo; `uv`; Dockerfile multi-stage; FastAPI serve a SPA; sem estado no filesystem do contêiner | Não registrei | Um serviço, uma origem |
| AD-29 | JWT de 8 h; cookie HttpOnly/Secure/SameSite=Lax/Path=/ sem Domain, `__Host-` quando possível; CSRF: GET/HEAD/OPTIONS sem efeito, JSON, validar Origin (Referer se faltar), sem CORS permissivo | Não registrei | Token copiado vale até `exp` |
| AD-30 | Inglês em código, banco e API; interface e mensagens em português; rotas `/api/...` | Misturar português e inglês no domínio técnico | Tabelas `users`, `wallets`, `lots`, `bids`, `receipts` |

## Decisões

### AD-1. Back-end: Python + FastAPI
**Decidi** usar Python e FastAPI.

**Por quê:** quero desenvolver este desafio com FastAPI e revisar a stack com a
qual já tive contato anteriormente durante a implementação, usando o Claude Code
para acelerar a execução, mas revisando e entendendo o código antes de cada
commit.

**Descartei:** Node.js + Express. Eu já havia estudado JavaScript, mas optei
conscientemente por FastAPI para este projeto.

### AD-2. Banco de dados: PostgreSQL, SQLAlchemy 2.x síncrono, Alembic, psycopg 3
**Decidi** usar PostgreSQL, SQLAlchemy 2.x, Alembic para migrations e psycopg 3
como driver. O SQLAlchemy é usado de forma síncrona, com `Session`.

**Por quê:** o domínio exige transações, concorrência entre lances,
movimentação coordenada de saldos, bloqueio de linhas, constraints e
consistência entre várias entidades. Quero que essas garantias sejam apoiadas
pelo banco. A API síncrona do SQLAlchemy também torna o fluxo transacional mais
simples de escrever, revisar e explicar dentro do prazo.

O endpoint WebSocket (AD-10) é assíncrono, sem obrigar toda a camada de
persistência a usar `AsyncSession` (detalhe no AD-25). Esta frase substitui a
versão anterior, que falava em SSE.

**Descartei:**
- MongoDB: não oferece vantagem relevante para este domínio fortemente
  relacional e transacional.
- MySQL: seria viável, mas escolhi PostgreSQL.
- SQLAlchemy assíncrono: adicionaria complexidade que não considero necessária
  para a escala deste desafio.

### AD-3. Dinheiro em inteiros, em centavos
**Decidi** representar todos os valores monetários como inteiros em centavos.
Exemplo: R$ 120,00 = 12000. No PostgreSQL, uso `BIGINT`.

**Nomes:** em inglês, com sufixo `_cents` (AD-30). Exemplos já definidos:
`total_balance_cents` e `committed_balance_cents`. Os demais valores
(lance inicial, incremento mínimo, lance atual e equivalentes) seguem o mesmo
padrão, com nomes exatos definidos na modelagem. Isso substitui a convenção
anterior em português (`saldo_total_centavos` etc.).

**Constraints:** crio constraints de banco, quando aplicável, para garantir pelo
menos:
- valores monetários não negativos;
- saldo comprometido não negativo;
- `committed_balance_cents <= total_balance_cents`.

**Por quê:** evitar erros de precisão e simplificar comparações e invariantes de
saldo.

**Descartei:** float. Não uso float para dinheiro em nenhuma camada.

### AD-4. Front-end: React + Vite + TypeScript
> **Confirmado (fecha o antigo B1):** TypeScript. Qualquer referência a
> JavaScript puro no AD-28 (antiga Q10) foi corrigida.

Esta decisão substitui a direção anterior de JavaScript puro.

**Decidi** usar React, Vite e TypeScript.

**Por quê:** embora TypeScript não seja obrigatório no enunciado, escolhi usá-lo
para tornar explícitos os contratos entre FastAPI e front-end; reduzir erros de
integração; tipar estados importantes do domínio, payloads e respostas da API e
eventos do WebSocket; e facilitar manutenção e refatoração durante os sete dias.
Aceito a curva adicional de aprendizado porque a implementação será assistida
por IA e eu revisarei o código.

**Regra de complexidade:** o TypeScript permanece simples e explicável.
- Prefiro: `interface`, `type`, `string`, `number`, `boolean`, `null`, arrays,
  props tipadas, `Promise<T>`, unions simples, tipos dos contratos HTTP e tipos
  dos eventos do WebSocket.
- Evito, salvo necessidade real e previamente explicada: generics complexos,
  conditional types, mapped types sofisticados, abstrações excessivamente
  genéricas e construções que eu não conseguiria explicar em uma entrevista.
- Se uma solução simples e uma sofisticada resolverem o mesmo problema, prefiro
  a simples.

**Descartei:** JavaScript puro. Seria suficiente para cumprir o desafio e teria
menor curva inicial, mas escolhi TypeScript porque o custo adicional é aceitável
antes do início da implementação e os contratos explícitos agregam valor neste
projeto.

### AD-5. Anti-sniping: renovação do prazo a partir do lance (revisada em 27/10/2026)
O enunciado diz: "lance aceito nos últimos 2 minutos estende o fim do lote
para +2 minutos". A frase permite duas interpretações:

- A) novo fim = momento do lance + 2 minutos
- B) novo fim = horário final atual + 2 minutos

**Decisão vigente (27/10/2026).** **Decidi** a opção A. Se um lance válido for
aceito quando `0 < ends_at - now <= 2 minutos` (janela inclusiva), o término alvo
passa a ser `now + 2 minutos`, com o mesmo `now` lido de `clock_timestamp()` depois
da trava do lote (AD-6, AD-26). Cada novo lance válido dentro da janela renova o
prazo para dois minutos depois do próprio lance, sem teto.

- O lote nunca reabre depois de encerrado: `now >= ends_at` é recusa `lot_ended`.
- Se `now + 2 minutos` for igual ao `ends_at` atual (restam exatamente 2 minutos),
  não há alteração efetiva do término e `anti_sniping_applied` permanece falso.
  Para restante estritamente menor que 2 minutos, o alvo é maior que o fim atual,
  então o fim sobe e a flag é verdadeira. O fim nunca diminui.
- Lance recusado nunca altera o fim.
- `ends_at` não faz parte da representação canônica v1 (AD-21) nem da cadeia
  SHA-256/âncora HMAC (AD-13): esta mudança não toca nenhuma delas.
- Não faço nenhuma alteração retroativa em lotes ou lances já persistidos; só os
  lances aceitos depois desta revisão seguem a regra nova.

**Exemplo:**
- fim atual 20:00; lance válido às 19:59; novo fim 20:01
- fim atual 20:01; lance válido às 20:00:30; novo fim 20:02:30
- fim atual 20:00; lance válido às 19:58 (exatamente 2 min restantes): o fim
  continua 20:00 e `anti_sniping_applied` é falso
- fim atual 20:00; lance válido às 19:57: fora da janela, o fim não muda

**Por quê:** inicialmente interpretei a frase do enunciado como a opção B. Depois
de refletir de novo sobre o comportamento esperado de um anti-sniping, mudei para a
opção A. Como o enunciado continua ambíguo, a escolha fica documentada aqui e no
README, em "Comportamentos que podem surpreender".

**Descartei:** `novo fim = horário final atual + 2 minutos` (opção B).

**Histórico da decisão.** Até 26/10/2026 a AD-5 dizia o contrário, e a
implementação das Stories 3.2 e 3.4 seguiu isso: eu havia **decidido** a opção B
(extensão cumulativa do horário final atual: `ends_at + 2 minutos`) e **descartado**
`novo fim = momento_do_lance + 2 minutos`. Troquei de interpretação em 27/10/2026,
antes da Story 4.1. A regra antiga valeu enquanto esteve em vigor: as Stories 3.2 e
3.4 e o deploy 2+3 (commit `3d3ea97`) a refletem, e os artefatos delas
permanecem como registro do que eu decidi na época, com nota de revisão. Lances já
gravados e `ends_at` já persistidos não são reescritos.

### AD-6. Fonte de hora: o PostgreSQL
**Decidi** que a autoridade para decisões críticas de tempo é o PostgreSQL.

Fluxo para lance e fechamento:
1. iniciar a transação;
2. adquirir a trava do lote;
3. depois da aquisição da trava, consultar `clock_timestamp()` no PostgreSQL;
4. guardar esse instante localmente;
5. usar exatamente esse instante em todas as decisões daquela operação.

Não uso o relógio do navegador para decisões de domínio. Não uso o horário
capturado antes de esperar pela trava. O front-end pode calcular a contagem
regressiva visualmente, mas o navegador nunca decide se um lote ainda aceita
lances.

**Testes:** a lógica de domínio permite horário controlável/injetável (AD-26).

**Por quê:** quero uma única autoridade temporal próxima dos dados que estão
sendo protegidos pela trava. Isso evita divergências entre relógios da
aplicação, do navegador e do banco e impede que o tempo usado na decisão fique
obsoleto enquanto a transação espera por uma trava.

**Descartei:** relógio do navegador; relógio da aplicação como autoridade
definitiva; horário capturado antes da aquisição da trava.

### AD-7. A aceitação de um lance é uma única transação
**Decidi** que a aceitação de um lance é uma única unidade transacional:

1. iniciar a transação;
2. bloquear o lote (`SELECT ... FOR UPDATE`);
3. capturar o horário atual do banco (`clock_timestamp()`, AD-6);
4. autenticar a cadeia, a âncora e a HMAC anteriores e vincular o estado
   operacional do lote (lance atual e líder) ao último lance autenticado (AD-13);
5. validar estado e período, lance mínimo e líder (regras pré-carteira);
6. identificar as carteiras envolvidas;
7. adquirir as travas das carteiras (AD-8);
8. validar o saldo disponível;
9. liberar o saldo comprometido do líder anterior;
10. comprometer o saldo do novo líder;
11. atualizar o líder e o lance atual;
12. aplicar o anti-sniping (AD-5: alvo `now + 2 min`, com o `now` do passo 3), se necessário;
13. definir a sequência como `bid_count` autenticado + 1;
14. gerar o pseudônimo (AD-20);
15. montar a representação canônica (AD-21) com o mesmo instante do passo 3;
16. calcular o hash e registrar o lance;
17. calcular e gravar a nova âncora: quantidade, hash final e HMAC (AD-13);
18. confirmar a transação.

Nenhuma dessas operações pode ficar parcialmente aplicada: uma falha em qualquer
passo desfaz tudo. Uma falha no passo 4 encerra a operação sem nenhum efeito.

**Refinamento de 26/10/2026 (Story 3.4).** A versão original tinha 16 passos, com
as regras logo depois da hora e o registro do lance num passo só. Acrescentei o
passo 4 por dois motivos. Primeiro, nenhum histórico pode ser estendido antes de o
estado anterior ser autenticado: senão, ao aceitar um lance legítimo, o serviço
assinaria um histórico adulterado no banco (lavagem por reautenticação, achado S-01
da Story 3.3). Segundo, o lance atual e o líder entram no mínimo, no "já está
ganhando" e na liberação de saldo, e não são cobertos pela âncora; só podem ser
usados depois de vinculados ao último lance autenticado. Desdobrei também o antigo
"registrar o lance" nos passos 13 a 16. A contagem de passos não é contrato; a
ordem e a atomicidade são. **Descartei** autenticar depois das regras pré-carteira
(as recusas sairiam sobre estado não autenticado) e verificar depois de escrever
(assinaria o estado adulterado). Detalhes em
`_bmad-output/implementation-artifacts/3-4-lance-transacional-com-travas-e-anti-sniping.md`.

**Descartei:** implementar as etapas do lance como operações ou commits
independentes, ou confiar apenas em validações na camada de aplicação. Isso
poderia gerar estados inconsistentes como: líder atualizado sem saldo
comprometido; saldo anterior liberado sem persistir o novo lance; histórico
gravado sem atualização consistente do lote; extensão de horário sem o restante
da operação.

### AD-8. Ordem das travas
**Decidi** manter uma ordem determinística para reduzir o risco de deadlock:

1. lote;
2. carteiras necessárias, sempre em ordem crescente de `user_id`.

Nunca adquiro uma carteira primeiro e depois o lote. Com duas carteiras, não uso
como critério "líder antigo primeiro" nem "novo líder primeiro": uso sempre a
mesma ordenação determinística. O mesmo princípio vale para outras operações que
movimentem várias carteiras, inclusive a liquidação.

**Por quê:** reduzir o risco de deadlock.

**Descartei:** ordenar as carteiras pelo papel (líder antigo primeiro ou novo
líder primeiro).

### AD-9. Fechamento e liquidação
**Decidi** que o fechamento adquire a mesma trava do lote usada pelo lance:

1. iniciar a transação;
2. `SELECT ... FOR UPDATE` no lote;
3. adquirir a trava;
4. consultar o horário atual do banco (AD-6);
5. reler `ends_at` e o estado do lote;
6. verificar se houve prorrogação;
7. se o lote ainda não venceu, não fechar;
8. se já estiver fechado/liquidado, não repetir efeitos;
9. se realmente venceu, executar a liquidação.

O fechamento é idempotente. Rodá-lo duas vezes não pode debitar duas vezes,
creditar duas vezes, gerar dois comprovantes nem alterar novamente o vencedor.

**Garantia estrutural:** no máximo um comprovante por lote vencedor, por exemplo
`UNIQUE(lot_id)` em `receipts`.

**Por quê:** a idempotência impede os efeitos duplicados descritos acima.

**Descartei:** decidir o encerramento usando estado ou horário lidos antes da
aquisição da trava.

### AD-10. Tempo real: WebSocket (reaberta)
Esta decisão **reabre e substitui** a versão anterior, que usava SSE.

**Decidi** usar WebSocket para receber atualizações da sala em tempo real. Os
comandos continuam REST, por exemplo `POST /api/lots/{lot_id}/bids`. A resposta
do POST informa imediatamente se o lance foi aceito ou recusado, com o motivo
exato da recusa. **Os lances não são enviados pelo WebSocket.**

**Heartbeat:** o cliente envia um heartbeat periódico enquanto estiver
conectado.

**Eventos:** snapshot inicial; novo lance; novo líder; novo horário após
anti-sniping; encerramento; liquidação/resultado.

**Reconexão:** ao reconectar, o servidor sempre envia um snapshot completo, então
eventos perdidos não deixam a interface inconsistente.

**Escala desta entrega:** um único processo, com connection manager em memória.
Sem Redis nem outro broker agora. Com vários workers no futuro, seria preciso
avaliar PostgreSQL `LISTEN/NOTIFY` ou Redis.

**Por quê:** como decidi permanecer no Render gratuito, quero que uma sala de
leilão aberta não dependa de um stream SSE que possa ficar sujeito ao sleep do
serviço por falta de tráfego de entrada. No Render gratuito, conexões WebSocket
com mensagens recebidas contam como tráfego de entrada; o heartbeat do cliente
aproveita isso.

**Descartei:** SSE para esta hospedagem específica.

**Rota e `Origin` da sala (decididos em 27/10/2026, Story 4.1; fecham Q2 e a parte
WebSocket da Q10, sem alterar a decisão acima):** a sala usa
`/ws/lots/{lot_id}`, na mesma origem; o lance segue só em
`POST /api/lots/{lot_id}/bids`. O handshake é público, sem JWT na URL. Se o
cabeçalho `Origin` existir, ele precisa ser igual à `APP_ORIGIN` configurada
(esquema, host e porta normalizada); origem diferente, malformada ou `null` é
rejeitada. Se não existir (cliente que não é navegador), aceito. Descartei exigir
`Origin` sempre (quebra scripts de teste sem ganho real num stream público) e não
validar nada (deixa uso cruzado entre sites sem barreira). Rota do comprovante e
do link continuam em aberto.

### AD-11. Autenticação: JWT em cookie HttpOnly, mesma origem
**Decidi** usar JWT em cookie HttpOnly, com aplicação em mesma origem. Em
produção: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`. O FastAPI serve a API e
o build do React/Vite, o que coloca front-end e back-end na mesma origem. Os
detalhes de duração, prefixo do cookie e proteção contra CSRF estão no AD-29.

- **Senhas:** Argon2, por biblioteca apropriada.
- **Papéis técnicos (fecha o antigo B3):** `AUCTIONEER` (leiloeiro) e `BIDDER`
  (licitante), por exemplo `UserRole.AUCTIONEER` e `UserRole.BIDDER`. No banco,
  no JWT e na API uso só esses identificadores em inglês; não uso mais
  LEILOEIRO nem LICITANTE em código, banco ou payloads. Na interface em
  português aparecem como "Leiloeiro" e "Licitante". `AUCTIONEER` cria e
  gerencia os próprios lotes e não pode dar lances. `BIDDER` deposita saldo, dá
  lances e arremata itens, mas não cria lotes.
- **Token:** de duração moderada (8 horas, AD-29). Sem refresh token
  inicialmente. O logout remove/invalida o cookie no navegador. Não coloco dados
  pessoais desnecessários no JWT.
- **WebSocket:** o stream da sala pode ser público e transportar apenas
  informações públicas/pseudonimizadas. Informações pessoais ou específicas da
  conta continuam vindo de endpoints autenticados.

**Por quê:** a aplicação é same-origin, então o cookie HttpOnly reduz a
exposição do token ao JavaScript e mantém a autenticação simples no front-end.
JWT evita introduzir armazenamento de sessões no banco dentro do prazo.

**Descartei:** token armazenado em localStorage; JWT colocado na URL; sessão
persistida no banco nesta entrega; nomes técnicos de papéis em português.

### AD-12. API externa: Art Institute of Chicago
**Decidi** usar a API do Art Institute of Chicago. O domínio dos itens é obras
de arte.

**Regras:**
- Uso somente obras de domínio público (AD-23).
- Na criação do lote, copio para o nosso banco os dados necessários (AD-23).
- Depois que o lote é criado, vitrine, sala, auditoria e comprovante não
  dependem da disponibilidade da API externa para os seus dados de negócio. Não
  uso a API externa como back-end em tempo de leitura dos lotes existentes. A
  imagem é a única exceção, tratada no AD-22.
- Seed e testes: fixtures locais. O seed funciona offline e não depende da API
  externa (AD-24).
- Antes da implementação completa, faço um smoke test pequeno da integração real
  (itens no AD-23).

**Por quê:** o catálogo de obras de arte combina naturalmente com o domínio de
uma casa de leilões e fornece conteúdo visual adequado ao produto.

**Descartei:** Scryfall e Open Library.

### AD-13. Histórico à prova de adulteração: cadeia SHA-256 + âncora HMAC
**Decidi** usar cadeia de hashes SHA-256 + âncora final protegida por HMAC.

**Cadeia:** cada lance tem a representação canônica definida no AD-21: versão,
ID do lote, número de sequência, pseudônimo do licitante (AD-20), valor em
centavos, timestamp e hash anterior. O lance grava seu `hash_atual`. O próximo
lance incorpora o hash anterior.

**Âncora:** o lote mantém dados de integridade contendo pelo menos: ID do lote;
quantidade de lances; hash final. Esses dados recebem uma assinatura HMAC. O
segredo do HMAC (`AUDIT_HMAC_SECRET`) fica fora do banco, em variável de
ambiente, e nunca é versionado. Ele é diferente do `PSEUDONYM_SECRET`.

**Auditoria:** detecta pelo menos: alteração de lance; inserção; remoção do
meio; remoção do último lance (truncamento); tentativa de recalcular a cadeia
sem possuir o segredo.

**Comprovante:** registra também a quantidade de lances e o hash final existente
na liquidação.

**Limitações declaradas no README:** comprometimento do segredo HMAC; rollback
completo do banco para um estado antigo consistente pode exigir uma âncora
externa para detecção absoluta.

**Por quê:** preciso detectar tanto alterações internas na cadeia quanto
truncamento ou tentativa de recalculá-la diretamente no banco. A cadeia SHA-256
mantém a sequência verificável, enquanto a âncora protegida por HMAC adiciona
uma prova que não pode ser recalculada apenas com acesso ao banco.

**Descartei:**
- somente SHA-256 encadeado;
- somente HMAC sem âncora de quantidade/hash final;
- trigger como mecanismo principal. Um trigger contra UPDATE/DELETE pode entrar
  apenas como defesa adicional, se houver tempo.

**Refinamento de 26/10/2026 (Stories 3.3 e 3.4), sem mudar a representação v1:**
- **Antes de estender o histórico**, sob a trava do lote, autentico o estado
  anterior: cadeia coerente para o lote; âncora com o mesmo `lot_id`, `bid_count`
  igual à quantidade de lances e `final_hash` igual ao último hash (genesis sem
  lances); HMAC válida. Falha responde 409 `lot_integrity_conflict`, com mensagem
  genérica, sem efeito, sem reparar e sem reassinar.
- **Vínculo operacional.** A HMAC protege o histórico canônico, mas o lance
  canônico v1 não contém `current_leader_id` nem o identificador real do usuário.
  Sem vínculo, adulterar esses ponteiros no lote desviaria a liberação de saldo para
  a carteira errada. Por isso, com lances, exijo que o último lance tenha
  `sequence = bid_count`, que o lance atual e o líder do lote sejam iguais aos dele e
  que o pseudônimo recalculado **só do líder atual** seja igual ao alias autenticado
  do último lance. Sem lances, lance atual e líder são vazios e a âncora é
  exatamente `0`/genesis com HMAC válida. Isso não é auditoria: a auditoria usa o
  alias gravado e nunca recalcula alias histórico (AD-20).
- **Inicialização.** Todo lote novo nasce com âncora vazia (`0`, genesis) assinada
  na mesma transação do `INSERT`. Lote anterior à Story 3.4 fica com âncora nula:
  não autenticado e sem aceitar lance. Assinatura ausente nunca vale como estado
  confiável. Nada reassina estado encontrado no banco (lance, boot, seed ou
  migration). **Descartei** a migration com o segredo, a reassinatura no boot
  (qualquer filtro seria dado manipulável do banco) e "âncora nula + zero lances =
  confiável".
- **Segredos operacionais.** `AUDIT_HMAC_SECRET` e `PSEUDONYM_SECRET` têm pelo menos
  32 bytes em UTF-8, são diferentes entre si e do `JWT_SECRET`, e a aplicação não
  inicia sem isso. O tamanho não garante entropia: uso valores aleatórios fortes.
  Os primitives puros continuam aceitando quaisquer `bytes` não vazios.
- **Limitação.** A âncora v1 não autentica os termos do lote (inclusive `ends_at`)
  nem os saldos das carteiras.

### AD-14. Hospedagem e deploy: Render gratuito, um único serviço
**Decidi** manter o projeto sem custo financeiro e usar o Render no plano
gratuito, desde que o teste de deploy confirme que atende ao desafio.

**Produção:**
- um único Web Service gratuito, com FastAPI, API, WebSocket e o build estático
  do React/Vite servido pelo próprio FastAPI (mesma origem);
- PostgreSQL gratuito do Render.

**Por quê:** o desafio dura sete dias e a carga esperada é pequena. Já tenho
experiência pessoal usando o Render em outro projeto e não quero assumir custo
sem necessidade comprovada.

**Limitações aceitas:** o plano gratuito pode ter cold start depois de período
sem tráfego. Isso será testado cedo, documentado no README e informado no
roteiro de avaliação. O banco gratuito também pode ter limitações de duração e
recursos, aceitáveis para o período do desafio.

**Mitigação:** criar `GET /health`. Fazer o primeiro deploy muito cedo, ainda no
primeiro épico, para validar FastAPI, PostgreSQL, React, WebSocket, cookies e
migrations. Não deixar o deploy para o fim. Ao reconectar o WebSocket depois de
queda/restart, o snapshot completo do lote recupera o estado.

Se surgir uma limitação comprovada do Render gratuito que impeça algum requisito
obrigatório, a decisão pode ser reaberta antes da entrega.

**Descartei:** Railway Hobby pago; Render pago inicialmente; Fly.io; separar
front-end e back-end em provedores diferentes nesta primeira entrega.

### AD-15. Identidade visual: catálogo de museu / casa de leilões de arte
**Decidi** seguir a direção visual de catálogo de museu / casa de leilões de
arte: estética editorial; bastante respiro; hierarquia visual forte; destaque
para obra e artista; valores monetários muito legíveis; cronômetro muito
legível; aparência própria; evitar dashboard genérico gerado por IA. Uso poucos
componentes reutilizáveis e tokens CSS próprios.

**Telas centrais:** vitrine; sala do lote ao vivo; carteira; painel do
leiloeiro; auditoria pública; meus arremates.

Estados como "você está ganhando", "você foi superado" e "lote encerrado" não
dependem somente de cor: uso também texto, ícone ou outra indicação acessível.

**Dark mode:** continua opcional. Estruturo os tokens para que possa ser
adicionado depois, mas não gasto tempo com ele antes dos fluxos obrigatórios.

**Por quê:** a identidade de catálogo de museu combina com a API e com o domínio
escolhido, diferencia a aplicação de um dashboard genérico e mantém foco visual
nas obras, valores e estado do leilão sem exigir uma biblioteca pesada de
componentes.

**Descartei:** a identidade "mesa de pregão"; UI kit genérico como identidade
principal.

**Atualização de 25/10/2026 (identidade ÁTRIO, sem mudar a AD).** O produto passou a se
chamar **ÁTRIO — Leilões de Arte**, com símbolo próprio em forma de arco/portal e
palavra "ÁTRIO". Segue a direção desta AD (catálogo/galeria, obra protagonista, muito
branco, roxo como marca e ação, títulos serifados, respiro): referência principal é a
identidade ÁTRIO que escolhi; a AURA é referência complementar de densidade, cards e
acabamento, sem copiar nome, logo, textos ou imagens. Não antecipo funcionalidade das
referências (lance, contagem regressiva, favoritos, busca pública, carteira). O
refinamento visual final continua previsto depois das funcionalidades críticas
(Story 6.2). Detalhes em `DESIGN.md` §2.

### AD-16. Prioridade de implementação: fluxo vertical primeiro
**Decidi** que a arquitetura favorece este fluxo vertical, entregue completo
antes de qualquer outra coisa:

1. leiloeiro cria lote;
2. lote aparece na vitrine;
3. licitante abre a sala;
4. licitante possui saldo;
5. licitante faz lance;
6. lance passa pelas regras transacionais;
7. outro cliente recebe atualização sem recarregar;
8. histórico fica persistido;
9. lote encerra corretamente;
10. ocorre liquidação;
11. vencedor recebe comprovante;
12. auditoria consegue verificar o histórico.

Opcionais e melhorias visuais vêm depois.

**Por quê:** quero reduzir o risco de terminar sete dias com muitas partes
isoladas e nenhum fluxo completo. Um caminho ponta a ponta funcionando cedo
permite testar integração, deploy e regras reais e facilita cortar opcionais sem
comprometer a entrega obrigatória.

**Descartei:** desenvolver todas as camadas ou funcionalidades em paralelo antes
de fechar um fluxo ponta a ponta.

### AD-17. Testes críticos em PostgreSQL real
**Decidi** manter a regra: testes críticos usam PostgreSQL real (AD-27). Prioridade
especial para: dois lances simultâneos; saldo disponível/comprometido; líder
anterior sendo superado; anti-sniping; tentativa de lance depois do fim;
fechamento concorrente; idempotência da liquidação; adulteração do histórico;
permissões por papel. Não afrouxo teste para fazer código passar.

**Por quê:** as garantias do domínio são apoiadas pelo banco (AD-2).

**Descartei:** não registrei alternativa para esta decisão.

### AD-18. Git e IA
**Decidi** manter as regras atuais: o Git é responsabilidade minha; o Claude não
executa commits; um commit por unidade coerente/story; as decisões são minhas e
o Claude implementa a partir delas; eu reviso antes dos commits;
`docs/uso_de_ia.md` é atualizado durante o desenvolvimento; qualquer número
mencionado vem de comando realmente executado.

**Por quê:** o histórico e o registro de IA refletem o meu processo.

**Descartei:** não registrei alternativa para esta decisão.

### AD-19. Gatilho do fechamento: estratégia dupla, sem liquidar em leituras
Esta decisão incorpora a resolução do antigo B2.

**Decidi** usar estratégia dupla. GET, HEAD e OPTIONS nunca alteram estado.

**Enquanto o processo estiver acordado:** um scheduler interno simples procura
lotes vencidos periodicamente e chama o mesmo serviço de fechamento idempotente
do AD-9. Não quero uma biblioteca pesada de jobs se um loop simples de aplicação
resolver.

**Catch-up:** o fechamento atrasado pode ser disparado apenas por:
1. a inicialização da aplicação, que executa o catch-up dos lotes vencidos antes
   do funcionamento normal. Depois de um cold start do Render, isso liquida os
   atrasados;
2. o scheduler interno, enquanto o processo estiver acordado;
3. operações que já alteram estado, especialmente a tentativa de lance.

**Tentativa de lance:** se chegar `POST /api/lots/{lot_id}/bids` e o lote já
estiver vencido, o fluxo pode primeiro executar o serviço idempotente de
fechamento/liquidação e, depois, devolver a resposta de lote encerrado.

**Leituras:** nenhuma leitura liquida. Isso vale para abrir sala, consultar
resultado, consultar meus arremates, o handshake do WebSocket e qualquer outra
leitura. Se uma leitura encontrar `ends_at <= agora` e o lote ainda não
liquidado, ela não liquida. A resposta representa um estado transitório
equivalente a "Encerrado, apurando resultado".

**O fechamento sempre:** abre transação; trava o lote; obtém `clock_timestamp()`;
relê `ends_at`; decide; liquida de forma idempotente; faz commit. Somente depois
de um commit bem-sucedido é publicado o evento WebSocket de encerramento.

**Por quê:** preservar a semântica HTTP, a proteção contra CSRF, a idempotência
e a ausência de efeitos colaterais em GET.

**Descartei:**
- depender exclusivamente de timer em memória ou exclusivamente de uma
  requisição específica;
- permitir que requisições GET executem liquidação apenas por ela ser derivada
  do tempo.

### AD-20. Pseudônimo determinístico por lote
**Decidi** usar pseudônimo determinístico por lote, não global, gerado com HMAC e
segredo próprio:

`HMAC(PSEUDONYM_SECRET, "{lot_id}:{user_id}")`

Exibo apenas parte suficiente do resultado, por exemplo `Licitante-A83F19C2`. O
mesmo usuário mantém o mesmo pseudônimo dentro do mesmo lote, recebe pseudônimo
diferente em lotes diferentes e não expõe nome, e-mail nem ID real.

Não persisto o mapeamento se ele puder ser regenerado deterministicamente. O
front-end descobre o pseudônimo do usuário atual por um endpoint autenticado
(estado autenticado da sala). O snapshot público contém apenas pseudônimos. O
`PSEUDONYM_SECRET` é diferente do `AUDIT_HMAC_SECRET`.

**Descartei:** pseudônimo global.

**Refinamento de 26/10/2026 (Story 3.3, Q3).** O alias é `Licitante-` seguido dos
primeiros 16 caracteres hexadecimais, em maiúsculas, do HMAC-SHA-256 (o exemplo de
8 caracteres acima e no AD-21 é ilustrativo). Ele é **persistido em cada lance** e
entra no hash; a auditoria usa o valor gravado e nunca recalcula nem reescreve
alias histórico. Não há tabela de mapeamento. Os dois segredos são configuração
estável: rotação transparente não é suportada. A Story 3.4 recalcula apenas o alias
do líder atual, para o vínculo operacional do AD-13. **Descartei** recalcular o
alias na auditoria (trocar o segredo mudaria bytes históricos).

### AD-21. Representação canônica do lance, versão v1
**Decidi** definir a versão `v1`. Representação lógica: `v`, `lot_id`,
`sequence`, `bidder_alias`, `amount_cents`, `timestamp`, `previous_hash`.

Serialização em JSON canônico:
- UTF-8;
- chaves ordenadas;
- separadores mínimos, sem espaços;
- inteiros permanecem inteiros;
- UUID em string lowercase;
- timestamp sempre em UTC, com exatamente 6 casas de microssegundos e sufixo `Z`.

Exemplo conceitual:

```
{"amount_cents":12000,"bidder_alias":"Licitante-A83F19C2","lot_id":"...","previous_hash":"...","sequence":3,"timestamp":"2026-10-23T04:15:30.123456Z","v":1}
```

O primeiro lance usa um valor genesis claramente definido para `previous_hash`:
64 zeros hexadecimais. A âncora HMAC também usa serialização canônica
versionada. Adiciono testes que provam que a mesma entrada produz sempre
exatamente os mesmos bytes e o mesmo hash.

**Descartei:** não registrei alternativa para esta decisão.

### AD-22. Imagem da obra: carregada direto do IIIF
> **Transporte revisado em 24/10/2026 (Story 2.3):** o hotlink direto do navegador
> deu 403 e foi trocado por proxy same-origin controlado; veja "Revisão da
> consequência técnica" no fim deste AD. O texto abaixo é a decisão original.

**Decidi** não baixar nem armazenar os bytes das imagens. Persisto `image_id`, a
URL/referência IIIF necessária e os metadados/atribuição necessários. O
front-end carrega a imagem diretamente do IIIF do Art Institute.

Se a imagem externa falhar, mostro um placeholder local e mantenho título,
artista, valores, lance, histórico e demais funções funcionando. A aplicação não
depende da API externa para seus dados de negócio. A disponibilidade da mídia
externa pode afetar a imagem, mas nunca torna a vitrine ou a sala inutilizável.
Documento essa distinção no README.

**Descartei:** baixar e armazenar os bytes das imagens.

**Revisão da consequência técnica (24/10/2026, Story 2.3).** A decisão original
previa que o navegador carregasse a imagem direto do IIIF (hotlink). O teste manual
da Story 2.3 refutou essa suposição: toda requisição `default.jpg` do navegador
recebeu HTTP 403 do Cloudflare da AIC, que exige uma identificação (`User-Agent` e
`AIC-User-Agent`) que a tag `<img>` não consegue enviar; o mesmo URL pedido pelo
servidor com esses cabeçalhos devolve 200 `image/jpeg`. O placeholder funcionou, mas
deixaria todas as obras sem imagem. **Decidi** então ajustar só o transporte, para um
proxy same-origin controlado: `GET /api/catalog/images/{image_id}`, que busca
`https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg` no servidor e
devolve o JPEG. O que continua valendo: os bytes **não são armazenados nem
persistidos** (ficam só em memória durante a resposta, sem filesystem, banco ou
cache), guardo `image_id` e a referência, e a falha da mídia degrada para o
placeholder local sem afetar o resto. O proxy não é genérico: aceita só `image_id`
validado (UUID minúsculo), com host, esquema, caminho, tamanho e formato fixos,
`follow_redirects=False`, teto de tamanho e conferência de tipo e assinatura JPEG; é
público (`PUBLIC`) por tratar obras de domínio público sem dado de conta e por servir
também a vitrine pública (Story 2.5). Isto revisa a consequência técnica do AD-22,
não o domínio da decisão. **Descartei** manter o hotlink (não funciona), baixar e
guardar as imagens, e um proxy genérico. Detalhes na Story 2.3 (P6.1).

### AD-23. Domínio público obrigatório e snapshot mínimo
**Decidi** que, nesta entrega, domínio público é filtro obrigatório, não apenas
preferência. Só permito criar lotes de obras com `is_public_domain=true`.

**Snapshot mínimo no lote:** `external_id`; `title`; `artist_display`;
`date_display`; `medium_display`; `department_title`; `artwork_type_title`;
`image_id`; referência/URL IIIF; informação de crédito/origem necessária; URL da
fonte, se disponível.

**O smoke test da API verifica:** busca; detalhe; filtro `is_public_domain=true`;
imagem IIIF; campos utilizados; comportamento quando a API está indisponível.

**Descartei:** domínio público apenas como preferência.

### AD-24. Seed idempotente na inicialização
**Decidi** que o seed é idempotente e pode ser executado na inicialização.

- Usuários semeados têm identificadores fixos e nunca são recriados se já
  existirem.
- Lotes de demonstração: nunca altero nem apago o histórico de um lote antigo;
  se já existir um lote demo realmente aberto, não crio outro; se todos os lotes
  demo estiverem encerrados, crio um novo com horários relativos ao momento
  atual.
- Marco os lotes de seed de forma explícita para distingui-los dos criados pelo
  usuário.
- O seed não consulta a API externa. Usa fixtures versionadas.

Assim, um cold start do Render não duplica usuários nem modifica lotes já
utilizados, mas garante que o avaliador encontre ao menos um fluxo demonstrável.

**Descartei:** não registrei alternativa para esta decisão.

### AD-25. WebSocket com SQLAlchemy síncrono
**Decidi** que o endpoint WebSocket é assíncrono, mas o SQLAlchemy permanece
síncrono. Nenhuma operação bloqueante de banco roda diretamente no event loop.

Para o snapshot ou outra leitura necessária pelo WebSocket: executo a operação
síncrona em threadpool, abro uma `Session` curta dentro dela e a fecho ao
terminar. Depois do snapshot, o WebSocket recebe atualizações de um connection
manager/broadcaster em memória.

Uma operação de domínio segue esta ordem: executa a transação; o commit é
confirmado; só então publica o evento no broadcaster. **Nunca publico evento
antes do commit.**

Se o processo morrer entre o commit e a publicação, não implemento outbox agora.
A reconexão com snapshot restaura o estado correto. Registro essa limitação no
README.

**Descartei:** outbox agora.

### AD-26. Hora injetável
**Decidi** que a regra de domínio não consulta o relógio diretamente. A camada
de aplicação: inicia a transação; adquire a trava; consulta `clock_timestamp()`
no PostgreSQL; recebe um `datetime`; e passa esse "agora" explicitamente para a
função/regra de domínio.

Nos testes unitários, passo um `datetime` fixo. Nos testes de integração, haverá
pelo menos testes usando o caminho real com `clock_timestamp()` do PostgreSQL,
especialmente: limite dos 2 minutos; lance depois do fim; fechamento.

**Descartei:** não registrei alternativa para esta decisão.

### AD-27. `verify` e testes
**Decidi** que o comando `verify` executa todas as verificações abaixo e falha
imediatamente se qualquer uma falhar.

- **Back-end:** `pytest`; Ruff para lint; `ruff format --check`; testes de
  integração críticos em PostgreSQL real.
- **Front-end:** ESLint; checagem de tipos do TypeScript (`tsc --noEmit`, ou
  equivalente adequado ao projeto); testes automatizados existentes; build de
  produção do Vite.

Para PostgreSQL real nos testes, uso Docker/Compose com um banco dedicado de
teste, isolado do desenvolvimento. Os testes nunca usam SQLite para representar
comportamento transacional do PostgreSQL.

**Descartei:** SQLite para representar comportamento transacional.

### AD-28. Monorepo, uv e Dockerfile multi-stage
**Decidi** usar monorepo:

```
/
  backend/
  frontend/
  docs/
  _bmad-output/
  CLAUDE.md
  Dockerfile
```

- **Back-end Python:** `pyproject.toml`; `uv` como gerenciador de dependências;
  Python em versão estável definida no projeto.
- **Front-end:** React; Vite; TypeScript simples e explicável (AD-4).
- **Deploy:** Dockerfile multi-stage. Primeiro estágio: instala as dependências
  do front-end e executa o build do Vite. Segundo estágio: prepara o ambiente
  Python, instala o back-end, copia o `dist` produzido pelo front-end. O FastAPI
  serve a API e a SPA na mesma origem.
- Não armazeno estado persistente no filesystem do contêiner.

**Descartei:** não registrei alternativa para esta decisão.

### AD-29. JWT, cookie e CSRF
**Decidi:**
- **JWT:** duração de 8 horas.
- **Cookie em produção:** `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem
  atributo `Domain`. Quando possível, uso o prefixo `__Host-` no nome.
- **Cookie em desenvolvimento (localhost):** `HttpOnly`, `Secure=false`,
  `SameSite=Lax`.
- **Logout:** apaga o cookie. Declaro no README a limitação de que um token
  previamente copiado continua válido até o `exp`.
- **CSRF:** `SameSite` não é a única proteção. Para operações que alteram estado:
  GET/HEAD/OPTIONS nunca alteram estado (inclui o handshake do WebSocket e
  qualquer leitura; nenhuma leitura liquida lote, AD-19); as requisições usam JSON; valido o
  `Origin` contra a origem configurada; quando o `Origin` não estiver
  disponível, no caso suportado, valido o `Referer`; rejeito origem diferente.
- Não habilito CORS permissivo.

**Descartei:** não registrei alternativa para esta decisão.

### AD-30. Idioma dos identificadores: inglês
**Decidi** padronizar inglês para código, banco e API.

- **Tabelas e colunas (exemplos):** `users`, `wallets`, `lots`, `bids`,
  `receipts`, `user_id`, `lot_id`, `total_balance_cents`,
  `committed_balance_cents`, `starts_at`, `ends_at`.
- **Rotas:** `/api/lots`, `/api/lots/{lot_id}`, `/api/lots/{lot_id}/bids`,
  `/api/lots/{lot_id}/audit`, `/api/wallet`, `/api/me/wins`.
- A interface e todas as mensagens exibidas ao usuário permanecem em português.
- Não misturo português e inglês dentro do domínio técnico.

**Descartei:** misturar português e inglês no domínio técnico.

## Revisão final: contradições

**Não há mais contradição material.** Os três bloqueadores foram fechados:

- **B1 (resolvido):** TypeScript. O AD-4 permanece vinculante, o AD-28 e o AD-27
  foram corrigidos e JavaScript puro permanece como alternativa descartada.
- **B2 (resolvido):** GET, HEAD e OPTIONS nunca alteram estado. O catch-up do
  AD-19 saiu das leituras e ficou na inicialização, no scheduler e em operações
  que já alteram estado. Alternativa descartada: liquidar em GET.
- **B3 (resolvido):** papéis técnicos `AUCTIONEER` e `BIDDER`.

Cruzamentos conferidos depois do fechamento: AD-19 com AD-29 (coerentes: nenhuma
leitura altera estado); AD-19 com AD-9 e AD-25 (o evento só sai depois do commit
de quem de fato fechou); AD-11 com AD-30 (papéis em inglês); AD-4, AD-27 e AD-28
(TypeScript em toda a toolchain); AD-7 com AD-8 (líder anterior lido depois da
trava do lote); AD-6 com AD-26 (hora do banco entra como parâmetro).

## Questões para a implementação (não mudam a arquitetura)

1. **Intervalos.** Intervalo do scheduler (AD-19), intervalo do heartbeat e tempo
   limite para conexões sem heartbeat (AD-10). O navegador não reconecta
   WebSocket sozinho: o cliente precisa de reconexão com espera crescente.
2. **Origin no WebSocket.** O stream é público, mas o handshake valida `Origin`?
   **Resolvida na Story 4.1 (27/10/2026):** decidi que o handshake de `/ws/lots/{lot_id}`
   valida `Origin` contra a `APP_ORIGIN` quando o cabeçalho existe (esquema, host e porta
   normalizada; diferente, malformado, `null` ou repetido é recusado antes do `accept`) e
   aceita a ausência dele (cliente que não é navegador). Descartei exigir `Origin` sempre
   e não validar nada; detalhes no AD-10 e na D7 da story.
3. **`bidder_alias` na linha do lance.** O pseudônimo entra no hash (AD-21):
   persisto o alias em cada lance ou o recalculo na auditoria com o
   `PSEUDONYM_SECRET`? Recalcular faz a rotação do segredo quebrar a verificação.
   **Resolvida na Story 3.3 (26/10/2026):** persisto o alias em cada lance; a
   auditoria nunca o recalcula; sem tabela de mapeamento; rotação transparente não
   suportada (refinamento no AD-20).
4. **Ordem na inicialização.** O catch-up de fechamento (AD-19) roda antes do
   seed (AD-24) e antes de atender tráfego normal, e "lote demo realmente aberto"
   significa estado aberto e `ends_at` maior que o `clock_timestamp()`. Se o seed
   criar lances, eles passam pelo serviço de domínio, para a cadeia e a âncora
   saírem válidas. Verificar no primeiro deploy se o catch-up não atrapalha a
   inicialização do Render.
   **Resolvida em parte na Story 2.4 (24/10/2026):** decidi que o lote demo
   realmente aberto é `is_demo` e `ends_at > clock_timestamp()`, lido depois de
   `pg_advisory_xact_lock`, que serializa dois seeds simultâneos; a ordem continua
   migrations → seed → servidor (`start.sh`). O catch-up de fechamento da 4.4 entra
   **antes** do seed, e a 3.6 acrescenta "e não cancelado" ao predicado. Um demo
   vencido e ainda não liquidado conta como encerrado (o seed cria outro).
   **Story 3.4 (26/10/2026):** o predicado ganha "e autenticado" (`anchor_hmac IS
   NOT NULL`): um demo anterior à 3.4, sem âncora, não conta como aberto, e o seed
   cria um demo novo já assinado, sem tornar o antigo confiável.
   Descartei `SELECT ... FOR UPDATE` (não há linha para travar), a trava de sessão e
   `pg_try_advisory_lock` com desistência. Continua aberto: o catch-up em si (4.4) e
   a verificação no primeiro deploy com ele.
5. **Limite exato dos 2 minutos.** O AD-26 pede esse limite nos testes de
   integração com o relógio real, mas o instante exato só é reproduzível com
   `now` injetado. Defino: limite exato em teste com `now` fixo; caminho real com
   margens.
6. **Evento de encerramento.** Só quem de fato fechou o lote publica o evento; a
   execução idempotente que não fez nada não publica.
7. **Smoke test.** O item "API indisponível" (AD-23) não é verificável contra a
   API real; precisa de falha simulada.
   **Resolvida na Story 2.3 (24/10/2026):** o smoke test da AIC é o script manual
   `backend/scripts/smoke_artic.py` (`cd backend && uv run python -m
   scripts.smoke_artic`), fora do `verify`; a indisponibilidade é a falha
   controlada e determinística do mesmo cliente apontado para `127.0.0.1:9`
   (conexão recusada); timeout fica coberto pelos testes com transporte falso;
   descartei rodar o smoke como `pytest -m smoke` e deixar a indisponibilidade só
   nos testes com transporte falso. Detalhes na story 2.3.
8. **Estado transitório nas leituras.** Nome do valor e do campo que representa
   "Encerrado, apurando resultado", e como a leitura o calcula sem alterar estado
   e sem travar o lote (com a hora do banco, coerente com o AD-6).
   **Resolvida na Story 2.5 (25/10/2026):** a leitura expõe só `phase`
   (`scheduled`, `live` ou `ended`), calculada no servidor com um `clock_timestamp()`
   avaliado uma vez por leitura, no mesmo statement que lê os lotes (CTE `MATERIALIZED` e
   `LEFT OUTER JOIN`, para `as_of` e linhas pertencerem ao mesmo snapshot), sem trava e
   sem escrita. Para `ended`, a interface mostra "Encerrado, apurando resultado". Não
   criei `settlement_status` nem coluna de estado: a Story 4.3 acrescenta um segundo eixo
   real quando a liquidação existir. Descartei `settlement_status = pending` sempre, um
   campo único com `closing`/`closed` e duas consultas independentes em `READ COMMITTED`
   (snapshots diferentes). Detalhes em
   `_bmad-output/implementation-artifacts/2-5-vitrine-pública-e-página-do-lote.md`.
9. **Tentativa de lance em lote vencido.** Ordem dentro da requisição: executar o
   fechamento (transação própria) e só então devolver "lote encerrado".
10. **Nomes ainda não definidos.** Rota do WebSocket da sala; rotas do comprovante
    e do link compartilhável; nome do segredo do JWT; ferramenta de teste do
    front-end.
    **Resolvidos na Story 1.2 (23/10/2026):** decidi `compose.yaml` na raiz do
    repositório; Python 3.13; PostgreSQL 18 em dev, teste e produção (padrão do
    Render para bancos novos; descartei 17 e 16); variáveis de banco
    `DATABASE_URL` e `TEST_DATABASE_URL`. Detalhes e alternativas descartadas em
    `_bmad-output/implementation-artifacts/1-2-postgresql-com-bancos-isolados-e-migrations.md`.
    **Resolvidos na Story 2.2 (24/10/2026):** o segredo do JWT é `JWT_SECRET`
    (obrigatório, no mínimo 32 caracteres, só em variável de ambiente; descartei
    deixá-lo opcional); as rotas de autenticação são `POST /api/auth/login`,
    `POST /api/auth/logout` e `GET /api/me` (descartei `/api/session` e
    `/api/login`). Continuam abertos: a rota do WebSocket da sala, as rotas do
    comprovante e do link compartilhável e a ferramenta de teste do front-end.
    Detalhes e alternativas descartadas em
    `_bmad-output/implementation-artifacts/2-2-login-papéis-e-política-de-acesso.md`.
    **Resolvido em parte na Story 2.4 (24/10/2026), ferramenta de teste do
    front-end:** decidi `node:test` nativo do Node 24, com `npm test` como etapa do
    `verify`, só para lógica pura sem DOM (hoje, o dinheiro em `money.ts`, os
    horários em `lotTime.ts` e a checagem do rascunho do lote em `lotDraft.ts`). Descartei Vitest com Testing Library: dependência nova para um
    arquivo pequeno. Componentes seguem sem teste automatizado. Continuam abertos: a
    rota do WebSocket da sala e as rotas do comprovante e do link compartilhável.
    **Atualização na Story 2.5 (25/10/2026), testes de navegador:** o `verify` padrão
    continua sendo o do AD-27 (`pytest`, Ruff, `ruff format --check`, integração em
    PostgreSQL real; ESLint, `tsc --noEmit` — que inclui os `tsconfig` do app, do Node e
    de `e2e/` —, `node --test`, build do Vite e `docker build`). Depois do teste manual
    da 2.5 adicionei o **Playwright** (`@playwright/test`, só Chromium, API simulada por
    interceptação de rede) como **camada adicional de navegador**, em `frontend/e2e/`
    (`npm run test:e2e`). Ele **não roda no `verify` padrão**: é opt-in com
    `VERIFY_E2E=1 ./verify.sh`, porque exige o Chromium instalado (`npx playwright
    install chromium`, ~100 MB) e não quero um browser como pré-requisito silencioso do
    `verify` básico. Os 5 testes de `real-stack.spec.ts` (FastAPI real + build + banco de
    teste) ficam ainda mais à parte: só rodam com `E2E_REAL_BASE_URL` e não fazem parte
    nem do `verify` padrão nem do `VERIFY_E2E=1`. Descartei incluir o Playwright sempre
    (quebraria o `verify` de quem não baixou o browser) e rodá-lo só em CI. O AD-27
    não foi alterado: "testes automatizados existentes" continua valendo; o Playwright é
    um acréscimo opcional, não uma etapa obrigatória.
    **Resolvido em parte na Story 4.1 (27/10/2026), rota do WebSocket da sala:** decidi
    `/ws/lots/{lot_id}`, na mesma origem (`ws` em desenvolvimento, `wss` em HTTPS), com
    política pública e `Origin` conforme a Q2; descartei `/api/lots/{lot_id}/ws`. O
    prefixo `/ws` é reservado no fallback da SPA. Continuam abertos: as rotas do
    comprovante e do link compartilhável.

## Pontos de atenção (consequências, não decisões)

- **Banco gratuito do Render:** pela documentação que li na pesquisa desta
  conversa, o PostgreSQL gratuito expira 30 dias após a criação, com 14 dias de
  carência antes de ser apagado. Um banco criado no primeiro deploy (por volta de
  24/10) expiraria por volta de 23/11. Confirmar na documentação atual e comparar
  com a data provável da avaliação.
- **Horas gratuitas:** a mesma documentação fala em 750 horas gratuitas por mês
  por workspace, consumidas enquanto um serviço gratuito está rodando. Com o
  heartbeat mantendo o serviço acordado, um único serviço 24 horas por dia usa
  cerca de 744 horas. Outro serviço gratuito no mesmo workspace soma horas.
- **Liquidação tardia:** com o serviço dormindo, o fechamento só acontece na
  inicialização seguinte (cold start), pelo scheduler ou numa tentativa de lance.
  Até lá, as leituras mostram "Encerrado, apurando resultado". Declarar no
  README.
- **Limitação commit/publicação (AD-25):** declarar no README.
- **Logout (AD-29):** sem sessão no banco, o token copiado vale até expirar.
- **Anti-sniping (AD-5):** sem teto de renovações. Declarar no README.
- **CHECK × liquidação (AD-3 e AD-9):** a CHECK é verificada a cada UPDATE;
  debitar o total e liberar o comprometido precisam ocorrer sem estado
  intermediário inválido.
- **Imagem (AD-22):** a mídia externa pode falhar sem derrubar a aplicação.
  Declarar no README.

## Histórico de alterações

- Story 3.4, consolidação (26/10/2026): AD-7 refinado (18 passos; autenticação do
  estado anterior depois da hora e antes das regras); AD-13 refinado (gate, vínculo
  operacional do líder e do lance atual, âncora na criação, lote legado não
  autenticado, regras dos segredos, limitação); AD-20 refinado (alias de 16 hex
  persistido, rotação não suportada); Questão 3 marcada como resolvida na 3.3;
  Questão 4 com o predicado do demo autenticado. Nenhuma decisão revertida.

- Story 2.5, testes de navegador (25/10/2026): Questão 10 atualizada (ferramenta de teste
  do front-end). `node --test` segue no `verify` padrão para lógica pura; o Playwright
  entrou como camada de navegador **opt-in** (`VERIFY_E2E=1 ./verify.sh`), fora do
  `verify` padrão. Nenhuma AD alterada; o AD-27 permanece como está.

- Story 2.5, identidade ÁTRIO (25/10/2026): o produto passou a se chamar ÁTRIO — Leilões de
  Arte (adendo sob a AD-15). Nenhuma AD alterada.

- Story 2.5 (25/10/2026): Questão 8 resolvida (só `phase`; leitura em um statement com a
  hora do banco; "Encerrado, apurando resultado" como texto de interface). Nenhuma AD
  alterada; o AD-22 segue intacto (a P9 manteve o proxy de imagem da 2.3). As decisões da
  story (P1 a P9 e D1 a D20) ficam em
  `_bmad-output/implementation-artifacts/2-5-vitrine-pública-e-página-do-lote.md`.

- Story 2.4 (24/10/2026): Questão 4 resolvida em parte (demo realmente aberto, trava
  consultiva, ordem na inicialização) e Questão 10 resolvida em parte (ferramenta de
  teste do front-end para lógica pura). Nenhuma AD alterada. As decisões da story
  (P1 a P9, D1 a D14, Q1 e A2 a A4) ficam em
  `_bmad-output/implementation-artifacts/2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado.md`.

- AD-22: consequência técnica revisada na Story 2.3 (24/10/2026). O hotlink direto do
  navegador deu 403 (Cloudflare) no teste manual; passo a servir a imagem por proxy
  same-origin controlado, sem armazenar bytes. Motivação original mantida.

- Questão 7 resolvida na Story 2.3. Nenhuma AD alterada.

- Questão 10: segredo do JWT (`JWT_SECRET`) e rotas de autenticação
  (`/api/auth/login`, `/api/auth/logout`, `/api/me`) resolvidos na Story 2.2.
  Nenhuma AD alterada.

- Questão 10: local do Compose, versão do Python, versão do PostgreSQL e nomes
  das variáveis de banco resolvidos na Story 1.2. Nenhuma AD alterada.

- Fechamento dos bloqueadores: B1 (TypeScript confirmado), B2 (leituras nunca
  liquidam; AD-19 reescrito), B3 (papéis `AUCTIONEER` e `BIDDER`). Fase marcada
  como ARQUITETURA CONCLUÍDA.
- AD-27: `tsc --noEmit` incluído no `verify` do front-end.
- AD-28: referência a JavaScript corrigida para TypeScript.
- AD-19: alternativa descartada acrescentada (liquidar em GET).

- AD-10: reaberta. SSE substituído por WebSocket, com heartbeat do cliente.
- AD-1, AD-2, AD-4, AD-14: referências a SSE trocadas por WebSocket.
- AD-3: nomes em português substituídos por nomes em inglês com sufixo `_cents`.
- AD-6, AD-8, AD-9, AD-11, AD-13, AD-15, AD-16: motivos acrescentados.
- AD-16: acrescentada a alternativa descartada.
- AD-12: "priorizando domínio público" substituído por filtro obrigatório (AD-23).
- AD-19 a AD-30: novos, a partir das respostas às antigas Q1 a Q12.
- Segredos nomeados: `AUDIT_HMAC_SECRET` e `PSEUDONYM_SECRET`.
- Nomes técnicos em português (`fim_em`, `lote_id`) substituídos por `ends_at`,
  `lot_id`.
