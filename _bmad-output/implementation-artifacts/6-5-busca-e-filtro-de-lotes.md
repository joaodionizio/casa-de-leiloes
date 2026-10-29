---
title: 'Story 6.5 — Busca e filtro de lotes'
type: feature
created: '2026-10-29'
status: done
route: dispatch
context:
  - CLAUDE.md
  - _bmad-output/planning-artifacts/DESIGN.md
  - _bmad-output/planning-artifacts/EXPERIENCE.md
  - _bmad-output/planning-artifacts/VITRINE-BLUEPRINT.md
---

<frozen-after-approval reason="implementação integral e sequencial autorizada expressamente pelo usuário">

## Intent

Decidi reativar a busca/filtro da Vitrine após o fechamento obrigatório do Épico 6. Quero localizar obras no snapshot já entregue por GET /api/lots, sem backend novo ou consulta à AIC. Descartei requisições por tecla e debounce sem rede. Esta story é o primeiro bloco do candidato conjunto 6.5 → 6.6 → 6.7 + footer + refinamentos de feedback humano externo.

## Boundaries & Constraints

Preservo estados do servidor, cancelados ausentes, ordem dos grupos, destaque e restauração de foco. Busco título, artista e data textual; ignoro UUID, trim do termo, normalização case/accent insensitive. Estado e termo se combinam sem apagar o termo. Controles reais com label, teclado, foco visível, seleção além da cor, alvos de toque adequados e feedback acessível sem spam. Identidade ÁTRIO editorial com obra protagonista. Nunca executar Git, gh, deploy, ler .env*, credenciais ou segredos. Não executar review independente. Não rodar gate integral neste bloco; apenas focais. A autorização já existe: não pedir aprovação intermediária.

## I/O & Edge-Case Matrix

| Cenário | Entrada / estado | Resultado |
| --- | --- | --- |
| Busca | título/artista/data, caixa e acentos variados | correspondências locais; trim; vazio mostra todos |
| Estado | Todos/Ao vivo/Próximos/Encerrados | somente grupo correspondente do snapshot |
| Combinação | termo e estado ativos | interseção; mudança de estado mantém termo |
| Vazio | zero correspondências | “Nenhum lote encontrado com esses filtros.” |
| Limpar | termo ou estado ativo | botão Limpar filtros repõe Todos e termo vazio |
| Rede | digitar/filtrar/limpar | nenhuma nova consulta, AIC ou mutação |

</frozen-after-approval>

## Code Map

- `frontend/src/api/publicLots.ts`: snapshot público completo live/scheduled/ended, já sem cancelados; não mudar API.
- `frontend/src/vitrine.ts`: seleção de destaque, rails e paginação locais; acrescentar filtro puro sem decidir fase pelo relógio.
- `frontend/src/VitrinePage.tsx`: conteúdo sobre snapshot; integrar busca/filtros antes do destaque sem dashboard.
- `frontend/src/App.css`: estilos atuais do catálogo; acrescentar controles discretos e responsivos por tokens.
- `frontend/src/vitrine.test.ts`, `frontend/e2e/vitrine.spec.ts`, `frontend/e2e/support/mockApi.ts`: reutilizar fixtures/padrões de testes.

## Tasks & Acceptance

- [x] `frontend/src/vitrine.ts`, `VitrinePage.tsx`, `App.css`: implementar busca/filtro local acessível e estado vazio/limpar.
- [x] `frontend/src/vitrine.test.ts`, `frontend/e2e/vitrine.spec.ts`: cobrir matriz, cancelados ausentes, nenhuma rede adicional/mutação e responsividade 1440/375/320.
- [x] Este artefato: registrar focais reais e deixar em review após implementação; não done.

**Critérios:** Dado snapshot pronto, quando busco e filtro, então só vejo lotes correspondentes sem rede adicional. Dado viewport estreito, quando opero controles por teclado/toque, então não há overflow global e a seleção é identificável sem depender da cor.

## Implementation Notes

6.5–6.7 foram inicialmente cortadas por prazo após a entrega obrigatória e posteriormente reativadas por decisão humana para implementar os opcionais. Execução já aprovada com foco por bloco e somente um VERIFY_E2E=1 ./verify.sh final pela coordenação. Alterações prévias do usuário em documentos devem ser preservadas.

## Verification

Executar testes Node focais e Playwright focais da Vitrine. Não executar verify integral, commit, deploy ou review. Relatar comandos, resultados e arquivos alterados. Se ajustes fora do Code Map forem estritamente necessários ao aceite, documentá-los.

### Implementação e focais reais — 29/10/2026

Decidi filtrar os três grupos do snapshot com função pura, preservando `as_of`,
ordem e estados do servidor. A busca ignora caixa/acentos, aplica trim e consulta
somente título, artista e data textual. Descartei busca por UUID, horários de
operação e qualquer nova consulta de negócio durante a interação.

