# Fechamento do Épico 6 — 29/10/2026

**ESTADO VIGENTE FINAL: Épico 6 done; 6.5/6.6/6.7 done — 29/10/2026.**
Decidi concluir o fechamento definitivo após a aprovação técnica agregada local
final (R6-OPT-01 RESOLVED) e o smoke público final do candidato publicado.
Zero novo BLOCKER/HIGH/MEDIUM; LOW externo de acesso ao link oficial da AIC
sob Cloudflare, registrado sem bloqueio. Footer e refinamentos validados em produção.

Preservo o fechamento obrigatório anterior e a reabertura posterior por decisão
humana para opcionais. A sequência terminou em aprovação técnica agregada local,
publicação informada/corroborada funcionalmente, smoke público final e fechamento
definitivo. Candidato local/main: `2a6dc9394be0174a74016b3de46c276eb5ef6074`;
SHA Render não autenticado. Reflog local registra push às 13:18:27−03:00;
coleta publicada 13:25–13:31 America/Maceio, health 200.

[Evidência completa do smoke público final](../_bmad-output/implementation-artifacts/smoke-publico-final-6-5-6-7.md).
Somente documentação/status alterados; sem código, SQL, banco direto, secrets,
commit, push, merge ou deploy. Os estados de reabertura/review/backlog abaixo
são **históricos**, superados por este estado vigente final.

---

## Histórico preservado do fechamento e da reabertura


**Estado vigente: reaberto / `in-progress` para os opcionais.**
Decidi reabrir o Épico 6 em 29/10/2026, depois do fechamento obrigatório abaixo.
6.5–6.7 foram inicialmente cortadas por prazo após a entrega obrigatória e posteriormente reativadas por decisão humana para implementar os opcionais.
Preservo 6.1–6.4 (incluindo 6.2A) como `done` e todas as evidências de produção.
O novo candidato inclui footer institucional e refinamentos pós-entrega derivados
de feedback humano externo: cadastro com senha forte e confirmação somente na
interface, ajuda contextual e informação complementar ao líder. Não atribuo esses
refinamentos ao enunciado da Verzel. Opcionais implementados em `review`, aguardando review agregado independente
posterior; não faço novo deploy nesta rodada.

**Fechamento obrigatório anterior, preservado: concluído / `done`. R6.4-01 — RESOLVED EM PRODUÇÃO.**
Fechamento autorizado expressamente pelo usuário, condicionado à revalidação
focal publicada sem novo BLOCKER/HIGH/MEDIUM. Condição satisfeita no recorte
executado. Stories 6.1, 6.2, 6.2A, 6.3 e 6.4 `done`; 6.5–6.7 continuam
cortadas, não implementadas, `backlog`. A retrospective permanece opcional.

## Identidade e atribuição

- Alvo: <https://casa-de-leiloes-i1xr.onrender.com>.
- Sessão iniciada em **29/10/2026, 11:44:31 America/Maceio (UTC−03:00)**;
  coleta focal conclusiva **11:47:10–11:47:57**, complemento OpenAPI
  **11:52:12**, no mesmo fuso.
- Git somente leitura: `HEAD`, `main` e referência local `origin/main` em
  **`7c285c38b5115198e5eac8da746edc764e28df9e`**,
  `fix: distingue lotes encerrados em apuração e liquidados`, commit de 11:40:14.
  Árvore inicialmente limpa. Reflog de HEAD registra fast-forward para main
  às 11:42:07; reflog de `origin/main` registra **update by push às 11:42:16**.
  Não houve fetch nem consulta da referência remota viva.
- Novo redeploy informado pelo usuário no pedido desta sessão. A resposta nova
  da API e o JS `/assets/index-C6fGFWZt.js` corroboram a publicação da correção;
  a validação anterior registrou `/assets/index-D-J4lFeo.js`.
- **SHA do Render não autenticado.** Não há ID/log de deploy obtido nesta sessão
  nem endpoint que associe criptograficamente serviço e commit. O SHA acima é
  identidade Git local; não é apresentado como SHA verificado do Render.

## Revalidação pública focal

Todos os horários desta tabela são de 29/10/2026, America/Maceio (UTC−03:00).

