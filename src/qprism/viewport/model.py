import math
import mercantile

TILE_SIZE_PX = 256 # Tile size in pixels

def latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    # Converts lat long into EPSG:3857 aka web mercator projection
    tile = mercantile.tile(lon, lat, zoom)
    return float(tile.x), float(tile.y)

def visible_tile_coords(lat: float, lon: float, zoom: int, viewport_height_px: int = 600, viewport_width_px: int = 800) -> set:
    """
    Takes a viewport center and computes the set of tile coordinates that are visible

    The logic comes from the web Mercator "worl pixel" model from the slippy /xyz tiling scheme as used by OSM, Mapbox, and leaflet. 
    """
    x_center, y_center = latlon_to_tile(lat, lon, zoom)
    global_px_x = x_center * TILE_SIZE_PX
    global_px_y = y_center * TILE_SIZE_PX

    half_w = viewport_width_px / 2.0
    half_h = viewport_height_px / 2.0
    left_px = global_px_x - half_w
    right_px = global_px_x + half_w
    top_px = global_px_y - half_h
    bottom_px = global_px_y + half_h

    x_min = math.floor(left_px / TILE_SIZE_PX)
    y_min = math.floor(top_px / TILE_SIZE_PX)
    x_max = math.floor(right_px / TILE_SIZE_PX)
    y_max = math.floor(bottom_px / TILE_SIZE_PX)

    visible_tiles = set()
    for ty in range(y_min, y_max + 1):
        if 0 <= ty < 2 ** zoom:
            for tx in range(x_min, x_max+1):
                n = 2 ** zoom
                tx_mod = ((tx % n) + n) % n
                visible_tiles.add((tx_mod, ty))
    return visible_tiles
