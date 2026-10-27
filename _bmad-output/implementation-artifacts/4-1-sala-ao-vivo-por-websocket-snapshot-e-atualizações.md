# Story 4.1 — Sala ao vivo por WebSocket: snapshot e atualizações

Status: **review** — implementada em 27/10/2026; findings aprovados do 1º code review corrigidos em 27/10/2026 (seção 15); aguardando re-review independente e meu teste manual no navegador

Próximo passo: build desta story (`bmad-build`), sem nova spec: esta story
consolidada é a especificação. A 4.2 não começa junto.
Chave: `4-1-sala-ao-vivo-por-websocket-snapshot-e-atualizações`.
Épico 4 — Sala ao vivo e encerramento. Criação: 27/10/2026; consolidação com as
decisões humanas: 27/10/2026. Trabalho documental, sem código.

> **Decisões do dono (27/10/2026).** D1 aprovada: rota `/ws/lots/{lot_id}`; lance
> só por `POST /api/lots/{lot_id}/bids`, nada de lance por WebSocket. D7 aprovada:
> sala pública, só estado público/pseudonimizado; `Origin` presente é validado
> contra a `APP_ORIGIN` configurada e diferente é rejeitado; ausente é aceito; sem
> JWT na URL. D2–D6 e D8–D10 aprovadas como propostas abaixo. Q2 e a parte
> WebSocket da Q10 estão fechadas (registradas em `CLAUDE.md` e no AD-10 de
> `docs/ARQUITETURA.md`, sem mudar a decisão do AD-10). Onde o texto abaixo ainda
> diz "recomendo", leia "decidi". Heartbeat, timeout, backoff e reconexão
> automática ficam na 4.2.

## 1. Story e objetivo

Como licitante, leiloeiro ou visitante da sala, quero receber um snapshot público
completo ao conectar e acompanhar lances, líder e novo fim sem recarregar, para
acompanhar a disputa com o estado confirmado do servidor.

Recomendo introduzir o WebSocket real como transporte de leitura da sala. O
lance permanece exclusivamente em `POST /api/lots/{lot_id}/bids`, na transação
existente. O transporte observa o resultado; não decide saldo, integridade,
aceitação, cancelamento ou anti-sniping.

ADs vinculantes: AD-1–AD-8, AD-10, AD-11, AD-15, AD-17, AD-19–AD-22,
AD-25–AD-30. O heartbeat e a reconexão previstos no conjunto AD-10/AD-25 são
entrega da 4.2; a 4.1 implementa apenas conexão, snapshot e atualizações.

## 2. Fontes e estado real relevante

Consultei `CLAUDE.md`, `docs/ARQUITETURA.md`, o enunciado/planejamento por suas
referências em `epics.md`, `sprint-status.yaml`, stories 3.4/3.5 e suas specs em
`_bmad-output/specs/spec-story-3-4-lance-transacional/` e
`_bmad-output/specs/spec-story-3-5-dar-lance-pela-sala-do-lote/`. Priorizei os
contratos transacional, HTTP, concorrência, frontend e testes, confrontados com
o código vivo. Para UX, li `DESIGN.md`, `EXPERIENCE.md` e
`docs/FRONTEND-WORKFLOW.md`. O PRD separado foi dispensado pelo projeto.

| Área | Estado confirmado e consequência |
| --- | --- |
| Tracking | Epics 1, 2 e 3 `done`; 3.4/3.5/3.6 `done`; Epic 4 e todas as 4.x `backlog`. A nota antiga de CLAUDE sobre Epic 3 não prevalece sobre o sprint atualizado |
| Writer de lance | `backend/app/bids.py`: `place_bid` não faz commit; `place_bid_route` síncrona autentica, encerra leitura de auth, chama serviço e executa `session.commit()` antes do 201. Ainda não publica |
| Protocolo | Lote `FOR UPDATE` → hora PostgreSQL → gate → regras → carteiras por UUID crescente → efeitos → commit. A 4.1 não altera ordem, regras ou locks |
| Sala REST | `GET /api/lots/{lot_id}/bids`: `PublicBidRoomResponse`; uma consulta com clock materializado e LATERAL; máximo 50 lances por `sequence DESC`; nenhuma escrita ou validação integral de integridade |
| Detalhe | `GET /api/lots/{lot_id}` fornece obra/termos públicos. A sala separa metadados estáticos e read model dinâmico |
| Privado | `GET /api/lots/{lot_id}/bids/mine` só BIDDER: `bidder_alias`, `my_bid_count`, `last_bid_cents`. Carteira por endpoint autenticado. Posição já foi decidida na 3.5; não reabro ranking |
| Cancelamento real | `backend/app/lot_cancellation.py`: mesma trava/gate; escreve só `cancelled_at` se sem lances; rota faz commit. Repetição é 200 idempotente. Hoje o resultado não distingue transição nova de repetição |
| Lote cancelado | Detalhe, sala e participação públicos/privados por lote passam a 404, e a vitrine o omite. `phase` continua apenas `scheduled`, `live`, `ended`; cancelamento é eixo separado |
| Frontend | `LotPage.tsx` coordena detail/room/priv, gerações, AbortController, `roomRound`/`mineRound`; 201 aplica overlay imediato e dispara releituras. Hoje nada atualiza por transporte contínuo |
| Garantias da 3.5 | `bidSubmission` mantém POST pendente por conta+lote através de remontagem; `bidPosition` exige par público/privado; countdown usa `performance.now()` e âncora servidor; zero agenda uma releitura por fim, sem decidir fase |
| Infra WS do Epic 1 | `/api/infra-check/ws` em `infra_check.py`: público, só echo de uma mensagem, depois fecha; limite 64 bytes e timeout técnico 10 s. Não é sala nem broadcaster. Sua política de Origin não decidiu Q2 |
| Infra aplicação | `websocket_route(..., policy=PUBLIC)` já existe em `access.py`; `main.py` registra rotas antes da SPA. `start.sh` sobe um uvicorn sem múltiplos workers. Vite só faz proxy HTTP de `/api` e `/health` hoje |
| Session | `db.py`: factory síncrona, `expire_on_commit=False`, dependência sem commit automático. Não compartilhar Session entre handler e thread de leitura WS |

Usei o código atual como autoridade de implementação. As seções “estado atual”
das specs antigas descrevem o momento anterior a seus builds, não o estado de hoje.

Testes consultados: `backend/tests/integration/test_bid_reads.py`,
`test_bid_routes.py`, `test_bid_service.py`, `test_bid_concurrency.py`,
`test_lot_cancellation.py`, `test_lot_cancellation_concurrency.py`,
`backend/tests/test_infra_check.py`, `test_access_policy.py`, `test_csrf.py`;
`frontend/e2e/lot-room.spec.ts`, `real-stack.spec.ts`, `support/mockApi.ts`, e
testes puros de bids, posição, countdown e submissão. Não executei testes.

## 3. Recomendações D1–D10

### D1 — Rota WebSocket (Q10; APROVADA)

Recomendo **`/ws/lots/{lot_id}`**, mesma origem, `ws` em desenvolvimento e `wss`
em HTTPS. Não encontrei rota final de sala já aprovada. O exemplo pedido pelo
usuário corresponde a uma rota clara de transporte; `AD-30` exemplifica `/api/*`
para HTTP e não fecha o nome do WS (Q10 continua aberta).

