# Re-review independente focal — R6-OPT-01

## Veredito independente vigente — correção reavaliada em 29/10/2026

**R6-OPT-01 = RESOLVED. Nenhum novo MEDIUM/HIGH/BLOCKER no escopo focal.** O parecer anterior abaixo é histórico e foi superado pela atualização real do candidato.

**APROVAÇÃO TÉCNICA AGREGADA FINAL DOS OPCIONAIS 6.5–6.7 E REFINAMENTOS PÓS-ENTREGA.** Preservo as aprovações das demais áreas; não repeti o review agregado.

- Revi `ContextHelp.tsx` e os testes atualizados: um `activeId` compartilhado, `useSyncExternalStore`, limpeza somente da instância ativa no unmount e Escape local/global. As cinco camadas da skill concluíram a releitura focal sem novo finding. As hipóteses de persistência do defeito anterior foram refutadas pela nova implementação e pelo probe.
- Executei independentemente `node /private/tmp/atrio-r6opt01-rereview-final/probe.mjs`, exit 0, sobre build temporário feito do código atual, sem carregar .env. Chromium real, componentes reais da Carteira e navegação real; respostas da API simuladas, sem mutação de negócio. Em mouse desktop 1440, teclado 320 e toque 320: A→B→C exibiu respectivamente `[true,false,false]`, `[false,true,false]`, `[false,false,true]`; sempre exatamente uma ajuda aberta. Escape fechou todas e preservou foco no trigger; reabrir C, fechar a própria e remount retornando fechado funcionaram. Reabrir A após remount também passou. Sem overflow em todas as etapas de 320px. Captura aberta/inspecionada.
- `aria-expanded` e visibilidade derivam da mesma identificação ativa; IDs/aria-controls e testes de foco, Space/Enter, Escape fora do trigger e instâncias de Sala/Auditoria foram examinados. Não encontrei regressão concreta. Evidências independentes: `/private/tmp/atrio-r6opt01-rereview-final/{probe.mjs,probe.json,probe.log,probe-320.png,gate-check.json}`.
- Gate novo conferido em `/private/tmp/atrio-r6-opt-01-fix/verify-final.log`: **VERIFY_E2E=1 ./verify.sh, exit 0**, conforme scope.json e conclusão normal do script com set -e; **2446 backend passed**, **206 Node passed**, **355 Playwright passed / 7 skipped**, Ruff/formato, ESLint, tipos, Vite e Docker aprovados. Os sete skips real-stack não foram contados como pass. Não reexecutei o gate integral nem os real-stack nesta releitura.
- A última correção executável ocorreu às **13:09:23 -03:00**, antes do início do gate às **13:09:58**, encerrado às **13:13:22**. Comparei SHA-256 atuais de **284 arquivos de código/configuração** com after.json: zero divergências, nenhum executável posterior ao início do gate. Before/after limitam a correção executável a `frontend/src/ContextHelp.tsx` e `frontend/e2e/post-delivery.spec.ts`. SHA-256: componente `ee160aa9022b1ab78e0a2a022da6c7f109d6d6d290124d946f61cb876bb86fb2`; E2E `c6530ec1c241c379d8c6a9e917868a0a6774b095bcb0dbcc7836233919ccfd1d`.
- **Liberado tecnicamente para organizar commits locais e posterior push/deploy manual.** Recomendo **6.5→done; 6.6→done; 6.7→done; footer/refinamentos aprovados**. Épico 6 permanece **in-progress apenas até deploy e smoke público final**. Estados não foram editados nesta sessão. Produção desta rodada ainda não validada.
- Pendências exclusivamente de produção: publicação manual do candidato aprovado e smoke público final. Nenhum código foi corrigido pelo revisor; nenhuma operação Git, commit/push/merge/deploy ou leitura de .env* foi executada.

## Atualização local da correção — 29/10/2026, 13:13 (-03:00)

**R6-OPT-01 corrigido localmente — aguardando re-review independente**

Este bloco registra implementação e verificação locais; o relatório independente anterior, preservado abaixo, examinou a versão sem a correção. Não concede aprovação de re-review nem altera os estados das Stories.

