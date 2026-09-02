import socket
import threading
import time
from collections.abc import Generator

import pytest

from aws_annoying.utils.network import get_free_port
from aws_annoying.utils.tcp_proxy import Address, TCPProxy

pytestmark = [
    pytest.mark.unit,
]


@pytest.fixture
def echo_server() -> Generator[int, None, None]:
    port = get_free_port()
    stop_event = threading.Event()

    def _start() -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(5)
        server.settimeout(0.5)

        while not stop_event.is_set():
            try:
                client, _ = server.accept()
                data = client.recv(1_024)
                if data:
                    client.sendall(data)
                client.close()
            except TimeoutError:  # noqa: PERF203
                continue
            except OSError:
                break

        server.close()

    thread = threading.Thread(target=_start, daemon=True)
    thread.start()
    time.sleep(0.05)

    try:
        yield port
    finally:
        stop_event.set()
        thread.join(timeout=1.0)


def test_tcp_proxy(echo_server: int) -> None:
    """Test basic bi-directional data forwarding between a client and a target server through the TCP proxy."""
    # Arrange
    proxy_port = get_free_port()

    # Start proxy server
    proxy = TCPProxy(Address("127.0.0.1", proxy_port), Address("127.0.0.1", echo_server))
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


def test_tcp_proxy_target_unreachable() -> None:
    """Test that connecting to the proxy when the target server is unreachable closes the client connection cleanly."""
    # Arrange
    target_port = get_free_port()
    proxy_port = get_free_port()

    proxy = TCPProxy(Address("127.0.0.1", proxy_port), Address("127.0.0.1", target_port))
    proxy.start()
    time.sleep(0.05)

    try:
        # Act & Assert
        with socket.create_connection(("127.0.0.1", proxy_port), timeout=2.0) as client:
            # Since target is not running, proxy closes client socket
            data = client.recv(1_024)
            assert data == b""
    finally:
        proxy.stop()


def test_tcp_proxy_half_close() -> None:
    """Test that TCP half-close (SHUT_WR) from client is forwarded, allowing the response to be received."""
    # Arrange
    echo_port = get_free_port()
    proxy_port = get_free_port()
    stop_event = threading.Event()

    def _read_all_then_reply_server(port: int, stop: threading.Event) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(1)
        server.settimeout(0.5)

        while not stop.is_set():
            try:
                client, _ = server.accept()
                chunks = []
                while True:
                    buf = client.recv(1_024)
                    if not buf:
                        break
                    chunks.append(buf)
                client.sendall(b"".join(chunks))
                client.close()
            except TimeoutError:
                continue
            except OSError:
                break

        server.close()

    server_thread = threading.Thread(target=_read_all_then_reply_server, args=(echo_port, stop_event), daemon=True)
    server_thread.start()
    time.sleep(0.05)

    proxy = TCPProxy(Address("127.0.0.1", proxy_port), Address("127.0.0.1", echo_port))
    proxy.start()
    time.sleep(0.05)

    try:
        # Act & Assert
        with socket.create_connection(("127.0.0.1", proxy_port), timeout=2.0) as client:
            client.sendall(b"ping")
            client.shutdown(socket.SHUT_WR)
            reply = client.recv(1_024)
            assert reply == b"ping"
    finally:
        proxy.stop()
        stop_event.set()
        server_thread.join(timeout=1.0)


def test_tcp_proxy_stop_when_not_started() -> None:
    """Test that stopping a proxy instance that has not been started succeeds without error."""
    # Arrange
    proxy = TCPProxy(Address("127.0.0.1", 12345), Address("127.0.0.1", 54321))

    # Act & Assert
    proxy.stop()  # Should not raise
