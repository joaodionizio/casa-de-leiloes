# Story 4.2 — Heartbeat e reconexão automática

Status: **review** — implementada e verificada em 27/10/2026; pronta para meu teste manual. Code review ainda não executado.
Chave canônica no sprint: `4-2-heartbeat-e-reconexao-automatica` (ASCII, conforme pedido de consolidação). Preservo o nome existente deste arquivo; não existe segunda story.

## Objetivo e autorização

Como visitante, licitante ou leiloeiro, quero perceber a perda das atualizações e recuperar automaticamente a sala por snapshot completo, preservando o último estado válido e sem repetir comandos.

Decidi QH-01–16 e autorizei somente consolidar documentação e marcar ready-for-dev. **Não autorizei implementação nesta sessão.** Sem Git, leitura de .env*, banco, testes de aplicação, deploy ou início da 4.3.

## Contrato canônico final

- [SPEC.md](../specs/spec-story-4-2-heartbeat-e-reconexao-automatica/SPEC.md): CAP-1–4, constraints, exclusões e sinal de sucesso.
- [Máquina de conexão](../specs/spec-story-4-2-heartbeat-e-reconexao-automatica/connection-contract.md): seis estados e T01–T25 reavaliadas; backend, corridas, UX, segurança, limites e arquivos prováveis.
- [Decisões humanas](../specs/spec-story-4-2-heartbeat-e-reconexao-automatica/human-decisions.md): QH-01–16 decididas, alternativas descartadas e detalhamento derivado.
- [Critérios e plano de testes](../specs/spec-story-4-2-heartbeat-e-reconexao-automatica/acceptance-and-tests.md): CA01–18; F01–20, B01–07, PG01–05, E01–08 e roteiro manual em dois contextos.
- [Autovalidação final](../specs/spec-story-4-2-heartbeat-e-reconexao-automatica/validation.md): coerência e preservação; não review independente.

## Decisões consolidadas

Ping/pong JSON correlacionado, só transporte. Ping a cada 20 s entre envios, uma pendência, pong em 10 s; silêncio do cliente no servidor em 60 s. Zero SQL ou snapshot por heartbeat. Deadline total de conexão/snapshot 30 s. Open não conecta; snapshot conecta; primeiro pong adicional da nova geração reseta backoff.

Backoff exponencial base 1 s, teto 30 s, equal jitter 50–100%, RNG controlável; tentativas indefinidas enquanto elegível/montado. Offline invalida/fecha e cancela timers, preservando sala; online elegível abre uma tentativa imediata deduplicada. Visible recalcula deadlines e executa no máximo uma ação imediata, sem reproduzir ticks perdidos.

Descartei esperar CLOSED: invalido geração anterior, retiro autoridade, chamo close e permito substituto sem esperar TCP. Aceito sobreposição física curta, nunca dois sockets autoritativos. Callbacks/timers antigos são inertes. Cancelamento explícito e unmount são terminais; REST 404 encerra genericamente sem presumir cancelamento; transporte/rede/timeouts e REST 5xx permanecem recuperáveis. Confirmação pública REST quando necessária, sem polling ou endpoint novo.

Deadline backend de send/close relevante é 10 s por operação; isolar travado sem prender outros nem segurar trava aguardando rede. **QH-11/12 explicitamente adiadas:** sem teto de conexões medido e sem timeout arbitrário pós-commit D-A. Esses riscos estão aceitos/documentados, não são questões humanas abertas.

## Invariantes e fronteiras

Preservo AD-10/25, um processo/manager em memória, comandos REST, snapshot completo primeiro em toda conexão, publicação pós-commit e políticas públicas/Origin/JWT. shouldApplyRoom continua exclusivo para estado público, sem reimplementação pela máquina; bid_count primário, as_of desempate, terminal prevalente. Dados válidos continuam visíveis em connecting/reconnecting/unavailable; GET/201 não provam saúde WS.

Fora: fechamento/liquidação, scheduler/catch-up, resultado/comprovante, Redis/broker/outbox, vários workers, replay, migrations, alterações financeiras e 4.3.

## Fontes e tracking histórico

Fontes da criação: CLAUDE, ARQUITETURA, FRONTEND-WORKFLOW, README, DESIGN, EXPERIENCE, Story 4.1, uso_de_ia e sprint; trecho 4.2 de epics e código do transporte. Nesta consolidação, o pedido humano e a memória canônica determinam as mudanças; recomendações anteriores incompatíveis foram substituídas no contrato, não apenas anotadas.