Alternativa: `/api/lots/{lot_id}/ws`, que compartilha o prefixo da API e sua
reserva HTTP. Custo semelhante: qualquer escolha requer proxy WS explícito no
Vite, política de acesso, teste de handshake e documentação. Com `/ws/*`,
recomendo reservar esse prefixo no fallback HTTP para não devolver HTML da SPA
num GET equivocado; registrar WS antes da SPA. Retirar a rota técnica
`/api/infra-check/ws` e seus testes específicos, substituindo-os pela sala real.

### D2 — Snapshot inicial completo do estado dinâmico

Recomendo o envelope exato `{type: "room_snapshot", lot_id, room}`, onde `room`
reutiliza **todos e somente** os campos atuais de `PublicBidRoomResponse`:

| Campo | Tipo e significado |
| --- | --- |
| `lot_id` (envelope) | UUID público do lote da conexão; evita aplicar mensagem de outro lote |
| `room.as_of` | ISO 8601 UTC do `clock_timestamp()` da leitura; âncora de relógio, não versão de commit |
| `room.phase` | `scheduled`, `live` ou `ended`, calculada no servidor |
| `room.ends_at` | Fim efetivo persistido, incluindo extensões já confirmadas |
| `room.current_bid_cents` | Inteiro em centavos ou `null` sem lances |
| `room.minimum_next_bid_cents` | Inteiro ou `null` quando não representável, pelas regras já existentes |
| `room.bid_count` | Contagem total; pode exceder o tamanho da janela |
| `room.bids` | Lista completa da janela atual: até 50, `sequence DESC`; cada item apenas `sequence`, `bidder_alias`, `amount_cents`, `placed_at` |

O primeiro item de `bids` identifica o líder por alias persistido, quando há
lances. Não acrescento `leader_id`, ranking, hash, carteira nem novo “server_time”
duplicando `as_of`. Preservo as nulabilidades e o mínimo mesmo em fase encerrada
do contrato REST; frontend não usa mínimo como autorização de lance.

“Completo” significa que uma nova aba recebe todo o estado dinâmico necessário
sem depender de eventos anteriores. A obra e os termos estáticos continuam no
GET de detalhe da 3.5; não há exigência de dispensar esse endpoint. A participação
e a carteira permanecem separadas. Não altero o contrato exato dos GETs para
acomodar campos do envelope WS. Para lote já cancelado não há snapshot público:
aplica-se D8. Para cancelamento posterior há evento terminal separado.

### D3 — Conjunto mínimo de eventos

Recomendo três variantes discriminadas e tipadas, com validação de payload:

| `type` | Campos além do discriminante | Quando |
| --- | --- | --- |
| `room_snapshot` | `lot_id`, `room` da D2 | Uma vez, como primeira mensagem de dados de toda conexão aceita |
| `bid_accepted` | `lot_id`, `room` completo da D2 | Após sinal pós-commit de lance e releitura pública confirmada |
| `lot_cancelled` | `lot_id`, `cancelled_at` UTC | Após transição real de cancelamento confirmada; terminal |

Não recomendo evento genérico `update` com campos opcionais frouxos nem eventos
separados para valor, líder e prorrogação, que permitiriam UI parcialmente atualizada.
`lot_cancelled` tem o instante persistido do cancelamento e não inventa fase
`cancelled`. Não crio eventos de encerramento/liquidação/resultado (4.3/4.4).

### D4 — Publicação somente pós-commit

Recomendo manter o serviço financeiro sem dependência de transporte. A rota
síncrona sinaliza **apenas depois de `session.commit()` retornar com sucesso**:

```text
POST /api/lots/{id}/bids
→ place_bid: trava → hora → gate → regras → efeitos
→ session.commit() concluído
→ sinal público mínimo (lot_id) ao publicador async
→ Session curta própria em threadpool: read_public_room
→ enfileirar snapshot público para clientes do lote
```

Para a ponte entre a rota `def` em worker AnyIO e o loop do manager, recomendo
`anyio.from_thread.run` chamado no caminho pós-commit. A leitura do publicador usa
`run_in_threadpool`/`to_thread.run_sync` e abre/fecha sua própria Session dentro
da função síncrona. Não usar `asyncio.run`, loop novo por POST, tarefa solta sem
dono nem compartilhar a Session da rota com o event loop. Se importar AnyIO
diretamente, declará-lo como dependência direta no futuro build (já resolvido no
lock); não atualizar versões como parte desta story.

Não publicar em `place_bid`, `flush`, `before_commit`, construção de resposta ou
dependência de encerramento da Session. Falha de commit, rollback, 404, recusa
422 e conflito 409 não sinalizam. Se a publicação falhar **depois** do commit,
o lance continua aceito e o 201 deve ser preservado: registrar falha genérica e
isolar conexões afetadas, sem rollback fictício ou recusa financeira tardia.
Falha indeterminada de rede no próprio COMMIT mantém a limitação já documentada.

Para cancelamento, distinguir internamente “nova transição” de “já cancelado”
sob a trava existente; só a primeira sinaliza depois do commit. Preservar corpo
e idempotência HTTP. Não basta publicar em todo resultado `CancelledLot` atual.

### D5 — Snapshot completo em vez de delta

Recomendo substituir o read model inteiro em cada `bid_accepted`, inclusive a
janela, o mínimo e `ends_at`. A exceção é o evento terminal de cancelamento,
cujo payload é fechado pela D3. Descarto concatenar lances e recalcular dinheiro
ou prorrogação no cliente. O custo da janela de 50 é pequeno nesta escala.

Cada sinal é seguido de releitura do estado público atual. Se dois commits
ocorrerem antes da publicação, o evento pode carregar o estado mais recente já
confirmado (coalescência); não prometo um evento de histórico por transação nem
um snapshot “exatamente do lance que disparou o sinal”. Todos os lances
confirmados permanecem no banco; a janela e o count convergem corretamente.

### D6 — Múltiplos clientes, ordem e handshake

Recomendo um manager por instância de aplicação, em memória, com assinantes
indexados por `lot_id`, acessado somente no event loop. Duas abas do mesmo lote
recebem o mesmo snapshot de broadcast; outro lote não recebe nada.

Serializar a **distribuição por lote**, incluindo inscrição, leitura inicial e
publicação: sob a coordenação local do manager, ler o snapshot, enfileirá-lo
como primeira mensagem e tornar a conexão elegível para as próximas publicações
sem janela de perda. O mesmo coordenador serializa releitura pós-commit e
enfileiramento para que uma leitura antiga não seja enviada depois de uma nova.
Essa coordenação não envolve a transação de lance, não acrescenta trava SQL nem
substitui AD-8. Não manter trava de distribuição durante I/O lento de cliente.

Recomendo fila limitada por conexão e um único emissor por socket, preservando
ordem de envio. Cliente travado/fila cheia deve ser encerrado e removido sem
bloquear outros clientes ou transformar o POST aceito em erro. A spec fixa a
capacidade pequena e a organização das tarefas; não é heartbeat. Limpar conexões,
filas e entradas de lote sem assinantes no disconnect/finalização; sem sessões
de banco durando a conexão.

O publicador lê o estado atual mesmo quando os sinais de A/B chegam invertidos.
Não enviar snapshot de B e depois estado anterior capturado de A. `bid_count`
não pode regredir numa conexão; cancelamento terminal não pode ser desfeito por
uma mensagem atrasada. `as_of` não prova ordem de commit e não substitui essa
coordenação. Sem versão persistida, migration, Redis, outbox ou novo protocolo
de locks financeiros.

