"""Login e logout continuam sob a proteção de escrita da 2.1 (Story 2.2, CAP-8)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tests.auth_support import HTTPS_ORIGIN, build_client

LOGIN = "/api/auth/login"
LOGOUT = "/api/auth/logout"
BODY = {"email": "bidder1@example.com", "password": "Demo123!"}


class RecordingSession:
    """Conta quantas sessões o handler abriu. `scalar` devolve `None`: usuário
    inexistente, ou seja, 401 `invalid_credentials` quando o handler roda."""

    opened = 0

    def scalar(self, *args: object, **kwargs: object) -> None:
        return None


@pytest.fixture
def recorder() -> type[RecordingSession]:
    RecordingSession.opened = 0
    return RecordingSession


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, recorder: type[RecordingSession]
) -> TestClient:
    def session_dependency() -> Iterator[RecordingSession]:
        recorder.opened += 1
        yield recorder()

    return build_client(
        monkeypatch, HTTPS_ORIGIN, session_dependency=session_dependency
    )


def assert_no_session_effects(response, recorder: type[RecordingSession]) -> None:
    assert "set-cookie" not in response.headers
    assert not any(h.startswith("access-control-") for h in response.headers)
    assert recorder.opened == 0


def test_control_valid_request_reaches_the_handler(
    client: TestClient, recorder: type[RecordingSession]
) -> None:
    response = client.post(LOGIN, json=BODY, headers={"Origin": HTTPS_ORIGIN})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert recorder.opened == 1


@pytest.mark.parametrize("path", [LOGIN, LOGOUT])
@pytest.mark.parametrize(
    "headers, code",
    [
        ({"Origin": "https://evil.example"}, "csrf_origin_mismatch"),
        ({}, "csrf_origin_missing"),
        ({"Referer": "https://evil.example/page"}, "csrf_origin_mismatch"),
        ({"Origin": "null"}, "csrf_origin_mismatch"),
    ],
)
def test_foreign_or_missing_origin_is_403(
    client: TestClient,
    recorder: type[RecordingSession],
    path: str,
    headers: dict[str, str],
    code: str,
) -> None:
    response = client.post(
        path,
        content='{"email":"a","password":"b"}',
        headers={**headers, "Content-Type": "application/json"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == code
    assert_no_session_effects(response, recorder)


@pytest.mark.parametrize("path", [LOGIN, LOGOUT])
@pytest.mark.parametrize(
    "content_type", [None, "text/plain", "application/x-www-form-urlencoded"]
)
def test_without_json_content_type_is_415(
    client: TestClient,
    recorder: type[RecordingSession],
    path: str,
    content_type: str | None,
) -> None:
    headers = {"Origin": HTTPS_ORIGIN}
    if content_type:
        headers["Content-Type"] = content_type

    response = client.post(path, content=b"x=1", headers=headers)

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"
    assert_no_session_effects(response, recorder)


@pytest.mark.parametrize("path", [LOGIN, LOGOUT])
@pytest.mark.parametrize("method", ["get", "head", "options"])
def test_reads_on_login_and_logout_never_touch_the_session(
    client: TestClient,
    recorder: type[RecordingSession],
    path: str,
    method: str,
) -> None:
    response = getattr(client, method)(path)

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert_no_session_effects(response, recorder)


def test_head_on_me_is_405_without_cookie(
    client: TestClient, recorder: type[RecordingSession]
) -> None:
    response = client.head("/api/me")
    assert response.status_code == 405
    assert_no_session_effects(response, recorder)


def test_logout_with_valid_origin_and_json_but_no_body_is_204(
    client: TestClient, recorder: type[RecordingSession]
) -> None:
    response = client.post(
        LOGOUT,
        headers={"Origin": HTTPS_ORIGIN, "Content-Type": "application/json"},
    )
    assert response.status_code == 204
    assert response.content == b""
    assert recorder.opened == 0


def test_no_cors_headers_even_on_a_preflight_style_request(
    client: TestClient,
) -> None:
    response = client.options(
        LOGIN,
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert not any(h.startswith("access-control-") for h in response.headers)
