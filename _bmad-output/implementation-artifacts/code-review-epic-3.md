# Code review Epic 3 — Carteira e lances íntegros

Status: **CORREÇÕES NECESSÁRIAS**. Review agregado do conteúdo atual em sessão independente, 26/10/2026, America/Maceio. Epic 3 permanece **`in-progress`**; Stories 3.1–3.6 permanecem `done`. Nenhum status alterado.

| Identificação | Registro |
| --- | --- |
| Responsável | Sessão independente solicitada por Joaodionizio, duas lentes auxiliares (backend/frontend) e triagem principal |
| Modelo | GPT-6.1 Sol Medium, conforme configuração informada pelo orquestrador; esta sessão não implementou as stories |
| Candidato | Arquivos vivos autorizados pelo pedido; branch/commit e correspondência local/remota não demonstrados |
| Comparação | Sem diff histórico fornecido e sem Git; revisão de integração do estado atual, sem certificar diff histórico completo |
| Decisão humana | Pendente; nenhum finding corrigido ou dispensado nesta sessão |

Fontes consultadas: `CLAUDE.md`, `docs/FECHAMENTO-DE-EPICO.md`, `docs/AUDITORIA-PROCESSO-EPIC-3.md`, `docs/ARQUITETURA.md`, `README.md`, `docs/uso_de_ia.md`, `deferred-work.md`, as seis stories (contratos, critérios e registros pertinentes), specs relevantes das seis stories, DESIGN/EXPERIENCE e código/testes reais. Registros históricos não substituíram fontes atuais.

Relação agregada inspecionada: `backend/app/{money,wallet,bid_rules,bid_integrity,bids,lot_cancellation,lots,seed,db,main,access,csrf,errors}.py`; migrations 0004–0006 e dependências de schema; testes puros de regras/integridade/gate e integração de carteira, bids, leituras, cancelamento, seed, migrations e concorrência cruzada; `frontend/src/{App,LoginForm,LotPage,LotBidPanel,BidForm,WalletPage,MyLots}.tsx`, clientes HTTP, registros pendentes, feedback, posição, countdown e navegação; testes puros e E2E pertinentes, especialmente sala/carteira/MyLots. Review conjunto, sem repetir seis reviews individuais. Apliquei a skill bmad-code-review com overrides locais e lentes de integração; não executei cada camada genérica como um agente distinto.

Limites: inspeção dirigida, sem leitura exaustiva de cada linha de todas as suítes, reprodução visual, carga, produção ou comparação histórica. Não houve teste novo nesta sessão.

**Gate prévio não demonstrado:** `docs/uso_de_ia.md:866` registra `VERIFY_E2E=1 ./verify.sh` verde na 3.6 (2036 backend, 158 front, 189 Playwright), mas `:869`–`:873` registra mudança posterior nas assertions, seguida apenas de três execuções focadas, sem verify completo posterior. Auditoria e deferred-work confirmam a lacuna. `/private/tmp/verify_out.txt` termina “todas as etapas passaram”, porém registra 1987 backend, 145 front e 156 Playwright/5 skipped, sem cancellation tests: é anterior à 3.6. Seu mtime é 26/10/2026 21:00:08, anterior ao teste concorrente atualizado. `/private/tmp/atrio-3-3-verify.log` também é histórico. Não usei esses logs como prova do candidato final e não rodei verify para suprir o gate. Concluí análise estática, sem aprovação técnica de fechamento.

## 1. Findings

**0 HIGH, 1 MEDIUM, 0 LOW novos.** Contagem dos findings triados, não de testes executados.

### F-01 — Sala pode permanecer bloqueada quando o envio termina durante a remontagem

**Severidade:** MEDIUM.

**Stories afetadas:** 3.5, integração com navegação/auth e padrão de envio da 3.1. A mesma janela na carteira já foi aceita como LOW-1 opcional; não reclassifico retroativamente essa decisão.

