# Story 3.5 — Dar lance pela sala do lote

Status: done

Chave do sprint: `3-5-dar-lance-pela-sala-do-lote`.
Épico: 3 (Carteira e lances íntegros), `in-progress`. Criação: 26/10/2026.
Consolidação: 26/10/2026.

> Esta story foi escrita sobre o código **real** depois da 3.4 (`done`). **Decisões D1 a D5
> consolidadas em 26/10/2026 (§12): todas fechadas.** Nenhuma decisão bloqueante resta para
> `/bmad-spec`, que fecha os schemas e nomes exatos contra o código real. Nenhum código,
> Git, `.env*`, spec ou build foi executado ao criá-la nem ao consolidá-la.

## 1. Story

Como licitante,
quero dar lance na página do lote e ver o resultado na hora,
para que eu participe do leilão pela interface.

**ADs:** AD-4, AD-6, AD-10, AD-15, AD-19, AD-20, AD-30 (e AD-3, AD-11, AD-29 por herança).

## 2. Objetivo e contexto

A 3.4 entregou o motor (`POST /api/lots/{lot_id}/bids`). A 3.5 **só integra a sala a ele**.
O Épico 3 termina **sem atualização automática entre clientes**: o WebSocket é da 4.1.
O lote cresce de "página pública" (2.5) para "sala": lance atual, mínimo, contagem
regressiva, histórico, carteira, formulário e feedback.

O que torna a 3.5 maior do que "ligar um formulário": **o que a sala precisa ler não existe
na API pública** (§3). Por isso há dois endpoints de **leitura** novos, sem tocar o motor.

## 3. Estado real do código (verificado)

### 3.1 O que já existe e a 3.5 reutiliza

| Peça | Onde | Estado real |
| --- | --- | --- |
| `POST /api/lots/{lot_id}/bids` | `backend/app/bids.py` | `BIDDER`; corpo `{amount_cents}` (`extra="forbid"`). **201** `{bid:{sequence,bidder_alias,amount_cents,placed_at}, lot:{current_bid_cents,ends_at,anti_sniping_applied}, wallet:{total_balance_cents,committed_balance_cents,available_balance_cents}}`, `no-store`. Recusa **422** `{status,code,message}` com `code` ∈ `below_minimum`, `insufficient_balance`, `already_winning`, `lot_not_started`, `lot_ended`. **409** `lot_integrity_conflict`. 401/403/404; 422 `validation_error` para corpo inválido. |
| `GET /api/lots/{lot_id}` | `backend/app/lots.py` | `PUBLIC`, `{as_of, lot}` com 17 chaves **fixadas por teste**. Tem `phase`, `starts_at`, `ends_at`, `starting_bid_cents`, `min_increment_cents`. **Não** tem lance atual, contagem, líder nem histórico. |
| `GET /api/wallet` | `backend/app/wallet.py` | `BIDDER`; `{total,committed,available}`. Já usado por `api/wallet.ts` (`fetchWallet`). |
| `GET /api/me` | `backend/app/auth.py` | `{email, role}` apenas. Sem alias. |
| `minimum_bid_cents(LotBidState)` | `backend/app/bid_rules.py` | Mínimo do domínio (3.2): `starting_bid` sem lance; `atual + incremento` com lance; `None` se passar de `MAX_CENTS`. |
| `generate_bidder_alias` | `backend/app/bid_integrity.py` | Alias determinístico por `(lot_id, user_id)`; segredo via `get_integrity_config` (`app.state.integrity_config`). |
| `Bid` / `read_history` | `backend/app/bids.py` | Tabela `bids`; `read_history` devolve também `bidder_id` e hashes — **não serve** para leitura pública sem projeção própria. |
| `AccessPolicy.OPTIONAL`, `BIDDER`, `NO_STORE`, `error_responses` | `backend/app/access.py`, `errors.py` | Padrão de política declarada por rota; um teste reprova rota sem política. |
| `parseReaisToCents`, `formatCents`, `moneyErrorMessage`, `MoneyField` | `frontend/src/money.ts`, `MoneyField.tsx` | Entrada em reais → centavos sem `float`. |
| `fetchWallet` + padrão de erro ambíguo | `api/wallet.ts`, `walletDeposit.ts`, `walletFeedback.ts`, `WalletPage.tsx` | Modelo exato a seguir: texto nasce do `code`/status, nunca do `message`; envio pendente fora do componente; erro ambíguo = uma releitura, sem afirmar sucesso. |
| `fetchPublicLot`, `LotPage.tsx`, `LotState`, `phaseStatusText` | `frontend/src/` | Página atual: arte + termos + ficha; `phase` e `as_of` vêm do servidor. **Hoje não há lance, campo, carteira, histórico nem contagem** (decisão da 2.5, P3). |
| `formatDateTime`, `asOfText` | `lotTime.ts`, `asOf.ts` | Formatação; `asOf.ts` proíbe `Date.now()` por contrato. |
| `mockApi` (Playwright) | `frontend/e2e/support/mockApi.ts` | Já simula sessão, carteira, depósito e `GET /api/lots/{id}`. Não simula lance nem histórico. |

### 3.2 O que falta (e não pode ser inventado no navegador)

1. **Lance atual, contagem de lances e histórico públicos** — nenhuma rota os entrega.
2. **Pseudônimo do usuário atual no lote** — nenhuma rota o entrega (AD-20 manda um
   endpoint autenticado). `PSEUDONYM_SECRET` nunca vai ao navegador.
3. **Próximo mínimo** — o front não tem o lance atual; recalcular `atual + incremento` no
   navegador duplicaria a regra da 3.2 e o tratamento de `MAX_CENTS`.
