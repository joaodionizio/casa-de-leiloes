# Evidência da Story 5.1 — 28/10/2026

Concluí a auditoria pública usando a SPEC consolidada/autovalidada e o fluxo enxuto
autorizado. Descartei checkpoints intermediários e review nesta sessão conforme
pedido explícito. Não alterei ADs, formato canônico, migrations ou dados de negócio.

## Contrato entregue

`GET /api/lots/{lot_id}/audit`: PUBLIC, no-store, somente leitura.

- Envelope: lot_id, as_of, integrity, phase, settlement_status, settlement,
  bid_count, final_hash, bids.
- integrity: verified/adulterated. phase: scheduled/live/ended/cancelled.
- settlement_status: pending/settled/not_applicable; cancelado não é unsold;
  expirado sem settlement permanece pending.
- Bid: sequence, bidder_alias, amount_cents, placed_at, canonical_version,
  previous_hash, current_hash; ordem crescente, sem limite da sala.
- Settlement: outcome, winner_alias, final_amount_cents, bid_count, final_hash,
  settled_at. Ausente enquanto não persistido.
- Em adulteração, somente lot_id/as_of/veredito são preservados; campos de estado,
  resultado, contagem e hash são null, bids é vazio. A página explica a retenção.
- 404 inexistente; 422 UUID inválido; 500 operacional genérico, sem falso veredito.

Reutilizei canonical v1, verify_bid_chain, AnchorState, verify_anchor_hmac e a
checagem estrutural settlement/receipt. Também conferi contagem/hash, líder/lance,
resultado, valor, pseudônimo, sequência vencedora e datas de liquidação. Não
recalculei aliases. O SELECT único inclui hora do banco e registros no mesmo
snapshot, sem FOR UPDATE, autoflush ou consultas a usuário/carteira/AIC. O handler
encerra a leitura com rollback e não confirma nem repara nada.

DTOs públicos explícitos e contrato OpenAPI exato excluem IDs privados, email,
nome privado, wallet, saldos, committed, JWT e HMAC/âncora. Alias com email
injetado no banco fica retido antes de serializar.

## Testes focais executados

- PostgreSQL: `uv run --project backend pytest backend/tests/integration/test_lot_audit.py -q`
  com os bancos locais isolados e UV_CACHE_DIR temporário: 22 passed, 4.29s.
- Frontend: `node --test src/api/audit.test.ts src/route.test.ts`: 23 passed.
- Navegador: `npx playwright test e2e/audit.spec.ts`: 13 passed, 3.6s.
- Correção dos guards: `uv run pytest tests/test_access_policy.py tests/test_openapi.py -q`
  com banco de teste configurado: 58 passed, 1.56s.
- Ruff/formato, ESLint focal e `npm run typecheck` passaram.

Cobri seis estados públicos e pureza da leitura, 100 lances persistidos,
sequência/aliases/centavos/instantes/hashes, configuração de pseudônimo diferente
sem recálculo, AIC indisponível e número constante de statements. As cinco
adulterações SQL exigidas foram executadas separadamente: valor alterado, inserção,
remoção do meio, truncamento e recálculo da cadeia/resumo sem nova HMAC. Também
cobri líder trocado, âncora ausente, settlement/receipt inconsistentes, alias
privado injetado, 404/422/500 e sessão suja sem autoflush.

Playwright cobriu acesso anônimo sem bloquear na sessão, navegação e retorno,
loading, vazio, pending, sold/unsold/cancelled, adulteração, falha/retry/404,
respostas tardias após desmontagem/troca de lote e 100 eventos com hashes abertos
em 320/1280px sem overflow global. O teste de contrato rejeita campos privados,
estados incompatíveis e sequência inválida. Não executei mutation testing.

## Gate final

Executei exclusivamente a variante `VERIFY_E2E=1 ./verify.sh`.

1. A tentativa dentro do sandbox parou no cache uv antes dos checks.
2. O primeiro gate efetivo parou no backend: 2255 passed e quatro falhas nas
   expectativas exaustivas de rotas/políticas, que ainda não incluíam audit.
3. Atualizei essas listas, acrescentei o contrato público exato no OpenAPI e rodei
   os 58 testes focais. Uma chamada sem TEST_DATABASE_URL foi recusada pela guarda
   antes dos testes; com o banco isolado configurado os testes passaram.
4. Repeti o gate somente por essa falha: exit 0, todas as etapas passaram.

Saída real resumida da execução final:

```text
2260 passed, 1 warning in 135.04s
Frontend Node: tests 187, pass 187, fail 0, skipped 0
Playwright: 5 skipped, 254 passed (30.2s)
verify.sh: todas as etapas passaram.
```

Ruff, formatação, PostgreSQL, ESLint, TypeScript, Vite e Docker passaram. Os cinco
skips são os testes real-stack existentes, opt-in por E2E_REAL_BASE_URL. O warning
Starlette/httpx é preexistente. Logs locais da sessão: `/private/tmp/story-5-1-verify.log`
e `/private/tmp/story-5-1-verify-failed.log`; esses caminhos são evidência auxiliar,
não dependências do contrato ou da story.

## Arquivos e limites

Produção: backend/app/lot_audit.py, backend/app/main.py; frontend/src/api/audit.ts,
AuditPage.tsx, App.tsx, route.ts, LotPage.tsx, App.css.
Testes: backend/tests/integration/test_lot_audit.py, test_access_policy.py,
test_openapi.py; frontend/src/api/audit.test.ts, route.test.ts e e2e/audit.spec.ts.
Documentação: SPEC, story, esta evidência, sprint-status e docs/uso_de_ia.md.

O artefato gerado frontend/test-results/.last-run.json foi alterado fora da lista
prevista pelo Playwright. Nenhum arquivo de segredo apareceu na checagem por nomes;
conteúdo de segredos não foi lido nem comparado. Usei baseline e diff sem Git.

HMAC é autenticação interna do servidor, não prova pública independente. A cadeia
é reproduzível com canonical v1 e hashes publicados; não prova todos os metadados
ou uma autoridade externa. Histórico completo custa O(n), sem paginação nesta story.
Navegador validado em Chromium local; não executei smoke de stack real/Render,
deploy, dispositivo físico ou outros browsers. Review independente e aceite
humano permanecem posteriores. Não iniciei 5.2/5.3, PDF ou painel adicional.

Story/SPEC/sprint 5.1: review. Epic 5: in-progress. Não done.

## Review independente final e fechamento — 28/10/2026

Concluí o review estático dos 14 riscos críticos com revisores Sol
(`gpt-6.1-sol`, raciocínio medium), contra SPEC, story, esta evidência, arquivos
alterados e dependências de integridade/liquidação. Resultado: 0 HIGH / 0 MEDIUM /
0 LOW funcional. Conferi as quatro expectativas antigas contra a baseline sem
Git: só inclusão da rota PUBLIC e deslocamento dos índices, sem enfraquecer
asserções. O contrato OpenAPI exato foi acrescentado.

Não surgiu suspeita concreta que exigisse teste focal; não reexecutei testes,
verify, suíte completa ou mutation testing. Os números acima são evidência da
implementação anterior. Decidi fazer o fechamento documental já autorizado,
marcando Story/SPEC/sprint 5.1 done e preservando Epic 5 in-progress; descartei
repetir gates sem causa. Não alterei código ou testes, não executei Git, não li
`.env*`, não fiz deploy nem iniciei 5.2/5.3.

Registro: [review final](../../implementation-artifacts/code-review-final-story-5-1.md).