A confirmação humana atual considera 4.1 concluída/aprovada; seu tracking ainda em review permanece histórico e não foi alterado nesta tarefa. Não atribuo novo review ou smoke Render a essa confirmação. Epic 4 continua in-progress e 4.3 backlog.

## Resultado documental

Nenhuma questão humana aberta para esta story. Spec validada quanto a coerência/preservação e pronta para desenvolvimento; build aguarda instrução separada. Nenhum resultado de teste de aplicação é alegado nesta etapa.

## Build autorizado — 27/10/2026

Autorizei nesta sessão implementar somente a 4.2 conforme a spec aprovada, executar os testes e smoke local. As restrições documentais anteriores registram a sessão de especificação. Sem Git, leitura de `.env*`, code review ou início da 4.3.


## Entrega do build — 27/10/2026

Implementei somente heartbeat/reconexão conforme QH-01–16, com seis estados,
geração autoritativa, deadlines, backoff/jitter, snapshot obrigatório, offline/online,
visible sem rajada e terminais WS/REST. Preservei shouldApplyRoom/sameRoomState
idênticos à partida, domínio financeiro e adiamentos QH-11/12.

- [x] Backend heartbeat sem SQL/snapshot, silêncio 60 s e send/close 10 s, isolamento/cleanup.
- [x] Máquina frontend e integração; snapshot 30 s, ping 20 s/pong 10 s; reset só snapshot+pong.
- [x] F01–20/B01–07/PG01–05/E01–08 executados com rastreabilidade, banco real nos PG.
- [x] Direcionados: 70 backend, 175 frontend, 66 E2E de sala/WS.
- [x] `./verify.sh`: exit0, 2079 backend/175 frontend, demais etapas passaram.
- [x] `VERIFY_E2E=1 ./verify.sh` final: exit0, 2079 backend/175 frontend/213 E2E,
  5 opt-in skipped; Ruff/format, ESLint, tsc, Vite e Docker passaram.
- [x] 5 opt-in de pilha real executados separadamente via Vite: passaram.
- [x] Smoke WS real pelo Vite: duas abas, StrictMode, ping/pong, offline/online,
  evento perdido recuperado por snapshot, callbacks aposentados, backend derrubado e
  reiniciado, atualizações nas duas abas, cliente silencioso expulso e 320 px sem overflow.
- [ ] Meu teste manual de aceitação.
- [ ] Code review independente em sessão posterior, conforme meu pedido.

[Evidência completa do build](../specs/spec-story-4-2-heartbeat-e-reconexao-automatica/implementation-evidence.md)
registra comandos/resultados, correções de fixtures/expectativas, arquivos extras e
limitações. Nenhuma divergência funcional conhecida da spec; nenhum Git, `.env*`,
deploy ou início da 4.3. Não considero a story done antes da minha aceitação/review.

## Finding manual — avisos stale após reconexão (27/10/2026)

No teste manual, observei que, após desconexão e refresh manual falho, a sala
voltava a mostrar conexão ativa por snapshot, mas conservava os avisos de falha
de atualização e histórico possivelmente desatualizado. O caminho de estado
público igual só reancorava o relógio; o resultado agregado da rodada também
misturava falhas públicas e privadas.

Autorizei corrigir somente esse finding. Separei a marcação pública de stale
das falhas da rodada: snapshot válido da geração atual limpa os avisos públicos,
inclusive se o estado for igual ou a arbitragem conservar dados mais novos.
Falha REST pública anterior ao snapshot não pode recolocar stale. Preservei
dados conhecidos, falhas legítimas de participação/carteira, arbitragem,
heartbeat, backoff, geração e reconexão. Descartei limpar indiscriminadamente
todos os erros da página, pois isso ocultaria falhas privadas reais.

Adicionei regressões Playwright para snapshot igual/mais novo, cada um com e
sem falhas privadas. Reproduzem sala conectada → perda → refresh 503 → ambos os
avisos stale → abertura ainda sem recuperação → snapshot → conectada sem avisos
públicos, com preço/histórico visíveis e erros privados preservados. Antes da
correção, os dois casos de snapshot igual falharam no aviso persistente; os dois
de snapshot mais novo passaram. Ajustei também um teste existente para exigir
a mensagem de falha privada, sem marcar o histórico público como stale quando
a leitura pública teve sucesso; mantive as garantias de POST ambíguo.

Mantenho a Story 4.2 em **review**, aguardando re-review focal e minha aceitação.
Não executei Git, não li `.env*`, não fiz deploy e não iniciei a 4.3.

Validação final desta correção:

