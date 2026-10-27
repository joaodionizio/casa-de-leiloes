# Story 4.1 — Sala ao vivo por WebSocket: snapshot e atualizações

Status: backlog — criada, aguardando decisões humanas Q2/Q10

Próximo passo: **PRECISA DE DECISÕES**; depois, criação de spec em sessão autorizada.
Chave: `4-1-sala-ao-vivo-por-websocket-snapshot-e-atualizações`.
Épico 4 — Sala ao vivo e encerramento. Criação: 27/10/2026.
Modelo solicitado: GPT-6.1 Sol Medium. Trabalho exclusivamente documental.

> Registrei recomendações concretas para D1–D10. Elas não representam aprovação
> do dono. Q2 e Q10 são decisões explicitamente reservadas a ele em `CLAUDE.md`
> e `docs/ARQUITETURA.md`; não as fechei por inferência. Por isso não marquei
> `ready-for-dev`, não iniciei o épico no sprint e não alterei nenhuma AD.

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

### D1 — Rota WebSocket (Q10; aprovação humana pendente)

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

### D7 — Acesso público e Origin (Q2; aprovação humana pendente)

Recomendo `websocket_route(..., policy=AccessPolicy.PUBLIC)`. Visitante,
AUCTIONEER, BIDDER e cookie inválido recebem o mesmo estado público. Sem JWT na
URL, exigência de login, leitura de `users` ou identidade por socket. O alias do
histórico é o persistido; nenhum alias histórico é recalculado para publicar.

Para **Q2**, recomendo validar `Origin` contra `APP_ORIGIN` configurada, comparando
origem completa (esquema, host, porta normalizada), rejeitando estrangeiro,
malformado e `null`; aceitar ausência só para clientes não navegador, como na
infra técnica atual. Browser same-origin sempre envia Origin. Não usar `Host`
recebido como lista de confiança nem Referer como fallback improvisado do WS.

Alternativas humanas: exigir Origin também nos clientes não navegador (política
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

## 5. Critérios de aceitação da futura implementação

Os critérios abaixo adotam as recomendações e ficam condicionados à decisão de
rota/Origin; a consolidação deve substituir esses dois pontos se o dono escolher
alternativas.

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
- [ ] Obter decisão humana somente para Q10/rota e Q2/Origin; consolidar docs.
- [ ] Criar spec autorizada: contrato final, coordenação handshake/publicação,
  ponte de threads, política de fila/limpeza e arbitragem REST/WS/201/privado.
- [ ] Submeter spec à revisão/aprovação humana conforme FRONTEND-WORKFLOW.
- [ ] Build autorizado: B1–B10 e manager/endpoint/writers pós-commit (CA1–9).
- [ ] Integrar frontend/proxy e F1–F4 (CA10–12).
- [ ] I1/I2, verify e documentação com evidência real (CA13–14); parar na 4.1.

Não executei essas tarefas de implementação nem criei spec nesta sessão.

## 11. Questões humanas realmente abertas

Somente duas decisões bloqueiam a consolidação da story para spec:

1. **Q10 / D1 — rota final:** aprovar `/ws/lots/{lot_id}` (recomendada), ou
   `/api/lots/{lot_id}/ws` (alternativa). Efeito: nome público, proxy e reserva de
   fallback; custo semelhante e baixo. Nenhuma rota de sala já existe para migrar.
2. **Q2 / D7 — Origin:** aprovar origem presente igual à `APP_ORIGIN` e ausência
   aceita para clientes não navegador (recomendada); ou exigir sempre; ou aceitar
   qualquer origem no stream público. Efeito: compatibilidade de scripts e
   exposição de uso cruzado; custo baixo. Sempre sem autenticação pelo cookie.

Não reabro posição do usuário, regra anti-sniping, locks, aliases, outbox ou
decisões financeiras. Q1 (intervalos/heartbeat/reconexão) pertence à 4.2 e não
bloqueia a 4.1; Q4/Q6/Q9 de fechamento pertencem à 4.4.

## 12. Definition of Done e conclusão desta criação

Para a futura implementação: duas abas no mesmo lote; lance exclusivamente REST;
commit concluído; outra aba recebe WebSocket e altera lance atual, histórico e
novo `ends_at` se houve anti-sniping, sem refresh manual, sem dados privados e
sem regressões da 3.5. Heartbeat e reconexão não fazem parte desse DoD.

Nesta criação, preenchi requisitos, contexto vivo, contrato recomendado,
alternativas, critérios, tarefas, arquivos, concorrência, privacidade e plano de
validação com base no checklist de create-story. Nenhuma implementação, teste,
verify, consulta ao banco, deploy, Git, leitura `.env*` ou alteração de secrets.
O sprint permanece `backlog`; criação documental não significa pronta para dev.

**Resultado: PRECISA DE DECISÕES (Q2 e Q10).** Após as respostas, consolidar estas
recomendações e registrar **PRONTA PARA SPEC**, sem iniciar implementação por
essa mudança de rótulo.

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