4. **Referência de hora do servidor para a contagem** — `as_of` + `ends_at` já existem na
   leitura do lote; a resposta do `POST` traz `bid.placed_at` (hora do banco da operação).
5. Toda a UI da sala, a rota de volta ao lote depois de sessão expirada (`App.tsx`) e a
   simulação de lance no Playwright.

### 3.3 Restrições do código existente que a story precisa respeitar

- `test_detail_has_the_17_keys...`, `test_detail_is_the_same_for_every_role` e
  `test_each_route_runs_exactly_one_statement_with_one_clock` (em
  `backend/tests/integration/test_public_lots.py`) **fixam** o detalhe público: uma
  instrução (`WITH clock ... FROM clock LEFT OUTER JOIN lots`), sem `ORDER BY`/`LIMIT`/`WHERE`,
  idêntico para todos os papéis. Enriquecer `GET /api/lots/{id}` quebraria três contratos da 2.5.
- `lots.py` **não** pode importar `bids.py` (`bids.py` já importa `lots.py`): ler `Bid` a
  partir de `lots.py` cria import circular.
- O 201 não traz `minimum_next_bid_cents` nem histórico; alterar o contrato da 3.4 está fora
  de escopo.
- `App.tsx → handleSessionExpired` só devolve à rota atual se ela for restrita; a página
  do lote não é, então um 401 durante o lance mandaria o usuário à vitrine.
- `e2e/session.spec.ts` (≈l.170–175) afirma que o licitante **não** vê "Dar lance" no lote.
  Passa a ser falso: o teste muda de propósito (§9).

## 4. Escopo

**Dentro:** (a) dois endpoints de **leitura** (`GET`, sem trava, sem escrita), (b) a sala no
front (contagem, lance atual, mínimo, posição, carteira, formulário, feedback, histórico),
(c) testes proporcionais, (d) README e `uso_de_ia.md`.

**Fora (confirmado):** WebSocket, heartbeat, reconexão, fechamento, liquidação, comprovante,
auditoria pública (5.1), cancelamento (3.6), Épico 4. Nenhuma alteração em `place_bid`,
locks, contabilidade de carteira, SHA/HMAC, `CanonicalBid`, gate de integridade. Nenhuma
migration. Nenhuma `Idempotency-Key`. Nenhum polling, nenhum loop de releitura, nenhuma
paginação ou cursor.

**3.5 e 4.1 (fronteira):**

| Story 3.5 | Story 4.1 |
| --- | --- |
| Leitura por HTTP | WebSocket |
| Atualização depois das ações do próprio cliente | Atualização causada por **outros** clientes, sem refresh |
| Uma releitura em `0:00` e botão "Atualizar sala" | Snapshot ao (re)conectar |
| `GET /bids` como read model da sala | Reaproveita/evolui esse read model no snapshot e nos eventos |

**Os 50 lances da sala não são o contrato da auditoria.** A Story 5.1 continua responsável
pelo histórico **completo**; o limite de 50 é só da sala e não vira requisito da 5.1.

## 5. Critérios de aceite

**AC1 — Sala ao vivo (original).** Dado um lote ao vivo, quando qualquer pessoa abre a sala,
então vê o lance atual (ou "Sem lances ainda", com o lance inicial), o mínimo para o próximo
lance, a contagem regressiva calculada a partir de dados do servidor e o histórico com
pseudônimo, valor e hora.

**AC2 — Pseudônimo próprio (original).** Dado um licitante logado na sala, então descobre seu
pseudônimo naquele lote (mesmo sem ter dado lance), obtido do servidor; o front nunca o deriva.

**AC3 — Recusas (original).** Para cada código `below_minimum`, `insufficient_balance`,
`already_winning`, `lot_not_started`, `lot_ended` aparece a mensagem exata da tabela da §8,
em português, escolhida pelo `code`, nunca pelo `message`. `lot_integrity_conflict`
(409) tem mensagem própria. Nenhuma recusa afirma lance registrado.

**AC4 — Lance aceito (original).** Depois do 201, a sala mostra o novo lance atual, o novo
fim (`ends_at`) e o saldo disponível vindos da resposta; o histórico e o mínimo vêm da
releitura que se segue (§7, "Após 201").

**AC5 — Privacidade (original).** O histórico público e as respostas novas não contêm nome,
e-mail, `user_id`, `bidder_id`, hashes nem HMAC (teste de chaves e de valores).

**AC6 — Visitante e leiloeiro (original).** Veem o lote, o lance atual, a contagem e o
histórico, mas **nenhum formulário de lance**, e o front não chama `bids/mine` nem
`/api/wallet` para eles. O visitante vê o caminho para entrar; o leiloeiro, um texto curto.

**AC7 — Contagem sem autoridade.** A contagem usa só `as_of`/`ends_at` do servidor e um
relógio **monotônico** (`performance.now`), nunca `Date.now()`/relógio de parede. Ela é só
apresentação: em `0:00` a sala mostra "Confirmando encerramento com o servidor…" e **não**
bloqueia o envio nem declara o lote encerrado; quem decide aceite, recusa e fase é o
servidor. O botão só é bloqueado enquanto há um envio pendente.

**AC7a — Uma releitura em `0:00` (D5).** Quando a contagem derivada chega a `0:00`, a sala faz
**uma** releitura (`GET /bids`, e `bids/mine` e carteira para o licitante), armada **uma vez por
valor de `ends_at`**. Sem polling e sem loop: se o servidor ainda disser "ao vivo" com o mesmo
`ends_at`, a sala continua em "Confirmando…" e só uma ação explícita ("Atualizar sala")
relê. Se vier `phase = ended`, mostra o encerramento; se vier `ends_at` posterior
(anti-sniping de outra pessoa), recalcula a contagem e reabre o gatilho para o novo valor.

