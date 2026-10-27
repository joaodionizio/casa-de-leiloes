# Code review Epic 2 — retrospectivo de integração

Status: **APROVADO — REVIEW EXECUTADO; LOW F-01 RESOLVIDO**.

## 1. Natureza retrospectiva

Executado em **26/10/2026, America/Maceio**, por nova sessão independente **GPT-6.1 Sol Medium** (`gpt-6.1-sol`, esforço medium, contexto novo; configuração confirmada pelo orquestrador). Esta sessão não especificou nem implementou as entregas revisadas.

Alvo: estado integrado atual das funcionalidades originadas nas Stories **2.1–2.5**, já evoluídas pelas Stories 3.1–3.6. Review feito agora para detectar problemas herdados ainda presentes antes da recuperação 2+3. **Não foi revisado o diff agregado original antes do merge.** Nenhuma comparação histórica foi fornecida; nenhum Git foi executado para reconstruí-la. Branch/commit/remoto e futura correspondência com merge/deploy não foram certificados.

Método: diretrizes de bmad-review e evidências agregadas de bmad-retrospective subordinadas ao escopo/formato do pedido. Lentes adversarial, caminhos de borda e proteção existente pela mesma sessão, sem subdelegação, quota artificial de findings ou repetição de cinco reviews por story. Não executei passos genéricos de Git/correção/status/retrospective adicional.

Fontes obrigatórias: `CLAUDE.md`, `README.md`, `docs/{FECHAMENTO-DE-EPICO,AUDITORIA-PROCESSO-EPIC-3,ARQUITETURA,FRONTEND-WORKFLOW,uso_de_ia}.md`, `_bmad-output/planning-artifacts/epics.md`, `implementation-artifacts/{sprint-status.yaml,deferred-work.md}`. Paths abreviados de artefatos pertencem a `_bmad-output/`. Stories finais 2.1–2.5: critérios, decisões, integrações, registros de review/correções/re-review e limitações; stories 1.2–1.4 como fundação. Specs pertinentes de auth/policy, catálogo, criação/seed, vitrine/navegação e contratos posteriores `spec-story-3-4-lance-transacional/seed-and-lot-creation.md` e `spec-story-3-6-leiloeiro-cancela-lote-sem-lances/database-and-reads.md`. Re-review final do Epic 3 usado como contexto, sem reabrir MEDIUM já corrigido/aprovado.

Inventário vivo: `backend/app/{auth,security,users,access,csrf,errors,artic,catalog,lots,lot_time,money,seed,lot_cancellation,main,config,db}.py`, migrations 0001–0006; frontend App/login/route/navigation, criação/form/review/MyLots, clientes HTTP auth/catalog/lots/publicLots, dinheiro/horários e ligação do detalhe à sala atual; testes pertinentes. Evidências por assunto abaixo. Não reauditei profundamente regras exclusivas do Epic 3.

## 2. Findings Epic 2

**0 HIGH, 0 MEDIUM, 1 LOW novo (F-01, hoje RESOLVIDO).** Nenhum bug funcional herdado confirmado como bloqueante da recuperação.

### F-01 — Resumos do README ainda refletem etapas anteriores do catálogo e do demo

**Severidade:** LOW.

**Status: RESOLVIDO (26/10/2026).** Correção exclusivamente documental no `README.md`: o snapshot da obra passou a ser descrito no presente (a AIC só serve à busca/seleção; `POST /api/lots` grava o snapshot e as leituras não consultam a AIC) e a definição de demo aberto agora inclui `cancelled_at` nulo, sem reativar demo cancelado, alinhada a `seed.py`. Nenhum código, migration ou teste alterado; verify não reexecutado por ser mudança só textual.

**Epic:** 2, integração com evolução do Epic 3.

**Stories afetadas:** 2.3, 2.4; integração 3.4/3.6.

**Arquivos:** `README.md:357`–`:358`, `:382`–`:383`, `:467`–`:470`; contrapontos em `README.md:314`–`:316`, `backend/app/lots.py:306`–`:315`, `:344`–`:387`, `backend/app/seed.py:132`–`:151` e spec 3.6 `database-and-reads.md`, seção 4.

**Problema:** A seção atual de catálogo diz que a 2.4 “vai copiar” os campos e fala em “Lotes futuros”, embora snapshot/persistência já estejam entregues. Mais concretamente, “Lote demo” define aberto por is_demo, fim futuro e âncora não nula, omite **cancelled_at IS NULL** e diz que outro só nasce quando os anteriores encerraram. O código exclui cancelados do EXISTS. A seção de deploy do mesmo README já descreve corretamente esse predicado, criando explicações diferentes no guia.

