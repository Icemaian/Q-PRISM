import os
import json
import subprocess
from pathlib import Path
import gzip, shutil, urllib.request, os

def linear_interpolation(a, b, t):
    return a + (b - a) * t

def interpolate_points(p0, p1, steps):
    for i in range(steps):
        t = i / float(steps)
        yield (
            linear_interpolation(p0[0], p1[0], t),
            linear_interpolation(p0[1], p1[1], t)
        )

def fetch_country_tiles_files(country: str = "united_states_of_america") -> None:
    url = f"https://hot-qa-tiles-us-east-1.s3.amazonaws.com/latest.country/{country}.mbtiles.gz"
    dst_gz = Path(__file__).parent.parent / Path(f"src/qprism/data/tiles/{country}.mbtiles.gz")
    if os.path.isfile(dst_gz):
        print("File already fetched, skipping")
        return None
    dst_gz.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dst_gz)
    with gzip.open(dst_gz, "rb") as src, dst_gz.with_suffix("").open("wb") as dst:
        shutil.copyfileobj(src, dst)
    os.remove(f"data/tiles/{country}.mbtiles.gz")

def generate_trace(waypoints, zoom=14, seconds_between=3, fps=10):
    frames = []
    ms_per_frame = int(1000 / fps)
    steps = seconds_between * fps
    t_ms = 0

    for i in range(len(waypoints) - 1):
        p0 = waypoints[i]
        p1 = waypoints[i+1]
        for (lon, lat) in interpolate_points(p0, p1, steps):
            frames.append({
                "t_ms": t_ms,
                "center_lon_lat": [lon, lat],
                "zoom": zoom,
            })
            t_ms += ms_per_frame

    final_lon, final_lat = waypoints [-1]
    frames.append({
        "t_ms": t_ms,
        "center_lon_lat": [final_lon, final_lat],
        "zoom": zoom,
    })

    return frames

def setup_self_signed_certs():
    cert_dir = Path(__file__).parent.parent / 'src/qprism/certs'
    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"

    if not cert_path.exists() or not key_path.exists():
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key_path), "-out", str(cert_path),
            "-days", "365", "-nodes",
            "-subj", "/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ], check=True)

def save_trace(frames, path): 
    Path(path).write_text(
            json.dumps({"frames": frames}, indent=2),
            encoding="utf-8"
    )
    print(f"Wrote {len(frames)} frames -> {path}")

if __name__ == "__main__":
    dc_trace = {
        "waypoints": [(-77.0559, 38.8893),(-77.0423, 38.8899), (-77.0352, 38.8895), (-77.0199, 38.8893), (-77.0091, 38.8899)],
        "zoom_level": 14,
        "name": 'dc_trace'
    }

    lu_trace = {
        "waypoints": [(-79.18345, 37.35031), (-79.18219, 37.34951), (-79.18034, 37.34874), (-79.17743, 37.35030), (-79.17603, 37.35096)],
        "zoom_level": 17,
        "name": 'lu_trace'
    }

    for trace in [lu_trace, dc_trace]:
        frames = generate_trace(
            trace['waypoints'],
            trace['zoom_level'],
            seconds_between=3,
            fps=10,
        )
        root_path = Path(__file__).parent.parent
        save_trace(frames, f"{root_path}/src/qprism/data/traces/{trace['name']}.json")
    print('Traces saved...')
    setup_self_signed_certs()
    print('Certs generated...')
    fetch_country_tiles_files()
    print('Tiles pulled...')
