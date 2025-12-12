from typing import Dict, Iterable, List, Tuple
from qprism.types import Tile
 
TileKey= Tuple[int, int, int]

class FairnessGaurd:
    def __init__(self, threshold: int = 3) -> None:
        self.skip_counts: Dict[TileKey, int] = {}
        self.threshold: int = threshold
        
    def _key(self, tile: Tile) -> TileKey:
       return (tile.z, tile.x, tile.y)
       
    def record_skips(self, tiles: Iterable[Tile]) -> None:
       for tile in tiles:
           key = self._key(tile)
           self.skip_counts[key] = self.skip_counts.get(key, 0) + 1
    
    def reset(self, tiles: Iterable[Tile]) -> None:
        for tile in tiles:
            self.skip_counts.pop(self._key(tile), None)

    def promote(self, tasks: List[Tile]) -> List[Tile]:
       for idx, tile in enumerate(tasks):
           key = self._key(tile)
           count = self.skip_counts.get(key, 0)
           if count >= self.threshold:
               tasks.insert(0, tasks.pop(idx))
               break
       return tasks