### D7 — Acesso público e Origin (Q2; APROVADA)

Recomendo `websocket_route(..., policy=AccessPolicy.PUBLIC)`. Visitante,
AUCTIONEER, BIDDER e cookie inválido recebem o mesmo estado público. Sem JWT na
URL, exigência de login, leitura de `users` ou identidade por socket. O alias do
histórico é o persistido; nenhum alias histórico é recalculado para publicar.

Para **Q2**, recomendo validar `Origin` contra `APP_ORIGIN` configurada, comparando
origem completa (esquema, host, porta normalizada), rejeitando estrangeiro,
malformado e `null`; aceitar ausência só para clientes não navegador, como na
infra técnica atual. Browser same-origin sempre envia Origin. Não usar `Host`
recebido como lista de confiança nem Referer como fallback improvisado do WS.

**Aprovado:** exatamente a política acima. Implementação: reutilizar
`parse_origin`/`format_origin` de `app/csrf.py` (esquema, host e porta efetiva)
contra a `APP_ORIGIN` já normalizada da aplicação; a comparação só por `host` da
verificação técnica da 1.4 (`infra_check.is_allowed_origin`) sai junto com ela e
não é reaproveitada. Rejeição no handshake, antes de `accept`.

Alternativas descartadas pelo dono: exigir Origin também nos clientes não navegador (política
mais fechada, testes/scripts precisam enviá-lo), ou não validar num stream
estritamente público (menos barreira a uso cruzado). Custo baixo para qualquer
escolha; recomendo a primeira política descrita, reaproveitando a origem
normalizada já configurada. A decisão não está implicitamente fechada pelo
middleware CSRF: ele atua somente em HTTP de escrita e não intercepta WS.

Participação (`/bids/mine`) e carteira só por endpoints autenticados. O frontend
revalida a participação por rodada de estado público aplicada, com coalescência,
e preserva o par público/privado. Não chama endpoints privados para visitante ou
leiloeiro. Saldo nunca é calculado por evento público.

### D8 — Cancelamento

Recomendo rejeitar novas conexões para lote inexistente **ou já cancelado**, sem
detalhe que diferencie os dois, alinhado ao 404 REST. Para os já conectados,
publicar `lot_cancelled` depois do commit, encerrar normalmente após sua entrega
e limpar assinantes. A UI invalida a sala para lance, mostra texto “Este lote foi
cancelado” e oferece retorno à vitrine; não depende de um GET que agora dá 404.

O instante `cancelled_at` vem da transição confirmada, sem expor dono ou motivo
interno. Conexão ocorrendo durante cancelamento vê snapshot anterior seguido do
terminal, ou já é rejeitada; nunca permanece ativa mostrando lote utilizável
após a publicação. A distinção de cancelamento para assinante existente não
altera a ocultação pública das leituras futuras aprovada na 3.6.

Na corrida bid × cancel, o protocolo já existente decide: cancel primeiro →
zero bids e só terminal; bid primeiro → cancel recusado e só atualização do bid.
Repetição idempotente e cancel recusado/rollback não geram evento novo.

### D9 — Anti-sniping

Recomendo enviar o `ends_at` efetivo lido após o commit, no mesmo snapshot do
lance, mínimo e histórico. Reancorar o countdown com `as_of`/`ends_at`, sem somar
dois minutos no browser, sem timer de domínio no WS e sem reabrir lote vencido.
Não preciso de evento separado `anti_sniping` nem de flag financeira pública:
o fim confirmado é suficiente. Na concorrência, a releitura pode já mostrar o
fim de estado confirmado posterior; isso é correto.

### D10 — Falha, mensagens de entrada e limite com a 4.2

Recomendo abrir uma conexão por montagem/lote e fechá-la no cleanup. Após queda,
manter último snapshot claramente marcado como desatualizado e o botão
“Atualizar sala” como releitura REST; recarregar/reabrir a página cria nova
conexão. Sem prometer continuidade enquanto desconectado, sem novo botão de
reconexão ou política definitiva de perda de conexão.

Contrato de entrada nesta story: nenhum comando de aplicação. Mensagem JSON de
lance nunca chama serviço nem altera banco; mensagem não suportada encerra com
1008 (binário não suportado, 1003). Rejeição antes de `accept` para id inválido,
lote ausente/cancelado ou Origin não permitido usa a semântica de recusa de
handshake do ASGI; não prometer 404 JSON no upgrade nem motivo legível ao JS do
browser. Erro interno após aceite fecha com 1011 genérico, sem stack/segredo.
Disconnect e encerramento normal limpam recursos; cancelamento entregue fecha
com 1000. Essas são recomendações de protocolo a fixar na spec.

**D-B (decisão minha após o 1º code review, 27/10/2026).** Ao receber o evento `offline` do
navegador, a sala fecha também o WebSocket atual e marca as atualizações ao vivo como
indisponíveis (o `onmessage` é desligado, para o que se aplica bater com o que o painel diz).
O evento `online` não reconecta, e nada disso é heartbeat, timeout, backoff ou reconexão
(4.2). Descartei deixar o socket aberto com o rótulo "desatualizado": se ele sobrevivesse
a uma oscilação curta, a tela aplicaria quadros ao vivo sob um aviso falso, e o estado nunca
voltaria a "conectado". Descartei também voltar a "conectado" ao próximo quadro: seria uma
política de conexão, que é da 4.2.

Não transportar o timeout de echo de 10 s para a sala. Não implementar heartbeat
de aplicação periódico, timeout por ausência dele, backoff, tentativas de
reconexão ou replay. Ping/pong de controle eventualmente fornecido por
Uvicorn/WebSocket é comportamento do protocolo/runtime; não constitui o
heartbeat de aplicação cliente da 4.2 e não deve ser usado como prova dele.

## 4. Integração frontend e proteção de respostas atrasadas

Recomendo um contrato WS TypeScript simples com discriminante e guardas de
payload, e uma autoridade comum para aplicar estado REST/WS/201 no `LotPage`.
Descarto um `setRoom` paralelo sem coordenação. Exijo na futura spec:

1. Identidade de montagem/lote em cada callback; fechar e ignorar socket antigo
   após navegação. Mudança de sessão não duplica uma conexão pública.
2. Snapshot completo substitui lista, nunca append; `sequence` continua key.
   Mensagem duplicada não duplica linhas nem gera tempestade de chamadas privadas.
3. `bid_count` menor não substitui estado com count maior. O count igual não
   ordena cancelamento nem mudança temporal de fase: terminal prevalece e rodadas
   capturadas antes de mensagem WS aplicada são invalidadas. REST posterior só
   pode aplicar pela geração vigente, respeitando o piso de count e terminal.
4. WS N+1 pode chegar antes do 201 do POST N. O 201 continua confirmando o sucesso
   daquela tentativa, mas seu overlay de preço/fim e âncora não pode regredir o
   estado N+1. A carteira retornada é um snapshot privado daquele POST; revalidar
   sem presumir que representa o saldo após outro bid já confirmado.
5. Evento público invalida o par de participação anterior; coordenar `/mine` e
   carteira por rodada coalescida. Não mostrar “ganhando/superado” com par velho;
   em falha, ocultar posição até revalidação válida. Não inferir aceitação de
   tentativa ambígua pelo alias de um evento.
