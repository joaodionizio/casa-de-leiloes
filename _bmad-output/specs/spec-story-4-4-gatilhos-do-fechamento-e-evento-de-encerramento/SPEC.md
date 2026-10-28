---
id: SPEC-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento
status: done
date: 2026-10-27
last_updated: 2026-10-28
companions:
  - current-state.md
  - scheduler-lifecycle-contract.md
  - event-contract.md
  - recovery-model.md
  - failure-retry-policy.md
  - concurrency-model.md
  - acceptance-and-tests.md
  - human-decisions.md
  - validation.md
  - ../../../docs/ARQUITETURA.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/transaction-contract.md
  - ../spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/data-contracts.md
  - ../spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/concurrency-model.md
sources: []
---

# Story 4.4 — Gatilhos do fechamento e evento de encerramento

> Contrato consolidado das decisões humanas QH-01–16 de 27/10/2026, derivado
> da memória canônica. Revalidado e promovido a **ready-for-dev** em 28/10/2026.
> Não autorizei implementação ou testes de aplicação nesta sessão.

## Why

Quero apurar lotes expirados durante a execução e após restart, com resultado
persistido recuperável pela sala. A 4.3 já liquida com segurança; esta story
orquestra descoberta, invocação e publicação, sem duplicar regras ou dinheiro.

## Capabilities

- **CAP-1**
  - **intent:** O sistema apura lotes vencidos enquanto está ativo.
  - **success:** Elegíveis produzem sold/unsold exclusivamente pelo comando 4.3; futuros/cancelados não liquidam e repetições não duplicam efeitos.
- **CAP-2**
  - **intent:** O sistema recupera apurações pendentes após downtime.
  - **success:** Depois de migrations/seed existentes, catch-up no lifespan tenta os pendentes iniciais antes do tráfego; scheduler continua o processamento posterior.
- **CAP-3**
  - **intent:** Clientes da sala descobrem o resultado durável com privacidade.
  - **success:** Terminal só após transição confirmada; snapshot converge clientes novos/offline para pending/sold/unsold, com cancelamento separado e sem identidade privada.
- **CAP-4**
  - **intent:** Falhas operacionais permitem progresso dos demais lotes.
  - **success:** Erros individuais são isolados, cooldown/backoff espaçam tentativas e cursor avança sobre backlog sem scan ilimitado ou loop quente.
- **CAP-5**
  - **intent:** Inicialização e desligamento controlam os recursos de fechamento.
  - **success:** Uma task de scheduler e um guard local por processo; sem ciclos acumulados, Session compartilhada ou abandono de worker; shutdown acompanha recursos iniciados e registra excesso da drenagem global de 30 s.

## Constraints