**Arquivos:** `frontend/src/LotPage.tsx:113`, `:445`, `:370`, `:338`; `frontend/src/bidSubmission.ts:43`; `_bmad-output/specs/spec-story-3-5-dar-lance-pela-sala-do-lote/frontend-flow.md:68`. Precedente herdado: `WalletPage.tsx:46`, `:133`, `walletDeposit.ts:55` e Story 3.1:769.

**Problema:** A montagem salva só `submitting=true` ao encontrar envio pendente. O efeito consulta novamente `pendingBidOf` para acompanhar a operação. O `finally` da promise apaga a entry ao terminar. Se isso ocorrer entre render e efeito, este encontra `null` e sai; nenhum consumidor dessa montagem chama `handleOutcome`, que retiraria o bloqueio. A spec da sala exige expressamente capturar a própria entry na primeira renderização para evitar o problema conhecido da carteira.

**Cenário concreto:** O licitante envia lance, sai da sala e retorna com POST pendente, por exemplo após login na mesma conta. `LoginForm.tsx:42`–`:45` chama `App.handleLoggedIn` depois de await. A montagem encontra a entry e inicializa submitting/ref como true. O POST termina antes do passive effect e remove a entry; o efeito retorna sem acompanhar o resultado. A montagem anterior já foi desmontada e ignora a resposta. Leituras iniciais carregam dados, mas não zeram submitting.

**Impacto:** Campo, “Dar lance” e “Atualizar sala” ficam bloqueados mesmo com a operação concluída; o gatilho de zero também não sincroniza. Recuperação exige outra navegação/remontagem; o feedback do aceite/recusa pode se perder. Não há corrupção ou duplicação de dinheiro no backend.

**Evidência e limite:** Interleaving demonstrado por leitura do componente/registro e scheduler instalado React DOM 19.3.1: `react-dom-client.development.js:1495` usa prioridade padrão em atualizações assíncronas sem evento; `:19554` agenda passive effects em callback normal; `:20016` força flush imediato apenas para lanes síncronas. Portanto o retorno assíncrono após login não garante execução do efeito antes da resolução. Não reproduzi o timing no navegador nesta sessão. Os testes `lot-room.spec.ts:296` e `wallet.spec.ts:331` mantêm POST pendente até depois de a montagem acompanhar a promise; não isolam essa janela.

**Correção recomendada:** Capturar a entry inicial na montagem e acompanhar sua própria promise mesmo que já tenha saído do registro global, preservando conta/lote/montagem e barreira contra segundo POST. Não exige refatoração geral. Corrigir a carteira continua sujeito à decisão humana de seu LOW opcional.

**Teste necessário:** Teste focado de componente/scheduler: capturar entry durante render, liquidar promise antes do passive effect, executar efeito e verificar resultado original, desbloqueio do campo/lance/refresh e exatamente um POST. Cobrir aceite e recusa/ambiguidade, sem retry automático.

**Decisão humana / estado:** **CORRIGIDO — AGUARDANDO RE-REVIEW.** `LotPage` captura a entry na primeira renderização (`capturedBid`) e o efeito usa `bidToFollow` (`bidSubmission.ts`), sem depender de segunda consulta ao registro. Teste puro em `bidSubmission.test.ts`; `VERIFY_E2E=1 ./verify.sh` posterior à correção, exit 0. Re-review pendente; Epic 3 segue `in-progress`.

Triagem rejeitada: formulário antigo imediatamente após lot_cancelled não virou finding. A spec 3.6 preserva deliberadamente o tratamento de recusa da sala e exibe “Este lote foi cancelado.”; refresh explícito/reentrada trata o 404 do detalhe. Ausência de WebSocket é deliberada. Limites documentados de âncora v1, rotação, idempotência e timeout não foram convertidos em bugs novos.

## 2. Money/wallet

