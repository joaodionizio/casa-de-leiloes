# Contrato de domínio — Story 3.2

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

Os trechos de código abaixo são **referência normativa** de forma, ordem e mensagens; o
implementador ajusta só o estilo (docstrings em português, comentários no padrão de
`lots.py`/`wallet.py`). Nomes, assinaturas, campos, ordem dos passos e mensagens de
exceção são contrato.

## 1. Estado atual relevante (conferido no código)

- `app/lots.py` define `LotPhase` (linhas 242–248) e `lot_phase` (251–260); `lot_phase`
  só valida `now` (`"now must be timezone-aware"`). Usos: `public_lot_summary`,
  `build_public_lots`, o campo `PublicLotSummary.phase`.
- `app/money.py`: `MAX_CENTS = 9_007_199_254_740_991`; importa `pydantic` (por `Cents`).
- `app/wallet.py`: `apply_deposit` rejeita `bool`/não-`int` e fora de `1..MAX_CENTS` com
  `ValueError` (F-09) — mesmo estilo aqui.
- `users.id` é `uuid.UUID`. Não existem `bids`, lance atual, líder nem `cancelled_at`.

## 2. `app/lot_time.py` (P8, D4, D7, D9)

Módulo novo. Imports permitidos: `from datetime import UTC, datetime` e
`from enum import StrEnum`. Nada mais.

```python
class LotPhase(StrEnum):
    # docstring IDÊNTICA à atual de app/lots.py (vira description no OpenAPI)
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"


def require_aware(name: str, value: object) -> datetime:
    """Erro de programação se `value` não for um instante com fuso."""
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def check_lot_window(starts_at: datetime, ends_at: datetime) -> None:
    require_aware("starts_at", starts_at)
    require_aware("ends_at", ends_at)
    if starts_at.astimezone(UTC) >= ends_at.astimezone(UTC):
        raise ValueError("starts_at must be before ends_at")


def lot_phase(starts_at: datetime, ends_at: datetime, now: datetime) -> LotPhase:
    check_lot_window(starts_at, ends_at)
    now_utc = require_aware("now", now).astimezone(UTC)
    if now_utc < starts_at.astimezone(UTC):
        return LotPhase.SCHEDULED
    if now_utc < ends_at.astimezone(UTC):
        return LotPhase.LIVE
    return LotPhase.ENDED
```

- Semântica idêntica: `now < starts_at` agendado; `starts_at <= now < ends_at` ao vivo;
  `now >= ends_at` encerrado. Precisão de microssegundo, sem arredondamento.
- `utcoffset() is None` cobre `tzinfo=None` e `tzinfo` que não informa offset.
- `astimezone(UTC)` torna a comparação exata mesmo quando os dois argumentos têm o mesmo
  objeto `tzinfo` numa hora ambígua (D7).

**`app/lots.py`:** apagar as definições de `LotPhase` e `lot_phase` e acrescentar
`from app.lot_time import LotPhase, lot_phase` no bloco de imports `app.*` (ordem do
Ruff/isort). Nada mais muda em `lots.py`: `resolve_schedule` mantém a própria checagem de
`now`. O comentário `# --- regra pura (AD-26) ---` continua acima de `ScheduleViolation`.

## 3. `app/bid_rules.py` — tipos (P1, P2, P4, P5, C1, D3, D5, D6)

Imports permitidos: `uuid`, `dataclasses` (`InitVar`, `dataclass`), `datetime`
(`UTC`, `datetime`, `timedelta`), `enum` (`StrEnum`), `app.money` (`MAX_CENTS`),
`app.lot_time` (`LotPhase`, `check_lot_window`, `lot_phase`, `require_aware`). Nada mais.

