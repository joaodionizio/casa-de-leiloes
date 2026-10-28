# Contrato final de evento e snapshot terminal

Decidi QH-04/05/06/15 e preservei Origin/rota pública da 4.1, gerações da 4.2 e
send/close 10 s. O transporte não liquida, calcula vencedor ou consulta identidade privada.

## Evento lot_closed: whitelist exata

| Campo | Tipo/regra | Origem |
| --- | --- | --- |
| type | literal lot_closed | Discriminante final |
| lot_id | UUID string do lote da conexão | Resultado confirmado |
| outcome | sold ou unsold | Settlement persistido |
| winner_alias | string padrão Licitante- + 16 hex maiúsculos; null em unsold | Alias persistido, sem recalcular do usuário |
| final_amount_cents | inteiro 1..9007199254740991 em sold; null em unsold | Valor persistido |
| bid_count | inteiro>0 em sold, 0 em unsold | Contagem congelada |
| final_hash | 64 hex minúsculos, genesis de 64 zeros em unsold | Hash congelado |
| settled_at | ISO 8601 UTC, precisão persistida até 6 casas, Z | Instante autoritativo pós-lock da liquidação original |
| as_of | Mesma serialização/instante de settled_at | Cópia derivada do instante já persistido, sem clock novo |

As nove chaves acima são obrigatórias e exclusivas, incluindo nulls explícitos.
No evento, as_of == settled_at; não uso tempo de publish, relógio da aplicação,
novo clock_timestamp ou novo instante de domínio. Essa igualdade não torna
settled_at um relógio de publicação ou versão de commit. Retry não altera instante.

Construo evento somente de settled_sold/settled_unsold com transitioned=true
após commit confirmado. not_due, already_settled, recusa, conflito ou exceção
não geram lot_closed. Hash público é referência, sem afirmar auditoria 5.1.
Proibidos winner_user_id, bidder_id, auctioneer_id, e-mail, wallet/saldos,
anchor_hmac/HMAC, segredos, objeto ORM, ReceiptRecord ou share token. Projeção
explícita, sem dump automático de SettlementRecord e sem joins com users/wallets
para montar o evento. Unsold não inventa preço zero, alias ou receipt.

## Snapshot compartilhado REST/WS

Decidi manter `{type: room_snapshot, lot_id, room}` e estender o mesmo
PublicBidRoomResponse de GET /api/lots/{id}/bids e de bid_accepted somente com:

| Campo em room | Contrato final |
| --- | --- |
| settlement_status | pending ou settled, derivado da existência confirmada, sem coluna redundante |
| settlement | null quando pending; quando settled, objeto público com outcome, winner_alias, final_amount_cents, bid_count, final_hash, settled_at, mesmas regras do evento |

room.as_of continua sendo o instante PostgreSQL **da leitura completa**, no
mesmo statement do lote/janela/settlement; não o substituo por settled_at nem
pelo as_of do evento. A cópia de as_of no evento é suficiente para seu contrato;
o objeto settlement do snapshot não duplica esse campo. Sem novo endpoint.
Preservo os demais campos de room, janela 50, mínimo e nulabilidades existentes.

Leio projeções públicas e coerência estrutural relacionada em um statement com
clock materializado, sem anexar dois readers READ COMMITTED independentes.
Reuso/componho regras estruturais dos readers 4.3 sem mover finanças/gate para
leitura. Reader não faz lock/escrita, repair, commit ou validação criptográfica
nova. Conflito estrutural dá falha genérica/log seguro, não resultado inventado.

| Estado persistido | phase | settlement_status / settlement | Comportamento |
| --- | --- | --- | --- |
| Sem settlement, futuro/ao vivo | scheduled/live | pending / null | Sala não terminal |
| Vencido sem settlement | ended | pending / null | Encerrado, apurando resultado; leitura não liquida |
| Settlement sold | Temporal, normalmente ended | settled / sold com alias e valor | Terminal econômico |
| Settlement unsold | Temporal, normalmente ended | settled / unsold com alias/preço null | Terminal sem vencedor |
| Cancelado | Não exposto em snapshot público novo | Sem snapshot, REST404/handshake recusado | Conectados recebem lot_cancelled, como na 4.1 |

