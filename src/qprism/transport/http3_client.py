from pathlib import Path
from aioquic.asyncio.client import connect
from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.quic.configuration import QuicConfiguration

async def fetch_tile_h3(server: str, port: int, tile_path: str):
    root_path = Path(__file__).parent.parent    
    config = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
    config.load_verify_locations(f"{root_path}/certs/cert.pem")
    async with connect(server, port, configuration=config) as client:
        quic = client._quic
        h3 = H3Connection(quic)
        stream_id = quic.get_next_available_stream_id()
        headers = [(b":method", b"GET"), (b":path", tile_path.encode()), (b"scheme", b"https"), (b":authority", server.encode())]
        h3.send_headers(stream_id, headers)
        h3.send_data(stream_id, b"", end_stream=True)
        await client.wait_closed()

