# Decisões humanas finais — Story 4.5

Consolidei QH-01–13 pela instrução humana de 28/10/2026. Nenhuma questão aberta.
O pedido autoriza consolidação e build sequenciais sem nova confirmação, após
validação documental e ausência de conflito AD. Recomendações do draft ficaram
superadas pelas decisões abaixo; memória histórica preservada sem reescrita.

| ID | Decisão final | Alternativa descartada |
| --- | --- | --- |
| QH-01 | Listagem atual, sem detalhe novo. | detalhe/ambos |
| QH-02 | Estender somente GET /api/lots/mine, preservar campos atuais e atualizar consumidores atomicamente; envelope atual as_of/items confirmado. | endpoint separado/combinação redundante |
| QH-03 | SOLD alias/final_amount_cents/bid_count/settled_at, sem final_hash no painel/DTO. | hash técnico |
| QH-04 | Sem receipt/referência/link/botão; compartilhável fica5.2. | receipt/link/indicador |
| QH-05 | Fetch montagem, botão Atualizar e refetch de focus/retorno, deduplicados. | somente manual ou WS |
| QH-06 | Sem polling, interval ou timer de 10 s. | polling10s |
| QH-07 | Preservar created_at DESC, id DESC, settlement não move lote. | reordenar após settlement |
| QH-08 | Sem filtros/tabs/busca/analytics. | filtros novos |
| QH-09 | Agendado, Ao vivo, Encerrado, apurando resultado, Vendido, Sem arremate, Cancelado. | cancelled igual a unsold |
| QH-10 | Somente winner_alias; sem user_id/email/nome real/wallet/HMAC/segredo. | identidade privada |
| QH-11 | Inconsistência falha integralmente sem repair/dados parciais; reutilizar conflito tipado existente quando aplicável. UI erro inicial e snapshot+stale em refresh falho. | lista/total parcial ou repair |
| QH-12 | Contagem na linha, fonte atual antes e settlement congelado depois; sem contar DOM. | count só no detalhe ou calculado no frontend |
| QH-13 | Total recebido soma backend INTEGER cents dos sold próprios, exclui scheduled/live/pending/unsold/cancelled/alheios; mesmo snapshot lógico da lista, frontend só formata BRL. | retirar soma ou somar bids/receipt/frontend |

## Consequências vinculantes

Lista/total pertencem ao mesmo snapshot. Inconsistência do par/Lot usa conflito tipado
existente quando aplicável (409 lot_integrity_conflict); falha operacional continua
500 genérico. Nenhuma identidade privada, hash ou receipt entra na resposta.
Montagem/manual/foco compartilham coordenação para não abrir leituras duplicadas;
sem timer ou nova infraestrutura. Sem edição de lote atual a ampliar.

Concluo build em Story/sprint review, SPEC in-review e Epic 4 in-progress.
Não executo Git, leio .env*, inicio Epic 5 ou faço code review nesta sessão.
