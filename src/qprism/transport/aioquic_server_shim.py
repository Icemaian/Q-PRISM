from aioquic.asyncio.server import serve
from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.quic.events import QuicEvent
from aioquic.h3.events import HeadersReceived, DataReceived, H3Event
from aioquic.quic.configuration import QuicConfiguration
from pathlib import Path
import aiosqlite
import asyncio

class QPRISMServerProtocol :
    def __init__(self, mb_tiles_path: str = ""):
        self.db = None
        if mb_tiles_path == "":
            self.mb_tiles_path = Path(__file__).parent.parent / "data/tiles/united_states_of_america.mbtiles"
        else:
            self.mb_tiles_path = mb_tiles_path

    async def tile_data(self, z: int, x: int, y: int) -> bytes:
        if self.db is None:
            self.db = await aiosqlite.connect(self.mb_tiles_path)
        tms_y = ( 1 << z) -1 - y
        cursor = await self.db.execute("SELECT tile_data from tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (z, x, tms_y))
        row = await cursor.fetchone()
        return row[0] if row else b""

    async def handle_stream(self, stream_id:int, headers: list, conn: H3Connection):
        path = dict(headers).get(b":path", b"/").decode()
        try:
            _, z, x, y_ext = path.strip("/").split("/")
            y, _ = y_ext.split(".")
            tyle_bytes = await self.tile_data(int(z), int(x), int(y))
            conn.send_headers(stream_id, [(b":status", b"200"), (b"content-type", b"application/x-protobuf")])   
            conn.send_data(stream_id, tyle_bytes, end_stream=True)
        except Exception as e:
            conn.send_headers(stream_id, [(b":status", b'404')], end_stream=True)

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
