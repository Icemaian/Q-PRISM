from qprism import metrics

def test_ttfv():
    assert metrics.time_to_first_viewport([(0, 0.5), (100, 0.99)]) == 100

def test_vss():
    samples = [(0, 1.0), (50, 0.0), (200, 1.0)]
    assert metrics.viewport_stall_seconds(samples) == 150

def test_percentiles():
    lat = [10, 20, 30, 40, 50]
    out = metrics.latency_percentiles(lat)
    assert out["p50"] == 30 and out["p95"] == 50

def test_cancel():
    assert metrics.cancel_ratio(10, 2) == 0.2

def test_fairness_gaurd():
    r0 = [(0, 100), (200, 300)]
    nonr0 = [50, 250, 400]
    assert metrics.fairness_gaurd_rate(r0, nonr0) == 1.0
