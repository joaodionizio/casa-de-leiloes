---
title: 'Story 6.4 — Validação final no ambiente publicado'
type: chore
created: '2026-10-29'
status: done
route: dispatch
story_key: 6-4-validação-final-no-ambiente-publicado
context: []
---

# Story 6.4 — Validação final no ambiente publicado

> **Estado vigente em 29/10/2026: done. R6.4-01 — RESOLVED EM PRODUÇÃO.**
> Revalidação focal final às 11:47 America/Maceio, registrada ao final desta
> story e em [FECHAMENTO-EPICO-6.md](../../docs/FECHAMENTO-EPICO-6.md).
> Os bloqueios e status anteriores abaixo são históricos, preservados.

<frozen-after-approval reason="escopo e execução autorizados no pedido explícito da Story 6.4">

## Intent

Validar como avaliador externo o candidato realmente publicado em
https://casa-de-leiloes-i1xr.onrender.com, executando o roteiro completo do
README por HTTPS, UI, REST e WebSocket. Registrar evidências reais e o estado
final do Épico 6, sem implementar opcionais ou corrigir produto nesta sessão.

## Boundaries & Constraints

Somente interfaces públicas normais. Não ler `.env*`, credenciais ou segredos;
não imprimir/armazenar senha descartável, cookie, JWT ou identidade real dos
licitantes. Não acessar banco/SQL de produção nem adulterar auditoria. Cadastro
sintético example.com, lote legítimo, depósitos e lances simulados estão
explicitamente autorizados. Não fazer carga, mudar relógio, proxy, DNS, derrubar
serviço, commit, push, merge ou deploy. Não modificar README silenciosamente:
avaliá-lo e registrar incorreções. Não iniciar 6.5–6.7. Preservar R6.2-01 LOW
aceito historicamente. Git somente leitura foi autorizado; não é necessário
executá-lo novamente. Correspondência SHA/Render não deve ser presumida.

Se houver MEDIUM/HIGH/BLOCKER, reproduzir duas vezes quando seguro, documentar
ID, etapa, evidência, impacto e correção mínima; interromper conclusão e manter
épico in-progress. Limitações instrumentais não são defeitos inventados.

## I/O & Edge-Case Matrix

| Cenário | Entrada | Resultado esperado |
| --- | --- | --- |
| Infraestrutura | GET health, raiz, assets, API lotes | 200 e contratos reais |
| SPA | acesso direto/reload login, register, lote, painéis, wins, audit, receipt | HTML/JS funcionais, History API sem 404 indevido |
| CA2 | login HTTPS, metadados, GET me, logout | __Host-auction_session, HttpOnly/Secure/Lax/Path=/, sem Domain, aceito/enviado/removido |
| CORS/guardas | preflight estrangeiro; register com {} e Origin estrangeiro / mídia ausente / text/plain | sem CORS permissivo; 403 / 415 / 415 sem efeito |
| Demos | três contas README / senha pública Demo123! | autenticação, área e restrições por papel |
| Cadastro | dois e-mails sintéticos únicos example.com e senha descartável em memória | BIDDER/AUCTIONEER 201 via UI, validação, confirmação/login sem autologin, sessão após reload |
| Seed | vitrine ANTES de criar lote | ao menos um lote realmente aberto; ausência é finding importante |
| Criação | UI, busca AIC, obra pública, valores válidos e término futuro curto | sucesso e vitrine; identificar pelo ID sem adulterar título da obra |
| Snapshot AIC | lote existente e criado | dados essenciais locais; mídia pode ser externa; não provocar queda |
| Disputa | contextos separados, depósito moderado, primeiro lance e superior | saldo/reserva/histórico/posição coerentes e liberação do superado |
| WebSocket | sala dos dois participantes | conexão real same-origin e atualização sem reload |
| Reconnect | breve offline apenas no contexto cliente, se viável | reconexão e snapshot/reconciliação, sem reenvio de lance |
| Anti-sniping | um lance legítimo em 0 < restante <= 2 min | ends_at anterior + 120s; registrar antes/agora/depois; se inviável, declarar não exercitado |
| Settlement | aguardar fim sem banco/endpoint especial | resultado real publicado, vencedor/valor corretos e WS terminal; GET não aciona liquidação |
| Wins | vencedor e perdedor | participação coerente, comprovante só para vencedor |
| Receipt/audit | autenticado e visitante | obra/valor/data/pseudônimo/contagem/hash, cadeia e veredito íntegro; sem e-mail/nome/UUID real |
| Logout | UI e GET autenticado posterior | estado público e 401 sem alegar revogação JWT |
| README | roteiro como avaliador | fluxos reproduzíveis; registrar divergência documental real |

Cold start não deve ser reinduzido; logs de build/migration 0006→0007/seed/
catch-up/startup/Uvicorn/health/live/login 200/logout 204 são relato fornecido
pelo usuário, apenas complementar. Se settlement usar outro lote, declarar
fluxo dividido. Não alegar um E2E único sem observá-lo.

</frozen-after-approval>

## Code Map

- `README.md`: contas, rotas e roteiro de avaliação; leitura apenas.
- `frontend/src/`: formulários e contratos públicos, para orientar automação real.
- `backend/app/`: contratos/políticas; leitura sem configurações secretas.
- `6-1-revisão-de-segurança-e-de-erros.md`, `6-2a-cadastro-de-usuarios.md`,
  `6-3-readme-completo-e-registro-de-uso-de-ia.md`: status condicionado à prova.