- Causa: `useState` independente em cada `ContextHelp`, somado ao E2E que exigia duas ajudas abertas.
- Solução: coordenador compartilhado no próprio módulo, com um único `activeId`, assinatura React via `useSyncExternalStore` e `useId` estável para coordenação/ARIA. Abrir outra substitui a ativa; repetir fecha; unmount limpa somente o próprio ID ativo. Escape no trigger preserva foco/isolamento; fora dele fecha a ajuda sem mover o foco e respeita eventos já consumidos. Sem dependências novas, alteração de textos/CSS ou manipulação do DOM para coordenação.
- Arquivos desta correção: `frontend/src/ContextHelp.tsx`, `frontend/e2e/post-delivery.spec.ts` e este registro.
- Provas em instâncias reais: Carteira A → B → C, `aria-expanded`, conteúdo anterior oculto, um único conteúdo visível, fechar a própria, Enter/Space, Escape dentro/fora do trigger, foco visível, IDs únicos, unmount/remount por History API, toque e ausência de POST. Temas light/dark a 320px sem overflow. Sala: mínimo → pseudônimo em áreas distintas; Auditoria: integridade → pseudônimo; Back à Sala sem popup fantasma. Sala/Auditoria também verificadas em dark a 320px.
- Focais finais: **204 passed, zero falhas/skips (24.3s)** — post-delivery, wallet, lot-room, lot-room-ws, audit, keyboard, layout e touch-targets. Lint/typecheck também aprovados.
- Gate posterior à última mudança executável: **`VERIFY_E2E=1 ./verify.sh`, exit 0**. **2446 backend passed (146.51s), 206 Node passed / 0 failed / 0 skipped, 355 Playwright passed / 7 skipped (39.9s)**. Um warning backend preexistente Starlette/httpx. Ruff check/format (111 arquivos), ESLint, typecheck, Vite e Docker build aprovados; mensagem final “verify.sh: todas as etapas passaram.”
- Execução com guardas temporárias externas ao repositório: Compose com `--env-file /dev/null`, uv com `--no-env-file`, fonte dotenv Python desativada e leituras Node de `.env*` bloqueadas. Nenhuma leitura de `.env*`. A primeira tentativa focal no sandbox não pôde abrir 127.0.0.1:4173 (EPERM); a execução autorizada fora do sandbox e a rodada focal final passaram.
- Identidade: comparação SHA-256 de **523 arquivos** do baseline desta sessão e diff sem Git confirmam somente os três arquivos acima alterados; **126 arquivos backend idênticos**, sem novas fontes fora do escopo. Story 6.6, fontes financeiras, testes real-stack e sprint-status preservados. Manifestos/diff/logs: `/private/tmp/atrio-r6-opt-01-fix/{before.json,after.json,scope.json,correction.diff,focal-final.log,verify-final.log}`.
- SHA-256 `ContextHelp.tsx`: `ee160aa9022b1ab78e0a2a022da6c7f109d6d6d290124d946f61cb876bb86fb2`. E2E: `c6530ec1c241c379d8c6a9e917868a0a6774b095bcb0dbcc7836233919ccfd1d`.
- Os **7 real-stack passed (4.7s)** de `/private/tmp/atrio-optionals-evidence/real-stack.log` permanecem evidência anterior; não foram repetidos nem contados como aprovação nova. A mudança não afeta seus cenários e nenhuma fonte backend/financeira mudou.
- Estados preservados: **6.1–6.4 done; 6.5/6.6/6.7 review; Épico 6 in-progress**. Sem commit, push, merge, rebase ou deploy. Parada para re-review focal independente; nenhuma aprovação independente nova é alegada.

## Relatório independente anterior — versão sem correção

29/10/2026 — America/Maceio. Skill bmad-code-review; cinco camadas concluídas. Escopo exclusivo: exclusividade das ajudas contextuais e seus controles/testes. As demais aprovações do review agregado ficam preservadas. Nenhuma correção de código, alteração de status, Git, commit/push/merge/deploy ou leitura de .env*.

**R6-OPT-01 = NOT RESOLVED. Severidade MEDIUM mantida.**

## 1. Estado encontrado

A versão disponível neste workspace ainda é a implementação anterior. `frontend/src/ContextHelp.tsx:5` mantém `open` independente por instância; o handler em `:15` alterna somente a própria instância. Não há provider/coordenador nos imports do componente. A busca por coordenador/provider/ajuda ativa/exclusividade não localizou implementação relacionada.

`frontend/e2e/post-delivery.spec.ts:138,142` ainda exige que Saldo total permaneça visível/expandido depois de abrir Saldo comprometido. O teste de toque alterna somente uma instância. Esses pontos são a evidência/cobertura do mesmo finding, sem criar novo ID ou reabrir outras áreas.

## 2. Probe independente executado

Executei `node /private/tmp/atrio-r6opt01-rereview-bld997aw/probe.mjs`, exit 0 do coletor. Isso significa coleta concluída, **não aprovação dos critérios**: `exclusiveAfterC=false` nos três cenários.

O runner constrói a aplicação real a partir do código atual, com Vite/React, em diretório temporário, `configFile:false` e `envDir` vazio dedicado, impedindo leitura implícita de .env. Serve os assets localmente e usa Chromium real. Somente respostas de negócio são simuladas: sessão BIDDER, carteira, listagem vazia e health. Nenhum banco ou mutação financeira foi necessário.