**AC8 — Anti-sniping.** Depois de um 201 com `anti_sniping_applied = true`, a contagem passa
a usar o novo `ends_at` e a sala diz que o prazo foi prorrogado. A UI só reflete o servidor.

**AC9 — Envio.** Durante o `POST`: botão "Enviando lance…" desabilitado, campo somente leitura,
`aria-busy`; Enter e clique duplo não geram segundo `POST`, nem após remontar a página.

**AC10 — Erro ambíguo.** Rede, 5xx ou 201 fora do contrato: nenhuma afirmação de sucesso nem
de falha, uma única releitura do estado, valor digitado preservado, nenhum reenvio
automático, texto manda conferir antes de tentar de novo.

**AC11 — Estados da fase.** Agendado: sem formulário, texto "Os lances abrem em …". Ao vivo:
formulário (licitante). Encerrado: "Encerrado, apurando resultado", sem formulário, sem
vencedor afirmado, histórico consultável.

**AC12 — Posição.** Licitante vê "✓ Você está ganhando", "↑ Você foi superado" ou nada
(neutro), por texto + símbolo, nunca só por cor; "Você" marca suas linhas no histórico.

**AC13 — Sessão.** 401 em qualquer chamada autenticada da sala → fluxo de sessão expirada
existente, **voltando ao mesmo lote (`/lots/{lot_id}`) depois do login**, pelo mecanismo
`returnTo`/`history` já existente (`route.ts`, `navigation.ts`). Sem open redirect:
`safeReturnPath` continua devolvendo só o caminho normalizado de uma rota interna conhecida.

**AC16 — Sem validação de domínio no navegador (D4).** O navegador só valida formato e
entrada (vazio, vírgula, casas decimais, positivo, tamanho). Não bloqueia o envio por valor
abaixo do mínimo nem por saldo insuficiente, e não usa o mínimo/saldo exibidos como
autoridade: `below_minimum` e `insufficient_balance` chegam do servidor.

**AC14 — Contratos.** Endpoints novos: schema tipado, política declarada, `no-store`,
OpenAPI testado, `error_responses` corretos.

**AC15 — Acessibilidade e responsividade.** Foco, rótulos, `role="status"`/`alert`, alvo de
toque ≥ 44 px, sem rolagem horizontal em 320 px, painel antes do histórico no mobile.

## 6. Contratos HTTP

### 6.1 Reutilizados, sem mudança
`POST /api/lots/{lot_id}/bids` (3.4), `GET /api/lots/{lot_id}` (2.5), `GET /api/wallet` (3.1),
`GET /api/me`, login/logout (2.2).

### 6.2 Novos (D1, D2, D3 fechadas; nomes exatos de schema fechados na `/bmad-spec`)

Conceitualmente, `GET /bids` fornece: lance atual, **alias do líder atual** (o `bidder_alias`
do primeiro item de `bids`, sem campo duplicado), mínimo para o próximo lance, `bid_count`
total, até 50 lances recentes (mais recente primeiro) e os dados temporais vivos da sala
(`as_of`, `phase`, `ends_at`). Os dados estáticos (obra, termos, `starts_at`) continuam no
detalhe da 2.5, que **não é alterado**.

**`GET /api/lots/{lot_id}/bids`** — `PUBLIC`, `Cache-Control: no-store`, `responses = 404, 422`.
Mesmo caminho do `POST`, métodos diferentes.

```json
{
  "as_of": "2026-10-26T14:30:00.123456Z",
  "phase": "live",
  "ends_at": "2026-10-26T15:00:00.000000Z",
  "current_bid_cents": 125000,
  "bid_count": 7,
  "minimum_next_bid_cents": 130000,
  "bids": [
    {"sequence": 7, "bidder_alias": "Licitante-A83F19C2D4E5B601",
     "amount_cents": 125000, "placed_at": "2026-10-26T14:29:41.500000Z"}
  ]
}
```

- `bids`: **só** `sequence`, `bidder_alias`, `amount_cents`, `placed_at`; ordem
  `sequence DESC` (mais recente primeiro); no máximo 50 (D2). `bid_count` é o **total** do
  lote (o front diz "50 mais recentes de N"). Sem paginação nem cursor. Nunca `bidder_id`,
  `user_id`, nome, e-mail, `previous_hash`, `current_hash` nem HMAC.
- `current_bid_cents` é `null` sem lances. `minimum_next_bid_cents` vem de
  `minimum_bid_cents` (reuso da 3.2, nenhuma fórmula nova); `null` quando nenhum valor até
  `MAX_CENTS` o alcança. `phase`, `as_of` e `ends_at` saem do **mesmo** snapshot.
- **Snapshot coerente:** lote, `bids` e `as_of` na mesma leitura. Invariante testável:
  `bids[0].amount_cents == current_bid_cents` e `bids[0].sequence == bid_count` (quando há
  lances). Preferência: **uma instrução** (CTE `clock` + `LEFT OUTER JOIN` do lote + subconsulta
  `LATERAL` limitada a 50), no padrão da 2.5; alternativa aceitável: transação
  `REPEATABLE READ` somente leitura. O build escolhe e prova com teste (o mesmo risco SR-08 C
  que o `deferred-work.md` já registra para a 5.1).
- Sem `FOR UPDATE`, sem escrita, sem `bidder_id`, sem hash, sem HMAC. **Não autentica a
  cadeia** (isso é a 5.1; AD-19: leitura pura). O estado mostrado é o armazenado; a defesa
  de escrita continua sendo o gate da 3.4. Vai ao README.
- Lote inexistente → 404 `not_found`; `lot_id` malformado → 422 sem tocar o banco.

**`GET /api/lots/{lot_id}/bids/mine`** — `BIDDER`, `no-store`, `responses = 401, 403, 404, 422`.

