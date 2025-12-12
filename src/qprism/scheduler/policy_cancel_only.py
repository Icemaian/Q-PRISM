from typing import Iterable, List, Tuple
from qprism.types import Tile
from qprism.scheduler.rings import compute_ring, Viewport
from qprism.scheduler.inflight_tracker import InflightTracker

class CancelOnlyScheduler:
    def __init__(self) -> None:
        self.inflight_tracker = InflightTracker()
    
    def schedule(self, viewport: Viewport, tiles: Iterable[Tile]) -> Tuple[List[Tile], List[Tile]]:
        to_cancel: List[Tile] = []
        for in_tile in list(self.inflight_tracker.get_in_flight()):
            ring_distance = compute_ring(in_tile, viewport)
            if ring_distance > 3:
                self.inflight_tracker.cancel(in_tile)
                to_cancel.append(in_tile)
                
        to_load: List[Tile] = []
        for tile in tiles:
            if not self.inflight_tracker.is_in_flight(tile):
                ring_distance = compute_ring(tile, viewport)
                if ring_distance <= 3:
                    to_load.append(tile)
                    
        for tile in to_load:
            self.inflight_tracker.add(tile)
            
        return to_load, to_cancel

