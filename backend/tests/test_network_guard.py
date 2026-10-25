"""A guarda de rede do `conftest.py` barra o que sair de loopback (CAP-7)."""

import socket

import pytest

from app.artic import ArticClient, CatalogUnavailable
from tests.conftest import BLOCKED_HOSTS


def test_default_client_is_blocked_and_the_host_is_recorded() -> None:
    with pytest.raises(CatalogUnavailable) as error:
        ArticClient().search("monet")

    assert error.value.reason == "connect"
    assert "api.artic.edu" in BLOCKED_HOSTS
    # O teste provou a guarda; limpa para a fixture autouse não reprová-lo.
    BLOCKED_HOSTS.clear()


def test_loopback_resolution_still_works() -> None:
    assert socket.getaddrinfo("localhost", 80)
    assert socket.getaddrinfo("127.0.0.1", 80)
    assert BLOCKED_HOSTS == []


def test_other_hosts_raise_os_error_and_are_recorded() -> None:
    with pytest.raises(OSError):
        socket.getaddrinfo("www.artic.edu", 443)
    assert BLOCKED_HOSTS == ["www.artic.edu"]
    BLOCKED_HOSTS.clear()
