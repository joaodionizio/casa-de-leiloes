# Deploy manual de recuperação — Epics 2 + 3

Preparado em 26/10/2026; fechamento documental em 27/10/2026.
**RECUPERAÇÃO EXECUTADA — EPIC 3 CONCLUÍDO.** Fiz manualmente o merge do Epic 3,
o push da `main`, a configuração do Render, o deploy conjunto 2+3, a validação
do ambiente público e o smoke dos fluxos entregues; confirmei a aplicação
publicada funcionando. O deploy do Epic 2 **não aconteceu no fechamento original**:
foi postergado por falha de processo e recuperado nesta publicação conjunta.
Não houve deploy isolado retroativo do Epic 2.

A evidência operacional é minha confirmação manual fornecida neste pedido;
a IA apenas a registrou. Não informei horário de execução, ID de deploy, logs,
IDs de lotes, valores observados nem resultado individual dos cenários abaixo.
A data acima é do registro documental, não um timestamp inventado de deploy.
Aplico o [processo canônico](FECHAMENTO-DE-EPICO.md), sem alterar seus gates.

## Gates técnicos e preparação — conclusão registrada

- [x] Stories 3.1–3.6 `done`, conferidas no sprint.
- [x] Review agregado do Epic 3 concluído; F-01 MEDIUM corrigido e aprovado no
  re-review; LOW opcional de cobertura do effect da sala aceito, não bloqueante.
- [x] Reviews retrospectivos de integração dos Epics 1 e 2 aprovados; LOW
  documental do Epic 2 resolvido. Não alego review do diff histórico original.
- [x] `VERIFY_E2E=1 ./verify.sh` completo final após a correção, anterior ao merge:
  exit 0 segundo evidência fornecida; pytest **2036 passed**, npm test
  **160 passed**, Playwright **189 passed, 5 skipped**; Ruff, format, ESLint,
  tsc, Vite build e Docker build passaram. Não reexecutei testes nesta tarefa.
- [x] Merge manual do Epic 3 e push da `main` confirmados pelo usuário.
- [x] Produção na branch **`main`**, commit publicado **`3d3ea97`**.
- [x] Configuração do Render executada manualmente pelo usuário.

Estudo individual, confirmação de cada variável e comparação histórica:
**não individualizado na evidência manual**. A confirmação geral não é uma
inspeção independente pela IA desses detalhes.

## Render: configuração e variáveis

URL pública registrada no primeiro deploy:
<https://casa-de-leiloes-i1xr.onrender.com>.

| Item | Verificação manual |
| --- | --- |
| Serviço | Web Service Docker existente, Dockerfile da raiz, sem Root Directory que exclua frontend/backend |
| Branch | `main`, commit publicado `3d3ea97`, confirmados manualmente |
| Auto-Deploy | Desabilitado; publicação manual |
| Health Check Path | `/health` |
| Comando | `CMD` da imagem; sem Docker Command próprio nem Pre-Deploy Command |
| Processo | Um processo uvicorn; sem acrescentar workers/reload |
| Banco | PostgreSQL existente, URL interna do Render; confirmar disponibilidade e validade do plano no painel |

| Nome | Origem/uso e requisito |
| --- | --- |
| `DATABASE_URL` | Obrigatória. Internal Database URL do PostgreSQL, só no painel; nunca copiar para evidências. Aceita `postgresql://` ou `postgresql+psycopg://`. |
| `APP_ORIGIN` | Obrigatória. Origem HTTPS exata da URL pública, sem caminho/barra final/query; API e SPA na mesma origem. |
| `JWT_SECRET` | Obrigatória. Valor aleatório forte, mínimo de 32 caracteres; manter estável se já configurado. |
| `AUDIT_HMAC_SECRET` | Obrigatória desde 3.4, inclusive para seed. Aleatório forte, mínimo de 32 bytes UTF-8; distinto dos outros dois segredos. |
| `PSEUDONYM_SECRET` | Obrigatória desde 3.4 para o servidor. Aleatório forte, mínimo de 32 bytes UTF-8; distinto dos outros dois segredos. |
| `PORT` | Fornecida pelo Render; o startup a usa, padrão local 8000. Não precisa de valor manual. |
| `SPA_DIST_DIR` | Já definida pela imagem como `/app/frontend-dist`; conferir ausência de override incorreto. |

