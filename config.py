from pathlib import Path
from typing import Any, Dict

import yaml

def load_yaml(path: str | Path) -> Dict[str, Any]:
    path = Path(path) if isinstance(path, str) else path 
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_expirement_config(path: str | Path) -> Dict[str, Any]:
    return load_yaml(path)
