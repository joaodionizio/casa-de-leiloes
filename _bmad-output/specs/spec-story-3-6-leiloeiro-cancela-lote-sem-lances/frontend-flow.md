# MyLots e adaptação mínima da sala

Decidi ampliar a lista densa atual, preservando miniatura, obra, datas, valores e
tokens ÁTRIO. Descartei cards grandes, framework de modal, redesign ou dependência
nova. `DESIGN.md`/`EXPERIENCE.md` continuam vinculantes.

## 1. Cliente e lógica pura

Em `api/lots.ts`, mantenho `LotResponse` e criação intactos. Acrescento
`MyLotResponse extends LotResponse` com `cancelled_at:string|null`,
`bid_count:number`, `phase:'scheduled'|'live'|'ended'`; `MyLotsResponse` com
`as_of:string`, `items:MyLotResponse[]`. `fetchMyLots` retorna no ramo ok também
`as_of`, preservando `items` e classificações atuais de falha. Guards exigem
timestamp válido com fuso, enum fechado, count inteiro seguro >=0, presença dos
campos nullable e os campos atuais. Não trato contrato antigo sem as_of como lista
vazia nem como sucesso. Tipos simples, sem mapped types.

`cancelLot(lotId)` executa um fetch `POST /api/lots/${encodeURIComponent(lotId)}/cancel`,
credentials same-origin e header JSON, corpo ausente. Valido 200 como objeto com
`id` do lote solicitado e `cancelled_at` não nulo, timestamp UTC válido. Uma forma
200 inválida/ID divergente é ambígua; não atualizo item otimisticamente. Tipos:
`CancelLotResponse` (`id`, `cancelled_at`) e `CancelLotResult` discriminado ok/failure.

`lotCancellation.ts`, puro/sem DOM, concentra `canCancelLot`, classificação de
status+code e textos. `canCancelLot` exige cancelled_at null, bid_count zero e
phase scheduled/live. Não calcula fase pelo browser, não autentica count e não
bloqueia por suposição sobre âncora. Backend continua autoridade.

| Resposta classificada | Texto/ação |
| --- | --- |
| 200 válido | “Lote cancelado.”; uma releitura MyLots |
| 422 lot_has_bids | “Este lote não pode ser cancelado porque já recebeu lances.”; uma releitura |
| 422 lot_ended | “Este lote já foi encerrado.”; uma releitura |
| 409 lot_integrity_conflict | Frase neutra do contrato HTTP; não afirmar cancelamento |
| 403 forbidden | “Você não pode cancelar este lote.” |
| 404 not_found | “Lote não encontrado.” |
| 401 | Callback onSessionExpired atual, cancelar fluxo privado local |
| Rede/5xx/status inesperado/corpo inválido ou código não reconhecido | Ambíguo: “Não foi possível confirmar o cancelamento. Confira a lista atualizada antes de tentar novamente.”; uma releitura, sem POST adicional |

Não uso message do servidor para decidir nem mostrar detalhe. Para 403 csrf/415,
não confundo com forbidden de ownership; sigo falha genérica conservadora sem
inferir resultado nem novo envio. Se a releitura ambígua também falhar, texto:
“Não foi possível confirmar o cancelamento nem atualizar a lista. Recarregue Meus
lotes e confira antes de tentar novamente.” Não faço loop. No sucesso confirmado
com refetch falho, preservo “Lote cancelado.” e acrescento “Não foi possível
atualizar a lista.”; não inverto o resultado do POST.

## 2. Lista, confirmação e envio

MyLots guarda lista e as_of do servidor. Cada item mostra estado temporal ou,
prioritariamente quando cancelled_at não é null, selo textual **Cancelado**. Não
transformo phase, removo item cancelado da lista ou apresento resultado final.
Exibo bid_count como quantidade de lances, com texto singular/plural; datas usam
`formatDateTime` e o fuso de apresentação existente.

CTA “Cancelar lote” só em item aparentemente elegível. Clique abre confirmação na
mesma linha: “O lote sai da vitrine e não pode ser reaberto.”, botões “Confirmar
cancelamento” e “Voltar”. Abro uma confirmação por vez e foco o botão Confirmar;
Voltar fecha e devolve foco ao CTA da linha. Sem portal/modal/framework novo.

Ao confirmar, uma ref síncrona de envio é marcada **antes** do primeiro await;
clique/Enter repetidos não iniciam segundo POST. Enquanto pendente, desabilito as
ações de cancelar/confirmar/voltar da lista, texto “Cancelando…”. A opção simples
é um envio pendente para toda a montagem de MyLots; não crio fila genérica nem
registro persistente. Nenhum retry automático, timeout com reenvio ou POST em efeito.
Não prometo deduplicação entre abas/reload; o servidor mantém a idempotência por lote.

Em sucesso, fecho confirmação, preservo região `role=status` com aviso, releio
MyLots uma vez e foco o título. Item vem novamente com Cancelado. Falha business
usa `role=alert`; has_bids/ended releem para atualizar elegibilidade. 409 não vira
sucesso nem inicia repair; pode manter lista e permitir ação manual posterior.
Em ambíguo, uma releitura mostra o estado atual, mas não declara retrospectivamente
o resultado do POST; selo Cancelado pode aparecer se confirmado no read model.

O fetch de lista mantém AbortController e descarta respostas abortadas/antigas;
invalido a leitura anterior ao POST para impedir que um snapshot antigo apague o
cancelamento após refetch. On unmount, descarto updates e callbacks de requests
antigos; não trato abort de leitura como prova de que o POST não gravou. A
autorização da rota da aplicação continua a existente, sem ler sessão nova.

Região de status permanece montada durante refetch; falha da lista não apaga aviso
de sucesso confirmado. Controles semânticos, labels por obra quando houver vários
botões iguais, foco visível, alvos ~44px; 320px sem overflow. Com 50 registros uso
a lista densa existente, sem paginação ou reprodução de imagem grande por item.

## 3. Sala da 3.5

Único delta de comportamento frontend na sala: acrescentar `lot_cancelled` a
`KnownBidFailure` e BUSINESS_CODES em `api/bids.ts`, e ao REFUSAL_TEXT em
`bidFeedback.ts`: **“Este lote foi cancelado.”**. Reutilizo o tratamento atual
de recusa e a rodada de atualização já existentes. Não altero LotPage/runRound,
countdown, barreira de envio, WebSocket, polling ou outras mensagens da 3.5.
O GET público agora 404 é aplicado no backend; o comportamento atual da sala para
recurso indisponível continua válido. Sala já aberta não recebe evento automático.
