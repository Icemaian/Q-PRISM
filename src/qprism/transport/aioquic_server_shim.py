from aioquic.asyncio.server import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.quic.events import QuicEvent, ProtocolNegotiated
from aioquic.h3.events import HeadersReceived, DataReceived, H3Event
from aioquic.quic.configuration import QuicConfiguration
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import aiosqlite
import asyncio

Headers = List[Tuple[bytes, bytes]]

def _headers_to_dict(headers: Headers) -> Dict:
    return {k: v for k, v in headers}

class QPRISMServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, mb_tiles_path: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._http: Optional[H3Connection] = None
        self._db: Optional[aiosqlite.Connection] = None
        self._db_lock = asyncio.Lock()
        self.db = None
        if mb_tiles_path == "":
            self.mb_tiles_path = Path(__file__).parent.parent / "data/tiles/united_states_of_america.mbtiles"
        else:
            self.mb_tiles_path = mb_tiles_path

    async def get_db(self) -> aiosqlite.Connection:
        async with self._db_lock:
            if self._db is None:
                self._db = await aiosqlite.connect(str(self.mb_tiles_path))
            return self._db

    async def tile_data(self, z: int, x: int, y: int) -> bytes:
        tms_y = ( 1 << z) -1 - y
        db = await self.get_db()
        cursor = await db.execute("SELECT tile_data from tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (z, x, tms_y))
        
        row = await cursor.fetchone()
        print(type(row))
        return row[0] if row else b""

    async def _handle_request(self, stream_id : int, headers: Headers) -> None:
        if self._http is None:
            return
        h = _headers_to_dict(headers)
        method = h.get(b":method", b"GET").decode(errors="ignore")
        path = h.get(b":path", b"/").decode(errors="ignore")
        if method != "GET":
            self._http.send_headers(stream_id, [(b":status", b"405")], end_stream = True)
            self.transmit()
            return
        try:
            parts = path.split("?")[0].strip("/").split("/")
            if len(parts) != 4 or parts[0] != "tiles":
                raise ValueError("bad path")
            z = int(parts[1])
            x = int(parts[2])
            y_str = parts[3].split('.')[0]
            y = int(y_str)

            data = await self.tile_data(z, x, y)
            if not data:
                self._http.send_headers(stream_id, [(b":status", b"404")], end_stream = True)
                self.transmit()
                return

            self._http.send_headers(
                stream_id,
                [
                    (b":status", b"200"),
                    (b"content-type", b"application/x-protobuf"),
                    (b"cache-control", b"public, max-age=60"),
                ]
            )

            self._http.send_data(stream_id, data, end_stream=True)
            self.transmit()

        except Exception:
            self._http.send_headers(stream_id, [(b":status", b"404")], end_stream=True)
            self.transmit()

    def _handle_h3_event(self, event: H3Event) -> None:
        if isinstance(event, HeadersReceived):
            asyncio.create_task(self._handle_request(event.stream_id, event.headers))

    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, ProtocolNegotiated):
            if event.alpn_protocol.startswith("h3"):
                self._http = H3Connection(self._quic)
        if self._http is None:
            return
        for http_event in self._http.handle_event(event):
            self._handle_h3_event(http_event)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if self._db is not None:
            asyncio.create_task(self._db.close())
            self._db = None
        super().connection_lost(exc)

async def run_server():
    config = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    root_path = Path(__file__).parent.parent
    config.load_cert_chain(f"{root_path}/certs/cert.pem", f"{root_path}/certs/key.pem")
    await serve(
        "localhost", 4433,
        configuration = config,
        create_protocol = QPRISMServerProtocol
    )


if __name__ == "__main__":
    asyncio.run(run_server())