```json
{ "bidder_alias": "Licitante-A83F19C2D4E5B601", "my_bid_count": 2, "last_bid_cents": 120000 }
```

- Resposta mínima, **sem `is_leading`**. O campo da contagem própria aparece aqui como
  `my_bid_count` para não se confundir com o `bid_count` **total** do `GET /bids`; a spec
  confirma o nome final.
- `bidder_alias`: `generate_bidder_alias(lot_id, user.id, PSEUDONYM_SECRET)` (primitive da
  3.3), sempre presente (determinístico), mesmo com `my_bid_count = 0`. Nunca calculado no
  navegador.
- `my_bid_count` e `last_bid_cents` contam os lances **pela coluna `bidder_alias`** (coberta
  pelos bytes canônicos), não por `bidder_id` (não autenticado pelo v1). `last_bid_cents`
  é `null` se nunca lançou. Nenhum lance de outra pessoa, nenhum ID.
- É o "endpoint autenticado" que o AD-20 e a 4.1 pedem; a 4.1 pode evoluí-lo sem mudar a
  regra de identidade.

Nenhuma migration: `bids` já tem PK `(lot_id, sequence)`; o filtro por alias roda sobre as
linhas do lote (escala do desafio).

## 7. Comportamento do front

### 7.1 Carga
`LotPage` passa a receber `viewer`: `checking | visitor | auctioneer | bidder` (de `App`,
sem nova chamada). Em paralelo, com `AbortController`:

- sempre: `GET /api/lots/{id}` (obra e termos estáticos) e `GET /api/lots/{id}/bids`
  (estado vivo);
- só `bidder`: `GET /api/lots/{id}/bids/mine` e `GET /api/wallet`;
- `checking`: não decide o formulário (evita piscar); resolve quando a sessão responder.

**Fonte única do dinâmico:** `ends_at`, `phase` e `as_of` da sala vêm **somente** de
`/bids`. O `ends_at`/`phase` do detalhe são ignorados na sala (o `ends_at` do detalhe fica
velho após anti-sniping). Isso inclui a linha "Termina…" e a lista "Término" já existentes.
O mesmo vale para falha parcial: sem `/bids` a sala mostra erro com "Tentar novamente"; o
detalhe estático continua visível.

### 7.2 Contagem regressiva (AD-6)
`restante = (ends_at − as_of) − (performance.now() − recebidoEm)`. Âncora refeita a cada
snapshot (`as_of`) e, no 201, em `bid.placed_at`. Nas duas âncoras o instante do servidor
nasce antes de a resposta chegar ao navegador, então o erro eventual é sempre **para mais**:
a contagem pode **superestimar** o restante (por ≈ um RTT), nunca subestimar; a releitura
seguinte a corrige. Por isso ela nunca é autoridade de encerramento. A sala mostra
"Situação atualizada às HH:MM:SS" com o `as_of` do `GET /bids` (não o do detalhe da 2.5):
se o aparelho dormir e o relógio monotônico ficar velho, a pessoa vê quando foi o último
snapshot. Só texto: sem timer, polling, `visibilitychange`, foco ou detecção de suspensão.
Relógio de parede nunca entra: pular o relógio do aparelho não muda a
contagem. Formato (apresentação): `MM:SS`, `HH:MM:SS`, `2 d 04 h`. Nunca negativa.
`role="timer"`, `aria-live="off"`; o horário absoluto do fim em texto estático ao lado.
Em `0:00`: "Confirmando encerramento com o servidor…", sem declarar encerrado, sem
bloquear o envio, e **uma** releitura (AC7a, D5).

### 7.3 Após 201 (Q5)
Aplica **imediatamente** `lot.current_bid_cents`, `lot.ends_at`, `wallet` e o aviso de
aceite; **em seguida** uma releitura de `/bids` + `/bids/mine` para histórico, mínimo,
contagem total e posição (o 201 não os traz e o front não os calcula; não é polling).
Enquanto a releitura está pendente, o mínimo mostra "atualizando…"; se ela falhar, a sala mantém o
que o 201 trouxe, mostra "Lance aceito, mas não foi possível atualizar a sala" com
"Atualizar", e o mínimo aparece como indisponível. Uma versão (`useRef`) impede que uma
leitura antiga sobrescreva uma resposta mais nova (padrão da `WalletPage`).

### 7.4 Após recusa conhecida
Mensagem da §8 em `role="alert"`, valor digitado mantido, foco no campo. Uma releitura
(`/bids`, `/bids/mine`, `/api/wallet`) porque o mínimo, o líder, o saldo ou a fase podem ter
mudado. `lot_ended` e `lot_not_started` atualizam a fase pelo snapshot. 401 → sessão
expirada. 403 → texto de papel errado. 404 → "Lote não encontrado".

### 7.5 Após erro ambíguo (Q7)
Rede, 5xx ou corpo fora do contrato: `walletDeposit`-style, uma releitura (§7.4), texto
neutro (§8). Nunca "aceito" nem "não registrado". O marcador "✓ Você está ganhando" pode
aparecer — é estado do servidor, não afirmação sobre a tentativa.

### 7.6 Formulário
- Campo em reais com `MoneyField`; `parseReaisToCents`; vazio por padrão.
- Atalho "Usar o mínimo ({R$})" **só aparece com o campo vazio ou inválido** e nunca sobrescreve
  valor válido digitado (EXPERIENCE §9). É o único atalho.
- Validação do navegador: apenas formato (vazio, vírgula, casas, positivo, tamanho). O
  mínimo e o saldo são **exibidos**, nunca usados para impedir o `POST`; abaixo do mínimo e
  saldo ficam com o servidor (D4, AC16).
- Envio pendente registrado **fora do componente**, por `usuário|lote` (como `walletDeposit.ts`),
  para sobreviver a remontagem e impedir segundo `POST`.