**OK**, por inspeção. Centavos inteiros/BIGINT, teto compartilhado e CHECKs mantêm total/comprometido não negativos e committed ≤ total; disponível é derivado. Lance lê disponível sob lock, soma compromisso novo e subtrai somente compromisso anterior daquele lote, preservando outros lotes. Totais não mudam. Cancelamento não consulta nem altera wallets. Depósito trava só sua carteira e preserva committed. Transação única e testes reais de rollback protegem contra efeitos parciais.

## 3. Bid transaction

**OK**, por inspeção. `place_bid` compõe evaluate_pre_wallet/post_wallet sem duplicação: período → mínimo → líder → saldo. lot_cancelled é guarda operacional posterior ao gate. HTTP preserva semântica e códigos. Um clock_timestamp pós-lock alimenta período, extensão, bytes e placed_at. UPDATE wallets, INSERT bid e UPDATE final coerente de lote pertencem à mesma transação. Não encontrei outro writer operacional de histórico/estado autenticado fora do protocolo.

## 4. Concurrency

**OK**, por inspeção. Lote primeiro, wallets por UUID crescente, refresh populate_existing; depósito não solicita lote depois de wallet. Cancelamento trava só lote. Testes PostgreSQL forçam sobreposição, líderes cruzados, controle negativo de deadlock, depósito × lance nas duas ordens e hora pós-espera. Cancel × first bid cobre ambas as ordens, HTTP e corrida livre; oráculo atual compara todas as wallets, cadeia/âncora e lote. Não encontrei terceiro estado permitido pelos escritores atuais. Não é medição de carga.

## 5. Integrity

**OK**, por inspeção. Alias persistido; JSON v1 ordenado/minimal UTF-8, timestamp UTC com seis casas, genesis, previous_hash, SHA-256 e HMAC anterior. Gate autentica cadeia, count/final_hash e vínculo do último bid ao líder/valor antes das regras. Só o alias do líder atual é recalculado para esse vínculo; aliases históricos permanecem persistidos. place_bid/cancel_lot compartilham gate; âncora nula falha fechado sem reassinatura. Criação/seed assinam apenas lote novo. Saldos/termos/dono/cancelamento e rollback conjunto de cadeia+âncora antigas ficam fora da garantia v1, conforme docs.

## 6. Anti-sniping

**OK**, por inspeção. Aceite com 0 < remaining ≤ 120s soma 120s ao fim corrente sob lock; exatamente no fim recusa e nunca reabre. Testes puros provam cumulatividade; PostgreSQL prova que segundo concorrente lê fim estendido e não o estende indevidamente. Sala aplica ends_at do 201/GET; countdown monotônico não decide fase nem bloqueia envio em zero. Consequências de F-01 estão em Room/frontend.

## 7. Room/frontend

**AJUSTAR — F-01.** Valor/mínimo/histórico/alias/posição/fim vêm dos contratos atuais. 201 precede releitura; gerações/abort descartam respostas antigas e pares de rodada ocultam posição desatualizada. Cliente valida formato, sem impor mínimo/saldo/tempo. Recuperação do envio durante remontagem, porém, não cumpre captura da entry exigida pela spec.

## 8. Cancellation

**OK**, por inspeção. Dono antes do gate; gate antes de idempotência/contagem; primeiro cancelamento exige vazio e now < ends_at. Repetição íntegra preserva timestamp sem UPDATE. Só cancelled_at muda. Público oculta cancelados; filtros nos JOINs preservam as_of e MyLots mantém item do dono. Confirmação inline, barreira síncrona e erro ambíguo conservador acompanham contrato. Sem cancelamento com bids nem estorno antecipado.

## 9. Privacy/security

