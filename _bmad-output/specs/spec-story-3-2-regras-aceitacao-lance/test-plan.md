# Plano de testes — Story 3.2

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

Todos unitários e puros, em `backend/tests/`, sem banco, sem HTTP, sem relógio. Nenhum
teste PostgreSQL novo: a regra é pura por desenho (AD-26); os críticos do AD-17 com lance
(trava, concorrência, `clock_timestamp()` real, margens) são da 3.4. Contagens só da
saída real do `verify`.

## 1. Arquivos e construtores

| Arquivo | Conteúdo |
| --- | --- |
| `tests/test_lot_time.py` (novo) | §2 |
| `tests/test_bid_rules.py` (novo) | §3 a §8, §10 |
| `tests/test_domain_purity.py` (novo) | §9 |
| `tests/test_lot_phase.py` | **intocado**; importa de `app.lots` e prova a reexportação |

Constantes e construtores no topo de `test_bid_rules.py`:

```python
START = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
END = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
BEFORE = START - timedelta(hours=1)   # agendado
LIVE = START + timedelta(hours=1)     # ao vivo, restante 5 h (sem anti-sniping)
MICRO = timedelta(microseconds=1)
TWO_MIN = timedelta(minutes=2)
BIDDER = uuid.UUID(int=1)
OTHER = uuid.UUID(int=2)
STARTING = 10_000
INCREMENT = 1_000
CURRENT_AMOUNT = 20_000               # mínimo seguinte: 21_000

def lot_state(*, starts_at=START, ends_at=END, starting=STARTING,
              increment=INCREMENT, current=None) -> LotBidState: ...
def leader(who: uuid.UUID, amount: int = CURRENT_AMOUNT) -> CurrentBid: ...
def attempt(amount: int, bidder: uuid.UUID = BIDDER) -> BidAttempt: ...
def accepted(ends_at=END, extended=False) -> BidAccepted: ...  # constrói o esperado
```

`FoldOffset` (para D7), definido em `test_lot_time.py` e repetido em `test_bid_rules.py`
(duas cópias de 4 linhas, sem módulo de suporte):

```python
class FoldOffset(tzinfo):
    """Offset −3 h com fold=0 e −4 h com fold=1: uma hora ambígua sem depender da
    base de fusos do sistema."""
    def utcoffset(self, dt): return timedelta(hours=-4 if dt.fold else -3)
    def dst(self, dt): return timedelta(0)
    def tzname(self, dt): return None
```

## 2. `lot_time` (CAP-1, P8, D7, D9)

| Teste | Caso → esperado |
| --- | --- |
| `test_lots_reexports_the_same_objects` | `app.lots.LotPhase is app.lot_time.LotPhase`; `app.lots.lot_phase is app.lot_time.lot_phase` |
| `test_naive_starts_at_is_refused` | `starts_at` sem fuso → `ValueError` match `"starts_at must be timezone-aware"` |
| `test_naive_ends_at_is_refused` | idem `"ends_at must be timezone-aware"` |
| `test_naive_now_is_refused_by_the_pure_module` | `now` sem fuso → `"now must be timezone-aware"` |
| `test_non_datetime_is_refused` (parametrize posição × valor) | cada posição com `"2026-10-25T12:00:00Z"`, `date(2026, 10, 25)`, `None` → `"<campo> must be a datetime"` |
| `test_tzinfo_without_offset_is_refused` | `tzinfo` cujo `utcoffset` devolve `None` → `"timezone-aware"` |
| `test_window_must_be_increasing` (parametrize) | `starts_at == ends_at`; `starts_at > ends_at`; mesmo instante em offsets diferentes (`START` e `START.astimezone(−03:00)`) → `"starts_at must be before ends_at"` |
| `test_window_is_checked_before_now` | `starts_at` sem fuso **e** `now` sem fuso → mensagem cita `starts_at` (ordem D9) |
| `test_same_tzinfo_in_an_ambiguous_hour_compares_instants` | `FoldOffset`: `starts_at = 2026-11-01 00:00` (03:00Z), `ends_at = 01:10 fold=1` (05:10Z), `now = 01:30 fold=0` (04:30Z) → `LIVE` (comparação de parede daria `ENDED`); `now = 02:20 fold=0` (05:20Z) → `ENDED` |
| `test_require_aware_returns_the_value` | devolve o mesmo objeto |
| `test_check_lot_window_accepts_a_valid_window` | devolve `None` |

