"""T35/T36: execute the production shell with command shims, without env files."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("fail", ["", "alembic", "python"])
def test_t35_t36_migration_seed_server_order_and_fail_fast(tmp_path, fail):
    commands = tmp_path / "commands"
    commands.mkdir()
    log = tmp_path / "order.log"
    for name in ("alembic", "python", "uvicorn"):
        shim = commands / name
        shim.write_text(
            "#!/bin/sh\n"
            'name="${0##*/}"\n'
            'printf "%s %s\\n" "$name" "$*" >> "$ORDER_LOG"\n'
            '[ "$name" != "$FAIL_COMMAND" ]\n'
        )
        shim.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{commands}:/usr/bin:/bin",
        "ORDER_LOG": str(log),
        "FAIL_COMMAND": fail,
    }
    script = Path(__file__).resolve().parents[1] / "scripts/start.sh"
    result = subprocess.run(["/bin/sh", str(script)], env=env, capture_output=True)
    lines = log.read_text().splitlines()
    expected = [
        "alembic upgrade head",
        "python -m app.seed",
        "uvicorn app.main:app --host 0.0.0.0 --port 8000",
    ]
    assert lines == expected[: {"alembic": 1, "python": 2, "": 3}[fail]]
    assert (result.returncode == 0) == (not fail)