- `sprint-status.yaml`: épico e stories; opcionais continuam backlog/cortadas.
- `code-review-epic-6.md`: agregado/re-review local aprovado, leitura apenas.
- `../../docs/uso_de_ia.md`: registrar esta execução sem apagar histórico.

## Tasks & Acceptance

- [x] Este artefato: executar matriz e registrar resultado de cada etapa, horários
  America/Maceio, HTTP, limitações, dados sintéticos anonimizados e findings.
- [x] `../../docs/uso_de_ia.md`: acrescentar métodos, resultados e limites reais.
- [x] Stories 6.1/6.2A/6.3 e `sprint-status.yaml`: sincronizar apenas se aprovado;
  6.2 mantém done, 6.5–6.7 backlog explicitamente cortadas.

**Critérios de aceite:** Dado o candidato publicado, quando o roteiro é
executado, então há evidência pública de segurança e fluxo completo. Dado um
defeito impeditivo ou uma prova obrigatória ausente, quando o relatório é
fechado, então a limitação/finding fica explícita e o épico não recebe done.
Dado sucesso sem BLOCKER/HIGH/MEDIUM, quando o registro é concluído, então
6.1/6.2/6.2A/6.3/6.4 e Épico 6 ficam done sem fingir execução de opcionais.

## Implementation Notes

Escopo detalhado fornecido pelo usuário e execução já autorizada. Sem nova
aprovação intermediária por ser a execução concreta do roteiro solicitado.
Árvore inicialmente limpa. Git read-only confirmou main e candidato local
`9f6d7a6316387927e57b8111caacfca36df2d993` (último título: docs: registra revisão
agregada do épico 6). Merge/deploy relatados pelo usuário; SHA do Render não
autenticado. GET /health real respondeu 200 e {"status":"ok"} nesta sessão.
Navegador integrado não conectou (ponte nativa indisponível); alternativa
Playwright instalada em `frontend/node_modules/playwright`, Chromium no cache
local. Rede do sandbox não resolve host; acesso público autorizado com execução
escalada funcionou. Scripts temporários podem ficar em /private/tmp, sem
storageState/cookies/JWT/senha em disco, sem tracing/HAR ou captura de headers
crus. Baseline documental mantido na área runtime local da skill, fora da story.

## Verification

Automação de navegador real e REST/WS públicos, sem interceptar APIs de produto.
Não repetir verify integral local: produto não será modificado. Conferir
documentos alterados com comparação sem Git, links e ausência de segredos.

## Execução publicada — 29/10/2026

**Veredito: fechamento interrompido por R6.4-01 MEDIUM.** O fluxo principal
publicado foi observado no mesmo lote desde criação pela UI até liquidação,
Meus arremates, comprovante e auditoria. A vitrine continua afirmando apuração
para lotes comprovadamente liquidados. Nenhuma correção de produto foi feita.
6.4 e Épico 6 permanecem `in-progress`; 6.1/6.2A/6.3 permanecem `review`,
6.2 permanece `done` com R6.2-01 LOW aceito, e 6.5–6.7 continuam backlog/cortadas.
A condição para promover stories/épico não foi satisfeita.

Todos os horários abaixo são **America/Maceio (UTC−03:00)**. Alvo único:
`https://casa-de-leiloes-i1xr.onrender.com`. `context: []` foi conferido antes
da execução; não havia arquivos adicionais indicados no frontmatter.

### Método e limites de atribuição

Usei Chromium real via Playwright instalado em `frontend/node_modules/playwright`,
em contextos isolados, UI sem interceptação e REST/WS públicos da mesma origem.
O navegador integrado foi tentado e a ponte nativa indisponível confirmou a
limitação instrumental; isso não foi tratado como defeito do produto. O comando
efetivo foi `node /private/tmp/atrio-64-public.cjs`, com rede escalada autorizada
e tarefas enviadas ao processo vivo. `init`, `guards`, `demos`, `register` e
`create` iniciaram o roteiro; comandos posteriores operaram os mesmos contextos.

Senhas descartáveis foram geradas em memória, nunca impressas ou gravadas.
Não houve storageState, tracing, HAR ou captura de cabeçalhos crus. Cookies/JWT
não foram registrados; apenas nome e flags do cookie. Os dois cadastros usaram
e-mails sintéticos únicos `example.com`, omitidos neste relatório. Os
licitantes são identificados exclusivamente pelos pseudônimos públicos do lote.
Não li `.env*`, credenciais privadas ou segredos; não acessei banco/SQL nem fiz
deploy ou mudanças de relógio/proxy/DNS. O agente de execução não usou Git;
a coordenação usou somente `git status`, `git branch --show-current`,
`git rev-parse HEAD` e `git log -1 --oneline`, autorizados para leitura e
identificação do candidato. Chromium foi encerrado.

A coleta sanitizada temporária está em
`/private/tmp/atrio64-evidence-public.json`: vitrine inicial, resposta de criação,
nove frames públicos WS (sem heartbeat), comprovante e auditoria. JSON válido,
10.555 bytes, sem chaves de e-mail/senha/identidade privada/sessão. Os resultados
de UI, flags e recusas foram observados na saída sanitizada do processo e
transcritos nesta matriz; não alego que o JSON contenha toda a saída da sessão.

