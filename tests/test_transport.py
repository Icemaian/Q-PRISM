from pathlib import Path
from contextlib import suppress
import pytest
import asyncio

from qprism.transport.qprism_h3_client import fetch_tile_qprism
from qprism.transport.aioquic_server_shim import run_server


@pytest.mark.asyncio
async def test_qprism_h3_priority_format():
    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(1.0)

    server = "localhost"
    port = 4433
    tile_path = str(Path(__file__).parent / "src/qprism/data/tiles/united_states_of_america.mbtiles")

    try:
        await fetch_tile_qprism(server, port, tile_path, urgency=1, incremental=True)
    finally:
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task
