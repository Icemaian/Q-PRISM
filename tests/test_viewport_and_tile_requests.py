import math
import json
from qprism.viewport import model, traces, completeness
from qprism.types import TileRequest, TileCompletion, Ring

def test_visible_tile_coords_basic():
    tiles = model.visible_tile_coords(0.0, 0.0, 1)
    assert len(tiles) == 4
    expected_tiles = {(x, y) for x in range(2) for y in range(2)}
    assert tiles == expected_tiles

def test_latlon_to_tile_and_wrapping():
    lat = 0.0
    zoom = 2

    x1, y1 = model.latlon_to_tile(lat, -180.0, zoom)
    x2, y2 = model.latlon_to_tile(lat, 180.0, zoom)
    
    assert math.isclose(x1 % 1.0, 0.0, abs_tol=1e-6)
    assert math.isclose(x2 % 1.0, 0.0, abs_tol=1e-6)
    n = 2 ** zoom
    tx1 = math.floor(x1) % n
    tx2 = math.floor(x2) % n
    assert (int(x2) + 1) % (2**zoom) == 0
    #assert math.floor(x1) % (2**zoom) == math.floor(x2) % (2**zoom)

def test_generate_requests_and_completeness(tmp_path):
    trace_points = [
            {"t_ms": 0, "lat": 0.0, "lon": 0.0, "zoom": 12},
            {"t_ms": 2000, "lat": 0.0, "lon": 90.0, "zoom": 12},
            {"t_ms": 3000, "lat": -75.0, "lon": 90.0, "zoom": 12}
    ]
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace_points))
    loaded_trace = traces.load_trace(str(trace_path))
    tile_requests = completeness.generate_tile_requests(loaded_trace)
    req_times = {req.requested_at_ms for req in tile_requests}
    assert 0 in req_times and 2000 in req_times

    seen_tiles = set()
    for req in tile_requests:
        assert isinstance(req, TileRequest)
        assert req.zoom in (12,)
        assert req.ring in (Ring.R0, Ring.R1, Ring.R2, Ring.R3)
        key = (req.zoom, req.tile_id)
        assert key not in seen_tiles
        seen_tiles.add(key)
    completions = []
    for req in tile_requests:
        completions.append(TileCompletion(
            tile_id=req.tile_id, 
            zoom=req.zoom,
            ring=req.ring,
            requested_at_ms=req.requested_at_ms,
            completed_at_ms=req.requested_at_ms + 1000,
            cancelled = False
        ))
    comp_series = completeness.compute_completeness(loaded_trace, completions)
    comp_dict = {t: frac for t, frac in comp_series}
    assert comp_dict.get(0, None) == 0.0
    assert math.isclose(comp_dict.get(1000, 0.0), 0.0625, rel_tol = 1e-6)
    assert math.isclose(comp_dict.get(2000, 0.0), 0.0, rel_tol = 1e-6)

