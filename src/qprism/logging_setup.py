from logging import config, getLogger, Logger, DEBUG
from pathlib import Path

from qprism.config import load_yaml


def configure_logging(config_path: str | Path = "configs/logging.yaml", verbose: bool = False) -> None:
    if config_path == "configs/logging.yaml":
        config_path = Path(__file__).parent / config_path
    cfg = load_yaml(config_path)
    config.dictConfig(cfg)
    if verbose:
        getLogger().setLevel(DEBUG)
def get_logger(name: str) -> Logger:
    return getLogger(name)
