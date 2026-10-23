# Registro de arquitetura: Casa de Leilões

Fase: **ARQUITETURA CONCLUÍDA**. Nenhum bloqueador aberto. As questões que
restam são de implementação e não mudam a arquitetura. Nenhuma linha de código
de aplicação foi escrita.

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
| AD-5 | Anti-sniping: extensão cumulativa do fim atual (+2 min por lance em `0 < restante <= 2 min`) | `fim = momento do lance + 2 min` | O fim pode subir sem teto enquanto houver lances na janela; documentar no README |
| AD-6 | Autoridade de hora: PostgreSQL, `clock_timestamp()` lido depois da trava do lote | Relógio do navegador; relógio da aplicação; hora lida antes da trava | Um único instante por operação |
| AD-7 | Lance = uma única transação (16 passos) | Etapas como operações ou commits independentes, ou só validação na aplicação | Falha em qualquer passo desfaz tudo |
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
| AD-22 | Imagem: não armazenar bytes; guardar `image_id` e referência IIIF; carregar direto do IIIF; placeholder local se falhar | Baixar e armazenar os bytes | Só a imagem depende do museu; o resto não |
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

### AD-5. Anti-sniping: extensão cumulativa do horário final atual
O enunciado diz: "lance aceito nos últimos 2 minutos estende o fim do lote
para +2 minutos". A frase permite duas interpretações:

- A) novo fim = momento do lance + 2 minutos
- B) novo fim = horário final atual + 2 minutos

**Decidi** a opção B. Se um lance válido for aceito quando
`0 < tempo restante <= 2 minutos` (janela inclusiva), somo 2 minutos ao horário
final atual (`ends_at`) do lote.

**Exemplo:**
- fim atual 20:00; lance válido às 19:59; novo fim 20:02
- fim atual 20:02; lance válido às 20:01; novo fim 20:04
- e assim sucessivamente

Um lance recebido depois do encerramento nunca reabre o lote.

**Por quê:** escolhi a interpretação de extensão cumulativa do horário final.
Como o enunciado é ambíguo, a escolha fica documentada aqui e no README, em
"Comportamentos que podem surpreender".

**Descartei:** `novo fim = momento_do_lance + 2 minutos`.

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
2. bloquear o lote;
3. capturar o horário atual do banco (AD-6);
4. validar estado e período;
5. validar o lance mínimo;
6. impedir o líder atual de cobrir o próprio lance;
7. identificar as carteiras envolvidas;
8. adquirir as travas necessárias (AD-8);
9. validar o saldo disponível;
10. liberar o saldo comprometido do líder anterior;
11. comprometer o saldo do novo líder;
12. atualizar o líder e o lance atual;
13. aplicar o anti-sniping (AD-5), se necessário;
14. registrar o lance;
15. registrar os dados da auditoria (AD-13);
16. confirmar a transação.

Nenhuma dessas operações pode ficar parcialmente aplicada.

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
**Decidi** não baixar nem armazenar os bytes das imagens. Persisto `image_id`, a
URL/referência IIIF necessária e os metadados/atribuição necessários. O
front-end carrega a imagem diretamente do IIIF do Art Institute.

Se a imagem externa falhar, mostro um placeholder local e mantenho título,
artista, valores, lance, histórico e demais funções funcionando. A aplicação não
depende da API externa para seus dados de negócio. A disponibilidade da mídia
externa pode afetar a imagem, mas nunca torna a vitrine ou a sala inutilizável.
Documento essa distinção no README.

**Descartei:** baixar e armazenar os bytes das imagens.

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
3. **`bidder_alias` na linha do lance.** O pseudônimo entra no hash (AD-21):
   persisto o alias em cada lance ou o recalculo na auditoria com o
   `PSEUDONYM_SECRET`? Recalcular faz a rotação do segredo quebrar a verificação.
4. **Ordem na inicialização.** O catch-up de fechamento (AD-19) roda antes do
   seed (AD-24) e antes de atender tráfego normal, e "lote demo realmente aberto"
   significa estado aberto e `ends_at` maior que o `clock_timestamp()`. Se o seed
   criar lances, eles passam pelo serviço de domínio, para a cadeia e a âncora
   saírem válidas. Verificar no primeiro deploy se o catch-up não atrapalha a
   inicialização do Render.
5. **Limite exato dos 2 minutos.** O AD-26 pede esse limite nos testes de
   integração com o relógio real, mas o instante exato só é reproduzível com
   `now` injetado. Defino: limite exato em teste com `now` fixo; caminho real com
   margens.
6. **Evento de encerramento.** Só quem de fato fechou o lote publica o evento; a
   execução idempotente que não fez nada não publica.
7. **Smoke test.** O item "API indisponível" (AD-23) não é verificável contra a
   API real; precisa de falha simulada.
8. **Estado transitório nas leituras.** Nome do valor e do campo que representa
   "Encerrado, apurando resultado", e como a leitura o calcula sem alterar estado
   e sem travar o lote (com a hora do banco, coerente com o AD-6).
9. **Tentativa de lance em lote vencido.** Ordem dentro da requisição: executar o
   fechamento (transação própria) e só então devolver "lote encerrado".
10. **Nomes ainda não definidos.** Rota do WebSocket da sala; rotas do comprovante
    e do link compartilhável; nome do segredo do JWT; ferramenta de teste do
    front-end; local do `docker-compose`; versão do Python; versão principal do
    PostgreSQL (alinhar a do contêiner de dev/teste com a oferecida pelo Render).

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
- **Anti-sniping (AD-5):** sem teto de extensões. Declarar no README.
- **CHECK × liquidação (AD-3 e AD-9):** a CHECK é verificada a cada UPDATE;
  debitar o total e liberar o comprometido precisam ocorrer sem estado
  intermediário inválido.
- **Imagem (AD-22):** a mídia externa pode falhar sem derrubar a aplicação.
  Declarar no README.

## Histórico de alterações

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