- Sem `minimum_next_bid_cents` (`null`, só perto de `MAX_CENTS`): mostra "Não há valor possível
  acima do lance atual." no lugar do mínimo; o formulário continua e o servidor responde
  `below_minimum` (D4).

### 7.7 Posição (Q6, D3)
Função pura. `lider = bids[0].bidder_alias` (o lance mais recente é o do líder; só existe
com lance atual); `meu = mine.bidder_alias`.
- **Ganhando:** há lance atual e `meu == lider`.
- **Superado:** `mine.my_bid_count > 0` e `meu != lider`.
- **Ainda não participou (neutro):** `mine.my_bid_count == 0`.

Funciona mesmo que o último lance do usuário esteja fora da janela de 50, porque
`my_bid_count` vem do servidor. Se `phase = ended`, a sala não mostra "ganhando/superado"
(não afirma vencedor) e mostra "Seu último lance: R$ X" quando `last_bid_cents` existir.

### 7.8 Atualização manual (D5)
Botão **"Atualizar sala"** (refaz as leituras da §7.1), disponível sempre que a sala está
carregada **e sem POST de lance pendente**, incluindo depois do `0:00`. Durante o envio
(`submitting`) ele fica desabilitado, como o botão de lance, para não disputar a tela com o
resultado do POST; ao fim do POST volta ao normal. Texto fixo: "A sala não se atualiza sozinha; use
Atualizar." Será substituído pela 4.1 (WebSocket). Não há polling nem loop.

## 8. Mapa de estados e textos

| Estado | Visitante | Leiloeiro | Licitante |
| --- | --- | --- | --- |
| Carregando | `role=status` "Carregando lote…" | idem | idem |
| `/bids` falhou | erro + "Tentar novamente"; detalhe estático visível | idem | idem |
| Agendado | "Os lances abrem em {início}" | idem | idem |
| Ao vivo, sem lances | lance inicial, mínimo, contagem, "Nenhum lance ainda" | idem | + formulário |
| Ao vivo, com lances | lance atual, mínimo, contagem, histórico | idem | + posição, saldo, formulário |
| Ao vivo, `0:00` | "Confirmando encerramento com o servidor…" + uma releitura | idem | idem, formulário **não** bloqueado; o servidor decide |
| Encerrado | "Encerrado, apurando resultado", histórico | idem | idem, sem formulário |
| Sem mínimo (`null`) | texto de limite | idem | texto de limite; formulário segue, o servidor decide |
| Enviando | — | — | botão "Enviando lance…", campo `readOnly` |
| Aceito | — | — | `✓ Lance de {R$} registrado.` (+ `Prazo prorrogado…`) |
| Recusado | — | — | `✕` + texto abaixo |
| Ambíguo | — | — | `!` + texto abaixo |
| Líder / superado | — | — | `✓ Você está ganhando` / `↑ Você foi superado` |
| Histórico vazio / com lances | "Nenhum lance ainda." / lista com "Você" | idem | idem |
| Chamada sem papel | visitante: "Entrar para dar lance" (→ login, volta ao lote) | "Sua conta é de leiloeiro: você acompanha o lote, mas não dá lances." | — |

| Código | Texto exibido |
| --- | --- |
| `below_minimum` | Seu lance está abaixo do mínimo para este lote. Confira o valor mínimo acima. |
| `insufficient_balance` | Saldo disponível insuficiente para este lance. (+ link "Ir para a carteira") |
| `already_winning` | Você já está ganhando este lote. |
| `lot_not_started` | Este lote ainda não começou. |
| `lot_ended` | Este lote já foi encerrado. |
| `lot_integrity_conflict` | Não foi possível verificar a integridade deste lote. O lance não foi registrado. |
| 422 `validation_error` | Informe um valor válido em reais. (no campo) |
| ambíguo | Não foi possível confirmar o lance. O estado abaixo é o atual do servidor; confira antes de tentar de novo. |
| outro 4xx (csrf, 415...) | Não foi possível enviar o lance. Recarregue a página e tente novamente. |

Texto, ícone e cor sempre juntos. Os textos acima são o contrato de teste.

## 9. Testes

### 9.1 Front, puros (`node --test`, sem DOM)
- `api/bids.ts`: classificação do `POST` (aceito, cada `code`, 409, 401, 403, 404, validação, outro 4xx,
  rede, 5xx, 201 fora do contrato, corpo não JSON); guardas dos dois `GET` (rejeitam campos faltando
  e valores inválidos; ignoram chaves extras sem exibi-las).
- `bidFeedback`: tabela §8 exata, **por `code`** (um teste prova que o `message` do servidor é ignorado).
- `bidPosition`: ganhando / superado / neutro / `ended` / sem lances; **último lance do usuário
  fora da janela de 50** (`my_bid_count > 0`, alias ausente de `bids`) continua "superado".
- `countdown`: `restante` com relógio monotônico injetado; limites (0, 1 ms, exatamente 2 min);
  nunca negativo; âncora trocada por novo snapshot; formatos `MM:SS`, `HH:MM:SS`, `2 d 04 h`;
  prova de que `Date.now` não é lido (ex.: `Date.now` lança no teste).
- Gatilho de `0:00`: arma **uma vez por `ends_at`**; mesmo `ends_at` depois da releitura não
  rearma; `ends_at` novo rearma.
- Estado do formulário: vazio/inválido/válido → atalho visível; barreira de envio duplo; **o
  formulário valida só formato**: valor abaixo do mínimo e valor acima do saldo passam à
  etapa de envio (D4).
- `route.test.ts`: `safeReturnPath` aceita `/lots/{uuid}` e continua rejeitando URL absoluta,
  `//host`, `/login` e texto livre (sem open redirect).