6. Preservar texto digitado, foco e mensagem do POST durante atualização; nunca
   reenviar lance, limpar erro de tentativa ou confirmar sucesso por broadcast.
   Manter registro pendente e acompanhamento na remontagem da 3.5/F-01.
7. Preservar Atualizar sala, releitura ao zero e após POST, descarte de respostas
   fora de ordem e `AbortController`; integrar WS a essas garantias. O browser
   não decide fase, elegibilidade financeira ou liquidação.
8. Atualizar o texto “a sala não se atualiza sozinha” no `LotBidPanel` para estado
   real da conexão: conectando, conectado, atualizações indisponíveis. Texto/ícone
   além de cor. Sem alterar visual da vitrine ou redesenhar a sala.

Não introduzo versão persistida nem uso só `Date.parse(as_of)` como ordem causal.
Os testes devem forçar as corridas acima, inclusive igualdade do timestamp e
cancelamento com count zero. A spec formaliza a máquina de aplicação e sua
arbitragem antes de qualquer build.

### 4.1 Regra de ordenação do estado da sala (aprovada, sem protocolo novo)

Aproveito `bid_count`, que já existe no read model e só cresce (cada lance aceito
soma 1; nada o reduz). Não crio versão, migration nem campo no payload. Uma função
pura e única, `shouldApplyRoom(current, incoming)`, vale para **toda** fonte de
estado público do cliente (snapshot WS, `bid_accepted`, GET `/bids` e o overlay do
201). Ela é a segunda linha de defesa; a primeira é a serialização por lote no
servidor (D6).

| Situação | Resultado |
| --- | --- |
| Lote já marcado como cancelado (terminal) | Nada o substitui; só mensagem de outro lote é descartada por `lot_id` |
| `incoming.bid_count < current.bid_count` | **Descarta.** Estado antigo nunca sobrescreve o mais recente |
| `incoming.bid_count > current.bid_count` | Aplica (substitui a sala inteira) |
| Igual | Mesmos lances e mesmo `ends_at` (só um lance muda `ends_at`); só `phase`, `as_of` e o mínimo derivam do tempo. Aplica **se e somente se** `as_of(incoming) >= as_of(current)`; `as_of` vem do mesmo `clock_timestamp()` do PostgreSQL e serve só de desempate de campos derivados do tempo, nunca para ordenar lances |

Corridas que os testes precisam provar:

1. **Snapshot inicial × broadcast concorrente.** No servidor: inscrição, leitura
   inicial e enfileiramento do snapshot são serializados por lote com a
   publicação (D6); o primeiro frame é sempre o snapshot e nenhum broadcast o
   precede nem o contradiz. No cliente: mesmo que um GET `/bids` ou um evento
   chegue fora de ordem, `shouldApplyRoom` descarta o de `bid_count` menor.
2. **201 do POST N × atualização WS mais recente.** O 201 sempre confirma a
   tentativa (mensagem de sucesso, limpeza do campo, carteira do próprio POST).
   O overlay de preço, `ends_at` e âncora só se aplica se
   `placed.bid.sequence > room.bid_count` atual; se a sala já tem
   `bid_count >= sequence` (WS N+1 chegou antes), o overlay é ignorado e a sala
   atual permanece. Se a sala ainda não existe (remontagem), o 201 a cria como hoje.
3. **REST atrasado depois de WS novo** (GET `/bids` lançado antes, resolvido
   depois): descartado pela mesma regra. Rodadas e gerações da 3.5 continuam
   valendo para `/mine`, carteira e detalhe.

`lot_cancelled` é terminal e prevalece sobre qualquer contagem, inclusive com
`bid_count` 0. A posição (ganhando/superado) continua exigindo par público/privado
da mesma rodada; um evento que aplica sala nova invalida o par e dispara
revalidação coalescida de `/mine` (só para BIDDER).

## 5. Critérios de aceitação da futura implementação

Os critérios abaixo adotam as decisões aprovadas (rota `/ws/lots/{lot_id}` e
política de `Origin` da D7). Acrescentei CA15 e CA16 na consolidação.

1. **CA1 — Conexão pública real.** Dado lote existente não cancelado, visitante,
   BIDDER e AUCTIONEER conectam na rota aprovada sem JWT na URL, inclusive sem
   login. A política pública é declarada e testada. O echo técnico é removido.
2. **CA2 — Snapshot inicial suficiente.** A primeira mensagem é `room_snapshot`
   com envelope D2 e todos os campos exatos do read model atual, inclusive vazio,
   50 recentes e total maior que 50. A nova aba não precisa de evento anterior.
3. **CA3 — Leitura pura e curta.** Snapshot/releituras de banco rodam em threadpool,
   Session criada/fechada na função síncrona, dados coerentes em um statement;
   nenhum SQL bloqueante no event loop. Handshake/GET/HEAD/OPTIONS não escrevem,
   não travam lote e não liquidam, inclusive quando vencido.
4. **CA4 — Pós-commit.** Dado POST válido e commit concluído, só então sinal e
   broadcast; o snapshot recebido é relível por outra Session independente.
   Flush, rollback, falha de commit, recusa e conflito não emitem atualização.
5. **CA5 — Broadcast isolado.** Duas conexões saudáveis do mesmo lote recebem o
   estado publicado; outra sala não recebe. Um cliente lento/desconectado não
   bloqueia os demais nem muda o resultado do POST confirmado.
6. **CA6 — Concorrência e ordem.** Dois lances concorrentes representam somente
   estados confirmados; snapshots não regridem e convergem para o estado final.
   Sinais invertidos e inscrição durante publicação não perdem a última mudança.
   Coalescência é permitida; não se exige cada estado intermediário na tela.
7. **CA7 — Privacidade.** Todos os eventos têm chaves e valores públicos
   permitidos; sem user_id, bidder_id, líder real, auctioneer_id, e-mail, nome,
   carteira, hash, HMAC, segredo ou dados internos. Alias histórico persistido.
8. **CA8 — Anti-sniping.** Aceite na janela entrega no evento o fim efetivamente
   persistido, coerente com lance/histórico; o outro cliente reancora countdown
   sem refresh nem cálculo local de extensão.
9. **CA9 — Cancelamento.** Novas conexões ausentes/canceladas são recusadas conforme
   D8; assinantes recebem terminal somente após transição confirmada e fecham.
   Repetição, recusa e rollback não geram novo terminal; corrida com primeiro
   lance preserva exatamente os dois resultados legítimos da 3.6.
10. **CA10 — Sala atualiza sem refresh.** Snapshot e `bid_accepted` atualizam
    preço, mínimo, líder por pseudônimo, count, histórico e fim na outra aba,
    substituindo lista sem duplicação. Eventos são tipados e validados.
11. **CA11 — Regressões protegidas.** REST atrasado, 201 N após WS N+1,
    callbacks de outro lote/conta e falha privada não restauram estado ou posição
    antigos; pending POST, digitação, foco, mensagens, countdown e refresh da 3.5
    continuam corretos. Posição própria usa endpoint autenticado e texto/ícone.
12. **CA12 — Fronteira 4.2.** Fechamento/erro mostra desatualização e mantém
    alternativa REST manual. Não há heartbeat de aplicação, timer de heartbeat,
    backoff, reconexão automática, replay nem reenvio automático de POST.
13. **CA13 — Desenvolvimento e produção.** Proxy WS do Vite e URL ws/wss mesma
    origem funcionam; a demonstração em URL Render usa a sala real e dois
    clientes, sem rota técnica. Prova local não é registrada como prova Render.
