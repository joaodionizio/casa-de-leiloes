# Story 3.2 — Regras de aceitação do lance com hora injetada

Status: done

Chave do sprint: `3-2-regras-de-aceitação-do-lance-com-hora-injetada`
Épico: 3 (Carteira e lances íntegros). Data de criação: 25/10/2026.

> **Nota de revisão da decisão (27/10/2026).** A AD-5 foi revisada por mim em
> 27/10/2026: a regra passou a ser `novo fim = now + 2 min` (renovação a partir do lance;
> com exatamente 2 min restantes não há mudança). Este documento registra o que eu decidi
> e implementei em 25/10/2026 (Story 3.2) com a regra anterior (`ends_at + 2 min`); **não o reescrevi**. A
> regra vigente está em `docs/ARQUITETURA.md`, AD-5.

> **Leitura desta story (25/10/2026).** Decidi P1 a P13 em 25/10/2026, antes de
> qualquer spec ou código. As decisões vigentes estão em **"Decisões fechadas (P1 a
> P13)"**, e as regras, os critérios, a matriz de testes e as tarefas abaixo já as
> refletem. A seção "Questões abertas" fica como registro histórico de antes da decisão;
> onde a minha decisão diverge da recomendação de lá, vale "Decisões fechadas":
> **P3** (fiquei com a ordem do AD-7, opção A, e não com a B recomendada), **P5**
> (`ends_at` efetivo sempre presente + `anti_sniping_applied`, e não `new_ends_at: None`),
> **P8** (`lot_phase` também passa a recusar `starts_at`/`ends_at` sem fuso e `starts_at
> >= ends_at`) e **P13** (o `ARQUITETURA.md` não muda). O ponto derivado **C1** também
> está decidido (opção b): o saldo disponível saiu de `BidAttempt` e a P1 foi ajustada
> para `evaluate_bid(lot, attempt, available_balance_cents, now)`. Não resta decisão
> bloqueante para a spec.

*(Estado de quando consolidei as decisões: `ready-for-dev`, sem spec, sem `bmad-spec`, sem
`bmad-build`, sem código, sem git.)*

## 1. Story e objetivo

Como licitante,
quero que meu lance seja avaliado por regras claras e sempre iguais,
para que eu saiba exatamente por que ele foi aceito ou recusado.

Nesta story entrego **só a regra de domínio pura** da aceitação de um lance: dado o
estado do lote, a tentativa de lance, o saldo disponível do licitante (recebido à parte,
porque é estado da carteira e não da tentativa) e um `now` recebido por parâmetro, ela
devolve **aceito** (com o `ends_at` efetivo e a indicação do
anti-sniping) ou **um** dos cinco motivos de recusa, de forma determinística e com uma
precedência fixada por contrato. Sem banco, sem HTTP, sem transação, sem relógio próprio,
sem alterar nada. Testada por uma matriz de testes unitários com `now` fixo.

Entrego também a extração da semântica temporal do lote (`LotPhase`, `lot_phase`) para um
módulo puro, `app/lot_time.py`, com a defesa de fuso e de horários completa (P8).

A 3.4 vai chamar a regra dentro da transação (lote travado, `clock_timestamp()` lido
depois da trava; a etapa sem carteira antes de travar carteiras; a avaliação completa
depois) e aplicar o resultado. A 3.5 vai traduzir o código de recusa em contrato HTTP e
mensagem.

## 2. Fontes usadas