`TEST_DATABASE_URL`, `VERIFY_E2E` e `E2E_REAL_BASE_URL` são de testes; não são
requisitos de produção. Não há `APP_ENV`, variável de CORS ou credencial da AIC
exigida pelo código atual. Fonte: `backend/app/config.py`, `main.py`, `seed.py`,
`backend/scripts/start.sh` e `Dockerfile`; não li `.env*`.

Sem `AUDIT_HMAC_SECRET` válido, o seed para o startup. O seed não valida
`PSEUDONYM_SECRET`, `JWT_SECRET` ou `APP_ORIGIN`: o servidor os valida depois;
portanto seed concluído sozinho não prova configuração válida. A rotação de
segredos de integridade não é suportada e pode bloquear lotes já assinados.

## Deploy executado — detalhes do roteiro original

- [x] Deploy de recuperação conjunto dos Epics 2 + 3 executado manualmente.
- [x] Aplicação publicada funcionando na URL registrada.

Preservo os detalhes do roteiro sem marcá-los como resultados observados:

- Opção **Manual Deploy → Deploy latest commit** utilizada: **não individualizado na evidência manual**.
- Build e acompanhamento do startup: **não individualizado na evidência manual**.
- Revisão Alembic observada em produção: **não individualizado na evidência manual**.
  A cadeia atual do projeto termina em **`0006`**: `0001` baseline → `0002` users
  → `0003` lots → `0004` wallets → `0005` bids → `0006` lot_cancellation.
- Seed antes do uvicorn, porta e estado `Live` do painel: **não individualizado na evidência manual**.
- Logs de falhas ou interrupções: não fornecidos; não invento ocorrências nem logs.

O seed usa fixture local, sem AIC: cria contas ausentes (1 leiloeiro, 2
licitantes), garante carteira zerada apenas para quem não tem, preserva saldos
e históricos e cria um demo novo se não houver demo não cancelado, com fim
futuro e âncora não nula. Demos legados sem âncora não contam: ficam intactos,
e nasce um demo autenticado. O seed não cria lances nem redefine senhas/saldos.

## Smoke público: infraestrutura e Epic 2

**Smoke público concluído segundo minha confirmação manual.** Cada item específico
não assinalado abaixo tem resultado **não individualizado na evidência manual**;
a caixa vazia indica ausência de evidência individual, não um gate geral pendente.
Os cenários e valores são o roteiro preparado, sem alegação de execução individual.

Roteiro original: executo depois de o serviço ficar disponível, pela URL pública. Uso
contas demo do README, em perfis de navegador separados; identifico os lotes
criados para o smoke e registro seus IDs públicos. São operações reais em dados
de demonstração; não há limpeza por SQL nem adulteração do banco de produção.

- [ ] `GET /health` → 200 JSON `{"status":"ok"}`; este endpoint não consulta o DB.
- [ ] `/` → SPA ÁTRIO/vitrine; JS e CSS reais carregam com MIME correto.
- [ ] Deep-link `/lots/<UUID existente>` e recarga → SPA com detalhe; não usar
  o antigo texto "Serviço no ar" como critério da interface atual.
- [ ] `/api/lots` → 200 JSON, `/api/lots/<id>` → detalhe; `/api/docs` e
  `/api/openapi.json` funcionam; `/api/nao-existe` → 404 JSON, nunca HTML.
- [ ] Login nas três contas demo; `/api/me` corresponde ao papel. Cookie de
  produção `__Host-auction_session`: HttpOnly, Secure, SameSite=Lax, Path=/,
  sem Domain. Logout apaga cookie. Registro só atributos, nunca token/cookie.
