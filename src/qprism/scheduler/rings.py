from typing import Tuple
from qprism.types import Tile

Viewport = Tuple[int, int, int, int, int]

def compute_ring(tile: Tile, viewport: Viewport) -> int:
    # computes the ring distance for a tile relative to the viewport

    min_x, max_x, min_y, max_y, view_z = viewport
    tile_x, tile_y, tile_z = tile.x, tile.y, tile.z
    
    if tile_z != view_z:
        return 999
        
    if tile_x < min_x:
       dx = min_x - tile_x
    elif tile_x > max_x:
       dx = tile_x - max_x
    else:
        dx = 0
        
    if tile_y < min_y:
        dy = min_y - tile_y
    elif tile_y > max_y:
        dy = tile_y - max_y
    else:
        dy = 0
    return dx if dx > dy else dy