**Cenário concreto:** Avaliador cancela o único demo assinado ainda com fim futuro e reinicia o serviço. Pela definição específica de demo aberto, esperaria que esse registro impedisse outro; o seed cria corretamente o substituto. Catálogo isoladamente também apresenta o snapshot já entregue como etapa futura.

**Impacto:** Expectativa documental imprecisa, sem falha de auth/dados/runtime. Não bloqueia próximos gates.

**Correção recomendada:** Em tarefa documental posterior autorizada, usar presente para snapshot/lotes já persistidos e sincronizar a definição completa do demo, incluindo cancelamento, preservando histórico. Não alterar código/seed para adequá-lo ao texto antigo.

**Teste necessário:** Conferência documental com código/spec e caso de demo cancelado; sem teste de runtime novo ou verify automático para simples correção textual.

**Decisão humana / estado:** **ABERTO — não corrigido; aceite/adiamento humano pendente.** README não foi editado nesta sessão.

## 3. Auth/roles

**OK — por inspeção.** `auth.py:43`–`:120` implementa login/logout/me, Argon2 e token somente em cookie. `security.py:51`–`:76` fixa HS256, claims obrigatórias e oito horas. `access.py:41`–`:96` confere assinatura/expiração e usuário/papel no banco; removido ou papel divergente invalida a sessão. AUCTIONEER cria/gerencia; BIDDER acessa carteira/lance. `access.py:130`–`:151` aplica a dependência declarada, e `test_access_policy.py:80`–`:116`, `:225` em diante verifica dependência além da metadata, inclusive endpoints reaproveitados.

Cookie HTTPS: __Host-auction_session, Secure/HttpOnly/SameSite=Lax/Path=/ sem Domain (`config.py:233`–`:250`, `auth.py:74`–`:84`). HTTP remoto impede boot; modo depende de APP_ORIGIN e não do esquema interno Render. Logout apaga cookie correspondente; token copiado válido até exp é limitação explícita AD-29, sem revogação prometida.

Origin/Referer exatos e JSON exigidos antes dos handlers, inclusive login/logout/cancelamento sem corpo (`csrf.py:61`–`:90`, `:118`–`:161`). Sem CORS permissivo. `frontend/src/api/auth.ts:57`–`:127` usa URL relativa/same-origin, sem guardar token no storage. Não encontrei escalation, confusão de papel ou incompatibilidade material com HTTPS Render documentado.

`App.tsx:175`–`:229`, `:240`–`:300` centraliza sessão/logout/expiração e evita montar áreas do outro papel; `route.ts:76`–`:83` restringe returnTo a rotas internas conhecidas permitidas. Sem open redirect/dead-end confirmado. Policies atuais de carteira/lance/mine e cancelamento continuam corretas; não reauditei internamente esses domínios posteriores.

## 4. External/public-domain integration

**OK — por inspeção.** `artic.py:97`–`:116` constrói consulta fixa com domínio público/imagem; `catalog.py:86`–`:133` reconfere is_public_domain is True no backend. POST só recebe ID/termos, recusa extras e reconsulta a obra (`lots.py:120`–`:156`, `:306`–`:315`, `:667`–`:729`). Não há caminho HTTP que aceite snapshot/owner arbitrário ou obra inelegível.

Destino externo fixo, redirects desabilitados, timeouts, normalização e erros categóricos isolam falhas da AIC; POST falho não grava. Proxy de imagem valida ID/tipo/assinatura/tamanho; falha permite placeholder, mantendo metadados. Cache/843 px/volume já são limites aceitos, não findings novos.

**Requisito central preservado:** snapshot de 11 campos copiado ao PostgreSQL; leituras usam o registro persistido (`lots.py:429`–`:464`, `:467`–`:636`), sem consulta externa de negócio posterior. `test_public_lots.py:969`–`:991` compara respostas com AIC saudável/falhando e exige zero chamadas; `test_my_lots.py:230`–`:244` protege MyLots. Só mídia depende do museu. F-01 é textual, não falha desse comportamento.

## 5. Lot creation

**OK — por inspeção.** Owner vem da sessão e entrada é fechada. Cents estrito/teto compartilhado em `backend/app/money.py`, BIGINT/CHECKs em 0003/0005; `frontend/src/money.ts:31`–`:62` converte por dígitos antes de Number sobre centavos seguros. Sem caminho monetário em float/reais decimais; carteira/lance atuais usam mesma unidade.

