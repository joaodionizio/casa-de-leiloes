# Revalidação final da especificação — 27/10/2026

## Veredito e alcance

Coerência e preservação revalidadas; contrato pronto para desenvolvimento, sem autorização de código. Todas QH-01–10 foram decididas explicitamente pelo usuário, não pela autovalidação. Preservo CAP-1–5. Esta conferência de coerência/preservação exigida por bmad-spec não é review independente, execução de aplicação ou aceite de implementação. Ready-for-dev registra a especificação consolidada; o usuário ainda proíbe código nesta sessão.

## Passagem 1 — Coerência (Spec Law)

| Regra | Conferência final | Resultado |
| --- | --- | --- |
| 1. Intent/success | CAP-1–5 com ambos os campos, critérios observáveis e testes mapeados | Atendida |
| 2. WHAT/HOW | Kernel descreve resultados; sequência SQL/schema/retornos nos companions | Atendida |
| 3. Constraints | Clock pós-lock, ordem, conservação/teto, cardinalidade, gate e limites de escopo excluem alternativas concretas | Atendida |
| 4. Non-goals | HTTP/WS/UI/gatilhos 4.4/painel 4.5 e 5.x explicitamente fora | Atendida |
| 5. Sinal de sucesso | CA01–21/PG01–35 permitem demonstrar efeitos únicos/atomicidade | Atendida como plano; execução só no build |
| 6. IDs | CAP-1–5 estáveis; CA01–18 e PG01–24 preservados, novos IDs sequenciais | Atendida |
| 8. Prosa | Kernel enxuto; detalhes por conteúdo; decisões superadas só como alternativas descartadas/memória | Atendida |

Conferi especialmente os seguintes pontos de coerência:

- Settlement e receipt têm **id próprio**, sem manter a recomendação anterior de lot_id como única PK. UNIQUE(lot_id) nos dois e UNIQUE(settlement_id) no receipt são explícitos.
- winning_bid_id conceitual está adaptado à PK composta real de bids por winning_bid_sequence + lot_id, sem nova coluna em bids/canônico. FK composta do receipt ao settlement impede vinculá-lo ao lote errado.
- HMAC e winner_user_id só no settlement interno; a proibição no receipt vale ao schema, DTO e retorno, não apenas à projeção pública. Não há nova API.
- Quatro statuses de sucesso/não transição são distintos de falhas tipadas; comando possui Session/commit, helper não tem transitioned. Nenhum consumidor recebe true antes da confirmação.
- Ramo idempotente precede not_due para não mascarar terminal adulterado, revalida gate e coerência, sem tentar consumir de novo a reserva já liquidada. Sold sem receipt e unsold com receipt falham sem repair.
- Unsold tem settlement com quatro NULL e nenhum preço zero fictício/receipt. Phase e contratos públicos permanecem intactos; pending deriva da ausência do settlement.
- A_W permanece igual, reservas alheias e perdedores são preservados, ΣT constante; teto não muda. Falha financeira aborta todas as linhas e não vira sucesso idempotente.
- CHECKs locais não prometem cardinalidade condicional entre tabelas; serviço/transação/revalidação/testes garantem sold com exatamente um receipt e unsold com zero. PG33 isola inconsistência sem falhar antes por FK irrelevante.
- Distingo COMMIT abortado de ACK perdido: no segundo caso, retry descobre settlement confirmado sem nova transferência. Não certifico rollback apenas porque o chamador recebeu erro.

## Passagem 2 — Preservação (Spec Law 7)

