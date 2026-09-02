import asyncio
import logging
import threading
from typing import NamedTuple

logger = logging.getLogger(__name__)


class Address(NamedTuple):
    """Network address containing a host string and integer port."""

    host: str
    port: int


class TCPProxy:
    """A TCP proxy forwarding traffic from a local host and port to a target host and port."""

    def __init__(  # noqa: D107
        self,
        listen: Address,
        target: Address,
        *,
        buffer_size: int = 4_096,
    ) -> None:
        self.listen = listen
        self.target = target
        self.buffer_size = buffer_size

        # Separate thread to run the asyncio event loop for the proxy server
        self._thread: threading.Thread | None = None
        self._running = threading.Event()

        # Synchronization primitives to block start() until the server binds or fails
        self._startup_event = threading.Event()
        self._startup_error: Exception | None = None

        # Asyncio server and loop references for graceful shutdown
        self._server: asyncio.Server | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._async_stop_event: asyncio.Event | None = None

    def start(self) -> None:
        """Start the proxy server in a background thread."""
        self._running.set()
        self._startup_event.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        self._startup_event.wait()
        if self._startup_error is not None:
            raise self._startup_error

    def _run(self) -> None:
        """Set up the asyncio event loop and run the proxy server until it is stopped."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_run())
        except Exception as e:  # noqa: BLE001
            if not self._startup_event.is_set():
                self._startup_error = e
        finally:
            self._startup_event.set()
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()

            if pending:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            self._loop.close()

    async def _async_run(self) -> None:
        """Start the asyncio server and block until the stop event is signaled."""
        self._async_stop_event = asyncio.Event()
        self._server = await asyncio.start_server(
            self._handle_client,
            self.listen.host,
            self.listen.port,
        )
        logger.debug("TCP proxy listening on %s forwarding to %s", self.listen, self.target)
        self._startup_event.set()
        async with self._server:
            # Run server until the event is set
            await self._async_stop_event.wait()

        logger.debug("TCP proxy stopped on %s", self.listen)

    def stop(self) -> None:
        """Stop the proxy server."""
        logger.debug("Stopping TCP proxy on %s", self.listen)
        self._running.clear()
        if self._loop and self._async_stop_event:
            self._loop.call_soon_threadsafe(self._async_stop_event.set)

        if self._thread:
            self._thread.join(timeout=2.0)

    async def _forward(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Asynchronously forward data from a stream reader to a stream writer."""
        try:
            while True:
                data = await reader.read(self.buffer_size)
                if not data:
                    break

                writer.write(data)
                await writer.drain()
        except OSError as e:
            logger.debug("Socket error during port forwarding: %s", e)
        finally:
            if writer.can_write_eof():
                writer.write_eof()
            else:
                writer.close()

    async def _handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
        """Handle an incoming client connection.

        Establishes a connection to the target and spawns bidirectional data forwarding tasks.
        """
        peername: tuple[str, int] | None = client_writer.get_extra_info("peername")  # (ip, port) tuple
        logger.debug("Accepted new client connection from %s", peername)
        try:
            remote_reader, remote_writer = await asyncio.open_connection(self.target.host, self.target.port)
        except OSError as e:
            logger.debug("Failed to connect to target %s: %s", self.target, e)
            client_writer.close()
            return

        # Bi-directional data forwarding between client and target
        t1 = asyncio.create_task(self._forward(client_reader, remote_writer))
        t2 = asyncio.create_task(self._forward(remote_reader, client_writer))

        try:
            await asyncio.gather(t1, t2)
        finally:
            client_writer.close()
            remote_writer.close()
            logger.debug("Closed connection for client %s", peername)