Datas ISO com timezone e conversão UTC possível (`lots.py:78`–`:116`); agendamento com um instante PostgreSQL e fim após início (`:269`–`:285`, `:321`–`:323`, `:709`–`:727`). Front faz validação preventiva e envia UTC; backend continua autoridade. Não confundi relógio de UX com autoridade transacional pós-lock do bid.

Novo lote nasce com ID do servidor, lance/líder vazios, bid_count=0, genesis e HMAC do próprio ID na mesma transação (`lots.py:344`–`:387`). cancelled_at nasce NULL pela coluna nullable sem default (0006). `test_lot_creation.py:644`–`:713` protege assinatura/atomicidade e `test_lots_cancellation_migration.py:70`–`:73` o estado não cancelado. O INSERT herdado contempla as evoluções 3.4/3.6.

## 6. Showcase/detail

**OK — por inspeção.** `lots.py:467`–`:636` mantém DTOs explícitos, fases/ordenação e campos de negócio, sem owner/usuário/flag demo/âncora públicos. Ausente/cancelado → 404; UUID inválido → 422. Dados estáticos continuam no detalhe original; disputa/fim atualizado vêm da sala (`LotPage.tsx:86`–`:90`), sem obrigar adição de todo campo da 3.5 ao DTO original.

as_of vem de clock_timestamp em CTE MATERIALIZED único, no mesmo statement dos lotes (`lots.py:512`–`:583`). Filtro de cancelados no JOIN preserva linha do relógio quando vazio/só cancelados. `test_public_lots.py:427`–`:475` e `test_lot_cancellation.py:599`–`:642` observam contrato/exclusão/ausência de escrita. Vitrine apresenta fase server-side; atualização entre clientes continua futura/deliberada.

## 7. Ownership/MyLots

**OK — por inspeção.** `lots.py:537`–`:561`, `:734`–`:760` usam owner da sessão e incluem próprios cancelados; `lot_cancellation.py:57`–`:89` verifica dono antes do gate/decisão. `test_my_lots.py:127`–`:155` e `test_lot_cancellation.py:231`–`:268` protegem outro leiloeiro/owner na query.

Mudança intencional propagada: envelope {as_of,items} e item com bid_count/phase/cancelled_at (`lots.py:414`–`:426`); schemas atuais em test_openapi; cliente `api/lots.ts:26`–`:41`, `:147`–`:165`, `:236`–`:248` valida envelope e rejeita formato antigo. `MyLots.tsx:90`–`:106`, `:254`–`:260` consome items e dá precedência ao selo cancelado. Nenhum consumidor atual esperando array direto ou contrato antigo foi identificado.

`test_lot_cancellation.py:645`–`:697` observa os 21 campos, contagem/fase/cancelamento e relógio vazio/só cancelado. Testes do cliente e e2e/my-lots contemplam o fluxo atual. Não tratei mudança planejada/atualizada como regressão.

## 8. Seed

**OK — por inspeção; ressalva textual F-01.** `seed.py:56`–`:117` preserva IDs, um AUCTIONEER/dois BIDDER e hashes existentes. run_seed completa carteiras faltantes sem zerar saldo; fixture local (`:120`–`:123`) não consulta AIC. Trava consultiva transacional precede clock/seleção (`:126`–`:185`).

