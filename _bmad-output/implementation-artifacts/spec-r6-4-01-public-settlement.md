---
status: in-review
context:
  - CLAUDE.md
  - docs/FRONTEND-WORKFLOW.md
  - _bmad-output/planning-artifacts/DESIGN.md
  - _bmad-output/planning-artifacts/EXPERIENCE.md
  - _bmad-output/planning-artifacts/VITRINE-BLUEPRINT.md
  - _bmad-output/specs/spec-story-6-2-identidade-visual-e-responsividade/visual-contract.md
---
# R6.4-01 — status público de settlement

## Escopo aprovado

Correção única do finding de apresentação na Vitrine. A implementação anterior não começou porque o DTO não distingue settlement; o usuário autorizou explicitamente a ampliação abaixo. Não iniciar outra funcionalidade. Não executar Git nem ler .env*, credenciais ou segredos.

## Code Map

- `backend/app/lots.py`: DTO público, statements list/detail e montagem. Import local de LotSettlement para evitar ciclo. Retornar informação explícita de existência, preservando snapshot materializado/linha vazia/cancelamento/ordem.
- `backend/tests/integration/test_public_lots.py`, `backend/tests/test_lot_phase.py`, `backend/tests/lot_support.py`, `backend/tests/test_openapi.py`, `backend/tests/integration/test_lot_cancellation.py`: provas reais e ajustes de assinaturas/fixtures e schema exato; examinar testes de settlement existentes para criar sold/unsold reais.
- `frontend/src/api/publicLots.ts`, seus testes e todos os consumidores/fixtures: campo obrigatório validado.
- `frontend/src/ClosedLotRow.tsx`, `lotLabels.ts` e testes: apresentação contextual única para texto visível/acessível. Preservar LotState/phaseStatusText genéricos e lógica da Sala.
- `frontend/e2e/support/mockApi.ts`, `vitrine.spec.ts`, demais fixtures necessárias: propagação contratual explícita, provas pending/settled/acessibilidade/1440/375/320 e ausência de requisições extras.
- `public-lot-dtos.md`, `SPEC.md` e `test-plan.md` da 2.5: registrar o contrato vigente e a substituição explícita das restrições históricas; story 6.4, sprint e uso de IA registram correção e estado pendente de produção.

## Tasks & Acceptance

- [x] Implementar DTO/query/serialização list/detail, leitura pura única sem N+1 nem dados extras.
- [x] Provar pending, sold, unsold, live, scheduled, cancelados ocultos, schema/privacidade, relógio materializado e GET puro.
- [x] Exigir campo no parser e atualizar fixtures; testar ausente/inválido.
- [x] Corrigir Vitrine pending/settled visual e nome acessível; provar responsividade e preservação dos estados anteriores.
- [x] Executar focais backend/frontend/E2E e Sala/QH-01 (incluindo R6-AGG-01).
- [x] Coordenação: gate completo VERIFY_E2E=1 ./verify.sh exit 0, evidência da 6.4, uso de IA e contrato público atualizados, status preservados.

## Verification

O agente de implementação executa testes focais pertinentes e informa comandos/contagens reais. A coordenação executará o gate completo, documentação, comparação e revisão depois do retorno. Não executar o gate integral no subagente. Não modificar documentos de evidência/sprint/README no subagente; informar os ajustes documentais necessários à coordenação. Não marcar a spec/story/épico como done.

## Decisão explícita do usuário

Autorizo explicitamente a ampliação mínima do contrato público necessária para corrigir `R6.4-01`.

Continue nesta MESMA sessão.

Sua análise está correta: o DTO atual não permite distinguir `ended+pending` de `ended+settled`, portanto NÃO devemos inferir isso no frontend.

Implemente a solução abaixo e conclua correção + testes + gate.

## DECISÃO DE CONTRATO

Adicionar ao contrato público de lote:

`settlement_status: Literal["pending", "settled"]`

Backend e frontend devem transportar esse campo explicitamente.

Sem novo endpoint.

Sem migration.

Sem alteração da tabela de settlement.

Sem exposição de resultado privado.

Sem nova requisição no frontend.

## SEMÂNTICA