14. **CA14 — Verificação do build.** Testes determinísticos abaixo e regressões
    relevantes passam; `./verify.sh` com saída real registrado. Playwright
    simulado e smoke real explicitamente identificados, conforme opt-ins atuais.
15. **CA15 — Estado antigo nunca sobrescreve o recente (servidor).** Dados dois
    commits A e B com sinais invertidos, ou conexão aberta durante uma publicação,
    a sequência de `bid_count` recebida por uma conexão é não decrescente, o
    primeiro frame é `room_snapshot` e o último estado recebido é o do banco.
16. **CA16 — Estado antigo nunca sobrescreve o recente (cliente).** Pela regra da
    §4.1: GET `/bids` ou evento com `bid_count` menor é descartado; o 201 do
    lance N não regride a sala já em N+1 (preço, mínimo, `ends_at`, âncora e
    histórico), mas confirma a tentativa; `lot_cancelled` não é desfeito por
    mensagem atrasada; empate de `bid_count` só aplica com `as_of` não menor.

## 6. Escopo e exclusões

Incluo endpoint WS, manager de um processo, snapshot inicial, broadcast completo
pós-commit de lance/cancelamento, integração com sala atual, limpeza de recursos,
política pública/Origin aprovada, substituição da verificação técnica, proxy de
desenvolvimento, testes e documentação da limitação commit/publicação.

Deixo fora: **Story 4.2 inteira** (heartbeat periódico, timeout, reconexão
automática/backoff e estratégia definitiva de conexão perdida); fechamento,
liquidação, scheduler, catch-up, evento de encerramento/resultado (4.3/4.4),
painel de resultado (4.5), comprovantes/auditoria, cancelamento com lances e
estorno (6.6), ranking, paginação integral, vitrine em tempo real, alterações de
saldo/hash/HMAC/regras/locks, outbox, broker, Redis, múltiplos workers,
exactly-once, garantia de replay, migração ou versão persistida, redesenho visual
e upgrade de stack. Não executar Git, ler `.env*` ou alterar secrets.

## 7. Riscos e limites aceitos

| Risco | Tratamento |
| --- | --- |
| Processo morre entre commit e publicação | Limitação AD-25; sem outbox. Na 4.1, refresh REST/reabrir a página recupera; recuperação automática só na 4.2. Não anunciar entrega garantida |
| Stream silencioso/serviço dorme antes da 4.2 | Não prometer detecção ou manutenção por heartbeat; mostrar desconexão quando detectada pelo transporte e manter refresh manual |
| Snapshot inicial disputa com broadcast | Coordenação local por lote da D6 + teste com barreira |
| Ordem das threads de POST difere da ordem de commit | Sinal só pós-commit; releitura e envio serializados do estado atual; sem snapshot antigo capturado no writer |
| Cliente lento prende distribuição/memória | Filas limitadas, um emissor por socket, limpeza e isolamento; sem aguardar I/O do cliente no writer financeiro |
| WS mais novo que 201/REST | Arbitragem compartilhada e testes adversos da §4; count não substitui terminal/gerações |
| Sobrecarga de leituras privadas | Coalescer rodadas; não reiniciar várias para mensagem duplicada; esconder posição antiga enquanto atualiza |
| Cancelamento repetido publica duas vezes | Distinguir nova transição sob trava, sem mudar HTTP nem gate |
| Origin divergente por proxy | Comparar com origem configurada aprovada, testar Vite e HTTPS; não inferir confiança de headers de proxy |
| Snapshot confundido com auditoria/decisão financeira | Leituras preservam contrato 3.5; o POST transacional continua autoridade; sem autenticar cadeia em toda leitura |
| Manager por processo usado com vários workers | Manter implantação de um processo do AD-10; sem escalar silenciosamente |
| **D-A (decisão minha após o 1º code review):** o `201` espera a publicação pós-commit | A rota espera, sem limite de tempo, a trava da sala do lote, uma vaga no limitador de leituras (4) e a releitura. Com rajada de conexões novas no mesmo lote ou banco lento, o `201` atrasa; se o navegador desistir antes, a tela trata o lance como incerto (a escrita já está confirmada). Mantive o comportamento e documentei no README. **Não** acrescentei timeout arbitrário nem teto de conexões: ambos ficam para a 4.2, junto da Q1 |

## 8. Plano de testes

Recomendo PostgreSQL real e conexões reais para persistência/commit e broadcaster;
testes puros para contratos/coordenador e Playwright para comportamento visível.
Não criar servidor financeiro falso como única prova de pós-commit.

| ID / AC | Cenário e prova determinística |
| --- | --- |
| B1 / CA1–3 | Conectar anônimo, BIDDER, AUCTIONEER e cookie inválido; snapshot com chaves exatas e nenhum SELECT de users; lote vazio, 51 bids, agendado, vencido e legado. Leitura não altera snapshot do banco |
| B2 / CA3 | Recorder: uma consulta de leitura com clock único, sem FOR UPDATE/escrita; função de banco executada fora da thread do loop; factory fecha Session antes de manter stream |
| B3 / CA4 | Dois sockets abertos; interceptar `Session.commit` no writer real com barreira/Event antes de delegar ao original. Enquanto bloqueado: estado velho numa conexão SQL independente, nenhum sinal/enfileiramento do publicador. Liberar commit; esperar marco pós-commit; receber evento e reler o bid em outra Session |
| B4 / CA4 | Injetar falhas depois de F1, depois do INSERT e antes do commit, como `test_bid_routes.py`; banco integral igual ao anterior e contador de publicação zero. Mesma prova para 422/409/404. Falha no broadcaster após commit preserva 201 e bid gravado |
| B5 / CA5 | Dois sockets L1, um L2: ambos L1 recebem mesmo estado; L2 sem enfileiramento. Desconectar um e simular fila cheia/cliente lento: outro segue, POST aceito e manager limpo |
| B6 / CA6 | A segura trava, B espera; A confirma, B segue. Atrasar sinal A até após sinal B, e leitura inicial até sobrepor publicação. Estados recebidos nunca regridem, final corresponde ao banco, primeiro frame sempre snapshot; não exigir todos os intermediários |
| B7 / CA7 | Percorrer JSON de cada variante: whitelist exata de chaves e ausência de valores reais de usuários, e-mails, hashes e segredos fictícios dos fixtures; aliases iguais aos persistidos. Logs/close reasons sem informação privada |
| B8 / CA8 | Fim com margem segura na janela; POST real renova o fim para `placed_at` + 2 min (AD-5 revisada em 27/10/2026); evento de ambos clientes contém fim relido e histórico correto. Concorrente seguinte lê o fim já renovado e, se ainda na janela, renova de novo a partir do próprio instante (lição IC-1 da 3.4, ajustada à AD-5 revisada) |
| B9 / CA9 | Cancelar conectado: terminal pós-commit, close 1000 e limpeza. Repetição, recusa e rollback não publicam. Novo connect cancelado/ausente indistinguível; corrida cancel × primeiro bid nas duas ordens existentes |
| B10 / CA1,12 | Origin conforme escolha final: mesmo, diferente, malformado, null e ausente; UUID inválido; erro interno genérico; texto de comando/bid e binário não escrevem; GET HTTP da rota WS não vira HTML; echo técnico deixa de existir |
| F1 / CA10 | WS simulado determinístico: snapshot monta e evento completo altera preço, mínimo, líder, total, histórico e fim sem clique/refresh; snapshot duplicado não duplica linhas nem chamadas privadas |
| F2 / CA11 | Adiar REST velho até após WS novo; adiar 201 N até após WS N+1; timestamps iguais; cancelamento count zero seguido de REST antigo; confirmar que valor/fim/terminal não regridem e mensagem do POST correto permanece |
| F3 / CA11 | Posição ganhando/superado/neutro com par atual; /mine atrasado/falha, participação fora dos 50, troca conta/lote e callback de socket desmontado. Visitante/leiloeiro não consultam endpoints privados |
| F4 / CA11–12 | Evento durante digitação/POST pendente; navegar e remontar no intervalo do F-01; zero countdown/refresh simultâneo/evento; nenhum POST duplicado. Close/error mantém snapshot marcado, refresh REST funciona, zero tentativas automáticas/heartbeat |
| B11 / CA15 | Ordenação no servidor: (a) conectar com barreira durante uma publicação em curso: primeiro frame é snapshot e `bid_count` não decresce depois; (b) sinais de A e B invertidos: o publicador lê o estado atual nas duas vezes, sequência não decrescente, final igual ao banco |
| F5 / CA16 | Testes puros de `shouldApplyRoom`: menor descarta, maior aplica, igual com `as_of` maior/igual aplica e menor descarta, terminal prevalece, `bid_count` 0, `lot_id` diferente; mais integração em `LotPage`: GET `/bids` atrasado após WS; 201 N depois de WS N+1 (overlay ignorado, mensagem de sucesso e carteira mantidas); snapshot duplicado |
| I1 / CA4–8,10 | Duas abas/clientes reais mesmo lote; uma dá lance REST; após commit outra muda preço/histórico e fim quando estendido, sem refresh. Teste com backend real, não apenas interceptação Playwright |
| I2 / CA13 | Smoke em desenvolvimento pelo proxy WS e no Render por wss; duas abas e Origin configurada. Registrar onde rodou; não executar deploy nesta criação |