Demo elegível exige is_demo/fim futuro/âncora não nula/**não cancelado** (`:141`–`:151`); sem elegível cria outro pelo create_lot atual, assinado. Não reativa/apaga/reassina registro existente. AUDIT_HMAC_SECRET posterior está documentado no startup/produção; nenhuma API externa obrigatória no boot. Legado/rotação seguem limites deliberados, sem finding duplicado.

## 9. Integration with current state

**OK — no escopo funcional herdado.**

| Percurso | Evidência/conclusão |
| --- | --- |
| Container → migrations → seed → app → SPA | start.sh:5–13, Dockerfile, models/migrations/seed e main; fail-fast e variáveis atuais coerentes. Fundação detalhada no relatório Epic 1. |
| BIDDER: app → login → vitrine → detalhe → carteira/sala | App/route/api/auth/LotPage e policies preservam público/privado e retorno seguro. Sem WS inventado. |
| AUCTIONEER: login → catálogo → criação → MyLots → cancelamento | LotCreation:21–96, LotForm/LotReview, clientes e MyLots mantêm percurso/ownership; lote novo compatível com integridade/cancelamento. |
| API externa × persistência | Escolha/publicação e mídia usam AIC; leituras de lotes existentes usam snapshot. |
| Auth × API × OpenAPI | 401 sem sessão, 403 por papel/owner, 404 ausente/oculto, 422 entrada/domínio e schema atuais coerentes. Precedências deliberadas de middleware/decode/policy respeitadas. |
| Migrations × código | 0001–0006 linear/aditiva, models/leitores atuais contemplam contagem/âncora/cancelamento e testes antigos usam head atual. |
| Produção | DATABASE_URL/APP_ORIGIN/JWT_SECRET/AUDIT_HMAC_SECRET/PSEUDONYM_SECRET/PORT/SPA_DIST_DIR reconciliados; sem variável obrigatória esquecida. Painel/valores não consultados. |

Requisitos de Epics 1/2 permanecem: React/Python/PostgreSQL, deploy baseline histórico, dois papéis, login/logout, busca externa, domínio público, criação e vitrine. Não cobrei entregas futuras 4–6. O MEDIUM do Epic 3 foi corrigido/aprovado no re-review posterior; não foi reaberto aqui.

## 10. Tests

**SUFICIENTE — por leitura da proteção existente para este gate.** Auth/policies/CSRF/roles reais, criação/atomicidade/snapshot/âncora, leituras públicas/as_of/zero AIC, MyLots/owner/cancelamento e migrations/seed estão protegidos. Evidências lidas incluem `test_csrf_auth.py:54`–`:156`, `integration/test_roles.py:111`–`:183`, `test_lot_creation.py:593`–`:713`, `test_public_lots.py:427`–`:475`, `:969`–`:991`, `test_lot_cancellation.py:599`–`:697`; cliente MyLots/rotas/dinheiro e `frontend/e2e/session.spec.ts` observam contratos/retorno/login/logout/roles.

Não exigi testes redundantes nem reabri dívida aceita de componentes, Chromium/API simulada e real-stack opt-in. LOW opcional do effect da sala continua registrado no Epic 3, fora das contagens aqui.

Execução desta sessão: inventário/leitura/busca por pwd, rg, cat, sed, nl e Python; escrita somente dos relatórios. **Nenhum teste, mutation testing, verify, Docker build, banco, servidor ou smoke executado.** Não surgiu dúvida funcional concreta que exigisse teste focado. O pedido fornece **VERIFY_E2E=1 ./verify.sh → exit 0 posterior à última correção do Epic 3**, também registrado no re-review final respectivo. Evidência usada como relato autorizado, sem inspeção de log ou reexecução. Inspeção dirigida não equivale a leitura exaustiva de toda suíte; sem visual/carga/rede externa/produção/comparação histórica.

## 11. Docs

**AJUSTAR SOMENTE LOW F-01.** README já contém contrato MyLots/cancelamento, novas variáveis, head 0006 e limites de legado/rotação/deploy. Nenhum finding anteriormente corrigido foi duplicado.

Registros administrativos, uso de IA e specs de stories anteriores são snapshots cronológicos: afirmações antigas de pendência/branch/schema/seed não substituem runtime atual. O done histórico do Epic 2 é conclusão local preservada; **o deploy correspondente não ocorreu naquele fechamento**, conforme usuário/documentação. Recuperação conjunta 2+3 permanece necessária. Nenhum relato de produção fabricado.

## 12. Recommendation

**EPIC 2 RETROSPECTIVAMENTE APROVADO**

O único LOW (F-01) era documental e foi corrigido no README; permanecem 0 HIGH e 0 MEDIUM. A natureza retrospectiva e as limitações da revisão (seções 1 e 10) seguem valendo.

| Epic | HIGH | MEDIUM | LOW novo | Veredito |
| --- | --- | --- | --- | --- |
| 1 | 0 | 0 | 0 | EPIC 1 RETROSPECTIVAMENTE APROVADO |
| 2 | 0 | 0 | 1 (resolvido) | EPIC 2 RETROSPECTIVAMENTE APROVADO |
| Total | **0** | **0** | **1** | **PRONTO PARA PRÓXIMOS GATES** |

Problema cruzado real: resumo do seed original do Epic 2 não incorporou completamente o filtro da 3.6 na seção específica do README (F-01); código e consumidores incorporaram. Nenhum outro bug funcional cruzado 1↔2↔estado atual confirmado. LOW opcional já existente no Epic 3 não integra essas contagens.

Readiness refere-se somente aos próximos gates destes reviews. **Não autoriza deploy**, fechamento operacional, main/commit/merge/painel/smoke. Decisões humanas dos gates seguem separadas; mudança posterior de código/testes exige reavaliar evidência pertinente.

Nenhum Git/gh/PR, deploy, `.env*`/segredo lido, código corrigido ou story/status alterado. Epic 3 continua **in-progress**; Epic 4 **não iniciado**. Somente `code-review-epic-1.md` e `code-review-epic-2.md` foram editados nesta sessão. Review encerrado.