```python
ANTI_SNIPING_WINDOW = timedelta(minutes=2)     # AD-5: 0 < restante <= janela
ANTI_SNIPING_EXTENSION = timedelta(minutes=2)  # AD-5: soma ao ends_at atual


class BidRefusal(StrEnum):
    # Declarados na ordem da precedência (P3); a ordem dos membros não é usada pelo código.
    LOT_NOT_STARTED = "lot_not_started"
    LOT_ENDED = "lot_ended"
    BELOW_MINIMUM = "below_minimum"
    ALREADY_WINNING = "already_winning"
    INSUFFICIENT_BALANCE = "insufficient_balance"


@dataclass(frozen=True, kw_only=True)
class CurrentBid:
    amount_cents: int
    leader_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class LotBidState:
    starts_at: datetime
    ends_at: datetime
    starting_bid_cents: int
    min_increment_cents: int
    current: CurrentBid | None


@dataclass(frozen=True, kw_only=True)
class BidAttempt:
    bidder_id: uuid.UUID
    amount_cents: int


@dataclass(frozen=True, kw_only=True)
class BidAccepted:
    ends_at: datetime            # fim efetivo depois da regra, sempre em UTC
    anti_sniping_applied: bool


_ISSUED_BY_PRE_WALLET = object()


@dataclass(frozen=True, kw_only=True)
class EligibleBid:
    """Tentativa que passou período, mínimo e líder. Só `evaluate_pre_wallet` a emite."""
    amount_cents: int
    ends_at: datetime  # UTC
    now: datetime      # UTC
    issued: InitVar[object] = None

    def __post_init__(self, issued: object) -> None:
        if issued is not _ISSUED_BY_PRE_WALLET:
            raise ValueError("EligibleBid is issued only by evaluate_pre_wallet")
```

Campos exatos (testados com `dataclasses.fields`): `CurrentBid` {`amount_cents`,
`leader_id`}; `LotBidState` {`starts_at`, `ends_at`, `starting_bid_cents`,
`min_increment_cents`, `current`}; `BidAttempt` {`bidder_id`, `amount_cents`};
`BidAccepted` {`ends_at`, `anti_sniping_applied`}; `EligibleBid` {`amount_cents`,
`ends_at`, `now`}. Nenhum campo de saldo fora do parâmetro `available_balance_cents`.

`current` não tem default: o adaptador da 3.4 escreve `current=None` explicitamente.

## 4. Invariantes e onde vivem (P7, P10, D4, D8, D9)

Auxiliares privados de `bid_rules`:

```python
def _require_cents(name: str, value: object, lowest: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be integer cents")
    if not lowest <= value <= MAX_CENTS:
        raise ValueError(f"{name} out of range")
    return value


def _require_user_id(name: str, value: object) -> uuid.UUID:
    if not isinstance(value, uuid.UUID):
        raise ValueError(f"{name} must be a UUID")
    return value
```

| Dono | Verifica (todas → `ValueError`) |
| --- | --- |
| `CurrentBid.__post_init__` | `amount_cents` `_require_cents(..., 1)`; `leader_id` `_require_user_id` |
| `LotBidState.__post_init__` | `check_lot_window(starts_at, ends_at)` (não-`datetime`, sem fuso, `starts_at >= ends_at`); `starting_bid_cents` e `min_increment_cents` `_require_cents(..., 1)`; `current` é `None` ou `CurrentBid` (senão `"current must be a CurrentBid or None"`); `current.amount_cents >= starting_bid_cents` (senão `"current bid below starting bid"`) |
| `BidAttempt.__post_init__` | `bidder_id` `_require_user_id`; `amount_cents` `_require_cents(..., 1)` |
| `BidAccepted.__post_init__` | `require_aware("ends_at", ...)`; `anti_sniping_applied` é `bool` (senão `"anti_sniping_applied must be a bool"`) |
| `EligibleBid.__post_init__` | token de emissão (D3) |
| `lot_phase` | `check_lot_window`; `require_aware("now", ...)` |
| `minimum_bid_cents` | `lot` é `LotBidState` (senão `"lot must be a LotBidState"`) |
| `evaluate_pre_wallet` | `lot` é `LotBidState`; `attempt` é `BidAttempt` (`"attempt must be a BidAttempt"`); `now` via `lot_phase` |
| `evaluate_post_wallet` | `eligible` é `EligibleBid` (`"eligible must be an EligibleBid"`); `_require_cents("available_balance_cents", ..., 0)` |
| `evaluate_bid` | `_require_cents("available_balance_cents", ..., 0)` **primeiro**; o resto pelas etapas |