**OK**, no escopo inspecionado. Policies separam bidder em carteira/lance/mine de auctioneer em cancelamento próprio. Origin/Referer/JSON protegem todas as escritas, inclusive cancelamento sem corpo. GETs não alteram estado. DTOs públicos explícitos não expõem identidade real, hashes/HMAC ou segredos; /mine só fornece participação apropriada da sessão e histórico usa alias persistido. no-store está nos sucessos/erros de negócio pertinentes; ausência herdada no 422 global/500 é limite explícito da spec. Códigos solicitados têm status/semântica coerentes; frontend usa code, não texto.

## 10. Migrations

**OK**, por inspeção. 0004 cria/backfill wallets; 0005 cria bids/resumo/âncora; 0006 acrescenta cancelled_at nullable sem relógio/default/backfill. Ordem, dependências, schema e models coerentes; legado não é autenticado automaticamente. Testes anteriores contemplam head posterior e restauram head. Downgrades perdem dados removidos, limite documentado de desenvolvimento; não exigi rollback impossível desses dados. Nenhuma migration executada nesta sessão.

## 11. Seed

**OK**, por inspeção. Usuários fixos/wallets faltantes sem zerar saldos. Fixture offline e create_lot criam demo novo com cadeia vazia/âncora, sem fabricar bids. Cancelado/legado não impede novo demo nem é reativado/reassinado. Advisory lock serializa seed e hora vem do banco. Predicado exige presença, não valida assinatura da âncora, limite explícito com gate operacional preservado. Startup é migrations → seed → servidor; catch-up fica na 4.4.

## 12. Tests

**AJUSTAR.** Arquitetura adequada: regras/golden vectors puros, PostgreSQL real, concorrência forçada/controle negativo, ataques ao gate, contratos/policies e Playwright simulado. Não encontrei propriedade crítica de dinheiro/locks protegida apenas por mock. Falta teste focado de F-01 e comprovação do verify completo final pós-assertions da 3.6. E2E simulado não prova produção; pilha real opcional não foi executada aqui.

Comandos efetivos: leituras/buscas via cat/sed/head/tail/rg/ls/stat, busca restrita de logs em /private/tmp, leitura do scheduler React instalado e escrita deste artefato. Tentativas iniciais uv dos resolvers de customization/config falharam no cache por permissão, antes da execução; resolvi configuração/overrides por leitura. Busca de logs encontrou uma subpasta de sistema inacessível e não a contornei. **Nenhum teste, verify, mutação, migration, servidor ou navegador executado nesta sessão.** Números anteriores são históricos identificados. A primeira tentativa de substituir este artefato via apply_patch foi recusada pelo formato, sem mudança; a gravação seguinte foi única e localizada.

## 13. Docs

**OK**, com divergência funcional da spec da sala registrada em F-01. README/arquitetura/uso de IA distinguem funcionalidades entregues de WebSocket/liquidação/auditoria futura e documentam limites reais. Seções antigas das stories são histórico, não contrato do runtime. Processo é honesto sobre verify/merge/deploy pendentes. Evidências futuras exigem atualização real, sem aprovação humana ou publicação fictícias neste review.

## 14. Deferred work

**OK**, quanto à classificação atual dos itens relacionados ao épico.

| Item | Situação |
| --- | --- |
| Gate 3.6, filtros públicos/seed de cancelados, writers da 3.4 | Resolvidos/contextualizados como histórico pela nota administrativa final |
| Committed na 3.4, lote antes de wallets, populate_existing | Implementados e exercitados em testes cruzados |
| Idempotência depósito/lance, COMMIT ambíguo, ledger | Ainda válidos; não implementados, limites explícitos |
| Contagem de wallets no log do seed | Ainda ausente; limitação operacional pequena |
| Autenticação administrativa de legado | Ainda futura, sem fallback automático |
| Rotação de segredos | Ainda não suportada, efeitos documentados |
| Lock/statement timeout e retry de deadlock | Ainda ausentes por decisão de escala |
| UPDATE único de lote e CHECK não adiável | Implementado; eventual pitfall em CLAUDE depende da decisão já registrada |
| Liquidação/terminal/auctioneer fora da âncora/estorno | Obrigações futuras 4.3/6.6 |
| Catch-up antes de seed/tentativa de lance | Futuro da 4.4 |
| Snapshot da auditoria pública | Futuro da 5.1; sala atual já usa statement único |
| Cumulatividade/T-SNIPE | Limite integrado explícito; prova pura e concorrente complementares |
| Componentes/E2E/opt-in | E2E evoluiu para carteira/sala/MyLots; componente isolado/browsers extras continuam limites |
| Verify/reviews/merge/deploy do fechamento | Evidências e decisões ainda pendentes; este review executado tem correção aberta |

