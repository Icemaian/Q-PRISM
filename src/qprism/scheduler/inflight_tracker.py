from typing import Dict, List, Tuple
from qprism.types import Tile

TileKey = Tuple[int, int, int]

class InflightTracker:
    def __init__(self) -> None:
        self._inflight: Dict[TileKey, Tile] = {}
        
    def _key(self, tile: Tile) -> TileKey:
        return (tile.z, tile.x, tile.y)

    def add(self, tile: Tile) -> None:
        self._inflight[self._key(tile)] = tile
        
    def remove(self, tile: Tile) -> None:
        self._inflight.pop(self._key(tile), None)
            
    def cancel(self, tile: Tile) -> None:
        self.remove(tile)
        
    def is_in_flight(self, tile: Tile) -> bool:
        return self._key(tile) in self._inflight
        
    def get_in_flight(self) -> List[Tile]:
        return list(self._inflight.values())