Não autentiquei SHA do serviço Render nem correspondência com o candidato local
registrado acima. Os logs de migration/seed/catch-up/startup fornecidos pelo
usuário são relato complementar, não logs obtidos nesta execução. Não reinduzi
cold start, indisponibilidade da AIC ou falha de mídia. Não executei novamente
verify local: somente documentos foram alterados nesta sessão.

### Matriz executada

| Etapa / horário | Evidência real e resultado |
| --- | --- |
| Infraestrutura, 11:02:04 / 11:06:57 | Raiz, `/health` e `/api/lots` HTTP 200; health `{"status":"ok"}`. Assets `/assets/index-D-J4lFeo.js` e `/assets/index-D47oPc_N.css` HTTP 200, tipos JavaScript/CSS. UI carregou Vitrine. |
| Seed antes da criação, 11:02:04 | Dois lotes com `phase=live`: Fragments (`f6cd5376-5b89-4cb0-93d6-b275dfb11535`) e A Sunday on La Grande Jatte — 1884 (`4a1fa6d1-3924-4a33-b33a-127a21a6c4dc`); nenhum agendado e Judith encerrado. Não houve ausência de lote aberto. |
| CORS/guardas, 11:02:27–28 / 11:06:24 | OPTIONS estrangeiro em register HTTP 405; `Access-Control-Allow-Origin` e `Access-Control-Allow-Credentials` ausentes. POST `{}` com Origin estrangeiro: 403 `csrf_origin_mismatch`; Content-Type vazio/ausente efetivo e text/plain: 415 `unsupported_media_type`. Erros JSON sanitizados; nenhuma criação solicitada por esses corpos inválidos. Não consultei banco para afirmar efeitos internos. |
| Demos/papéis, 11:02:46–56 | As três contas públicas do README autenticaram pela UI (POST login 200, GET me 200/papel esperado). Leiloeiro viu Criar lote/Meus lotes; licitantes, Carteira/Meus arremates. Leiloeiro GET wallet/POST deposit: 403 `forbidden`; licitantes GET lots/mine/POST lots: 403 `forbidden`. |
| CA2 HTTPS, 11:02:46–56 / 11:07:35 | Cookie aceito e enviado pelo Chromium: `__Host-auction_session`, HttpOnly=true, Secure=true, SameSite=Lax, Path=/, host-only. Inspeção em memória do Set-Cookie confirmou **ausência de Domain**, sem exibir seu valor. GET me autenticado 200. CA2 público de cookie/Origin/CORS/login/logout aprovado, ressalvada a atribuição de SHA não autenticada. |
| Cadastro BIDDER, 11:03:07–13 | Formulário vazio exibiu validações de papel/e-mail/senha; envio preenchido pela UI retornou 201. Confirmação “Conta criada com sucesso. Entre para continuar.”, zero cookies, GET me 401 antes do login. Login 200 e sessão GET me 200 após reload. Carteira inicial zero comprovada às 11:04:15. |
| Cadastro AUCTIONEER, 11:03:15–22 | Mesma validação UI, cadastro 201, confirmação em login, zero cookies/me 401 antes de autenticar; login 200 e me 200 após reload. Não houve autologin nem confirmação por e-mail. |
| Busca AIC/criação, 11:03:41–46 | UI buscou Monet (200, 20 obras); detalhe Water Lilies, Claude Monet, 1906, AIC 16568, marcado domínio público. Revisão/publicação pela UI retornou POST lots 201; título original preservado. Inicial 10000/incremento 1000 centavos, início 11:03:45.526839, fim 11:06:00; confirmação “Lote criado” e vitrine pública incluíram o ID novo. |
| Snapshot essencial, 11:10:40 | GET público do lote existente de Seurat e do lote novo 200, com título/autoria/data/técnica/dimensões/external_id/source_url/image_url. A sala também exibiu a ficha completa. Isso comprova leitura real desses dados; não comprova operação durante indisponibilidade externa, que não foi provocada. Mídia continua via proxy da AIC. |
| Depósitos, 11:04:15–19 | Contexto 1 sintético: saldo inicial 0; depósito UI R$ 1.000 HTTP 200 → total 100000/comprometido 0/disponível 100000 centavos. Contexto 2 demo: inicial 167000/0/167000; depósito UI R$ 1.000 HTTP 200 → 267000/0/267000. Saldo demo prévio não foi zerado. |
| WS real, 11:04:17–20 | Ambos os navegadores abriram `wss://casa-de-leiloes-i1xr.onrender.com/ws/lots/98497701-51da-47ff-a6f2-8e3ece875511`; receberam room_snapshot e heartbeat/pong. UI confirmou sala conectada. |
| Primeiro lance/anti-sniping, 11:05:31 | GET de sala anterior: as_of 11:05:31.417426, fim 11:06:00, zero lances. POST UI R$ 100 HTTP 201, placed_at 11:05:31.717593, restante 28,282407 s; fim persistido 11:08:00, **anterior +120 s**, anti_sniping_applied=true. Reserva 10000/disponível 90000; UI “Você está ganhando”. Ambos WS receberam bid_accepted sem reload. |
| Recusas de negócio, 11:05:39 | Líder tentar 11000: 422 `already_winning`; outro licitante 10001: 422 `below_minimum`; outro 300000: 422 `insufficient_balance`. Não houve lance extra ou nova extensão. |
| Superação, 11:05:52–53 | Segundo lance UI R$ 110 HTTP 201, placed_at 11:05:52.256107; anti_sniping=false/fim 11:08, pois restavam 127,743893 s. Ambos WS atualizaram valor/histórico. Primeiro contexto ficou 100000/0/100000 e “Você foi superado”; segundo 267000/11000/256000 e “Você está ganhando”. |
| Reconexão, 11:06:09–18 | Offline somente no contexto 1 por 3 s fechou WS e mostrou “Sem conexão com a rede”. Online abriu novo WS; snapshot 11:06:12.938271 reconciliou os dois lances e fim 11:08. UI voltou conectada; histórico permaneceu com dois lances, sem reenvio. Contexto 2 continuou online. |
| SPA pública, 11:06:51–57 | Acesso direto e reload em login, register, lote novo, audit e receipt: HTML 200, títulos e conteúdo React corretos. Antes do settlement receipt exibia “Comprovante não encontrado”, coerente com ausência de resultado. |
| SPA privada, 11:07:19–24 / 11:08:58–11:09:01 | Acesso direto+reload 200 em Meus lotes, Criar lote, Carteira e Meus arremates. As capturas rápidas iniciais de Meus lotes/wins ainda mostravam carregamento; as verificações posteriores aguardaram dados e confirmaram os painéis completos. |
| Settlement autônomo, 11:08:01–02 | Não fiz leituras de lote entre 11:07:24 e o terminal. Ambos WS receberam espontaneamente lot_closed com settled_at 11:08:01.810386, sold, valor 11000, dois lances e vencedor público correto; sockets terminaram às 11:08:02 e salas mostraram “Encerrado”. Nenhum banco/endpoint especial ou GET disparou apuração. |
| Saldos/resultado, 11:08:20–21 / 11:09:01 | Perdedor 100000/0/100000; vencedor 256000/0/256000, débito de 11000 e reserva liberada. GET lots/mine 200 do leiloeiro: sold/11000/dois lances, total_received_cents 11000; UI “Vendido” e total recebido R$ 110. O crédito é observado no painel público normal do dono, sem acesso interno à carteira AUCTIONEER. |
| Wins vencedor/perdedor, 11:08:20–21 / 11:08:58–59 | REST 200: sintético result=not_won; demo 2 result=won, valor 11000/data/pseudônimo. UI do perdedor não tinha link Comprovante; UI do vencedor tinha um link Comprovante e Copiar link. Comprovante permanece público para quem possui a URL, como contratado. |
| Receipt/audit, 11:08:21 / 11:09:48–52 | REST 200 e UI 200 para autenticado e visitante: Water Lilies, R$ 110, data, pseudônimo, dois lances, sequência vencedora 2/hash final. Audit integrity=verified, UI “Integridade verificada”, histórico completo de dois lances. Respostas públicas sem e-mail/nome/UUID de pessoa; UUID do lote é público. |
| Cadeia independente, 11:10:21 | Recalculei SHA-256 dos dois JSONs canônicos v1 públicos; ambos current_hash e previous_hash conferiram, do genesis zero ao hash final. O HMAC secreto não foi acessado/recalculado: o veredito de âncora é a verificação pública do servidor. |
| Logout, 11:10:42–46 | UI Sair nos cinco contextos autenticados: POST 204, cookies 0, GET me 401 e estado público com Entrar. Não alego revogação de JWT copiado. |
| README / fechamento | Fluxo principal reproduzível até comprovante/audit no mesmo lote. Divergências e trechos não exercitados abaixo; README permaneceu intacto. Fechamento recusado por R6.4-01, sem novas mutações de produto após sua confirmação, exceto o logout previsto. |

