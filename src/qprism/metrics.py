from typing import List, Tuple, Dict, Optional
from statistics import mean, stdev

ViewportSample = Tuple[int, float]

def time_to_first_viewport(samples: List[ViewportSample], threshold: float = 0.98, motion_start: int = 0) -> Optional[int]:
    for t, comp in sorted(samples):
        if t >= motion_start and comp >= threshold:
            return t - motion_start
    return None

def viewport_stall_seconds(samples: List[ViewportSample], threshold: float = 0.98, debounce_ms: int = 100, motion_start: int = 0) -> int:
    total_stall = 0
    in_stall = False
    stall_start = 0

    for t, comp in sorted(samples):
        if t < motion_start:
            continue
        if comp < threshold:
            if not in_stall:
                in_stall = True
                stall_start = t
        else:
            if in_stall:
                duration = t - stall_start
                if duration >= debounce_ms:
                    total_stall += duration
                in_stall = False
    if in_stall:
        duration = samples[-1][0] - stall_start
        if duration >= debounce_ms:
            total_stall += duration
    return total_stall

def latency_percentiles(latencies: List[int], percentiles=(50, 95,99)) -> Dict[str, Optional[int]]:
    if not latencies:
        return {f"p{p}": None for p in percentiles}
    sorted_latencies = sorted(latencies)
    result = {}
    for p in percentiles:
        k = max(0, min(len(sorted_latencies) -1, int((p / 100) * len(sorted_latencies))))
        result[f"p{p}"] = sorted_latencies[k]
    return result

def cancel_ratio(total: int, cancelled: int) -> Optional[float]:
    return cancelled / total if total else None

def fairness_gaurd_rate(r0_intervals: List[Tuple[int, int]], nonr0_requests: List[int]) -> Optional[float]:
    if not r0_intervals:
        return None
    r0_intervals.sort()
    gaurd_events = 0
    for t in sorted(nonr0_requests):
        if any(start <= t <= end for start, end in r0_intervals):
            gaurd_events += 1
    return gaurd_events / len(r0_intervals)

