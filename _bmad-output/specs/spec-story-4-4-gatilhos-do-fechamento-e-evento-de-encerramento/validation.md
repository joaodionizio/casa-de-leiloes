# Revalidação documental final — Story 4.4

Data: 28/10/2026. Consolidei decisões humanas QH-01–16 recebidas em 27/10/2026.
A avaliação cobre documentos; não executei aplicação, SQL, pytest, Playwright,
verify, migrations, smoke ou deploy, nem review independente.

## Passagem 1 — Coerência

CAP-1–5 preservam IDs e possuem intent/success verificáveis. CAP-6 foi aposentada
por QH-14 e não reutilizada. Constraints eliminam gatilhos de POST, relógio
pré-lock, publicação pré-commit, dados privados, timeouts inventados e abandono
de worker. Detalhes ficam nos companions; non-goals e sinal de sucesso explícitos.
QH-01–16 estão decididas, sem alternativas pendentes no contrato normativo.

Resolvi conflitos antigos com a direção humana atual: seed antes do catch-up,
POST só recusa, evento com as_of=settled_at e deadlines WS10 s preservados.
Atualizei primeiro AD-19/Q4/Q9 e resumos afetados; histórico anterior está
identificado como superado, sem editar a memória canônica ou stories anteriores.

O ciclo não espera rede de cada socket para avançar: publicação pós-commit é
task interna possuída/supervisionada, sem retry periódico, timeout 2 s ou outro
serviço. No shutdown, 30 s são janela global de drenagem, não prova de cancelamento
SQL: excesso loga erro e não autoriza abandonar Session/engine ou declarar
rollback. Limites DB existentes não viram promessa de prazo SQL novo.

Veredito: **PASS**. Conferência estática aprovada antes da promoção, conforme abaixo.

## Passagem 2 — Preservação das decisões

| Decisão/requisito | Contrato e oráculo final |
| --- | --- |
| QH-01/03, cadência 2 s e SKIP local | scheduler-lifecycle-contract; T10/T27/T36 |
| QH-02/13, migrations→seed→catch-up→scheduler→tráfego | scheduler-lifecycle-contract/current-state; T06/T07/T35/T36 |
| QH-04, nove campos e as_of=settled_at | event-contract; T18/T19/T20/T40 |
| QH-05/06, drenar/1000 e snapshot terminal inicial | event-contract; T21/T22/T23/T25 |
| QH-07/08/12, snapshot e invalidação best-effort sem replay | recovery-model/failure-retry-policy; T05/T16/T17/T37/T38 |
| QH-09/10, cooldown local 300 s sem bypass/reparo | failure-retry-policy; T11/T12/T13/T32 |
| QH-11, 200 linhas/50 tentativas/cursor/wrap | scheduler-lifecycle-contract; T33/T34/T35 |
| QH-14, POST sem settlement/transação/evento adicional | SPEC constraints e CA11; T09/T31/T32 |
| QH-15, phase separado de settlement e cliente terminal | event-contract; T22/T23/T24/T38/T40 |
| QH-16, DB existente/WS10 s/drenagem global 30 s | scheduler-lifecycle-contract/failure-retry-policy; T26/T27/T39 |
| Transitórios/COMMIT ambíguo, retry futuro 2–30 s | failure-retry-policy/recovery-model; T14/T15/T37 |
| Corridas reais e autoridade temporal/cumulatividade | concurrency-model; T08/T09/T10/T30 |
| Startup sold/unsold/futuro/cancelado/problemático | T03/T04/T05/T06/T07/T36 |
| Leituras/handshake não liquidam; privacidade | T20/T28/T29; M06/M07 |
| Sem implementação/4.5/infra externa/UX nova | SPEC non-goals/current-state; T40 |

Preservei T01–30 mínimos, T31–40 complementares e M01–08, rederivando os
oráculos afetados. M05 agora exige seed antes de catch-up e recuperação antes
do tráfego. Nenhum cenário planejado é apresentado como teste executado.
Veredito semântico: PASS.

## Conferência mecânica e gate

Executei a conferência documental em Python stdlib, sem importar aplicação ou
configuração do produto. Saída real pré-promoção: **exit 0, errors=[]**.

- 201 arquivos de código/testes/scripts da baseline permaneceram byte a byte idênticos.
- Memória original preservada por prefixo do corpo: somente append pelo writer oficial.
- 5 CAP ativas com intent/success; CAP-6 aposentada; QH-01–16 decididas, sem questão aberta.
- IDs CA01–12, T01–40 e M01–08 completos/únicos; 16 companions e links locais válidos.
- Evento com 9 campos exatos, incluindo as_of derivado de settled_at.
- SPEC/story ainda draft e sprint backlog durante o gate: promoção não foi antecipada.

Depois dos dois PASS semânticos e do gate estático, promovi SPEC/story/sprint
para **ready-for-dev**. Epic 4 permanece in-progress; 4.3 done e 4.5 backlog.
Nenhum estado de outra story mudou. Conferência pós-promoção executada:
**exit 0, errors=[]**; 201 arquivos e inventário de código/testes intactos,
históricos preservados, links/IDs válidos e somente a entrada 4.4 mudou de
backlog para ready-for-dev. Foram alterados 18 documentos, sem código.

Isso comprova consistência documental e preservação do código comparado, não
funcionamento futuro de scheduler/WS/PG. Os testes permanecem planejados;
ready-for-dev não autoriza implementação. Sem review independente nesta sessão.
