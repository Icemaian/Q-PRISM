from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

@dataclass(slots=True)
class BaseConfig:
    experiment_root: Path
    duckdb_path: Path
    default_trace: Path
    default_tile_source: Path
    viewport_sample_hz: int
    viewport_complete_threshold: float
    stall_threshold_seconds: float

@dataclass(slots=True)
class ExperimentConfig:
    name: str
    scheduler_variant: str
    netem_profile: str
    trace_path: Path
    runs: int
    seed_base: int
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], root_path: str = "") -> "ExperimentConfig":
        if root_path == "":
            root_path = Path(__file__).parent
        required = ["name", "scheduler_variant", "netem_profile", "trace_path"]
        missing = [k for k in required if k not in data]
        if missing:
            raise KeyError(f"Expirement config missing required keys: {missing}")
        return cls(
            name=str(data["name"]),
            scheduler_variant=str(data["scheduler_variant"]),
            netem_profile=str(data["netem_profile"]),
            trace_path=Path(root_path / data["trace_path"]), 
            runs=int(data.get("runs", 1)),
            seed_base=int(data.get("seed_base", 0)),
            notes=str(data["notes"]) if "notes" in data else None,
        )

def load_yaml(path: str | Path) -> Dict[str, Any]:
    path = Path(path) if isinstance(path, str) else path 
    with path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data or {}

def load_base_config(path: str | Path ="configs/base.yaml") -> BaseConfig:
    if path == "configs/base.yaml":
        path = Path(__file__).parent / path
    raw = load_yaml(path)

    experiment_root = raw.get('experiment_root')
    if experiment_root is None:
        raise KeyError('Base config is missing/corrupted...')

    duckdb_path = raw.get('duckdb_path')
    default_trace = raw.get('default_trace')
    default_tile_source = raw.get('default_tile_source')

    if duckdb_path is None:
        raise KeyError("Base config missing duckdb_path")
    if default_trace is None:
        raise KeyError("Base config is missing default_trace")
    if default_tile_source is None:
        raise KeyError("Base config is missing default_tile_source")

    return BaseConfig(
        experiment_root=Path(experiment_root),
        duckdb_path=Path(duckdb_path),
        default_trace=Path(default_trace),
        default_tile_source=Path(default_tile_source),
        viewport_sample_hz=int(raw.get("viewport_sample_hz", 10)),
        viewport_complete_threshold=float(raw.get("viewport_complete_threshold", 0.95)),
        stall_threshold_seconds=float(raw.get("stall_threshold_seconds", 0.25))
    )
    
def load_experiment_config(path: str | Path) -> ExperimentConfig:
    return ExperimentConfig.from_dict(load_yaml(path))