| Direção humana/AD | Contrato final | Testes/critério |
| --- | --- | --- |
| QH-01 interno, sem rota e gatilhos somente 4.4 | transaction-contract fronteira; SPEC Non-goals | CA21/U03/R05 |
| QH-02 settlement próprio, IDs/UNIQUE e sold/unsold econômico autoritativo | data-contracts lot_settlements, financial-invariants | CA01/02/09, PG12/27 |
| QH-03 receipt distinto, ID próprio/UNIQUE lote+settlement, só sold e campos seguros | data-contracts receipts | CA09/13/14, PG28/29 |
| QH-04 readers internos por lote, sem API | data-contracts readers | CA15/21/U04 |
| QH-05 quatro resultados, true só pós-commit, retry false e falhas tipadas | data-contracts serviço; transaction-contract | CA16/19, U03/PG20/34 |
| QH-06 HTTP não aplicável; orientação futura 200/200 | human-decisions QH-06 | H01/H02 retirados, R05 |
| QH-07 pending/settled + sold/unsold separados de phase; zero WS/UI | data-contracts estados; SPEC Non-goals | CA21/R01/R05 |
| QH-08 teto → rollback/conflito; condição operacional sem retry quente futuro | financial-invariants; transaction-contract falhas | CA19/PG10/30 |
| QH-09 histórico autenticado, âncora interna congelada e receipt sem HMAC, v1 intacto | data-contracts integridade/schema | CA12/13/14, PG13/14/29, R03 |
| QH-10 coerência de repetição e zero reparo/reliquidação | transaction-contract ramo idempotente | CA20/PG23/31/32/33 |
| Financeiro: A=T−C, W T−F/C−F, S T+F/C igual, conservação/perdedores/outros lotes | financial-invariants equações e tabela 1–8 | CA10/PG09/25/26 |
| Locking: lote/clock/fim/settlement/gate/carteiras/liquidação/inserts/commit | transaction-contract passos 1–16 | CA03/04/07, PG04/07/20 |
| Lance primeiro estende E+2min; closer relê e não fecha futuro | concurrency-model lance primeiro | CA04/05, PG05/35 |
| Closer primeiro depois do fim impede reabertura | concurrency-model fechamento primeiro | CA06/PG06/24 |
| Dois closers: segundo vê/revalida settlement, uma economia/linha/receipt | concurrency-model dois closers | CA07/PG07/28 |
| Falhas no meio/INSERT receipt/COMMIT e confirmação perdida | transaction-contract falhas; concurrency-model | CA11/16, PG11/22/34 |
| Onze testes adicionais explícitos | acceptance-and-tests PG25–35, um por requisito humano | CA10/13/14/19/20 e PG25–35 |
| Pedido original: vazio/ativo/legado/privacidade/leituras puras/rollback | data-contracts, transaction-contract, financeiro | CA01–17, PG01–24 preservados |
| AD-5/6/7/8/9/13/17/19/20/21/25/26/30 | SPEC Constraints e companions técnicos | Plano PG real/barreiras e regressões R01–R03 |
| Atualizar story/sprint só após revalidação; IA, sem código/Git/.env*/4.4 | Story, sprint, uso_de_ia e memória | D01, conferência estática final |

Todos os onze novos cenários humanos têm prova explícita PG25–35; manter PG01–24 não foi considerado suficiente por si só. H01/H02 condicionais de API saíram do plano conforme decisão humana, não por lacuna de cobertura.

### Wrapper-only content

Nenhum requisito funcional descartado. Nome transitório do anexo/marcadores de entrega são embalagem; decisões foram absorvidas, sem dependência externa do attachment. Memória, README, sprint e registro de IA permanecem metadados de processo fora de companions/sources; arquitetura/UX necessários continuam companions adotados.

## Conferências executadas e limites

Resolvi configuração/customização BMAD com cache uv em /private/tmp e sem hooks adicionais; retomei memória existente e acrescentei decisões pelo writer oficial. Conferi referências locais/companions, CAP/QH/CA/PG, campos/regras finais, ausência de propostas condicionais de API e tracking, preservação do corpo anterior da memória e hashes de arquivos de aplicação/testes selecionados na partida.

Não executei pytest, verify, Playwright, SQL, migrations, navegador, smoke, deploy ou Git; não li .env*. Nenhum código de aplicação/testes foi alterado; nenhum teste listado no plano foi executado. As referências PostgreSQL do companion de concorrência foram consultadas na criação, não são nova prova de execução. Review independente do futuro código e autorização de build continuam separados desta prontidão documental.
