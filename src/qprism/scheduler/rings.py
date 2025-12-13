from typing import Set, Tuple
from qprism.types import Ring, Tile

Viewport = Tuple[int, int, int, int, int]

def compute_ring(tile: Tile, viewport: Viewport) -> int:
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

    return max(dx, dy)

def ring_enum(tile: Tile, viewport: Viewport) -> Ring:
    dist = compute_ring(tile, viewport)
    return Ring.R3 if dist > 3 else Ring(dist)

def viewport_from_visible(visible_xy: Set[Tuple[int, int]], zoom: int) -> Viewport:
    xs = [x for x, _ in visible_xy]
    ys = [y for _, y in visible_xy]
    return (min(xs), max(xs), min(ys), max(ys), zoom)
