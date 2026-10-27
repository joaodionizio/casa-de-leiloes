---
title: 'Story 4.2 — limpar stale público após recuperação'
type: 'bugfix'
created: '2026-10-27'
status: 'in-review'
route: 'oneshot'
---

<frozen-after-approval reason="correção solicitada explicitamente pelo usuário">

## Intent

Corrijo somente o finding manual da Story 4.2: após perda da conexão e refresh
manual falho, um snapshot válido da geração WebSocket atual deve retirar os
avisos públicos de sala/histórico desatualizados, inclusive se os dados forem
iguais aos retidos. Preservo o último estado durante falhas e mantenho mensagens
privadas legítimas de participação/carteira. Não altero arbitragem, heartbeat,
backoff, geração, reconexão nem implemento a 4.3. Entrego para re-review focal,
sem declarar aceite ou mudar o status da story.

</frozen-after-approval>

## Implementation Notes

- Separo o indicador público de desatualização do resultado agregado da rodada,
  que também contém leituras privadas. A época pública impede falha REST anterior
  ao snapshot de recolocar stale.
- Arquivos previstos: `frontend/src/LotPage.tsx`,
  `frontend/e2e/lot-room-ws.spec.ts`, story 4.2, `docs/uso_de_ia.md` e esta nota.
- Regressão: sala conectada → perda → refresh 503 → avisos stale → reconexão →
  snapshot igual/mais novo → conectada sem avisos públicos, com preço/histórico
  preservados e mensagens privadas de falha mantidas.
- Validação solicitada: testes direcionados, `./verify.sh` e
  `VERIFY_E2E=1 ./verify.sh`, sem Git ou leitura de `.env*`.
- Implementei a marcação `publicStale` em `LotPage.tsx`, independente de `sync`,
  e a limpeza por snapshot antes dos retornos da arbitragem/estado igual. Mantive
  os erros privados e o restante da coordenação de rodadas.
- A checagem interna encontrou a ordem snapshot igual → falha REST antiga;
  movi o avanço da época pública para cada snapshot e acrescentei um quinto
  caso Playwright. Rechecagem interna: nenhum defeito concreto restante.
- Direcionados finais: 71 testes Playwright aprovados. `./verify.sh`: exit 0,
  2079 backend e 175 frontend, Ruff/format, ESLint, tsc, Vite e Docker passaram.
  `VERIFY_E2E=1 ./verify.sh`: exit 0, 2079 backend, 175 frontend,
  218 E2E aprovados e 5 opt-in skipped; demais etapas passaram. Não executei
  novamente os opt-in de pilha real ou smoke Render. Entrego para re-review focal.


## Correção focal MEDIUM — estado privado independente (27/10/2026)

Autorizei nesta sessão somente corrigir o finding do re-review: dados privados
retidos após 503 precisam de aviso próprio, mesmo depois de snapshot público.
Mantenho a nota e a Story 4.2 em review, sem antecipar a 4.3.

Decidi representar a validação de `/mine` explicitamente como `unconfirmed`,
`confirmed` ou `stale`, e a falha da carteira como `walletStale`, independente de
`publicStale`. Descartei inferir confirmação de `ready` ou só do pareamento.
Ao iniciar uma leitura privada, oculto posição anterior e preservo erro existente;
só resultado privado vigente bem-sucedido confirma participação/limpa sua falha.
Preservo saldo anterior com aviso textual em caso de falha. Troca de conta remove
estado privado da conta anterior. O 201 preserva o aviso até o GET privado vigente ter sucesso.

Arquivos desta correção: `frontend/src/LotPage.tsx`,
`frontend/src/LotBidPanel.tsx`, `frontend/e2e/lot-room-ws.spec.ts`, esta nota,
story 4.2 e `docs/uso_de_ia.md`. Sem mudanças em arbitragem, transporte ou backend.
Acrescentei matriz de `/mine`, carteira e ambos falhando depois de sucesso inicial,
snapshot idêntico e recuperação privada posterior, além de sucesso privado
substituído chegando após falha nova. Validação e mutação concluídas; resultados abaixo.


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
