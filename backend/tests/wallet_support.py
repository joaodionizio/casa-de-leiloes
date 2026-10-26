"""Apoio dos testes da carteira (Story 3.1): usuários com carteira, leitura e escrita
diretas por SQL e a sincronização dos testes de concorrência. Dinheiro sempre como
parâmetro inteiro, nunca `float`."""

import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.seed import seed_users
from app.wallet import ensure_wallets


def seed_users_with_wallets(factory: sessionmaker[Session]) -> None:
    """Os três usuários semeados, cada um com a sua carteira zerada. O
    `seed_demo_users` da 2.2 continua só com usuários (D11)."""
    with factory() as session:
        seed_users(session)
        ensure_wallets(session)
        session.commit()


def wallet_row(
    factory: sessionmaker[Session], user_id: uuid.UUID
) -> tuple[int, int] | None:
    """`(total, committed)` da carteira, ou `None` se ela não existe."""
    with factory() as session:
        row = session.execute(
            text(
                "SELECT total_balance_cents, committed_balance_cents "
                "FROM wallets WHERE user_id = :id"
            ),
            {"id": user_id},
        ).one_or_none()
    return None if row is None else (row[0], row[1])


def wallet_rows(factory: sessionmaker[Session]) -> list[tuple]:
    with factory() as session:
        return [
            tuple(row)
            for row in session.execute(
                text(
                    "SELECT user_id, total_balance_cents, committed_balance_cents "
                    "FROM wallets ORDER BY user_id"
                )
            )
        ]


def set_wallet(
    factory: sessionmaker[Session], user_id: uuid.UUID, total: int, committed: int = 0
) -> None:
    """Estado que a API não cria (saldo perto do teto, comprometido > 0)."""
    with factory() as session:
        session.execute(
            text(
                "UPDATE wallets SET total_balance_cents = :total, "
                "committed_balance_cents = :committed WHERE user_id = :id"
            ),
            {"id": user_id, "total": total, "committed": committed},
        )
        session.commit()


def delete_wallet(factory: sessionmaker[Session], user_id: uuid.UUID) -> None:
    with factory() as session:
        session.execute(
            text("DELETE FROM wallets WHERE user_id = :id"), {"id": user_id}
        )
        session.commit()


# --- concorrência ---


class LockAttempt:
    """Avisa quando a segunda transação está prestes a ler a carteira.

    Conta os `SELECT` da tabela `wallets` do engine desde que o observador foi ligado,
    o que acontece depois de A já segurar a trava: o próximo é o de B. Não exige
    `FOR UPDATE` de propósito: sem a trava no código, B lê o saldo antigo e o teste
    falha pelo estado final, não por este passo. O aviso sai do evento
    `before_cursor_execute` (antes de o statement ir ao servidor), então vale para a
    thread de B e para o threadpool do `TestClient`.
    """

    def __init__(self, expected: int = 1) -> None:
        self.expected = expected
        self.seen = 0
        self.reached = threading.Event()
        self._lock = threading.Lock()

    def __call__(self, conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        normalized = statement.lstrip().upper()
        if not normalized.startswith("SELECT") or "WALLETS" not in normalized:
            return
        with self._lock:
            self.seen += 1
            if self.seen >= self.expected:
                self.reached.set()


@contextmanager
def watch_lock_attempt(engine: Engine, expected: int = 1) -> Iterator[LockAttempt]:
    attempt = LockAttempt(expected)
    event.listen(engine, "before_cursor_execute", attempt)
    try:
        yield attempt
    finally:
        event.remove(engine, "before_cursor_execute", attempt)


def someone_is_waiting_for_a_lock(engine: Engine) -> bool:
    """Evidência auxiliar de que B está mesmo esperando a trava: um backend **deste
    banco** (não o de dev nem outro do mesmo servidor), que não é esta conexão de
    observação, bloqueado por outra sessão (`pg_blocking_pids`). A prova de correção
    dos testes é o estado final, não esta consulta."""
    with engine.connect() as connection:
        waiting = connection.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() "
                "AND pid <> pg_backend_pid() "
                "AND cardinality(pg_blocking_pids(pid)) > 0"
            )
        ).scalar_one()
        connection.rollback()
    return waiting > 0


def wait_for_blocked_lock(engine: Engine, timeout: float = 10.0) -> bool:
    """Espera até `timeout` s a evidência de que alguém está bloqueado em trava.
    Devolve se a viu; não levanta, para o teste decidir o que fazer."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if someone_is_waiting_for_a_lock(engine):
            return True
        time.sleep(0.02)
    return False


def naive_deposit(
    factory: sessionmaker[Session],
    user_id: uuid.UUID,
    amount: int,
    barrier: threading.Barrier,
) -> None:
    """O padrão inseguro, só para o controle negativo: lê fora da trava, espera a
    outra thread ler também, soma em Python e grava o valor absoluto. Nunca é usado
    pelo código de produção."""
    with factory() as session:
        read = session.execute(
            text("SELECT total_balance_cents FROM wallets WHERE user_id = :id"),
            {"id": user_id},
        ).scalar_one()
        barrier.wait(timeout=10)
        session.execute(
            text("UPDATE wallets SET total_balance_cents = :total WHERE user_id = :id"),
            {"id": user_id, "total": read + amount},
        )
        session.commit()
