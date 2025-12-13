from dataclasses import dataclass
from qprism.types import Ring

@dataclass(frozen=True, slots=True)
class EpsPriority:
    """HTTP Priority header fields (RFC 9218).
    
    urgency: 0 (highest) to 7 (lowest)
    incremental: whether response can be delivered incrementally
    """
    urgency: int
    incremental: bool

def eps_from_ring(ring: Ring) -> EpsPriority:
    """Map viewport ring to HTTP priority.
    
    Ring distance maps to urgency (R0->0, R1->1, etc).
    Only R0 (most visible) uses incremental delivery.
    """
    urgency = max(0, min(7, int(ring)))
    incremental = ring == Ring.R0
    return EpsPriority(urgency=urgency, incremental=incremental)
