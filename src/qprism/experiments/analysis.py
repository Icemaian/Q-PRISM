from typing import Dict, Any
import duckdb
from qprism.metrics import *

def compute_run_metrics(conn, run_id: int) -> Dict[str, Any]:
    samples = conn.execute(f"SELECT ts_ms, completeness FROM viewport_samples WHERE run_id = {run_id}").fetchall()
    requests = conn.execute(f"SELECT ring, requested_at FROM tile_requests WHERE run_id = {run_id}").fetchall()
    completions = conn.execute(f"SELECT ring, requested_at, completed_at, cancelled FROM tile_completions WHERE run_id ={run_id}").fetchall()

    ttfv = time_to_first_viewport(samples)
    vss = viewport_stall_seconds(samples)

    latencies = [comp - req for (_r, req, comp, c) in completions if not c]
    lats = latency_percentiles(latencies)

    cancel = cancel_ratio(len(requests), sum(1 for (t, comp) in requests if t is None))

    r0s = [(req, comp) for (_r, req, comp, c) in completions if _r ==0]
    nonr0s = [comp for (t,comp) in requests if t > 0]
    fairness = fairness_gaurd_rate(r0s, nonr0s)

    return {
        "ttfv": ttfv, "vss": vss,
        **lats, "cancel_ratio": cancel,
        "fairness_gaurd_rate": fairness
    }

def aggregate_metrics(metrics: List[Dict]) -> Dict[str, Dict[str, float]]:
    result = {}
    for key in metrics[0].keys():
        values = [m[key] for m in metrics if m[key] is not None]
        if values:
            result[key] = {
                "mean": mean(values),
                "stdev": stdev(values) if len(values) > 1 else 0.0,
                "count": len(values)
            }
        else:
            result[key] = {"mean": None, "stdev":None, "count": 0}
    return result