| Hora | Prova real | Resultado |
| --- | --- | --- |
| 11:47:10 | GET `/health` | **200**, `{"status":"ok"}` |
| 11:47:10 | GET `/api/lots` | **200**; quatro lotes, todos com `settlement_status`, somente `pending` ou `settled`; dois live+pending, dois ended+settled, zero scheduled e zero ended+pending |
| 11:47:10 | GET `/api/lots/98497701-51da-47ff-a6f2-8e3ece875511` | **200**; Water Lilies, `phase=ended`, `settlement_status=settled`; os dez campos de resumo coincidem com a listagem; detalhe tem 18 campos |
| 11:47:12 | Vitrine desktop 1440×1000, DOM, nome acessível e screenshot inspecionado | **Water Lilies: Encerrado**; nome acessível **Water Lilies. Encerrado.**; Judith também **Encerrado**, nome **Judith. Encerrado.**; nenhum desses itens contém “Encerrado, apurando resultado” |
| 11:47:12 | Regressão Vitrine | Fragments e Seurat continuam **Ao vivo**; Próximos lotes exibe **Nenhum lote agendado.**, coerente com API vazia; sem overflow horizontal |
| 11:47:12 / 11:47:46–57 | Raiz, assets e chamadas normais | Raiz, JS `index-C6fGFWZt.js`, CSS `index-D47oPc_N.css`, API e quatro imagens **200**; uma consulta de lotes por montagem da Vitrine; sem polling/detalhes extras por item |
| 11:47:13–19 | Sala e GET público `/api/lots/{id}/bids` do Water Lilies | HTML/API **200**; contrato próprio rico `ended+settled`, settlement preservado com outcome, pseudônimo, valor, contagem, hash e instante; estado visual **Encerrado**; um bloco de status, **zero timers**; um GET de bids pela UI e um WS, encerrado após o terminal; sem nova conexão durante observação de 6 s |
| 11:47:20 | Comprovante `/api/lots/{id}/receipt` e `/lots/{id}/receipt` | API e HTML **200**; UI **Arrematado**; Water Lilies, 11000 centavos, dois lances e mesmo hash anterior |
| 11:47:21 | Auditoria `/api/lots/{id}/audit` e `/lots/{id}/audit` | API e HTML **200**; `integrity=verified`, `ended+settled`; UI **Integridade verificada**; dois lances e hash igual ao comprovante |
| 11:47:46–57 | Observação focal de JS/rede, 4 s por página (Vitrine/Sala) | Zero `pageerror`, zero falhas de transporte, zero requisições não GET; somente `/api/me` **401 esperado para visitante**, registrado pelo console como recurso recusado; nenhum outro HTTP >=400 |
| 11:52:12 | GET `/api/openapi.json` | **200**; `PublicLotSummary` e `PublicLotDetail` incluem `settlement_status` em **required**, enum exato **pending / settled** |

Lote principal, o mesmo do E2E publicado anterior:
**`98497701-51da-47ff-a6f2-8e3ece875511` — Water Lilies**.
Segundo lote settled conferido na Vitrine:
`1d08ed79-3b0e-4a14-afc6-39773e8fdfff` — Judith.
Hash final público preservado:
`5930c83674d431416dbef132e05c90d37cd853f70b99ac7f774c064c1cd4ba2e`.

Listagem conferida por conjunto exato de dez chaves públicas:
`id`, `title`, `artist_display`, `date_display`, `image_url`,
`starting_bid_cents`, `starts_at`, `ends_at`, `phase`, `settlement_status`.
Detalhe acrescenta somente os oito campos públicos previstos:
`external_id`, `medium_display`, `dimensions`, `department_title`,
`artwork_type_title`, `credit_line`, `source_url`, `min_increment_cents`.
Não apareceu campo privado novo, e-mail, identificação real de usuário,
credencial, HMAC, vencedor ou resultado financeiro no resumo/detalhe.

**Pending:** não havia lote naturalmente `ended+pending`. Não criei condição no
banco, não criei lote nem esperei transição. O branch foi comprovado **localmente
pelos testes versionados** em `frontend/e2e/vitrine.spec.ts` (pending/settled,
nomes acessíveis, 1440/375/320), `frontend/src/lotLabels.test.ts` e
`backend/tests/integration/test_public_lots.py`, com gate final registrado na
Story 6.4. Não alego observação publicada desse branch. Também não havia lote
agendado: conferi o estado vazio publicado, preservando a prova local de Agendado.