A fonte de verdade é a existência do settlement persistido para o lote.

Contrato:

### `phase !== "ended"`
O `settlement_status` pode naturalmente ser `pending`.

Nenhuma alteração visual necessária nos estados live/scheduled.

### `phase === "ended"` + `settlement_status === "pending"`

Mostrar:

`Encerrado, apurando resultado`

### `phase === "ended"` + `settlement_status === "settled"`

Mostrar:

`Encerrado`

Não inferir settlement por:
- relógio do navegador;
- `ends_at`;
- existência de receipt;
- quantidade de lances;
- texto;
- timeout.

O settlement persistido é a autoridade.

## PRIVACIDADE

O resumo público deve expor SOMENTE:

`settlement_status`

Não acrescentar:
- winner_user_id;
- e-mail;
- UUID do vencedor;
- carteira;
- receipt privado;
- valor que ainda não fazia parte do DTO;
- qualquer dado interno desnecessário.

O status `pending|settled` não é dado pessoal.

## BACKEND — PUBLIC LOT SUMMARY

Atualize `PublicLotSummary`.

Adicionar:

`settlement_status: Literal["pending", "settled"]`

Como `PublicLotDetail` herda do summary, o detalhe público deve permanecer contratualmente consistente.

Não crie outro DTO divergente apenas para evitar atualizar o detalhe.

## QUERY DA VITRINE

O `GET /api/lots` deve continuar sendo leitura pura e eficiente.

Preserve:

- um snapshot;
- um `clock_timestamp()` materializado;
- nenhum lock;
- nenhuma mutação;
- nenhuma liquidação por leitura;
- nenhum N+1;
- nenhuma chamada por lote.

Amplie o statement público para trazer a existência do `LotSettlement` na MESMA consulta.

A implementação pode usar:
- `LEFT OUTER JOIN` com `LotSettlement`, cuja relação por `lot_id` é única;
- ou expressão EXISTS equivalente,

desde que:
- seja uma única consulta;
- não multiplique lotes;
- preserve a linha `as_of` quando não houver lotes;
- preserve cancelados fora da Vitrine;
- preserve ordenação/classificação atuais.

IMPORTANTE:
`lot_settlement.py` importa `lots.py`.

Evite introduzir import circular em module scope.

Use import local onde necessário, seguindo o padrão já existente no projeto.

## QUERY DO DETALHE PÚBLICO

Atualize também `GET /api/lots/{lot_id}` para fornecer o mesmo `settlement_status`.

Preserve:
- um único snapshot;
- GET puro;
- sem settlement acionado pela leitura;
- 404 atual;
- cancelados ocultos conforme contrato.

Não faça uma segunda query apenas para settlement se puder obter no mesmo statement.

## SERIALIZAÇÃO

A função de summary/detail deve receber informação explícita de settlement.

Não faça query dentro de `public_lot_summary()`.

Preferência conceitual:

- query lê Lot + existência/id de settlement;
- camada de montagem recebe essa informação;
- define:
  - settlement encontrado → `"settled"`
  - ausente → `"pending"`.

Não precisa serializar o objeto settlement inteiro.

## FRONTEND — CONTRATO

Encontre o tipo/parser real dos lotes públicos.

Adicione `settlement_status` ao contrato estrito.

Não aceite ausência silenciosamente.

O frontend precisa detectar contrato inválido se o campo obrigatório estiver ausente ou tiver outro valor.

Atualize mocks/fixtures de forma explícita:
- lotes pendentes;
- lotes liquidados.

Não coloque default `"pending"` que esconda servidor antigo/contrato quebrado.

## VITRINE

Corrija `ClosedLotRow`/`LotState`/labels pelo menor caminho coerente.

Não mude globalmente toda semântica de `phaseStatusText("ended")` se isso afetar contextos que não possuem settlement explícito.

A Vitrine agora TEM informação suficiente.

Use os dois campos.

Visual:

`ended + pending`
→ `Encerrado, apurando resultado`

`ended + settled`
→ `Encerrado`

O nome acessível deve corresponder ao texto real.

Não permitir divergência entre:
- texto visual;
- aria-label/nome acessível.

## SALA

