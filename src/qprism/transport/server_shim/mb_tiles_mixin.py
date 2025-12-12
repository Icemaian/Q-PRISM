import asyncio
from pathlib import Path
from typing import Optional
import aiosqlite

class MbTilesMixin:
    def __init__(self, mbtiles_path: Path):
        self.mbtiles_path = mbtiles_path
        self._db: Optional[aiosqlite.Connection] = None
        self._db_lock = asyncio.Lock()

    async def get_db(self) -> aiosqlite.Connection:
        async with self._db_lock:
            if self._db is None:
                self._db = await aiosqlite.connect(str(self.mbtiles_path))
            return self._db

    async def tile_data(self, z: int, x: int, y: int) -> bytes:
        tms_y = (1 << z) - 1 - y
        db = await self.get_db()
        cur = await db.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, tms_y),
        )
        row = await cur.fetchone()
        return row[0] if row else b""