Os 8 limites atuais (`START − 1µs` … `END + 30 dias`), offsets diferentes, `now` sem fuso,
os três valores do enum e as funções públicas da vitrine continuam em
`test_lot_phase.py`, sem mudança. O schema `LotPhase` do OpenAPI continua em
`test_openapi.py`, sem mudança.

## 3. Tipos e invariantes (CAP-2, P7, P10, D3–D6, D9)

Cada linha é um caso de `pytest.raises(ValueError)`; nenhuma pode devolver `BidRefusal`.

| Teste | Casos |
| --- | --- |
| `test_money_fields_reject_non_integer_cents` (parametrize campo × valor) | campos `CurrentBid.amount_cents`, `LotBidState.starting_bid_cents`, `LotBidState.min_increment_cents`, `BidAttempt.amount_cents`; valores `True`, `False`, `1.0`, `1.5`, `"100"`, `None` |
| `test_money_fields_reject_out_of_range` | mesmos campos com `0`, `-1`, `MAX_CENTS + 1` |
| `test_money_fields_accept_the_limits` | `1` e `MAX_CENTS` em cada campo constroem |
| `test_user_ids_must_be_uuid` | `leader_id` e `bidder_id` com `str(uuid)`, `1`, `None` |
| `test_lot_times_are_validated_on_construction` | `starts_at`/`ends_at` sem fuso; não-`datetime`; `starts_at == ends_at`; `starts_at > ends_at` |
| `test_current_must_be_a_current_bid_or_none` | `current=(20_000, OTHER)`, `current={"amount_cents": 20_000}` |
| `test_current_bid_below_starting_bid_is_corruption` | `current.amount_cents = STARTING − 1` → `ValueError`; `= STARTING` constrói |
| `test_bid_accepted_requires_aware_end_and_bool_flag` | `ends_at` sem fuso; `anti_sniping_applied` em `1`, `"yes"`, `None` |
| `test_eligible_bid_cannot_be_forged` | `EligibleBid(amount_cents=1, ends_at=END, now=LIVE)` → `ValueError`; `dataclasses.replace(eligible_real, amount_cents=2)` → `ValueError` |
| `test_available_balance_is_validated` (parametrize) | em `evaluate_bid` e em `evaluate_post_wallet`: `-1`, `MAX_CENTS + 1`, `True`, `1.0`, `"1"`, `None` |
| `test_available_balance_limits_are_valid` | `0` e `MAX_CENTS` não levantam |
| `test_corrupt_balance_is_never_hidden_behind_a_refusal` | lote encerrado (`now=END`) e saldo `-1` → `ValueError`, não `lot_ended`; idem lote agendado |
| `test_functions_reject_foreign_objects` | `minimum_bid_cents(SimpleNamespace(...))`, `evaluate_pre_wallet` com `lot`/`attempt` não-domínio, `evaluate_post_wallet(BidRefusal.LOT_ENDED, 0)` e `(None, 0)` → `ValueError` |
| `test_naive_now_is_refused_by_both_entry_points` | `evaluate_pre_wallet` e `evaluate_bid` com `now` sem fuso |
| `test_exact_fields` | `dataclasses.fields` de cada tipo = conjuntos de `domain-contract.md` §3; `BidAttempt` sem campo de saldo |
| `test_attempt_has_no_balance_parameter` | `BidAttempt(bidder_id=BIDDER, amount_cents=1, available_balance_cents=1)` → `TypeError` |
| `test_construction_is_keyword_only` | `BidAttempt(BIDDER, 1)` → `TypeError` |
| `test_domain_objects_are_frozen` | atribuir a um campo de cada tipo → `FrozenInstanceError` |
| `test_scheduled_lot_with_a_current_bid_is_not_corruption` | `current=leader(OTHER)`, `now=BEFORE` → `lot_not_started`, sem exceção |
| `test_refusal_codes_are_exactly_the_five` | `{r.value for r in BidRefusal}` = os cinco da P2 |
| `test_refusal_codes_are_not_http_catalog_codes` | `{r.value for r in BidRefusal} & set(app.errors.MESSAGES) == set()` |