`CLAUDE.md`; `docs/ARQUITETURA.md` (AD-3, AD-5, AD-6, AD-7, AD-8, AD-17, AD-19, AD-26,
AD-27, AD-30; questões 5 e 9); `docs/desafio-elite-dev.md` ("Regras de lance", "Saldo
comprometido", "Prorrogação (anti-sniping)", "Mensagens de feedback"); `README.md`
("Lotes", "Carteira", "Comportamentos que podem surpreender"); `docs/uso_de_ia.md`
(seções 2.5 e 3.1); `_bmad-output/planning-artifacts/epics.md` (Épico 3, Stories 3.2 a
3.6, FR10 a FR13); `sprint-status.yaml`; `deferred-work.md`; `DESIGN.md` (estados
"✓ Você está ganhando"/"↑ Você foi superado", "próximo mínimo"); `EXPERIENCE.md` (§9
Sala do lote, §10 Encerrado, apurando); a Story 3.1 inteira e a spec
`spec-story-3-1-carteira-deposito/` (`SPEC.md`, `decisions.md` D1 e D4); as Stories 2.4
e 2.5 (fase temporal, `resolve_schedule`, `lot_phase`); o código real de
`backend/app/lots.py`, `backend/app/money.py`, `backend/app/wallet.py`,
`backend/app/errors.py` e os testes `tests/test_lot_phase.py`, `tests/test_lot_rules.py`,
`tests/test_wallet_rules.py` e `tests/test_openapi.py`.

O skill `bmad-create-story` **não está instalado** (a pasta `_bmad/bmm/v6-shims/` só tem
o README que o lista como "retained in full"), como nas Stories 2.2, 2.4 e 3.1. Segui a
estrutura da 3.1 e as seções pedidas na instrução da sessão.

ADs: o `epics.md` declara AD-5 e AD-26 para a 3.2 e a dependência da questão 5. Também
considero AD-3 (dinheiro em centavos e teto), AD-6 (o navegador nunca decide; a hora vem
de fora da regra), AD-7 (ordem das validações e precedência, P3), AD-8 (só para não
atrapalhar a 3.4, P11), AD-17/AD-27 (testes e `verify`) e AD-30 (código em inglês,
mensagens em português). **Nenhuma AD é alterada por esta story.**

## 3. Estado real herdado (conferido nos arquivos, sem git)

**Sprint.** `epic-3: in-progress`; `3-1-carteira-e-depósito-simulado: done`; 3.3 a 3.6
`backlog`. A 3.1 está `done`, com code review e re-review aprovados.

**Dinheiro (`app/money.py`, 3.1 P3).** `MAX_CENTS = 9_007_199_254_740_991` (`2**53 - 1`)
e `Cents = Annotated[StrictInt, Field(gt=0, le=MAX_CENTS)]`. O módulo não importa nenhum
outro módulo do app (`test_money_imports_no_other_app_module`). `lots.py` e `wallet.py`
importam dele e não redefinem nada (teste AST). Existe um teste AST que proíbe `float`,
constante `float` e divisão (`ast.Div`) em `money.py` e `wallet.py`. `money.py` importa
`pydantic` (por causa de `Cents`); a regra de lance usa só `MAX_CENTS`.

**Carteira (`app/wallet.py`, 3.1).** Regra pura: `available_cents(total, committed) ->
int` e `apply_deposit(total, amount) -> int | DepositRefusal`, com defesa em profundidade
(F-09: `ValueError` para valor que não é `Cents`). Recusa de negócio como `StrEnum`
(`DepositRefusal`). `committed_balance_cents` existe e **vale sempre 0** (a 3.4 o altera).
O disponível nunca é persistido. `wallet.py` importa FastAPI e SQLAlchemy, e um teste o
proíbe de importar `app.lots`.

**Lotes e fase (`app/lots.py`, 2.4 e 2.5).** Seção "regra pura (AD-26)" com
`ScheduleViolation`, `Schedule` (`@dataclass(frozen=True)`), `resolve_schedule`,
`LotPhase` (`scheduled`/`live`/`ended`) e `lot_phase(starts_at, ends_at, now)`, que **só
valida o `now`**: com `starts_at`/`ends_at` sem fuso, a comparação dá `TypeError`
("can't compare offset-naive and offset-aware datetimes", conferido com Python), e com
`starts_at >= ends_at` devolve uma fase sem reclamar. `lots.py` importa FastAPI,
Pydantic, SQLAlchemy, `app.artic` e `app.catalog`. **Usos reais de `lot_phase`/`LotPhase`
(conferidos por busca):** só `public_lot_summary` e `build_public_lots` em `lots.py`,
sempre com lotes lidos do banco (`timestamptz` com fuso; CHECK `ends_after_starts`), o
campo `phase: LotPhase` de `PublicLotSummary` e `tests/test_openapi.py`, que fixa o
schema `LotPhase` com `["scheduled", "live", "ended"]`.

**Termos do lote (2.4).** `starting_bid_cents` e `min_increment_cents` em `1..MAX_CENTS`
na API, no modelo e na CHECK; `ends_at > starts_at` na CHECK. Nada impede
`min_increment_cents = MAX_CENTS`. Não existe edição de termos, `current_bid`, líder,
tabela `bids` nem `cancelled_at`.

**Erros (`app/errors.py`).** Catálogo `MESSAGES` fixado por igualdade exata em
`test_errors.py`. Nenhum código de lance existe, e esta story não acrescenta nenhum (P2).

**Front-end.** Nada de lance. Esta story não toca `frontend/`.

## 4. Escopo

1. `app/lot_time.py`: `LotPhase` e `lot_phase` movidos de `lots.py`, sem mudar a
   semântica, com a defesa completa (P8); `lots.py` reexporta os dois nomes.
2. `app/bid_rules.py` (P9), só domínio puro:
   - `BidRefusal` (`StrEnum`) com os cinco códigos (P2);
   - dataclasses congeladas `CurrentBid`, `LotBidState`, `BidAttempt`, `BidAccepted`
     (P1, P4, P5), cada uma validando as próprias invariantes na construção (P7, P10);
   - a função pura do mínimo exigido, `int | None` (P5, P6);
   - a etapa pura sem carteira, conceitualmente `(lot, attempt, now)`, que executa
     exatamente período → mínimo → líder e não recebe nem conhece saldo (P11, C1);
   - `evaluate_bid(lot, attempt, available_balance_cents, now) -> BidAccepted |
     BidRefusal`, que **reutiliza** a etapa sem carteira, só depois verifica o saldo e
     só então decide o anti-sniping (P3, P11, C1, AD-5).
3. Testes unitários puros (seção 16).
4. Documentação: esta story, `sprint-status.yaml`, `docs/uso_de_ia.md`.

## 5. Fora do escopo

Não implemento nesta story (e não antecipo):

- migration; tabela `bids`; colunas de lance atual, líder, sequência ou âncora em `lots`;
  qualquer acesso a banco;
- `POST /api/lots/{lot_id}/bids` ou qualquer rota; erros HTTP; entradas em
  `errors.py`/`MESSAGES` (P2);
- rota, tela, formulário, botão "Dar lance" ou mensagem no front;
- alteração de `total_balance_cents` ou `committed_balance_cents`; liberação do saldo do
  líder anterior;
- `SELECT ... FOR UPDATE`, ordem de travas, `clock_timestamp()` no fluxo transacional;
- persistência do `ends_at` efetivo; evento de anti-sniping;
- pseudônimo, HMAC, SHA-256, `previous_hash`, canônico, sequência, histórico (3.3, 3.4);
- WebSocket (4.1), fechamento e liquidação (4.3, 4.4), catch-up em tentativa de lance
  (questão 9, 4.4);
- cancelamento: sem sexto motivo, sem `status=cancelled`, sem campo de cancelamento na
  regra (P12, 3.6);
- teto de extensões do anti-sniping (AD-5: sem teto);
- verificação de papel (`AUCTIONEER` não dá lance): política de acesso da rota na 3.4
  (AD-11), não regra de domínio;
- qualquer mudança em `docs/ARQUITETURA.md` ou `CLAUDE.md` (P13; divergência 4).

Fronteiras: **3.3** = pseudônimo, canônico, SHA, HMAC. **3.4** = transação real (trava do
lote, hora do PostgreSQL depois da trava, etapa sem carteira, travas de carteira, saldo,
comprometido, líder anterior/novo, persistir lance e `ends_at`, integridade, commit,
concorrência e margens do caminho real). **3.5** = endpoint/experiência de dar lance,
contrato HTTP e mensagem. **3.6** = cancelamento.

## 6. Regras de domínio e fluxo da avaliação

Fluxo conceitual decidido (P1, P3, P10, P11, C1):

1. As invariantes estruturais são validadas **na construção** de `CurrentBid`,
   `LotBidState` e `BidAttempt` (P7, P10). Objeto construído = objeto válido.
   `BidAttempt` representa só a tentativa: `bidder_id` e `amount_cents`.
2. `now` é recebido explicitamente (sem fuso → `ValueError`); `available_balance_cents`
   é recebido à parte, só pela avaliação completa (fora de `0..MAX_CENTS`, `bool` ou
   não `int` → `ValueError`).
3. Período, pela semântica única de `lot_phase` (P8):
   - `now < starts_at` → `lot_not_started`;
   - `now >= ends_at` → `lot_ended` (nunca reabre).
4. Calcula o mínimo exigido pela função única (P5, P6).
5. `amount_cents` abaixo do mínimo, ou mínimo irrepresentável (`None`) → `below_minimum`.
6. `attempt.bidder_id == lot.current.leader_id` → `already_winning`.
7. `amount_cents > available_balance_cents` → `insufficient_balance`.
8. O lance é aceito.
9. **Só então** decide o anti-sniping: se `0 < ends_at - now <= 2 min`, o `ends_at`
   efetivo é `lot.ends_at + 2 min`; senão, é `lot.ends_at`.
10. Devolve `BidAccepted(ends_at=<efetivo>, anti_sniping_applied=<bool>)`.

Os passos 3 a 6 formam a **etapa sem carteira** (P11, C1): recebe `(lot, attempt, now)`,
uma única implementação, pública, que não recebe nem conhece saldo. A avaliação completa
`evaluate_bid(lot, attempt, available_balance_cents, now)` reutiliza essa mesma
implementação; se ela recusar, devolve a recusa; só depois valida o saldo (passo 7); se
insuficiente, `insufficient_balance`; se aceito, decide o anti-sniping (passos 9 e 10).
Não existe uma segunda cópia das três regras sem carteira. O anti-sniping nunca roda para
lance recusado.

**Composição sem dupla execução (para a spec).** A 3.4 chama a etapa sem carteira antes
de travar carteiras e, depois das travas, precisa da decisão de saldo e do anti-sniping.
A spec define a composição de modo que esse caminho **não execute duas vezes** as mesmas
validações sem necessidade, por exemplo com um resultado intermediário (a etapa sem
carteira devolve `BidRefusal` ou um "elegível" que a etapa de saldo consome), e
`evaluate_bid` é a composição das duas para quem já tem tudo. Limites que a spec
respeita: as três regras sem carteira existem num só lugar; o intermediário, se existir,
não acrescenta dado novo nem campo "porque pode ser útil", não infla a API pública do
domínio e não permite chegar à decisão de saldo sem ter passado pela etapa sem carteira;
`evaluate_bid` dá sempre o mesmo resultado que a composição.

| # | Regra | Falha → código |
| --- | --- | --- |
| R1 | `now < starts_at` | `lot_not_started` |
| R2 | `now >= ends_at` | `lot_ended` |
| R3 | Sem lance atual: `amount_cents >= starting_bid_cents` | `below_minimum` |
| R4 | Com lance atual: `amount_cents >= current.amount_cents + min_increment_cents`, e esse mínimo `<= MAX_CENTS` | `below_minimum` |
| R5 | Com lance atual: `bidder_id != current.leader_id` | `already_winning` |
| R6 | `amount_cents <= available_balance_cents` | `insufficient_balance` |
| R7 | Só se aceito: `0 < ends_at - now <= 2 min` → `ends_at + 2 min` | — (não recusa) |

- R6 compara com o **disponível** da 3.1 (`total - committed`), recebido pronto como
  parâmetro próprio de `evaluate_bid` (C1), nunca dentro de `BidAttempt`: é estado
  autoritativo da carteira, e na 3.4 só é confiável depois das travas; a 3.4 o calcula
  com `wallet.available_cents` a partir da carteira travada. Como o líder é recusado em R5, quem chega a R6 não tem saldo comprometido
  **neste** lote: não existe "completar a diferença" do próprio lance.
- A regra não muda nada: devolve uma decisão.

## 7. Limites temporais

- **Fase (P8, sem mudança de semântica).** `now < starts_at` → `scheduled`; `starts_at <=
  now < ends_at` → `live`; `now >= ends_at` → `ended`. Exatamente `starts_at` **aceita**;
  exatamente `ends_at` **recusa** (`lot_ended`).
- **Defesa de `lot_phase` (P8).** `ValueError` se `starts_at`, `ends_at` ou `now` não
  tiverem fuso, e se `starts_at >= ends_at`. Hoje `lot_phase` só valida o `now`. Os
  chamadores reais (vitrine e página do lote) passam lotes do banco, sempre com fuso e
  com `ends_at > starts_at` garantido pela CHECK: nenhum caminho válido muda.
- **Precisão.** Microssegundo, comum ao `datetime` do Python e ao
  `timestamptz`/`clock_timestamp()` do PostgreSQL. Nenhum arredondamento.
- **Fuso.** A comparação é entre instantes; o offset de cada argumento não importa. O
  `ends_at` de `BidAccepted` sai em UTC, como `resolve_schedule` e os DTOs.
- **Sem relógio.** Nenhum dos dois módulos chama `datetime.now`, `datetime.utcnow`,
  `date.today`, `time.time`, `time.monotonic` nem consulta o banco.
- **Lance atual com lote agendado (confirmado em 25/10/2026).** `LotBidState` com
  `current` e `now < starts_at` **não** é `ValueError`: a fase depende do `now`, e a
  presença de um lance atual não basta, nesta regra pura, para provar corrupção
  histórica. Resultado: `lot_not_started`, como manda a P3. Não invento uma invariante
  temporal persistente que esta story não tem dados para comprovar.
- **Questão 5 (P13).** Esta story concretiza a parte pura com `now` injetado; a 3.4 faz
  o caminho real (trava do lote, `clock_timestamp()` depois da trava, integração com
  margens).

## 8. Limites monetários

- Todo valor é `int` estrito em centavos (`bool` recusado), nunca `float`, fração ou
  divisão. Fonte única do teto: `app.money.MAX_CENTS`, sem segunda constante.
- **Faixas (fora delas → `ValueError`, P7):** `starting_bid_cents` e
  `min_increment_cents` em `1..MAX_CENTS`; `CurrentBid.amount_cents` em `1..MAX_CENTS` e
  `>= starting_bid_cents` (validado em `LotBidState`, que conhece os dois);
  `BidAttempt.amount_cents` em `1..MAX_CENTS`; o parâmetro `available_balance_cents` de
  `evaluate_bid` em `0..MAX_CENTS` (validado na entrada da avaliação completa, C1).
- **`current + increment`.** Em Python a soma de dois inteiros em `1..MAX_CENTS` vai no
  máximo a `2**54 - 2`, um `int` exato: não há overflow (no `BIGINT` da 3.4 também cabe,
  `2**54 < 2**63 - 1`). O problema é a **representabilidade**: se a soma passa de
  `MAX_CENTS`, nenhum lance válido atinge o mínimo. É alcançável com dados válidos (lote
  com `starting_bid_cents = 1` e `min_increment_cents = MAX_CENTS`, depois do primeiro
  lance).
- **Função do mínimo (P5, P6).** Devolve `int | None`: sem lance atual,
  `starting_bid_cents`; com lance atual, `current + increment` se `<= MAX_CENTS`; senão
  `None` ("nenhum mínimo representável"). **Nunca** clamp, wrap, `float` ou inteiro acima
  de `MAX_CENTS`.
- **Avaliação com `None`.** `below_minimum`, porque nenhum `amount_cents` válido alcança o
  mínimo real.
- **Saldo exato.** `available == amount` é aceito; `available == amount - 1` recusa.

## 9. Motivos de recusa (P2)

`BidRefusal` (`StrEnum`) de domínio, com exatamente estes cinco valores. **Não** entram
em `errors.py`/`MESSAGES` nesta story: a tradução para contrato HTTP e a mensagem
efetivamente enviada pela API nascem quando o endpoint for integrado (3.4/3.5).

| Código | Significado | Redação portuguesa esperada (referência, não contrato HTTP) |
| --- | --- | --- |
| `lot_not_started` | `now < starts_at` | "Este lote ainda não começou." |
| `lot_ended` | `now >= ends_at` | "Este lote já foi encerrado." |
| `below_minimum` | valor abaixo do lance inicial (sem lance) ou de atual + incremento, ou mínimo irrepresentável | "Seu lance está abaixo do mínimo para este lote." |
| `already_winning` | quem lidera tentou cobrir o próprio lance | "Você já está ganhando este lote." |
| `insufficient_balance` | valor acima do saldo disponível | "Saldo disponível insuficiente para este lance." |

Os códigos não colidem com nenhuma chave atual de `MESSAGES` (verificado por teste, sem
alterar o catálogo) e nunca expõem dado de outro licitante (`already_winning` só existe
para o próprio líder).

## 10. Precedência das recusas (P3, contrato de domínio)

Ordem fixa, a do AD-7: **período → mínimo → líder → saldo**.

1. `lot_not_started` / `lot_ended` (mutuamente exclusivos, pois `starts_at < ends_at`);
2. `below_minimum`;
3. `already_winning`;
4. `insufficient_balance`.

Consequência explícita: se o licitante já lidera **e** o valor está abaixo do mínimo, a
resposta é `below_minimum`. Não altero o AD-7.

Combinações obrigatórias, cada uma um teste nomeado (além da tabela completa da seção
16):

| Combinação | Resultado |
| --- | --- |
| não iniciado + abaixo do mínimo | `lot_not_started` |
| encerrado + abaixo do mínimo | `lot_ended` |
| encerrado + líder atual | `lot_ended` |
| abaixo do mínimo + líder atual | `below_minimum` |
| abaixo do mínimo + saldo insuficiente | `below_minimum` |
| líder atual + saldo insuficiente | `already_winning` |
| só saldo insuficiente | `insufficient_balance` |
| encerrado + líder + abaixo do mínimo + saldo insuficiente (exemplo da sessão) | `lot_ended` |

A precedência é contrato: a tabela do teste é escrita à mão, nunca derivada de uma
constante ou da ordem do código, e uma mutação que troque a ordem de duas verificações
precisa quebrar algum desses testes.

## 11. Anti-sniping (AD-5)

- Só para lance **aceito**; nenhuma recusa estende.
- Janela inclusiva: `0 < lot.ends_at - now <= 2 min`. O aceite já exige `now <
  ends_at`, então o restante é sempre `> 0`; a condição fica explícita no código, como no
  AD-5.
- Com extensão: `BidAccepted(ends_at=lot.ends_at + 2 min, anti_sniping_applied=True)`.
- Sem extensão: `BidAccepted(ends_at=lot.ends_at, anti_sniping_applied=False)`.
- Sempre `lot.ends_at + 2 min`, **nunca** `now + 2 min`; cumulativo (a próxima avaliação
  recebe o `ends_at` já estendido, que a 3.4 persiste); sem teto.
- O `ends_at` efetivo está **sempre** presente (P5): a 3.4 o grava e usa o indicador para
  publicar o novo horário (4.1), sem recalcular nada.
- Exatamente `ends_at`: `lot_ended`, sem extensão. Depois do fim: nunca reabre.
- Constantes (nomes finais na spec): janela e extensão como dois nomes, ambos
  `timedelta(minutes=2)`, porque o AD-5 descreve dois conceitos.

## 12. Hora injetada (AD-6, AD-26)

- `now` é parâmetro explícito e obrigatório de `evaluate_bid`, da etapa sem carteira e
  de `lot_phase`; nunca opcional, nunca com default.
- Um teste AST garante que `app/bid_rules.py` e `app/lot_time.py` não chamam relógio nem
  importam `time`; um teste comportamental prova que o resultado segue o `now` injetado
  (o mesmo estado com `now` em 2000 e em 2100 dá resultados diferentes e coerentes com
  cada `now`, seja qual for a data em que o teste roda).
- O navegador nunca decide; esta story não cria regra no front.

## 13. Relação com a 3.1

- `MAX_CENTS` vem de `app.money` (identidade testada), nunca redefinido.
- O saldo comparado é o disponível da 3.1, recebido pronto; a regra não importa
  `app.wallet` (que importa FastAPI e SQLAlchemy).
- Mesmo estilo: recusa de negócio como `StrEnum`; erro de programação como `ValueError`
  (F-09); nenhum `float` nem divisão (teste AST estendido aos módulos novos).
- `committed_balance_cents` continua 0.

## 14. Preparação para a 3.4 (sem implementá-la)

| A 3.4 precisa | O que esta story entrega |
| --- | --- |
| Montar a entrada sem a regra conhecer o ORM | dataclasses de domínio (P1); o adaptador `Lot`/carteira → dataclasses é da 3.4 |
| Representar "sem lance" sem estado impossível | `current: CurrentBid | None` (P4); a 3.4 traduz as colunas e falha se vierem incoerentes |
| Seguir o AD-7: período, mínimo e líder **antes** de travar carteiras | etapa pura sem carteira `(lot, attempt, now)` (P11, C1), a mesma que `evaluate_bid` reutiliza; `BidAttempt` já pode ser montado antes das travas, porque não tem saldo |
| Decidir saldo depois de travar carteiras | o disponível da carteira travada como parâmetro próprio (C1), na composição sem dupla execução definida pela spec, ou em `evaluate_bid(lot, attempt, available_balance_cents, now)` |
| Aplicar o anti-sniping sem recalcular | `BidAccepted.ends_at` efetivo + `anti_sniping_applied` (P5) |
| Responder o motivo exato | `BidRefusal` (P2), traduzido em HTTP na 3.4/3.5 |
| Mostrar o mínimo do próximo lance (3.5) | função única `int | None` (P5, P6) |
| `now` | parâmetro; a 3.4 lê um único `clock_timestamp()` depois da trava do lote |

Fluxo previsto na 3.4 (descrição, não implementação): travar o lote → ler um único
`clock_timestamp()` → montar `LotBidState` e `BidAttempt` → etapa sem carteira; se
recusar, parar antes de travar carteiras → senão, identificar e travar as carteiras em
`user_id` crescente (AD-8) → calcular o disponível confirmado da carteira travada →
decisão de saldo e anti-sniping, reutilizando o resultado da etapa sem carteira (sem
repetir as validações, conforme a composição da spec) → continuar a transação.

## 15. Critérios de aceite

Todos verificáveis por teste unitário puro; nenhum depende de banco ou HTTP.

1. **CA1 — Decisão única.** Para objetos de domínio válidos, saldo em `0..MAX_CENTS` e
   `now` com fuso, `evaluate_bid(lot, attempt, available_balance_cents, now)` devolve ou `BidAccepted` ou exatamente um dos cinco `BidRefusal`. Mesma
   entrada → mesmo resultado; as entradas não são alteradas (dataclasses congeladas).
2. **CA2 — Período.** `starts_at - 1µs` → `lot_not_started`; `starts_at` → não recusa por
   período; meio → não recusa por período; `ends_at - 1µs` → não recusa por período;
   `ends_at` e depois → `lot_ended`. Em toda uma grade de `now`, a recusa por período
   coincide com `lot_phase` (`SCHEDULED` ↔ `lot_not_started`, `ENDED` ↔ `lot_ended`).
3. **CA3 — Primeiro lance.** Sem lance atual: `starting - 1` → `below_minimum`;
   `starting` e `starting + 1` → aceito.
4. **CA4 — Lance seguinte.** Lance atual `c`, incremento `i`: `c + i - 1`, `c` e abaixo de
   `c` → `below_minimum`; `c + i` e `c + i + 1` → aceito.
5. **CA5 — Líder.** O líder, com valor `>=` mínimo e saldo suficiente →
   `already_winning`; outro licitante com exatamente a mesma entrada → aceito.
6. **CA6 — Saldo.** `available = amount - 1` → `insufficient_balance`; `available =
   amount` e `amount + 1` → aceito; `available = 0` → `insufficient_balance`.
7. **CA7 — Precedência (P3).** As oito combinações da seção 10 devolvem exatamente o
   código indicado, cada uma num teste nomeado, além da tabela completa escrita à mão
   (seção 16).
8. **CA8 — Anti-sniping.** Para lance aceito: restante `2 min + 1µs` e 1 h →
   `ends_at == lot.ends_at` e `anti_sniping_applied is False`; exatamente `2 min`, `2 min
   - 1µs` e `1µs` → `ends_at == lot.ends_at + 2 min` e `anti_sniping_applied is True`; o
   `ends_at` estendido difere de `now + 2 min` num caso construído para os dois
   diferirem; duas avaliações em sequência (a segunda com o fim já estendido) somam 4
   minutos ao fim original; o `ends_at` sai em UTC mesmo com entradas em outro offset.
   `now == ends_at` → `lot_ended`. Cada recusa (`below_minimum`, `already_winning`,
   `insufficient_balance`) dentro da janela → recusa, nenhum `BidAccepted`.
9. **CA9 — `MAX_CENTS` (P6).** `amount = MAX_CENTS` aceito quando mínimo e saldo
   permitem; `c + i == MAX_CENTS` → mínimo `MAX_CENTS`, `MAX_CENTS` aceito e `MAX_CENTS -
   1` recusado; `c + i == MAX_CENTS + 1` e `c = i = MAX_CENTS` → função do mínimo devolve
   `None` e toda tentativa válida (inclusive `MAX_CENTS`) dá `below_minimum`, sem
   exceção; sem lance atual com `starting = MAX_CENTS` → mínimo `MAX_CENTS`. A função do
   mínimo nunca devolve valor acima de `MAX_CENTS`.
10. **CA10 — Hora injetada.** Nenhuma leitura de relógio nos dois módulos (AST); o
    resultado segue o `now` injetado (2000 × 2100); `now` sem fuso → `ValueError` em
    `evaluate_bid`, na etapa sem carteira e em `lot_phase`.
11. **CA11 — Invariantes (P7, P10).** Cada caso da tabela da P7 levanta `ValueError` na
    construção do objeto correspondente (ou na entrada da função pública, para os
    argumentos soltos: `now` nas duas etapas e `available_balance_cents` na avaliação
    completa) e **nunca** vira recusa de negócio. `BidAttempt` não tem campo de saldo
    (C1). `LotBidState` com `current` e `now < starts_at` **não** levanta: devolve
    `lot_not_started`.
12. **CA12 — `lot_time` (P8).** `app.lots.LotPhase is app.lot_time.LotPhase` e
    `app.lots.lot_phase is app.lot_time.lot_phase`; `lot_phase` recusa com `ValueError`
    `starts_at`, `ends_at` ou `now` sem fuso e `starts_at >= ends_at` (inclusive igual);
    a semântica das três fases é a mesma; `tests/test_lot_phase.py` passa sem mudar
    nenhuma asserção existente; o schema `LotPhase` do OpenAPI continua
    `["scheduled", "live", "ended"]`.
13. **CA13 — Pureza (P9).** `app/bid_rules.py` importa só biblioteca padrão,
    `app.money` e `app.lot_time`; `app/lot_time.py` importa só biblioteca padrão. Nenhum
    dos dois importa `fastapi`, `sqlalchemy`, `pydantic`, `httpx`, `app.db`, `app.main`,
    `app.lots`, `app.wallet`, `app.catalog`, `app.artic`, `app.errors`; nenhum usa
    `float`, constante `float` ou divisão, nem redefine `MAX_CENTS`.
14. **CA14 — Etapa sem carteira e composição (P11, C1).** A etapa sem carteira recebe
    `(lot, attempt, now)`, sem nenhum parâmetro de saldo, e devolve, para toda linha da
    tabela de precedência, a mesma recusa que `evaluate_bid` quando a recusa não é
    `insufficient_balance`, e "elegível" (sem recusa) quando `evaluate_bid` aceita ou
    recusa por saldo. A composição definida pela spec (etapa sem carteira seguida da
    decisão de saldo, sem repetir validações) dá, em toda a tabela, exatamente o mesmo
    resultado que `evaluate_bid`. Não existe segunda implementação de período, mínimo ou
    líder.
15. **CA15 — Códigos (P2).** O conjunto de valores de `BidRefusal` é exatamente
    `{lot_not_started, lot_ended, below_minimum, already_winning, insufficient_balance}`;
    nenhum está em `MESSAGES`; `errors.py` e `test_errors.py` não mudam.
16. **CA16 — Regressões e verificação.** Toda a suíte segue verde sem afrouxar asserção;
    `./verify.sh` completo com a saída real registrada; nenhum número que não venha de
    comando executado. Story, `sprint-status.yaml` e `docs/uso_de_ia.md` atualizados na
    implementação; `ARQUITETURA.md`, `CLAUDE.md`, `README.md` e `errors.py` sem mudança.

## 16. Matriz de testes

Todos unitários e puros (`backend/tests/`, sem banco). Nomes e arquivos finais na spec.
Contagens só virão do `verify`.

| Grupo | Casos |
| --- | --- |
| `lot_time` (P8) | os casos atuais de `test_lot_phase.py` intactos; novos: `starts_at` sem fuso, `ends_at` sem fuso, `now` sem fuso, `starts_at == ends_at`, `starts_at > ends_at` → `ValueError`; identidade da reexportação; imports só da biblioteca padrão; schema `LotPhase` do OpenAPI inalterado |
| Período | `starts_at - 1µs`; `starts_at`; meio; `ends_at - 1µs`; `ends_at`; `ends_at + 1µs`; muito antes; muito depois; offsets diferentes no mesmo instante; equivalência com `lot_phase` numa grade de `now` |
| Primeiro lance | `starting - 1`, `starting`, `starting + 1`; `starting = 1` com `amount = 1`; `starting = MAX_CENTS` com `amount = MAX_CENTS` |
| Lance seguinte | `c + i - 1`, `c + i`, `c + i + 1`; `amount = c`; `amount < c`; `i = 1` |
| Líder | líder com valor e saldo suficientes → `already_winning`; outro licitante com a mesma entrada → aceito; sem lance atual, ninguém é líder |
| Saldo | `amount - 1`, `amount`, `amount + 1`; `available = 0`; `available = MAX_CENTS` |
| Precedência (P3) | as oito combinações nomeadas da seção 10; tabela completa escrita à mão: fase (agendado, ao vivo, encerrado) × lance atual (não, sim com outro líder, sim com o próprio licitante) × valor (`>=` mínimo, `<` mínimo) × saldo (suficiente, insuficiente), só combinações construíveis, com o resultado esperado digitado no teste |
| Anti-sniping | restante `2 min + 1µs` e 1 h sem extensão; exatamente `2 min`, `2 min - 1µs` e `1µs` com extensão; `now = starts_at` em lote de duração `<= 2 min` (aceito e estendido); `ends_at` → `lot_ended`; cada recusa dentro da janela sem `BidAccepted`; `ends_at` estendido `== lot.ends_at + 2 min` e `!= now + 2 min`; cumulativo em duas avaliações; saída em UTC; sem extensão → `ends_at == lot.ends_at` e `False` |
| Etapa sem carteira e composição (P11, C1) | assinatura `(lot, attempt, now)` sem saldo; equivalência com `evaluate_bid` em toda a tabela de precedência; composição (etapa sem carteira → decisão de saldo) igual a `evaluate_bid` em toda a tabela; cada regra sem carteira executada uma vez por caminho (forma da prova na spec); `now` sem fuso → `ValueError` nas duas |
| Hora injetada | AST: nenhum `now(`, `utcnow`, `today`, `time.time`, `monotonic`, `clock_timestamp`, nem import de `time`; `now` em 2000 e 2100 dirigem o resultado; mesmo estado com dois `now` → dois resultados determinísticos; `now` sem fuso → `ValueError` |
| `MAX_CENTS` (P6) | `amount = MAX_CENTS` aceito; `c + i == MAX_CENTS`; `c + i == MAX_CENTS + 1`; `c = i = MAX_CENTS`; lote `starting = 1`, `i = MAX_CENTS` depois do primeiro lance; função do mínimo nos mesmos casos (`int` ou `None`, nunca `> MAX_CENTS`) |
| Invariantes (P7, P10) | um teste por linha da tabela da P7, no objeto ou função onde a validação mora (`available_balance_cents` negativo, acima de `MAX_CENTS`, `bool` ou não `int` → `ValueError` em `evaluate_bid`); `BidAttempt` não aceita campo de saldo; lote agendado com `current` → `lot_not_started`, sem exceção; nenhum vira recusa |
| Pureza e contrato | AST de imports dos dois módulos; sem `float`/divisão; sem redefinir `MAX_CENTS`; `bid_rules.MAX_CENTS is money.MAX_CENTS`; dataclasses congeladas (atribuir levanta `FrozenInstanceError`); conjunto exato de `BidRefusal`; nenhum código em `MESSAGES` |
| Regressão | suíte inteira; `test_lot_phase.py`, `test_lot_rules.py`, `test_wallet_rules.py`, `test_openapi.py` e `test_errors.py` sem asserção alterada |

**Mutações temporárias (registrar na story, não versionar), como na 3.1:** trocar mínimo
e líder de ordem (falham os testes "abaixo do mínimo + líder"); trocar líder e saldo
(falha "líder + saldo insuficiente"); `<=` por `<` na janela (falha "exatamente 2 min");
`lot.ends_at + 2 min` por `now + 2 min` (falha o teste de base da extensão); `>=` por `>`
no mínimo (falham os limites exatos); clamp do mínimo em `MAX_CENTS` (falha o caso
irrepresentável); decidir o anti-sniping antes do saldo (falha "recusa dentro da
janela"); apagar a validação de fuso de `starts_at` em `lot_phase` (falha o teste novo).
Restaurar e conferir com `diff`.

**PostgreSQL real: nenhum teste novo.** A regra é pura por desenho (AD-26); os testes
críticos do AD-17 com lance (lances simultâneos, líder superado, anti-sniping e lance
depois do fim pelo caminho real com `clock_timestamp()`) dependem de trava, tabela de
lances e carteira comprometida e são da 3.4. O `verify` continua rodando toda a suíte de
integração existente.

## 17. Tarefas

- [x] **T1 — Decidir P1 a P13.** Decididas em 25/10/2026 e registradas em "Decisões
  fechadas", em primeira pessoa e com as alternativas descartadas.
- [x] **T2 — Decidir C1.** Opção (b) em 25/10/2026: saldo fora de `BidAttempt`; P1
  ajustada.
- [x] **T3 — Spec** (`bmad-spec`): `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/`
  (`SPEC.md`, `decisions.md` D1 a D14, `domain-contract.md`, `test-plan.md`,
  `implementation-map.md`), revisada antes do build.
- [x] **T4 — `lot_time` (CA12, P8).** `app/lot_time.py` com `LotPhase`, `lot_phase`,
  `require_aware` e `check_lot_window` (defesa completa, mesma semântica, comparação por
  instante em UTC); `lots.py` importa e reexporta, sem segunda definição.
- [x] **T5 — Regra pura (CA1 a CA11, CA13 a CA15; P1 a P7, P9 a P11).** `app/bid_rules.py`:
  `BidRefusal`; `CurrentBid`, `LotBidState`, `BidAttempt` (só `bidder_id` e
  `amount_cents`), `BidAccepted` e `EligibleBid`, com validação na construção;
  `minimum_bid_cents`; `evaluate_pre_wallet`; `evaluate_post_wallet`; `evaluate_bid` como
  composição das duas; constantes do anti-sniping.
- [x] **T6 — Testes** (matriz da seção 16): `tests/test_lot_time.py`,
  `tests/test_bid_rules.py`, `tests/test_domain_purity.py`; mutações M1 a M11 executadas.
- [x] **T7 — Verificar e documentar (CA16).** `./verify.sh` e `VERIFY_E2E=1 ./verify.sh`
  com a saída real abaixo; esta story, `sprint-status.yaml` (`review`) e
  `docs/uso_de_ia.md`. Parei na 3.2.

## 18. Arquivos prováveis (previsão, não implementação)

| Área | Arquivo | Ação prevista |
| --- | --- | --- |
| Back-end | `backend/app/lot_time.py` | novo (P8): `LotPhase`, `lot_phase` |
| Back-end | `backend/app/lots.py` | importa `LotPhase`/`lot_phase` de `app.lot_time` (e continua usando os dois), sem mudança de comportamento |
| Back-end | `backend/app/bid_rules.py` | novo (P9): enum, dataclasses, mínimo, etapa sem carteira, `evaluate_bid`, constantes |
| Testes | `backend/tests/test_bid_rules.py` (e, se útil, um módulo de construtores) | novos |
| Testes | `backend/tests/test_lot_phase.py` (ou um `test_lot_time.py`) | só **acréscimo** dos casos novos da P8 e da identidade; nenhuma asserção existente muda |
| Docs | esta story, `sprint-status.yaml`, `docs/uso_de_ia.md` | alterados |
| Sem mudança prevista | `app/money.py`, `app/wallet.py`, `app/errors.py`, `app/main.py`, `app/seed.py`, migrations, `tests/test_lot_rules.py`, `tests/test_wallet_rules.py`, `tests/test_errors.py`, `tests/test_openapi.py`, `frontend/`, `README.md`, `docs/ARQUITETURA.md`, `CLAUDE.md` | intocados |

## 19. Riscos

- **Precedência acidental.** Mitigação: P3 escrita como contrato, oito testes nomeados,
  tabela completa escrita à mão, mutações de ordem.
- **Duas semânticas de tempo.** Mitigação: P8 (módulo único) e teste de equivalência.
- **Regressão da vitrine pela defesa nova de `lot_phase`.** Um lote com horário sem fuso
  ou `starts_at >= ends_at` passaria a dar 500 na vitrine em vez de uma fase. Os lotes
  vêm do banco, com fuso e com a CHECK `ends_after_starts`: inalcançável por caminho
  válido; as suítes da 2.5 seguem como prova.
- **Clamp ou overflow no mínimo.** Mitigação: P6, `int | None`, testes no limite,
  mutação de clamp.
- **Estado corrompido escondido.** Mitigação: P4 (irrepresentável) e P7 (`ValueError`).
- **Validação espalhada.** Mitigação: P10 — cada invariante vive num só lugar (no objeto
  que a possui); as funções públicas só validam os argumentos soltos que recebem.
- **Etapa sem carteira divergir da avaliação completa.** Mitigação: `evaluate_bid` a
  reutiliza; testes de equivalência e de composição.
- **Dupla execução das validações na 3.4** (etapa sem carteira e depois avaliação
  completa repetindo as mesmas regras). Mitigação: composição definida na spec (C1),
  com um resultado intermediário que não infla a API pública.
- **Saldo lido fora da trava.** Mitigação: C1 — o saldo nem existe na tentativa; só
  entra como parâmetro da decisão de saldo, que a 3.4 chama depois das travas.
- **`BidAccepted` incoerente** (`anti_sniping_applied` sem mudança de horário ou o
  contrário). Mitigação: os dois campos são produzidos num único ponto; testes conferem
  `anti_sniping_applied == (ends_at != lot.ends_at)`.
- **`ends_at + 2 min` além do limite do `datetime`.** Só alcançável com `now` no ano
  9999; o `now` real vem do banco. Registrado, sem código especial.

## Decisões fechadas (P1 a P13, 25/10/2026)

Decidi tudo antes da spec e do código. Registro cada decisão e o que descartei.

| Questão | Decidi | Descartei |
| --- | --- | --- |
| P1 formato *(ajustada pela C1)* | Dataclasses congeladas de domínio `LotBidState`, `BidAttempt`, `CurrentBid` e `BidAccepted`, puras, sem ORM, FastAPI ou Pydantic. `BidAttempt` é só a tentativa (`bidder_id`, `amount_cents`). `now` e o saldo disponível são parâmetros explícitos: `evaluate_bid(lot, attempt, available_balance_cents, now) -> BidAccepted \| BidRefusal` | dez parâmetros soltos; modelos Pydantic; método no ORM `Lot`; a assinatura inicial `evaluate_bid(lot, attempt, now)` com o saldo dentro de `BidAttempt` (substituída pela C1) |
| P2 códigos | Exatamente `lot_not_started`, `lot_ended`, `below_minimum`, `already_winning` e `insufficient_balance`, num `StrEnum` de domínio. **Não** entram em `errors.py`/`MESSAGES` nesta story: a 3.2 define semântica e código; o contrato HTTP e a mensagem enviada pela API entram com a integração do endpoint, especialmente na 3.5. A redação portuguesa esperada fica só como referência (seção 9) | `lot_not_live`; `already_leading`/`self_outbid`; `insufficient_funds`; `bid_below_minimum`; entradas no catálogo já na 3.2 |
| P3 precedência | **Opção A**, a ordem vinculante do AD-7: período (`lot_not_started`, `lot_ended`) → `below_minimum` → `already_winning` → `insufficient_balance` → aceite. O líder com valor abaixo do mínimo recebe `below_minimum`. Não altero o AD-7. Testes explícitos de precedência (seção 10) tornam a ordem contrato | a opção B (líder antes do mínimo, que exigiria mudar o AD-7), recomendada antes da decisão; saldo antes do mínimo; ordem implícita nos `if` |
| P4 sem lance | `current: CurrentBid \| None`; `CurrentBid` contém, inseparáveis, o valor e o id do líder. "Lance sem líder" e "líder sem lance" não são representáveis pela API normal do domínio | dois opcionais independentes; sentinela `0` |
| P5 aceite | `BidAccepted(ends_at: datetime, anti_sniping_applied: bool)`, com o `ends_at` **efetivo sempre presente**: sem extensão, `lot.ends_at` e `False`; com extensão, `lot.ends_at + 2 min` e `True`. A 3.4 consome a decisão sem recalcular. Nada além do necessário no resultado; o mínimo tem função pura própria (fonte única) e não se repete no aceite | `new_ends_at: None` como "sem alteração" (minha recomendação antes da decisão); aceite sem dados; dados de persistência no resultado |
| P6 teto | Se `current + increment > MAX_CENTS`, não há próximo lance representável: a função do mínimo devolve `None` (`int \| None`); uma tentativa normal resulta em `below_minimum`. Nunca clamp, wrap, `float` ou inteiro acima de `MAX_CENTS`. Testes específicos | sexto motivo; clamp; devolver o inteiro exato acima do teto |
| P7 invariantes | Estado inválido é erro de programação: `ValueError` para `now`, `starts_at` ou `ends_at` sem fuso; `starts_at >= ends_at`; dinheiro que não é `int` estrito ou é `bool`; dinheiro fora da faixa (`amount_cents <= 0` ou `> MAX_CENTS`, `starting_bid_cents <= 0`, `min_increment_cents <= 0`, lance atual fora da faixa ou abaixo do lance inicial, saldo disponível negativo ou acima de `MAX_CENTS`); demais estados estruturalmente impossíveis pelos tipos. Nunca convertido em recusa de negócio | tratar `amount_cents <= 0` como `below_minimum`; `assert`; esconder corrupção atrás de `insufficient_balance` ou outra recusa |
| P8 tempo | Extrair `LotPhase` e `lot_phase()` para `app/lot_time.py`, puro (sem FastAPI, SQLAlchemy, AIC, ORM), reexportados por `app.lots` como o contrato monetário da 3.1. `lot_phase()` passa a recusar com `ValueError` `starts_at`, `ends_at` ou `now` sem fuso e `starts_at >= ends_at`. Semântica vigente intocada | importar de `app.lots`; receber a fase pronta; reescrever as comparações no módulo de lances |
| P9 módulo | `app/bid_rules.py`, só domínio puro: sem ORM, `Session`, FastAPI, PostgreSQL ou rotas. A 3.4 cria/expande a camada persistente e transacional (provavelmente `app/bids.py`) e importa a regra | `app/bids.py` único no padrão de `lots.py`/`wallet.py` (perderia a prova de pureza na 3.4); pacote `app/bids/` |
| P10 defesa | As dataclasses validam as próprias invariantes na construção (`__post_init__` ou equivalente); `evaluate_bid` recebe objetos já válidos; funções públicas auxiliares que podem ser chamadas diretamente validam os pressupostos relevantes. Sem depender do Pydantic futuro e sem repetir a mesma tabela de validação em várias funções | validar só o `now`; `assert`; repetir as validações em cada função |
| P11 etapa sem carteira | Uma etapa pura e reutilizável com as validações que **não** exigem carteira (período → mínimo → líder). `evaluate_bid` reutiliza **exatamente** essa lógica e depois avalia o saldo. Prepara a 3.4: travar lote, obter `now`, etapa sem carteira, retornar sem travar carteiras se já recusado, senão travar carteiras e validar saldo. Sem duplicar regras | só `evaluate_bid` (a 3.4 travaria carteiras para lances condenados); duas implementações paralelas (prefixo e completa) |
| P12 cancelado | Totalmente fora da 3.2: sem sexto motivo, sem `status=cancelled` na regra, sem antecipar a 3.6. A integração acontece conscientemente na 3.6 | campo de cancelamento agora |
| C1 saldo fora da tentativa | **Opção (b).** `available_balance_cents` não fica em `BidAttempt`: não é parte da tentativa do usuário, é estado autoritativo da carteira e, na 3.4, só é confiável depois das travas. `BidAttempt(bidder_id, amount_cents)` com as próprias invariantes; `LotBidState` sem mudança. Etapa sem carteira conceitualmente `(lot, attempt, now)`, executando exatamente período → mínimo → líder, sem receber nem conhecer saldo. `evaluate_bid(lot, attempt, available_balance_cents, now)` reutiliza a mesma implementação dessas regras, devolve a recusa se houver, só depois valida o saldo (`insufficient_balance`) e, se aceito, calcula o anti-sniping. A spec evita executar duas vezes as mesmas validações no caminho da 3.4 quando isso puder ser composto de forma limpa, podendo definir um resultado intermediário/tipo interno sem inflar a API pública | (a) saldo dentro de `BidAttempt` e etapa sem carteira com `bidder_id`/`amount_cents` soltos (minha recomendação antes da decisão); (c) um terceiro tipo só para a etapa sem carteira |
| P13 questão 5 | A questão do limite exato dos 2 minutos já está decidida no `ARQUITETURA.md` ("Defino: limite exato em teste com `now` fixo; caminho real com margens"). Esta story concretiza a parte pura (2 min exatos e `2 min - 1µs` estendem; `> 2 min` não estende; `0 < restante <= 2 min` estende; exatamente `ends_at` é encerrado; lance inválido nunca estende), tudo com `now` injetado. A 3.4 faz o caminho real (trava, `clock_timestamp()` depois dela, integração com margens). Não altero a arquitetura para "resolver" algo já decidido. O `CLAUDE.md`, que ainda lista a questão 5 como aberta, está desatualizado em relação ao `ARQUITETURA.md` (divergência 4) | registrar a questão como "resolvida em parte" no `ARQUITETURA.md` (minha recomendação antes da decisão); testar o limite exato com o relógio real |

**Ajustes derivados das decisões (consequências, não decisões novas):**

- Validação organizada por dono (P7 + P10): `CurrentBid` valida o próprio valor e o
  `UUID` do líder; `LotBidState` valida horários, termos e a relação `current.amount_cents
  >= starting_bid_cents`; `BidAttempt` valida o `UUID` do licitante e o valor (C1: sem
  saldo); `BidAccepted` valida que o `ends_at` tem fuso. `lot_phase` valida os próprios
  argumentos (é pública e chamada pela vitrine). A etapa sem carteira valida só o `now`;
  a avaliação completa valida o `now` e o `available_balance_cents`; os dois usam um
  único conjunto de auxiliares privados compartilhados, sem repetir a tabela.
- A recusa por período é a de `lot_phase` (P3 + P8): `evaluate_bid` chama `lot_phase`, e
  a semântica temporal existe num lugar só.
- Lance atual com lote agendado não é invariante (depende de `now`); o período vence
  (seção 7). **Confirmado por mim em 25/10/2026**, junto com a C1.
- O `ends_at` de `BidAccepted` sai em UTC.

**C1 — registro histórico (consequência de P1 + P11, decidida em 25/10/2026: opção b;
ver a linha C1 em "Decisões fechadas").**

A etapa sem carteira roda **antes** de a 3.4 ter o saldo disponível (as carteiras ainda
não foram travadas). Como a P1 põe `available_balance_cents` dentro de `BidAttempt`, a
etapa sem carteira **não pode** receber um `BidAttempt` (a 3.4 não teria como montá-lo
sem ler a carteira fora da trava).

- **(a) Recomendada:** manter a P1 ao pé da letra — `BidAttempt(bidder_id, amount_cents,
  available_balance_cents)` e `evaluate_bid(lot, attempt, now)` — e dar à etapa sem
  carteira a forma `check_bid_terms(lot, bidder_id, amount_cents, now) -> BidRefusal |
  None` (nome final na spec), que valida esses argumentos soltos pelos mesmos auxiliares
  privados de `BidAttempt` (P10). `evaluate_bid` chama `check_bid_terms(lot,
  attempt.bidder_id, attempt.amount_cents, now)` e depois o saldo.
- **(b)** Tirar o saldo de `BidAttempt` (`BidAttempt(bidder_id, amount_cents)`), usado
  pelas duas funções, e passar o saldo à parte: `evaluate_bid(lot, attempt,
  available_balance_cents, now)`. Mais simétrico, mas muda a assinatura aprovada na P1.
- **(c)** Um terceiro tipo só para a etapa sem carteira. Mais um tipo sem necessidade.

Com (a), nada do que decidi muda; com (b), a P1 muda de assinatura. *(Decidi (b): o saldo
é estado autoritativo da carteira, não parte da tentativa; a P1 foi ajustada.)*

## Questões abertas (registro histórico, decididas em 25/10/2026)

Texto de antes da decisão, mantido como registro. As decisões vigentes estão em
"Decisões fechadas (P1 a P13)".

### P1 — Formato da regra pura

- **(a)** Função com parâmetros explícitos só por palavra-chave (dez parâmetros).
- **(b)** Dataclasses congeladas + `now` explícito: `LotBidState(starts_at, ends_at,
  starting_bid_cents, min_increment_cents, current: CurrentBid | None)`,
  `BidAttempt(bidder_id, amount_cents, available_balance_cents)` e
  `evaluate_bid(lot, attempt, now) -> BidAccepted | BidRefusal`, com validação no
  `__post_init__`.
- **(c)** Modelos Pydantic. **(d)** Método no ORM `Lot`.

**Recomendação:** (b), pelo precedente `Schedule`, pelo agrupamento e pela validação na
construção. Descartadas: (a) parâmetros fáceis de trocar; (c) Pydantic é borda de API;
(d) acoplamento ao ORM.

### P2 — Códigos dos cinco motivos e onde mora a mensagem

Códigos propostos: `lot_not_started`, `lot_ended`, `below_minimum`, `already_winning`,
`insufficient_balance`, num `StrEnum` `BidRefusal`. Mensagens: (a) só na story, catálogo
na 3.4; (b) catálogo já na 3.2. **Recomendação:** os cinco códigos e (a).

### P3 — Precedência entre recusas simultâneas

- **(A)** Ordem literal do AD-7: período → mínimo → líder → saldo.
- **(B)** "O que nenhum valor resolve vem antes": período → líder → mínimo → saldo
  (exigiria ajustar o AD-7 antes do código).
- **(C)** Saldo antes do mínimo.

**Recomendação de então:** (B), para o líder com valor abaixo do mínimo receber direto
"você já está ganhando". *(Decidi (A); ver "Decisões fechadas".)*

### P4 — Representação de "sem lance atual / sem líder"

(a) dois opcionais; (b) `current: CurrentBid | None`; (c) sentinela `0`.
**Recomendação:** (b).

### P5 — Resultado do aceite e anti-sniping

(a) `BidAccepted(new_ends_at: datetime | None)`; (b) `BidAccepted(ends_at, extended:
bool)`; (c) aceite sem dados. Mais a função pública do mínimo. **Recomendação de então:**
(a). *(Decidi (b), com o nome `anti_sniping_applied`; ver "Decisões fechadas".)*

### P6 — `current + increment > MAX_CENTS`

(a) mínimo exato, `below_minimum`, função do mínimo devolve `None`; (b) função devolve o
inteiro acima do teto; (c) sexto motivo; (d) clamp. **Recomendação:** (a).

### P7 — Estados inconsistentes

Proposta: `ValueError` para horários sem fuso, `starts_at >= ends_at`, dinheiro fora da
faixa, `bool` ou não `int`, lance atual abaixo do inicial, saldo negativo, `amount_cents
<= 0` (precedente F-09), ids que não são `UUID`; recusa de negócio só para as cinco
situações válidas. **Recomendação:** essa tabela.

### P8 — Reutilizar `lot_phase`

(a) importar de `app.lots`; (b) mover para módulo puro e reexportar; (c) fase pronta como
entrada; (d) reescrever. **Recomendação de então:** (b), sem mudar `lot_phase`; a regra de
lance validaria os fusos antes. *(Decidi (b) e também reforçar a defesa da própria
`lot_phase`; ver "Decisões fechadas".)*

### P9 — Onde vive a regra

(a) `app/bids.py` único; (b) `app/bid_rules.py` puro; (c) pacote. **Recomendação:** (b).

### P10 — Defesa em profundidade

(a) validação completa na construção; (b) só o `now`; (c) `assert`. **Recomendação:**
(a), limitada à tabela da P7.

### P11 — Uma chamada ou prefixo sem saldo

(a) função de prefixo sem saldo, reutilizada pela completa; (b) só a completa.
**Recomendação:** (a).

### P12 — Lote cancelado

**Recomendação:** fora da 3.2; a 3.6 decide.

### P13 — Questão 5

**Recomendação de então:** confirmar e registrar no `ARQUITETURA.md` como "resolvida em
parte na 3.2". *(Decidi não alterar a arquitetura; ver "Decisões fechadas".)*

## Divergências encontradas entre as fontes e o código

1. **Skill.** `bmad-create-story` não está instalado (só o README do shim).
2. **ADs da story.** O `epics.md` lista AD-5 e AD-26; considero também AD-3, AD-6, AD-7,
   AD-8, AD-17, AD-27 e AD-30. Acréscimo, não contradição.
3. **AD-7 × precedência.** Resolvida pela P3 (opção A): a precedência segue o AD-7, que
   não muda.
4. **Questão 5 (administrativa).** O `ARQUITETURA.md` já escreve "Defino: limite exato em
   teste com `now` fixo; caminho real com margens"; o `CLAUDE.md` ainda a lista entre as
   questões abertas e está, portanto, **desatualizado** em relação ao `ARQUITETURA.md`.
   Não corrijo nesta story (P13); pede uma ação separada, como as dívidas do item 9.
5. **`lot_phase` só valida o `now`.** Com `starts_at`/`ends_at` sem fuso dá `TypeError`,
   e com `starts_at >= ends_at` devolve uma fase. Corrigido pela P8 nesta story.
6. **Acoplamento de `lots.py`.** `lot_phase` mora num módulo que importa FastAPI,
   SQLAlchemy e o cliente da AIC. Resolvido pela P8.
7. **Mínimo irrepresentável alcançável.** A 2.4 aceita `min_increment_cents = MAX_CENTS`.
   Tratado pela P6.
8. **Cancelado.** A 3.6 cria um estado que os cinco motivos não cobrem. Fora da 3.2 (P12).
9. **Dívida administrativa herdada (não corrijo; exige ação separada, como registrado na
   3.1):** `sprint-status.yaml` ainda tem `epic-1: in-progress` com 1.1 a 1.4 `done`, e o
   `deferred-work.md` (2.1) ainda fala da 1.4 como `review`.

## Documentação a sincronizar (na implementação, não agora)

- Esta story: registro de implementação, evidências reais e mutações.
- `sprint-status.yaml`: a story avança conforme o fluxo BMAD.
- `docs/uso_de_ia.md`: seção da 3.2 (criação da story, decisões, spec, implementação).
- `README.md`: sem mudança (nenhum comportamento visível; a 3.4/3.5 documentam o lance e
  o anti-sniping sem teto).
- `docs/ARQUITETURA.md` e `CLAUDE.md`: sem mudança nesta story (P13; divergência 4).

## Definition of Done da story

- P1 a P13 e C1 decididas e registradas (feito).
- Spec criada a partir desta story, só quando eu mandar.
- `app/lot_time.py` com a defesa da P8 e reexportação em `lots.py`, sem mudança de
  semântica.
- `app/bid_rules.py` puro, com os cinco códigos, as quatro dataclasses validadas na
  construção (`BidAttempt` sem saldo), a função do mínimo `int | None`, a etapa sem
  carteira `(lot, attempt, now)` reutilizada por `evaluate_bid(lot, attempt,
  available_balance_cents, now)` e pela composição sem dupla execução, a precedência da P3 e o anti-sniping só no aceite.
- Matriz da seção 16 implementada e verde, inclusive as oito combinações de precedência,
  a tabela completa escrita à mão, pureza e invariantes; mutações temporárias
  registradas.
- Nenhum teste existente afrouxado.
- `./verify.sh` passa, com a saída real registrada nesta story.
- `docs/uso_de_ia.md` com a seção da 3.2; `sprint-status.yaml` atualizado pelo fluxo.
- Nenhuma migration, rota, erro HTTP, entrada em `MESSAGES`, tela, alteração de saldo,
  trava, `clock_timestamp()` ou persistência de `ends_at`.
- Code review conforme o fluxo do épico; eu reviso e faço o commit. Paro na 3.2.

## Registro e status

Status: **done** (26/10/2026). Implementação, verificações e revisão independente
final concluídas. F-01, F-02, F-03 e N-01 corrigidos; documentação de D8 sincronizada.
A re-review final foi **APROVADA PARA DONE**, sem novo finding real, com a
compatibilidade para a Story 3.4 pronta sem redesenho. Decidi encerrar a Story 3.2.
Os registros abaixo preservam o histórico das etapas anteriores. Sem Git e sem deploy.
A Story 3.3 não foi iniciada.

## Registro de implementação (26/10/2026)

**Criados:** `backend/app/lot_time.py`, `backend/app/bid_rules.py`,
`backend/tests/test_lot_time.py`, `backend/tests/test_bid_rules.py`,
`backend/tests/test_domain_purity.py`.
**Modificados:** `backend/app/lots.py` (removidas as definições de `LotPhase` e
`lot_phase`; `from app.lot_time import LotPhase, lot_phase`, que continuam importáveis de
`app.lots`), esta story, `sprint-status.yaml`, `docs/uso_de_ia.md`.
**Intocados (conferido):** `money.py`, `wallet.py`, `errors.py`, migrations, `frontend/`,
`README.md`, `ARQUITETURA.md`, `CLAUDE.md`, `tests/test_lot_phase.py`,
`tests/test_lot_rules.py`, `tests/test_wallet_rules.py`, `tests/test_errors.py`,
`tests/test_openapi.py`, `tests/integration/*`.

**Desenho final (como na spec).**

- `lot_time`: `LotPhase`, `lot_phase(starts_at, ends_at, now)`, `require_aware`,
  `check_lot_window`. Só `datetime` e `enum`. `lot_phase` valida a janela (`ValueError` para
  não-`datetime`, sem fuso e `starts_at >= ends_at`) e depois o `now`, e compara depois de
  `astimezone(UTC)`.
- `bid_rules`: `BidRefusal` (cinco valores), `CurrentBid(amount_cents, leader_id)`,
  `LotBidState(starts_at, ends_at, starting_bid_cents, min_increment_cents, current)`,
  `BidAttempt(bidder_id, amount_cents)`, `BidAccepted(ends_at, anti_sniping_applied)`,
  `EligibleBid(amount_cents, ends_at, now)`, todos `frozen=True, kw_only=True`.
- Assinaturas: `minimum_bid_cents(lot) -> int | None`; `evaluate_pre_wallet(lot, attempt,
  now) -> EligibleBid | BidRefusal`; `evaluate_post_wallet(eligible,
  available_balance_cents) -> BidAccepted | BidRefusal`; `evaluate_bid(lot, attempt,
  available_balance_cents, now) -> BidAccepted | BidRefusal`.
- Ordem real: período (`lot_phase`) → mínimo (`minimum_bid_cents`) → líder → saldo →
  anti-sniping. `evaluate_bid` valida o saldo, chama `evaluate_pre_wallet`, devolve a
  recusa se houver e senão chama `evaluate_post_wallet`: nenhuma regra existe duas vezes.
- `EligibleBid`: um `InitVar` `issued` que precisa ser o token privado do módulo
  (`_ISSUED_BY_PRE_WALLET`); construção direta e `dataclasses.replace` levantam
  `ValueError`. É só uma trava contra uso acidental, não fronteira de segurança, e usa só
  recursos simples de `dataclasses` (D3).

**Desvios da spec:** nenhum de comportamento. Só ajuste de estilo: comentários e
docstrings reduzidos a 88 colunas (Ruff E501). O teste de `EligibleBid` por `dataclasses.replace`
passou sem ajuste no Python 3.13 do projeto.

**Mutações temporárias (M1 a M11), todas executadas** (cópia em área temporária; mutação
aplicada por script; testes de `test_bid_rules`, `test_lot_time`, `test_domain_purity` e
`test_lot_phase`; arquivo restaurado por cópia e conferido com `cmp`, idêntico nas onze):

| # | Mutação | Resultado (falharam, entre outros) |
| --- | --- | --- |
| M1 | mínimo ↔ líder em `evaluate_pre_wallet` | 7 falhas: `test_below_minimum_beats_already_winning`, linhas 23 e 24 da tabela (em três testes) |
| M2 | saldo antes de `evaluate_pre_wallet` em `evaluate_bid` | 38 falhas: `test_below_minimum_beats_insufficient_balance`, `test_already_winning_beats_insufficient_balance`, `test_ended_beats_everything`, linhas `INSUF` da tabela |
| M3 | período depois do mínimo | 41 falhas: `test_not_started_beats_below_minimum`, `test_ended_beats_below_minimum`, `test_ended_beats_everything`, linhas da tabela |
| M4 | `<=` → `<` na janela | 1 falha: `test_anti_sniping_window[2min]` |
| M5 | `ends_at + 2 min` → `now + 2 min` | 11 falhas: `test_extension_is_from_current_end_not_from_now`, `test_extension_is_cumulative`, `test_anti_sniping_window`, outros |
| M6 | `<` → `<=` no mínimo | 53 falhas, incluindo `test_first_bid_minimum[10000-10000]` e `test_next_bid_minimum[1000-21000]` (o aceite do mínimo exato deixou de ocorrer, derrubando também testes que dependem do `eligible_bid()` auxiliar) |
| M7 | clamp `min(minimum, MAX_CENTS)` no lugar de `None` | 4 falhas: `test_next_minimum_one_above_max_is_unreachable`, `test_current_and_increment_at_max`, `test_increment_max_after_first_bid` |
| M8 | anti-sniping decidido antes do saldo | 1 falha: `test_refusals_inside_the_window_never_extend[insufficient_balance]` |
| M9 | apagar `require_aware("starts_at", ...)` de `check_lot_window` | 8 falhas: `test_naive_starts_at_is_refused`, não-`datetime`, `tzinfo` sem offset, ordem da janela |
| M10 | comparar sem `astimezone(UTC)` em `lot_phase` | 2 falhas: `test_same_tzinfo_in_an_ambiguous_hour_compares_instants`, `test_period_with_same_tzinfo_in_an_ambiguous_hour` |
| M11 | validar o saldo só depois de `evaluate_pre_wallet` | 2 falhas: `test_corrupt_balance_is_never_hidden_behind_a_refusal[ended]` e `[scheduled]` |

Depois de cada restauração a suíte voltou ao verde (conferido no `verify` final).

**Verificação (saída real desta sessão, 26/10/2026).**

- `./verify.sh`: exit 0. Ruff ok; `ruff format --check`: 71 arquivos; pytest: **1553
  passed, 1 warning** em 49,60 s; ESLint, `tsc`, `node --test` (114 testes, 114 pass),
  build do Vite e `docker build` ok.
- `VERIFY_E2E=1 ./verify.sh`: exit 0. Mesmo back-end (1553 passed, 49,47 s) e front;
  Playwright: **127 passed, 5 skipped** (`real-stack.spec.ts`, só com `E2E_REAL_BASE_URL`).
- Testes novos da 3.2 isolados: `test_domain_purity.py`, `test_lot_time.py`,
  `test_bid_rules.py` e `test_lot_phase.py` juntos, 385 passed em 0,18 s (execução focada
  antes do `verify`).
- Nenhum teste existente foi alterado ou afrouxado.

**Teste manual:** nenhum específico. A story não cria UI nem endpoint; a regra pura é
coberta por testes e a regressão das telas existentes pelo `verify` e pelo E2E.

**Riscos e limitações.** (1) A `lot_phase` agora recusa janelas inválidas com `ValueError`;
lotes do banco sempre têm fuso e `ends_after_starts`, então nenhum caminho válido muda.
(2) `EligibleBid` impede uso acidental, não código Python malicioso. (3) `app.money`
importa `pydantic`, então `bid_rules` o carrega de forma transitiva; os imports diretos
respeitam a allowlist. (4) `ends_at + 2 min` só sai do intervalo do `datetime` com `now`
no ano 9999; o `now` real vem do banco (3.4).


## Correções dos findings aprovados F-01 a F-03 (26/10/2026)

Decidi limitar esta rodada aos três findings aprovados e manter a story em `review`.
Não autorizei nova revisão, fechamento da story nem início da 3.3.

- **F-01 — igualdade de UUID.** Acrescentei
  `test_already_winning_uses_uuid_equality_not_identity`: dois objetos `uuid.UUID`
  distintos com o mesmo valor, com asserções explícitas de `==` e `is not`. Tanto
  `evaluate_pre_wallet` quanto `evaluate_bid` devolvem `ALREADY_WINNING` com o mínimo
  válido e saldo suficiente. Mantive a comparação correta de produção com `==`.
- **Mutação real do F-01.** Troquei temporariamente
  `attempt.bidder_id == lot.current.leader_id` por `is`. O teste novo falhou:
  `evaluate_pre_wallet` devolveu `EligibleBid` em vez de `ALREADY_WINNING`.
  Resultado: **1 failed**, pytest exit 1. Restaurei em `finally` a cópia anterior à
  mutação; `cmp` terminou com exit 0 (conteúdo idêntico). Depois da restauração,
  a suíte focada voltou ao verde.
- **F-02 — referências de relógio.** Estendi o detector AST existente para examinar
  também `ast.Attribute` em contexto de leitura dos nomes de relógio em
  `datetime`, `date` e `time`, além das chamadas já detectadas. O autoteste cobre
  `datetime.now()`, `datetime.utcnow()`, `time.time()` e os três callables como
  `field(default_factory=...)`, preservando os casos anteriores. Na prova direta,
  `field(default_factory=datetime.now)` devolveu `['now']`;
  `datetime.utcnow` e `time.time` nas factories devolveram `['utcnow']` e `['time']`.
  Acrescentei casos válidos para `now` injetado, `eligible.now`, construção de um
  `datetime` fixo e `field(default_factory=list)`. Descartei a detecção indiscriminada
  de qualquer atributo chamado `now`: ela rejeitava o dado válido `eligible.now`.
  Não introduzi busca textual, framework de lint nem defesa contra reflexão.
- **F-03 — documentação da composição.** Ajustei apenas as docstrings do módulo e de
  `evaluate_bid`: para entradas estruturalmente válidas, a avaliação equivale à
  composição pré-carteira → pós-carteira; por D8, o saldo separado é validado antes
  das recusas de negócio e sua corrupção levanta `ValueError`, inclusive antes de
  uma recusa temporal. Comparei a AST com a cópia anterior, removendo docstrings:
  código executável idêntico. Não alterei arquitetura nem comportamento de domínio.

**Verificações reais desta rodada.**

- Focada após restaurar a mutação: `uv run pytest tests/test_bid_rules.py
  tests/test_domain_purity.py` — **355 passed em 0,16 s**, exit 0.
- `./verify.sh` — **exit 0**: Ruff ok, 71 arquivos formatados, back-end
  **1563 passed, 1 warning em 50,59 s**; ESLint, typecheck, **114 testes do front-end**,
  build Vite e build Docker aprovados. O aviso é a depreciação de `httpx` pelo
  `starlette.testclient` já presente no ambiente.
- Não repeti o E2E opt-in nesta rodada, conforme o escopo aprovado.

**Ambiente e desvios.** A sessão executou no Codex com GPT-6.1, e não no Sonnet pedido
no texto inicial. O cache padrão do `uv` foi bloqueado pelo sandbox; usei
`UV_CACHE_DIR=/private/tmp/story32-uv-cache`. Os testes focados receberam os valores
locais fictícios de banco e origem já usados pelo `verify.sh`, sem ler `.env*`.
A conexão ao PostgreSQL exigiu execução fora do sandbox; o banco foi confirmado
saudável via Docker Compose. O primeiro detector rejeitou `eligible.now`; corrigi
esse falso positivo e acrescentei a regressão. O primeiro `verify` parou em duas
linhas acima de 88 colunas; corrigi a formatação e repeti o verify completo com sucesso.

**Estado final.** `sprint-status.yaml` permaneceu byte a byte idêntico à cópia do início:
Story 3.2 `review`, Epic 3 `in-progress`, Story 3.3 `backlog`. Não executei Git,
code review, deploy nem iniciei a 3.3.


## Correção N-01 e sincronização documental de D8 (26/10/2026)

Decidi corrigir somente a brecha de aliases normais do guardrail AST apontada na
re-review independente (F-02 parcial, N-01 MEDIUM). Mantive a story em `review` e
não autorizei nova rodada de code review nesta sessão.

- **Detector:** uma primeira passagem por `ast.Import` e `ast.ImportFrom` absolutos
  monta um mapa dos imports de `datetime` e `time`. Exemplos: `dt` resolve para
  `datetime.datetime` com `from datetime import datetime as dt`, ou para `datetime`
  com `import datetime as dt`; `clock` resolve para `time`. Uma função curta resolve
  cadeias de `ast.Name`/`ast.Attribute`. A segunda passagem verifica nomes carregados
  cujo dono canônico é `datetime.datetime`, `datetime.date` ou `time`, comparando o
  nome final com a lista proibida já existente. Assim a mesma regra encontra uma
  chamada e uma referência a callable, sem depender de `ast.Call` nem do nome literal
  do alias. Não acrescentei dependências, busca textual ou framework de lint.
- **Regressões:** preservei todos os casos anteriores e acrescentei chamadas e
  factories para `datetime.datetime.now/utcnow`, `dt.datetime.now/utcnow`,
  `datetime.now/utcnow`, `dt.now/utcnow`, `time.time`, `clock.time` e uma função
  importada diretamente com alias (`from time import time as read_clock`). Um teste
  explícito cobre `field(default_factory=dt.now)`. Os negativos preservam
  `eligible.now`, `lot.starts_at`, `result.ends_at`, datas fixas e factory `list`;
  também provam que nomes locais, chamadas locais e imports de outros módulos não
  viram relógio só por se chamarem `datetime`, `time` ou `now`.
- **Mutação real:** ignorei temporariamente `alias.asname` no mapa de `ImportFrom`,
  registrando `datetime` em vez de `dt`. O teste
  `test_clock_detector_detects_dt_now_factory` falhou: detector retornou `[]` em vez
  de `['now']`. Resultado: **1 failed em 0,03 s**, pytest exit 1. Restaurei o arquivo
  em `finally` e confirmei com `cmp` (exit 0, conteúdo idêntico ao anterior à mutação).
- **D8:** sincronizei somente a docstring ilustrativa e o parágrafo de garantias do
  `domain-contract.md`: equivalência pré → pós-carteira para entradas estruturalmente
  válidas, validação antecipada do saldo separado e `ValueError` para saldo
  corrompido antes de recusas de negócio. Não alterei a decisão nem a implementação.

**Resultados reais desta rodada:** `test_domain_purity.py`: **52 passed em 0,04 s**;
`test_bid_rules.py test_lot_time.py test_domain_purity.py`, depois da restauração:
**405 passed em 0,22 s**. `./verify.sh`: **exit 0**, Ruff ok, 71 arquivos formatados,
**1592 passed, 1 warning em 49,75 s** no back-end, ESLint, typecheck,
**114 testes do front-end**, Vite e Docker build aprovados. O warning é a depreciação
herdada de `httpx` no `starlette.testclient`, mantida sem correção.

**Escopo e ambiente:** comparei os arquivos Python de `backend/app` com cópias do início:
todos byte a byte idênticos. Usei cache temporário do `uv` e acesso ao PostgreSQL local
fora do sandbox, com os valores fictícios de banco e origem do `verify.sh`; não li
`.env*`. Ajustei duas linhas longas com o formatador Ruff antes do verify. Sem desvio
funcional; não repeti E2E porque nenhum código de front-end ou navegador foi alterado.

**Estado:** `sprint-status.yaml` idêntico ao inicial: 3.2 `review`, Epic 3
`in-progress`, 3.3 `backlog`. Não executei Git, deploy, nova revisão nem iniciei a 3.3.


## Re-review independente final e fechamento administrativo (26/10/2026)

A revisão independente final confirmou F-01, F-02, F-03 e N-01 **CORRIGIDOS**,
D8/documentação **SINCRONIZADA**, nenhum novo finding real e compatibilidade com a
Story 3.4 **PRONTA SEM REDESENHO**. A recomendação final foi **APROVADA PARA DONE**.
Com essa aprovação, decidi concluir a Story 3.2 e atualizar seu status para `done`.

Usei as evidências já registradas da última correção: pureza **52 passed**, domínio
**405 passed**, `./verify.sh` **exit 0**, back-end **1592 testes passando**, front-end
**114 testes passando**, lint, formatação, typecheck e builds aprovados. O warning
Starlette/httpx é herdado e permanece fora do escopo. Não repeti verificações nem
executei novo code review para este fechamento administrativo.

Preservei os registros anteriores. Alterei somente documentação/status: Story 3.2
`done`, Epic 3 `in-progress`, Story 3.1 `done`, Story 3.3 `backlog`. Não executei Git,
commit, push ou deploy, nem iniciei a Story 3.3.