| Etapa | aria-expanded de A / B / C | Ajudas visíveis |
| --- | --- | --- |
| Inicial | false / false / false | 0 |
| Abrir A: Saldo total | true / false / false | 1 |
| Abrir B: Saldo comprometido | true / true / false | 2 — FALHA |
| Abrir C: Saldo disponível | true / true / true | 3 — FALHA |
| Escape em C | true / true / false | 2 |
| Reabrir C | true / true / true | 3 |
| Fechar C pela própria ação | true / true / false | 2 |
| Desmontar Carteira navegando à Vitrine e retornar | false / false / false | 0 |
| Reabrir A após remount | true / false / false | 1 |

A mesma sequência foi observada com **mouse em 1440px**, **teclado em 320px** e **toque em 320px**. Teclado usa foco/Enter; toque usa tap real em contexto hasTouch. Escape devolveu foco ao acionador C nos três cenários. Navegação usa links reais da aplicação e remonta os componentes.

Evidências: `/private/tmp/atrio-r6opt01-rereview-bld997aw/probe.mjs`, `probe.log`, `probe.json`, `probe-320.png`. Captura aberta e inspecionada. Não executei novamente a suíte versionada nem o gate integral; li as expectativas relacionadas e executei o probe independente acima.

## 3. Acessibilidade e mobile

Os botões nativos continuam acessíveis por mouse, Enter e toque; `aria-expanded` acompanha a abertura individual e `aria-controls` aponta para o conteúdo. Escape fecha a instância focada e devolve foco. Fechar a própria e reabrir funcionam. Unmount/remount remove o estado local anterior e retorna fechado, sem estado órfão observado.

Essas propriedades não suprem a exclusividade: A e B permanecem expandidas ao abrir C e após Escape em C. Em 320px, todas as etapas tiveram `document.documentElement.scrollWidth <= innerWidth`, e a captura não mostrou recorte global. Nenhuma nova regressão de overflow confirmada no recorte.

## 4. Evidência do gate e identidade

Não foi localizado/fornecido um novo gate posterior a uma correção de R6-OPT-01. A evidência disponível continua `/private/tmp/atrio-optionals-evidence/verify-final.log`, encerrada em **29/10/2026 12:47:10 -03:00**: 2446 backend, 206 Node, 355 Playwright passed / 7 skipped, demais etapas aprovadas. Esse é o gate anterior ao finding e contém a expectativa de múltiplas ajudas abertas. Não o apresento como novo gate pós-correção.

SHA-256 atual do componente: `f2f3b932bb2825be2254ee0a552025b5faddd4cde595ac7bd644c9367a169e45`.
SHA-256 atual do E2E: `c51f912d8b60bf54a4320c95f65253ffb7f8d489b75440ee8f47083e39661279`.

Ambos coincidem exatamente com o manifesto do candidato original. Mtimes: componente **12:34:07**, E2E **12:41:22**, anteriores ao gate antigo. A conferência dos 50 arquivos de código/testes do manifesto original encontrou zero divergências. A identidade confirma que a correção descrita no pedido não está presente no candidato acessível; não é apenas ausência de log novo. Não há prova de gate posterior à correção que autorize liberação.

## 5. Camadas e triagem

Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Acceptance Auditor e Project Auditor concluíram a revisão focal. Todos apontaram a ausência de exclusividade e/ou as expectativas contraditórias. Cada observação foi confirmada pelo código/teste e pelo probe; severidade MEDIUM. Agrupadas em **R6-OPT-01**, mesma causa e mesmo aceite. Nenhum finding novo separado, nenhum LOW reaberto, nenhuma reavaliação financeira/dos demais opcionais. Nenhuma camada falhou nesta rodada.

## 6. Veredito e próximos estados

**Não concedo APROVAÇÃO TÉCNICA AGREGADA FINAL DOS OPCIONAIS 6.5–6.7 E REFINAMENTOS PÓS-ENTREGA. Candidato não liberado para commits/push/deploy como aprovado.**

As demais áreas aprovadas permanecem aprovadas. Recomendo manter 6.5/6.6/6.7 em review e Épico 6 in-progress, sem editar esses estados nesta sessão. Falta disponibilizar a correção de exclusividade neste candidato, alinhar os testes ao aceite e comprovar gate posterior com identidade/hashes, seguido de re-review focal. Após aprovação local, continuarão pendentes deploy manual e smoke público final. As pendências atuais, portanto, ainda não são exclusivamente de produção.

A ponte integrada do Browser foi tentada e estava indisponível; usei Chromium Playwright local como fallback. Nenhuma aprovação de produção foi inferida. Parei após o relatório.