## 4. Período, primeiro lance, lance seguinte, líder, saldo (CAP-3 a CAP-6)

Saldo suficiente = `MAX_CENTS` salvo indicação. Nos testes de período: sem lance,
`attempt(10_000)`.

| Teste | Caso → esperado |
| --- | --- |
| `test_period_boundaries` (parametrize, esperado digitado) | `START − 1µs` → `lot_not_started`; `START` → `accepted()`; `START + 3h` → `accepted()`; `END − 1µs` → `accepted(END + TWO_MIN, True)`; `END` → `lot_ended`; `END + 1µs` → `lot_ended`; `START − 30 dias` → `lot_not_started`; `END + 30 dias` → `lot_ended` |
| `test_period_refusal_matches_lot_phase` | grade dos 8 `now` acima: `SCHEDULED` ↔ `lot_not_started`, `ENDED` ↔ `lot_ended`, `LIVE` ↔ nenhuma recusa de período |
| `test_period_compares_instants_across_offsets` | `starts_at`/`ends_at` em −03:00, `now` em +09:00, mesmos instantes da grade → mesmos resultados |
| `test_period_with_same_tzinfo_in_an_ambiguous_hour` | `FoldOffset`, janela 03:00Z–05:10Z: `now = 01:30 fold=0` (04:30Z) → `accepted(05:10Z, False)`; `now = 02:09 fold=0` (05:09Z) → `accepted(05:12Z, True)` |
| `test_first_bid_minimum` (parametrize) | sem lance: `9_999` → `below_minimum`; `10_000` e `10_001` → aceito; `starting=1`, `amount=1` → aceito |
| `test_next_bid_minimum` (parametrize) | `current=leader(OTHER, 20_000)`, `i=1_000`: `20_999`, `20_000`, `15_000` → `below_minimum`; `21_000`, `21_001` → aceito; `i=1`: `20_000` → `below_minimum`, `20_001` → aceito |
| `test_minimum_bid_cents` (parametrize) | sem lance → `STARTING`; `current=20_000, i=1_000` → `21_000`; os casos de §6 |
| `test_leader_cannot_outbid_itself` | `current=leader(BIDDER)`, `amount=21_000`, saldo suficiente → `already_winning` |
| `test_another_bidder_with_the_same_input_is_accepted` | idem com `current=leader(OTHER)` → aceito |
| `test_no_current_bid_means_no_leader` | sem lance, `BIDDER`, `10_000` → aceito |
| `test_balance_boundaries` (parametrize) | `current=leader(OTHER)`, `amount=21_000`: saldo `20_999` → `insufficient_balance`; `21_000`, `21_001`, `MAX_CENTS` → aceito; `0` → `insufficient_balance` |
| `test_same_input_same_result_and_inputs_unchanged` | duas chamadas iguais → resultados iguais; `lot`/`attempt` iguais a cópias feitas antes |

## 5. Precedência (CAP-6, P3, D11)

### 5.1 Oito combinações nomeadas (um teste cada)

| Teste | Montagem | Esperado |
| --- | --- | --- |
| `test_not_started_beats_below_minimum` | `now=BEFORE`, sem lance, `9_999`, saldo `MAX_CENTS` | `lot_not_started` |
| `test_ended_beats_below_minimum` | `now=END`, sem lance, `9_999` | `lot_ended` |
| `test_ended_beats_already_winning` | `now=END`, `leader(BIDDER)`, `21_000` | `lot_ended` |
| `test_below_minimum_beats_already_winning` | `now=LIVE`, `leader(BIDDER)`, `20_500` | `below_minimum` |
| `test_below_minimum_beats_insufficient_balance` | `now=LIVE`, sem lance, `9_999`, saldo `0` | `below_minimum` |
| `test_already_winning_beats_insufficient_balance` | `now=LIVE`, `leader(BIDDER)`, `21_000`, saldo `20_999` | `already_winning` |
| `test_only_insufficient_balance` | `now=LIVE`, `leader(OTHER)`, `21_000`, saldo `20_999` | `insufficient_balance` |
| `test_ended_beats_everything` | `now=END`, `leader(BIDDER)`, `20_500`, saldo `0` | `lot_ended` |

