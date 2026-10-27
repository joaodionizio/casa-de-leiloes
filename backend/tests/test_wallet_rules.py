"""Regra pura da carteira e contrato monetário (Story 3.1, CAP-3, CAP-6). Sem banco."""

import ast
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app import lots, money, wallet
from app.money import MAX_CENTS
from app.wallet import DepositRefusal, DepositRequest, apply_deposit, available_cents


@pytest.mark.parametrize(
    ("total", "committed", "expected"),
    [(0, 0, 0), (1000, 0, 1000), (1000, 400, 600), (MAX_CENTS, MAX_CENTS, 0)],
)
def test_available_is_total_minus_committed(
    total: int, committed: int, expected: int
) -> None:
    assert available_cents(total, committed) == expected


@pytest.mark.parametrize(
    ("total", "amount", "expected"),
    [
        (0, 1, 1),
        (100, 50, 150),
        (MAX_CENTS - 10, 10, MAX_CENTS),
        (0, MAX_CENTS, MAX_CENTS),
    ],
)
def test_apply_deposit_adds_exactly(total: int, amount: int, expected: int) -> None:
    assert apply_deposit(total, amount) == expected


@pytest.mark.parametrize(
    ("total", "amount"), [(MAX_CENTS - 10, 11), (MAX_CENTS, 1), (1, MAX_CENTS)]
)
def test_apply_deposit_refuses_a_total_above_the_ceiling(
    total: int, amount: int
) -> None:
    assert apply_deposit(total, amount) is DepositRefusal.BALANCE_LIMIT_EXCEEDED


@pytest.mark.parametrize(
    "amount", [0, -1, -MAX_CENTS, MAX_CENTS + 1, True, False, 100.0, 1.5, "100", None]
)
def test_apply_deposit_rejects_an_amount_that_is_not_positive_cents(
    amount: Any,
) -> None:
    """A regra guarda o próprio contrato (`Cents`), além da validação da API: um
    depósito nunca diminui o saldo nem aceita `bool`, fração ou texto."""
    with pytest.raises(ValueError):
        apply_deposit(0, amount)


def test_the_refusal_code_is_the_catalog_code() -> None:
    from app.errors import BALANCE_LIMIT_EXCEEDED, MESSAGES

    assert DepositRefusal.BALANCE_LIMIT_EXCEEDED.value == BALANCE_LIMIT_EXCEEDED
    assert BALANCE_LIMIT_EXCEEDED in MESSAGES


# --- DepositRequest: entrada estrita em centavos ---


def error_type(payload: Any) -> str:
    with pytest.raises(ValidationError) as error:
        DepositRequest.model_validate(payload)
    (item,) = error.value.errors()
    return item["type"]


@pytest.mark.parametrize("amount", [1, 50000, MAX_CENTS])
def test_valid_amounts_are_accepted(amount: int) -> None:
    assert (
        DepositRequest.model_validate({"amount_cents": amount}).amount_cents == amount
    )


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "greater_than"),
        (-1, "greater_than"),
        (MAX_CENTS + 1, "less_than_equal"),
        (100.0, "int_type"),
        (100.5, "int_type"),
        ("100", "int_type"),
        (True, "int_type"),
        (False, "int_type"),
        (None, "int_type"),
        (1e2, "int_type"),
    ],
)
def test_invalid_amounts_are_refused_with_the_real_pydantic_type(
    amount: Any, expected: str
) -> None:
    assert error_type({"amount_cents": amount}) == expected


def test_missing_and_extra_fields_are_refused() -> None:
    assert error_type({}) == "missing"
    for extra in ("user_id", "total_balance_cents", "committed_balance_cents"):
        assert error_type({"amount_cents": 1, extra: 1}) == "extra_forbidden"


# --- contrato monetário único ---


def test_money_is_the_only_definition_of_the_ceiling_and_cents() -> None:
    assert money.MAX_CENTS == 2**53 - 1 == 9007199254740991
    assert lots.MAX_CENTS is money.MAX_CENTS
    assert lots.Cents is money.Cents
    assert wallet.MAX_CENTS is money.MAX_CENTS
    assert wallet.Cents is money.Cents


def assigned_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def test_lots_and_wallet_do_not_redefine_the_money_contract() -> None:
    for module in (lots, wallet):
        assert assigned_names(Path(module.__file__)) & {"MAX_CENTS", "Cents"} == set()
    assert {"MAX_CENTS", "Cents"} <= assigned_names(Path(money.__file__))


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def test_wallet_does_not_import_lots_catalog_artic_main_or_http_clients() -> None:
    modules = imported_modules(Path(wallet.__file__))
    forbidden = {"app.lots", "app.catalog", "app.artic", "app.main", "httpx"}
    assert modules & forbidden == set()


def test_money_imports_no_other_app_module() -> None:
    assert {
        m for m in imported_modules(Path(money.__file__)) if m.startswith("app")
    } == set()


def test_no_float_in_the_money_and_wallet_sources() -> None:
    for module in (money, wallet):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            assert not (isinstance(node, ast.Name) and node.id == "float")
            assert not (
                isinstance(node, ast.Constant) and isinstance(node.value, float)
            )
            assert not (isinstance(node, ast.Div))
