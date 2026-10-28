# Story 4.4 — Gatilhos do fechamento e evento de encerramento

Status: **done** — fechamento aprovado em 28/10/2026. Sprint: **done**.
Epic 4: **in-progress**. Build autorizado por pedido explícito em 28/10/2026.

Como avaliador, quero que lotes vencidos sejam apurados durante a execução e
após restart, com resultado confirmado recuperável pela sala, sem depender de
uma requisição nem duplicar efeitos econômicos.

## Escopo e contrato canônico

Consolidei somente documentos pela bmad-spec. Decidi migrations → seed existente
→ lifespan/catch-up → scheduler → tráfego. Preservo start.sh/seed externos ao
lifespan. POST vencido mantém a recusa existente, sem segunda transação de
settle_lot, publicação ou códigos HTTP novos de settlement.

Leio [SPEC.md](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/SPEC.md)
e todos os companions declarados. O pacote contém:

- [Baseline e mapa provável do build](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/current-state.md).
- [Scheduler/lifecycle, query e chamada exata](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/scheduler-lifecycle-contract.md).
- [Contrato de evento/snapshot/cliente](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/event-contract.md).
- [Recuperação commit/publicação](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/recovery-model.md).
- [Falhas, retries e logs](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/failure-retry-policy.md).
- [Concorrência e prova PostgreSQL](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/concurrency-model.md).
- [CA01–12, T01–40 e M01–08](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/acceptance-and-tests.md).
- [QH-01–16 decididas e histórico de alternativas](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/human-decisions.md).
- [Validação documental](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/validation.md).

## Contrato final

Scheduler interno por processo, ciclo → espera interrompível de 2 s, guard
SKIP sem fila/overlap. Até 200 linhas consultadas e 50 tentativas por ciclo,
ordem/cursor (ends_at,id), cooldown considerado e wrap no fim. Catch-up percorre
população inicial finita pelo mesmo mecanismo antes do tráfego, depois do seed.
Falha individual não derruba startup; falha sistêmica pode impedi-lo com log.

Uso só settle_lot(session_factory, *, lot_id, integrity), dono de Session/commit.
Somente settled_sold/settled_unsold com transitioned=true permitem lot_closed;
not_due/already_settled não publicam. Evento tem type, lot_id, outcome,
winner_alias, final_amount_cents, bid_count, final_hash, settled_at e as_of,
com as_of igual ao settled_at persistido. Unsold tem alias/preço null.
Sem dados privados, HMAC, wallet, receipt interno ou clock novo na montagem.

Snapshot compartilhado REST/WS acrescenta settlement_status/settlement, separado
de phase. Snapshot settled inicial é entregue antes de close 1000 e antes de
qualquer ping/reconnect. Conectado drena lot_closed e fecha 1000; cancelamento
mantém semântica própria. Publish perdido recupera por snapshot/reconnect;
falha viva tenta terminalizar/invalidar sala e close recuperável best-effort,
sem replay periódico, outbox ou desfazer/refazer settlement.

Financeiro permanente/teto e integridade têm cooldown local 300 s com erro
operacional, sem bypass/reparo. Transitórios só repetem em ciclo futuro com
backoff 2–30 s. Preservo limites DB existentes e send/close 10 s da 4.2; sem timeout 2 s
ou hard timeout que abandone trabalho síncrono. Shutdown impede novas admissões,
interrompe sleep e acompanha tasks/workers em janela global 30 s; excesso gera
erro claro, sem liberar Session/engine em uso ou presumir rollback.

Integração mínima do cliente é contrato/estado/cleanup, sem nova tela/UX de
resultado, painel 4.5, auditoria 5.1, link/comprovante 5.2 ou meus arremates 5.3.
CAP-1–5 preservadas; CAP-6 aposentada por QH-14, sem reutilizar ID.

## Decisões e validação

QH-01–16 decididas em 27/10/2026, sem questões humanas abertas. As decisões
QH-02/13/14 revisaram AD-19/Q4/Q9; registrei primeiro a mudança na arquitetura,
sincronizei resumos CLAUDE/épico/README e rederivei os companions. Alternativas
superadas permanecem no histórico de human-decisions e memória append-only.

CA01–12, T01–40 e M01–08 permanecem com IDs estáveis e oráculos finais. T31/T32
agora exigem ausência de settlement/publicação pelo POST vencido. PG real é
obrigatório para lock/commit/saldos/concorrência; casos continuam planejados,
sem testes executados nesta consolidação.

- [x] Receber e consolidar QH-01–16 pela memória oficial.
- [x] Atualizar contratos/testes e referências arquiteturais afetadas.
- [x] Revalidar coerência/preservação e conferir referências/IDs/tracking/hashes.
- [x] Depois do gate documental, promover story/SPEC/sprint ready-for-dev.
- [x] Obter autorização separada de implementação e executar build/gates futuros.

## Limites da sessão de especificação — histórico

Somente documentos, sem código, testes de aplicação, SQL, migrations, verify,
navegador, smoke ou deploy. Nenhum Git, leitura de .env* ou início da 4.5.
Autovalidação não é review independente ou prova de scheduler funcionando.

## Build autorizado concluído — 28/10/2026

Implementei somente 4.4: scheduler/catch-up, descoberta paginada, cooldown/backoff,
settle_lot exclusivo, lot_closed pós-commit, snapshot/cliente terminal e lifecycle.
Não alterei o serviço financeiro 4.3, seed/start.sh, bidding ou canonical v1.

Matriz final:40 testes backend novos passaram (7.47s), com os 40 cenários T01–40
mapeados também às regressões e provas TS/E2E. Concorrência real observa PID
bloqueado, commit/rollback/ACK e shutdown; nove mutações detectadas/restauradas.
Smoke sold/unsold/reconnect/restart aprovado. Verifies finais exit0: backend
2206 (126.82s) e 2206 (125.59s), frontend 179 em ambos; Playwright 226
(24.8s),5 skips existentes. Ruff/format/tipos/lint/Vite/Docker aprovados.

[Relatório completo e lista de arquivos](../specs/spec-story-4-4-gatilhos-do-fechamento-e-evento-de-encerramento/implementation-evidence.md).
Story/sprint ficam review, SPEC in-review, Epic 4 in-progress; 4.5 continua backlog.
Não fiz code review, Git, leitura de .env* ou deploy. Review/aceite ficam para
outra sessão; não marquei done.


## Fechamento final — 28/10/2026

Review inicial aprovado com LOWs, sem HIGH ou MEDIUM; F44-01, F44-02,
F44-R01 e F44-R02 resolvidos. Gate final aprovado; Story segura para `done`.
A evidência final registra 42 testes 4.4, 153 regressões 4.1–4.3 e os dois
verifies aprovados. SPEC `done`; Epic 4 permanece `in-progress`; 4.5 `backlog`.