Mais `test_not_started_beats_leader_and_balance`: `now=BEFORE`, `leader(BIDDER)`, `21_000`,
saldo `0` → `lot_not_started`.

### 5.2 Tabela completa, escrita à mão (`test_precedence_table`)

Fase: `SCHEDULED` (`now=BEFORE`), `LIVE` (`now=LIVE`), `ENDED` (`now=END`). Lance atual:
`NONE`, `OTHER` (`leader(OTHER)`), `SELF` (`leader(BIDDER)`); tentativa sempre de
`BIDDER`. Valor: `OK = 50_000`, `LOW = 9_999` (abaixo do mínimo em todos os casos).
Saldo: `SUFF = 50_000`, `INSUF = 9_998`. `ACCEPT = accepted()` (`END`, `False`). Cada
linha é uma tupla literal no `parametrize`; o esperado nunca é calculado.

| # | Fase | Atual | Valor | Saldo | Esperado |
| --- | --- | --- | --- | --- | --- |
| 1 | SCHEDULED | NONE | OK | SUFF | `lot_not_started` |
| 2 | SCHEDULED | NONE | OK | INSUF | `lot_not_started` |
| 3 | SCHEDULED | NONE | LOW | SUFF | `lot_not_started` |
| 4 | SCHEDULED | NONE | LOW | INSUF | `lot_not_started` |
| 5 | SCHEDULED | OTHER | OK | SUFF | `lot_not_started` |
| 6 | SCHEDULED | OTHER | OK | INSUF | `lot_not_started` |
| 7 | SCHEDULED | OTHER | LOW | SUFF | `lot_not_started` |
| 8 | SCHEDULED | OTHER | LOW | INSUF | `lot_not_started` |
| 9 | SCHEDULED | SELF | OK | SUFF | `lot_not_started` |
| 10 | SCHEDULED | SELF | OK | INSUF | `lot_not_started` |
| 11 | SCHEDULED | SELF | LOW | SUFF | `lot_not_started` |
| 12 | SCHEDULED | SELF | LOW | INSUF | `lot_not_started` |
| 13 | LIVE | NONE | OK | SUFF | `ACCEPT` |
| 14 | LIVE | NONE | OK | INSUF | `insufficient_balance` |
| 15 | LIVE | NONE | LOW | SUFF | `below_minimum` |
| 16 | LIVE | NONE | LOW | INSUF | `below_minimum` |
| 17 | LIVE | OTHER | OK | SUFF | `ACCEPT` |
| 18 | LIVE | OTHER | OK | INSUF | `insufficient_balance` |
| 19 | LIVE | OTHER | LOW | SUFF | `below_minimum` |
| 20 | LIVE | OTHER | LOW | INSUF | `below_minimum` |
| 21 | LIVE | SELF | OK | SUFF | `already_winning` |
| 22 | LIVE | SELF | OK | INSUF | `already_winning` |
| 23 | LIVE | SELF | LOW | SUFF | `below_minimum` |
| 24 | LIVE | SELF | LOW | INSUF | `below_minimum` |
| 25 | ENDED | NONE | OK | SUFF | `lot_ended` |
| 26 | ENDED | NONE | OK | INSUF | `lot_ended` |
| 27 | ENDED | NONE | LOW | SUFF | `lot_ended` |
| 28 | ENDED | NONE | LOW | INSUF | `lot_ended` |
| 29 | ENDED | OTHER | OK | SUFF | `lot_ended` |
| 30 | ENDED | OTHER | OK | INSUF | `lot_ended` |
| 31 | ENDED | OTHER | LOW | SUFF | `lot_ended` |
| 32 | ENDED | OTHER | LOW | INSUF | `lot_ended` |
| 33 | ENDED | SELF | OK | SUFF | `lot_ended` |
| 34 | ENDED | SELF | OK | INSUF | `lot_ended` |
| 35 | ENDED | SELF | LOW | SUFF | `lot_ended` |
| 36 | ENDED | SELF | LOW | INSUF | `lot_ended` |