- [ ] Sem sessão, carteira retorna 401; com leiloeiro, carteira/depósito/lance
  retornam 403; com licitante, criação/cancelamento retornam 403, usando pedidos
  válidos de mesma origem e JSON. Guard CSRF pode recusar antes da policy.
- [ ] Como leiloeiro, busco uma obra na AIC, confirmo domínio público, abro
  detalhe e crio lote; snapshot/título/atributos/termos aparecem em Meus lotes,
  vitrine e detalhe públicos. Imagem indisponível degrada para placeholder.
- [ ] Vitrine separa ao vivo/agendados/encerrados quando houver esses dados;
  se faltarem estados para provar um cenário, registro pendência, sem inventar sucesso.
- [ ] Verifico as contas semeadas e um demo autenticado com lances abertos;
  carteira existente pode já ter saldo, pois o seed nunca o zera.
- [ ] Pedidos sintéticos pela origem pública: Origin estrangeiro → 403
  `csrf_origin_mismatch`; sem Origin/Referer → 403 `csrf_origin_missing`;
  mesma origem com `text/plain` → 415 `unsupported_media_type`.
  Não colo cookies ou cabeçalhos autenticados em logs/evidências.

## Smoke público: Epic 3

Resultado de cada cenário abaixo: **não individualizado na evidência manual**.
Os valores de R$ 90/100/110/200 são exemplos do roteiro, não valores observados.

Para tornar valores reproduzíveis, crio um lote novo com lance inicial
**R$ 100,00** e incremento **R$ 10,00**, início já alcançado e fim a mais de
dois minutos. Deposito pelo menos **R$ 200,00** em cada bidder se o saldo
disponível ainda não bastar, anotando antes/depois. Comparo **deltas** dos saldos,
pois contas demo são compartilhadas. Se terceiros interferirem, registro e
repito em lote identificado; não afirmo resultado determinístico sobre dados
alterados por outra sessão.

- [ ] Bidder1 abre Carteira: total/comprometido/disponível; depósito aumenta
  exatamente o total e disponível, sem alterar comprometido. Não repito POST
  automaticamente em timeout; releio saldo antes de decidir nova tentativa.
- [ ] Na sala, bidder1 envia **R$ 90,00** antes do primeiro lance: 422
  `below_minimum`, feedback claro, carteira/histórico inalterados.
- [ ] Bidder1 envia **R$ 100,00**: 201; atual=100, mínimo=110, posição
  "ganhando"; comprometido sobe 100 e disponível cai 100, total não muda.
- [ ] Bidder1 tenta **R$ 110,00**: 422 `already_winning`, sem efeitos. Uso valor
  que cumpre o mínimo, pois abaixo dele prevalece `below_minimum`.
- [ ] Bidder2 envia **R$ 110,00**: 201; comprometido de bidder2 sobe 110 e o
  de bidder1 cai 100; total de ambos não muda. Bidder1 clica **Atualizar sala**:
  "superado" e saldo liberado; não espero atualização automática entre navegadores.
- [ ] Em outro lote, licitante que não lidera envia valor que cumpre o mínimo
  mas excede seu disponível: 422 `insufficient_balance`, sem efeitos.
- [ ] Em lote agendado, POST válido recebe 422 `lot_not_started`; em lote de
  fim já passado, 422 `lot_ended`. Leitura não fecha nem liquida; não testo
  scheduler, liquidação, comprovante ou sala WebSocket futuros.
- [ ] Para anti-sniping, uso outro lote novo de janela curta; com `phase=live`
  e `0 < ends_at - as_of <= 2 min` na leitura, envio lance válido com saldo.
  Confirmo na resposta 201 `anti_sniping_applied=true` e `ends_at` anterior
  **+120 segundos**. Registro o antes/depois real; se passou do fim antes do
  aceite, a recusa é correta e repito com margem. Lote nunca reabre.
