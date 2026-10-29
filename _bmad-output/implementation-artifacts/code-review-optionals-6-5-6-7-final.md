# Review agregado independente final — opcionais 6.5–6.7

Data: 29/10/2026, America/Maceio. Skill: bmad-code-review. Sessão independente da implementação. Revisão do estado atual, sem correção de código ou alteração de status.

**Veredito: candidato NÃO liberado para commit/push/deploy.** Um finding MEDIUM confirmado; zero BLOCKER/HIGH. Stories 6.5/6.6/6.7 permanecem review e Épico 6 in-progress. Produção desta rodada não validada.

## Finding confirmado

**R6-OPT-01 — MEDIUM — Ajuda contextual permite todas as explicações abertas simultaneamente.**

- Refinamento: tooltips/ajuda contextual.
- Arquivo/linha: frontend/src/ContextHelp.tsx:5 e :15; frontend/e2e/post-delivery.spec.ts:136–142.
- Evidência/reprodução: na Carteira, abrir Ajuda: Saldo total, depois Saldo comprometido e Saldo disponível. Cada instância mantém open independente; as três explicações continuam abertas. O E2E executado exige explicitamente que a primeira permaneça aberta ao acionar a segunda.
- Contrato violado: pedido do review exige “não abrir todos simultaneamente”.
- Impacto: comportamento de interação e teste contradizem aceite explícito do refinamento; trocar de ajuda acumula explicações em vez de substituir a ativa.
- Correção mínima: coordenar uma ajuda ativa por contexto/tela e fechar a anterior ao abrir outra; ajustar o E2E para exclusividade, preservando mouse, teclado, toque, Escape, foco e ARIA. Nenhuma correção aplicada.

## Avaliação por contrato

| Item | Resultado e limites |
| --- | --- |
| 6.5 | Filtro puro do snapshot carregado por título/artista/data, trim do termo, caixa/acentos ignorados; grupos, ordem e as_of preservados. Combinação, limpar, vazio, Back/foco e ausência de novas consultas cobertos. Cancelados excluídos pelo backend. |
| 6.6 | Dono AUCTIONEER; scheduled/live permitidos, ended/settled recusados, integridade antes dos atalhos de negócio conforme contrato; histórico preservado. |
| Locks/atomicidade/refund | lock_lot → clock_timestamp → dono → histórico autenticado → terminal/idempotência/fim → lock_wallet. Subtrai authenticated.current.amount_cents da carteira do líder autenticado, com limites e committed suficiente. Total não muda; outras reservas ficam. cancelled_at e carteira na mesma Session/transação; flush não confirma; rota faz commit único e só depois sinaliza transitioned. Falhas em UPDATE de carteira/lote e precommit deixam snapshot intacto. |
| cancel×bid | Sessões/conexões independentes e threads; espera observada por pg_blocking_pids. Cancel primeiro recusa lance; novo líder primeiro faz cancel reler e liberar a reserva nova. Saldos finais e reserva de outro lote verificados. |
| cancel×settlement | Sobreposição real observada, inclusive cancel antes do prazo e closer esperando até ficar devido. Cancel válido impede liquidação; settlement vencedor não é desfeito. |
| Auditoria pós-cancel | Cadeia, sequência, bid_count, current, hashes e anchor_hmac preservados; auditoria aceita cadeia íntegra e detecta adulteração/cancelado com settlement. |
| 6.7 | Tokens claros em :root e overrides dark; script antes do mount prioriza preferência válida e depois sistema. Escritas em atrio-theme são light/dark. Persistência, History API, login/logout, storage indisponível, nome acessível/foco e reduced-motion examinados/testados. |
| Senha forte | Backend RegisterRequest e frontend: 8–1024 code points, 3/4 grupos Ll/Lu/Nd/P/S. Sem trim/normalização da senha. Login mantém sua regra anterior; Argon2id e demos preservados. Discrepância Unicode rara tratada na triagem abaixo. |
| Confirmação | Somente frontend, igualdade literal/case-sensitive/espaços, toggle preserva campos, divergência impede POST e barreira síncrona bloqueia duplo envio. Payload exato email/password/role. Não foi identificada senha real em logs inspecionados; fixtures têm senhas fictícias de teste. |
| Tooltips/ajuda | Botões focáveis, aria-expanded/controls, teclado/mouse/toque/Escape e 320px cobertos. Divulgação em fluxo evita recorte. Texto de reserva não afirma gasto e integridade não promete blockchain/inviolabilidade. Exclusividade falha: R6-OPT-01. |
| Feedback ao líder | Guardas de winning/live/wallet ready/não stale/sem overlay/mínimo conhecido e incertezas; texto usa “no momento”. Transições WS e outbid cobertos. Precedência backend preserva período → mínimo → already_winning → saldo. |
| Footer | Autoria e copyright exatos; disclaimer de simulação; links do projeto e AIC com noopener noreferrer; sem contatos inventados; health vem da leitura real existente. |
| Regressões 6.1–6.4 | Inventário independente da aplicação: exatamente sete POSTs, nenhuma nova escrita. Cadastro/login/demos, Sala/WS, carteira, settlement/anti-sniping, auditoria, comprovante e settlement_status cobertos no gate registrado. Não repetido review integral anterior. R6-AGG-01/02 e R6.4-01 não reabertos por evidência nova. |