Nas provas negativas, observar pontos de sinal/enfileiramento com spies e marcos
de sincronização; não bloquear para sempre em `receive_json()` esperando “nada”.
Deadlines limitam travamentos, não provam correção por passagem de tempo. Usar
barreiras/Event e finalizadores, como testes de concorrência existentes, sem
sleep arbitrário. Nenhum hook de teste novo em produção.

No build: preservar `./verify.sh` e suítes atuais; `VERIFY_E2E=1 ./verify.sh`
continua opt-in com Chromium. `real-stack.spec.ts` continua separado por
`E2E_REAL_BASE_URL`. Não ampliar esses gates silenciosamente.

## 9. Arquivos provavelmente afetados no futuro build

| Arquivo | Estado, mudança e preservação |
| --- | --- |
| `backend/app/lot_room.py` (nome proposto, novo) | Contratos WS públicos, leitura em threadpool e manager/registro. Evitar import circular com bids/cancelamento; main injeta dependência/manager |
| `backend/app/main.py` | Instanciar manager por app, lifecycle/limpeza e registrar sala; retirar registro do echo; preservar auth, origem, segredos e ordem antes da SPA |
| `backend/app/bids.py` | Reusar reader público e acrescentar sinal na rota depois do commit; preservar POST/GET, gate, regras, locks, DTOs e recusas |
| `backend/app/lot_cancellation.py` | Distinguir transição nova no resultado interno e sinal pós-commit; preservar idempotência, gate, exclusão de leituras públicas e corpo HTTP |
| `backend/app/infra_check.py` | Remover rota técnica substituída e imports; não migrar timeout/echo para a sala |
| `backend/app/spa.py` | Com D1 recomendada, reservar `/ws`/`/ws/*` para HTTP não virar SPA, preservando segurança de path e rotas existentes |
| `backend/app/access.py`, `db.py`, `lots.py` | Reusar helpers atuais; editar só se refatoração mínima justificada. Nenhuma mudança de schema/locks |
| `backend/pyproject.toml`, `backend/uv.lock` | Só declarar dependência direta AnyIO se importada; preservar versões resolvidas |
| `backend/tests/test_access_policy.py`, `test_infra_check.py`, `test_csrf.py`, `test_spa.py` | Substituir casos de echo por política pública/Origin e reserva da rota real; preservar regressões HTTP |
| `backend/tests/integration/test_lot_room_ws.py` (novo), testes de bids/cancelamento | B1–B10; reusar fixtures, fábrica de app, banco isolado e orquestração existente |
| `frontend/src/LotPage.tsx` | Unificar WS com rodadas detail/room/priv, overlay 201, cleanup e relógio; preservar pending entry capturada, sessão, mensagens e refresh |
| `frontend/src/LotBidPanel.tsx` | Estado textual da conexão; preservar layout, ações, feedback e posição |
| `frontend/src/lotRoomSocket.ts` e teste (nomes propostos) | Contrato WS tipado, validação, URL e arbitragem pura. WebSocket nativo; sem framework de estado ou socket.io |
| `frontend/src/api/bids.ts` e testes | Reusar tipos/guardas do read model se necessário, sem alterar contrato HTTP |
| `frontend/vite.config.ts` | Proxy de upgrade WS na rota aprovada, preservando mesma origem e porta fixa |
| `frontend/e2e/lot-room.spec.ts`, `support/mockApi.ts`, eventualmente `real-stack.spec.ts` | F1–F4, I1; preservar regressões de 3.5 e testes reais opt-in |
| `README.md`, `docs/uso_de_ia.md`, story, sprint | Documentar sala real, echo removido, limitação pós-commit e ausência de 4.2; comandos e resultados reais só no build |

`BidForm`, `bidSubmission`, dinheiro, `bid_integrity`, `bid_rules`, migrations,
carteiras e navegação não precisam mudar por padrão. Não tocar em `.env*` nem
em valores de segredos. Atualizar Q2/Q10 de CLAUDE/arquitetura somente depois da
decisão humana, preservando alternativas e a AD existente.

## 10. Tarefas para spec/build posteriores

- [x] Criar contexto documental, recomendações D1–D10, critérios e test plan.
- [x] Obter decisão humana para Q10/rota e Q2/Origin; consolidar docs (27/10/2026).
- [x] Spec: dispensada; esta story consolidada é a especificação (decisão do dono).
  Contrato final, coordenação handshake/publicação, ponte de threads, fila/limpeza
  e arbitragem estão nas D2–D10 e na §4.1.
- [x] Revisão/aprovação humana das decisões (27/10/2026).
- [x] Build autorizado: B1–B10 e manager/endpoint/writers pós-commit (CA1–9).
- [x] Integrar frontend/proxy e F1–F4 (CA10–12).
- [x] I1 local, verify e documentação com evidência real (CA14). I2 no Render **não** executado
  (CA13: a prova local não vale como prova Render). Teste manual no navegador: pendente, é meu.

Não executei essas tarefas de implementação nem criei spec nesta sessão.

## 11. Questões humanas

Nenhuma aberta para a 4.1. Q10 (rota `/ws/lots/{lot_id}`) e Q2 (`Origin`, D7)
foram decididas em 27/10/2026. Continuam fora desta story: Q1 (4.2), Q4/Q6/Q9 (4.4)
e a rota do comprovante/link da Q10. Não reabro posição do usuário, anti-sniping
(AD-5 revisada), locks, aliases, outbox ou decisões financeiras.

## 12. Definition of Done e conclusão desta criação

