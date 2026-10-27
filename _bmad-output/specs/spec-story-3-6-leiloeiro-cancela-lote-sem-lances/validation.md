# Preservação, evidências e veredito

Decidi separar a prontidão do contrato da comprovação de implementação. Descartei
atribuir testes históricos de outras stories a esta rodada. A validação abaixo é
a autovalidação requerida pela bmad-spec, não code review ou execução de build.

## Índice obrigatório dos 16 itens

| Item solicitado | Local do contrato |
| --- | --- |
| 1. Contrato HTTP exato | `http-contract.md` §§1–2,4 |
| 2. Migration 0006 | `database-and-reads.md` §1 |
| 3. Fluxo transacional | `transaction-contract.md` §§1–2 |
| 4. Precedência de erros | `http-contract.md` §3 |
| 5. Concorrência | `transaction-contract.md` §4; `test-plan.md` §3 |
| 6. Integridade | `transaction-contract.md` §3 |
| 7. Leituras públicas | `database-and-reads.md` §2 |
| 8. MyLots/frontend | `database-and-reads.md` §3; `frontend-flow.md` §§1–3 |
| 9. Testes | `test-plan.md` §§1–3,5 |
| 10. Mutation plan | `test-plan.md` §4, M1–M8 do pedido e M9 adicional |
| 11. Arquivos previstos | `implementation-map.md` §1 |
| 12. Edge cases | `implementation-map.md` §3 |
| 13. Critérios refinados | `implementation-map.md` §2, AC1–AC12 |
| 14. Decisões abertas restantes | `implementation-map.md` §4: nenhuma |
| 15. Escopo | `SPEC.md` Non-goals; `implementation-map.md` §4: sem Epic 4 |
| 16. Veredito | Este arquivo e `implementation-map.md` §4: PRONTA PARA BUILD |

## Fontes e estado observado

| Fonte consultada | Conteúdo que vincula esta spec |
| --- | --- |
| Pedido `Texto colado.txt` da sessão; story final `../../implementation-artifacts/3-6-leiloeiro-cancela-lote-sem-lances.md` | D1–D7, algoritmo, 16 itens, casos/testes e limites; status ready-for-dev |
| `../../../CLAUDE.md`, `../../../docs/ARQUITETURA.md` | AD-6/7/8/11/13/19/24/26/29/30, autoridade temporal, gate, políticas, seed e limites operacionais |
| `../../planning-artifacts/epics.md` e `../../implementation-artifacts/deferred-work.md` | FR4/FR6, herança da trava/gate, filtro no ON, seed, separação de estorno/resultado |
| Story final 2.4 e `../spec-story-2-4-criacao-lotes/` | LotResponse/criação, MyLots owner-only, todos os itens e ordenação, seed offline idempotente, evolução aditiva |
| Story final 2.5 e `../spec-story-2-5-vitrine-publica/` | Fase temporal, CTE MATERIALIZED/LEFT JOIN e as_of no vazio, DTOs públicos, navegação e políticas |
| Story final 3.3 e `../spec-story-3-3-integridade-historico/` | Âncora v1, alias/cadeia canônicos, assinatura anterior obrigatória, nenhuma reassinatura de estado encontrado |
| Story final 3.4 e `../spec-story-3-4-lance-transacional/` | Gate real reutilizável, lock/populate_existing, clock pós-lock, commit da rota, READ COMMITTED e concorrência |
| Story final 3.5 e `../spec-story-3-5-dar-lance-pela-sala-do-lote/` | Leituras públicas/próprias distintas, status/code, envio/releitura e sala final sem redesign |
| `../../planning-artifacts/DESIGN.md`, `EXPERIENCE.md`, `VITRINE-BLUEPRINT.md`, `../../../docs/FRONTEND-WORKFLOW.md` | Lista densa, marca/obra, confirmação funcional, foco/teclado/mobile; nenhuma revisão global |
| `backend/app/{lots,bids,main,access,db,errors,csrf,seed,bid_rules}.py` (raiz do projeto) | Ausência atual de cancelamento, nomes/imports/SQL reais, validação/guards/headers e pontos exatos de composição |
| `backend/migrations/versions/{0003_lots,0005_bids}.py`, testes de lotes/lances/migrations/MyLots e suportes | Próxima revisão 0006, schema pinado, helpers reais, locks/eventos/barreiras e invariantes independentes |
| `frontend/src/{MyLots,LotPage}.tsx`, `api/{lots,bids}.ts`, `bidFeedback.ts`, testes/mockApi e package.json | Lista atual somente leitura, contratos concretos, mensagens locais e infraestrutura node:test/Playwright existente |