| Comando | Resultado real |
| --- | --- |
| `npx playwright test e2e/lot-room-ws.spec.ts e2e/lot-room.spec.ts --workers=2` | exit 0; `71 passed (16.8s)` |
| `./verify.sh` | exit 0; `2079 passed, 1 warning in 105.05s`; frontend `tests 175`, `pass 175`, `fail 0`; Ruff/format, ESLint, tsc, Vite e Docker passaram |
| `VERIFY_E2E=1 ./verify.sh` | exit 0; `2079 passed, 1 warning in 98.36s`; frontend `tests 175`, `pass 175`, `fail 0`; `218 passed (25.7s)`, `5 skipped`; demais etapas passaram; `verify.sh: todas as etapas passaram.` |

O quinto caso focal protege snapshot igual → falha REST antiga: incrementei a
época das leituras públicas em todo snapshot, preservando a rodada privada.
A checagem interna da correção terminou sem defeitos concretos restantes; não
substitui o re-review focal solicitado. O warning backend é a depreciação
Starlette/httpx preexistente. Os 5 skipped continuam sendo os opt-in de pilha real;
não os reexecutei nesta correção.

Executei os comandos com dotenv desabilitado em uv/Python/Compose e proteção
temporária de leitura no Node, fora do produto; loopback exigiu execução elevada.
Não alterei verify/configuração da aplicação para isso. Logs locais:
`/tmp/atrio42-stale-targeted-final.log`, `/tmp/atrio42-stale-verify.log` e
`/tmp/atrio42-stale-verify-e2e.log`. Arquivos da correção: `LotPage.tsx`,
`lot-room-ws.spec.ts`, esta story, `docs/uso_de_ia.md` e a nota focal
`spec-4-2-correcao-stale-publico.md`. O Playwright regenerou
`frontend/test-results/.last-run.json`, fora da lista prevista de fontes.


## Correção focal MEDIUM — falhas privadas após sucesso (27/10/2026)

Autorizei corrigir exclusivamente o finding do re-review focal, sem reabrir a
4.2 nem iniciar a 4.3. Separei a confirmação de `/mine` (`unconfirmed`,
`confirmed`, `stale`) do estado de carregamento dos dados retidos; registrei
`walletStale` independentemente de `publicStale`. Descartei tratar `ready` como
confirmação da rodada vigente. Saldo anterior permanece visível acompanhado do
aviso de carteira; posição/último lance próprios ficam ocultos durante validação
ou falha, preservando M1. Só resposta privada atual, não substituída, pode limpar
a falha correspondente; snapshot público não altera os indicadores privados.

Acrescentei quatro casos Playwright: matriz com falha posterior de `/mine`,
carteira e ambos, depois de sucesso inicial, recuperação por snapshot idêntico e
sucesso privado posterior; e resposta privada substituída após falha mais nova.
No caso de ambos, testo também recuperação individual de cada recurso sem
apagar o erro do outro. A primeira execução teve 74 passed e uma expectativa
incorreta da fixture: `/mine` bem-sucedido com sala REST falha não produz par
vigente. Ajustei o caso isolado da carteira para sala e `/mine` bem-sucedidos,
sem afrouxar M1. Não alterei arbitragem, heartbeat, backoff, geração, política de
reconexão, terminais ou backend.

Mutação executada: fiz snapshot marcar `/mine` confirmado e limpar `walletStale`.
O cenário principal (ambos) falhou justamente na ausência indevida do aviso
privado após snapshot; Playwright exit 1, `1 failed`. Restaurei o fonte em
`finally` e conferi igualdade com o original. O código mutante não é a entrega.
Validação final concluída; mantenho status review para novo re-review focal.


Validação já concluída desta correção privada: direcionados finais
`75 passed (18.8s)`; `./verify.sh` exit 0 com
`2079 passed, 1 warning in 100.57s`, frontend `tests 175`, `pass 175`, `fail 0`.
Ruff/format, ESLint, TypeScript, Vite e Docker passaram. A mutação teve exit 1
com `1 failed` no cenário principal após snapshot; fonte original restaurado.
A checagem interna focal final não encontrou defeito concreto aberto.
`VERIFY_E2E=1 ./verify.sh` exit 0: `2079 passed, 1 warning in 99.41s`,
frontend `tests 175`, `pass 175`, `fail 0`, Playwright `222 passed (26.9s)` e
`5 skipped` (opt-in de pilha real). Ruff/format, ESLint, TypeScript, Vite e Docker
passaram; ambos os gates terminaram com `verify.sh: todas as etapas passaram.`
O warning backend Starlette/httpx continua preexistente. Não reexecutei pilha
real nem smoke Render nesta correção.

