from pathlib import Path
import duckdb

from qprism.config import ExperimentConfig
from qprism.types import TileRequest, TileCompletion

class DuckDBLogger:
    def __init__(self, db_path: str | Path):
        if isinstance(db_path, Path): # Set path and allow for in memory storage
            self.db_path = db_path
        else:
            self.db_path = Path(db_path) if db_path != ':memory:' else db_path

        self.conn = duckdb.connect(str(self.db_path))

        try:
            # check if database initialized
            self.conn.execute("SELECT 1 FROM runs LIMIT 1")
        except Exception:
            schema_file = Path(__file__).parent / "schema.sql"
            schema_sql = schema_file.read_text()

            for stmt in schema_sql.split(';'):
                if stmt.strip():
                    self.conn.execute(stmt)
            self.conn.commit()

    def log_run(self, experiment: ExperimentConfig, run_idx: int = 0) -> int:
        actual_seed = experiment.seed_base + run_idx
        result = self.conn.execute(
            "INSERT INTO runs (experiment_name, scheduler_variant, netem_profile, trace, seed, notes) "
            "VALUES (?, ?, ?, ?, ?, ?) RETURNING run_id",
            (
                experiment.name,
                experiment.scheduler_variant,
                experiment.netem_profile,
                str(experiment.trace_path),
                actual_seed,
                experiment.notes
            )
        ).fetchone()
        run_id = result[0]
        self.conn.commit()
        return run_id

    def log_tile_requested(self, run_id: int, tile_req: TileRequest) -> None:
        self.conn.execute(
            "INSERT INTO tile_requests (run_id, tile_id, zoom, ring, requested_at)"
            "VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                tile_req.tile_id,
                tile_req.zoom,
                int(tile_req.ring),
                tile_req.requested_at_ms
            )
        )
        self.conn.commit()

    def log_tile_completed(self, run_id: int, tile_comp: TileCompletion) -> None:
        self.conn.execute(
            "INSERT INTO tile_completions "
            "(run_id, tile_id, zoom, ring, requested_at, completed_at, cancelled, bytes_transferred) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                tile_comp.tile_id,
                tile_comp.zoom,
                int(tile_comp.ring),
                tile_comp.requested_at_ms,
                tile_comp.completed_at_ms,
                tile_comp.cancelled,
                tile_comp.bytes_transferred
            )
        )
        self.conn.commit()

    def log_viewport_sample(self, run_id: int, timestamp_ms: int, completeness: float) -> None:
        self.conn.execute(
            "INSERT INTO viewport_samples (run_id, ts_ms, completeness) VALUES (?, ?, ?)",
            (run_id, timestamp_ms, completeness)
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def __enter__(self):
        return self
