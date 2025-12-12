from __future__ import annotations
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration
from .H3_util import H3BaseClient, build_client_config, make_h3_headers

def _priority_value(urgency: int, incremental: bool) -> bytes:
    u = max(0, min(7, int(urgency)))
    s = f"u={u}" + (", i" if incremental else "")
    return s.encode()

async def fetch_tile_qprism( server: str, port: int, tile_path: str, *, urgency: int = 0, incremental: bool = False, config: QuicConfiguration | None = None ) -> bytes:
    cfg = config or build_client_config()
    cfg.verify_mode = False
    extra = [(b"priority", _priority_value(urgency, incremental))]
    headers = make_h3_headers(server, tile_path, extra=extra)
    proto_holder: dict[str, H3BaseClient] = {}

    def make_proto(*a, **k):
        p = H3BaseClient(*a, request_headers=headers, **k)
        proto_holder["p"] = p
        return p

    async with connect(server, port, configuration=cfg, create_protocol=make_proto) as client:
        proto = proto_holder["p"]
        body = await proto.wait_body()
        await client.wait_closed()
        return body
