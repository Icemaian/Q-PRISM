from typing import Iterable, List, Tuple
from qprism.types import Tile
from qprism.scheduler.rings import compute_ring, Viewport
from qprism.scheduler.inflight_tracker import InflightTracker
from qprism.scheduler.fairness_gaurd import FairnessGaurd

class QPrismScheduler:
    def __init__(self) -> None:
        self.inflight_tracker = InflightTracker()
        self.fairness_gaurd = FairnessGaurd()
        
    def schedule(self, viewport: Viewport, tiles: Iterable[Tile]) -> Tuple[List[Tile], List[Tile]]:
        to_cancel: List[Tile] = []
        for in_tile in list(self.inflight_tracker.get_in_flight()):
            ring_distance = compute_ring(in_tile, viewport)
            if ring_distance > 3:
                self.inflight_tracker.cancel(in_tile)
                to_cancel.append(in_tile)
                self.fairness_gaurd.reset([in_tile])
                
        canidates: List[Tile] = []
        for tile in tiles:
            if not self.inflight_tracker.is_in_flight(tile):
                ring_distance = compute_ring(tile, viewport)
                if ring_distance <= 3:
                    canidates.append(tile)
        canidates.sort(key=lambda t: compute_ring(t, viewport))
        canidates = self.fairness_gaurd.promote(canidates)
        
        to_load: List[Tile] = canidates
        waiting: List[Tile] = []
        
        if waiting:
            self.fairness_gaurd.record_skips(waiting)
            
        for tile in to_load:
            self.inflight_tracker.add(tile)
        self.fairness_gaurd.reset(to_load)
        return to_load, to_cancel

