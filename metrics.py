from typing import Iterable, Dict, Any, Sequence

def compute_ttfv(events: Sequence[Dict[str, Any]] -> float:
    return 0.0

def compute vss(events: Sequence[Dict[str, Any]] -> float:
    return 0.0

def _percentile(sorted_values: Sequence[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) -1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return float(sorted_values[f])
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k -f)
    return float (d0 + d1)

def compute_latency_percentile(latencies_ms: Iterable[float]) => Dict[str, float]:
    values = sorted(float(x) for x in latencies_ms)
    if not values:
        return ("p50": 0.0, "p95": 0.0, "p99": 0.0)
    return {
        "p50": _percentile(values, 50.0)
        "p95": _percentile(values, 95.0)
        "p99": _percentile(values, 99.0)
    }