Usei as proteções temporárias externas já existentes contra dotenv em
uv/Python/Compose e leitura de `.env*` no Node; o sandbox bloqueou loopback na
primeira tentativa dos direcionados, que rodei com acesso elevado. Não alterei
verify nem configuração da aplicação. O Playwright regenerou somente
`frontend/test-results/.last-run.json` fora dos seis arquivos previstos;
nenhum arquivo de segredo alterado foi detectado pela checagem de nomes.
Não executei Git, não li `.env*`, não fiz deploy e não iniciei a 4.3.
Parei com a correção pronta para novo re-review focal, sem declarar aceite final.


## Cobertura focal — sucesso privado superseded realmente entregue (27/10/2026)

Corrigi somente a lacuna de cobertura apontada no re-review: o teste anterior
abortava os GETs antigos, portanto sua liberação não provava descarte de sucesso
privado pela lógica de aplicação. Descartei usar aborto de fetch como evidência
de sucesso superseded entregue. Não alterei produção: comparei `LotPage.tsx`
e `LotBidPanel.tsx` byte a byte com a partida após restaurar a mutação.

Substituí o caso no spec WS por uma sequência determinística A/B/C. Um adaptador
de fetch instalado só neste teste remove o signal unicamente das duas chamadas
HTTP de A, preservando os sinais e gerações originais usados por `loadPrivate`.
A requisição continua sendo HTTP real interceptado pelo Playwright; não simulei
`fetchMyBids`, `fetchWallet`, os validadores nem o resultado de `isCurrent`.
Espero os dois handlers de A entrarem na barreira antes de iniciar B. B responde
503 e o teste espera os dois avisos privados e o fim da rodada. Só então libero
A com HTTP 200 e corpos válidos de participação/carteira. Registro dentro de
`Response.json` os corpos consumidos, status 200 e sinais originais já abortados,
provando que o transporte de A entregou sucesso mesmo após a substituição lógica.
Depois de ambos os JSONs resolvidos, espero dois frames para as continuações da
aplicação e o commit do React. Exijo avisos presentes, posição antiga oculta,
saldo conhecido de R$ 4.890,00 preservado contra R$ 890,00 de A, preço/histórico
públicos mantidos. C vigente tem sucesso, mostra posição/saldo atuais de
R$ 6.000,00 e remove ambos os avisos.

Mutação executada: permiti que resultados privados bem-sucedidos ignorassem a
guarda `round.isCurrent()`. O teste passou pelas comprovações de entrega dos dois
HTTP 200 e falhou depois porque o aviso de carteira havia sido removido:
Playwright exit 1, `1 failed`. Restaurei automaticamente o fonte em `finally` e
conferi igualdade byte a byte. A checagem interna independente do teste não
encontrou defeito concreto de cobertura. Nenhum defeito funcional foi revelado.
Somente o spec de testes e os três documentos desta correção foram editados;
validação final concluída. Mantenho a Story 4.2 em review para novo re-review,
sem aceite final, Git, leitura de `.env*`, backend ou início da 4.3.


Validação final da cobertura superseded:

| Gate | Resultado real |
| --- | --- |
| `npx playwright test e2e/lot-room-ws.spec.ts --workers=2` | exit 0; `33 passed (8.0s)` |
| `./verify.sh` | exit 0; `2079 passed, 1 warning in 102.63s`; frontend `tests 175`, `pass 175`, `fail 0` |
| `VERIFY_E2E=1 ./verify.sh` | exit 0; `2079 passed, 1 warning in 100.04s`; frontend 175/175; `222 passed (23.9s)`, `5 skipped` |

Ruff/format, ESLint, TypeScript, Vite e Docker passaram em ambos os gates,
encerrados com `verify.sh: todas as etapas passaram.` Os cinco skips são opt-in
de pilha real, não reexecutados nesta tarefa; o warning backend Starlette/httpx
é preexistente. Mantive as proteções externas já existentes contra leitura de
`.env*` em uv/Python/Compose/Node, sem mudar verify ou configuração da aplicação.
A mutação terminou com exit 1 e `1 failed`, como esperado; o fonte foi restaurado.

Entrega: somente `frontend/e2e/lot-room-ws.spec.ts`, story 4.2,
`docs/uso_de_ia.md` e nota focal; o Playwright regenerou
`frontend/test-results/.last-run.json` fora da lista prevista. A comparação
final de `LotPage.tsx` e `LotBidPanel.tsx` com a partida confirmou conteúdo
idêntico. Não detectei arquivo de segredo alterado pela checagem de nomes.
Nenhum finding interno aberto. Parei pronta para novo re-review focal.