A mesma lista literal (um nome de módulo, p. ex. `PRECEDENCE_TABLE`) alimenta §7.

## 6. `MAX_CENTS` (CAP-3, P6)

Saldo `MAX_CENTS` em todos.

| Teste | Montagem → esperado |
| --- | --- |
| `test_max_amount_is_accepted` | `starting=1`, sem lance, `MAX_CENTS` → aceito |
| `test_starting_at_max` | `starting=MAX_CENTS`, sem lance: mínimo `MAX_CENTS`; `MAX_CENTS` → aceito; `MAX_CENTS − 1` → `below_minimum` |
| `test_next_minimum_exactly_max` | `current=MAX_CENTS − 1_000`, `i=1_000`: mínimo `MAX_CENTS`; `MAX_CENTS` aceito; `MAX_CENTS − 1` → `below_minimum` |
| `test_next_minimum_one_above_max_is_unreachable` | `current=MAX_CENTS − 999`, `i=1_000` (soma `MAX_CENTS + 1`): mínimo `None`; `MAX_CENTS` → `below_minimum`, sem exceção |
| `test_current_and_increment_at_max` | `starting=1`, `current=MAX_CENTS`, `i=MAX_CENTS`: mínimo `None`; `MAX_CENTS` → `below_minimum` |
| `test_increment_max_after_first_bid` | `starting=1`, `i=MAX_CENTS`, `current=leader(OTHER, 1)`: mínimo `None`; `MAX_CENTS` → `below_minimum` |
| `test_minimum_never_exceeds_max` | para todos os lotes desta seção: `m is None or m <= MAX_CENTS` e `type(m) is int` quando não `None` |

Os limites inválidos (`starting`, `increment`, tentativa e saldo acima de `MAX_CENTS`)
estão em §3.

## 7. Composição pré/pós-carteira (CAP-4, CAP-5, CAP-6, P11, C1, D2, D12)

| Teste | Prova |
| --- | --- |
| `test_pre_wallet_signature_has_no_balance` | `inspect.signature(evaluate_pre_wallet).parameters` = `["lot", "attempt", "now"]`; `evaluate_post_wallet` = `["eligible", "available_balance_cents"]`; `evaluate_bid` = `["lot", "attempt", "available_balance_cents", "now"]` |
| `test_pre_wallet_matches_the_table` | para cada linha de `PRECEDENCE_TABLE`: se o esperado é `lot_not_started`, `lot_ended`, `below_minimum` ou `already_winning`, `evaluate_pre_wallet` devolve exatamente ele; se é `ACCEPT` ou `insufficient_balance`, devolve um `EligibleBid` |
| `test_composition_equals_evaluate_bid` | para cada linha: `pre = evaluate_pre_wallet(...)`; `composto = pre if isinstance(pre, BidRefusal) else evaluate_post_wallet(pre, saldo)`; `composto == evaluate_bid(...) == esperado` |
| `test_post_wallet_only_decides_balance_and_extension` | para todo `EligibleBid` da tabela e saldos `0`, `9_998`, `50_000`, `MAX_CENTS`: resultado é `BidAccepted` ou `insufficient_balance` |
| `test_post_wallet_does_not_rerun_pre_wallet_rules` | obtém o `EligibleBid` sem spy; depois `monkeypatch` de `bid_rules.lot_phase` e `bid_rules.minimum_bid_cents` com contadores que delegam ao original; `evaluate_post_wallet` → zero chamadas a ambos |
| `test_evaluate_bid_runs_each_rule_once` | contadores em `bid_rules.lot_phase` e `bid_rules.minimum_bid_cents`: linha aceita → 1 e 1; linha `below_minimum` → 1 e 1; linha `lot_not_started` → 1 e 0 |
| `test_pre_wallet_refusal_never_reaches_the_balance` | contador em `bid_rules.evaluate_post_wallet`: zero chamadas nas linhas com recusa pré-carteira; uma nas linhas `ACCEPT` e `insufficient_balance` |
| `test_eligible_bid_is_utc_and_carries_only_what_is_needed` | entradas em −03:00: `eligible.ends_at`/`eligible.now` com `utcoffset() == 0` e iguais aos instantes; campos exatos `{amount_cents, ends_at, now}` |

