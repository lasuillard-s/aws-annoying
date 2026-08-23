from __future__ import annotations

import socket
import threading
import time

import pytest

from aws_annoying.utils.network import get_free_port
from aws_annoying.utils.tcp_proxy import TCPProxy

pytestmark = [
    pytest.mark.unit,
]


def _start_echo_server(port: int, stop_event: threading.Event) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(5)
    server.settimeout(0.5)

    while not stop_event.is_set():
        try:
            client, _ = server.accept()
            data = client.recv(1024)
            if data:
                client.sendall(data)
            client.close()
        except TimeoutError:  # noqa: PERF203
            continue
        except OSError:
            break

    server.close()


def test_tcp_proxy() -> None:
    # Arrange
    echo_port = get_free_port()
    proxy_port = get_free_port()
    stop_event = threading.Event()

    # Start target echo server
    echo_thread = threading.Thread(target=_start_echo_server, args=(echo_port, stop_event), daemon=True)
    echo_thread.start()
    time.sleep(0.05)

    # Start proxy server
    proxy = TCPProxy("127.0.0.1", proxy_port, "127.0.0.1", echo_port)
    proxy.start()
    time.sleep(0.05)

    try:
        # Act
        with socket.create_connection(("127.0.0.1", proxy_port), timeout=2.0) as client:
            client.sendall(b"hello world")
            data = client.recv(1_024)

            # Assert
            assert data == b"hello world"
    finally:
        proxy.stop()
        stop_event.set()
        echo_thread.join(timeout=1.0)
