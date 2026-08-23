from __future__ import annotations

import socket

import pytest

from aws_annoying.utils.network import get_free_port

pytestmark = [
    pytest.mark.unit,
]


def test_get_free_port() -> None:
    # Act
    port = get_free_port()

    # Assert
    assert isinstance(port, int)
    assert 0 < port < 65536

    # Verify we can bind to the port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))