## Testes independentes realmente executados

- PostgreSQL real descartável na porta 55436: **589 passed**, zero skips, **54.77 s**, um warning preexistente Starlette/httpx. Arquivos: test_lot_cancellation.py, test_lot_cancellation_concurrency.py, test_lot_settlement_concurrency.py, test_lot_room_ws.py, test_lot_audit.py, test_registration.py, test_auth_flow.py, test_seed.py, test_csrf.py e test_access_policy.py.
- Node: **62 passed**, zero falhas/skips. vitrine, route, lotCancellation, api/audit, api/lots, passwordStrength e api/auth.
- Chromium/Playwright: **128 passed**, zero skips, **17.5 s**. vitrine.spec.ts, registration.spec.ts, post-delivery.spec.ts, my-lots.spec.ts e audit.spec.ts. O finding de ajuda passa porque a expectativa atual fixa o comportamento divergente.
- Inventário independente: introspecção direta de app.routes, filtrando POST/PUT/PATCH/DELETE: sete escritas, todas POST — register, login, logout, criar lote, bid, cancel, deposit. Uma tentativa inicial importou o helper de inventário do módulo errado e falhou; o inventário final usa diretamente as rotas reais.
- As primeiras tentativas PG falharam porque o container descartável estava parado. Reiniciei somente atrio-optionals-test-20261029; não utilizei o banco habitual. Fonte dotenv desativada pelo wrapper temporário inspecionado; sem leitura de .env*.
- Evidências da sessão: /private/tmp/atrio-final-independent-review/{backend.log,node.log,playwright.log,http-writes.json,executable-hashes.json}.

## Validade do gate e real-stack anteriores

Conferi o log integral existente em /private/tmp/atrio-optionals-evidence/verify-final.log: **2446 backend**, **206 Node**, **355 Playwright passed / 7 skipped**, Ruff/formato, ESLint, typecheck, Vite e Docker aprovados; mensagem final “todas as etapas passaram”. Skips não foram contados como pass.

Os 50 arquivos de código/testes do manifesto coincidem com SHA-256 atuais. A última modificação executável listada foi **12:42:30**, anterior à criação do log do gate às **12:43:41**, encerrado às **12:47:10**. Examinei 334 arquivos de código/configuração, sem arquivo alterado após o baseline fora do manifesto fornecido. O manifesto foi criado/atualizado durante/depois do gate e consolidado às 12:50; a atribuição depende de log, hashes atuais e metadados locais, não de uma assinatura externa anterior à execução. Não identifiquei evidência de alteração executável pós-gate que exigisse nova execução integral. Não reexecutei verify.sh.

