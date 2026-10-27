---
id: SPEC-story-3-2-regras-aceitacao-lance
companions:
  - decisions.md
  - domain-contract.md
  - test-plan.md
  - implementation-map.md
  - ../spec-story-3-1-carteira-deposito/decisions.md
  - ../../../docs/ARQUITETURA.md
sources:
  - ../../implementation-artifacts/3-2-regras-de-aceitação-do-lance-com-hora-injetada.md
---

> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.


> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

> **Contrato canônico.** Esta SPEC e os arquivos em `companions:` formam o contrato
> completo da Story 3.2. P1 a P13 e C1 foram decididas pelo Joaodionizio antes desta spec
> e **não são reabertas** (`decisions.md` §1). D1 a D14 detalham essas decisões dentro do
> que elas permitem (`decisions.md` §2). Nenhuma questão aberta. A 3.2 é domínio puro:
> sem banco, HTTP, transação, relógio próprio nem persistência.

# Story 3.2: regras de aceitação do lance com hora injetada

## Why

Mandato do desafio ("Regras de lance", "Prorrogação (anti-sniping)") e do AD-26: a
decisão de aceitar ou recusar um lance precisa ser uma regra única, determinística e
testável com `now` fixo, antes que a 3.4 a coloque dentro da transação com travas e
`clock_timestamp()`. Três riscos guiam o desenho: precedência acidental entre recusas
simultâneas (P3), um mínimo que passa do teto monetário da 3.1 (P6) e a etapa
pré-carteira da 3.4 divergir da avaliação completa ou repetir as mesmas validações
(P11, C1). Também tira a semântica temporal do lote de um módulo acoplado a FastAPI,
SQLAlchemy e AIC (P8).

## Capabilities

- **CAP-1**
  - **intent:** A fase temporal do lote vive num módulo puro, com defesa completa de fuso e de janela, sem mudar a semântica nem quebrar quem já a importa de `app.lots`.
  - **success:** `app/lot_time.py` só importa biblioteca padrão; `app.lots.LotPhase is app.lot_time.LotPhase` e `app.lots.lot_phase is app.lot_time.lot_phase`; `lot_phase` levanta `ValueError` para `starts_at`, `ends_at` ou `now` sem fuso, não-`datetime`, e `starts_at >= ends_at`; compara instantes mesmo com o mesmo `tzinfo` em horas ambíguas; `tests/test_lot_phase.py`, `tests/integration/test_public_lots.py` e `tests/test_openapi.py` passam sem nenhuma linha alterada.
- **CAP-2**
  - **intent:** O estado do lote, o lance atual, a tentativa e o aceite são objetos de domínio imutáveis que só existem válidos.
  - **success:** Cada linha da tabela de invariantes (`domain-contract.md` §4) levanta `ValueError` na construção; nenhuma vira recusa; `BidAttempt` tem exatamente `bidder_id` e `amount_cents`; atribuir a qualquer campo levanta `FrozenInstanceError`; construção posicional levanta `TypeError`.
- **CAP-3**
  - **intent:** O próximo lance mínimo tem uma única fonte, que declara explicitamente quando nenhum valor representável o alcança.
  - **success:** `minimum_bid_cents` devolve `starting_bid_cents` sem lance atual, `current + increment` quando `<= MAX_CENTS` e `None` acima; nunca devolve inteiro `> MAX_CENTS`; com `None`, toda tentativa válida (inclusive `MAX_CENTS`) dá `below_minimum`.
- **CAP-4**
  - **intent:** A etapa pré-carteira decide período, mínimo e líder, nessa ordem, sem receber nem conhecer saldo.
  - **success:** `evaluate_pre_wallet(lot, attempt, now)` não tem parâmetro de saldo; devolve a recusa de período, mínimo ou líder, ou um `EligibleBid`; `EligibleBid` não pode ser construído nem copiado com `dataclasses.replace` fora dela (`ValueError`).
- **CAP-5**
  - **intent:** A etapa pós-carteira decide só o saldo e, apenas para lance aceito, o anti-sniping, sem repetir nenhuma regra pré-carteira.
  - **success:** `evaluate_post_wallet(eligible, available_balance_cents)` só devolve `BidAccepted` ou `insufficient_balance`; durante a chamada, `lot_phase` e `minimum_bid_cents` são chamados zero vezes (spy).
- **CAP-6**
  - **intent:** A avaliação completa é exatamente a composição das duas etapas e respeita a precedência contratual período → mínimo → líder → saldo.
  - **success:** As 36 linhas da tabela escrita à mão e os 8 testes nomeados de precedência passam; `evaluate_bid` e a composição explícita dão o mesmo resultado em todas as linhas; em `evaluate_bid`, recusa pré-carteira chama `evaluate_post_wallet` zero vezes, e `lot_phase`/`minimum_bid_cents` rodam uma vez cada; as mutações M1 a M3 e M11 fazem algum teste falhar.