### 9.2 Back-end (PostgreSQL real, `tests/integration/test_bid_reads.py`)
Só o **novo contrato**; não repete concorrência, rollback, HMAC ou ordem de locks da 3.4.
- `GET /bids`: lote sem lances (campos nulos, mínimo = lance inicial); com lances (ordem
  `DESC`, mínimo = atual + incremento); `MAX_CENTS` → `minimum_next_bid_cents = null`; limite de 50
  com `bid_count` total real (51 lances → 50 itens, `bid_count = 51`, o mais recente primeiro);
  chaves **exatas**; ausência de `bidder_id`, e-mail, hashes, HMAC e UUIDs
  de usuário em chaves e valores; 404; 422; `no-store`; idêntico para todos os papéis;
  uma instrução com um `clock_timestamp()` e sem `FOR UPDATE`; invariante de coerência
  (`bids[0]` = `current_bid_cents`/`bid_count`) com commit concorrente; `phase` com `now` fixo;
  anti-sniping refletido em `ends_at` depois de um lance real.
- `GET /bids/mine`: chaves exatas (`bidder_alias`, `my_bid_count`, `last_bid_cents`; **sem
  `is_leading`**); alias igual ao `generate_bidder_alias` e ao gravado no lance; mesmo alias
  antes e depois do primeiro lance; contagem e último valor só do próprio alias (dois
  licitantes, incluindo lance fora da janela de 50 do `GET /bids`); `last_bid_cents = null`
  sem lances; 401 anônimo, 403 leiloeiro, 404, 422; `no-store`; resposta sem segredo.
- Os dois `GET` não escrevem nem travam (padrão de `test_public_lots`: sem `FOR UPDATE`, sem
  conexão ociosa em transação).
- `test_openapi.py` (caminhos, `responses`, schemas) e `test_access_policy.py`
  (`PUBLIC` e `BIDDER`) atualizados; o teste "toda rota declara política" segue verde.

### 9.3 Playwright (Chromium, API simulada, `frontend/e2e/`)
`mockApi` ganha um leilão com estado: `GET /bids`, `GET /bids/mine`, `POST /bids` (modos:
aceito, aceito com anti-sniping, cada recusa, `integrity`, `server_error`, `network`, atraso) e
carteira que muda com o aceite. Use `page.clock` para a contagem (sem esperar tempo real).
- visitante sem formulário e com "Entrar"; leiloeiro sem formulário e **sem** `bids/mine`/`wallet`;
  licitante com formulário;
- aceito: lance atual, saldo, histórico (após releitura) e "Você" atualizam;
- cada um dos cinco motivos exibe a mensagem exata e mantém o valor digitado;
- botão e campo bloqueados durante o `POST`; segundo `POST` não sai (clique duplo, Enter, remontagem);
- erro ambíguo: sem afirmação, uma releitura, nenhum reenvio;
- privacidade: nenhuma string de e-mail/ID no DOM da sala;
- anti-sniping: `ends_at` novo e contagem reiniciada;
- `0:00` (com `page.clock`): mostra "Confirmando…", faz **exatamente uma** releitura (contar
  `GET /bids`), não bloqueia o botão, e sem outra releitura enquanto nada muda; `phase = ended`
  na releitura mostra o encerramento; `ends_at` posterior recomeça a contagem; "Atualizar
  sala" refaz as leituras;
- D4: valor abaixo do mínimo e valor acima do saldo **chegam ao servidor** (o `POST` sai) e
  mostram `below_minimum` / `insufficient_balance`; formato inválido não gera `POST`;
- posição: ganhando, superado e neutro, inclusive com o último lance do usuário fora dos 50;
- 401 no lance volta ao **mesmo lote** (`/lots/{id}`) após o login, e só a ele;
- 320 px e 1280 px: sem rolagem horizontal, painel antes do histórico no mobile, alvos ≥ 44 px
  (estende `layout.spec.ts`, `touch-targets.spec.ts`, `keyboard.spec.ts`);
- ajuste consciente de `session.spec.ts`/`vitrine.spec.ts`: o licitante agora **vê** "Dar lance" no
  lote; o visitante continua sem botão.

### 9.4 Manual (roteiro curto para mim)
Dois navegadores no demo: lance no A; B vê o novo lance só após "Atualizar"; B supera A; A volta e
vê "↑ Você foi superado"; saldo insuficiente; lance nos últimos 2 minutos prorroga; lote vencido.

## 10. Tarefas

- [x] **T1 Back-end — leituras (AC1, 2, 5, 14).** `GET /bids` e `GET /bids/mine` em `bids.py`
  (DTOs, projeção própria sem `bidder_id`/hash, snapshot coerente, política declarada).
  Testes da §9.2. OpenAPI e política.
- [x] **T2 Front — contrato e lógica pura (AC3, 7–10, 12).** `api/bids.ts`, `bidFeedback.ts`,
  `bidPosition.ts`, `countdown.ts`, registro de envio pendente. Testes da §9.1.
- [x] **T3 Front — sala (AC1, 4, 6, 8, 11–13, 15).** `LotPage` recebe `viewer`; componentes
  `LotBidPanel`, `BidForm`, `BidHistory`, `Countdown`; `App.tsx` (`viewer` e retorno ao lote
  em 401: `handleSessionExpired` passa a guardar `returnTo` também para a rota do lote;
  `safeReturnPath` já aceita lote); estilos em `App.css` com os tokens existentes.
- [x] **T4 Playwright (§9.3)** e ajustes dos specs existentes.
- [x] **T5 Documentação.** README (seção "Lances"/"Vitrine e página do lote": sala sem
  atualização automática, contagem, erro ambíguo, histórico limitado, leitura sem
  autenticar a cadeia); `docs/uso_de_ia.md`; `deferred-work.md` só se surgir dívida real.