Fontes históricas preservam trechos de planejamento já superados: a 3.6 final e
D1–D7 prevalecem no escopo atual. Não reescrevi specs de outras stories. O quadro
do estado real em `implementation-map.md` fixa a base para o implementador; a
inspeção de arquivos não comprova migration aplicada, banco/deploy em execução
ou testes atuais passando.

Ajustes LOW da revisão (26/10/2026), só documentais: F-01 nota de README sobre 404 posterior ao `lot_cancelled`; F-02 M1 reformulada; F-03 filtro no JOIN só nas consultas com relógio; F-04 precedência de UUID malformado (AUCTIONEER 422, BIDDER 403, anônimo 401). Nenhuma decisão reaberta.

Uma precisão necessária: a generalização da story “filtro no JOIN” aplica-se às
três leituras com clock LEFT JOIN. `my_bids_statement` real usa WHERE e zero linhas
para 404; adiciono ali o filtro no WHERE. Isso preserva a decisão D3 e não exige
refatoração. Na sala, D5 muda o catálogo HTTP backend; a instrução específica
mantém as demais mensagens locais da 3.5, acrescentando apenas lot_cancelled.

## Passagem 1 — Coerência

**APROVADA.** Seis CAPs com intent e success observáveis; intents descrevem
comportamento e detalhes técnicos ficam nos companions. IDs CAP-1–CAP-6 únicos,
sem renumerar contrato anterior (pasta nova). Constraints eliminam escolhas
incompatíveis; non-goals explícitos e sinal de sucesso testável. Nomes/imports
coerentes com código atual; sem dependência circular, carteira no cancelamento
ou timestamp anterior ao lock. Não há questão de produto inventada.

## Passagem 2 — Preservação

**APROVADA.** A matriz acima localiza os 16 itens. D1 está no limite temporal;
D2 no gate/idempotência; D3 nos filtros/painel; D4 no lance/sala; D5 no 409 neutro;
D6 no módulo/imports; D7 no DTO administrativo e preservação de criação 201.
I01–I18 preservam os casos de integração; C1/C2/C3 cobrem ambas ordens e corrida
livre com oráculo completo; M1–M8 mantêm a numeração do pedido (M1 reformulada), mais filtro M9 restrito às consultas com LEFT JOIN.
Migration, seed, estados de UI, foco, double submit, erro ambíguo e limites de
integridade estão presentes. Nenhum requisito de Epic 4 entrou no escopo.

Wrapper-only content: seleção de modelo e ordem “depois pare” são metadados da
execução, preservados no registro operacional sem virarem capacidades de produto.
Proibições de Git, arquivos de segredos, código e build valem para esta rodada;
não foram convertidas em tarefas de implementação. Nenhuma instrução vinculante
foi descartada como decoração.

## Evidência e conclusão

Ativação/config resolvidos pelos scripts da skill; hooks prepend/append,
persistent facts e on_complete estão vazios. O cache padrão do uv recusou uma
escrita fora do sandbox; a execução prosseguiu com `UV_CACHE_DIR=/private/tmp/casa-uv-cache`,
sem escalada. Memlog criado/append pelo script compartilhado; kernel e companions
derivados dessas decisões e fontes. Sem story breakdown em modo headless.

Esta rodada executou inspeção de fontes, escrita de artefatos e validação
documental de referências/estrutura. Nenhum teste de produto, mutation testing,
verify, build, migração, banco, navegador, Git ou deploy foi executado; nenhum
arquivo `.env*` foi lido/editado. Não há número de testes aprovado reivindicado.

**Decisões abertas restantes: nenhuma.**

**Veredito: PRONTA PARA BUILD.** A entrega para aqui; iniciar implementação exige
outra instrução. Somente a pasta desta spec foi criada nesta execução.
