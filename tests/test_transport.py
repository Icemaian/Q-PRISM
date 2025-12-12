import socket
import sqlite3
from pathlib import Path
from typing import Tuple

import asyncio
import pytest
from os.path import isfile
from aiohttp import web
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration

from qprism.transport.server_shim.factory import server_shim_init
from qprism.transport.server_shim.mb_tiles_backend import MbTilesBackend
from qprism.transport.clients.H2_client import fetch_tile_h2
from qprism.transport.clients.H3_client import fetch_tile_h3
from qprism.transport.clients.QPRISM_client import fetch_tile_qprism

def _mbtiles_path_from_test() -> Path:
    return Path(__file__).parent.parent / "src/qprism/data/tiles/united_states_of_america.mbtiles"

def _pick_any_xyz_tile(mbtiles_path: Path) -> Tuple[int, int, int]:
    con = sqlite3.connect(str(mbtiles_path))
    try:
        cur = con.execute("SELECT zoom_level, tile_column, tile_row FROM tiles LIMIT 1")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("MBTiles has no tiles")
        z, x, tms_y = int(row[0]), int(row[1]), int(row[2])
        y = (1 << z) - 1 - tms_y
        return z, x, y
    finally:
        con.close()

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])

def _cert_paths() -> Tuple[str, str]:
    root = Path(__file__).parent.parent / "src/qprism"
    cert = root / "certs" / "cert.pem"
    key = root / "certs" / "key.pem"
    if isfile(cert) and isfile(key): 
        return str(cert), str(key)
    else:
        raise FileNotFoundError(f'Could not find Cert or key at {root}/certs/')

async def _start_h2_test_server(backend: MbTilesBackend) -> Tuple[web.AppRunner, str]:
    async def handle(request: web.Request) -> web.Response:
        z = int(request.match_info["z"])
        x = int(request.match_info["x"])
        y = int(request.match_info["y"])
        data = await backend.tile_data(z, x, y)
        if not data:
            return web.Response(status=404, body=b"")
        headers = {
            "content-type": "application/x-protobuf",
            "cache-control": "public, max-age=60",
        }
        if data.startswith(b"\x1f\x8b"):
            headers["content-encoding"] = "gzip"
        return web.Response(status=200, body=data, headers=headers)

    app = web.Application()
    app.router.add_get(r"/tiles/{z:\d+}/{x:\d+}/{y:\d+}.pbf", handle)

    runner = web.AppRunner(app)
    await runner.setup()
    port = _free_port()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    return runner, f"http://127.0.0.1:{port}"

@pytest.mark.asyncio
async def test_h2_client_server_pair_smoke():
    mbtiles = _mbtiles_path_from_test()
    z, x, y = _pick_any_xyz_tile(mbtiles)
    tile_path = f"/tiles/{z}/{x}/{y}.pbf"

    backend = MbTilesBackend(mbtiles)
    runner, base_url = await _start_h2_test_server(backend)
    try:
        body = await asyncio.wait_for(fetch_tile_h2(base_url, tile_path), timeout=5.0)
        assert isinstance(body, (bytes, bytearray))
        assert len(body) > 0
    finally:
        await runner.cleanup()

@pytest.mark.asyncio
async def test_h3_client_server_pair_smoke():
    mbtiles = _mbtiles_path_from_test()
    z, x, y = _pick_any_xyz_tile(mbtiles)
    tile_path = f"/tiles/{z}/{x}/{y}.pbf"

    cert, key = _cert_paths()
    print(cert, key)
    quic_cfg = QuicConfiguration(is_client=False, alpn_protocols=["h3"])
    quic_cfg.load_cert_chain(str(cert), str(key))

    protocol_factory = server_shim_init("H3", mbtiles_path=mbtiles)

    port = _free_port()
    server = await serve("127.0.0.1", port, configuration=quic_cfg, create_protocol=protocol_factory)
    try:
        body = await asyncio.wait_for(fetch_tile_h3("127.0.0.1", port, tile_path), timeout=5.0)
        assert isinstance(body, (bytes, bytearray))
        assert len(body) > 0
    finally:
        server.close()

@pytest.mark.asyncio
async def test_qprism_client_server_pair_smoke():
    mbtiles = _mbtiles_path_from_test()
    z, x, y = _pick_any_xyz_tile(mbtiles)
    tile_path = f"/tiles/{z}/{x}/{y}.pbf"

    cert, key = _cert_paths()

    quic_cfg = QuicConfiguration(is_client=False, alpn_protocols=["h3"])
    quic_cfg.load_cert_chain(str(cert), str(key))

    protocol_factory = server_shim_init("QPRISM", mbtiles_path=mbtiles)

    port = _free_port()
    server = await serve("127.0.0.1", port, configuration=quic_cfg, create_protocol=protocol_factory)
    try:
        body = await asyncio.wait_for(fetch_tile_qprism("127.0.0.1", port, tile_path, urgency=0, incremental=True), timeout=5.0)
        assert isinstance(body, (bytes, bytearray))
        assert len(body) > 0
    finally:
        server.close()
