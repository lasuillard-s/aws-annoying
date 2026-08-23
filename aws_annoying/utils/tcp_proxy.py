from __future__ import annotations

import contextlib
import socket
import threading


class TCPProxy:
    """A TCP proxy forwarding traffic from a local host and port to a target host and port."""

    def __init__(self, listen_host: str, listen_port: int, target_host: str, target_port: int) -> None:  # noqa: D107
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port

        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the proxy server in a background thread."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.listen_host, self.listen_port))
        self._server.listen(128)

        self._running = True

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._running and self._server:
            try:
                client, _ = self._server.accept()
                t = threading.Thread(
                    target=_handle_client,
                    args=(client, self.target_host, self.target_port),
                    daemon=True,
                )
                t.start()
            except OSError:  # noqa: PERF203
                break

    def stop(self) -> None:
        """Stop the proxy server."""
        self._running = False
        if self._server:
            with contextlib.suppress(OSError):
                self._server.close()
            self._server = None


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