NÃO modifique a lógica da Sala para “adotar” o DTO da Vitrine.

A Sala já possui seu próprio contrato rico e QH-01 aprovado.

Preserve:

- ended + pending;
- ended + settled sold;
- ended + settled unsold;
- timer;
- WS;
- retry;
- correção R6-AGG-01.

Execute regressões focais para garantir que nada foi afetado.

## OUTROS CONSUMIDORES

Procure todos os consumidores do contrato público.

A mudança do DTO é intencional.

Atualize tipos/mocks/testes necessários.

Não altere textos de:
- Painel do leiloeiro;
- Meus arremates;
- comprovante;
- auditoria

a menos que compile/teste exija propagação puramente contratual e o comportamento permaneça igual.

## TESTES BACKEND OBRIGATÓRIOS

Provar pelo menos:

### 1. ended pendente

Lote venceu, sem `LotSettlement`.

`GET /api/lots`

retorna:
- `phase = "ended"`
- `settlement_status = "pending"`

### 2. ended liquidado sold

Existe `LotSettlement`.

Retorna:
- `phase = "ended"`
- `settlement_status = "settled"`

### 3. ended liquidado unsold

Mesmo contrato:
- `phase = "ended"`
- `settlement_status = "settled"`

### 4. live

Continua:
- `phase = "live"`
- sem alteração de classificação.

### 5. scheduled

Continua:
- `phase = "scheduled"`.

### 6. pure read

GET não cria settlement.

### 7. query behavior

Evitar N+1 e preservar a natureza de snapshot único da leitura.

Atualize OpenAPI/contrato se houver teste exato do schema.

## TESTES FRONTEND/E2E OBRIGATÓRIOS

### Caso A
Resumo:

`phase: ended`
`settlement_status: pending`

Visual:
`Encerrado, apurando resultado`

### Caso B
Resumo:

`phase: ended`
`settlement_status: settled`

Visual:
`Encerrado`

E zero ocorrência de “apurando resultado” nesse item.

### Caso C
Acessibilidade:

nome acessível acompanha o estado correto.

### Caso D
Estados live/scheduled continuam corretos.

### Caso E
Sala/QH-01 continua passando.

### Caso F
Vitrine em 1440/375/320 continua sem overflow/regressão visual.

Não precisa screenshot pixel-perfect.

## COMPATIBILIDADE

Esta é uma alteração coordenada backend + frontend no MESMO deploy.

Não implemente fallback para backend antigo.

Contrato obrigatório novo é preferível a mascarar inconsistência de versão.

## R6.4-01

Depois da correção local, marque apenas:

`R6.4-01 corrigido localmente — aguardando revalidação publicada`

NÃO marque RESOLVED em produção ainda.

## GATE

Rode focais primeiro.

Depois obrigatoriamente:

`VERIFY_E2E=1 ./verify.sh`

Precisa terminar exit 0.

Informe contagens reais.

## DOCUMENTAÇÃO

Atualize apenas o necessário para registrar:

- causa real: DTO público não distinguia settlement;
- decisão de ampliar o contrato;
- novo campo `settlement_status`;
- correção local;
- regressões;
- gate;
- redeploy ainda necessário.

Se README documenta formato JSON exato e precisar ser atualizado, faça o ajuste mínimo.

Não reabra 6.3 sem motivo.

## STATUS

Mantenha:

- 6.1: review até fechamento final da 6.4;
- 6.2: done;
- 6.2A: tecnicamente revisada;
- 6.3: tecnicamente revisada;
- 6.4: in-progress;
- Épico 6: in-progress;
- 6.5–6.7: cortadas.

## GIT

NÃO faça:
- commit;
- push;
- merge;
- deploy.

O usuário fará isso depois do gate.

## SAÍDA

Informe:

1. contrato backend final;
2. como a consulta pública foi ampliada;
3. confirmação de uma única leitura/snapshot e ausência de N+1;
4. contrato frontend atualizado;
5. comportamento da Vitrine pending;
6. comportamento da Vitrine settled;
7. testes backend;
8. testes frontend/E2E;
9. regressões da Sala;
10. resultado do `VERIFY_E2E=1 ./verify.sh`;
11. arquivos modificados;
12. status de R6.4-01 como corrigido localmente mas ainda pendente de produção;
13. limitações.