Integrei campo de busca com label, grupo de rádios nativos Todos/Ao vivo/Próximos/
Encerrados, contagem, vazio e Limpar filtros antes do destaque. A seleção tem
rádio marcado e sublinhado; os alvos medidos chegam a 44 px. A busca atualiza
imediatamente; o resumo acessível é anunciado ao sair do campo, selecionar estado
ou limpar, evitando anúncio por tecla. Limpar devolve foco à busca. Destaque,
rails e paginação são calculados sobre a interseção dos filtros.

Precisei ampliar o Code Map em `frontend/src/route.ts` e `route.test.ts` para
guardar/validar termo e estado no histórico: ao voltar de um lote, os mesmos
filtros e a paginação são restaurados para permitir devolver o foco ao link
original. Também acrescentei `announceCount` opcional a `ClosedLots.tsx` para
suprimir o anúncio automático da contagem de encerrados durante busca ativa;
o resumo dos filtros concentra esse feedback. Nenhum contrato HTTP mudou.

Comandos executados em `frontend/`:

- `node --test src/vitrine.test.ts src/route.test.ts`: **37 passaram**, zero falha.
- `npm run typecheck`: **exit 0**, incluindo TypeScript dos testes E2E.
- `npx eslint src/vitrine.ts src/VitrinePage.tsx src/ClosedLots.tsx src/route.ts src/vitrine.test.ts src/route.test.ts e2e/vitrine.spec.ts`: **exit 0**.
- `npx playwright test e2e/vitrine.spec.ts`: **26 passaram** em Chromium,
  incluindo cinco novos cenários da 6.5, responsividade 1440/375/320,
  teclado, seleção sem depender de cor, toque, foco/Back, paginação, cancelado
  ausente e nenhum novo GET de negócio, chamada AIC ou mutação ao filtrar/limpar.
  Imagens continuam com carregamento normal do catálogo; o teste separa essas
  requisições das consultas de negócio.

A primeira tentativa Playwright foi impedida pelo sandbox ao abrir
127.0.0.1:4173 (`listen EPERM`); a repetição com execução escalada autorizada
passou. O preview reportou avisos NO_COLOR/FORCE_COLOR e EPIPE no proxy WebSocket
de testes que abrem a sala; não houve falha de teste. O Playwright construiu o
frontend para servir o preview. Não executei gate integral, Git, gh, deploy,
review independente nem leitura de `.env*`, credenciais ou segredos.

Estado: **review**. O gate conjunto e o registro agregado em `docs/uso_de_ia.md`
ficam com a coordenação, conforme a autorização desta rodada; não iniciei 6.6.


### Integração com 6.7 — 29/10/2026

Mantive o snapshot/API e acrescentei apresentação compacta do filtro por select
nativo abaixo de 1024px, preservando os rádios no desktop. Ambos alteram o mesmo
estado e conservam termo/foco/limpar; só um conjunto é visível por viewport.
Ajustei a checagem de teclado e alvo de toque às duas apresentações. A integração
preserva CTA típico no primeiro viewport, testado também em 768px, sem afrouxar
os critérios anteriores. Focais finais pertinentes de layout/vitrine/tema:
81 passed. Estado continua review, sem novo endpoint, consulta AIC ou mutação.


Gate conjunto final: VERIFY_E2E=1 ./verify.sh exit 0; 2446 backend, 206 Node,
355 Playwright, Docker aprovado. Real-stack separado 7 passed e smoke financeiro
real aprovado. Resultado e limites em [FECHAMENTO-EPICO-6.md](../../docs/FECHAMENTO-EPICO-6.md).
Estado review; review agregado independente dos opcionais pendente.


## Fechamento vigente — smoke público final, 29/10/2026

**Estado: done.** Decidi concluir esta story após a aprovação técnica agregada
local vigente (R6-OPT-01 RESOLVED) e o smoke real do candidato publicado em
29/10/2026, America/Maceio. Descartei reabrir implementação ou repetir toda 6.4.
Candidato Git local/main: `2a6dc9394be0174a74016b3de46c276eb5ef6074`; SHA do
Render não autenticado. Zero novo BLOCKER/HIGH/MEDIUM; ressalva LOW externa
no acesso ao link oficial AIC por Cloudflare, sem bloqueio do fechamento.

Resultados, limites e fluxo financeiro: [smoke público final](smoke-publico-final-6-5-6-7.md).
6.5: busca/filtros/combinação sem requests extras; 6.6: cancelamento com lance e
refund exato de R$90, total R$100 preservado e auditoria íntegra; 6.7: tema
persistente, footer/cadastro/ajudas/contexto do líder validados em produção.
Preservo o fechamento obrigatório anterior e a reabertura humana posterior para
os opcionais; **Épico 6 done novamente, fechamento definitivo**. Blocos anteriores
que aguardam review/publicação são registros históricos, superados por este.
Nenhuma mudança de código, banco direto, commit, push, merge ou deploy nesta sessão.