- [x] **T6 `./verify.sh`** (e `VERIFY_E2E=1`), saída real, e parar.

## 11. Dev Notes

### Arquivos prováveis
- Back-end: `backend/app/bids.py` (leituras + DTOs); `backend/tests/integration/test_bid_reads.py`
  (novo); `backend/tests/test_openapi.py`; `backend/tests/test_access_policy.py`; README.
  **Intocados:** `bid_rules.py`, `bid_integrity.py`, `lots.py`, `lot_time.py`, `money.py`, `wallet.py`,
  `errors.py`, `place_bid`, migrations.
- Front: `src/api/bids.ts` (+ teste), `src/bidFeedback.ts`, `src/bidPosition.ts`, `src/countdown.ts`
  (+ testes), `src/LotBidPanel.tsx`, `src/BidForm.tsx`, `src/BidHistory.tsx`, `src/Countdown.tsx`,
  `src/LotPage.tsx`, `src/App.tsx`, `src/lotTime.ts` (hora com segundos para o histórico),
  `src/App.css`, `e2e/support/mockApi.ts`, `e2e/lot-room.spec.ts` (novo) e specs existentes.
- Leia antes: `DESIGN.md` §9 e §14, `EXPERIENCE.md` §9–§12 e §16, `FRONTEND-WORKFLOW.md`, AD-6, AD-10,
  AD-20, `walletDeposit.ts`/`WalletPage.tsx` (padrão de envio), `2-5` P3.

### Armadilhas
- Não usar `Date.now()`/`new Date()` para a contagem. `asOf.ts` já usa `new Date()` só para escolher
  a forma do texto; a contagem usa `performance.now()` e valores do servidor.
- Não combinar `dateStyle`/`timeStyle` com `timeZoneName` em `Intl` (tela branca da 2.4).
- Não ler `Bid` a partir de `lots.py` (import circular); as leituras novas moram em `bids.py`.
- Não reutilizar `read_history` na rota pública: ela devolve `bidder_id` e hashes.
- Não confiar na ordem do ORM: `ORDER BY sequence DESC` explícito.
- Mock do Playwright: o mesmo `Page` não deve engolir `POST` duplo; contar `POST /bids`.
- `/api/lots/{lot_id}/bids` (GET) e `/api/lots/mine` não colidem; a ordem `mine` antes de `{lot_id}` segue testada.
- Lotes legados (`anchor_hmac` nulo) aparecem normalmente; o `POST` responde 409. A UI mostra a
  mensagem de integridade.

### Riscos
- **Estado mostrado não autenticado:** a leitura pública não verifica a cadeia; um banco
  adulterado seria exibido até a 5.1 e o `POST` seguir recusando com 409.
- **Dois pedidos (detalhe + `/bids`) com `as_of` diferentes:** mitigado pela fonte única do dinâmico (§7.1).
- **Âncora no `placed_at`:** erro de ≈ um RTT, corrigido pela releitura.

## 12. Decisões fechadas (26/10/2026)

Decidi D1 a D5 depois de ler a versão anterior desta story. Não há decisão aberta.

| ID | Decisão | Alternativa descartada | Motivo |
| --- | --- | --- | --- |
| **D1 — FECHADA** | A sala lê o estado vivo de um read model público novo, `GET /api/lots/{lot_id}/bids`. O `GET /api/lots/{lot_id}` da 2.5 **não muda**. Somente leitura: sem trava de lance, sem escrita; `GET` nunca liquida, assina, corrige ou repara. | Embutir no detalhe existente. | Quebraria contratos pinados da 2.5 (17 chaves, igual para todos os papéis, uma instrução), criaria import circular `lots`↔`bids` e acoplaria o detalhe estático ao histórico. O read model novo pode ser reaproveitado pela 4.1. |
| **D2 — FECHADA** | Até os **50 lances mais recentes**, mais recente primeiro, mais o `bid_count` **total**. Cada item: `sequence`, `bidder_alias`, `amount_cents`, `placed_at`. Sem paginação nem cursor. Não é o contrato da auditoria: a 5.1 entrega o histórico completo. | Todos os lances; paginação por cursor. | A sala é "recente e compacto" (EXPERIENCE §11); a lista completa é da 5.1; cursor seria endpoint que a 4.1 trocaria. |
| **D3 — FECHADA** | `GET /api/lots/{lot_id}/bids/mine`, política `BIDDER`, resposta mínima `bidder_alias`, contagem própria e `last_bid_cents` (`null` se nunca lançou), **sem `is_leading`**. A posição é derivada no front (§7.7) e funciona com o último lance fora da janela de 50. | `is_leading` no servidor; detalhe `OPTIONAL` com bloco do usuário. | O líder já é público (`bids[0]`); `is_leading` repetiria um dado e viria de outro snapshot; o detalhe `OPTIONAL` mistura público e privado e quebra "igual para todos os papéis". |
| **D4 — FECHADA** | O navegador valida só formato e entrada. Mínimo e saldo são exibidos, mas **não impedem o `POST`**; o servidor decide as cinco recusas. | Pré-bloquear com o mínimo/saldo do último snapshot. | O snapshot pode estar velho, o saldo muda em outra aba, o servidor é a autoridade, e os códigos da 3.2 continuam demonstráveis pela interface. |
| **D5 — FECHADA** | Em `0:00`, **uma** releitura (por valor de `ends_at`), sem polling nem loop, mais o botão "Atualizar sala". O servidor decide o encerramento; `ends_at` posterior recalcula a contagem. O envio não é bloqueado por `0:00`. | Só botão manual; nada. | A releitura é disparada por tempo vindo do servidor e quem reclassifica é o servidor; só o botão deixaria a promessa da contagem sem resposta, e nada deixaria a sala presa. |

