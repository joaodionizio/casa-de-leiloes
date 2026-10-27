"""`GET /api/lots` e `GET /api/lots/{lot_id}` sobre PostgreSQL real (Story 2.5,
test-plan §3). Nenhum caso depende de espera ou de corrida: o instante é fixado por
`fixed_as_of` ou o ponto de concorrência é injetado por `before_public_read`."""

import re
import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import seed
from app.lots import public_snapshot_statement, read_public_snapshot
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    cookie_name_of,
    forge_token,
    json_headers,
    login,
    seed_demo_users,
    seeded_id,
)
from tests.catalog_support import FakeArtic, install, raising, standard_handler
from tests.lot_support import (
    IMAGE_ID,
    before_public_read,
    count_lots,
    db_now,
    fixed_as_of,
    insert_lot,
    integrity_secrets,
    lot_rows,
    normalized,
    statement_recorder,
)

URL = "/api/lots"
MICRO = timedelta(microseconds=1)
SUMMARY_KEYS = sorted(
    [
        "id",
        "title",
        "artist_display",
        "date_display",
        "image_url",
        "starting_bid_cents",
        "starts_at",
        "ends_at",
        "phase",
    ]
)
DETAIL_KEYS = sorted(
    SUMMARY_KEYS
    + [
        "external_id",
        "medium_display",
        "dimensions",
        "department_title",
        "artwork_type_title",
        "credit_line",
        "source_url",
        "min_increment_cents",
    ]
)
FORBIDDEN_KEYS = {
    "auctioneer_id",
    "is_demo",
    "created_at",
    "image_id",
    "email",
    "password_hash",
    "role",
    "status",
    "settlement_status",
}
LOCK_PATTERN = re.compile(
    r"\bFOR\s+(NO\s+KEY\s+UPDATE|UPDATE|KEY\s+SHARE|SHARE)\b|\bLOCK\b", re.IGNORECASE
)
WRITE_PATTERN = re.compile(r"\b(INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_demo_users(db_session_factory)
    return db_session_factory


@pytest.fixture
def auctioneer_id() -> uuid.UUID:
    return seeded_id(AUCTIONEER_EMAIL)


def client_for(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    email: str | None = None,
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    if email is not None:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


def keys_anywhere(value: Any) -> set[str]:
    """Todas as chaves de objeto em qualquer nível."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            found |= keys_anywhere(item)
    elif isinstance(value, list):
        for item in value:
            found |= keys_anywhere(item)
    return found


def all_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [*body["live"], *body["scheduled"], *body["ended"]]


def insert_phase_set(
    seeded: sessionmaker[Session], auctioneer_id: uuid.UUID, now: datetime
) -> dict[str, uuid.UUID]:
    """Um lote por fase, com margens de 1 h em torno de `now`."""
    return {
        "scheduled": insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=5),
        ),
        "live": insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
        ),
        "ended": insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            starts_at=now - timedelta(hours=5),
            ends_at=now - timedelta(hours=1),
        ),
    }


# --- vitrine: acesso e forma ---


def test_everyone_gets_the_same_body_for_the_same_database_and_instant(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    insert_phase_set(seeded, auctioneer_id, now)
    fixed_as_of(monkeypatch, now)

    anonymous = client_for(monkeypatch, seeded)
    bidder = client_for(monkeypatch, seeded, BIDDER_EMAIL)
    auctioneer = client_for(monkeypatch, seeded, AUCTIONEER_EMAIL)
    tampered = client_for(monkeypatch, seeded)
    tampered.cookies.set(
        cookie_name_of(tampered),
        forge_token(tampered, secret="outro-segredo-" + "x" * 40),
        domain="testserver",
    )
    expired = client_for(monkeypatch, seeded)
    expired.cookies.set(
        cookie_name_of(expired),
        forge_token(expired, issued_ago=timedelta(hours=9)),
        domain="testserver",
    )

    responses = [
        client.get(URL) for client in (anonymous, bidder, auctioneer, tampered, expired)
    ]

    assert [response.status_code for response in responses] == [200] * 5
    assert len({response.content for response in responses}) == 1


def test_an_empty_database_returns_as_of_and_three_empty_groups(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = client_for(monkeypatch, seeded)
    before = db_now(seeded)

    response = client.get(URL)

    after = db_now(seeded)
    body = response.json()
    assert response.status_code == 200
    assert sorted(body) == ["as_of", "ended", "live", "scheduled"]
    assert (body["live"], body["scheduled"], body["ended"]) == ([], [], [])
    assert body["as_of"].endswith("Z")
    as_of = datetime.fromisoformat(body["as_of"])
    assert before <= as_of <= after
    assert response.headers["cache-control"] == "no-store"


def test_every_lot_appears_in_exactly_one_group(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    ids = insert_phase_set(seeded, auctioneer_id, now)
    insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        starts_at=now - timedelta(hours=2),
        ends_at=now + timedelta(hours=9),
    )
    client = client_for(monkeypatch, seeded)

    body = client.get(URL).json()

    assert len(all_items(body)) == count_lots(seeded) == 4
    assert len({item["id"] for item in all_items(body)}) == 4
    assert str(ids["scheduled"]) in [item["id"] for item in body["scheduled"]]
    assert str(ids["ended"]) in [item["id"] for item in body["ended"]]
    assert str(ids["live"]) in [item["id"] for item in body["live"]]
    assert {item["phase"] for item in body["live"]} == {"live"}
    assert {item["phase"] for item in body["scheduled"]} == {"scheduled"}
    assert {item["phase"] for item in body["ended"]} == {"ended"}


def test_lots_of_two_auctioneers_all_appear(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    other = uuid.uuid4()
    with seeded() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, 'segundo@example.com', 'h', 'AUCTIONEER')"
            ),
            {"id": other},
        )
        session.commit()
    first = insert_lot(seeded, auctioneer_id=auctioneer_id)
    second = insert_lot(seeded, auctioneer_id=other)
    client = client_for(monkeypatch, seeded)

    ids = {item["id"] for item in client.get(URL).json()["live"]}

    assert ids == {str(first), str(second)}


def test_vitrine_items_have_exactly_the_contract_keys_and_values(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    lot_id = insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        title=None,
        artist_display="Artista\nDois",
        date_display="1884",
        starting_bid_cents=9_007_199_254_740_991,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
    )
    client = client_for(monkeypatch, seeded)

    response = client.get(URL)

    body = response.json()
    assert sorted(body) == ["as_of", "ended", "live", "scheduled"]
    (item,) = body["live"]
    assert sorted(item) == SUMMARY_KEYS
    assert item["id"] == str(lot_id)
    assert item["title"] is None
    assert item["artist_display"] == "Artista\nDois"
    assert item["date_display"] == "1884"
    assert item["starting_bid_cents"] == 9_007_199_254_740_991
    assert item["image_url"] == f"/api/catalog/images/{IMAGE_ID}"
    assert item["starts_at"].endswith("Z")
    assert item["ends_at"].endswith("Z")
    assert item["phase"] == "live"
    assert response.headers["cache-control"] == "no-store"


def test_nothing_internal_is_exposed_anywhere(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    lot_id = insert_lot(seeded, auctioneer_id=auctioneer_id, is_demo=True)
    insert_phase_set(seeded, auctioneer_id, now)
    client = client_for(monkeypatch, seeded, BIDDER_EMAIL)

    listing = client.get(URL)
    detail = client.get(f"{URL}/{lot_id}")

    assert FORBIDDEN_KEYS.isdisjoint(keys_anywhere(listing.json()))
    assert FORBIDDEN_KEYS.isdisjoint(keys_anywhere(detail.json()))
    for forbidden in (BIDDER_EMAIL, AUCTIONEER_EMAIL, str(auctioneer_id), IMAGE_ID):
        # O `image_id` só aparece embutido em `image_url`, nunca como valor solto.
        if forbidden == IMAGE_ID:
            assert f'"{IMAGE_ID}"' not in listing.text
            assert f'"{IMAGE_ID}"' not in detail.text
        else:
            assert forbidden not in listing.text
            assert forbidden not in detail.text


def test_the_seeded_demo_lot_appears_live_like_a_manual_lot(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    with seeded() as session:
        seed.run_seed(session, audit_hmac_secret=integrity_secrets()[0])
        session.commit()
    manual = insert_lot(seeded, auctioneer_id=auctioneer_id)
    old_demo = insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        is_demo=True,
        starts_at=db_now(seeded) - timedelta(days=9),
        ends_at=db_now(seeded) - timedelta(days=6),
    )
    before = lot_rows(seeded)
    client = client_for(monkeypatch, seeded)

    body = client.get(URL).json()

    live_ids = {item["id"] for item in body["live"]}
    demo = next(item for item in body["live"] if item["id"] != str(manual))
    manual_item = next(item for item in body["live"] if item["id"] == str(manual))
    assert str(manual) in live_ids
    assert sorted(demo) == sorted(manual_item) == SUMMARY_KEYS
    assert [item["id"] for item in body["ended"]] == [str(old_demo)]
    assert body["ended"][0]["phase"] == "ended"
    assert lot_rows(seeded) == before  # o demo vencido segue intocado


# --- instante, snapshot e fase (P2 refinada, D1) ---


def test_phase_boundaries_use_one_fixed_instant_through_http(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    hour = timedelta(hours=1)
    expected = {
        insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            starts_at=now + MICRO,
            ends_at=now + hour,
        ): "scheduled",
        insert_lot(
            seeded, auctioneer_id=auctioneer_id, starts_at=now, ends_at=now + hour
        ): "live",
        insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            starts_at=now - hour,
            ends_at=now + MICRO,
        ): "live",
        insert_lot(
            seeded, auctioneer_id=auctioneer_id, starts_at=now - hour, ends_at=now
        ): "ended",
        insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            starts_at=now - hour,
            ends_at=now - MICRO,
        ): "ended",
    }
    fixed_as_of(monkeypatch, now)
    client = client_for(monkeypatch, seeded)

    body = client.get(URL).json()

    assert datetime.fromisoformat(body["as_of"]) == now
    assert {item["id"]: item["phase"] for item in all_items(body)} == {
        str(lot_id): phase for lot_id, phase in expected.items()
    }


def test_the_sql_returns_one_distinct_as_of_for_all_rows(
    seeded: sessionmaker[Session], auctioneer_id: uuid.UUID
) -> None:
    for _ in range(20):
        insert_lot(seeded, auctioneer_id=auctioneer_id)

    before = db_now(seeded)
    with seeded() as session:
        rows = session.execute(public_snapshot_statement()).all()
        session.rollback()
        as_of, lots = read_public_snapshot(session)
        session.rollback()
    after = db_now(seeded)

    # Cada execução avalia o relógio uma vez e o repete nas 20 linhas.
    assert len(rows) == 20
    assert len({row.as_of for row in rows}) == 1
    assert before <= rows[0].as_of.astimezone(UTC) <= as_of <= after
    assert len(lots) == 20


@pytest.mark.parametrize("target", ["list", "detail"])
def test_each_route_runs_exactly_one_statement_with_one_clock(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
    db_engine: Engine,
    target: str,
) -> None:
    lot_id = insert_lot(seeded, auctioneer_id=auctioneer_id)
    path = URL if target == "list" else f"{URL}/{lot_id}"
    # Autenticado: mesmo com sessão, a rota pública só faz a leitura.
    client = client_for(monkeypatch, seeded, BIDDER_EMAIL)

    with statement_recorder(db_engine) as recorder:
        assert client.get(path).status_code == 200

    (statement,) = [normalized(sql) for sql in recorder.statements]
    assert statement.startswith("WITH clock AS MATERIALIZED")
    assert statement.count("clock_timestamp") == 1
    assert "FROM clock LEFT OUTER JOIN lots ON" in statement
    assert " ORDER BY " not in statement
    assert " LIMIT " not in statement.upper()
    assert " WHERE " not in statement


def test_an_empty_database_still_has_as_of_from_the_single_row_of_the_join(
    seeded: sessionmaker[Session],
) -> None:
    with seeded() as session:
        as_of, found = read_public_snapshot(session)
        session.rollback()

    assert found == []
    assert as_of.tzinfo is not None


def test_a_missing_lot_still_runs_the_single_read_and_answers_404(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    client = client_for(monkeypatch, seeded)

    with statement_recorder(db_engine) as recorder:
        response = client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert len(recorder.statements) == 1
    assert normalized(recorder.statements[0]).startswith("WITH clock AS MATERIALIZED")


def commit_live_lot(
    engine: Engine, lot_id: uuid.UUID, owner: uuid.UUID, *, commit: bool
) -> Any:
    """Insere um lote numa conexão própria, com `starts_at` e `created_at` no
    `clock_timestamp()` dela. Devolve a conexão quando não confirma."""
    connection = engine.connect()
    connection.execute(
        text(
            "INSERT INTO lots (id, auctioneer_id, external_id, image_id, source_url, "
            "starting_bid_cents, min_increment_cents, starts_at, ends_at, created_at) "
            "VALUES (:id, :owner, 27992, :image, "
            "'https://www.artic.edu/artworks/27992', 10000, 1000, "
            "clock_timestamp(), clock_timestamp() + interval '2 hours', "
            "clock_timestamp())"
        ),
        {"id": lot_id, "owner": owner, "image": IMAGE_ID},
    )
    if commit:
        connection.commit()
        connection.close()
        return None
    return connection


def test_a_lot_committed_just_before_the_read_enters_with_created_at_before_as_of(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
    db_engine: Engine,
) -> None:
    newcomer = uuid.uuid4()
    client = client_for(monkeypatch, seeded)

    with before_public_read(
        db_engine,
        lambda: commit_live_lot(db_engine, newcomer, auctioneer_id, commit=True),
    ):
        body = client.get(URL).json()

    as_of = datetime.fromisoformat(body["as_of"])
    assert [item["id"] for item in body["live"]] == [str(newcomer)]
    assert body["live"][0]["phase"] == "live"
    with seeded() as session:
        created = session.execute(
            text("SELECT created_at, starts_at FROM lots WHERE id = :id"),
            {"id": newcomer},
        ).one()
    assert created.created_at <= as_of
    assert created.starts_at <= as_of


def test_the_detail_of_a_lot_committed_just_before_the_read_sees_it(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
    db_engine: Engine,
) -> None:
    newcomer = uuid.uuid4()
    client = client_for(monkeypatch, seeded)

    with before_public_read(
        db_engine,
        lambda: commit_live_lot(db_engine, newcomer, auctioneer_id, commit=True),
    ):
        response = client.get(f"{URL}/{newcomer}")

    assert response.status_code == 200
    body = response.json()
    assert body["lot"]["phase"] == "live"
    assert datetime.fromisoformat(body["lot"]["starts_at"]) <= datetime.fromisoformat(
        body["as_of"]
    )


def test_an_uncommitted_lot_does_not_enter_and_does_not_block(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
    db_engine: Engine,
) -> None:
    pending = uuid.uuid4()
    held: list[Any] = []
    client = client_for(monkeypatch, seeded)

    def hold() -> None:
        held.append(commit_live_lot(db_engine, pending, auctioneer_id, commit=False))

    try:
        with before_public_read(db_engine, hold):
            response = client.get(URL)
    finally:
        for connection in held:
            connection.rollback()
            connection.close()

    assert response.status_code == 200
    assert all_items(response.json()) == []


def test_negative_control_two_queries_would_show_a_lot_created_after_as_of(
    seeded: sessionmaker[Session], auctioneer_id: uuid.UUID, db_engine: Engine
) -> None:
    """Prova que o teste de snapshot detectaria a versão de duas consultas (a que a
    spec descartou). Escrita só aqui, no teste: nenhuma função de produção é usada."""
    newcomer = uuid.uuid4()
    with seeded() as session:
        as_of = session.execute(text("SELECT clock_timestamp()")).scalar_one()
        commit_live_lot(db_engine, newcomer, auctioneer_id, commit=True)
        created_at = session.execute(
            text("SELECT created_at FROM lots WHERE id = :id"), {"id": newcomer}
        ).scalar_one()
        session.rollback()

    assert created_at > as_of


def test_the_real_path_classifies_with_margins_around_the_database_clock(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    ids = insert_phase_set(seeded, auctioneer_id, now)
    client = client_for(monkeypatch, seeded)
    before = db_now(seeded)

    body = client.get(URL).json()

    after = db_now(seeded)
    assert before <= datetime.fromisoformat(body["as_of"]) <= after
    assert [item["id"] for item in body["scheduled"]] == [str(ids["scheduled"])]
    assert [item["id"] for item in body["live"]] == [str(ids["live"])]
    assert [item["id"] for item in body["ended"]] == [str(ids["ended"])]


# --- ordenação (P4, D3) ---


def lot_ids_in_order(*values: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=value) for value in values]


def test_each_group_is_ordered_and_ties_break_by_id_ascending(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    hour = timedelta(hours=1)
    a, b, c, d, e, f = lot_ids_in_order(1, 2, 3, 4, 5, 6)
    # Ao vivo: b e c empatam em ends_at (b antes por id), a termina depois, d antes.
    for lot_id, ends in [(a, 5), (c, 3), (b, 3), (d, 1)]:
        insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            id=lot_id,
            starts_at=now - hour,
            ends_at=now + ends * hour,
        )
    # Agendados: e e f empatam em starts_at.
    for lot_id, starts in [(f, 2), (e, 2)]:
        insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            id=lot_id,
            starts_at=now + starts * hour,
            ends_at=now + 9 * hour,
        )
    ended_old, ended_new_b, ended_new_a = lot_ids_in_order(10, 12, 11)
    insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        id=ended_old,
        starts_at=now - 9 * hour,
        ends_at=now - 5 * hour,
    )
    for lot_id in (ended_new_b, ended_new_a):
        insert_lot(
            seeded,
            auctioneer_id=auctioneer_id,
            id=lot_id,
            starts_at=now - 9 * hour,
            ends_at=now - 2 * hour,
        )
    client = client_for(monkeypatch, seeded)

    body = client.get(URL).json()

    assert [item["id"] for item in body["live"]] == [str(x) for x in (d, b, c, a)]
    assert [item["id"] for item in body["scheduled"]] == [str(x) for x in (e, f)]
    assert [item["id"] for item in body["ended"]] == [
        str(ended_new_a),
        str(ended_new_b),
        str(ended_old),
    ]
    # O destaque é o primeiro ao vivo (o que termina primeiro).
    assert body["live"][0]["id"] == str(d)


def test_without_live_lots_the_first_scheduled_is_the_next_to_start(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    later = insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        starts_at=now + timedelta(hours=5),
        ends_at=now + timedelta(hours=9),
    )
    sooner = insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        starts_at=now + timedelta(hours=2),
        ends_at=now + timedelta(hours=9),
    )
    client = client_for(monkeypatch, seeded)

    body = client.get(URL).json()

    assert body["live"] == []
    assert [item["id"] for item in body["scheduled"]] == [str(sooner), str(later)]


# --- detalhe ---


def test_detail_is_the_same_for_every_role(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    lot_id = insert_lot(seeded, auctioneer_id=auctioneer_id)
    fixed_as_of(monkeypatch, now)

    responses = [
        client_for(monkeypatch, seeded, email).get(f"{URL}/{lot_id}")
        for email in (None, BIDDER_EMAIL, OTHER_BIDDER_EMAIL, AUCTIONEER_EMAIL)
    ]

    assert [response.status_code for response in responses] == [200] * 4
    assert len({response.content for response in responses}) == 1


def test_detail_has_the_17_keys_and_the_values_of_the_row(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    lot_id = insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        title="A Sunday on La Grande Jatte — 1884",
        artist_display="Georges Seurat\n(French, 1859–1891)",
        date_display="1884–86",
        medium_display="Oil on canvas",
        dimensions="207.5 × 308.1 cm",
        department_title="Painting and Sculpture of Europe",
        artwork_type_title="Painting",
        credit_line="Helen Birch Bartlett Memorial Collection",
        starting_bid_cents=10_000,
        min_increment_cents=1_000,
    )
    client = client_for(monkeypatch, seeded)

    response = client.get(f"{URL}/{lot_id}")

    body = response.json()
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert sorted(body) == ["as_of", "lot"]
    lot = body["lot"]
    assert sorted(lot) == DETAIL_KEYS
    assert len(lot) == 17
    assert lot["id"] == str(lot_id)
    assert lot["external_id"] == 27992
    assert lot["title"] == "A Sunday on La Grande Jatte — 1884"
    assert lot["artist_display"] == "Georges Seurat\n(French, 1859–1891)"
    assert lot["medium_display"] == "Oil on canvas"
    assert lot["dimensions"] == "207.5 × 308.1 cm"
    assert lot["department_title"] == "Painting and Sculpture of Europe"
    assert lot["artwork_type_title"] == "Painting"
    assert lot["credit_line"] == "Helen Birch Bartlett Memorial Collection"
    assert lot["source_url"] == "https://www.artic.edu/artworks/27992"
    assert lot["starting_bid_cents"] == 10_000
    assert lot["min_increment_cents"] == 1_000
    assert lot["image_url"] == f"/api/catalog/images/{IMAGE_ID}"
    assert FORBIDDEN_KEYS.isdisjoint(keys_anywhere(body))


def test_detail_phase_follows_the_fixed_instant(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    ids = insert_phase_set(seeded, auctioneer_id, now)
    fixed_as_of(monkeypatch, now)
    client = client_for(monkeypatch, seeded)

    phases = {
        name: client.get(f"{URL}/{lot_id}").json()["lot"]["phase"]
        for name, lot_id in ids.items()
    }

    assert phases == {"scheduled": "scheduled", "live": "live", "ended": "ended"}


def test_a_valid_unknown_uuid_is_404_with_the_exact_body_and_no_store(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = client_for(monkeypatch, seeded)

    response = client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "status": 404,
        "code": "not_found",
        "message": "Recurso não encontrado.",
    }
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "bad_id", ["abc", "mine-x", "123", "2d484387-2509-5e8e-2c43-22f9981972e"]
)
def test_a_malformed_lot_id_is_422_without_touching_the_database(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    bad_id: str,
) -> None:
    client = client_for(monkeypatch, seeded)

    with statement_recorder(db_engine) as recorder:
        response = client.get(f"{URL}/{bad_id}")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"] == [{"loc": ["path", "lot_id"], "type": "uuid_parsing"}]
    assert recorder.statements == []


# --- leitura pura e sem trava (AD-19, CA4) ---


@pytest.mark.parametrize("target", ["list", "detail"])
def test_public_reads_are_pure_selects_without_locks(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
    db_engine: Engine,
    target: str,
) -> None:
    now = db_now(seeded)
    insert_phase_set(seeded, auctioneer_id, now)
    expired = insert_lot(
        seeded,
        auctioneer_id=auctioneer_id,
        is_demo=True,
        starts_at=now - timedelta(days=5),
        ends_at=now - timedelta(days=2),
    )
    path = URL if target == "list" else f"{URL}/{expired}"
    client = client_for(monkeypatch, seeded)
    rows_before = lot_rows(seeded)
    count_before = count_lots(seeded)
    run_seed = mock.Mock(side_effect=AssertionError("o seed não pode rodar"))
    monkeypatch.setattr(seed, "run_seed", run_seed)

    with statement_recorder(db_engine) as recorder:
        response = client.get(path)

    assert response.status_code == 200
    (statement,) = [normalized(sql) for sql in recorder.statements]
    assert statement.startswith("WITH clock AS MATERIALIZED")
    assert statement.split(" ", 1)[0].upper() == "WITH"
    assert WRITE_PATTERN.search(statement) is None
    assert LOCK_PATTERN.search(statement) is None
    assert lot_rows(seeded) == rows_before
    assert count_lots(seeded) == count_before
    run_seed.assert_not_called()


def test_a_row_lock_and_an_uncommitted_update_do_not_block_the_reads(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
    db_engine: Engine,
) -> None:
    lot_id = insert_lot(seeded, auctioneer_id=auctioneer_id, title="CONFIRMADO")
    client = client_for(monkeypatch, seeded)
    results: dict[str, httpx.Response] = {}

    def read(name: str, path: str) -> None:
        results[name] = client.get(path)

    holder = db_engine.connect()
    try:
        holder.execute(
            text("SELECT id FROM lots WHERE id = :id FOR UPDATE"), {"id": lot_id}
        )
        holder.execute(
            text("UPDATE lots SET title = 'NAO CONFIRMADO' WHERE id = :id"),
            {"id": lot_id},
        )
        threads = [
            threading.Thread(target=read, args=("list", URL)),
            threading.Thread(target=read, args=("detail", f"{URL}/{lot_id}")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            # Rede de segurança: a asserção é "terminou", não "foi rápido".
            thread.join(timeout=5)
        finished = [not thread.is_alive() for thread in threads]
    finally:
        holder.rollback()
        holder.close()

    assert finished == [True, True]
    assert results["list"].status_code == results["detail"].status_code == 200
    assert results["list"].json()["live"][0]["title"] == "CONFIRMADO"
    assert results["detail"].json()["lot"]["title"] == "CONFIRMADO"


def test_no_connection_is_left_idle_in_transaction_after_the_reads(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    lot_id = insert_lot(seeded, auctioneer_id=auctioneer_id)
    client = client_for(monkeypatch, seeded)

    assert client.get(URL).status_code == 200
    assert client.get(f"{URL}/{lot_id}").status_code == 200
    assert client.get(f"{URL}/{uuid.uuid4()}").status_code == 404

    with seeded() as session:
        idle = session.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() "
                "AND state = 'idle in transaction' AND pid <> pg_backend_pid()"
            )
        ).scalar_one()
        session.rollback()
    assert idle == 0


@pytest.mark.parametrize("target", ["list", "detail", "missing"])
def test_the_handler_ends_the_read_transaction_before_the_session_closes(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
    target: str,
) -> None:
    lot_id = insert_lot(seeded, auctioneer_id=auctioneer_id)
    path = {
        "list": URL,
        "detail": f"{URL}/{lot_id}",
        "missing": f"{URL}/{uuid.uuid4()}",
    }[target]
    client = client_for(monkeypatch, seeded)
    events: list[str] = []
    real_rollback = Session.rollback

    def spy(self: Session) -> None:
        events.append("rollback")
        real_rollback(self)

    def override_session() -> Any:
        with seeded() as session:
            yield session
            events.append("teardown")

    from app.db import get_session

    monkeypatch.setattr(Session, "rollback", spy)
    client.app.dependency_overrides[get_session] = override_session  # type: ignore[attr-defined]

    client.get(path)

    # O handler chama `rollback` antes de a dependência encerrar a sessão.
    assert events.index("rollback") < events.index("teardown")


# --- sem AIC (CA7) ---


def test_public_reads_never_touch_the_catalog_client(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    now = db_now(seeded)
    ids = insert_phase_set(seeded, auctioneer_id, now)
    fixed_as_of(monkeypatch, now)
    healthy = FakeArtic(standard_handler)
    failing = FakeArtic(
        raising(lambda request: httpx.ConnectError("x", request=request))
    )
    paths = [URL, *(f"{URL}/{lot_id}" for lot_id in ids.values())]

    bodies = []
    for fake in (healthy, failing):
        client = client_for(monkeypatch, seeded)
        install(client.app, fake)  # type: ignore[arg-type]
        bodies.append([client.get(path).content for path in paths])

    assert bodies[0] == bodies[1]
    assert healthy.requests == []
    assert failing.requests == []


def test_public_routes_do_not_depend_on_the_catalog_dependency() -> None:
    from fastapi.routing import APIRoute

    from app.catalog import get_artic_client
    from app.main import app

    def dependency_callables(route: APIRoute) -> set[Any]:
        stack = [route.dependant]
        found: set[Any] = set()
        while stack:
            dependant = stack.pop()
            found.add(dependant.call)
            stack.extend(dependant.dependencies)
        return found

    routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path in (URL, "/api/lots/{lot_id}")
        and "GET" in route.methods
    ]
    assert len(routes) == 2
    for route in routes:
        assert get_artic_client not in dependency_callables(route)


# --- rotas vizinhas e métodos ---


def test_mine_is_registered_before_the_lot_id_route() -> None:
    from app.main import app

    paths = [getattr(route, "path", "") for route in app.routes]

    assert paths.index("/api/lots/mine") < paths.index("/api/lots/{lot_id}")


def test_mine_is_not_captured_by_the_public_detail_route(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    mine = insert_lot(seeded, auctioneer_id=auctioneer_id)
    other = uuid.uuid4()
    with seeded() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, 'segundo@example.com', 'h', 'AUCTIONEER')"
            ),
            {"id": other},
        )
        session.commit()
    insert_lot(seeded, auctioneer_id=other)

    anonymous = client_for(monkeypatch, seeded).get("/api/lots/mine")
    bidder = client_for(monkeypatch, seeded, BIDDER_EMAIL).get("/api/lots/mine")
    owner = client_for(monkeypatch, seeded, AUCTIONEER_EMAIL).get("/api/lots/mine")

    assert anonymous.status_code == 401
    assert bidder.status_code == 403
    assert owner.status_code == 200
    assert [item["id"] for item in owner.json()["items"]] == [str(mine)]


def test_collection_and_item_do_not_accept_writes_other_than_the_creation(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer_id: uuid.UUID,
) -> None:
    lot_id = insert_lot(seeded, auctioneer_id=auctioneer_id)
    before = lot_rows(seeded)
    client = client_for(monkeypatch, seeded, AUCTIONEER_EMAIL)
    headers = json_headers(HTTPS_ORIGIN)

    statuses = [
        client.put(URL, json={}, headers=headers).status_code,
        client.delete(URL, headers=headers).status_code,
        client.put(f"{URL}/{lot_id}", json={}, headers=headers).status_code,
        client.delete(f"{URL}/{lot_id}", headers=headers).status_code,
        client.head(URL).status_code,
        client.options(URL).status_code,
        client.head(f"{URL}/{lot_id}").status_code,
        client.options(f"{URL}/{lot_id}").status_code,
    ]

    assert statuses == [405] * 8
    assert lot_rows(seeded) == before