Fora da tabela, por decisão: lote agendado com `current` **não** é inválido (P7) e dá
`lot_not_started`. `MAX_CENTS + 1` em `current.amount_cents` é inválido pela faixa; não
existe checagem de `current.amount_cents + min_increment_cents` na construção (é
representável em Python e o caso é tratado pelo mínimo, P6).

`ValueError` é erro de programação: nunca é capturado dentro dos módulos nem convertido
em `BidRefusal`. Numa requisição futura, vira o 500 genérico da 2.1.

## 5. Mínimo exigido (P5, P6)

```python
def minimum_bid_cents(lot: LotBidState) -> int | None:
    """Próximo lance mínimo, ou None quando nenhum valor até MAX_CENTS o alcança."""
    if not isinstance(lot, LotBidState):
        raise ValueError("lot must be a LotBidState")
    if lot.current is None:
        return lot.starting_bid_cents
    minimum = lot.current.amount_cents + lot.min_increment_cents
    return minimum if minimum <= MAX_CENTS else None
```

A soma é `int` exato do Python (máximo `2**54 − 2`): não há overflow, só
irrepresentabilidade. Nunca clamp, wrap ou `float`. É a fonte única do mínimo para a 3.5
("próximo mínimo" na sala).

## 6. Etapa pré-carteira (P3, P11, C1)

```python
def evaluate_pre_wallet(
    lot: LotBidState, attempt: BidAttempt, now: datetime
) -> EligibleBid | BidRefusal:
    """Período → mínimo → líder, nesta ordem (P3, AD-7 passos 4 a 6). Sem saldo."""
    # tipos de lot e attempt
    # 1. Período: a semântica única de lot_phase (também valida now).
    phase = lot_phase(lot.starts_at, lot.ends_at, now)
    if phase is LotPhase.SCHEDULED:
        return BidRefusal.LOT_NOT_STARTED
    if phase is LotPhase.ENDED:
        return BidRefusal.LOT_ENDED
    # 2. Mínimo: None = nenhum valor representável o alcança.
    minimum = minimum_bid_cents(lot)
    if minimum is None or attempt.amount_cents < minimum:
        return BidRefusal.BELOW_MINIMUM
    # 3. Líder não cobre o próprio lance.
    if lot.current is not None and attempt.bidder_id == lot.current.leader_id:
        return BidRefusal.ALREADY_WINNING
    return EligibleBid(
        amount_cents=attempt.amount_cents,
        ends_at=lot.ends_at.astimezone(UTC),
        now=now.astimezone(UTC),
        issued=_ISSUED_BY_PRE_WALLET,
    )
```

`lot_phase` e `minimum_bid_cents` são chamados pelo nome global do módulo (necessário
para os spies de D12). `lot_phase` revalida a janela já validada por `LotBidState`: é a
defesa própria de uma função pública (P8), custo desprezível, e mantém um único lugar
para a semântica temporal.

## 7. Etapa pós-carteira: saldo e anti-sniping (P3, P5, AD-5)

```python
def evaluate_post_wallet(
    eligible: EligibleBid, available_balance_cents: int
) -> BidAccepted | BidRefusal:
    """Saldo e, só para lance aceito, o anti-sniping (AD-7 passos 9 e 13)."""
    # tipo de eligible; _require_cents("available_balance_cents", ..., 0)
    # 4. Saldo disponível (total − comprometido, calculado pela 3.4 na carteira travada).
    if eligible.amount_cents > available_balance_cents:
        return BidRefusal.INSUFFICIENT_BALANCE
    # 5. Aceito. Só agora o anti-sniping: 0 < restante <= janela (AD-5, inclusiva).
    remaining = eligible.ends_at - eligible.now
    if timedelta(0) < remaining <= ANTI_SNIPING_WINDOW:
        return BidAccepted(
            ends_at=eligible.ends_at + ANTI_SNIPING_EXTENSION,
            anti_sniping_applied=True,
        )
    return BidAccepted(ends_at=eligible.ends_at, anti_sniping_applied=False)
```

- `eligible.ends_at` e `eligible.now` já estão em UTC (D7): a subtração é entre instantes.
- `remaining > 0` é sempre verdade aqui (o período exige `now < ends_at`); a condição fica
  escrita, como no AD-5.