## 8. Anti-sniping (CAP-7, AD-5, P5, P13)

Lote `START`–`END`, sem lance, `amount=10_000`, saldo `10_000`, `now = END − restante`.

| Teste | Caso → esperado |
| --- | --- |
| `test_anti_sniping_window` (parametrize, esperado digitado) | restante `1 h` → `accepted(END, False)`; `2 min + 1µs` → `accepted(END, False)`; `2 min` → `accepted(END + TWO_MIN, True)`; `2 min − 1µs` → idem; `1µs` → idem |
| `test_extension_is_from_current_end_not_from_now` | restante `1 min`: `ends_at == END + 2 min` e `!= now + 2 min` |
| `test_no_extension_keeps_the_current_end` | restante `1 h`: `ends_at == END`, `anti_sniping_applied is False` |
| `test_end_instant_and_after_are_ended` | `now = END` e `END + 1µs` → `lot_ended`, nenhum `BidAccepted` |
| `test_extension_is_cumulative` | 1ª: `now = END − 1 min` → `E1 = END + 2 min`; 2ª: lote com `ends_at = E1`, `current=leader(BIDDER, 10_000)`, tentativa de `OTHER` com `11_000`, `now = E1 − 30 s` → `END + 4 min` |
| `test_short_lot_accepted_at_start_is_extended` | `starts_at = T`, `ends_at = T + 90 s`, `now = T` → `accepted(T + 90 s + 2 min, True)` |
| `test_refusals_inside_the_window_never_extend` (parametrize) | restante `1 min`: `below_minimum` (`9_999`), `already_winning` (`leader(BIDDER)`, `21_000`), `insufficient_balance` (saldo `9_999`) → o `BidRefusal`, nunca `BidAccepted` |
| `test_accepted_end_is_utc` | `starts_at`/`ends_at` em −03:00, `now` em +05:30, restante `1 min` → `ends_at.utcoffset() == timedelta(0)` e `== END + 2 min`; restante `1 h` → `ends_at.utcoffset() == timedelta(0)` |
| `test_flag_matches_end_change` | para todos os aceites de §4, §5 e §8: `result.anti_sniping_applied == (result.ends_at != lot.ends_at)` |

## 9. Pureza e hora injetada (CAP-8, CAP-9, P9, D13) — `test_domain_purity.py`

Auxiliares próprios do arquivo (padrão de `test_access_policy.py`): `imported_modules(path)`,
`imported_names(path, module)`, `clock_calls(tree)`, `assigned_names(path)`.

