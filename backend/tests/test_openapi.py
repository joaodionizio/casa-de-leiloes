import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main
from app.config import SpaSettings
from app.main import create_app


@pytest.fixture
def api_only(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    return TestClient(create_app(app_origin="https://casa.example"))


def test_docs_and_schema_live_under_api(api_only: TestClient) -> None:
    docs = api_only.get("/api/docs")
    assert docs.status_code == 200
    assert docs.headers["content-type"].startswith("text/html")

    schema = api_only.get("/api/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["info"]["title"] == "ÁTRIO"
    assert list(schema.json()["paths"]) == [
        "/health",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/me",
        "/api/catalog/artworks",
        "/api/catalog/artworks/{external_id}",
        "/api/catalog/images/{image_id}",
        "/api/lots",
        "/api/lots/mine",
        "/api/lots/{lot_id}",
        "/api/wallet",
        "/api/wallet/deposit",
        "/api/lots/{lot_id}/bids",
        "/api/lots/{lot_id}/bids/mine",
        "/api/lots/{lot_id}/cancel",
    ]


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/api/redoc"])
def test_old_documentation_routes_are_gone(api_only: TestClient, path: str) -> None:
    assert api_only.get(path).status_code == 404


def test_oauth2_redirect_is_disabled(api_only: TestClient) -> None:
    paths = [getattr(route, "path", "") for route in api_only.app.routes]  # type: ignore[attr-defined]
    assert not any("oauth2-redirect" in path for path in paths)
    assert "oauth2RedirectUrl" not in api_only.get("/api/docs").text
    assert api_only.get("/api/docs/oauth2-redirect").status_code == 404


ERROR_REF = "#/components/schemas/ErrorResponse"


def response_ref(operation: dict, status: str) -> str:
    return operation["responses"][status]["content"]["application/json"]["schema"][
        "$ref"
    ]


def test_error_responses_of_the_new_routes_use_the_real_envelope(
    api_only: TestClient,
) -> None:
    schema = api_only.get("/api/openapi.json").json()
    login = schema["paths"]["/api/auth/login"]["post"]
    me = schema["paths"]["/api/me"]["get"]

    assert response_ref(login, "401") == ERROR_REF
    assert response_ref(login, "422") == ERROR_REF
    assert response_ref(me, "401") == ERROR_REF
    assert "204" in schema["paths"]["/api/auth/logout"]["post"]["responses"]


def test_default_validation_schema_is_gone(api_only: TestClient) -> None:
    # Se uma rota futura com corpo esquecer `error_responses(..., 422)`, o schema
    # padrão do FastAPI volta e este teste reprova.
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas
    assert {"ErrorResponse", "ErrorDetail", "CurrentUser", "LoginRequest"} <= set(
        schemas
    )


def test_openapi_has_no_secret_cookie_or_token_in_the_documented_bodies(
    api_only: TestClient,
) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]
    assert sorted(schemas["CurrentUser"]["properties"]) == ["email", "role"]


def test_app_openapi_is_not_overridden(api_only: TestClient) -> None:
    # Sem override de `app.openapi()`: o método continua sendo o do FastAPI.
    assert type(api_only.app).openapi is FastAPI.openapi
    assert "openapi" not in vars(api_only.app)


# --- Story 2.3: catálogo da AIC ---

SEARCH_PATH = "/api/catalog/artworks"
DETAIL_PATH = "/api/catalog/artworks/{external_id}"
SUMMARY_FIELDS = [
    "artist_display",
    "date_display",
    "external_id",
    "image_id",
    "image_url",
    "title",
]
DETAIL_FIELDS = sorted(
    SUMMARY_FIELDS
    + [
        "artwork_type_title",
        "credit_line",
        "department_title",
        "dimensions",
        "medium_display",
        "source_url",
    ]
)


def test_catalog_routes_document_the_real_error_envelope(
    api_only: TestClient,
) -> None:
    paths = api_only.get("/api/openapi.json").json()["paths"]
    search = paths[SEARCH_PATH]["get"]
    detail = paths[DETAIL_PATH]["get"]

    for status in ("401", "403", "422", "503"):
        assert response_ref(search, status) == ERROR_REF
        assert response_ref(detail, status) == ERROR_REF
    assert response_ref(detail, "404") == ERROR_REF
    assert "404" not in search["responses"]


def test_catalog_schemas_have_exactly_the_contract_fields(
    api_only: TestClient,
) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]

    assert sorted(schemas["ArtworkSummary"]["properties"]) == SUMMARY_FIELDS
    assert sorted(schemas["ArtworkDetail"]["properties"]) == DETAIL_FIELDS
    assert sorted(schemas["ArtworkSearchResponse"]["properties"]) == ["items"]