Sala/QH-01 não regrediu no estado terminal observado. Não reproduzi a corrida
terminal-durante-retry em produção; sua prova versionada e o re-review de
R6-AGG-01 permanecem válidos. Não repeti adulteração, cadeia independente,
cadastros, lances, depósitos ou roteiro E2E anterior.

## Gates e findings preservados

| Gate / finding | Evidência / decisão vigente |
| --- | --- |
| Review agregado independente + re-review | [code-review-epic-6.md §16](../_bmad-output/implementation-artifacts/code-review-epic-6.md); aprovação técnica local preservada, sem inventar novo review nesta sessão |
| R6-AGG-01 / R6-AGG-02 | **RESOLVED**, conforme re-review independente; não reabertos |
| R6.1-01 | **RESOLVIDO**, conforme re-review da 6.1 |
| R6.2-01 LOW | **Aceito**, sem correção nem reclassificação |
| Gate local final após R6.4-01 | `VERIFY_E2E=1 ./verify.sh`, **exit 0**; 2413 pytest, 199 Node, 322 Playwright passed / 7 skipped, Ruff/formato/lint/tsc/Vite/Docker aprovados; prova histórica detalhada na Story 6.4, não reexecutada agora |
| Publicação anterior | [Story 6.4](../_bmad-output/implementation-artifacts/6-4-validação-final-no-ambiente-publicado.md), matriz 11:02–11:16: CA2 público da 6.1 e fluxo completo já comprovados; preservados sem repetição |
| Merge/push/redeploy | Git read-only e relato do usuário delimitados acima; publicação funcional corroborada pela API/UI novas, sem SHA Render inventado |
| R6.4-01 | **RESOLVED EM PRODUÇÃO**, pela revalidação focal acima |
| Findings novos no recorte | **0 BLOCKER / 0 HIGH / 0 MEDIUM**; nenhum novo finding de produto confirmado |

Não foi fornecida nesta sessão uma confirmação separada de estudo humano de cada
story; não a deduzo de testes ou de `done`. A instrução humana explícita atual
autoriza o fechamento documental sob a condição focal satisfeita. Não transforma
limites históricos em novas provas nem cria review/deploy pelo agente.

## Método e limites instrumentais

Browser integrado tentado conforme a skill de controle do navegador; ponte nativa
indisponível. Alternativa: Chromium real via Playwright já instalado, sessão
pública sem login, sem interceptação/mock, somente interfaces HTTPS públicas.
Execução fora do sandbox foi autorizada pela revisão automática para navegador
e rede; nenhum banco, segredo ou operação Git de escrita foi acessado.

Comando focal: `node /private/tmp/atrio64-final-revalidation.cjs`. Todas as
asserções funcionais e capturas passaram; a asserção final genérica de console
terminou **exit 1** porque tratava o 401 esperado de `/api/me` como erro.
Não alego esse runner integral verde. A observação específica
`node /private/tmp/atrio64-final-observation.cjs` correlacionou cada 401 com
`/api/me`, confirmou ausência de exceção JS/transporte/repetição e terminou
**exit 0 / OBSERVATION_PASS**. Antes disso, uma tentativa expirou esperando
`networkidle`, e outra usou seletor de cartão no CTA do destaque; os ajustes
foram apenas no runner temporário. Nenhum desses eventos demonstrou falha do produto.

Evidências temporárias públicas e sanitizadas em `/private/tmp/`:
`atrio64-final-evidence.json`, `atrio64-final-observation.json`,
`atrio64-final-vitrine.png`, `atrio64-final-sala.png`. Capturas foram abertas e
inspecionadas; não são aceite visual humano novo. Este documento e a Story 6.4
preservam as evidências essenciais sem depender da permanência desses arquivos.
Chromium encerrado. Não houve cookie/JWT/senha armazenado, GET acionando apuração,
mutação de produto, mudança de código, commit, push ou deploy.

## Estado final

