import pytest

from tests.db_guard import UnsafeTestDatabaseError, assert_safe_test_target

DEV = "postgresql://u:p@localhost:5432/casa_de_leiloes_dev"
TEST = "postgresql://u:p@localhost:5432/casa_de_leiloes_test"


def test_accepts_distinct_test_database_and_normalizes() -> None:
    result = assert_safe_test_target(TEST, DEV)
    assert result.startswith("postgresql+psycopg://")


@pytest.mark.parametrize("missing", [None, ""])
def test_aborts_when_test_url_is_missing(missing: str | None) -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="TEST_DATABASE_URL is not set"):
        assert_safe_test_target(missing, DEV)


def test_aborts_when_test_url_equals_dev_url() -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="equal to DATABASE_URL"):
        assert_safe_test_target(DEV, DEV)


def test_aborts_when_urls_differ_only_by_driver_spelling() -> None:
    same = "postgresql+psycopg://u:p@localhost:5432/casa_de_leiloes_dev"
    with pytest.raises(UnsafeTestDatabaseError, match="equal to DATABASE_URL"):
        assert_safe_test_target(same, DEV)


def test_aborts_when_database_name_has_no_test_suffix() -> None:
    url = "postgresql://u:secret-pw@localhost:5432/casa_de_leiloes_prod"
    with pytest.raises(UnsafeTestDatabaseError) as error:
        assert_safe_test_target(url, DEV)
    assert "secret-pw" not in str(error.value)
