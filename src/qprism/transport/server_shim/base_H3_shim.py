import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import HeadersReceived, H3Event
from aioquic.quic.events import (
    ProtocolNegotiated,
    QuicEvent,
    StopSendingReceived,
    StreamReset,
)

from qprism.transport.server_shim.mb_tiles_mixin import MbTilesMixin

Headers = List[Tuple[bytes, bytes]]
CHUNK_BYTES = 16 * 1024
H3_REQUEST_CANCELLED = 0x010C


def _headers_to_dict(headers: Headers) -> Dict[bytes, bytes]:
    return {k: v for k, v in headers}


class BaseH3Shim(QuicConnectionProtocol, MbTilesMixin):
    def __init__(self, *args, mbtiles_path: str = "", **kwargs):
        QuicConnectionProtocol.__init__(self, *args, **kwargs)
        default_path = Path("data/tiles/united_states_of_america.mbtiles")
        MbTilesMixin.__init__(self, Path(mbtiles_path) if mbtiles_path else default_path)

        self._http: Optional[H3Connection] = None
        self._cancelled: set[int] = set()
        self._tasks: Dict[int, asyncio.Task] = {}

    def _is_cancelled(self, stream_id: int) -> bool:
        return stream_id in self._cancelled

    def _mark_cancelled(self, stream_id: int) -> None:
        self._cancelled.add(stream_id)

        task = self._tasks.pop(stream_id, None)
        if task is not None:
            task.cancel()

        self._quic.reset_stream(stream_id, H3_REQUEST_CANCELLED)
        self.transmit()

    def connection_lost(self, exc: Optional[Exception]) -> None:
        for t in list(self._tasks.values()):
            t.cancel()
        self._tasks.clear()

        if self._db is not None:
            asyncio.create_task(self._db.close())
            self._db = None

        super().connection_lost(exc)

    def _parse_tile_path(self, path: str) -> Tuple[int, int, int]:
        parts = path.split("?")[0].strip("/").split("/")
        if len(parts) != 4 or parts[0] != "tiles":
            raise ValueError("bad path")
        z = int(parts[1])
        x = int(parts[2])
        y = int(parts[3].split(".")[0])
        return z, x, y

    def _response_headers_for(self, data: bytes) -> Headers:
        hdrs: Headers = [
            (b":status", b"200"),
            (b"content-type", b"application/x-protobuf"),
            (b"cache-control", b"public, max-age=60"),
        ]
        if data.startswith(b"\x1f\x8b"):
            hdrs.append((b"content-encoding", b"gzip"))
        return hdrs

    async def _send_tile_bytes(self, stream_id: int, data: bytes) -> None:
        assert self._http is not None
        mv = memoryview(data)
        n = len(mv)
        off = 0

        while off < n:
            if self._is_cancelled(stream_id):
                return
            end = min(off + CHUNK_BYTES, n)
            self._http.send_data(stream_id, mv[off:end].tobytes(), end_stream=(end == n))
            self.transmit()
            off = end
            await asyncio.sleep(0)

    async def _handle_request(self, stream_id: int, headers: Headers) -> None:
        if self._http is None or self._is_cancelled(stream_id):
            return

        try:
            h = _headers_to_dict(headers)
            method = h.get(b":method", b"GET").decode(errors="ignore")
            path = h.get(b":path", b"/").decode(errors="ignore")

            if method != "GET":
                self._http.send_headers(stream_id, [(b":status", b"405")], end_stream=True)
                self.transmit()
                return

            z, x, y = self._parse_tile_path(path)
            data = await self.tile_data(z, x, y)

            if self._is_cancelled(stream_id):
                return

            if not data:
                self._http.send_headers(stream_id, [(b":status", b"404")], end_stream=True)
                self.transmit()
                return

            self._http.send_headers(stream_id, self._response_headers_for(data))
            await self._send_tile_bytes(stream_id, data)

        except asyncio.CancelledError:
            return
        except Exception:
            if self._http is not None and not self._is_cancelled(stream_id):
                self._http.send_headers(stream_id, [(b":status", b"404")], end_stream=True)
                self.transmit()
        finally:
            self._tasks.pop(stream_id, None)
            self._cancelled.discard(stream_id)

    def _admit_request(self, stream_id: int, headers: Headers) -> None:
        self._tasks[stream_id] = asyncio.create_task(self._handle_request(stream_id, headers))

    def _handle_h3_event(self, event: H3Event) -> None:
        if isinstance(event, HeadersReceived):
            if self._is_cancelled(event.stream_id) or event.stream_id in self._tasks:
                return
            self._admit_request(event.stream_id, event.headers)

    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, (StopSendingReceived, StreamReset)):
            self._mark_cancelled(event.stream_id)

        if isinstance(event, ProtocolNegotiated):
            if event.alpn_protocol.startswith("h3"):
                self._http = H3Connection(self._quic)

        if self._http is None:
            return

        for http_event in self._http.handle_event(event):
            self._handle_h3_event(http_event)