LOW-1 de remontagem da carteira já consta da decisão da Story 3.1. F-01 registra propagação na sala, cujo contrato exigia evitá-la. Não escrevi em deferred-work/stories nem inventei dívida genérica.

## 15. Scope

**OK.** Sem WebSocket, settlement, receipt ou auditoria pública final antecipados. Fundamentos criptográficos/gate/read models são intencionais. Scheduler/catch-up e fluxos dos Epics 4/5 permanecem futuros; nenhum próximo épico iniciado.

## 16. Complexity

**COMPLEXA MAS ACEITÁVEL.** Backend mantém primitives puros/transações explícitas sem framework genérico. Sala coordena respostas fora de ordem, sessão, remount, overlay do aceite e countdown; isso explica sua complexidade. F-01 pede correção localizada da posse da promise, sem refatoração estética ou nova infraestrutura.

## 17. Recommendation

**CORREÇÕES NECESSÁRIAS**

F-01 MEDIUM permanece aberto; não aprovo fechamento técnico. Falta também demonstrar verify completo final e correspondência do candidato/base conforme processo. Após decisão/correção autorizada: teste focado, verify completo/E2E pertinente e re-review da correção. Mudança de código/testes invalida evidência anterior pertinente. Gate de diff histórico continua sem comparação fornecida.

Nenhuma correção/dispensa presumida. Merge/deploy/smoke são etapas separadas. Único arquivo alterado: este artefato. Nenhum Git/gh, deploy, leitura de .env*/credenciais ou alteração de status. Epic 3 permanece **in-progress**. Trabalho encerrado neste review.

---

## Re-review focado de F-01 — 26/10/2026

Sessão independente GPT-6.1 Sol Medium, conforme configuração solicitada ao orquestrador. Inspecionei exclusivamente a correção de F-01 em `frontend/src/LotPage.tsx`, `frontend/src/bidSubmission.ts`, `frontend/src/bidSubmission.test.ts`, os cenários pertinentes de `frontend/e2e/lot-room.spec.ts` e o registro atualizado acima; consultei `CLAUDE.md` como instrução local. Não executei o workflow agregado novamente, testes nem verify. Acrescentei somente este registro. As conclusões abaixo substituem as conclusões históricas sobre F-01 e a falta de verify posterior; não certificam os demais gates. Epic 3 continua **`in-progress`**.

### 1. Bug produtivo

**CORRIGIDO.** Em R1–R3, `LotPage.tsx:115` captura a própria entry no estado `capturedBid`; `:118` inicializa `submitting` pela existência dessa referência. Em R4–R5, a resolução e o `finally` de `bidSubmission.ts:43` removem a chave global, sem invalidar o objeto guardado no estado. Em R6, o passive effect real (`LotPage.tsx:449`–`:454`) chama `bidToFollow(capturedBid, privateOwner, lotId)`. Para conta/lote iguais, `bidSubmission.ts:59` devolve **esse mesmo objeto**, independentemente do Map. O efeito passa a entry a `later(() => handleOutcome(entry))`; `handleOutcome` aguarda `entry.outcome` em `:371`. A promise já resolvida continua consumível por `await`. Portanto a remoção do registro não interrompe mais o caminho até o resultado original. Não encontrei o caminho original de bloqueio permanente.