Depois PARE para commit/deploy/revalidação.

## Review Triage Log

Executei as três camadas internas da skill bmad-build. Edge Case Hunter retornou
`[]`; Verification Gap Reviewer retornou `No verification gaps found`. O Blind
Hunter calculou piso 9 em um diff que inclui a evidência histórica restaurada e
apresentou os nove itens abaixo. Esta revisão interna não concede aceite humano
ou validação de produção.

| Item | Veredito / rota | Evidência e decisão |
| --- | --- | --- |
| BH01 — detalhe em cancelamento exige 17 campos | low / patch | O gate reproduziu exatamente `18 == 17`, com 2412 passed/1 failed. Atualizei somente a expectativa para 18 e o assert pending; focal de cancelamento: 38 passed. Gate integral renovado em seguida. |
| BH02 — SPEC 2.5 proíbe settlement_status | low / patch documental | A CAP-5 registra o contrato histórico. Acrescentei nota de substituição explícita por R6.4-01 e link ao DTO vigente, preservando o histórico. |
| BH03 — plano 2.5 mantém contagens 9/17 | low / patch documental | Mesma restrição histórica no plano. Nota explícita fixa 10/18 e o novo contrato; testes executáveis/OpenAPI foram atualizados e exercitados. |
| BH04 — mocks de Sala/Vitrine podem divergir | false | São fotografias e contratos separados, por decisão aprovada. O novo cenário usa status explícito da listagem e verifica zero chamadas de Sala; os cenários ricos da Sala recebem suas próprias fixtures. Nenhum comportamento incorreto do produto demonstrado; unificar modelos mudaria desnecessariamente os mocks da Sala. |
| BH05 — falta cenário pending→settled após reload | false | Não há cache/status local por lote introduzido: cada GET validado monta a tela usando os dados novos. Os dois estados são provados por DOM, e navegação/reload já são exercitados pela suíte. Nenhum resultado incorreto ou critério obrigatório descoberto sem cobertura. |
| BH06 — texto poderia estar cortado em 320 | false | `.closed-status` tem overflow-wrap:anywhere, sem overflow hidden, altura fixa ou line-clamp; o clamp é só do título/artista. Os três viewports verificam status visível, caixa dentro da largura e documento sem overflow. Nenhum clipping encontrado no caminho alterado. |
| BH07 — falta lista com três encerrados simultâneos | false | O join usa lot_id único e a montagem testa pertinência no conjunto de IDs por item; os três resultados persistidos são exercitados por GETs reais com outros lotes na mesma lista, contagens/ordem e sem N+1. A sugestão amplia combinações, sem demonstrar associação incorreta ou requisito obrigatório ausente. |
| BH08 — falta testar HTTP de contrato ausente | false | fetchPublicLots/fetchPublicLot usam diretamente os guards e retornam failure:server em caso falso. Os guards de listagem e detalhe têm provas de ausência e valores inválidos; não houve desvio desse fluxo. Um teste adicional do wrapper duplicaria o caminho existente sem falha demonstrada. |
| BH09 — evidência publicada estaria só em tmp | false | A story versionada contém matriz, horários, HTTP, valores, lote, pseudônimos, hash final e reprodução dupla. O JSON temporário é coleta complementar; a evidência não depende exclusivamente dele. Não copio dados adicionais de produção sem necessidade para a correção local. |

Não mantive finding novo de código aberto. R6.4-01 permanece pendente de
publicação/revalidação. Os ajustes confirmados são propagação do contrato
aprovado, sem funcionalidade adicional.

## Resultado local final

Gate renovado `VERIFY_E2E=1 ./verify.sh`: exit 0; 2413 pytest passed (1 warning),
199 Node pass, 322 Playwright passed/7 skipped. Ruff/formato/lint/typecheck/Vite/
Docker aprovados; 256 hashes workspace/cópia idênticos. Story 6.4 permanece
in-progress e esta correção aguarda publicação/revalidação; não houve commit,
push, merge ou deploy. Evidência e lista de arquivos na story 6.4.
