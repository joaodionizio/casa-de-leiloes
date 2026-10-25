"""A fixture do lote demo chega à imagem de produção e é coerente com a 2.3
(Story 2.4, CAP-9, test-plan §6). Sem banco."""

import fnmatch
import json
from pathlib import Path

from app.artic import IMAGE_ID_PATTERN
from app.catalog import _detail
from app.config import BACKEND_DIR
from app.lots import ArtworkSnapshot, snapshot_from_detail
from app.seed import (
    DEMO_ARTWORK_PATH,
    DEMO_AUCTIONEER_ID,
    SEED_USERS,
    load_demo_artwork,
)
from app.users import UserRole
from tests.catalog_support import FakeArtic, artic_client, json_response, load_fixture

REPO_ROOT = Path(BACKEND_DIR).parent
FIXTURE = Path(BACKEND_DIR) / "app" / "seed_data" / "demo_artwork.json"
SNAPSHOT_KEYS = {
    "external_id",
    "title",
    "artist_display",
    "date_display",
    "medium_display",
    "dimensions",
    "department_title",
    "artwork_type_title",
    "image_id",
    "credit_line",
    "source_url",
}


def test_the_fixture_lives_under_backend_app() -> None:
    assert DEMO_ARTWORK_PATH == FIXTURE
    assert FIXTURE.is_file()
    assert not (FIXTURE.parent / "__init__.py").exists()  # só dados, não é pacote


def test_the_fixture_has_exactly_the_snapshot_fields_and_validates() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert set(raw) == SNAPSHOT_KEYS
    snapshot = ArtworkSnapshot.model_validate(raw)
    assert snapshot == load_demo_artwork()
    assert snapshot.external_id == 27992
    assert IMAGE_ID_PATTERN.fullmatch(snapshot.image_id)


def test_the_fixture_has_no_personal_data() -> None:
    text = FIXTURE.read_text(encoding="utf-8").lower()

    assert "@" not in text
    assert "password" not in text


def test_the_fixture_matches_the_aic_test_fixture_of_story_2_3() -> None:
    fake = FakeArtic(lambda request: json_response(load_fixture("artwork_27992.json")))
    artwork = artic_client(fake).get_artwork(27992)
    assert artwork is not None and artwork.image_id is not None

    expected = snapshot_from_detail(_detail(artwork, artwork.image_id))

    assert load_demo_artwork() == expected


def test_the_production_image_copies_it_and_dockerignore_does_not_exclude_it() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY backend/app ./app" in dockerfile

    relative = "backend/app/seed_data/demo_artwork.json"
    parts = relative.split("/")
    candidates = {"/".join(parts[:index]) for index in range(1, len(parts) + 1)}
    for line in (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith("#") or pattern.startswith("!"):
            continue
        pattern = pattern.removeprefix("/")
        for candidate in candidates:
            assert not fnmatch.fnmatch(candidate, pattern), (pattern, candidate)
            assert not fnmatch.fnmatch(candidate, pattern.removeprefix("**/")), (
                pattern,
                candidate,
            )


def test_the_demo_auctioneer_is_the_seeded_auctioneer() -> None:
    auctioneers = [seed for seed in SEED_USERS if seed.role == UserRole.AUCTIONEER]

    assert [seed.id for seed in auctioneers] == [DEMO_AUCTIONEER_ID]
    assert str(DEMO_AUCTIONEER_ID) == "219e37a5-0def-4b26-87d4-b08668f7c112"