O log real-stack separado registra **7 passed**, **4.7 s**, zero skips, com E2E_REAL_BASE_URL local. Li os sete cenários e distingui as duas contas criadas em API real dos mocks. O smoke complementar registra REAL_CANCEL_PASS e possui runner com asserts de UI/HTTP/WS, refund exato, total intacto, auditoria/bids/hash, idempotência, Vitrine ausente e participação cancelada. Esses sete e o smoke são **evidência histórica inspecionada, não reexecução independente nesta sessão**.

## Inspeção visual e documentação

Abri oito capturas existentes: Vitrine light/dark desktop, Vitrine dark 320, Sala dark 320, Cadastro dark 320, footer light 320/dark desktop e ajuda dark 320. Não observei overflow global, texto ilegível, tooltip cortado ou prejuízo funcional evidente nessa amostra. Tokens/contraste e medidas 320/375/1440 também são cobertos pelos E2E executados. Não inspecionei visualmente cada estado de Login/Auditoria/Comprovante nesta sessão; não alego cobertura visual integral dessas telas.

Documentação vigente registra corte inicial dos opcionais, reativação por decisão humana, refinamentos externos sem atribuí-los à Verzel e publicação anterior separada do candidato novo. Sprint: opcionais review, épico in-progress. Registros antigos de backlog/done permanecem como histórico, com estado vigente apresentado no topo/final.

## Camadas e triagem

- Blind Hunter: dez hipóteses examinadas, nove refutadas pelo próprio revisor. Candidato sobre timestamp impossível de cancelled_at: **defer/excluído por preexistência**, pois o baseline já aceitava cancelado vazio sem validar esse timestamp; o reproducer apresentado usava histórico vazio. Não é finding novo dos opcionais.
- Edge Case Hunter: nenhum defeito financeiro novo confirmado. Candidato de vínculo privado bidder_id/alias na auditoria: excluído por preexistência e contrato AD-20. Candidato Unicode 16 em frontend versus Unicode 15.1 em Python: diferença real de classificação para U+1C89; **LOW rejeitado pela regra da skill**, dada raridade do caractere e correção além de ajuste direto. Backend recusa com validação, sem enfraquecer segurança.
- Verification Gap Reviewer: nenhum gap confirmado.
- Acceptance Auditor: R6-OPT-01 confirmado e retido como MEDIUM.
- Project Auditor: **falhou por limite de uso antes de produzir conclusão**. Não alego conclusão das cinco camadas nem clean review. Coordenação fez conferências próprias de arquitetura, UI, histórico e evidência, sem apresentá-las como substituto independente dessa camada.

Apêndice de rejeitados/refutados: alias histórico não recalculado é intencional; resposta de auditoria antiga é abortada/componente keyed; receipt inconsistente é recusado; role público é literal fechado; User/Wallet compartilham transação; dono precede gate conforme contrato; guarda síncrona bloqueia cancelamento duplicado; filtros são restaurados pelo history.state; storage indisponível tem fallback. Todos mantidos como refutados, sem finding inventado.

## Limitações e status recomendado

Revisão sem correções, commit/push/merge/rebase/deploy ou modificação de story/sprint. Uma consulta git status foi executada antes de carregar a proibição local; foi reconhecida e não repetida. Ponte do Browser integrado indisponível; testes usaram Chromium Playwright local conforme fallback. Produção nova, outros motores e nova aprovação visual humana não foram validados. Limitação commit/publicação WS sem outbox permanece preexistente.

**6.5 → review; 6.6 → review; 6.7 → review; footer sem finding próprio; ajuda pendente R6-OPT-01; Épico 6 → in-progress. Candidato não liberado para commit/push/deploy.** Recomendo corrigir R6-OPT-01 em etapa autorizada separada e revalidar seu aceite. Parei após registrar este relatório.
