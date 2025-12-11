import os
import textwrap
import pytest
from pathlib import Path
from qprism.config import ExperimentConfig
from qprism.types import TileRequest, TileCompletion, Ring
from qprism.logging_sink.duckdb_logger import DuckDBLogger
from qprism.netem import profiles as netem_profiles
from qprism.netem import controller as netem_controller

def test_duckdb_logger_integration(tmp_path):
    db_file = tmp_path / "test_qprism.duckdb"
    DDB_logger = DuckDBLogger(db_file)
    DDB_logger.conn.execute("SELECT count(*) FROM runs").fetchone()
    DDB_logger.conn.execute("SELECT count(*) from tile_requests").fetchone()
    DDB_logger.conn.execute("SELECT count(*) FROM tile_completions").fetchone()
    DDB_logger.conn.execute("SELECT count(*) FROM viewport_samples").fetchone()
    exp_config = ExperimentConfig(
        name="test_experiment",
        scheduler_variant="http2_default",
        netem_profile="low_loss",
        trace_path=Path(__file__).parent.parent / 'src/qprism/data/traces/lu_trace.json',
        runs=3,
        seed_base=123,
        notes="test notes"
    )
    run_id = DDB_logger.log_run(exp_config)
    assert run_id == 1
    tile_req = TileRequest(
        tile_id="tile1",
        zoom=5,
        ring=Ring.R1,
        requested_at_ms=100
    )
    DDB_logger.log_tile_requested(run_id, tile_req)
    tile_comp = TileCompletion(
        tile_id="tile1",
        zoom=5,
        ring=Ring.R1,
        requested_at_ms=100,
        completed_at_ms=300,
        cancelled=False,
        bytes_transferred=5000
    )
    DDB_logger.log_tile_completed(run_id, tile_comp)
    DDB_logger.log_viewport_sample(run_id, timestamp_ms=150, completeness=0.075)
    run_row = DDB_logger.conn.execute(
        "SELECT experiment_name, scheduler_variant, netem_profile, trace, seed, notes FROM runs WHERE run_id =?",
        [run_id]
    ).fetchone()
    assert run_row == (
        exp_config.name,
        exp_config.scheduler_variant,
        exp_config.netem_profile,
        str(exp_config.trace_path),
        exp_config.seed_base,
        exp_config.notes

    )
    req_rows = DDB_logger.conn.execute("SELECT run_id, tile_id, zoom, ring, requested_at, FROM tile_requests").fetchall()
    assert req_rows == [(run_id, "tile1", 5, 1, 100)]
    comp_rows = DDB_logger.conn.execute(
        "SELECT run_id, tile_id, zoom, ring, requested_at, completed_at, cancelled, bytes_transferred FROM tile_completions"
    ).fetchall()
    assert comp_rows == [(run_id, "tile1", 5, 1, 100, 300, False, 5000)]
    sample_rows = DDB_logger.conn.execute(
        "SELECT run_id, ts_ms, completeness FROM viewport_samples"
    ).fetchall()
    assert sample_rows == [(run_id, 150, pytest.approx(0.075, rel=1e-9, abs=1e-9))]
    DDB_logger.close()

def test_netem_profiles_loading(tmp_path):
    yaml_content = textwrap.dedent("""\
            profiles:
                test_profile:
                    description: "Temporary test profile"
                    rtt_ms: 100
                    jitter_ms: 10
                    loss: 0.05
    """)
    profile_file = tmp_path / "temp_netem_profiles.yaml"
    profile_file.write_text(yaml_content)
    profile_file.write_text(yaml_content)
    profiles = netem_profiles.load_profiles(profile_file)
    assert "test_profile" in profiles
    p = profiles["test_profile"]
    assert p.name == "test_profile"
    assert p.rtt_ms == 100
    assert p.jitter_ms == 10
    assert pytest.approx(p.loss, rel=1e-9) == 0.05
    assert p.description == "Temporary test profile"

def test_netem_controller_commands():
    profiles = netem_profiles.load_profiles()
    profile = profiles["mid_loss"]
    cmd = netem_controller.apply_profile(profile, interface="lo", dry_run=True)
    cmd_str = " ".join(cmd)
    assert f"delay {profile.rtt_ms}ms" in cmd_str
    assert f"{profile.jitter_ms}ms" in cmd_str
    expected_loss = f"{int(profile.loss*100)}%"
    assert f"loss {expected_loss}" in cmd_str
    assert "distribution normal" in cmd_str
    no_jitter = netem_profiles.NetemProfile(
        name="no_jitter",
        rtt_ms=50,
        jitter_ms=0,
        loss=0.02,
        description="No Jitter")
    cmd2 = netem_controller.apply_profile(no_jitter, interface="lo", dry_run=True)
    cmd2_str = " ".join(cmd2)
    assert "delay 50ms" in cmd2_str
    assert "distribution normal" not in cmd2_str
    assert "loss 2%" in cmd2_str
    clear_cmd = netem_controller.clear(interface="lo", dry_run=True)
    assert clear_cmd == ["tc", "qdisc", "del", "dev", "lo", "root"]
    