Para a futura implementação: duas abas no mesmo lote; lance exclusivamente REST;
commit concluído; outra aba recebe WebSocket e altera lance atual, histórico e
novo `ends_at` se houve anti-sniping, sem refresh manual, sem dados privados e
sem regressões da 3.5. Heartbeat e reconexão não fazem parte desse DoD.

Nesta consolidação (27/10/2026), registrei as decisões D1–D10 do dono, a regra de
ordenação por `bid_count` (§4.1), CA15/CA16 e os testes B11/F5, e fechei Q2 e a
parte WebSocket da Q10 em `CLAUDE.md` e no AD-10. Nenhuma implementação, teste,
verify, consulta ao banco, deploy, Git, leitura `.env*` ou alteração de secrets.

**Resultado: PRONTA PARA IMPLEMENTAÇÃO (`ready-for-dev`).** O sprint reflete o
status; o épico 4 passa a `in-progress` quando o build começar.

### Referências técnicas verificadas

Recomendo manter as versões do lock local: FastAPI 0.162.0, Starlette 1.9.0,
AnyIO 4.15.1, Uvicorn 0.54.0 e SQLAlchemy 2.1.6; no frontend, Vite 8.3.4 e
Playwright 1.64.1 resolvidos no manifesto/lock. Não afirmo que sejam as versões
mais recentes de todos os projetos nem proponho upgrade.

