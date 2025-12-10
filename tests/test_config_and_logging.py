import logging
from pathlib import Path

from qprism.config import (
    load_yaml,
    load_base_config,
    load_experiment_config,
    BaseConfig,
    ExpirmentConfig,
)
from qprism.logging_setup import configure_logging, get_logger

def test_load_yaml_base_has_expected_keys() -> None:
    data = load_yaml("config/base.yaml")
    assert "duckdb_path" in data
    assert "default_trace" in data
    assert ("experiment_root" in data)

def test_load_base_config_normalize_types() -> None:
    base = load_base_config()
    assert isinstance(base, BaseConfig)
    assert isinstance(base.experiment_root, Path)
    assert isinstance(base.duckdb_path, Path)
    assert base.viewport_sample_hz > 0
    assert 0.0 < base.viewport_complete_threshold <= 1.0
    assert base.stall_threshold_seconds > 0.0

def test_load_experiment_config_h2_default() -> None:
    cfg = load_experiment_config("config/experiments/http2_default.yaml")
    assert isinstance(cfg, ExpirmentConfig)
    assert cfg.name == "http2_default"
    assert cfg.scheduler_variant == "http2_default"
    assert cfg.netem_profile == "low_loss"
    assert isinstance(cfg.trace_path, Path)
    assert cfg.trace_path == "data/traces/lu_trace.json"
    assert cfg.runs > 0
    assert cfg.seed_base >= 0

def test_configure_logging_and_get_logger(capsys) -> None:
    configure_logging()
    logger = get_logger("qprism.test.config")
    assert isinstance(logger, logging.Logger)
    logger.info("config/logging smoke test")