- [ ] `/api/lots/<id>/bids` público: histórico recente (até 50), valor/hora,
  sequência e aliases `Licitante-` + 16 hex; lance atual coincide com o último.
  Sem nome, email, user_id/bidder_id, hashes ou HMAC. `/bids/mine` autenticado:
  alias, quantidade própria e último valor coerentes para cada bidder.
- [ ] A leitura da sala **não autentica a cadeia**. Registro a coerência
  observável; não declaro auditoria pública integral, endpoint ainda da 5.1.
  A prova de adulteração/gate permanece nos testes PostgreSQL locais isolados;
  nunca adultero produção para smoke. Lote legado sem âncora, se existir,
  responde 409 `lot_integrity_conflict` ao POST, sem reparo automático.
- [ ] Como dono, cancelo outro lote novo sem lances: 200; some da vitrine,
  detalhe e `/bids`/`/bids/mine` retornam 404; permanece em Meus lotes como
  Cancelado. Nova tentativa de lance no cancelado íntegro → 422 `lot_cancelled`.
- [ ] No lote com lances, cancelamento como dono → 422 `lot_has_bids`, sem
  estorno. Não testo cancelamento com estorno opcional da 6.6.

As rotas de POST sem corpo (logout e cancelamento) ainda exigem
`Content-Type: application/json` e Origin/Referer válido. Valores de requests
monetários são inteiros em centavos. Posso usar a UI e conferir as chamadas em
Network; não preciso inventar endpoints de diagnóstico.

## Evidências e conclusão

- [x] Registrei review → correção → verify → merge → deploy → smoke → epic done.
- [x] Registrei os limites da confirmação geral, preservando cenários sem prova individual.
- [x] Sincronizei auditoria, README, uso de IA, deferred-work e sprint neste fechamento.
- [x] Epic 3 `done` autorizado pelo pedido explícito de encerramento do usuário.

| Evidência de execução | Registro |
| --- | --- |
| Responsável operacional | Usuário: merge, push, configuração do Render, deploy, validação e smoke manuais |
| Data/hora operacional e ID de deploy | não individualizado na evidência manual |
| Branch / commit publicado | `main` / `3d3ea97`, confirmados pelo usuário |
| URL / funcionamento | https://casa-de-leiloes-i1xr.onrender.com — aplicação publicada funcionando, conforme confirmação manual |
| Reviews/re-reviews | [Epic 1](../_bmad-output/implementation-artifacts/code-review-epic-1.md) retrospectivo aprovado; [Epic 2](../_bmad-output/implementation-artifacts/code-review-epic-2.md) retrospectivo aprovado; [Epic 3](../_bmad-output/implementation-artifacts/code-review-epic-3.md) aprovado após correção/re-review de F-01 MEDIUM, LOW opcional aceito |
| Verify final e E2E | `VERIFY_E2E=1 ./verify.sh`, exit 0, posterior à correção e anterior ao merge: pytest 2036, npm test 160, Playwright 189 passed/5 skipped; Ruff, format, ESLint, tsc, Vite e Docker build passaram; evidência fornecida, sem nova execução |
| Migrations/seed/uvicorn/Live observados | não individualizado na evidência manual; head atual do projeto `0006` |
| Smoke público | Concluído manualmente pelo usuário para os fluxos entregues; ambiente público validado |
| HTTP, UI, API, cookies, papéis e cada cenário de negócio | não individualizado na evidência manual |
| Cold start, validade atual do plano, falhas específicas e cenários não executados | não individualizado na evidência manual |
| Encerramento | Epic 3 concluído; deploy tardio do Epic 2 recuperado conjuntamente |

Não substituo as evidências originais da Story 1.4 nem apresento a confirmação
geral como logs de cada cenário. Não fiz novo deploy nem smoke nesta sessão.
Epic 4 pode ser iniciado após o commit administrativo manual deste fechamento.
