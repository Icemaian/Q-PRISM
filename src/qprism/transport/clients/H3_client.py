from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration
from .H3_util import H3BaseClient, build_client_config, make_h3_headers

async def fetch_tile_h3( server: str, port: int, tile_path: str, *, config: QuicConfiguration | None = None) -> bytes:
    cfg = config or build_client_config()
    cfg.verify_mode = False
    headers = make_h3_headers(server, tile_path)
    proto_holder = []

    def create_protocol(*a, **k):
        proto = H3BaseClient(*a, request_headers=headers, **k)
        proto_holder.append(proto)
        return proto

    async with connect(server, port, configuration=cfg, create_protocol=create_protocol) as client:
        proto = proto_holder[0]
        body = await proto.wait_body()
        client.close()
        return body
