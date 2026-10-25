"""Cliente e adaptador da AIC, sem banco (Story 2.3, test-plan §3)."""

from collections.abc import Callable

import httpx
import pytest

from app.artic import (
    AIC_USER_AGENT,
    DEFAULT_TIMEOUT,
    DETAIL_FIELDS,
    SEARCH_FIELDS,
    USER_AGENT,
    ArticClient,
    CatalogUnavailable,
    build_search_query,
    iiif_image_url,
)
from tests.catalog_support import (
    FAILURES_BOTH,
    IMAGE_FAILURES,
    IMAGE_ID,
    UPSTREAM_IMAGE_URL,
    FakeArtic,
    artic_client,
    image_bytes,
    image_response,
    jpeg_handler,
    json_response,
    load_fixture,
    raising,
    search_params,
    standard_handler,
)

EXPECTED_HEADERS = {
    "user-agent": "casa-de-leiloes/1.0",
    "aic-user-agent": "casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)",
    "accept": "application/json",
}
FILTERS = [
    {"term": {"is_public_domain": True}},
    {"exists": {"field": "image_id"}},
]


def standard_fake() -> FakeArtic:
    return FakeArtic(standard_handler)


# --- cabeçalhos e requisições ---


def test_identification_constants_are_exact() -> None:
    assert USER_AGENT == "casa-de-leiloes/1.0"
    assert AIC_USER_AGENT == (
        "casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)"
    )


def test_every_request_carries_the_exact_headers() -> None:
    fake = standard_fake()
    client = artic_client(fake)
    client.search("monet")
    client.get_artwork(27992)

    assert len(fake.requests) == 2
    for request in fake.requests:
        for name, value in EXPECTED_HEADERS.items():
            assert request.headers[name] == value


def test_search_request_shape() -> None:
    fake = standard_fake()
    artic_client(fake).search("monet")

    (request,) = fake.requests
    assert request.method == "GET"
    assert request.url.host == "api.artic.edu"
    assert request.url.path == "/api/v1/artworks/search"
    assert list(request.url.params) == ["params"]
    assert search_params(request) == {
        "q": "monet",
        "query": {
            "bool": {
                "must": [{"multi_match": {"query": "monet", "operator": "and"}}],
                "filter": FILTERS,
            }
        },
        "limit": 20,
        "fields": SEARCH_FIELDS,
    }
    bool_query = search_params(request)["query"]["bool"]
    assert {"term": {"is_public_domain": True}} in bool_query["filter"]
    assert {"exists": {"field": "image_id"}} in bool_query["filter"]
    assert bool_query["must"][0]["multi_match"]["operator"] == "and"


@pytest.mark.parametrize("term", ["cézanne", "日本"])
def test_non_ascii_terms_are_not_escaped_in_the_json(term: str) -> None:
    fake = standard_fake()
    artic_client(fake).search(term)

    (request,) = fake.requests
    assert search_params(request)["q"] == term
    # JSON em UTF-8 (percent-encoded pelo httpx), nunca `\uXXXX` (o firewall recusa).
    assert b"%5Cu" not in request.url.query
    assert b"\\u" not in request.url.query


DSL_TERMS = [
    '{"match_all":{}}',
    '"},"query":{"match_all":{}},"x":{"',
    "*:*",
    "is_public_domain:false",
]


@pytest.mark.parametrize("term", DSL_TERMS)
def test_build_search_query_keeps_the_term_as_a_plain_value(term: str) -> None:
    query = build_search_query(term)

    assert set(query) == {"q", "query", "limit", "fields"}
    assert query["q"] == term
    assert query["query"]["bool"]["filter"] == FILTERS
    assert query["query"]["bool"]["must"] == [
        {"multi_match": {"query": term, "operator": "and"}}
    ]


@pytest.mark.parametrize("term", DSL_TERMS)
def test_term_that_looks_like_dsl_reaches_the_aic_only_as_a_value(term: str) -> None:
    fake = standard_fake()
    artic_client(fake).search(term)

    (request,) = fake.requests
    params = search_params(request)
    assert set(params) == {"q", "query", "limit", "fields"}
    assert params["q"] == term
    assert params["query"]["bool"]["filter"] == FILTERS
    assert params["query"]["bool"]["must"][0]["multi_match"]["query"] == term
    assert params == build_search_query(term)


def test_detail_request_shape() -> None:
    fake = standard_fake()
    artic_client(fake).get_artwork(27992)

    (request,) = fake.requests
    assert request.method == "GET"
    assert request.url.host == "api.artic.edu"
    assert request.url.path == "/api/v1/artworks/27992"
    assert dict(request.url.params) == {"fields": DETAIL_FIELDS}
    assert DETAIL_FIELDS == (
        "id,title,artist_display,date_display,medium_display,dimensions,"
        "department_title,artwork_type_title,image_id,is_public_domain,credit_line"
    )