### Lote observado do início ao fim

- ID público: `98497701-51da-47ff-a6f2-8e3ece875511` — **Water Lilies**.
- Primeiro pseudônimo: `Licitante-E50E5008CF19EECD`; vencedor:
  `Licitante-FC45A7951800596B`. Nenhuma identidade privada foi registrada.
- Início `2026-10-29T14:03:45.526839Z`; fim original
  `2026-10-29T14:06:00Z`; fim prorrogado `2026-10-29T14:08:00Z`;
  settlement `2026-10-29T14:08:01.810386Z`.
- Hash final:
  `5930c83674d431416dbef132e05c90d37cd853f70b99ac7f774c064c1cd4ba2e`.
- [Sala pública](https://casa-de-leiloes-i1xr.onrender.com/lots/98497701-51da-47ff-a6f2-8e3ece875511),
  [comprovante](https://casa-de-leiloes-i1xr.onrender.com/lots/98497701-51da-47ff-a6f2-8e3ece875511/receipt)
  e [auditoria](https://casa-de-leiloes-i1xr.onrender.com/lots/98497701-51da-47ff-a6f2-8e3ece875511/audit).

Judith foi apenas inspeção complementar de um lote anterior, **não substituto
do settlement observado no lote novo**. Sua sala/audit/receipt 200 às 11:06:23–24
confirmaram sold/133000 centavos/settled_at 10:54:06.141435, integrity=verified.
O rótulo “apurando” da vitrine não comprova falha do scheduler.

### Finding impeditivo

**R6.4-01 — MEDIUM — Vitrine afirma apuração para lotes já liquidados.**

- **Etapa:** Vitrine, seção Encerrados, após settlement real.
- **Reprodução 1:** 11:08:37, navegação direta `/`, HTTP 200. As linhas Water
  Lilies e Judith exibiram **“Encerrado, apurando resultado”**.
- **Reprodução 2:** 11:08:38, reload `/`, HTTP 200. Mesmos rótulos, sem mudança.
- **Contraprova pública:** WS lot_closed do Water Lilies às 11:08:01.810386,
  receipt/audit 200 às 11:08:21 e estado `settled`/`sold`/11000. Judith já tinha
  settlement às 10:54:06.141435 e voltou `settled` na sala 200 às 11:08:38.627687.
  Ambos os resultados estão disponíveis, mas a vitrine persiste em “apurando”.
- **Impacto:** informação pública de conclusão persistentemente incorreta,
  induzindo o avaliador/visitante a acreditar que o resultado não foi apurado.
  Não observei corrupção financeira, perda do resultado na sala ou comprovante
  indisponível. A classificação refere-se à apresentação terminal enganosa.
- **Causa corroborada por leitura:** `frontend/src/ClosedLotRow.tsx` passa apenas
  phase para LotState; `frontend/src/lotPhase.ts` traduz ended em “Encerrado,
  apurando resultado” incondicionalmente. O resumo público não contém settlement.
- **Correção mínima proposta, não executada:** usar na vitrine o rótulo neutro
  “Encerrado” quando o contrato não informa a apuração, preservando o texto
  “apurando” somente onde existe estado pending autoritativo. Revalidar os dois
  lotes liquidados após publicação da correção, sem alterar auditoria/banco.
- **Decisão:** aberto; impede `done` da 6.4/Épico 6 pela regra da spec. Não foi
  dispensado nem corrigido, e não altera o LOW histórico R6.2-01.

### README e provas não executadas

O README descreveu corretamente contas, cadastro, depósitos, lances, extensão,
liquidação, wins e contratos públicos observados. Permaneceram desatualizados
os trechos que dizem review agregado pendente e 6.4 não executada; a afirmação
histórica da última evidência de deploy 2+3 também não registra esta execução.
Isso foi registrado como divergência documental, sem editar silenciosamente o
README ou inventar SHA publicado. Uma atualização futura deve refletir o
fechamento **impedido**, não anunciar Épico 6 concluído.

Não criei segundo lote para demonstrar cancelamento do passo 3 do README nem
exercitei resultado sem lances. As recusas de carteira/depósito foram testadas
no leiloeiro demo, mas não no novo AUCTIONEER. A tentativa de lance pelo
leiloeiro não foi exercitada em nenhuma dessas contas; não alego essa prova
negativa publicada. Após confirmar o MEDIUM, finalizei apenas leituras, logout,
uma requisição inválida sem efeito para completar a prova de mídia e documentação.
Esses subcenários ficam **não exercitados**
nesta validação, sem atribuir falha ao produto. Não houve ensaio de carga,
adulteração de histórico, queda de serviço, manipulação de relógio, falha AIC
induzida ou novo aceite visual humano de todos os breakpoints. Reconexão e
anti-sniping foram realmente exercitados, não inferidos de testes locais.

### Verificação documental desta execução

A comparação sem Git com as cópias anteriores confirmou o preenchimento
desta story, o acréscimo cronológico em `docs/uso_de_ia.md` e a transição inicial
da 6.4 de backlog para in-progress em `sprint-status.yaml`. Frontmatter e bloco
congelado foram preservados; links relativos conferidos; ausência de valores de
senha/cookie/JWT e identidade privada conferida nos documentos e JSON público.
Stories 6.1/6.2A/6.3 e sprint não foram promovidos. Não repeti o gate executável
nem iniciei stories opcionais.

### Complemento obrigatório de mídia — 11:16:00 America/Maceio

A conferência do runner mostrou que a primeira prova usava Content-Type vazio.
Para distinguir isso da ausência real do cabeçalho, executei uma única requisição
inválida, sem campos capazes de criar usuário:

```sh
curl --max-time 30 -sS --request POST \
  --header 'Origin: https://casa-de-leiloes-i1xr.onrender.com' \
  --header 'Content-Type:' --data-binary '{}' \
  -w '\nHTTP %{http_code}\n' \
  https://casa-de-leiloes-i1xr.onrender.com/api/auth/register
```

O cabeçalho foi omitido por curl; resultado **415**, código
`unsupported_media_type`, envelope JSON conforme contrato. Portanto há provas
distintas de Content-Type vazio, ausente e text/plain. Não houve cadastro ou
novo efeito de negócio. A matriz anterior deve ser lida com esta distinção.

A inspeção estrutural de `backend/app/lots.py`, funções
`read_public_snapshot`, `read_public_lot_snapshot`, `public_lot_detail` e rotas
GET públicas, confirmou seleção dos campos persistidos de Lot, sem chamada AIC
nessas leituras. Isso complementa a leitura pública dos snapshots sem simular
indisponibilidade externa nem provar identidade criptográfica do build Render.

## Correção local de R6.4-01 — 29/10/2026

Encontrei R6.4-01 em produção na execução registrada acima. Confirmei que o
DTO público original não distinguia a existência de settlement: listagem e
detalhe classificavam `phase` pelos horários, enquanto a linha de encerrados
e seu nome acessível traduziam todo `ended` em “apurando resultado”. Isso
explica o texto incorreto mesmo com liquidação, comprovante e auditoria corretos.

Interrompi inicialmente a implementação por insuficiência do contrato, conforme
a instrução humana. Depois recebi autorização explícita para acrescentar somente
`settlement_status: pending|settled` ao resumo e ao detalhe público herdado.
Decidi usar a existência do `LotSettlement` persistido na mesma consulta; descartei
inferir por relógio/receipt/lances ou fazer requisições adicionais. A especificação
da correção está em [spec-r6-4-01-public-settlement.md](spec-r6-4-01-public-settlement.md).

O contrato aprovado da Vitrine é `ended+pending` → **Encerrado, apurando
resultado** e `ended+settled` → **Encerrado**, com o mesmo texto no nome
acessível. Live/scheduled e a exclusão de cancelados permanecem. Sala/QH-01
mantém seu contrato rico próprio; não altero settlement, scheduler, WebSocket,
regra financeira, Painel, Meus arremates, comprovante ou auditoria.

Backend e frontend precisam ser publicados juntos: o parser exige o novo campo,
sem fallback para backend antigo. O status não acrescenta dados pessoais,
vencedor, valores ou resultado ao resumo. GET continua leitura pura, sem locks,
com um statement e um relógio materializado por rota; não há N+1.

A evidência de produção acima é histórica, preservada da mesma sessão; não
executei novamente o fluxo publicado nesta correção. O registro temporário
permitiu restaurar esta story, ausente no workspace na retomada. A instrução
histórica de não repetir verify aplicava-se à fase exclusivamente documental;
a correção executável exige novo gate local.

### Verificação da correção

As regressões versionadas cobrem GETs reais para `ended+pending`, sold e
unsold persistidos; live/scheduled e cancelados; chaves exatas e privacidade;
status obrigatório no OpenAPI; leitura pura e um statement com relógio
materializado; ausência do campo/valores inválidos no parser; apresentação
visual/acessível e ausência de novas chamadas em 1440/375/320. As provas
anteriores de volume, responsividade e navegação foram preservadas.

Executei os focais na cópia permitida, sem dotenv/credenciais, com PostgreSQL
real exclusivo `atrio_r6401_test` no container isolado `atrio-r6401-postgres-1`.
Os comandos foram:

```sh
python3 -B /private/tmp/atrio-r6401/run.py backend tests/test_lot_phase.py tests/test_openapi.py tests/integration/test_public_lots.py -q
python3 -B /private/tmp/atrio-r6401/run.py node
python3 -B /private/tmp/atrio-r6401/run.py browser vitrine.spec.ts lot-room.spec.ts lot-room-ws.spec.ts layout.spec.ts --workers=2 --trace=off
python3 -B /private/tmp/atrio-r6401/run.py backend tests/integration/test_lot_cancellation.py -q
```

| Focal | Resultado real / exit |
| --- | --- |
| Lotes públicos, fases, DTO e OpenAPI | **98 passed**, 1 warning; 9.57 s / 0 |
| Node completo | **199 pass** / 0 |
| Vitrine, layout e Sala/WS | **136 passed**, 23.1 s / 0 |
| Cancelamento / propagação contratual | **38 passed**, 1 warning; 6.56 s / 0 |

Os 136 Playwright incluem Sala `ended+pending`, settled sold/unsold,
timer/WS/retry e a regressão R6-AGG-01. Não alterei a lógica ou o protocolo
da Sala. O primeiro focal de navegador terminou 133 passed/3 failed porque
a expectativa nova de Ao vivo omitira o marcador decorativo “●”; corrigi só
a asserção, repetindo os mesmos 136 testes com sucesso.

O primeiro gate completo encontrou uma asserção histórica em
`test_lot_cancellation.py` exigindo 17 campos no detalhe: **2412 passed,
1 failed, 1 warning**, 147.67 s, exit 1. Atualizei a expectativa para 18 campos
e acrescentei assert de status pending, sem afrouxar comportamento de
cancelamento. Executei o focal de 38 testes e iniciei novamente o gate integral.

As três camadas internas de revisão e a triagem estão na spec da correção.
Corrigi a propagação acima e acrescentei notas de substituição das restrições
históricas na SPEC/plano de testes 2.5. Não concedo aceite de produção a partir
da revisão ou dos testes locais.

### Gate local renovado — resultado final

Executei **`VERIFY_E2E=1 ./verify.sh`**, sem modificar o script, por
`python3 -B /private/tmp/atrio-r6401/run.py gate`. O wrapper define VERIFY_E2E=1
e executa `./verify.sh` na raiz da cópia com ambiente filtrado, sem dotenv ou
credenciais, usando Compose/porta e banco isolados. Conferi **256/256 hashes
SHA-256** das fontes permitidas no workspace/cópia, sem divergências. Nenhuma
fonte executável foi alterada após o gate verde.

| Etapa final | Resultado real |
| --- | --- |
| Ruff check / format --check | All checks passed; **111 files already formatted** |
| pytest / PostgreSQL real | **2413 passed**, 1 warning preexistente; **139.29 s** |
| ESLint / typecheck | Aprovados |
| Node completo | **199 pass**, 0 fail/cancelled/skipped |
| Vite | Build de produção aprovado |
| Playwright completo | **322 passed / 7 skipped**, **33.2 s** |
| Docker build | Aprovado |
| Gate | **exit 0**, `verify.sh: todas as etapas passaram.` / `VALIDATION_EXIT_CODE=0` |

Logs temporários: `backend-focal.log`, `browser-focal.log`,
`cancellation-focal.log`, `verify-first.log`, `verify-final.log` e
`manifest.json` em `/private/tmp/atrio-r6401/`. As regressões e as contagens
acima estão registradas no repositório. O único warning é a depreciação já
existente de TestClient/httpx; os sete skips são real-stack opt-in, não
provas de produção. Chromium usa API/WS simulados; backend usa PostgreSQL real.
Não houve screenshot pixel-perfect, novo aceite visual humano ou revalidação
publicada nesta correção. Parei somente o container isolado criado para os
testes, preservando o volume e sem manipular banco de desenvolvimento.

**R6.4-01 corrigido localmente — aguardando revalidação publicada.** Não marco
RESOLVED em produção. É necessário novo deploy coordenado backend/frontend e
revalidar a Vitrine publicada; o gate verde não fecha a Story 6.4 ou o Épico 6.

### Condição de fechamento preservada

**6.4 e Épico 6 permanecem in-progress.** Mantenho 6.1 em review, embora CA2
público já tenha sido evidenciado; 6.2 done; 6.2A e 6.3 tecnicamente revisadas,
sem promoção adicional; 6.5–6.7 cortadas/backlog. A correção precisa de novo
deploy coordenado e revalidação pública, incluindo os lotes já liquidados
Water Lilies e Judith. Não faço commit, push, merge ou deploy nesta correção.

### Arquivos desta correção

- [_bmad-output/implementation-artifacts/6-4-validação-final-no-ambiente-publicado.md](6-4-validação-final-no-ambiente-publicado.md)
- [_bmad-output/implementation-artifacts/spec-r6-4-01-public-settlement.md](spec-r6-4-01-public-settlement.md)
- [_bmad-output/implementation-artifacts/sprint-status.yaml](sprint-status.yaml)
- [_bmad-output/specs/spec-story-2-5-vitrine-publica/SPEC.md](../specs/spec-story-2-5-vitrine-publica/SPEC.md)
- [_bmad-output/specs/spec-story-2-5-vitrine-publica/public-lot-dtos.md](../specs/spec-story-2-5-vitrine-publica/public-lot-dtos.md)
- [_bmad-output/specs/spec-story-2-5-vitrine-publica/test-plan.md](../specs/spec-story-2-5-vitrine-publica/test-plan.md)
- [backend/app/lots.py](../../backend/app/lots.py)
- [backend/tests/integration/test_lot_cancellation.py](../../backend/tests/integration/test_lot_cancellation.py)
- [backend/tests/integration/test_public_lots.py](../../backend/tests/integration/test_public_lots.py)
- [backend/tests/lot_support.py](../../backend/tests/lot_support.py)
- [backend/tests/test_lot_phase.py](../../backend/tests/test_lot_phase.py)
- [backend/tests/test_openapi.py](../../backend/tests/test_openapi.py)
- [docs/uso_de_ia.md](../../docs/uso_de_ia.md)
- [frontend/e2e/support/mockApi.ts](../../frontend/e2e/support/mockApi.ts)
- [frontend/e2e/vitrine.spec.ts](../../frontend/e2e/vitrine.spec.ts)
- [frontend/src/ClosedLotRow.tsx](../../frontend/src/ClosedLotRow.tsx)
- [frontend/src/api/publicLots.test.ts](../../frontend/src/api/publicLots.test.ts)
- [frontend/src/api/publicLots.ts](../../frontend/src/api/publicLots.ts)
- [frontend/src/lotLabels.test.ts](../../frontend/src/lotLabels.test.ts)
- [frontend/src/lotLabels.ts](../../frontend/src/lotLabels.ts)
- [frontend/src/vitrine.test.ts](../../frontend/src/vitrine.test.ts)

A story foi restaurada da evidência anterior e a spec da correção foi criada;
esses são os dois arquivos ausentes da baseline capturada na retomada. Os
demais já tinham cópia anterior à edição. Não detectei nomes de arquivos de
segredo alterados na conferência do marcador; nenhum conteúdo secreto foi lido.
README permaneceu intacto, pois não descreve JSON exato que exigisse propagação.

## Revalidação publicada final e focal — 29/10/2026

**R6.4-01 — RESOLVED EM PRODUÇÃO. Story 6.4 e Épico 6: done.**
Autorização humana explícita para esta revalidação e o fechamento condicionado
à ausência de novo BLOCKER/HIGH/MEDIUM; condição satisfeita no recorte observado.
O veredito substitui a pendência de publicação da seção anterior. Não repeti o
E2E completo nem alterei código. Relatório final e gates rastreáveis:
[FECHAMENTO-EPICO-6.md](../../docs/FECHAMENTO-EPICO-6.md).

### Identidade do novo candidato

Alvo único: `https://casa-de-leiloes-i1xr.onrender.com`. Início da sessão
**29/10/2026 11:44:31 America/Maceio (UTC−03:00)**; coleta conclusiva
**11:47:10–11:47:57**, mesmo fuso. Git somente leitura confirmou `HEAD`, `main`
e referência local `origin/main` em
`7c285c38b5115198e5eac8da746edc764e28df9e`, commit da correção de 11:40:14.
Reflog registra fast-forward da main às 11:42:07 e `origin/main` atualizado
**by push às 11:42:16**. Não houve fetch: a referência remota viva não foi consultada.
Redeploy informado pelo usuário neste pedido; API nova e asset
`index-C6fGFWZt.js` corroboram publicação funcional da correção, diferente do
`index-D-J4lFeo.js` anterior. **Não autentiquei SHA, ID ou logs do deploy Render.**

### Matriz focal executada

| Prova / horário America/Maceio | Resultado observado |
| --- | --- |
| Health, 11:47:10 | GET `/health` **200**, `{"status":"ok"}` |
| Contrato público, 11:47:10 | GET `/api/lots` **200**, quatro lotes com campo obrigatório presente e valores apenas `pending`/`settled`; dez chaves públicas exatas. Dois live+pending, dois ended+settled; scheduled vazio. Nenhum campo privado novo |
| Detalhe, 11:47:10 | GET `/api/lots/98497701-51da-47ff-a6f2-8e3ece875511` **200**, 18 chaves previstas, resumo idêntico ao da listagem; `phase=ended`, `settlement_status=settled` |
| Vitrine, 11:47:12 | **Water Lilies** e **Judith** mostram **Encerrado**, sem “Encerrado, apurando resultado”; nomes acessíveis **Water Lilies. Encerrado.** e **Judith. Encerrado.**, conferidos por asserção de acessibilidade |
| Regressão visual desktop, 11:47:12 | 1440×1000, screenshot aberto e inspecionado, sem overflow; Fragments e Seurat **Ao vivo**; Próximos lotes **Nenhum lote agendado.**, coerente com API; raiz, JS e CSS **200**, tipos corretos |
| Sala, 11:47:13–19 | HTML e GET `/api/lots/{id}/bids` **200**; contrato rico próprio `ended+settled`, settlement preservado; QH-01 terminal **Encerrado**. Um bloco de status, zero timers, um GET bids da UI; um WS abriu e fechou após terminal, sem duplicação/reconexão durante 6 s |
| Comprovante, 11:47:20 | API e página pública **200**; **Arrematado**, Water Lilies, 11000 centavos, dois lances, mesmo hash final |
| Auditoria, 11:47:21 | API e página pública **200**, `integrity=verified`, UI **Integridade verificada**, `ended+settled`, mesmo hash do comprovante |
| JS/rede, 11:47:46–57 | Observação focal de 4 s por Vitrine/Sala: zero exceção JavaScript, falha de transporte ou escrita; HTTP >=400 somente `/api/me` **401 esperado para visitante**. Uma leitura de lotes e uma de bids por respectiva montagem, sem repetição evidente |
| OpenAPI público, 11:52:12 | GET `/api/openapi.json` **200**; `PublicLotSummary` e `PublicLotDetail` exigem `settlement_status` em **required**, enum exato `pending` / `settled` |

O lote principal é **o mesmo Water Lilies do E2E anterior**, ID
`98497701-51da-47ff-a6f2-8e3ece875511`; hash preservado
`5930c83674d431416dbef132e05c90d37cd853f70b99ac7f774c064c1cd4ba2e`.
Não repeti adulteração ou recálculo da cadeia. Sala mantém seu contrato próprio;
a corrida terminal-durante-retry de R6-AGG-01 não foi reinduzida em produção.

**Branch pending:** nenhum lote naturalmente `ended+pending` no momento da
coleta. Não criei condição artificial no banco nem aguardei transição. O branch
foi comprovado localmente pelos testes versionados e pelo gate final acima,
incluindo `frontend/e2e/vitrine.spec.ts` (pending/settled e nomes acessíveis em
1440/375/320), `frontend/src/lotLabels.test.ts` e
`backend/tests/integration/test_public_lots.py`. Ausência natural não é falha.
Sem lote agendado disponível, confirmei o estado vazio publicado; o rótulo de
um item Agendado permanece coberto localmente, sem alegar sua observação pública.

### Método, limites e fechamento

Skill de controle do navegador usada; ponte integrada indisponível. Fallback
Chromium real via Playwright instalado, contexto público, sem login/mock ou
interceptação; rede/navegador escalados aprovados automaticamente. Scripts e
evidências públicas sanitizadas em `/private/tmp/atrio64-final-*`, incluindo
JSON de resultados e screenshots Vitrine/Sala, inspecionados nesta sessão.
O relatório final preserva o essencial desses arquivos temporários.

O runner focal terminou **exit 1 somente na asserção genérica final de console**,
após todas as provas funcionais: contava os 401 esperados de `/api/me` como erro.
A observação específica posterior correlacionou os HTTP com os endpoints e
terminou **exit 0 / OBSERVATION_PASS**, sem exceções JS ou HTTP inesperado.
Tentativas prévias tiveram timeout de `networkidle` e seletor incorreto do CTA
do destaque; ajustei apenas o runner temporário. Nenhum finding de produto
derivou desses limites instrumentais; não apresento o runner inicial como verde.

**Findings novos: 0 BLOCKER / 0 HIGH / 0 MEDIUM.** Preservo **R6.2-01 LOW
aceito**, **R6-AGG-01/02 RESOLVED** e R6.1-01 resolvido. Promovo 6.1 a done
pela prova CA2 publicada anterior; 6.2 permanece done; 6.2A/6.3 done pelo agregado
aprovado e provas existentes; 6.4 done; Épico 6 done. 6.5–6.7 continuam cortadas,
não implementadas, backlog. Retrospective opcional. Status, uso de IA, README
e artefato final sincronizados apenas documentalmente, com histórico preservado.
Não executei novo verify local, commit, push ou deploy. Chromium encerrado.

Conferência documental final: `git diff --check` sem erros; onze arquivos
documentais/status alterados ou criados, sem fonte executável. Estados das
stories/sprint e opcionais conferidos; links do fechamento válidos; bloco
congelado desta story preservado; HEAD permanece no mesmo SHA local.
