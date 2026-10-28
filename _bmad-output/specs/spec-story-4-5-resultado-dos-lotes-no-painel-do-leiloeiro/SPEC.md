---
id: SPEC-story-4-5-resultado-dos-lotes-no-painel-do-leiloeiro
status: done
date: 2026-10-28
companions:
  - current-state.md
  - data-api-contract.md
  - authorization-contract.md
  - ux-contract.md
  - refresh-strategy.md
  - acceptance-and-tests.md
  - human-decisions.md
  - validation.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
sources: []
---

# Story 4.5 — Resultado dos lotes no painel do leiloeiro

> Consolidei QH-01–13 pela decisão humana de 28/10/2026. Contrato revalidado e
> pronto para desenvolvimento; o mesmo pedido autoriza build imediato, sem nova confirmação.

## Why

Quero acompanhar o resultado dos meus lotes no painel autenticado e o total recebido
nas vendas. A 4.3 persiste a apuração e a 4.4 a executa automaticamente; falta ao
painel distinguir resultado confirmado de lote ainda aguardando apuração.

## Capabilities

- **CAP-1**
  - **intent:** Como leiloeiro, reconheço a situação de cada lote próprio.
  - **success:** Agendado/ao vivo, expirado sem settlement, vendido, sem arremate e cancelado são distinguíveis, sem vencedor inferido de prazo ou lances.
- **CAP-2**
  - **intent:** Consulto o resumo persistido de um lote apurado.
  - **success:** Sold apresenta pseudônimo, valor, contagem e instante na listagem; unsold não apresenta vencedor nem preço artificial.
- **CAP-3**
  - **intent:** Consigo obter o resultado atualizado ao usar o painel.
  - **success:** O mecanismo aprovado em QH-05/06 atualiza pending para sold/unsold sem comandos econômicos; resposta substituída não regride a tela.
- **CAP-4**
  - **intent:** Acesso somente os resultados privados autorizados para minha conta.
  - **success:** Lista contém só lotes próprios; bidder recebe 403 e anônimo 401; contrato não contém identidade privada do vencedor, HMAC ou carteira.
- **CAP-5**
  - **intent:** Reconheço quando os dados não estão disponíveis com segurança.
  - **success:** Loading, erro, vazio e inconsistência são tratados sem inventar resultado; leitura de vários lotes não produz N+1 nem efeitos econômicos.
- **CAP-6**
  - **intent:** Conheço o total recebido pelas vendas dos meus lotes.
  - **success:** Soma simples dos valores persistidos de sold próprios, no mesmo snapshot, dá zero sem vendas e exclui pending, unsold, cancelled e lotes alheios; falha não apresenta total parcial.

## Constraints

- Settlement 4.3 é a fonte autoritativa; só ele confirma sold/unsold. Expirado sem settlement permanece apurando. Cancelamento preserva semântica própria.
- Leituras não chamam settle_lot/prepare_settlement, scheduler ou publicação; não criam settlement/receipt, modificam wallet/bids, reparam dados ou adquirem lock de escrita.
- DTO privado explícito, whitelist e ownership no banco; nenhum dump ORM/SettlementRecord ou consulta da identidade do vencedor. Somente pseudônimo (QH-10).
- Centavos inteiros no backend, BRL pelo formatador existente; UTC na API, fuso do navegador na UI; relógio PostgreSQL e linhas no mesmo snapshot.
- Sem request por card/linha nem reader por item; preservar contratos públicos REST/WS e mecanismo financeiro das 4.3/4.4.
- Respeito DESIGN/EXPERIENCE: lista densa, miniatura, hierarquia editorial, estado em texto e responsividade; sem dashboard analítico ou infraestrutura nova.
- QH-13: total_received_cents soma sold próprios no mesmo snapshot da lista; não é saldo de carteira. QH-11 exige falha integral sem repair e preservação do snapshot anterior com stale no frontend.
- Resultado na lista; somente extensão de /api/lots/mine; montagem/manual Atualizar/foco, sem polling; ordem atual e nenhum filtro. Build autorizado após gate documental; conclusão em review/in-review, Epic 4 in-progress.

## Non-goals

- Liquidação, reprocessamento, botão de liquidar, nova regra financeira, scheduler/callback React, alteração de lances/anti-sniping/heartbeat ou WebSocket administrativo.
- Auditoria 5.1, comprovante público/link/PDF/download 5.2, meus arremates 5.3, notificações, gráficos, relatórios, exportação ou painel global.
- Exposição de winner_user_id, email/nome real do vencedor, wallet, HMAC, IDs internos dispensáveis ou edição de settlement.
- Git, leitura de .env*, deploy, code review nesta sessão ou início do Epic 5.

## Success signal

CA01–CA12 e B01–24/F01–22/E01–08 demonstram leitura privada pura, resultado persistido,
total próprio coerente, atualização sem duplicação e preservação de dados no erro,
sem regressão do painel/cancelamento. Testes críticos usam PostgreSQL real;
smoke de UI e dois verifies precisam de evidência real no build autorizado.

## Decisões consolidadas

QH-01–13 decididas em human-decisions.md; nenhuma questão aberta. Mantive CAP-1–6.
As recomendações anteriores incompatíveis são históricas na memória append-only.
Não existe edição de lote atual; não a invento sob regressão. Implementação segue
este pacote e seus companions sem antecipar Epic 5.

## Resultado do build autorizado — 28/10/2026

Implementei somente a 4.5, executei os gates e o smoke; Story/sprint ficam review,
SPEC in-review e Epic 4 in-progress. QH-01–13 permanecem decididas.
[Contrato entregue, matriz de provas, resultados reais, arquivos e limites](implementation-evidence.md).
Não fiz code review ou deploy, Git, leitura de .env* ou início do Epic 5.

## Fechamento documental — 28/10/2026

SPEC aprovada e concluída. Review final da Story 4.5 informado pelo usuário: aprovada, 0 HIGH / 0 MEDIUM / 0 LOW. Story e sprint `done`; Epic 4 aprovado para fechamento e `done`.