def test_default_timeout_is_the_approved_one() -> None:
    assert DEFAULT_TIMEOUT.connect == 3.0
    assert DEFAULT_TIMEOUT.read == 5.0
    assert DEFAULT_TIMEOUT.write == 5.0
    assert DEFAULT_TIMEOUT.pool == 3.0


def test_redirect_is_not_followed() -> None:
    def redirect(request: httpx.Request) -> httpx.Response:
        return httpx.Response(301, headers={"Location": "https://example.org/x"})

    for call in (
        lambda client: client.search("monet"),
        lambda client: client.get_artwork(27992),
    ):
        fake = FakeArtic(redirect)
        with pytest.raises(CatalogUnavailable) as error:
            call(artic_client(fake))
        assert error.value.reason == "redirect"
        # O host do `Location` nunca é requisitado.
        assert len(fake.requests) == 1
        assert fake.requests[0].url.host == "api.artic.edu"


# --- parsing ---


def test_search_adapter_keeps_valid_ids_and_marks_the_rest_unknown() -> None:
    artworks = artic_client(standard_fake()).search("monet")

    # Só o item de `id` string some; a elegibilidade é do serviço.
    assert [a.external_id for a in artworks] == [
        16568,
        16571,
        16572,
        100001,
        100002,
        100003,
        100004,
    ]
    by_id = {a.external_id: a for a in artworks}
    assert by_id[100001].is_public_domain is False
    assert by_id[100002].is_public_domain is None  # chave ausente
    assert by_id[100003].image_id is None  # null
    assert by_id[100004].image_id is None  # "../evil"
    assert by_id[16572].date_display is None
    assert by_id[16572].artist_display == "Atelier Monet\nFrench, 19th century"
    assert by_id[16568].title == "Water Lilies"


def test_detail_complete() -> None:
    artwork = artic_client(standard_fake()).get_artwork(27992)

    assert artwork is not None
    assert artwork.external_id == 27992
    assert artwork.title == "A Sunday on La Grande Jatte — 1884"
    assert artwork.artist_display == "Georges Seurat (French, 1859–1891)"
    assert artwork.date_display == "1884–86, border added 1888–89"
    assert artwork.medium_display == "Oil on canvas"
    assert artwork.dimensions == "207.5 × 308.1 cm (81 3/4 × 121 1/4 in.)"
    assert artwork.department_title == "Painting and Sculpture of Europe"
    assert artwork.artwork_type_title == "Painting"
    assert artwork.image_id == "2d484387-2509-5e8e-2c43-22f9981972eb"
    assert artwork.is_public_domain is True
    assert artwork.credit_line == "Helen Birch Bartlett Memorial Collection"


def test_detail_with_missing_empty_and_non_string_fields_becomes_none() -> None:
    body = load_fixture("artwork_missing_fields.json")
    body["data"]["dimensions"] = 42  # não é string
    fake = FakeArtic(lambda request: json_response(body))

    artwork = artic_client(fake).get_artwork(555001)

    assert artwork is not None
    assert artwork.title == "Study"  # strip
    assert artwork.medium_display is None  # ausente
    assert artwork.department_title is None  # ausente
    assert artwork.dimensions is None  # não string
    assert artwork.credit_line is None  # ""
    assert artwork.date_display is None  # null


def test_detail_404_is_none_and_not_a_failure() -> None:
    fake = FakeArtic(lambda request: json_response(load_fixture("not_found.json"), 404))
    assert artic_client(fake).get_artwork(999999999) is None


def test_non_bool_public_domain_becomes_none() -> None:
    body = load_fixture("artwork_27992.json")
    body["data"]["is_public_domain"] = "true"
    fake = FakeArtic(lambda request: json_response(body))

    artwork = artic_client(fake).get_artwork(27992)

    assert artwork is not None
    assert artwork.is_public_domain is None


def test_boolean_id_is_not_a_valid_id() -> None:
    body = {"data": [{"id": True, "title": "x"}, {"id": 0}, {"id": -3}, "texto"]}
    fake = FakeArtic(lambda request: json_response(body))
    assert artic_client(fake).search("x") == []


# --- falhas ---