### 2. Accepted

**OK.** O aceite chega pelo mesmo `entry.outcome` e pelo mesmo `handleOutcome`, inclusive quando settled antes do efeito. Após a guarda de montagem/conta e o desbloqueio, o 201 aplica valor, fim, carteira, overlay e confirmação; a sala pode nascer do aceite mesmo sem leitura inicial concluída. `cancelRound()` invalida leituras anteriores e a rodada posterior atualiza sala/participação sem novo POST. Falha nessa sincronização preserva a confirmação e acrescenta o aviso. Os testes Playwright de aceite e de remontagem (`lot-room.spec.ts:100`, `:199`, `:297`, `:319`) cobrem consequências relevantes, mas não forçam R4–R5 antes do passive effect. Falta desse caso específico é cobertura incompleta, sem erro demonstrado no caminho produtivo.

### 3. Refusal

**OK.** O teste novo (`bidSubmission.test.ts:74`) usa o registro e a promise reais de `startBid`: captura em `:83`, resolve com `below_minimum`, aguarda o outcome, comprova registry vazio em `:86`, seleciona a entry capturada, verifica identidade e resultado e conta um único envio. Ele discrimina a seleção correta contra uma segunda consulta isolada ao Map; não é apenas retorno de objeto fabricado. Seu limite é não montar `LotPage` nem observar controles. No componente, a recusa passa pelo desbloqueio comum, preserva o valor, aplica feedback/foco e sincroniza. Playwright cobre recusas usuais em `lot-room.spec.ts:141`.

### 4. Ambiguous

**OK.** O outcome ambíguo também chega pela referência preservada e libera `submitting` antes do branch. O componente mostra aviso neutro, relê sala/participação/carteira e informa sincronização completa ou parcial; não chama `startBid` nem repete o POST. A conversão de rejeição inesperada em ambígua permanece em `startBid`. Testes puros de envio único/rejeição e Playwright (`lot-room.spec.ts:212`, `:228`, `:238`) cobrem esses comportamentos; não há caso próprio do interleaving R1–R6 para ambíguo. A análise do caminho comum não indica bug por essa ausência.

### 5. submitting/unblock

**OK.** O ciclo real é `capturedBid !== null → submitting=true → effect → bidToFollow(capturedBid, ...) → later → handleOutcome → await entry.outcome → guarda → setSubmitting(false) + submittingRef.current=false` (`LotPage.tsx:115`–`:118`, `:371`–`:374`, `:449`–`:454`). O desbloqueio antecede todos os branches e suas releituras; não depende do sucesso de GET posterior. O estado é passado ao painel em `:654`; refresh/zero usam o ref. Para a montagem vigente da mesma conta/lote, settle antes do efeito não deixa mais `submitting` sem consumidor. O retorno antecipado por unmount ou conta diferente é descarte intencional, não perda de resultado da montagem válida.

### 6. barrier/account/lot/unmount

**OK no escopo de F-01.** `bidToFollow` exige igualdade de owner **e** lotId para aproveitar a captura; em qualquer divergência consulta a chave atual, e `privateOwner === null` impede acompanhamento privado. O efeito depende de conta/lote; `ownerRef`, atualizado no efeito de sessão, impede aplicar o outcome à conta errada. A seleção por lote impede reutilizar captura de outro lote no acompanhamento da navegação. Não alterei nem reauditei o roteador.

O cleanup existente marca `mountedRef=false` e aborta leituras; o primeiro retorno de `handleOutcome` após o await descarta UI de montagem desmontada/conta diferente. O cleanup não cancela o POST nem libera a barreira. Se outra montagem capturou a entry antes do settle, continua acompanhando a própria referência; se reentrar depois de concluída e removida, começa sem envio pendente e lê o estado atual, conforme o protocolo existente (o registry não é histórico de notificações).