- **CAP-7**
  - **intent:** O lance aceito com `0 < ends_at − now <= 2 min` estende o fim atual em 2 minutos, cumulativamente; nenhuma recusa estende.
  - **success:** Restante `2 min + 1 µs` e 1 h: `ends_at == lot.ends_at`, `False`; `2 min`, `2 min − 1 µs`, `1 µs`: `ends_at == lot.ends_at + 2 min`, `True`, e `!= now + 2 min`; `now == ends_at` → `lot_ended`; duas extensões seguidas somam 4 min; saída em UTC; recusas dentro da janela não produzem `BidAccepted`; mutações M4, M5 e M8 falham.
- **CAP-8**
  - **intent:** O domínio não lê relógio nem depende de ORM, FastAPI, Pydantic, sessão ou banco.
  - **success:** O teste AST confirma a allowlist de imports dos dois módulos, a ausência de chamadas de relógio, de `float`, de divisão e de redefinição de `MAX_CENTS`; `bid_rules.MAX_CENTS is money.MAX_CENTS`; o mesmo estado com `now` em 2000 e em 2100 dá resultados coerentes com cada `now`.
- **CAP-9**
  - **intent:** Os cinco motivos de recusa são códigos de domínio estáveis, sem contrato HTTP nesta story.
  - **success:** `{r.value for r in BidRefusal}` é exatamente o conjunto da P2; nenhum valor está em `app.errors.MESSAGES`; `errors.py` e `test_errors.py` sem mudança.
- **CAP-10**
  - **intent:** A entrega é verificada e documentada sem tocar no que é de outras stories.
  - **success:** `./verify.sh` termina com exit 0 e a saída real fica registrada na story; as mutações M1 a M11 executadas, revertidas e registradas; story, `sprint-status.yaml` (`review`) e `docs/uso_de_ia.md` atualizados; nenhum arquivo da lista "Intocados" (`implementation-map.md` §2) muda.

## Constraints

- AD-26/AD-6: `now` é parâmetro obrigatório, sem default, de `lot_phase`, `evaluate_pre_wallet` e `evaluate_bid`; nenhum dos dois módulos chama `datetime.now`, `utcnow`, `today`, `time.*` nem consulta banco.
- P3/AD-7: a ordem período → mínimo → líder → saldo → anti-sniping é contrato; o anti-sniping roda só depois de todas as validações de aceite.
- AD-5: extensão = `lot.ends_at + 2 min`, nunca `now + 2 min`; janela inclusiva `0 < restante <= 2 min`; `now >= ends_at` nunca reabre; sem teto de extensões.
- AD-3/P6: dinheiro só `int` estrito em centavos (`bool` recusado), nunca `float`, fração, divisão, clamp ou wrap; teto só `app.money.MAX_CENTS`.
- P9: `app/bid_rules.py` importa só biblioteca padrão, `app.money` e `app.lot_time`; `app/lot_time.py` só biblioteca padrão.
- P10/D4: cada invariante é verificada num único dono; funções públicas validam só os argumentos soltos que recebem e o tipo dos objetos de domínio.
- P11/C1/D2: período, mínimo e líder existem em uma única implementação (`evaluate_pre_wallet`); `evaluate_bid` só a compõe com `evaluate_post_wallet`; saldo nunca entra em `BidAttempt`.
- P8: a semântica das três fases não muda; `test_lot_phase.py` não muda.
- AD-30: código e mensagens de exceção em inglês; códigos de recusa em inglês.
- Nenhum teste existente muda; nenhuma asserção é afrouxada (CLAUDE.md).

## Non-goals

- Migration, tabela `bids`, ORM `Bid`, lance atual ou líder persistidos, persistência de `ends_at` (3.4).
- Endpoint de lance, política HTTP, entradas em `errors.py`/`MESSAGES`, mensagens da API, front de lance (3.4, 3.5).
- `SELECT ... FOR UPDATE`, travas de lote ou carteira, `clock_timestamp()` real, `Session`, testes PostgreSQL novos (3.4).
- Comprometer ou liberar saldo, consultar `Wallet`, importar `app.wallet` (3.4).
- Pseudônimo, canônico, SHA-256, HMAC, sequência, histórico (3.3, 3.4); WebSocket, fechamento, liquidação, catch-up (4.x).
- Cancelamento: sexto motivo, `cancelled`, campo novo (3.6).
- Verificação de papel (`AUCTIONEER` não dá lance): política de rota da 3.4.
- Mudança em `docs/ARQUITETURA.md`, `CLAUDE.md` ou `README.md`; correção das dívidas administrativas.

## Success signal

- `uv run pytest tests/test_lot_time.py tests/test_bid_rules.py tests/test_domain_purity.py tests/test_lot_phase.py` passa; cada mutação M1–M11 faz pelo menos um teste nomeado falhar e, revertida (conferida com `diff`), tudo volta a passar; `./verify.sh` termina com exit 0. Um leitor monta qualquer combinação de fase, lance atual, valor e saldo e encontra o resultado esperado digitado à mão na tabela de precedência.

## Assumptions

- `uuid.UUID` é o tipo de `bidder_id`/`leader_id`, porque `users.id` é `UUID` no banco e no ORM; a 3.4 passa `User.id` sem conversão.
- O `ValueError` de estado inválido, numa requisição futura, vira o 500 genérico do handler da 2.1, como o F-09 da 3.1.