| Story / épico | Estado |
| --- | --- |
| 6.1 | **done** — CA2 publicado comprovado anteriormente, pendência encerrada |
| 6.2 | **done**, R6.2-01 LOW aceito |
| 6.2A | **done**, review individual deferido foi atendido pelo agregado |
| 6.3 | **done**, agregado aprovado e documentação sincronizada |
| 6.4 | **done**, R6.4-01 resolvido em produção |
| Épico 6 | **done / concluído** |
| 6.5 / 6.6 / 6.7 | **backlog / cortadas / não implementadas**, nunca done |

Fechamento documental conforme [processo canônico](FECHAMENTO-DE-EPICO.md),
instrução humana atual e limites de atribuição registrados. Commit/push destes
documentos continuam manuais fora desta sessão. Nenhuma próxima story iniciada.


## Candidato local dos opcionais — implementação concluída em 29/10/2026

**6.5, 6.6 e 6.7: review. Épico 6: in-progress / reaberto.** Não executei
review independente nesta sessão e paro para um único review agregado dos
opcionais. Não marco done, não faço commit, push, pull, merge, rebase, gh ou
deploy. Preservo 6.1/6.2/6.2A/6.3/6.4 done e todas as evidências anteriores,
inclusive R6.4-01 resolvido em produção. Esta rodada comprova candidato local,
não uma nova publicação.

6.5–6.7 foram inicialmente cortadas por prazo após a entrega obrigatória e posteriormente reativadas por decisão humana para implementar os opcionais.

### Escopo entregue e contratos

**6.5:** busco título, artista e data textual com trim do termo e normalização
case/accent insensitive, sem pesquisar UUID. Todos/Ao vivo/Próximos/Encerrados
se combinam com o termo sobre o snapshot de GET /api/lots. Não criei endpoint,
request por tecla, debounce sem rede ou consulta à AIC. Cancelados continuam
fora do snapshot. Limpar, vazio explícito, foco/Back, labels e anúncio sem spam
estão cobertos. Uso rádios no desktop e select nativo em mobile/tablet para
preservar a obra e a ação no primeiro viewport, sem overflow.

**6.6:** ampliei somente o serviço e a rota existentes. Lote → hora do banco
após trava → dono → histórico autenticado → settlement terminal → idempotência
→ fim → carteira do líder autenticado → invariante → liberação exata →
cancelled_at → flush → commit pela rota → publicação apenas depois do commit.
Total inalterado, comprometido reduzido só pelo valor deste lote e disponível
derivado. Sem lances, nenhuma carteira envolvida. Não alterei/apaguei lances,
sequências, hashes, final_hash, anchor_hmac, bid_count, current_bid_cents ou
current_leader_id. Wallet inconsistente e falhas intermediárias fazem rollback
com erro interno genérico. Outro dono/BIDDER/fim/terminal/adulteração recusam.
Idempotência conserva timestamp, carteira e não duplica evento. Cancel×bid em
ambas as ordens relê o líder atual; cancel×settlement respeita terminal ou
cancelamento válido anterior ao fim. Auditoria pública preserva a cadeia.

No painel, scheduled/live próprios permitem cancelar com ou sem lances;
com lances exibo a confirmação aprovada e CTA Cancelar lote. Protejo envio
repetido, não exponho identidade do líder e não anuncio sucesso em erro.
A Vitrine exclui o cancelado; Meus lotes mostra Cancelado. Mantive exatamente
POST /api/lots/{lot_id}/cancel e o inventário de **sete escritas**, comprovado
pela regressão de test_csrf.py/test_access_policy.py e pelo gate.

**6.7:** tokens em :root e data-theme=dark, color-scheme, inicialização antes
do mount para evitar flash, preferência válida light/dark em atrio-theme e
fallback para prefers-color-scheme. O toggle tem nome acessível dinâmico,
foco e alvo de 44px. Persistência em reload/navegação/login/logout/outra aba,
storage indisponível e reduced-motion têm testes. Textos, muted, marca,
success/warning/danger e ações têm contraste de tokens >=4,5:1 nas superfícies
verificadas. Não dupliquei CSS por componente; impressão usa tokens claros.

