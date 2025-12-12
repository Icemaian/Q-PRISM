import random
from typing import List, Set

from qprism.types import Tile
from qprism.scheduler.policy_qprism import QPrismScheduler
from qprism.scheduler.policy_priority_only import PriorityOnlyScheduler
from qprism.scheduler.policy_cancel_only import CancelOnlyScheduler
from qprism.scheduler.rings import compute_ring, Viewport

# Centered viewport 
viewport: Viewport = (4,6,4,6,10)

# R0 tiles within viewport
tile_r0_a = Tile(5,5,10)
tile_r0_b = Tile(5,6,10)
tile_r0_c = Tile(6,5,10)
tile_r0_d = Tile(6,6,10)
R0_tiles: List[Tile] = [tile_r0_a, tile_r0_b, tile_r0_c, tile_r0_d]

# R1 tiles one tile away
tile_r1_a = Tile(4,5,10)
tile_r1_b = Tile(7,6,10)
tile_r1_c = Tile(5,4,10)
tile_r1_d = Tile(6,7,10)
R1_tiles: List[Tile] = [tile_r1_a, tile_r1_b, tile_r1_c, tile_r1_d]

# R2 tiles two tiles away
tile_r2_a = Tile(3,5,10)
tile_r2_b = Tile(5,3,10)
tile_r2_c = Tile(8,6,10)
tile_r2_d = Tile(6,8,10)
R2_tiles: List[Tile] = [tile_r2_a, tile_r2_b, tile_r2_c, tile_r2_d]

# R3 tiles three tiles away
tile_r3_a = Tile(2,5,10)
tile_r3_b = Tile(5,2,10)
tile_r3_c = Tile(9,6,10)
tile_r3_d = Tile(6,9,10)
R3_tiles: List[Tile] = [tile_r3_a, tile_r3_b, tile_r3_c, tile_r3_d]

all_needed_tiles: List[Tile] = R0_tiles + R1_tiles + R3_tiles

tile_inflight_needed1 = tile_r0_a
tile_inflight_needed2 = tile_r0_b

tile_inflight_out1 = Tile(10, 10, 10)
tile_inflight_out2 = Tile(5, 5, 9)
tile_inflight_out3 = Tile(10, 10, 11)
outside_inflight_tiles: List[Tile] = [tile_inflight_out1, tile_inflight_out2, tile_inflight_out3]

initial_inflight_tiles: List[Tile] = [
    tile_inflight_needed1,
    tile_inflight_needed2,
    *outside_inflight_tiles
]

#Test tiles
first_tile = tile_r3_c
second_tile = tile_r0_b

other_tiles = [t for t in all_needed_tiles if t not in (first_tile, second_tile)]
random.shuffle(other_tiles)
available_tiles: List[Tile] = [first_tile, second_tile] + other_tiles

qprism_scheduler = QPrismScheduler()
priority_scheduler = PriorityOnlyScheduler()
cancel_scheduler = CancelOnlyScheduler()

# Add tiles to each scheduler
for tile in initial_inflight_tiles:
    qprism_scheduler.inflight_tracker.add(tile)
    priority_scheduler.inflight_tracker.add(tile)
    cancel_scheduler.inflight_tracker.add(tile)
    
q_to_load, q_to_cancel = qprism_scheduler.schedule(viewport, available_tiles)
p_to_load, p_to_cancel = priority_scheduler.schedule(viewport, available_tiles)
c_to_load, c_to_cancel = cancel_scheduler.schedule(viewport, available_tiles)
needed_new_set: Set[Tile] = set(all_needed_tiles) - {tile_inflight_needed1, tile_inflight_needed2}

# Q-PRISM Policy checks
assert set(q_to_cancel) == set(outside_inflight_tiles), "QPrism to_cancel should be the outside/stale tiles"
assert set(q_to_load) == needed_new_set, "QPrism to_load should be all needed tiles not already in flight"
q_rings = [compute_ring(t, viewport) for t in q_to_load]
assert q_rings == sorted(q_rings), "QPrism to_load tiles should be sorted by urgency rings"
assert qprism_scheduler.inflight_tracker.is_in_flight(tile_inflight_needed1)
assert qprism_scheduler.inflight_tracker.is_in_flight(tile_inflight_needed2)
assert tile_inflight_needed1 not in q_to_load and tile_inflight_needed2 not in q_to_load
for t in outside_inflight_tiles:
    assert not qprism_scheduler.inflight_tracker.is_in_flight(t)
    
# Priority-only Policy Checks
assert p_to_cancel == [], "Priority-only should not cancel any tiles"
assert set(p_to_load) == needed_new_set, "Priority-only to_load should be all needed tiles not in flight"
p_rings = [compute_ring(t, viewport) for t in p_to_load]
assert p_rings == sorted(p_rings), "Priority-only to_load tiles should be sorted by urgency"
for t in outside_inflight_tiles:
    assert priority_scheduler.inflight_tracker.is_in_flight(t)
assert priority_scheduler.inflight_tracker.is_in_flight(tile_inflight_needed1)
assert priority_scheduler.inflight_tracker.is_in_flight(tile_inflight_needed2)
assert tile_inflight_needed1 not in p_to_load and tile_inflight_needed2 not in p_to_load

# Cancel-only Polciy
assert set(c_to_cancel) == set(outside_inflight_tiles), "Cancel-only to_cancel should cancel the outside/stale tiles"
assert set(c_to_load) == needed_new_set, "Cancel-only to_load should be all needed tiles not in flight"
assert compute_ring(c_to_load[0], viewport) == 3, "First Cancel-only to_loadtile should be ring3 (from input order)"
ring_values = [compute_ring(t,viewport) for t in c_to_load]
assert 0 in ring_values, "Cancel-only to_load should include some R0 tiles"
first_ring = ring_values[0]
min_ring_later = min(ring_values[1:]) if len(ring_values) > 1 else first_ring
assert first_ring > min_ring_later, "Cancel-only to_load order is not sorted by ring urgency"
assert cancel_scheduler.inflight_tracker.is_in_flight(tile_inflight_needed1)
assert cancel_scheduler.inflight_tracker.is_in_flight(tile_inflight_needed2)
assert tile_inflight_needed1 not in c_to_load and tile_inflight_needed2 not in c_to_load
for t in outside_inflight_tiles:
    assert not cancel_scheduler.inflight_tracker.is_in_flight(t)