- Extensão = **fim atual** + 2 min, nunca `now + 2 min`. Cumulativa porque a próxima
  avaliação recebe o `ends_at` que a 3.4 persistiu. Sem teto.
- `BidAccepted.ends_at` sai em UTC; `anti_sniping_applied == (ends_at != lot.ends_at)`.
- Saldo exatamente igual ao valor é aceito. Como o líder já foi recusado na etapa 3,
  quem chega aqui não tem saldo comprometido neste lote.

## 8. Avaliação completa (P1, C1, D2, D8)

```python
def evaluate_bid(
    lot: LotBidState,
    attempt: BidAttempt,
    available_balance_cents: int,
    now: datetime,
) -> BidAccepted | BidRefusal:
    """Para entradas estruturalmente válidas, equivale à composição
    `evaluate_pre_wallet` → `evaluate_post_wallet` que a 3.4 executa em duas partes.
    Por D8, valida o saldo separado antecipadamente: saldo corrompido levanta
    `ValueError` antes de qualquer recusa de negócio, inclusive temporal.
    Precedência (contrato, P3): período → mínimo → líder → saldo;
    anti-sniping só no aceite.
    """
    _require_cents("available_balance_cents", available_balance_cents, 0)
    checked = evaluate_pre_wallet(lot, attempt, now)
    if isinstance(checked, BidRefusal):
        return checked
    return evaluate_post_wallet(checked, available_balance_cents)
```

Garantias: uma implementação de cada regra; para entradas estruturalmente válidas,
`evaluate_bid` equivale à composição pré-carteira → pós-carteira. Por D8, valida o
saldo separado antecipadamente: saldo corrompido gera `ValueError` antes de qualquer
recusa de negócio, mesmo em lote agendado ou encerrado. Uma recusa pré-carteira não
executa a etapa pós-carteira nem a regra de suficiência do saldo.

## 9. Recusas de domínio × erros de programação

| Situação | Resultado |
| --- | --- |
| Entradas válidas e uma das cinco regras falha | o `BidRefusal` correspondente (devolvido, nunca levantado) |
| Entradas válidas e nenhuma falha | `BidAccepted` |
| Qualquer linha da tabela §4 | `ValueError` (levantado) |
| Lote agendado com `current` | `lot_not_started` |

Redação portuguesa de referência (não é contrato HTTP; a 3.4/3.5 decide o catálogo):
`lot_not_started` "Este lote ainda não começou."; `lot_ended` "Este lote já foi
encerrado."; `below_minimum` "Seu lance está abaixo do mínimo para este lote.";
`already_winning` "Você já está ganhando este lote."; `insufficient_balance` "Saldo
disponível insuficiente para este lance." Não entram no código desta story.

## 10. Compatibilidade com a 3.4 (descrição, não implementação)

| A 3.4 faz | Usa da 3.2 |
| --- | --- |
| trava o lote; lê um `clock_timestamp()` | — |
| monta `LotBidState` (das colunas do lote e do lance atual; `current=None` sem lance) e `BidAttempt` (`user.id`, `amount_cents` do corpo) | tipos validados na construção; incoerência → `ValueError` → 500 |
| `evaluate_pre_wallet(lot, attempt, now)`; se `BidRefusal`, rollback e responde sem travar carteiras | etapa pré-carteira |
| identifica carteiras (licitante e líder anterior), trava em `user_id` crescente (AD-8), calcula `wallet.available_cents(total, committed)` da carteira do licitante | — |
| `evaluate_post_wallet(eligible, available)`; se `insufficient_balance`, rollback | etapa pós-carteira, sem repetir regras |
| grava valor/líder, compromete/libera saldo, persiste `BidAccepted.ends_at`, publica `anti_sniping_applied` (4.1) | `BidAccepted` |
| mostra o próximo mínimo (3.5) | `minimum_bid_cents` |

Quem já tem tudo em mãos (testes, ferramentas) usa `evaluate_bid`. A 3.2 não cria
`app/bids.py`, adaptador ORM → domínio nem nada da lista acima à esquerda.