def test_catalog_schemas_do_not_leak_aic_internals(api_only: TestClient) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]
    forbidden = {"_score", "thumbnail", "config", "is_public_domain", "alt_text"}

    for name in ("ArtworkSummary", "ArtworkDetail", "ArtworkSearchResponse"):
        assert forbidden.isdisjoint(schemas[name]["properties"])
    assert "HTTPValidationError" not in schemas


def test_image_route_documents_a_jpeg_and_the_real_error_envelope(
    api_only: TestClient,
) -> None:
    paths = api_only.get("/api/openapi.json").json()["paths"]
    image = paths["/api/catalog/images/{image_id}"]["get"]

    assert "image/jpeg" in image["responses"]["200"]["content"]
    for status in ("404", "422", "503"):
        assert response_ref(image, status) == ERROR_REF
    # Rota pública: não documenta 401/403.
    assert "401" not in image["responses"]
    assert "403" not in image["responses"]


# --- Story 2.4: lotes ---

LOTS_PATH = "/api/lots"
MINE_PATH = "/api/lots/mine"
LOT_DETAIL_PATH = "/api/lots/{lot_id}"
WALLET_PATH = "/api/wallet"
DEPOSIT_PATH = "/api/wallet/deposit"
BIDS_PATH = "/api/lots/{lot_id}/bids"
MY_BIDS_PATH = "/api/lots/{lot_id}/bids/mine"
CANCEL_PATH = "/api/lots/{lot_id}/cancel"
LOT_FIELDS = sorted(
    [
        "id",
        "external_id",
        "title",
        "artist_display",
        "date_display",
        "medium_display",
        "dimensions",
        "department_title",
        "artwork_type_title",
        "credit_line",
        "source_url",
        "image_id",
        "image_url",
        "starting_bid_cents",
        "min_increment_cents",
        "starts_at",
        "ends_at",
        "created_at",
    ]
)


def test_lot_routes_come_after_the_catalog_routes(api_only: TestClient) -> None:
    paths = list(api_only.get("/api/openapi.json").json()["paths"])

    # Story 3.1: a carteira vem depois dos lotes, imediatamente. Story 3.4: o lance
    # (`register_bid_routes`) vem depois da carteira. Story 3.6: o cancelamento vem por
    # último.
    assert paths[-8:-5] == [LOTS_PATH, MINE_PATH, LOT_DETAIL_PATH]
    assert paths[-5:-3] == [WALLET_PATH, DEPOSIT_PATH]
    assert paths[-3:-1] == [BIDS_PATH, MY_BIDS_PATH]
    assert paths[-1] == CANCEL_PATH
    assert paths.index("/api/catalog/images/{image_id}") < paths.index(LOTS_PATH)


def test_create_lot_documents_201_and_the_real_error_envelope(
    api_only: TestClient,
) -> None:
    operation = api_only.get("/api/openapi.json").json()["paths"][LOTS_PATH]["post"]

    assert operation["responses"]["201"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/LotResponse")
    for status in ("401", "403", "422", "503"):
        assert response_ref(operation, status) == ERROR_REF
    assert operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/CreateLotRequest")


def test_my_lots_documents_200_and_the_auth_errors(api_only: TestClient) -> None:
    paths = api_only.get("/api/openapi.json").json()["paths"]
    operation = paths[MINE_PATH]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/MyLotsResponse")
    for status in ("401", "403"):
        assert response_ref(operation, status) == ERROR_REF
    assert "parameters" not in operation  # o dono vem só da sessão
    # Story 2.5: `GET /api/lots` (vitrine) divide o caminho com o `POST` da 2.4.
    assert set(paths[LOTS_PATH]) == {"get", "post"}
    assert set(paths[MINE_PATH]) == {"get"}
    assert set(paths[LOT_DETAIL_PATH]) == {"get"}


def test_lot_schemas_have_exactly_the_contract_fields(api_only: TestClient) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]

    assert sorted(schemas["CreateLotRequest"]["properties"]) == [
        "ends_at",
        "external_id",
        "min_increment_cents",
        "starting_bid_cents",
        "starts_at",
    ]
    assert sorted(schemas["CreateLotRequest"]["required"]) == [
        "ends_at",
        "external_id",
        "min_increment_cents",
        "starting_bid_cents",
    ]
    assert schemas["CreateLotRequest"]["additionalProperties"] is False
    assert sorted(schemas["LotResponse"]["properties"]) == LOT_FIELDS
    assert sorted(schemas["MyLotsResponse"]["properties"]) == ["as_of", "items"]
    assert sorted(schemas["MyLotsResponse"]["required"]) == ["as_of", "items"]
    # Story 3.6, D7: o item da lista do dono é o `LotResponse` mais três campos; a
    # criação (201) continua com o `LotResponse`.
    assert sorted(schemas["MyLotResponse"]["properties"]) == sorted(
        [*LOT_FIELDS, "cancelled_at", "bid_count", "phase"]
    )
    assert len(schemas["MyLotResponse"]["properties"]) == len(LOT_FIELDS) + 3
    assert "HTTPValidationError" not in schemas


