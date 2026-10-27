
> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.

# Mapa de implementação e base real

Decidi a sequência abaixo para o futuro build, sem executá-lo nesta sessão. Descartei alterações de schema, reescrita do motor e preparação antecipada de WebSocket.

## Base conferida

| Fonte real | Consequência para a3.5 |
| --- | --- |
| `backend/app/bids.py` | Bid tem PK(lot_id,sequence),alias persistido e dados privados; `read_history` seleciona bidder_id/hashes e não serve como leitura pública. `AcceptedBidResponse` é reutilizável; `register_bid_routes` já é registrado por main |
| `backend/app/lots.py` | Detalhe retorna17 campos e leitura própria com clock materializado; testes pinam keys,statement e igualdade entre papéis; não editar/importar bids neste módulo |
| `backend/app/bid_rules.py` | `minimum_bid_cents(LotBidState)` exige CurrentBid com leader UUID; mínimo pode ser null; só adapto projeção interna no read model |
| `backend/app/lot_time.py`, `money.py` | Fase única recebe now; dinheiro limitado ao inteiro seguro; reutilizar sem mudança |
| `backend/app/access.py`, `errors.py`, `db.py` | api_route/política obrigatórios,NO_STORE,erros sanitizados; Session curta sem commit automático. Global422/500 sem no-store é precedente documentado |
| `frontend/src/LotPage.tsx` | Só arte/termos hoje; usa fase/fim do detalhe em três lugares; substituir fonte dinâmica em todos, preservar obra/ficha/back/foco/title |
| `frontend/src/App.tsx` | Sessão já existe; LotPage não recebe viewer; handleSessionExpired só guarda rota restrita e hoje perderia lote público |
| `frontend/src/api/publicLots.ts`, `api/wallet.ts` | Fetch individual same-origin,guardas simples,resultados discriminados; não há client.ts genérico para reutilizar |
| `frontend/src/walletDeposit.ts`, `WalletPage.tsx` | Registro pendente por owner fora do componente,sem retry e versão contra leituras antigas são os padrões a estender por owner+lote |
| `frontend/src/route.ts`, `navigation.ts` | safeReturnPath já aceita lote conhecido e normaliza; History API e returnTo existentes dispensam novo roteador |
| `frontend/src/money.ts`, `MoneyField.tsx`, `lotTime.ts` | Parser/formatador e readOnly existem; formatter com segundos é adição local; Intl não combina dateStyle/timeStyle com timeZoneName |
| `frontend/e2e/support/mockApi.ts`, `session.spec.ts` | Mock ainda não conhece bids; session exige ausência de lance do BIDDER no lote,contrato que muda deliberadamente |

Stories2.5 e3.1–3.4 foram usadas para herança:17 campos/detalhe; padrão ambíguo/pending da carteira; mínimo nullable/fase; alias persistido/segredo estável;201 e409 do motor. Descrições antigas “ainda não existe”/números históricos dessas stories não substituem o código final nem viram resultado desta sessão.

## Passos e arquivos

| Ordem | Arquivos futuros | Mudança e critério de conclusão |
| --- | --- | --- |
| T1 | `backend/app/bids.py` | DTOs PublicBidRoomResponse/MyLotBidsResponse,duas consultas puras e rotas GET em register_bid_routes; manter POST/modelo/gate/serviço intactos; http-contract completo |
| T2 | `backend/tests/integration/test_bid_reads.py`, `test_openapi.py`, `test_access_policy.py` | B1–B11 e políticas/schemas; auxiliares em bid_support/lot_support somente se reuso necessário |
| T3 | `frontend/src/api/bids.ts`, `bidFeedback.ts`, `bidPosition.ts`, `countdown.ts`, `bidSubmission.ts` + respectivos `.test.ts` | Contratos/classificação,texto,posição,timer/trigger,pending por owner+lote e transições puras; F1–F8 |
| T4 | `frontend/src/LotBidPanel.tsx`, `BidForm.tsx`, `BidHistory.tsx`, `Countdown.tsx` | Componentes finos ligados à lógica; sem framework/dependência/store novos |
| T5 | `frontend/src/LotPage.tsx`, `App.tsx`, `App.css`, `lotTime.ts`, `route.test.ts` | viewer/owner,onSessionExpired,fonte dinâmica única,versões/abort,retorno seguro,layout e hora do histórico com segundos; route.ts/navigation.ts sem mudança esperada |
| T6 | `frontend/e2e/support/mockApi.ts`, `lot-room.spec.ts`, `session.spec.ts`, `vitrine.spec.ts`, `layout.spec.ts`, `keyboard.spec.ts`, `touch-targets.spec.ts` | Mock compatível e E1–E12; ajustar somente expectativas do detalhe que mudaram conscientemente; preservar vitrine |
| T7 | `README.md`, `docs/uso_de_ia.md`, story3.5, `sprint-status.yaml`; `deferred-work.md` apenas dívida real | Documentar resultado real do build,testes e limitações; mudar somente tracking da3.5 quando etapa de build justificar |
| T8 | Comandos do test-plan | Verify normal+E2E; evidência real e roteiro manual; parar após3.5 |

Nenhuma edição prevista em `lots.py`, `bid_rules.py`, `bid_integrity.py`, `lot_time.py`, `money.py`, `wallet.py`, `errors.py`, main/config/seed, migrations,package.json ouverify.sh. `bids.py` ganha leituras sem refatorar `place_bid`. Imports necessários de Lot e mínimo não criam lots→bids. Não crio índice,schema de cancelamento,novos códigos de recusa ou liquidação.

## Documentação futura obrigatória

README: sala não se atualiza por outros clientes; “A sala não se atualiza sozinha; use Atualizar.” permanece visível na sala. Explicar countdown como estimativa visual do último estado lido (pode superestimar; o servidor continua autoridade para aceitar ou recusar o lance) e a linha “Situação atualizada às HH:MM:SS” (`as_of` de `/bids`), útil após suspensão do aparelho,zero com releitura única,anti-sniping cumulativo,feedback imediato201,erro ambíguo sem retry,limite50 exclusivo da sala e leitura que não autentica cadeia. A auditoria5.1 futura mantém histórico completo,sem ser implementada/especificada aqui. Explicar legado lido normalmente masPOST409 e segredo de pseudônimo estável herdado,sem instrução de reassinar/rotacionar. Não prometer idempotência entre abas/reload ou retries manuais.

## Decisões, limites e parada

D1–D5 permanecem fechadas. Fechei nomesDTO/campos,query única pública e consulta própria,estado da UI,trigger/mapeamento/mensagens e arquivos como detalhes autorizados da spec. Não encontrei BLOCKER de produto. Preservo exceção de header422/500 já existente (http-contract) sem mudança global.

Esta execução escreve somente esta pasta de spec; não altera source story/status de ready-for-dev,sprint,arquitetura ou código. Não há autorização de build inferida deste documento. Próxima etapa,quando solicitada,é implementar apenas esta story a partir do contrato; esta sessão termina na spec.