- QH-02/13 e AD-19 revisada: migrations → seed existente → lifespan/catch-up → scheduler → tráfego; não mover seed ou duplicar sua execução.
- QH-14 e Q9 revisada: POST vencido mantém só a recusa existente; zero segunda transação de settlement ou publicação por esse caminho. Settlement operacional exclusivo de catch-up/scheduler.
- QH-01/03: ciclo seguido de espera interrompível de 2 s; guard local SKIP, sem timer fixo sobreposto ou fila de ciclos.
- QH-11: no máximo 200 linhas candidatas consultadas e 50 tentativas efetivas por ciclo, ordem/cursor (ends_at,id), cooldown considerado e wrap ao fim.
- AD-5/6/9/26: autoridade temporal PostgreSQL sob lot lock; fim vigente relido; janela inclusiva soma 2 min cumulativos. Seleção não fornece tempo crítico ao comando.
- Uso só settle_lot(session_factory, *, lot_id, integrity), dono da Session/commit; sem prepare_settlement no orquestrador, finanças duplicadas, commit externo ou reparo.
- Só settled_sold/settled_unsold com transitioned=true permitem lot_closed; not_due e already_settled não publicam. COMMIT ambíguo nunca vira sucesso presumido.
- QH-04: payload público fechado, incluindo as_of igual ao settled_at persistido, sem nova leitura temporal. Snapshot completo mantém room.as_of da leitura e eixo settlement separado de phase.
- QH-05/06/15: terminal entregue ou snapshot settled tornam cliente terminal antes de heartbeat/reconnect; drenar frame e close 1000; cancelado mantém semântica pública existente.
- QH-07/08/12 e AD-25: snapshot/reconnect recupera publish perdido; em falha viva log + terminalização/invalidação e close best-effort recuperável; sem replay automático ou outbox, sem desfazer/refazer settlement.
- QH-09/10: financeiro permanente/teto e integridade têm cooldown local de 300 s, zero terminal/bypass/reparo; falhas transitórias repetem só em ciclo futuro com backoff 2–30 s.
- QH-16: preservar send/close WS10 s da 4.2 e limites DB existentes; sem timeout arbitrário 2 s, novos limites DB ou hard timeout que abandone trabalho síncrono. Drenagem global 30 s com erro claro se excedida, sem presumir rollback.
- AD-10/25/28: um processo, manager em memória; Session sync curta em worker, nenhum SQL bloqueante no event loop ou rede sob trava financeira; tasks internas sempre possuídas/supervisionadas.
- AD-17/30: testes críticos PostgreSQL real; identificadores em inglês e mensagens em português; GET/HEAD/OPTIONS/handshake/ping nunca liquidam.

## Non-goals

- Código, migrations, testes de aplicação/SQL/verify/deploy nesta sessão; Git e leitura de .env* proibidos.
- Gatilho de settlement em POST, nova regra de lance/contabilidade, código HTTP adicional para settlement ou reparo/reassinatura de legado.
- Nova tela/UX de resultado, painel 4.5, auditoria pública 5.1, comprovante compartilhável 5.2 e meus arremates 5.3.
- Redis/Celery/Kafka/cron externo/worker separado, coordenação distribuída, fila persistente, outbox ou estado durável de publicação.
- Reabrir tetos de conexões e timeout pós-commit D-A explicitamente adiados na 4.2.

## Success signal

No build futuro autorizado, CA01–12 e T01–40 demonstram apuração idempotente,
terminal exclusivamente pós-commit, recuperação por snapshot e lifecycle seguro.
Nesta consolidação, decisões fechadas, contratos alinhados e conferências
estáticas aprovadas são o gate para ready-for-dev; não são testes de produto.

## Decisões consolidadas

QH-01–16 decididas, sem questões humanas abertas. CAP-1–5 preservadas; CAP-6,
que propunha fechamento no POST vencido, foi aposentada por QH-14 e seu ID não
será reutilizado. Alternativas superadas ficam no histórico de human-decisions
e na memória append-only, fora do contrato normativo. Ready-for-dev não autoriza código.

## Build autorizado — 28/10/2026

Autorizei nesta sessão a implementação e os testes da Story 4.4 pelo pedido
explícito. As restrições de somente documentos acima registram a sessão de
especificação anterior. Preservo QH-01–16 e todos os contratos aprovados.
Não autorizei code review nesta sessão, Git, leitura de .env* ou início da 4.5.

## Resultado do build autorizado — 28/10/2026

Implementei o contrato e executei a matriz T01–40, regressões, nove mutações,
smoke e ambos os verifies. Mantive QH-01–16 e CAP-1–5, sem iniciar 4.5.
[Arquitetura implementada, testes, saídas reais, arquivos e limitações](implementation-evidence.md).
Build pronto para review independente em outra sessão; não marquei done.


## Fechamento final — 28/10/2026

SPEC concluída e aprovada; Story e sprint `done`. Os LOWs F44-01, F44-02,
F44-R01 e F44-R02 foram resolvidos, sem HIGH ou MEDIUM; gate final aprovado.
A [evidência final](implementation-evidence.md) registra a validação. Epic 4
permanece `in-progress` e Story 4.5 permanece `backlog`.
