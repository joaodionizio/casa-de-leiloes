---
id: SPEC-story-3-6-leiloeiro-cancela-lote-sem-lances
companions:
  - http-contract.md
  - transaction-contract.md
  - database-and-reads.md
  - frontend-flow.md
  - test-plan.md
  - implementation-map.md
  - validation.md
  - ../../../CLAUDE.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
sources:
  - ../../implementation-artifacts/3-6-leiloeiro-cancela-lote-sem-lances.md
---

# Story 3.6 — Leiloeiro cancela lote sem lances

Contrato derivado da memória canônica e das fontes citadas em `validation.md`, em
26/10/2026. Preservei D1–D7 fechadas. Os companions integram o contrato; o índice
dos 16 itens solicitados está em `validation.md`. Nenhuma decisão aberta.

## Why

Preciso atender FR4 e FR6: o leiloeiro deve retirar uma obra própria antes do fim
sem deixar saldo comprometido ou aceitar um primeiro lance depois do cancelamento.
Decidi apoiar a ação na trava e na autenticação já entregues pela 3.4; descartei
confiar apenas na contagem exibida na lista administrativa.

## Capabilities

- **CAP-1**
  - **intent:** O leiloeiro retira um lote próprio que ainda não recebeu lances e não terminou.
  - **success:** Agendado ou ao vivo, íntegro e vazio, retorna 200 com ID e instante de cancelamento; somente `cancelled_at` muda.
- **CAP-2**
  - **intent:** A autorização e a repetição da ação preservam o resultado legítimo.
  - **success:** Só o dono cancela; repetição íntegra retorna o timestamp original sem UPDATE; adulteração retorna 409 antes da idempotência.
- **CAP-3**
  - **intent:** Cancelamento e primeiro lance concorrentes deixam um resultado consistente.
  - **success:** C1/C2/C3 em PostgreSQL real só admitem cancelado com zero lances ou não cancelado com exatamente um lance e cancelamento recusado.
- **CAP-4**
  - **intent:** O cancelado deixa de ser acessível ao público e continua identificável pelo dono.
  - **success:** Some dos três grupos da vitrine; detalhe, histórico da sala e participação própria respondem 404 após suas políticas; MyLots continua listando com `cancelled_at`, contagem, fase temporal e `as_of`.
- **CAP-5**
  - **intent:** O leiloeiro cancela pela lista com confirmação e feedback confiável.
  - **success:** CTA elegível, confirmação inline, um POST por envio pendente, releitura no sucesso, selo Cancelado e erros por código; resultado ambíguo não afirma sucesso nem falha e não reenvia.
- **CAP-6**
  - **intent:** A aplicação mantém um demo válido e informa ao licitante que o lote foi cancelado.
  - **success:** Seed ignora demo cancelado sem alterá-lo; lance em cancelado íntegro retorna `422 lot_cancelled` sem efeitos, e a sala mostra “Este lote foi cancelado.”.

## Constraints

- D1–D7 são vinculantes; primeiro cancelamento exige `database_now < ends_at`, mas repetição íntegra precede essa regra.
- Trava exclusiva do lote, hora única pós-trava, ownership, gate existente, idempotência, lances, fim e escrita nessa ordem. Sem carteira ou nova assinatura.
- Reutilizo `authenticate_previous_state` de `app.bids`; não movo, refatoro nem copio o gate. O módulo dedicado é ligado em `main.py`, sem import circular.
- Âncora ausente não é confiável; nenhuma reparação, reassinatura ou exceção administrativa. `cancelled_at` fica fora da âncora v1.
- Leituras permanecem puras. `phase` só admite `scheduled`, `live`, `ended`; `cancelled_at` é o eixo próprio de cancelamento.
- MyLots recebe read model específico; criação 201, DTOs públicos e protocolos da sala permanecem com seus contratos, exceto filtros públicos e novo código de recusa expressamente solicitados.
- Migração aditiva, sem backfill, default de relógio, CHECK novo ou índice sem benefício comprovado.
- React/TypeScript simples, tokens existentes, estado por texto, foco e controles semânticos; nenhuma dependência ou infraestrutura genérica nova.

## Non-goals

- Cancelar lote com lances, estornar ou alterar carteiras; fechar, liquidar, definir resultado ou iniciar Epic 4.
- WebSocket, polling, auditoria pública, busca/filtro e redesign da sala.
- State machine, service framework, repository abstraction ou commands genéricos; refatoração do gate.

## Success signal

No build futuro, o dono cancela um lote agendado e outro ao vivo sem lances, vê ambos
em Meus lotes como Cancelado e encontra 404 nas leituras públicas. Os testes de
concorrência rejeitam qualquer estado híbrido e a repetição preserva o instante
original. O plano de testes e as mutações verificam esses critérios sem repetir
toda a suíte da 3.4. Esta rodada entrega somente a especificação.