Consultei documentação primária para validar as APIs necessárias:
[FastAPI — WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
(disconnect e manager em memória limitado a um processo),
[AnyIO — API](https://anyio.readthedocs.io/en/stable/api.html)
(`from_thread.run` e restrição de worker/token),
[AnyIO — threads](https://anyio.readthedocs.io/en/stable/threads.html)
(ponte worker/loop),
[Vite — server options](https://vite.dev/config/server-options)
(proxy com upgrade WebSocket). São apoio técnico; as decisões do produto e as
versões vinculantes vêm do projeto. A spec deve conferir compatibilidade no
ambiente instalado antes do build.

## 13. Registro do build (27/10/2026)

Implementado: `backend/app/lot_room.py` (manager por processo, snapshot e `bid_accepted`
lidos em Session curta no threadpool, fila de 8 por conexão, um emissor por socket,
`lot_cancelled` terminal); sinal pós-commit em `bids.py` e `lot_cancellation.py`
(cancelamento só na transição nova); eco técnico `infra_check` removido; `/ws` reservado
no `spa.py`; proxy WS no Vite; `lotRoomSocket.ts` (`parseRoomMessage`, `shouldApplyRoom`,
URL ws/wss) e integração em `LotPage`/`LotBidPanel` (estado textual da conexão). Fora:
heartbeat, timeout, backoff, reconexão (4.2); fechamento, liquidação, scheduler,
comprovante (4.3/4.4). `anyio` declarado como dependência direta, sem mudar versões.

**Defeito achado na verificação (meu, do próprio teste):** em `VERIFY_E2E=1` o spec
`lot-room-ws.spec.ts` "countdown zero…" esperava `0:01`, mas o formato real do contador é
`00:01`. Corrigi só a expectativa errada (não afrouxei nada: a asserção segue exata) e
repeti o spec 5× (30/30 passaram).

**Smoke local (I1/CA13 parcial)**, banco descartável `casa_smoke` (já removido), segredos
fictícios só no ambiente do processo, uvicorn + Vite, duas conexões reais em
`ws://localhost:5173/ws/lots/{id}` (proxy do Vite): ambas receberam `room_snapshot` como
1º frame (`bid_count` 0); um `POST` de lance (201) gerou `bid_accepted` idêntico nas duas
(`bid_count` 1, 10000, alias `Licitante-…`); chaves só `type/lot_id/room`,
`as_of/bid_count/bids/current_bid_cents/ends_at/minimum_next_bid_cents/phase` e por lance
`amount_cents/bidder_alias/placed_at/sequence`; `Origin` hostil e lote inexistente: 403.

**Comandos executados (saída real):**
- Direcionados (backend): `pytest tests/test_lot_room.py tests/integration/test_lot_room_ws.py
  tests/test_access_policy.py tests/test_csrf.py tests/test_infra_check.py tests/test_spa.py`
  → 372 passed, 1 warning. Direcionado front: `node --test src/lotRoomSocket.test.ts` → 2/2.
- `./verify.sh` → exit 0: Ruff e format ok (91 arquivos); 2047 passed, 1 warning; 162 testes
  front, 0 falhas; ESLint, tsc, build do Vite e docker build ok.
- `VERIFY_E2E=1 ./verify.sh` (1ª execução) → falhou no teste acima (194 passed, 1 failed,
  5 skipped); após a correção → exit 0, Playwright 195 passed, 5 skipped.
- Único warning: `StarletteDeprecationWarning` (httpx no `starlette.testclient`), de
  dependência, preexistente; não mexi nas versões.

**Checklist de fechamento:** primeiro frame sempre `room_snapshot` (subscribe serializado
com a publicação; teste B6/B11 e smoke); sem broadcast antes do `commit()` (barreira em
`Session.commit`, B3); rollback/recusa/409 não publicam (B4); releitura em Session própria
e curta, em threadpool, com limiter (B2); nada de SQL síncrono no loop; cliente lento é
removido sem travar os demais (B5); isolamento por `lot_id`; terminal de cancelamento não
é desfeito (`shouldApplyRoom`, F2); `shouldApplyRoom` único para GET, WS e overlay do 201;
`bid_count` ordena e `as_of` do servidor só desempata; 201 confirma sucesso e carteira sem
regredir a sala; payload sem `user_id`, e-mail, carteira, hash ou HMAC (B7); o front só usa
o `ends_at` do servidor; 4.2 e 4.3/4.4 fora.

**Não feito:** I2 (Render, wss) e teste manual no navegador. Review independente ainda não
executado, por instrução.

## 14. Finding do meu teste manual e correção (27/10/2026)

**Finding (MEDIUM).** Com a sala conectada, pus o navegador em Network → Offline e esperei: o
indicador seguiu "Sala conectada". Ao clicar em "Atualizar sala", a falha do GET do detalhe
trocou a tela inteira por "Não foi possível carregar o lote".

**Causa.** (1) Sem heartbeat (4.2), o browser pode manter um socket morto "aberto" por muito
tempo, então `onclose`/`onerror` não disparavam. (2) `loadDetail` em `LotPage.tsx` gravava
`detail = failed` mesmo com o lote já exibido (a sala e a participação já preservavam o
último estado, o detalhe não). (3) `LotBidPanel` recebia `syncFailed` mas não o mostrava.

**Correção (só dentro da 4.1).**
- `LotPage.tsx`: o evento `offline` do navegador marca a conexão como indisponível (único
  sinal precoce sem heartbeat; não é heartbeat nem reconexão, e `online` não reconecta).
  *Atualizado na seção 15 (D-B): o `offline` também fecha o socket atual.* Remoção
  do listener no cleanup.
- `LotPage.tsx`: falha de rede/servidor na releitura do detalhe preserva o lote já exibido;
  só `not_found` (lote removido/cancelado) o substitui. Primeiro carregamento com falha segue
  mostrando o erro global.
- `LotBidPanel.tsx`: mensagem local `role="alert"` "Não foi possível atualizar a sala…
  últimos dados recebidos… tente novamente", com "Atualizar sala" habilitado para nova tentativa.
- Um GET manual bem-sucedido aplica a sala por `shouldApplyRoom`, mas não marca a conexão
  como conectada: só o socket faz isso. Sem reconexão, backoff ou heartbeat (4.2).

**Testes novos (`frontend/e2e/lot-room-ws.spec.ts`, Playwright com API simulada):**
offline muda de conectado para desatualizado e mantém preço/histórico; nenhum novo
`WebSocket` depois de `online` + refresh (1 conexão); fechamento do socket sem conexão
útil não apaga a sala e há uma só tentativa; refresh REST que falha (503 em detalhe e sala)
preserva a sala, mostra a mensagem local e não troca a página; novo refresh com sucesso
aplica a sala mais nova e limpa a mensagem. Observação: as rotas do Playwright respondem antes
da camada de rede, então a falha do refresh é injetada como 503 (`hold().fail()`), e o
offline real só exercita o evento `offline`. A falha por rede de verdade fica no meu teste manual.

**Execução:** `playwright test lot-room-ws --repeat-each=3` → 27 passed. `./verify.sh` →
exit 0 (Ruff/format ok, 2047 passed e 1 warning, 162 testes front, ESLint, tsc, build,
docker build). `VERIFY_E2E=1 ./verify.sh`: resultado registrado abaixo.

`VERIFY_E2E=1 ./verify.sh` após a correção → exit 0: 2047 backend passed (1 warning, o mesmo
`StarletteDeprecationWarning`), 162 testes front, Playwright 198 passed e 5 skipped, build e
docker build ok. Status segue `review`; aguardo meu novo teste manual.

## 15. Correções do 1º code review independente (27/10/2026)

O review (5 camadas, sessão diferente da que implementou) deu **CORREÇÃO NECESSÁRIA**: 1 MEDIUM, vários
LOW e duas decisões minhas. Corrigi só o que aprovei; não reespecifiquei a story nem toquei na 4.2+.

| ID | O que mudou |
| --- | --- |
| M1 | `privatePending` em `LotPage.tsx`: enquanto a revalidação de `/mine` disparada por quadro do socket está pendente, a posição fica oculta mas **não** aparece "Não foi possível carregar sua participação." (só em falha real) |
| L1 | `sameRoomState` (`lotRoomSocket.ts`) ignora só o `as_of`; mesmo estado público com `as_of` novo reancora o relógio e **não** cancela rodada nem dispara leitura privada. Substitui o `JSON.stringify` |
| L2 | `ambiguousRef`: se um quadro do socket supera a rodada pós-POST e a revalidação coalescida termina bem, o aviso de POST ambíguo passa a "O estado abaixo é o atual do servidor". Falha mantém o aviso parcial. Novo envio limpa a marca |
| L3 | Ao entrar em "Este lote foi cancelado", o foco vai ao `h1` (anunciado pelo leitor de tela) |
| L4 | `read_cancellation` normaliza `cancelled_at` para UTC |
| L5 | O handler não captura mais `CancelledError`: limpa (bloco blindado) e o cancelamento propaga |
| L6 | `manualFresh`: leitura manual bem-sucedida com socket indisponível mostra "Dados atualizados por leitura manual…" (não "desatualizado"); o GET não marca o socket como conectado; nova queda ou refresh falho limpa a marca |
| L7 | Testes das lacunas do plano da 4.1 (abaixo) |
| L8 | UUIDs fixos nos parâmetros (`test_lot_room.py`, `test_infra_check.py`) e nas constantes de lote inexistente |
| L9 | Logs de publicação, isolamento, falha de conexão e expulsão por fila cheia incluem `lot_id` e a **classe** da exceção (nunca a mensagem); expulsão e isolamento agora são logados |
| L10 | `docs/ARQUITETURA.md`: Q2 resolvida e parte WebSocket da Q10 resolvida na 4.1; comprovante/link seguem abertos |
| D-A | Mantive o comportamento; limitação documentada no README e na tabela de riscos (§7). Sem timeout nem teto de conexões: 4.2, com a Q1 |
| D-B | `offline` fecha também o socket atual e marca ao vivo como indisponível; `online` não reconecta (registrado na D10) |

**Testes novos/ajustados (L7 e demais).** Backend: falha de publicação com socket real conectado → 201,
fechamento 1011, sala limpa, log com `lot_id` e classe e sem a mensagem privada; fila cheia por POSTs reais
(um cliente que nunca drena é expulso com 1011 e o saudável recebe todos os quadros); repetição do
cancelamento não sinaliza (contando `signal_committed`, sem depender de assinantes); recusas 403, 422
(`lot_has_bids`, `lot_ended`), 409 e 404 da rota de cancelamento não sinalizam e não alteram o banco; Origin
decide sozinho para lote existente (controle com Origin válido aceito, `test_csrf.py` reescrito: antes passava
porque o lote não existia); `Origin` repetido recusado antes da leitura (ASGI direto); cancelamento do handler
propaga e limpa; whitelist exata de chaves de `bid_accepted` e do snapshot, sem e-mails, ids, hashes nem âncora.
Frontend: `sameRoomState` (node), e no Playwright M1 (mensagem ausente com `/mine` retido), L1 (`as_of`
crescente, sem nova chamada privada), L2, L3, D-B (socket realmente fechado), L6, e `lot_cancelled` terminal
(foco, leitura pendente abortada e quadro posterior de contagem maior não desfazem). Observação: ao chegar o
terminal, a página **aborta** o GET pendente; por isso não existe "resposta REST tardia" a aplicar no browser, e a
2ª linha de defesa (`shouldApplyRoom(..., cancelled)`) fica coberta no teste puro, não no Playwright.

**Prova de que os testes mordem (mutação, restaurada depois).** Reintroduzir a captura de `CancelledError` fez
falhar 2 testes de `test_lot_room.py`; sinalizar a cada cancelamento (sem `transitioned`) fez falhar
`test_cancel_post_commit_terminal_idempotent_and_hidden`; desligar M1, L1, L2, L3 e D-B no `LotPage.tsx` fez
falhar 6 specs de `lot-room-ws`, que passaram de novo com o código restaurado.

**Comandos executados (saída real):**
- Direcionados backend: `pytest tests/test_lot_room.py tests/integration/test_lot_room_ws.py tests/test_csrf.py
  tests/test_infra_check.py tests/test_access_policy.py tests/test_spa.py` → 382 passed, 1 warning.
- Direcionado front: `npx playwright test lot-room-ws --repeat-each=3` → 33 passed; `npm test` → 163 pass, 0 fail.
- A 1ª execução de `./verify.sh` parou no Ruff (8 × E501 e formatação nos testes novos, meus); corrigi só
  formatação/linhas e repeti.
- `./verify.sh` → exit 0: Ruff e format ok (91 arquivos); **2057 passed**, 1 warning; 163 testes front, 0 falhas;
  ESLint, tsc, build do Vite e docker build ok.
- `VERIFY_E2E=1 ./verify.sh` → exit 0: 2057 passed backend, 163 front, **Playwright 200 passed, 5 skipped**,
  build e docker build ok. Warning único: o mesmo `StarletteDeprecationWarning`, preexistente.

**Não feito / pendente:** I2 (Render, wss, duas abas) e meu teste manual no navegador; re-review independente.
Itens deferidos pelo review e que **não** mexi: e2e opt-in (decisão do CA14). Status segue `review`; sprint-status
intocado. Não iniciei a 4.2; sem Git; nenhum `.env*` lido.
