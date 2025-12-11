import os
import json
from dataclasses import dataclass

@dataclass
class TracePoint:
    t_ms: int
    lat: float
    lon: float
    zoom: int

def load_trace(trace_path: str):
    if not os.path.isfile(trace_path):
        raise FileNotFoundError(f'Could not find trace file: {trace_path}')
    with open(trace_path, 'r') as f:
        points = json.load(f)

    trace = []
    for pt in points:
        if all(k in pt for k in ("t_ms", "lat", "lon", "zoom")):
            trace.append(TracePoint(
                t_ms = int(pt['t_ms']),
                lat = float(pt['lat']),
                lon = float(pt['lon']),
                zoom = int(pt['zoom'])
            ))
        else:
            raise ValueError(f"Trace point is missing required fields: {pt}")
    trace.sort(key=lambda p: p.t_ms)
    return trace
