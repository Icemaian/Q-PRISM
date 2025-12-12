from dataclasses import dataclass
from enum import Enum
from typing import Optional

@dataclass(frozen=True)
class Tile:
    x: int
    y: int
    z: int

    def __repr__(self):
        return f"Tile({self.x}, {self.y}, z={self.z})"

class Ring(int, Enum):
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3

class SchedulerVariant(str, Enum):
    HTTP2_DEFAULT = "http2_default"
    HTTTP3_DEFAULT = "http3_default"
    QPRISM_FULL = "qprism_full" 
    QPRISM_PRIORITY_ONLY = "qprism_priority_only"
    QPRISM_CANCEL_ONLY = "qprism_cancel_only"

@dataclass(slots=True)
class TileRequest:
    tile_id: str
    zoom: int
    ring: Ring
    requested_at_ms: int
    deadline_ms: Optional[int] = None

@dataclass(slots=True)
class TileCompletion:
    tile_id: str
    zoom: int
    ring: Ring
    requested_at_ms: int
    completed_at_ms: int
    cancelled: bool = False
    bytes_transferred: Optional[int] = None

