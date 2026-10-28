# Estado atual e mapa de implementação provável

Registrei o estado por leitura estática em 28/10/2026, sem executar aplicação.
Separo observação de proposta; leio as evidências antigas como históricas.

## Painel e contrato privado atuais

| Fonte viva | Observação |
| --- | --- |
| `frontend/src/MyLots.tsx` | `/auctioneer/lots`, lista densa com miniatura/título/artista, fase textual, contagem, início/fim, lance inicial/incremento e cancelamento inline |
| `frontend/src/api/lots.ts` | `MyLotResponse = LotResponse + cancelled_at, bid_count, phase`; envelope `{as_of, items}`; valida fase/contagem/data; fetch same-origin abortável |
| `backend/app/lots.py` | `GET /api/lots/mine`, policy AUCTIONEER/require_auctioneer; filtro pelo user.id autenticado, inclui cancelados; `no-store` |
| `my_lots_statement/read_my_lots_snapshot` | Clock CTE MATERIALIZED + LEFT JOIN por ownership, um statement, sem lock/escrita; sem paginação/limite; ordem created_at DESC, id DESC |
| `MyLots.readList` | Leitura ao montar/abrir, retry de erro inicial e refetch após certos retornos do cancelamento; sem refresh geral/foco/polling/WS |
| Refs de leitura | AbortController + seq + mountedRef descartam leituras substituídas; refresh falho conserva lista no fluxo de cancelamento |
| `lotPhase.ts` | Labels atuais Agendado/Ao vivo/Encerrado; `phaseStatusText` já usa Encerrado, apurando resultado em outras telas |
| `lotTime.ts`, `money.ts` | UTC recebido é mostrado em pt-BR no fuso do navegador, com indicação de fuso; BRL por conversão textual exata de cents |

O painel não recebe settlement/receipt, alias vencedor, valor final ou total vendido.
Um ended aparece apenas como Encerrado no MyLots atual; não confundo essa tela com
a frase transitória usada na sala. O as_of é validado no cliente, mas o MyLots não o
armazena no seu estado nem exibe linha de atualização. Não localizei edição de lote
ou rota privada de detalhe de resultado; criação e cancelamento existem.

## Persistência e readers

`backend/app/lot_settlement.py` contém LotSettlement (sold/unsold, UNIQUE lot_id) e
Receipt separado (somente sold, UNIQUE lot_id/settlement_id). Settlement guarda
identidade interna/HMAC que não pertencem ao novo DTO. Receipt é prova base, não
fonte substituta do resultado e não link público.

`read_settlement` e `read_receipt` usam `_read_pair` num statement por lote e
`_structural_conflict`: sold exige receipt e cópias coincidentes; unsold exige ausência
de receipt, vencedor/valor/seq nulos e count zero/genesis; receipt órfão é conflito.
Esses readers não verificam sozinhos cancelled_at, prazo ou equivalência com Lot.
Não recomendo invocá-los N vezes na listagem.

`backend/app/bids.py`, `public_room_statement/read_public_room` (4.4), demonstra a
composição em statement único com projeções internas e checks de Lot contra par.
Confere count/hash/current bid/current leader e settled_at >= ends_at. A projeção
pública inclui final_hash; isso não obriga o DTO privado do painel a incluí-lo.
Não recomendo chamar /bids por linha, carregar janela de bids ou copiar o DTO público
inteiro para satisfazer o painel.

A 4.4 publica lot_closed só após nova transição confirmada e atualiza a sala. Não
existe assinatura do painel; catch-up/scheduler permanecem seus produtores únicos.
Read model não executa o gate financeiro/criptográfico nem certifica auditoria.

## Evidência e discrepâncias preservadas

- Stories 4.3/4.4 e specs estão done; Epic 4 in-progress.
- O pedido informa 4.1/4.2 concluídas, mas o sprint ainda registra review. Não alterei essas stories: não há autorização para reconciliação fora da 4.5.
- `epics.md` 4.5 exige total recebido. Registrei QH-13 e o usuário decidiu manter soma simples de vendidos; preservei a exigência no draft sem criar analytics.
- Não reutilizo contagens históricas de testes como novas execuções.

## Testes existentes e pontos de extensão futura

`backend/tests/integration/test_my_lots.py` prova ownership, query string sem autoridade,
ordem/desempate, lista sem limite (101 lotes), contrato exato, AIC ausente, SELECT puro,
401/403 e métodos não suportados. `test_lot_cancellation*`, `test_lot_settlement*` e
`test_bid_reads.py` fornecem regressões de cancelamento, par persistido e leitura pública.
`backend/tests/test_access_policy.py` e `tests/access_policy.py` verificam políticas.

`frontend/src/api/lots.test.ts` testa contrato/fetch; `lotCancellation.test.ts`,
`lotPhase.test.ts`, `lotTime.test.ts`, `money.test.ts` cobrem lógica pura.
`frontend/e2e/my-lots.spec.ts` cobre DOM, cancelamento, foco, erros, empty state,
requests e 320px com API simulada; `e2e/support/mockApi.ts` é o harness. O projeto
usa node:test sem DOM e Playwright Chromium; não há necessidade comprovada de
nova dependência para testes de componente.

## Mapa do build aprovado

| Arquivo | Mudança provável futura |
| --- | --- |
| `backend/app/lots.py` | DTO privado, leitura em lote e projeção; soma simples QH-13 |
| `backend/app/lot_settlement.py` | Somente eventual extração/reuso de validador estrutural puro; preservar comando financeiro |
| `backend/tests/integration/test_my_lots.py`, `test_my_lots_results.py` | Estado/whitelist/queries/pureza/total e ownership |
| `backend/tests/test_openapi.py`, `tests/access_policy.py` | Ajustar contratos exatos/políticas somente se afetados |
| `frontend/src/api/lots.ts`, `.test.ts` | Contrato privado e validação em runtime |
| `frontend/src/MyLots.tsx` | Resumo/total, erros e estratégia aprovada de refetch |
| `frontend/src/lotPhase.ts` ou helper próprio | Mapeamento privado de resultado sem alterar labels públicos por acidente |
| `frontend/src/App.css` | Estender estilos existentes se necessário |
| `frontend/e2e/my-lots.spec.ts`, `e2e/support/mockApi.ts` | Sold/unsold/pending/refresh/total e regressões |
| `README.md`, story, spec, sprint, `docs/uso_de_ia.md` | Documentar comportamento aprovado e evidência real no build |

Não planejo migration, rota de settlement/receipt, edição, scheduler, auth nova,
wallet, bids, sala, WebSocket ou início de outra story. O pedido humano atual autoriza este build após consolidação.

## Estado entregue

A tabela de observação acima é a baseline anterior ao build. A entrega final estende
a mesma listagem; detalhes e prova executada em implementation-evidence.md.
Não adicionei edição de lote, migration, rota, dependência ou mecanismo financeiro.