### Decisões complementares (também fechadas)

- **Após 201:** aplica `current_bid_cents`, `ends_at`, `wallet` e o aviso de aceite, e relê a sala
  (`/bids`, `/bids/mine`) para histórico, mínimo, contagem total e posição (§7.3).
- **Erro ambíguo do `POST`:** padrão da carteira (3.1): não afirma sucesso nem falha, não reenvia, uma
  releitura segura, texto que não induz a repetir às cegas, sem `Idempotency-Key` (§7.5).
- **401 na sala:** o login volta a `/lots/{lot_id}` pelo `returnTo`/`history` existente, sem open redirect (AC13).
- **Atalho "Usar o mínimo", visitante com "Entrar", leiloeiro sem ação, formato do cronômetro:** vêm
  de `EXPERIENCE.md` §9 e do protótipo aprovado.
- **Contrato exato:** os nomes finais dos schemas (inclusive `my_bid_count`) são fechados na
  `/bmad-spec` contra o código real.

### Classificação das questões do pedido original

| Q | Situação | Onde |
| --- | --- | --- |
| Q1 histórico | **FECHADA** (D1, D2) | §6.2 |
| Q2 pseudônimo | **FECHADA** (D3) | §6.2 |
| Q3 mínimo | **FECHADA**: `minimum_next_bid_cents` vem do servidor, via `minimum_bid_cents` (3.2) | §6.2 |
| Q4 contagem | **FECHADA**: `as_of`/`ends_at` + relógio monotônico; `0:00` por D5 | §7.2, AC7a |
| Q5 após 201 | **FECHADA**: aplicar a resposta e reler | §7.3 |
| Q6 ganhando/superado | **FECHADA** (D3) | §7.7 |
| Q7 erro ambíguo | **FECHADA**: padrão da 3.1 | §7.5 |
| Q8 outras mudanças no back-end | **FECHADA**: nenhuma além dos dois `GET`; o retorno ao lote em 401 é mudança de front (`App.tsx`) | §3.3 |

## 13. Referências
- `CLAUDE.md`; `docs/ARQUITETURA.md` AD-3, AD-5, AD-6, AD-10, AD-19, AD-20, AD-26.
- `epics.md` Story 3.5 (e 4.1 para a posição); `DESIGN.md` §9, §14; `EXPERIENCE.md` §9–§12, §16.
- `docs/FRONTEND-WORKFLOW.md`; `ux-designs/casa-de-leiloes/PROTOTIPO.md` (referência, não vinculante).
- `3-4-...md` §12 P6–P7; `2-5-...md` P2, P3; `deferred-work.md` (SR-08 C, F-6, Idempotency).

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5.5 (`claude-sonnet-5-5`), via `/bmad-build`.

### Debug Log References

- Build inicial: `./verify.sh` com `VERIFY_E2E=1`: todas as etapas passaram (pytest 1987 passed; `node --test`
  145 pass; Playwright 156 passed; build do Vite e `docker build` ok).
- Após as correções do primeiro review: `VERIFY_E2E=1 ./verify.sh`, exit 0;
  pytest 1987 passed; npm test 147 passed; Playwright 168 passed; Ruff/format,
  ESLint, tsc, Vite build e docker build OK. Esta é a última verificação completa
  informada; o re-review posterior executou apenas teste focado e não alterou código.

### Completion Notes List

- Backend: `PublicBidRoomResponse`, `MyLotBidsResponse` e as duas rotas GET em `bids.py`;
  16 testes novos em `test_bid_reads.py`; `test_openapi.py` e `test_access_policy.py`
  ajustados; uma linha obsoleta (405 em GET) removida de `test_bid_routes.py`.
- Frontend: `api/bids.ts`, `bidFeedback.ts`, `bidPosition.ts`, `countdown.ts`,
  `bidSubmission.ts` (+ testes), `LotBidPanel`, `BidForm`, `BidHistory`, `CountdownTimer`,
  `LotPage` reescrita, `App.tsx` (viewer, owner e retorno ao lote em 401), `money.ts`
  (`centsToInputText`), `lotTime.ts` (`formatClock`), `App.css`.
- Playwright: `lot-room.spec.ts` novo, `mockApi.ts` estendido; `session.spec.ts` e
  `vitrine.spec.ts` ajustados onde a intenção mudou.
- `Countdown.tsx` foi renomeado `CountdownTimer.tsx` por colisão de caixa com `countdown.ts`.

### File List

Ver o relatório final da sessão.

### Review independente e fechamento (26/10/2026)

- Build concluído com Claude Sonnet 5.5.
- O primeiro code review independente, com GPT-6.1 Sol Medium, encontrou **6 MEDIUM
  (F-01 a F-06) e 1 LOW opcional (F-07)**. A aprovação final não apaga esses findings.
- F-01, F-02, F-03, F-04, F-05 e F-06 foram corrigidos; F-07 recebeu cobertura
  adicional, considerada suficiente no re-review. A verificação completa após as
  correções passou, conforme o registro acima.
- O re-review independente e focado, com GPT-6.1 Sol Medium, confirmou todos os
  findings corrigidos/atendidos e não encontrou regressão concreta.
- `LotPage.tsx`: **COMPLEXA MAS ACEITÁVEL**. Nenhuma dívida genérica de refatoração
  foi criada; nenhum item concreto adicional da 3.5 exigiu registro em deferred-work.
- Recomendação final: **APROVADA PARA DONE**. Story 3.5 encerrada como `done`;
  Epic 3 permanece `in-progress` e Story 3.6 permanece `backlog`.
- Este fechamento alterou somente documentação/status, com checagem de consistência;
  não repetiu testes, não alterou código/testes, não executou Git e não acessou `.env*`.