Não crio phase sold/unsold/cancelled ou exposição nova de cancelado. Settlement
existente nunca autoriza reabrir lote se termos temporalmente incoerentes; uma
leitura pública não se apresenta como auditoria integral ou reparo de dado adulterado.

## Manager e drenagem

Publicação terminal, subscribe e sinais de lance/cancelamento compartilham
coordenação por lote no loop do manager. Só a execução que confirmou transição
solicita lot_closed. Estado terminal local impede mensagens tardias de desfazer
o resultado enquanto a entrada da sala vive; após limpeza/restart, banco decide.
Não crio tombstones globais duráveis ou cache econômico que substitua o banco.

Em conexão existente, enfileiro terminal após commit e depois retiro assinante
de broadcasts. Sender único drena na ordem e fecha 1000 só após terminal. Não
aciono stopped antes da drenagem bem-sucedida, pois isso pode perder o frame.
Fila cheia/send timeout remove só cliente lento; sem rede sob lock de distribuição
ou financeiro. Send/close mantêm deadline 10 s, sem substituição por 2 s.

Em conexão nova settled, leio persistido, aceito e envio room_snapshot terminal
como primeira mensagem de dados, depois close 1000; não registro para broadcasts
posteriores nem recuso antes do snapshot. Nunca chamo settle_lot no handshake.
Corrida de inscrição vê pending seguido de terminal ou snapshot terminal,
sem janela de registro tardio que perca uma publicação concluída normalmente.
Se sinal de bid atrasado já lê settled, seu snapshot pode convergir o cliente,
sem fabricar outro lot_closed. Terminal enfileirado não recebe broadcasts futuros.

## Falha viva de publicação

A task pós-commit é supervisionada, sem bloquear o processamento financeiro dos
próximos lotes e sem retry periódico. Em exceção, registro erro seguro, tento
marcar terminal/invalidar a sala e executar close/invalidation best-effort
**recuperável**, por exemplo 1011 na política existente. Nunca fecho como sucesso
terminal sem resultado entregue. Novo subscribe consulta persistido e converge.

A invalidação considera também inscrições pendentes: uma leitura antiga que
termina depois da falha não pode registrar socket pending silenciosamente;
deve observar marcador terminal/invalidação local e reler ou encerrar de forma
recuperável, mantendo a posse de seu worker/Session. Falha de invalidação também
é registrada, sem certificar recuperação imediata ou desfazer settlement.
Não imponho timeout 2 s de coordenação/isolamento nem declaro D-A resolvido.

## Cliente, arbitragem e compatibilidade

Adequo tipos/validação/parser, sameRoomState, arbitragem e máquina existente para
settlement. Dados pending→settled podem ter count igual; resultado terminal
prevalece mesmo com REST pending tardio e as_of maior. Identidade estável do
resultado usa lot_id/settled_at/outcome/final_hash; duplicata idêntica é inerte,
terminal divergente não substitui silenciosamente o conhecido.

Snapshot settled é entregue ao consumidor e torna a máquina terminal antes de
qualquer ping inicial ou retry; lot_closed da geração atual também encerra
heartbeat/reconnect/timers. Close 1000 sem resultado conhecido não prova settlement
e permanece recuperável. Pending preserva snapshot+pong para reset do backoff,
gerações aposentadas inertes, offline/online e deadlines já aprovados 4.2.

Evento esparso não inventa bids perdidos: uma releitura REST final pura pode
alinhar a janela se necessário, sem condicionar o terminal a ela. Falha mantém
resultado conhecido e só sinaliza histórico desatualizado. Snapshot terminal
inicial já é completo e dispensa essa releitura. Nenhuma operação de leitura
liquida. Dados públicos não limpam erros privados de mine/carteira nem calculam saldo.

Sem nova tela/UX de resultado, painel de vencedor, botão ou link; preservo obra,
histórico e estados existentes. Contratos novos backend/SPA devem ser publicados
juntos; abas antigas podem ignorar lot_closed e precisar refresh, pois o parser
legado não conhece o terminal. Não introduzo protocolo versionado/replay nesta story.
