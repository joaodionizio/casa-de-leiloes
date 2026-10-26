"""Pureza dos módulos de domínio do lance e da fase do lote (Story 3.2, test-plan §9;
P9, D13): imports só da allowlist, nenhuma leitura de relógio, sem float nem divisão."""

import ast
from pathlib import Path

import pytest

import app.bid_integrity as bid_integrity
import app.bid_rules as bid_rules
import app.money as money

APP = Path(__file__).resolve().parents[1] / "app"
LOT_TIME = APP / "lot_time.py"
BID_RULES = APP / "bid_rules.py"
BID_INTEGRITY = APP / "bid_integrity.py"
DOMAIN_MODULES = [
    pytest.param(LOT_TIME, id="lot_time"),
    pytest.param(BID_RULES, id="bid_rules"),
    pytest.param(BID_INTEGRITY, id="bid_integrity"),
]

INFRASTRUCTURE = {
    "time",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "pydantic",
    "httpx",
    "psycopg",
    "app.db",
    "app.main",
    "app.lots",
    "app.wallet",
    "app.catalog",
    "app.artic",
    "app.errors",
    "app.users",
    "app.access",
}
CLOCK_NAMES = {
    "now",
    "utcnow",
    "today",
    "time",
    "time_ns",
    "monotonic",
    "monotonic_ns",
    "perf_counter",
    "perf_counter_ns",
    "fromtimestamp",
    "utcfromtimestamp",
    "clock_timestamp",
}


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def imported_names(path: Path, module: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            names.update(alias.name for alias in node.names)
    return names


def assigned_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def clock_calls(tree: ast.AST) -> list[str]:
    """Resolve imports simples para detectar relógios chamados ou referenciados."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"datetime", "time"}:
                    aliases[alias.asname or alias.name] = alias.name
        elif (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module in {"datetime", "time"}
        ):
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    def qualified_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return aliases.get(node.id)
        if isinstance(node, ast.Attribute):
            owner = qualified_name(node.value)
            if owner is not None:
                return f"{owner}.{node.attr}"
        return None

    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Name, ast.Attribute)) or not isinstance(
            node.ctx, ast.Load
        ):
            continue
        qualified = qualified_name(node)
        if qualified is None:
            continue
        owner, _, name = qualified.rpartition(".")
        if (
            owner in {"datetime.datetime", "datetime.date", "time"}
            and name in CLOCK_NAMES
        ):
            found.append(name)
    return found


def test_lot_time_imports_only_the_standard_library() -> None:
    assert imported_modules(LOT_TIME) <= {"datetime", "enum"}
    assert imported_names(LOT_TIME, "datetime") <= {"UTC", "datetime"}


def test_bid_rules_imports_only_the_allowed_modules() -> None:
    modules = imported_modules(BID_RULES)
    allowed = {"uuid", "dataclasses", "datetime", "enum", "app.money", "app.lot_time"}
    assert modules <= allowed
    assert {"app.money", "app.lot_time"} <= modules
    assert imported_names(BID_RULES, "datetime") <= {"UTC", "datetime", "timedelta"}


@pytest.mark.parametrize("path", DOMAIN_MODULES)
def test_domain_modules_avoid_infrastructure(path: Path) -> None:
    assert imported_modules(path) & INFRASTRUCTURE == set()


@pytest.mark.parametrize("path", DOMAIN_MODULES)
def test_domain_modules_never_read_a_clock(path: Path) -> None:
    assert clock_calls(parse(path)) == []


@pytest.mark.parametrize(
    "source",
    [
        "from datetime import datetime\nx = datetime.now()",
        "import time\ny = time.monotonic()",
        "from time import time\nz = time()",
        "from datetime import datetime\nx = datetime.utcnow()",
        "import time\nx = time.time()",
        "from dataclasses import field\n"
        "from datetime import datetime\nx = field(default_factory=datetime.now)",
        "from dataclasses import field\n"
        "from datetime import datetime\nx = field(default_factory=datetime.utcnow)",
        "from dataclasses import field\n"
        "import time\nx = field(default_factory=time.time)",
    ],
)
def test_clock_detector_detects_a_clock(source: str) -> None:
    assert clock_calls(ast.parse(source)) != []


@pytest.mark.parametrize("usage", ["{clock}()", "field(default_factory={clock})"])
@pytest.mark.parametrize(
    ("imports", "clock", "expected"),
    [
        ("import datetime", "datetime.datetime.now", "now"),
        ("import datetime", "datetime.datetime.utcnow", "utcnow"),
        ("import datetime as dt", "dt.datetime.now", "now"),
        ("import datetime as dt", "dt.datetime.utcnow", "utcnow"),
        ("from datetime import datetime", "datetime.now", "now"),
        ("from datetime import datetime", "datetime.utcnow", "utcnow"),
        ("from datetime import datetime as dt", "dt.now", "now"),
        ("from datetime import datetime as dt", "dt.utcnow", "utcnow"),
        ("import time", "time.time", "time"),
        ("import time as clock", "clock.time", "time"),
        ("from time import time as read_clock", "read_clock", "time"),
    ],
)
def test_clock_detector_resolves_import_aliases(
    imports: str, clock: str, expected: str, usage: str
) -> None:
    source = (
        f"from dataclasses import field\n{imports}\nvalue = {usage.format(clock=clock)}"
    )
    assert clock_calls(ast.parse(source)) == [expected]


def test_clock_detector_detects_dt_now_factory() -> None:
    source = (
        "from datetime import datetime as dt\n"
        "from dataclasses import field\n"
        "created_at = field(default_factory=dt.now)"
    )
    assert clock_calls(ast.parse(source)) == ["now"]


@pytest.mark.parametrize(
    "source",
    [
        "def evaluate(now):\n    return now",
        "def evaluate(eligible):\n    return eligible.now",
        "from datetime import UTC, datetime\nx = datetime(2026, 10, 26, tzinfo=UTC)",
        "from dataclasses import field\nx = field(default_factory=list)",
        "value = lot.starts_at\nend = result.ends_at",
        "value = datetime.now\nother = time.time\nlocal = dt.now",
        "def now():\n    return 42\nvalue = now()",
        "value = eligible.now()",
        "from other_module import datetime\nvalue = datetime.now()",
        "import other_module as time\nvalue = time.time()",
    ],
)
def test_clock_detector_preserves_valid_sources(source: str) -> None:
    assert clock_calls(ast.parse(source)) == []


@pytest.mark.parametrize("path", DOMAIN_MODULES)
def test_no_float_or_division_in_domain_modules(path: Path) -> None:
    for node in ast.walk(parse(path)):
        assert not (isinstance(node, ast.Name) and node.id == "float")
        assert not (isinstance(node, ast.Constant) and isinstance(node.value, float))
        assert not isinstance(node, ast.Div)


@pytest.mark.parametrize("path", DOMAIN_MODULES)
def test_domain_modules_do_not_redefine_max_cents(path: Path) -> None:
    assert "MAX_CENTS" not in assigned_names(path)


def test_bid_rules_uses_the_shared_money_ceiling() -> None:
    assert bid_rules.MAX_CENTS is money.MAX_CENTS


def test_bid_integrity_imports_only_the_allowed_modules() -> None:
    modules = imported_modules(BID_INTEGRITY)
    assert modules <= {
        "dataclasses",
        "datetime",
        "hashlib",
        "hmac",
        "json",
        "re",
        "uuid",
        "app.money",
        "app.lot_time",
    }
    assert {"app.money", "app.lot_time"} <= modules
    assert imported_names(BID_INTEGRITY, "app.money") == {"MAX_CENTS"}
    assert imported_names(BID_INTEGRITY, "app.lot_time") == {"require_aware"}
    for node in ast.walk(parse(BID_INTEGRITY)):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert all(alias.name != "*" for alias in node.names)


def forbidden_builtin_references(tree: ast.AST) -> list[str]:
    forbidden = {"open", "input", "__import__", "eval", "exec"}
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "builtins":
                    aliases[alias.asname or alias.name] = "builtins"
        elif isinstance(node, ast.ImportFrom) and node.module == "builtins":
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = aliases.get(node.id, node.id)
            if name in forbidden:
                found.append(name)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and isinstance(node.value, ast.Name)
            and aliases.get(node.value.id) == "builtins"
            and node.attr in forbidden
        ):
            found.append(node.attr)
    return found


@pytest.mark.parametrize("path", DOMAIN_MODULES)
def test_domain_modules_avoid_io_and_dynamic_execution(path: Path) -> None:
    assert forbidden_builtin_references(parse(path)) == []


@pytest.mark.parametrize("name", ["open", "input", "__import__", "eval", "exec"])
@pytest.mark.parametrize(
    "source",
    [
        "{name}('x')",
        "factory = {name}",
        "import builtins as b\nb.{name}('x')",
        "from builtins import {name} as f\nf('x')",
    ],
)
def test_builtin_detector_positive(name: str, source: str) -> None:
    assert forbidden_builtin_references(ast.parse(source.format(name=name))) == [name]


@pytest.mark.parametrize(
    "source",
    [
        "value = bid.timestamp",
        "result = require_aware('timestamp', value)",
        "value = json.dumps(payload)",
    ],
)
def test_builtin_detector_negative(source: str) -> None:
    assert forbidden_builtin_references(ast.parse(source)) == []


def test_bid_integrity_shared_constants() -> None:
    assert bid_integrity.MAX_CENTS is money.MAX_CENTS
    definitions = [
        node
        for node in ast.walk(parse(BID_INTEGRITY))
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "GENESIS_HASH" for t in node.targets
        )
    ]
    assert len(definitions) == 1
    # Uma única fonte produtiva dos zeros; validação de vazio/cadeia a consome.
    value = definitions[0].value
    assert isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult)
    assert isinstance(value.left, ast.Constant) and value.left.value == "0"
    assert isinstance(value.right, ast.Constant) and value.right.value == 64
    assert (
        sum(
            isinstance(node, ast.Name)
            and node.id == "GENESIS_HASH"
            and isinstance(node.ctx, ast.Load)
            for node in ast.walk(parse(BID_INTEGRITY))
        )
        >= 2
    )


# --- Story 3.4: `bids.py` compõe os primitives; ele mesmo não lê relógio ---


def test_bids_module_reads_no_clock_and_does_not_import_the_app_entrypoint() -> None:
    bids_py = APP / "bids.py"
    tree = parse(bids_py)

    # Sem allowlist de imports (não é módulo de domínio), mas sem relógio Python.
    assert clock_calls(tree) == []
    assert "app.main" not in imported_modules(bids_py)
    assert "time" not in imported_modules(bids_py)
    source = bids_py.read_text(encoding="utf-8")
    assert "clock_timestamp" not in source.replace("`clock_timestamp()`", "")
    assert "CURRENT_TIMESTAMP" not in source.upper()
