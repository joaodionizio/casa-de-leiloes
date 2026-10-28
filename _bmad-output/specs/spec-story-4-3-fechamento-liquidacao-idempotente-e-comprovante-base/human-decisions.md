# Questões para decisão humana — decisões consolidadas

**QH-01–QH-10 DECIDIDAS pelo usuário em 27/10/2026. Nenhuma questão humana aberta da Story 4.3.** Registro as escolhas e as alternativas descartadas. As novas instruções substituem as recomendações do draft; a memória mantém o histórico append-only. Ready-for-dev não autoriza código nesta sessão.

## QH-01 — DECIDIDA: invocação interna

Decidi expor somente serviço interno de fechamento/liquidação, chamado diretamente pelos testes. Descartei nova rota HTTP manual/pública/privada e ações implícitas em GET/HEAD/OPTIONS/handshake. A 4.4 terá gatilhos operacionais/automáticos e publicação após commit; não os implemento agora.

## QH-02 — DECIDIDA: settlement econômico próprio

Decidi lot_settlements 1:1 com lote, **id próprio** e **lot_id UNIQUE**, para sold e unsold. Existência commitada significa apuração concluída; settlement é registro econômico autoritativo. Mínimos: id/lot_id/outcome, winner_user_id/alias/winning_bid_id/F nullable só unsold, count/hash, cópia interna da âncora HMAC validada e settled_at. Descartei colunas de resultado em lots e a recomendação anterior de usar lot_id como única PK sem id próprio. Unsold não inventa vencedor ou preço.

## QH-03 — DECIDIDA: receipt separado e seguro

Decidi receipts apenas para sold, id próprio, lot_id UNIQUE e settlement_id UNIQUE, referência winning bid, alias/F/settled_at/count/hash. Descartei usar settlement como receipt, omitir id próprio, pôr winner_user_id/HMAC em qualquer coluna do comprovante, duplicar snapshot da obra ou adicionar link/token da 5.2. Metadados públicos permanecem em lots. Campos finais em data-contracts.md.

## QH-04 — DECIDIDA: readers internos

Decidi readers internos por lot_id para recuperar settlement e comprovante existente. Descartei GET privado/público novo; reader não cria registros ou liquida implicitamente. Não há API/rota nova nesta story.

## QH-05 — DECIDIDA: discriminação e confirmação

Decidi resultado discriminado para nova sold, nova unsold, já liquidado e ainda não elegível. Detalhei statuses settled_sold/settled_unsold/already_settled/not_due; transitioned=true só depois de commit confirmado de nova liquidação. Repetição válida devolve dados persistidos com false e sem escrita. Falhas financeiras/de integridade são falhas de domínio tipadas, fora dos sucessos; descartei sucesso idempotente cego ou DTO de sucesso entregue após mero flush. Helpers provisórios não expõem transitioned.

## QH-06 — DECIDIDA: HTTP não aplicável

Decidi não criar HTTP na 4.3. Registro apenas preferência futura: se existir API explícita de fechamento, HTTP 200 tanto para nova transição quanto repetição, diferenciadas pelo corpo. Descartei implementar rota ou status agora; não há testes de nova API pendentes desta decisão.

## QH-07 — DECIDIDA: eixo independente de phase

Decidi settlement status conceitual pending/settled, com outcome sold/unsold quando settled. Descartei expandir phase ou alterar WS, room_snapshot, bid_accepted, máquina 4.2, UI da sala e painel nesta story. Stories futuras consumirão resultado persistido; fim sem settlement mantém “Encerrado, apurando resultado”.

## QH-08 — DECIDIDA: teto preservado e rollback total

Decidi conflito financeiro tipado com rollback completo se crédito viola teto/invariante: nenhum débito, liberação parcial, crédito, settlement ou receipt. Descartei aumentar/ignorar/contornar teto, mudar regra financeira, saturar crédito ou criar contabilidade alternativa. A 4.4 deve tratar a condição operacional sem retry quente infinito; o mecanismo não é escopo da 4.3 nem questão humana pendente dela.

## QH-09 — DECIDIDA: integridade interna congelada

Decidi autenticar histórico existente antes de liquidar e congelar count/final_hash/âncora HMAC validada/winning bid no settlement. Receipt pode portar referência do bid/count/hash, **nunca HMAC**. Descartei referência mutável sem cópia da âncora, reassinatura de legado e alteração de canonical bid v1. Não crio assinatura própria do receipt ou segredo novo.

## QH-10 — DECIDIDA: revalidar repetição

Decidi revalidar coerência entre lote, settlement, receipt obrigatório em sold/ausente em unsold e referências de integridade antes de sucesso idempotente. Inconsistência falha com IntegrityConflict: sem reparar, sobrescrever, recriar, reliquidar ou alterar carteiras. Descartei confiar na mera existência do terminal e não confiro reserva como se ainda não tivesse sido consumida.

## Adaptações técnicas vinculadas às decisões

winning_bid_id é a identidade conceitual do lance. Como bids tem PK (lot_id,sequence), adapto para winning_bid_sequence mais lot_id e FK composta, sem novo bids.id ou mudança de canônico. IDs próprios UUID em settlement/receipt respeitam a decisão humana; a referência do comprovante não é identidade privada do usuário.

Comando interno é dono único de sua Session/commit; helper sem sucesso público provisório preserva o padrão de composição do Epic 3. Essas adaptações usam a autorização de ajustar nomes/tipos às convenções, sem modificar a semântica decidida. Contratos e plano de testes registram os detalhes, não deixam alternativas abertas.

Scheduler/catch-up/evento (Q1/Q4/Q6/Q9 históricas) e rotas do comprovante/link permanecem para suas stories posteriores. Não são bloqueios pendentes da 4.3 e não autorizam antecipação.