`startBid` mantém a barreira síncrona por conta/lote (`pending.has` antes de enviar); o `finally` remove somente a entry correspondente e somente após o envio terminar. O efeito corrigido apenas observa, sem POST nem release. Duas montagens observarem a mesma promise não duplica a operação: a desmontada descarta UI e cada montagem tem suas próprias leituras/guardas. Não identifiquei duplicação perigosa introduzida pela correção.

### 7. Test coverage

**LOW — FALTA TESTE DISCRIMINANTE DO EFFECT.** Uma regressão que trocasse apenas `bidToFollow(capturedBid, ...)` por `pendingBidOf(...)` **dentro do efeito** não seria morta pelo teste puro: ele continuaria chamando o helper correto. Os Playwright atuais atrasam POST e observam remontagem, mas não controlam deterministicamente o intervalo render → passive effect. Assim, não demonstram matar essa mutação específica.

Classifiquei a lacuna como proteção futura contra regressão, sem manter o MEDIUM produtivo: o encadeamento real é curto, inspecionável e correto; o teste puro prova a parte sensível à remoção do registry e há E2E de resultado/remontagem/desbloqueio. Accepted e ambiguous carecem de casos próprios desse intervalo, mas compartilham o mesmo await e desbloqueio. Um teste discriminante do consumidor seria útil como melhoria opcional. Não recomendo introduzir uma nova stack de testes de componente agora apenas para esse gate, considerando a entrega próxima e o risco residual. Se for possível controlar o intervalo no Playwright existente, isso pode acrescentar proteção sem framework novo; adicionar casos puros de accepted/ambiguous sozinho não fecha a lacuna da chamada no efeito. Não criei infraestrutura nem testes nesta sessão.

### 8. Verify final

**COMPROVADO PELO RELATO POSTERIOR À CORREÇÃO.** O pedido fornece `VERIFY_E2E=1 ./verify.sh`, exit 0, executado após a correção: pytest 2036 passed/1 warning; npm test 160 passed; Playwright 189 passed/5 skipped; Ruff, format (89 arquivos já formatados), ESLint, tsc, Vite build e Docker build aprovados. A decisão atualizada de F-01 acima também registra verify posterior, exit 0. Uso essa evidência autorizada como relato, sem alegar execução ou inspeção de log nesta sessão. A ausência apontada no review anterior é histórica e foi superada; não a reutilizo como finding nem encontrei contradição documental real de cronologia.

### 9. Findings novos

Somente a lacuna **LOW opcional** descrita na seção 7: falta de teste discriminante do uso da captura no passive effect. Nenhum novo bug produtivo ou finding bloqueante identificado neste re-review. Não reclassifiquei achados de outros escopos.

### 10. Recommendation

**F-01 APROVADO COM LOW OPCIONAL**

Fechei tecnicamente o MEDIUM F-01 neste re-review; a melhoria de cobertura não bloqueia os próximos gates. Isso não declara fechamento do Epic 3: ele permanece **`in-progress`**, sem Git, deploy, backend, Epic 4 ou alteração de status. Registro encerrado.

---

Nota administrativa final — registro em 27/10/2026: **Gate de fechamento concluído
posteriormente: verify, merge e deploy/smoke.** O re-review acima aprovou F-01
MEDIUM; LOW opcional de cobertura aceito, não bloqueante. Conforme evidência
fornecida, verify final verde (pytest 2036, npm test 160, Playwright 189 passed/
5 skipped e demais etapas aprovadas); merge/push da `main` e deploy/smoke foram
executados manualmente pelo usuário, commit publicado `3d3ea97`, aplicação
funcionando em <https://casa-de-leiloes-i1xr.onrender.com>. Epic 3 `done`.
Esta nota registra o encerramento posterior; não altera os findings nem os
vereditos históricos. Detalhes operacionais não individualizados estão no
[registro de recuperação](../../docs/DEPLOY-RECUPERACAO-EPICS-2-3.md).
