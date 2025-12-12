import math
from typing import List, Tuple
from qprism.types import TileRequest, TileCompletion, Ring
from qprism.viewport import model
from qprism.viewport.traces import TracePoint

def generate_tile_requests(trace: List[TracePoint]) -> List[TileRequest]:
    # Comverts list of points (our trace) and returns the tile requests

    requests: List[TileRequest] = []
    requested_tiles = set()
    prev_visible = set()
    for i, tp in enumerate(trace):
        visible = model.visible_tile_coords(tp.lat, tp.lon, tp.zoom)
        new_tiles = visible if i == 0 else (visible - prev_visible)
        for (tx, ty) in sorted(new_tiles):
            tile_key = (tp.zoom, tx, ty)
            if tile_key in requested_tiles:
                continue
            x_float, y_float = model.latlon_to_tile(tp.lat, tp.lon, tp.zoom)
            cx = math.floor(x_float)
            cy = math.floor(y_float)
    
            dx = abs(tx -cx)
            dy = abs(ty - cy)

            dist = dx if dx >= dy else dy
            ring = Ring.R3 if dist > 3 else Ring(dist)
            tile_id = f"{tx}_{ty}"
            req = TileRequest(tile_id=tile_id, zoom=tp.zoom, ring=ring, requested_at_ms=tp.t_ms)
            requests.append(req)
            requested_tiles.add(tile_key)
        prev_visible = visible

    requests.sort(key=lambda r: r.requested_at_ms)
    return requests

def compute_completeness(trace: List[TracePoint], tile_completions: List[TileCompletion]) -> List[Tuple[int, float]]:
    completeness_series: List[Tuple[int, float]] = []
    trace = sorted(trace, key=lambda tp: tp.t_ms)
    completions = sorted(tile_completions, key=lambda tc: tc.completed_at_ms)
    needed_tiles = set()
    loaded_tiles = set()
    comp_idx = 0

    if trace:
        tp = trace[0]
        needed_tiles = {(tp.zoom, x, y) for (x,y) in model.visible_tile_coords(tp.lat, tp.lon, tp.zoom)}
        loaded_tiles.clear()
        initial_frac = 1.0 if not needed_tiles else 0.0
        completeness_series.append((tp.t_ms, initial_frac))

    for v_idx in range(1, len(trace) + 1):
        next_view_time = trace[v_idx].t_ms if v_idx < len(trace) else None
        while comp_idx < len(completions) and (next_view_time is None or completions[comp_idx].completed_at_ms <= next_view_time):
            tc = completions[comp_idx]
            comp_idx += 1
            try:
                tx_str, ty_str = tc.tile_id.split('_')
                tx_i, ty_i = int(tx_str), int(ty_str)
            except ValueError:
                continue
            tile_key = (tc.zoom, tx_i,ty_i)
            if tile_key in needed_tiles and not tc.cancelled:
                loaded_tiles.add(tile_key)
                frac = 1.0 if not needed_tiles else len(loaded_tiles) / len(needed_tiles)
                completeness_series.append((tc.completed_at_ms, frac))
            if next_view_time is not None:
                tp_next = trace[v_idx]
                needed_tiles = {(tp_next.zoom, x, y) for (x, y) in model.visible_tile_coords(tp_next.lat, tp_next.lon, tp_next.zoom)}
                loaded_tiles = {t for t in loaded_tiles if t in needed_tiles}
                frac = 1.0 if not needed_tiles else len(loaded_tiles) / len(needed_tiles)
                completeness_series.append((tp_next.t_ms, frac))
        completeness_series.sort(key=lambda x: x[0])
    return completeness_series
        