**Footer, polimento complementar da 6.7:** marca existente; tagline “Leilões de
arte em domínio público, em tempo real.”; seção O projeto com ÁTRIO — Leilões de
Arte e “Projeto demonstrativo desenvolvido para o Desafio Elite Dev — Verzel.”;
Recursos com [Código-fonte](https://github.com/joaodionizio/casa-de-leiloes) e
[Acervo artístico — Art Institute of Chicago](https://www.artic.edu/collection),
ambos externos com noopener noreferrer. Aviso: “Leilões, saldos, depósitos e
transações são simulados — este é um projeto de demonstração, não uma plataforma
comercial em operação.”. Health real preservado. Fechamento textual exato:

> © 2026 ÁTRIO — Leilões de Arte
>
> Desenvolvido por João Luís Dionízio — Desafio Elite Dev — Verzel

Não abreviei o nome nem acrescentei e-mail, telefone, endereço, CNPJ ou redes
sociais. RockHub é só inspiração estrutural. Desktop usa colunas; mobile uma
coluna; claro/escuro pertencem ao mesmo design system, sem footer forçado escuro.

**Refinamentos pós-entrega derivados de feedback humano externo:** novos
cadastros exigem 8–1024 code points e pelo menos 3 dos 4 grupos Unicode Ll/Lu/Nd
ou P/S. Espaços são preservados e contam no comprimento sem constituir grupo.
Backend valida no RegisterRequest com 422 sanitizado. Não alterei login,
Argon2id, usuários existentes, demos ou JWT. Confirmar senha compara igualdade
literal apenas na interface, incluindo caixa e espaços, com required/mismatch,
aria/foco/limpeza ao corrigir e toggle que preserva ambos os valores. Criar
conta fica disabled inválido e o handler também valida/protege double submit.
Payload continua exatamente email/password/role. Ajuda reutilizável explica
saldos, mínimo, pseudônimo e integridade, abre/fecha por teclado/mouse/toque e
Escape, sem recorte. Contexto financeiro do líder só aparece com carteira e
estado confiáveis, usando “no momento”; some em stale/falha/overlay/mínimo
incerto/outbid/fim. already_winning permanece autoritativo; não mudei AD-7 nem
adquiri carteira extra para explicar UX. Não atribuo esses refinamentos à Verzel.

### Verificações executadas no candidato

| Etapa | Resultado real |
| --- | --- |
| Focais 6.5 | Node **37 passed**; Playwright Vitrine **26 passed**; tipos e lint aprovados |
| Focais 6.6 | PostgreSQL **451 passed**, **34.88 s**, sem skips; Node **19 passed**; Playwright painel/auditoria/WS **89 passed**, **10.8 s** |
| Focais cadastro/6.7 | PostgreSQL cadastro/login/seed **138 passed**, **13.03 s**; Node senha/auth/vitrine/route **43 passed**; tipos/lint/Ruff aprovados |
| Correções de integração | Rodada ampla **278 passed** e duas falhas finais; corrigi layout tablet e seletor exato; reexecução pertinente **81 passed**, **8.5 s**, sem skips |
| Único gate integral | `VERIFY_E2E=1 ./verify.sh` → **exit 0**, “verify.sh: todas as etapas passaram.” |
| Ruff | check aprovado; **111 files already formatted** |
| pytest completo / PostgreSQL real | **2446 passed**, **149.98 s**, 1 warning preexistente |
| Frontend completo | ESLint/typecheck/build Vite aprovados; Node **206 passed**, zero falhas/skips |
| Playwright do gate | **355 passed / 7 skipped**, **41.5 s**; skips eram real-stack opt-in |
| Docker | build de produção aprovado; nenhum deploy |
| Real-stack separado | `E2E_REAL_BASE_URL=http://127.0.0.1:4180 npm run test:e2e -- real-stack.spec.ts --workers=1` → **7 passed**, **4.7 s**, zero skips |
| Smoke financeiro real complementar | **REAL_CANCEL_PASS**: UI/HTTP/WS, estorno exato, total preservado, auditoria/hash/bids preservados, idempotência, Vitrine ausente e participação cancelada |
| Visual temporário | **35 capturas**, claro/escuro, 1440/375/320, sem overflow global; Vitrine/footer/filtros, Sala, formulário e ajuda inspecionados |

As regressões do gate incluem cadastro/login/logout/demos, Vitrine/Sala/timer/
retry/WS, carteira/lance/anti-sniping/settlement, Meus arremates, comprovante,
auditoria e segurança das sete escritas. R6-AGG-01, R6-AGG-02 e R6.4-01 continuam
cobertos pelos testes executados; não alego nova prova publicada dessas corridas.

Usei PostgreSQL 18 descartável na porta 55436, com bancos separados para suíte
e aplicação real. O banco habitual não recebeu estes cenários. Para impedir
leitura implícita de .env na configuração existente, os focais finais/gate e
servidor usaram sitecustomize temporário que desliga só a fonte dotenv; valores
fictícios vieram do ambiente e segredos efêmeros foram gerados em memória, sem
impressão. Não li/copiei conteúdo de .env* ou credenciais privadas. A conferência
por nomes não encontrou arquivo de segredo alterado.

A skill de controle do navegador foi carregada; a ponte integrada estava
indisponível. Usei Chromium local do Playwright como fallback. Capturas de UI
usam fixtures de API e imagens locais; real-stack e smoke usam API/FastAPI/WS/PG
reais, sem interceptação de negócio. Números e resultados vêm dos comandos
executados. O warning de httpx/TestClient é preexistente; o preview dos casos
REST sem mock de socket pode registrar proxy WS ECONNREFUSED, sem teste falho.

Evidências temporárias: `/private/tmp/atrio-optionals-evidence/`, incluindo
verify-final.log, real-stack.log, real-cancel.log/json, logs focais, visual/*.png,
measurements.json, manifest.json e candidate.diff. Os hashes de código/testes
foram comparados com o manifesto anterior ao gate: **nenhuma alteração posterior
nesses arquivos**. A consolidação posterior foi somente documental.

### Limites e próxima etapa

Não executei review independente nesta sessão. As capturas são inspeção visual
de fixtures, sem contrato pixel-perfect ou novo aceite visual humano. Testei
Chromium, não outros motores ou produção. Não publiquei o candidato; as provas
públicas anteriores continuam restritas à entrega obrigatória. Preservo a
limitação existente commit→publicação WS sem outbox. Não houve migration, ledger,
dependência nova ou nova rota de escrita. Aguardo um único review agregado
independente dos opcionais; o épico permanece reaberto/in-progress.

### Arquivos alterados nesta rodada

A comparação é contra a baseline local capturada antes das edições, preservando
as alterações documentais que já existiam. Não usei Git para gerar o diff.
São **59 arquivos**, incluindo testes e artefatos BMAD:

- [README.md](../README.md)
- [_bmad-output/implementation-artifacts/6-5-busca-e-filtro-de-lotes.md](../_bmad-output/implementation-artifacts/6-5-busca-e-filtro-de-lotes.md)
- [_bmad-output/implementation-artifacts/6-6-cancelamento-com-estorno-automatico.md](../_bmad-output/implementation-artifacts/6-6-cancelamento-com-estorno-automatico.md)
- [_bmad-output/implementation-artifacts/6-7-dark-mode.md](../_bmad-output/implementation-artifacts/6-7-dark-mode.md)
- [_bmad-output/implementation-artifacts/epic-6-context.md](../_bmad-output/implementation-artifacts/epic-6-context.md)
- [_bmad-output/implementation-artifacts/sprint-status.yaml](../_bmad-output/implementation-artifacts/sprint-status.yaml)
- [_bmad-output/planning-artifacts/epics.md](../_bmad-output/planning-artifacts/epics.md)
- [backend/app/auth.py](../backend/app/auth.py)
- [backend/app/lot_audit.py](../backend/app/lot_audit.py)
- [backend/app/lot_cancellation.py](../backend/app/lot_cancellation.py)
- [backend/tests/bid_support.py](../backend/tests/bid_support.py)
- [backend/tests/integration/test_lot_cancellation.py](../backend/tests/integration/test_lot_cancellation.py)
- [backend/tests/integration/test_lot_cancellation_concurrency.py](../backend/tests/integration/test_lot_cancellation_concurrency.py)
- [backend/tests/integration/test_lot_room_ws.py](../backend/tests/integration/test_lot_room_ws.py)
- [backend/tests/integration/test_lot_settlement_concurrency.py](../backend/tests/integration/test_lot_settlement_concurrency.py)
- [backend/tests/integration/test_registration.py](../backend/tests/integration/test_registration.py)
- [docs/FECHAMENTO-EPICO-6.md](../docs/FECHAMENTO-EPICO-6.md)
- [docs/uso_de_ia.md](../docs/uso_de_ia.md)
- [frontend/e2e/audit.spec.ts](../frontend/e2e/audit.spec.ts)
- [frontend/e2e/brand.spec.ts](../frontend/e2e/brand.spec.ts)
- [frontend/e2e/keyboard.spec.ts](../frontend/e2e/keyboard.spec.ts)
- [frontend/e2e/my-lots.spec.ts](../frontend/e2e/my-lots.spec.ts)
- [frontend/e2e/post-delivery.spec.ts](../frontend/e2e/post-delivery.spec.ts)
- [frontend/e2e/real-stack.spec.ts](../frontend/e2e/real-stack.spec.ts)
- [frontend/e2e/registration.spec.ts](../frontend/e2e/registration.spec.ts)
- [frontend/e2e/support/mockApi.ts](../frontend/e2e/support/mockApi.ts)
- [frontend/e2e/touch-targets.spec.ts](../frontend/e2e/touch-targets.spec.ts)
- [frontend/e2e/vitrine.spec.ts](../frontend/e2e/vitrine.spec.ts)
- [frontend/e2e/wallet.spec.ts](../frontend/e2e/wallet.spec.ts)
- [frontend/index.html](../frontend/index.html)
- [frontend/src/App.css](../frontend/src/App.css)
- [frontend/src/App.tsx](../frontend/src/App.tsx)
- [frontend/src/AuditPage.tsx](../frontend/src/AuditPage.tsx)
- [frontend/src/ClosedLots.tsx](../frontend/src/ClosedLots.tsx)
- [frontend/src/ContextHelp.tsx](../frontend/src/ContextHelp.tsx)
- [frontend/src/LotBidPanel.tsx](../frontend/src/LotBidPanel.tsx)
- [frontend/src/MyLots.tsx](../frontend/src/MyLots.tsx)
- [frontend/src/RegisterForm.tsx](../frontend/src/RegisterForm.tsx)
- [frontend/src/SiteFooter.tsx](../frontend/src/SiteFooter.tsx)
- [frontend/src/SiteHeader.tsx](../frontend/src/SiteHeader.tsx)
- [frontend/src/ThemeToggle.tsx](../frontend/src/ThemeToggle.tsx)
- [frontend/src/VitrinePage.tsx](../frontend/src/VitrinePage.tsx)
- [frontend/src/WalletPage.tsx](../frontend/src/WalletPage.tsx)
- [frontend/src/api/audit.test.ts](../frontend/src/api/audit.test.ts)
- [frontend/src/api/audit.ts](../frontend/src/api/audit.ts)
- [frontend/src/api/auth.test.ts](../frontend/src/api/auth.test.ts)
- [frontend/src/api/auth.ts](../frontend/src/api/auth.ts)
- [frontend/src/api/lots.test.ts](../frontend/src/api/lots.test.ts)
- [frontend/src/api/lots.ts](../frontend/src/api/lots.ts)
- [frontend/src/contextHelpText.ts](../frontend/src/contextHelpText.ts)
- [frontend/src/index.css](../frontend/src/index.css)
- [frontend/src/lotCancellation.test.ts](../frontend/src/lotCancellation.test.ts)
- [frontend/src/lotCancellation.ts](../frontend/src/lotCancellation.ts)
- [frontend/src/passwordStrength.test.ts](../frontend/src/passwordStrength.test.ts)
- [frontend/src/passwordStrength.ts](../frontend/src/passwordStrength.ts)
- [frontend/src/route.test.ts](../frontend/src/route.test.ts)
- [frontend/src/route.ts](../frontend/src/route.ts)
- [frontend/src/vitrine.test.ts](../frontend/src/vitrine.test.ts)
- [frontend/src/vitrine.ts](../frontend/src/vitrine.ts)

Além dos mapas iniciais, os ajustes necessários ao aceite incluíram route.ts,
route.test.ts e ClosedLots.tsx (restauração e anúncio sem spam), api/lots.ts e
lots.test.ts (retirada da recusa obsoleta), e2e/audit.spec.ts e wallet.spec.ts
(contratos de cancelado com cadeia e controles reais de ajuda). Os demais
componentes/helpers novos constam da story 6.7. Não há segredo alterado por nome.
