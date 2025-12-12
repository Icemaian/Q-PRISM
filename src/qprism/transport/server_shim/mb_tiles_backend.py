from pathlib import Path

from qprism.transport.server_shim.mb_tiles_mixin import MbTilesMixin

class MbTilesBackend(MbTilesMixin):
    def __init__(self, mbtiles_path: Path):
        super().__init__(mbtiles_path)

async def h2_get_tile_bytes(backend: MbTilesBackend, z: int, x: int, y: int) -> bytes:
    return await backend.tile_data(z, x, y)
