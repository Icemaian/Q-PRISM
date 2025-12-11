from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import yaml

@dataclass(slots=True)
class NetemProfile:
    name: str
    rtt_ms: int
    jitter_ms: int
    loss: float
    description: str

def load_profiles(path: str | Path = "configs/netem_profiles.yaml") -> Dict[str, NetemProfile]:
    if isinstance(path, str):
        if path == "configs/netem_profiles.yaml":
            path = Path(__file__).parent.parent / path
        else:
            path = Path(path)
    
    data = {}

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles_dict = raw.get("profiles", raw)
    for name, vals in profiles_dict.items():
        if isinstance(vals, dict):
            data[name] = NetemProfile(
                name=name,
                rtt_ms=int(vals.get("rtt_ms", 0)),
                jitter_ms=int(vals.get("jitter_ms", 0)),
                loss=float(vals.get("loss", 0.0)),
                description=str(vals.get("description", ""))
            )
    return data