def test_no_lot_schema_exposes_the_owner_or_the_demo_flag(
    api_only: TestClient,
) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]

    for name in ("CreateLotRequest", "LotResponse", "MyLotResponse", "MyLotsResponse"):
        properties = set(schemas[name]["properties"])
        assert {"is_demo", "auctioneer_id", "is_public_domain", "status"}.isdisjoint(
            properties
        )


# --- Story 2.5: vitrine e página do lote ---

PUBLIC_SUMMARY_FIELDS = [
    "ends_at",
    "artist_display",
    "date_display",
    "id",
    "image_url",
    "phase",
    "starting_bid_cents",
    "starts_at",
    "title",
]
PUBLIC_DETAIL_FIELDS = PUBLIC_SUMMARY_FIELDS + [
    "credit_line",
    "dimensions",
    "department_title",
    "artwork_type_title",
    "external_id",
    "medium_display",
    "min_increment_cents",
    "source_url",
]
INTERNAL_FIELDS = {
    "is_demo",
    "auctioneer_id",
    "created_at",
    "image_id",
    "status",
    "settlement_status",
}


def test_public_vitrine_documents_200_without_errors(api_only: TestClient) -> None:
    operation = api_only.get("/api/openapi.json").json()["paths"][LOTS_PATH]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PublicLotsResponse")
    # Rota pública sem parâmetros: nada de 401, 403 nem 422.
    assert set(operation["responses"]) == {"200"}
    assert "parameters" not in operation


def test_public_detail_documents_the_uuid_parameter_and_the_real_errors(
    api_only: TestClient,
) -> None:
    operation = api_only.get("/api/openapi.json").json()["paths"][LOT_DETAIL_PATH][
        "get"
    ]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PublicLotDetailResponse")
    for status in ("404", "422"):
        assert response_ref(operation, status) == ERROR_REF
    assert "401" not in operation["responses"]
    assert "403" not in operation["responses"]
    (parameter,) = operation["parameters"]
    assert parameter["name"] == "lot_id"
    assert parameter["in"] == "path"
    assert parameter["schema"]["format"] == "uuid"


def test_public_lot_schemas_have_exactly_the_contract_fields(
    api_only: TestClient,
) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]

    assert sorted(schemas["PublicLotSummary"]["properties"]) == sorted(
        PUBLIC_SUMMARY_FIELDS
    )
    assert sorted(schemas["PublicLotDetail"]["properties"]) == sorted(
        PUBLIC_DETAIL_FIELDS
    )
    assert sorted(schemas["PublicLotsResponse"]["properties"]) == [
        "as_of",
        "ended",
        "live",
        "scheduled",
    ]
    assert sorted(schemas["PublicLotDetailResponse"]["properties"]) == ["as_of", "lot"]
    assert schemas["LotPhase"]["enum"] == ["scheduled", "live", "ended"]
    assert "HTTPValidationError" not in schemas


def test_no_public_lot_schema_exposes_internal_fields(api_only: TestClient) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]

    for name in (
        "PublicLotSummary",
        "PublicLotDetail",
        "PublicLotsResponse",
        "PublicLotDetailResponse",
    ):
        assert INTERNAL_FIELDS.isdisjoint(schemas[name]["properties"])
    # O `LotResponse` privado continua como era (com `created_at` e `image_id`).
    assert sorted(schemas["LotResponse"]["properties"]) == LOT_FIELDS


# --- Story 3.1: carteira ---


def test_wallet_read_documents_200_and_the_auth_errors(api_only: TestClient) -> None:
    paths = api_only.get("/api/openapi.json").json()["paths"]
    operation = paths[WALLET_PATH]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/WalletResponse")
    for status in ("401", "403"):
        assert response_ref(operation, status) == ERROR_REF
    assert "422" not in operation["responses"]
    assert "parameters" not in operation  # o dono vem só da sessão
    assert "requestBody" not in operation
    assert set(paths[WALLET_PATH]) == {"get"}


def test_deposit_documents_200_the_request_and_the_real_error_envelope(
    api_only: TestClient,
) -> None:
    paths = api_only.get("/api/openapi.json").json()["paths"]
    operation = paths[DEPOSIT_PATH]["post"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/WalletResponse")
    for status in ("401", "403", "422"):
        assert response_ref(operation, status) == ERROR_REF
    assert operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DepositRequest")
    assert set(paths[DEPOSIT_PATH]) == {"post"}


def test_wallet_schemas_have_exactly_the_contract_fields(api_only: TestClient) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]

    assert sorted(schemas["WalletResponse"]["properties"]) == [
        "available_balance_cents",
        "committed_balance_cents",
        "total_balance_cents",
    ]
    assert sorted(schemas["WalletResponse"]["required"]) == [
        "available_balance_cents",
        "committed_balance_cents",
        "total_balance_cents",
    ]
    assert sorted(schemas["DepositRequest"]["properties"]) == ["amount_cents"]
    assert schemas["DepositRequest"]["required"] == ["amount_cents"]
    assert schemas["DepositRequest"]["additionalProperties"] is False
    assert "HTTPValidationError" not in schemas


