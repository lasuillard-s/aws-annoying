from __future__ import annotations

import contextlib
import socket
import sys
import threading


def _forward(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            src.close()
        with contextlib.suppress(OSError):
            dst.close()


def _handle_client(client_socket: socket.socket, target_host: str, target_port: int) -> None:
    try:
        remote_socket = socket.create_connection((target_host, target_port))
    except OSError:
        client_socket.close()
        return

    t1 = threading.Thread(target=_forward, args=(client_socket, remote_socket), daemon=True)
    t2 = threading.Thread(target=_forward, args=(remote_socket, client_socket), daemon=True)
    t1.start()
    t2.start()


def start_proxy(listen_host: str, listen_port: int, target_host: str, target_port: int) -> None:
    """Start a TCP proxy forwarding traffic from listen_host:listen_port to target_host:target_port.

    Args:
        listen_host: Host address to bind to.
        listen_port: Port to listen on.
        target_host: Destination host address.
        target_port: Destination port.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_host, listen_port))
    server.listen(128)

    while True:
        try:
            client, _ = server.accept()
            t = threading.Thread(target=_handle_client, args=(client, target_host, target_port), daemon=True)
            t.start()
        except (KeyboardInterrupt, OSError):  # noqa: PERF203
            break

    server.close()


if __name__ == "__main__":
    if len(sys.argv) == 5:  # noqa: PLR2004
        start_proxy(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]))
