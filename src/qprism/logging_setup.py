from logging import config, getLogger, Logger
from pathlib import Path

from .config import load_yaml


def configure_logging(config_path: str | Path = "configs/logging.yaml") -> None:
    if config_path == "configs/logging.yaml":
        config_path = Path(__file__).parent / config_path
    print(config_path)
    cfg = load_yaml(config_path)
    config.dictConfig(cfg)

def get_logger(name: str) -> Logger:
    return getLogger(name)