# --- Story 3.4: o lance ---


def test_place_bid_documents_201_and_the_real_error_envelope(
    api_only: TestClient,
) -> None:
    operation = api_only.get("/api/openapi.json").json()["paths"][BIDS_PATH]["post"]

    assert operation["responses"]["201"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PlaceBidResponse")
    for status in ("401", "403", "404", "409", "422"):
        assert response_ref(operation, status) == ERROR_REF
    assert operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PlaceBidRequest")
    # Story 3.5: a leitura pública da sala divide o caminho com o POST.
    assert set(api_only.get("/api/openapi.json").json()["paths"][BIDS_PATH]) == {
        "get",
        "post",
    }


def test_room_reads_document_their_schemas_and_errors(api_only: TestClient) -> None:
    paths = api_only.get("/api/openapi.json").json()["paths"]
    room = paths[BIDS_PATH]["get"]
    mine = paths[MY_BIDS_PATH]["get"]

    assert room["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/PublicBidRoomResponse")
    for status in ("404", "422"):
        assert response_ref(room, status) == ERROR_REF
    assert "401" not in room["responses"]
    assert mine["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/MyLotBidsResponse")
    for status in ("401", "403", "404", "422"):
        assert response_ref(mine, status) == ERROR_REF
    assert set(paths[MY_BIDS_PATH]) == {"get"}

    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]
    room_fields = [
        "as_of",
        "bid_count",
        "bids",
        "current_bid_cents",
        "ends_at",
        "minimum_next_bid_cents",
        "phase",
    ]
    assert sorted(schemas["PublicBidRoomResponse"]["properties"]) == room_fields
    assert sorted(schemas["PublicBidRoomResponse"]["required"]) == room_fields
    my_fields = ["bidder_alias", "last_bid_cents", "my_bid_count"]
    assert sorted(schemas["MyLotBidsResponse"]["properties"]) == my_fields
    assert sorted(schemas["MyLotBidsResponse"]["required"]) == my_fields


def test_bid_schemas_have_exactly_the_contract_fields_and_no_private_ones(
    api_only: TestClient,
) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]

    assert sorted(schemas["PlaceBidRequest"]["properties"]) == ["amount_cents"]
    assert schemas["PlaceBidRequest"]["required"] == ["amount_cents"]
    assert schemas["PlaceBidRequest"]["additionalProperties"] is False
    assert sorted(schemas["PlaceBidResponse"]["properties"]) == [
        "bid",
        "lot",
        "wallet",
    ]
    assert sorted(schemas["AcceptedBidResponse"]["properties"]) == [
        "amount_cents",
        "bidder_alias",
        "placed_at",
        "sequence",
    ]
    assert sorted(schemas["BidLotStateResponse"]["properties"]) == [
        "anti_sniping_applied",
        "current_bid_cents",
        "ends_at",
    ]
    bid_schemas = json.dumps(
        {
            name: schemas[name]
            for name in (
                "PlaceBidRequest",
                "PlaceBidResponse",
                "AcceptedBidResponse",
                "BidLotStateResponse",
            )
        }
    )
    for forbidden in (
        "bidder_id",
        "user_id",
        "current_leader_id",
        "auctioneer_id",
        "previous_hash",
        "current_hash",
        "final_hash",
        "anchor_hmac",
        "canonical_version",
        "is_demo",
        "email",
        "secret",
    ):
        assert forbidden not in bid_schemas, forbidden
    assert "HTTPValidationError" not in schemas


# --- Story 3.6: cancelamento ---


def test_cancel_documents_200_without_a_body_and_the_real_error_envelope(
    api_only: TestClient,
) -> None:
    paths = api_only.get("/api/openapi.json").json()["paths"]
    operation = paths[CANCEL_PATH]["post"]

    assert set(paths[CANCEL_PATH]) == {"post"}
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/CancelLotResponse")
    for status in ("401", "403", "404", "409", "422"):
        assert response_ref(operation, status) == ERROR_REF
    assert "requestBody" not in operation  # sem corpo: o dono vem da sessão
    assert [p["name"] for p in operation["parameters"]] == ["lot_id"]

    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]
    assert sorted(schemas["CancelLotResponse"]["properties"]) == ["cancelled_at", "id"]
    assert sorted(schemas["CancelLotResponse"]["required"]) == ["cancelled_at", "id"]
