# Deploy manual de recuperação — Epics 2 + 3

Preparado em 26/10/2026; **PENDENTE, NÃO EXECUTADO**. Decidi fazer uma única
recuperação conjunta: o Epic 2 foi concluído localmente e incorporado à `main`
(informação minha), mas seu deploy foi postergado por falha de processo.
Não publico o Epic 2 isoladamente. O Epic 3 continua `in-progress` até concluir
este checklist e registrar evidências, conforme o
[processo canônico](FECHAMENTO-DE-EPICO.md).

## Antes: gates técnicos e preparação manual

- [ ] Confirmo a branch Epic 3 final, todas as stories 3.x `done`, documentação
  sincronizada e estudo concluído quando aplicável (registro/confirmo a evidência).
- [ ] Review agregado do Epic 3 aprovado em sessão/modelo independente,
  com alvo/comparação confirmados por mim e artefato preenchido.
- [ ] Reviews retrospectivos de integração dos Epics 1 e 2 concluídos no mesmo
  candidato; achados relevantes corrigidos e re-review quando necessário.
- [ ] `./verify.sh` completo verde **após a última correção**, com PostgreSQL
  de teste isolado; `VERIFY_E2E=1 ./verify.sh` verde para a UI deste fechamento.
  Registro saídas reais. O último verify histórico da 3.6 precede a correção
  final de assertions; ele não é prova de nova execução do candidato final.
- [ ] Git/commits, push e merge do Epic 3 feitos manualmente por mim; `main`
  remota atualizada e conteúdo final correspondente ao revisado/verificado.
- [ ] Confirmo no painel a branch de produção `main` e o commit a publicar.
  A configuração efetiva atual do painel não foi inspecionada pelo agente.
- [ ] Verifico todas as variáveis abaixo antes de iniciar o deploy. Preservo
  segredos já usados; nenhuma rotação faz parte desta recuperação.

## Render: configuração e variáveis

URL pública registrada no primeiro deploy:
<https://casa-de-leiloes-i1xr.onrender.com>.

| Item | Verificação manual |
| --- | --- |
| Serviço | Web Service Docker existente, Dockerfile da raiz, sem Root Directory que exclua frontend/backend |
| Branch | `main`; substituir a antiga `epic-1` se ainda estiver configurada |
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

## Deploy: executar manualmente depois dos gates

- [ ] No serviço do Render, confirmo novamente `main` e o commit final remoto.
- [ ] Uso **Manual Deploy → Deploy latest commit**. Essa opção publica o commit
  mais recente da branch vinculada. Fonte: [documentação oficial do Render](https://render.com/docs/deploys).
- [ ] Acompanho build da imagem única (React/Vite e Python) e startup.
- [ ] Confirmo `alembic upgrade head` concluído até **`0006`**. A cadeia atual é
  `0001` baseline → `0002` users → `0003` lots → `0004` wallets → `0005` bids →
  `0006` lot_cancellation. Não exijo reaplicação de revisões já aplicadas.
- [ ] Confirmo `python -m app.seed` concluído, antes do uvicorn.
- [ ] Confirmo uvicorn em `0.0.0.0` na porta fornecida e serviço `Live`.
- [ ] Se migration, seed, import/configuração ou startup falhar, interrompo o
  fechamento e registro a falha sem segredos. Não apago banco nem faço downgrade.

O seed usa fixture local, sem AIC: cria contas ausentes (1 leiloeiro, 2
licitantes), garante carteira zerada apenas para quem não tem, preserva saldos
e históricos e cria um demo novo se não houver demo não cancelado, com fim
futuro e âncora não nula. Demos legados sem âncora não contam: ficam intactos,
e nasce um demo autenticado. O seed não cria lances nem redefine senhas/saldos.

## Smoke público: infraestrutura e Epic 2

Executo somente depois de o serviço ficar disponível, pela URL pública. Uso
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

- [ ] Registro data/hora em America/Maceio, branch/commit confirmado por mim,
  URL, revisão Alembic observada, seed/startup/Live, comando/resultado do verify
  final, links dos três reviews e de re-reviews, resultados dos cenários acima.
- [ ] Registro falhas, limitações e cenários não executados. Cold start só ganha
  número se medido; não houve medição nesta tarefa. O primeiro deploy registrou
  expiração do PostgreSQL em 23/11/2026; confirmo a situação atual no painel.
- [ ] Atualizo o registro de fechamento no artefato de auditoria, README/uso
  de IA/deferred-work conforme necessário, sem substituir as evidências da 1.4.
- [ ] Confirmo todos os gates cumpridos e só então autorizo `epic-3: done`,
  commit/push documental manual e início do próximo épico por instrução minha.

| Evidência de execução | Registro |
| --- | --- |
| Responsável/data/fuso | PENDENTE |
| Commit final da `main` e commit efetivamente publicado | PENDENTE |
| Reviews/re-reviews e decisão humana | PENDENTE |
| Verify final e E2E | PENDENTE |
| Migrations/seed/uvicorn/Live | PENDENTE |
| HTTP, UI, API, cookies e papéis | PENDENTE |
| Depósitos/lances/saldos/anti-sniping/cancelamento | PENDENTE |
| Falhas/limitações/cenários não executados | PENDENTE |
| Autorização final para `done` | PENDENTE |
