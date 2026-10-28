---
id: SPEC-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base
status: done
date: 2026-10-27
companions:
  - current-state.md
  - transaction-contract.md
  - financial-invariants.md
  - data-contracts.md
  - concurrency-model.md
  - acceptance-and-tests.md
  - human-decisions.md
  - validation.md
  - ../../../docs/ARQUITETURA.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
sources: []
---

# Story 4.3 — Fechamento, liquidação idempotente e comprovante base

> Fechamento formal em 27/10/2026: **concluída e aprovada**. O review e as
> evidências posteriores estão em [implementation-evidence.md](implementation-evidence.md)
> e [code-review-final-story-4-3.md](../../implementation-artifacts/code-review-final-story-4-3.md).
> Os relatos de etapas anteriores permanecem abaixo como histórico.

> Contrato final derivado da memória canônica e das decisões humanas QH-01–10 de 27/10/2026. Consolidei somente especificação. Ready-for-dev significa contrato pronto; não autorizei implementação nesta sessão.

## Why

Quero concluir a apuração dos lotes expirados com resultado econômico durável, transferência correta do valor arrematado e comprovante base recuperável. A trava compartilhada com lances e a liquidação indivisível impedem cobrança duplicada, fechamento prematuro e comprovantes de operações revertidas.

## Capabilities

- **CAP-1**
  - **intent:** O sistema apura um lote elegível e registra seu resultado com ou sem vencedor.
  - **success:** Lote ativo permanece intacto; expirado íntegro produz exatamente um settlement sold ou unsold, sem vencedor fictício.
- **CAP-2**
  - **intent:** Vencedor e leiloeiro recebem os efeitos financeiros corretos da arrematação.
  - **success:** Total e reserva do vencedor diminuem F, total do leiloeiro aumenta F; disponível do vencedor, perdedores e reservas de outros lotes permanecem corretos; falha reverte tudo.
- **CAP-3**
  - **intent:** Resultado e comprovante base podem ser recuperados após a liquidação.
  - **success:** Readers internos por lot_id recuperam settlement autoritativo e exatamente um receipt para sold, nenhum para unsold, com os valores originais persistidos.
- **CAP-4**
  - **intent:** Lances e tentativas simultâneas ou repetidas de fechamento produzem um resultado coerente.
  - **success:** Fim estendido confirmado impede fechamento antes do novo prazo; fechamento confirmado impede reabertura; repetição válida revalida e retorna dados originais sem efeitos, transitioned=false.
- **CAP-5**
  - **intent:** A apuração usa histórico autenticado e mantém identidades privadas fora do comprovante.
  - **success:** Adulteração/âncora ausente ou incoerência de settlement/receipt causa conflito sem reparo; receipt não contém identidade privada, carteira ou HMAC, inclusive no schema.

## Constraints

- Serviço exclusivamente interno, sem novas rotas HTTP; testes o chamam diretamente. Readers por lot_id não produzem side-effects.
- AD-6/8/9/26: lot lock primeiro, um clock_timestamp após lock, ends_at relido e settlement verificado; autenticar estado antes de efeitos; carteiras por user_id crescente; commit único.
- AD-5 vigente: janela 0 < restante <= 2 min soma 2 min ao fim vigente, sem teto. Não liquidar se now < ends_at; não alterar fim no fechamento.
- AD-3/7: centavos inteiros, CHECK imediata, A=T-C; consumir F reservado sem cobrá-lo novamente do disponível; conservar soma dos totais.
- QH-02/03: lot_settlements com id próprio e lot_id UNIQUE; receipts separado com id próprio, lot_id UNIQUE e settlement_id UNIQUE, somente sold. Settlement é o registro econômico autoritativo.
- QH-08: teto financeiro violado causa conflito tipado e rollback completo, sem novo settlement/receipt. Tratamento operacional sem retry quente infinito será da 4.4.
- AD-13/20/21: cadeia/âncora/HMAC e vínculo operacional autenticados; snapshot de integridade interno no settlement; receipt sem HMAC; canonical bid v1 intacto e nenhum reparo/reassinatura de legado.
- QH-05/10: transitioned=true somente depois de novo commit confirmado; repetição inconsistente é conflito de integridade, nunca sucesso ou nova liquidação.
- AD-17: testes críticos PostgreSQL real, conexões independentes e barreiras; plano em acceptance-and-tests.md.
- AD-19/25: leituras/handshake nunca liquidam; fase temporal separada de pending/settled e sold/unsold; publicação futura somente pós-commit, sem acoplar manager WS agora.
- AD-30: banco/código/contratos em inglês, interface/mensagens em português; banco síncrono fora do event loop.

## Non-goals

- Scheduler, catch-up no boot, gatilho periódico ou em tentativa de lance, evento/publicação WS de encerramento (4.4).
- Novas APIs, alteração de room_snapshot/bid_accepted, máquina 4.2, UI da sala ou painel do leiloeiro (4.5).
- Auditoria pública (5.1), link compartilhável (5.2), meus arremates (5.3), snapshot extra da obra, ledger, nova contabilidade, estorno, broker/outbox ou múltiplos workers de hospedagem.
- Implementação, migrations executadas, testes de aplicação executados, Git, leitura de .env* ou deploy nesta sessão.

## Success signal

No futuro build autorizado, os critérios CA01–21 e os testes PG01–35 demonstram uma única transferência, um settlement autoritativo e receipt exclusivo quando sold; unsold existe sem receipt; falhas/repetições não deixam efeitos parciais nem duplicados. Os testes financeiros, de integridade e concorrência usam PostgreSQL real e registram evidência de execução.

## Decisões consolidadas

QH-01–10 decididas e consolidadas em human-decisions.md. Nenhuma questão humana aberta na 4.3. HTTP 200 novo/repetido é apenas orientação futura; não há API nesta story. Implementação aguarda autorização separada.

## Build autorizado em 27/10/2026

O pedido humano posterior autorizou implementação e validação exclusivamente da
4.3. As referências acima à sessão sem código são o registro da especificação
original; essa restrição documental foi superada pela autorização explícita do
build, sem reabrir QH-01–10 ou ampliar o escopo funcional. Evidência real, matriz
PG01–35, mutações, gates e limitações em
[implementation-evidence.md](implementation-evidence.md). Review independente e
aceite humano permanecem para a etapa posterior; não iniciei a 4.4.