| Teste | Prova |
| --- | --- |
| `test_lot_time_imports_only_the_standard_library` | módulos ⊆ `{"datetime", "enum"}`; nomes de `datetime` ⊆ `{"UTC", "datetime"}` |
| `test_bid_rules_imports_only_the_allowed_modules` | módulos ⊆ `{"uuid", "dataclasses", "datetime", "enum", "app.money", "app.lot_time"}` e ⊇ `{"app.money", "app.lot_time"}`; nomes de `datetime` ⊆ `{"UTC", "datetime", "timedelta"}` |
| `test_domain_modules_avoid_infrastructure` | interseção com `{"time", "fastapi", "starlette", "sqlalchemy", "pydantic", "httpx", "psycopg", "app.db", "app.main", "app.lots", "app.wallet", "app.catalog", "app.artic", "app.errors", "app.users", "app.access"}` vazia nos dois |
| `test_domain_modules_never_read_a_clock` | nenhuma `ast.Call` cujo `func` seja `Attribute` ou `Name` com nome em `{"now", "utcnow", "today", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "fromtimestamp", "utcfromtimestamp", "clock_timestamp"}` |
| `test_clock_detector_detects_a_clock` | o mesmo detector, aplicado a `ast.parse("from datetime import datetime\nx = datetime.now()")` e a `"import time\ny = time.monotonic()"`, encontra a chamada (prova que a guarda funciona) |
| `test_no_float_or_division_in_domain_modules` | nenhum `Name("float")`, constante `float` nem `ast.Div` nos dois |
| `test_domain_modules_do_not_redefine_max_cents` | `MAX_CENTS` não atribuído nos dois; `bid_rules.MAX_CENTS is money.MAX_CENTS` |
| `test_injected_now_drives_the_result` (em `test_bid_rules.py`) | lote 2026: `now = 2000-01-01` → `lot_not_started`; `now = 2100-01-01` → `lot_ended`; lote `2100-01-01 → 2100-01-02` com `now = 2100-01-01T12:00Z` → aceito; lote `2000-01-01 → 2000-01-02` com `now = 2000-01-01T12:00Z` → aceito |

## 10. Mutações temporárias (CAP-6, CAP-7, CAP-10; registrar na story, não versionar)

Procedimento sem git: `cp backend/app/<arquivo>.py "$SCRATCH/<arquivo>.orig"`; aplicar a
mutação; rodar os testes; registrar quais falharam; `cp` de volta; `diff` contra a cópia
(saída vazia); rodar os testes de novo (verdes).

| # | Mutação | Precisa falhar (no mínimo) |
| --- | --- | --- |
| M1 | trocar a ordem dos passos 2 (mínimo) e 3 (líder) em `evaluate_pre_wallet` | `test_below_minimum_beats_already_winning`; linhas 23–24 |
| M2 | em `evaluate_bid`, checar `amount > saldo` antes de `evaluate_pre_wallet` | `test_already_winning_beats_insufficient_balance`; `test_below_minimum_beats_insufficient_balance`; toda linha `INSUF` da tabela cujo esperado não é `insufficient_balance` |
| M3 | mover o período para depois do mínimo | `test_not_started_beats_below_minimum`; `test_ended_beats_below_minimum` |
| M4 | `<=` → `<` na janela | `test_anti_sniping_window[2 min]` |
| M5 | `eligible.ends_at + EXT` → `eligible.now + EXT` | `test_extension_is_from_current_end_not_from_now`; `test_extension_is_cumulative` |
| M6 | `attempt.amount_cents < minimum` → `<=` | `test_first_bid_minimum[10_000]`; `test_next_bid_minimum[21_000]` |
| M7 | mínimo com clamp: `min(minimum, MAX_CENTS)` em vez de `None` | `test_next_minimum_one_above_max_is_unreachable` |
| M8 | decidir o anti-sniping (e devolver `BidAccepted`) antes do saldo | `test_refusals_inside_the_window_never_extend[insufficient_balance]` |
| M9 | apagar `require_aware("starts_at", ...)` de `check_lot_window` | `test_naive_starts_at_is_refused` |
| M10 | comparar sem `astimezone(UTC)` em `lot_phase` | `test_same_tzinfo_in_an_ambiguous_hour_compares_instants` |
| M11 | em `evaluate_bid`, validar o saldo só depois de `evaluate_pre_wallet` | `test_corrupt_balance_is_never_hidden_behind_a_refusal` |

Se uma mutação não derrubar nenhum teste, o teste correspondente está fraco: corrigir o
**teste** (nunca a mutação) e repetir.

## 11. Regressão

Suíte inteira verde; `test_lot_phase.py`, `test_lot_rules.py`, `test_wallet_rules.py`,
`test_openapi.py`, `test_errors.py`, `test_access_policy.py` e
`tests/integration/test_public_lots.py` sem nenhuma linha alterada.
