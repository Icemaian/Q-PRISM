from enum import Enum
from pathlib import Path
from typing import Optional, Type, Union

from qprism.transport.server_shim.qprism_server import QPRISMServer
from qprism.transport.server_shim.base_H3_shim import BaseH3Shim
from qprism.transport.server_shim.mb_tiles_backend import MbTilesBackend

class ServerShimKind(str, Enum):
    H2 = "H2"
    H3 = "H3"
    QPRISM = "QPRISM"

def server_shim_init(
    kind: Union[ServerShimKind, str],
    *,
    mbtiles_path: Optional[Union[str, Path]] = None,
    protocol_kwargs: Optional[dict] = None,
):
    protocol_kwargs = protocol_kwargs or {}
    cfg_path = Path(mbtiles_path) if mbtiles_path is not None else None

    if isinstance(kind, str):
        kind = ServerShimKind(kind.upper())

    if kind is ServerShimKind.H2:
        return MbTilesBackend(cfg_path or Path("data/tiles/united_states_of_america.mbtiles"))

    protocol_cls: Type[object]
    if kind is ServerShimKind.H3:
        protocol_cls = BaseH3Shim
    elif kind is ServerShimKind.QPRISM:
        protocol_cls = QPRISMServer
    else:
        raise ValueError(f"Unsupported kind: {kind}")

    def _factory(*args, **kwargs):
        merged = dict(protocol_kwargs)
        merged.update(kwargs)
        if cfg_path is not None:
            merged["mbtiles_path"] = str(cfg_path)
        return protocol_cls(*args, **merged)

    return _factory