@pytest.mark.parametrize(("reason", "handler"), FAILURES_BOTH)
def test_search_failures_become_catalog_unavailable(
    reason: str, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    with pytest.raises(CatalogUnavailable) as error:
        artic_client(FakeArtic(handler)).search("monet")
    assert error.value.reason == reason


@pytest.mark.parametrize(("reason", "handler"), FAILURES_BOTH)
def test_detail_failures_become_catalog_unavailable(
    reason: str, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    with pytest.raises(CatalogUnavailable) as error:
        artic_client(FakeArtic(handler)).get_artwork(27992)
    assert error.value.reason == reason


def test_search_404_is_a_failure_not_an_empty_result() -> None:
    fake = FakeArtic(lambda request: json_response(load_fixture("not_found.json"), 404))
    with pytest.raises(CatalogUnavailable) as error:
        artic_client(fake).search("monet")
    assert error.value.reason == "http_404"


def test_detail_with_another_id_is_bad_shape() -> None:
    body = load_fixture("artwork_27992.json")
    body["data"]["id"] = 11111
    fake = FakeArtic(lambda request: json_response(body))
    with pytest.raises(CatalogUnavailable) as error:
        artic_client(fake).get_artwork(27992)
    assert error.value.reason == "bad_shape"


def test_unexpected_http_library_error_does_not_escape() -> None:
    fake = FakeArtic(raising(lambda r: httpx.DecodingError("d", request=r)))
    with pytest.raises(CatalogUnavailable) as error:
        artic_client(fake).search("monet")
    assert error.value.reason == "bad_shape"


def test_constructor_does_no_network() -> None:
    # A guarda de rede (conftest) reprova o teste se algo resolver um host.
    ArticClient()


# --- IIIF ---


def test_iiif_url_uses_the_fixed_base() -> None:
    assert iiif_image_url("2d484387-2509-5e8e-2c43-22f9981972eb") == (
        "https://www.artic.edu/iiif/2/2d484387-2509-5e8e-2c43-22f9981972eb"
        "/full/843,/0/default.jpg"
    )


@pytest.mark.parametrize(
    "image_id",
    [
        "2D484387-2509-5E8E-2C43-22F9981972EB",
        "../evil",
        "https://x",
        "",
        "2d484387-2509-5e8e-2c43-22f9981972eb/../x",
        "2d484387-2509-5e8e-2c43-22f9981972eb\n",
    ],
)
def test_iiif_url_refuses_invalid_image_ids(image_id: str) -> None:
    with pytest.raises(ValueError):
        iiif_image_url(image_id)


# --- imagem no IIIF (proxy same-origin, revisão do AD-22) ---


def test_get_image_requests_the_fixed_iiif_url_with_the_identification() -> None:
    fake = FakeArtic(jpeg_handler)

    data = artic_client(fake).get_image(IMAGE_ID)

    assert data == image_bytes()
    (request,) = fake.requests
    assert request.method == "GET"
    assert str(request.url) == UPSTREAM_IMAGE_URL
    assert request.url.scheme == "https"
    assert request.url.host == "www.artic.edu"
    assert request.url.path == f"/iiif/2/{IMAGE_ID}/full/843,/0/default.jpg"
    assert request.url.query == b""
    assert request.headers["user-agent"] == EXPECTED_HEADERS["user-agent"]
    assert request.headers["aic-user-agent"] == EXPECTED_HEADERS["aic-user-agent"]


def test_get_image_404_is_none_and_not_a_failure() -> None:
    fake = FakeArtic(lambda request: httpx.Response(404, text="nope"))
    assert artic_client(fake).get_image(IMAGE_ID) is None


@pytest.mark.parametrize(("reason", "handler"), IMAGE_FAILURES)
def test_get_image_failures_become_catalog_unavailable(
    reason: str, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    fake = FakeArtic(handler)
    with pytest.raises(CatalogUnavailable) as error:
        artic_client(fake).get_image(IMAGE_ID)
    assert error.value.reason == reason
    # Sem seguir redirecionamento: uma única requisição, sempre ao host fixo.
    assert len(fake.requests) == 1
    assert fake.requests[0].url.host == "www.artic.edu"


def test_get_image_refuses_a_body_over_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.artic.MAX_IMAGE_BYTES", 100)
    fake = FakeArtic(image_response(b"\xff\xd8\xff" + b"0" * 500))
    with pytest.raises(CatalogUnavailable) as error:
        artic_client(fake).get_image(IMAGE_ID)
    assert error.value.reason == "bad_shape"


@pytest.mark.parametrize(
    "image_id", ["../evil", "https://x", "", IMAGE_ID.upper(), IMAGE_ID + "/x"]
)
def test_get_image_with_an_invalid_id_never_reaches_the_transport(
    image_id: str,
) -> None:
    fake = FakeArtic(jpeg_handler)
    with pytest.raises(ValueError):
        artic_client(fake).get_image(image_id)
    assert fake.requests == []
