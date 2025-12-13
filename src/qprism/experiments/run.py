import asyncio
import random
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from aiohttp import web
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration

from qprism.config import BaseConfig, ExperimentConfig
from qprism.eps import eps_from_ring
from qprism.logging_sink.duckdb_logger import DuckDBLogger
from qprism.netem import controller as netem_controller
from qprism.netem import profiles as netem_profiles
from qprism.scheduler.policy_cancel_only import CancelOnlyScheduler
from qprism.scheduler.policy_priority_only import PriorityOnlyScheduler
from qprism.scheduler.policy_qprism import QPrismScheduler
from qprism.scheduler.rings import Viewport, ring_enum, viewport_from_visible
from qprism.transport.clients.H2_client import fetch_tile_h2
from qprism.transport.clients.H3_client import fetch_tile_h3
from qprism.transport.clients.QPRISM_client import fetch_tile_qprism
from qprism.transport.server_shim.factory import server_shim_init
from qprism.transport.server_shim.mb_tiles_backend import MbTilesBackend
from qprism.types import Tile, TileCompletion, TileRequest
from qprism.viewport import model
from qprism.viewport.completeness import compute_completeness
from qprism.viewport.traces import TracePoint, load_trace

@dataclass(frozen=True)
class _TileKey:
    z: int
    x: int
    y: int

    def tile_id(self) -> str:
        return f"{self.x}_{self.y}"

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])

def _make_scheduler(variant: str):
    v = variant.lower()
    if v == "qprism_full":
        return QPrismScheduler()
    if v == "qprism_priority_only":
        return PriorityOnlyScheduler()
    if v == "qprism_cancel_only":
        return CancelOnlyScheduler()
    return None

def _load_certs(repo_root: Path) -> Tuple[Path, Path]:
    cert = repo_root / "src" / "qprism" / "certs" / "cert.pem"
    key = repo_root / "src" / "qprism" / "certs" / "key.pem"
    if not cert.is_file() or not key.is_file():
        raise FileNotFoundError(f"Missing certs: {cert}, {key}")
    return cert, key

async def _start_h2_server(mbtiles_path: Path) -> Tuple[web.AppRunner, str]:
    backend = MbTilesBackend(mbtiles_path)

    async def handle(request: web.Request) -> web.Response:
        z = int(request.match_info["z"])
        x = int(request.match_info["x"])
        y = int(request.match_info["y"])
        data = await backend.tile_data(z, x, y)
        if not data:
            return web.Response(status=404, body=b"")
        headers = {
            "content-type": "application/x-protobuf",
            "cache-control": "public, max-age=60",
        }
        if data.startswith(b"\x1f\x8b"):
            headers["content-encoding"] = "gzip"
        return web.Response(status=200, body=data, headers=headers)

    app = web.Application()
    app.router.add_get(r"/tiles/{z:\d+}/{x:\d+}/{y:\d+}.pbf", handle)

    runner = web.AppRunner(app)
    await runner.setup()
    port = _free_port()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    return runner, f"http://127.0.0.1:{port}"


async def _start_h3_server(
    kind: str,
    mbtiles_path: Path,
    host: str,
    port: int,
    repo_root: Path,
) -> asyncio.AbstractServer:
    cert, key = _load_certs(repo_root)
    quic_cfg = QuicConfiguration(is_client=False, alpn_protocols=["h3"])
    quic_cfg.load_cert_chain(str(cert), str(key))
    protocol_factory = server_shim_init(kind, mbtiles_path=mbtiles_path)
    return await serve(host, port, configuration=quic_cfg, create_protocol=protocol_factory)

@dataclass
class _ServerContext:
    h2_runner: Optional[web.AppRunner] = None
    h3_server: Optional[asyncio.AbstractServer] = None
    base_url: Optional[str] = None

async def _boot_server(
    variant: str,
    tiles_path: Path,
    host: str,
    port: int,
    repo_root: Path,
) -> _ServerContext:
    ctx = _ServerContext()
    v = variant.lower()

    if v == "http2_default":
        ctx.h2_runner, ctx.base_url = await _start_h2_server(tiles_path)
    elif v == "http3_default":
        ctx.h3_server = await _start_h3_server("H3", tiles_path, host, port, repo_root)
    else:
        ctx.h3_server = await _start_h3_server("QPRISM", tiles_path, host, port, repo_root)

    return ctx


async def _shutdown_server(ctx: _ServerContext) -> None:
    if ctx.h3_server is not None:
        ctx.h3_server.close()
        await asyncio.sleep(0.05)
    if ctx.h2_runner is not None:
        await ctx.h2_runner.cleanup()


async def _fetch_tile(
    tk: _TileKey,
    tr: TileRequest,
    variant: str,
    base_url: Optional[str],
    host: str,
    port: int,
) -> bytes:
    tile_path = f"/tiles/{tk.z}/{tk.x}/{tk.y}.pbf"

    if variant == "http2_default":
        assert base_url is not None
        return await fetch_tile_h2(base_url, tile_path)
    elif variant == "http3_default":
        return await fetch_tile_h3(host, port, tile_path)
    else:
        eps = eps_from_ring(tr.ring)
        return await fetch_tile_qprism(
            host, port, tile_path, urgency=eps.urgency, incremental=eps.incremental
        )


async def _run_single_trace(
    trace: List[TracePoint],
    scheduler,
    variant: str,
    base_url: Optional[str],
    host: str,
    port: int,
    run_id: int,
    ddb: DuckDBLogger,
    rng: random.Random,
) -> List[TileCompletion]:
    t0 = time.monotonic()
    requested: Set[_TileKey] = set()
    in_flight: Dict[_TileKey, asyncio.Task] = {}
    completions: List[TileCompletion] = []

    async def _fetch_and_record(tk: _TileKey, tr: TileRequest) -> None:
        try:
            body = await _fetch_tile(tk, tr, variant, base_url, host, port)
            completed_at_ms = int((time.monotonic() - t0) * 1000)
            tc = TileCompletion(
                tile_id=tk.tile_id(),
                zoom=tk.z,
                ring=tr.ring,
                requested_at_ms=tr.requested_at_ms,
                completed_at_ms=completed_at_ms,
                cancelled=False,
                bytes_transferred=len(body),
            )
            completions.append(tc)
            ddb.log_tile_completed(run_id, tc)

        except asyncio.CancelledError:
            completed_at_ms = int((time.monotonic() - t0) * 1000)
            tc = TileCompletion(
                tile_id=tk.tile_id(),
                zoom=tk.z,
                ring=tr.ring,
                requested_at_ms=tr.requested_at_ms,
                completed_at_ms=completed_at_ms,
                cancelled=True,
                bytes_transferred=0,
            )
            completions.append(tc)
            ddb.log_tile_completed(run_id, tc)
            raise
        finally:
            in_flight.pop(tk, None)

    for tp in trace:
        visible_xy = model.visible_tile_coords(tp.lat, tp.lon, tp.zoom)
        if not visible_xy:
            continue

        viewport = viewport_from_visible(visible_xy, tp.zoom)
        visible_tiles = [Tile(x, y, tp.zoom) for (x, y) in visible_xy]
        rng.shuffle(visible_tiles)

        if scheduler is None:
            to_cancel = []
            to_load = [t for t in visible_tiles if _TileKey(t.z, t.x, t.y) not in requested]
        else:
            to_load, to_cancel = scheduler.schedule(viewport, visible_tiles)

        for t in to_cancel:
            tk = _TileKey(t.z, t.x, t.y)
            task = in_flight.get(tk)
            if task and not task.done():
                task.cancel()

        for t in to_load:
            tk = _TileKey(t.z, t.x, t.y)
            if tk in requested:
                continue
            requested.add(tk)

            ring = ring_enum(t, viewport)
            tr = TileRequest(tile_id=tk.tile_id(), zoom=tk.z, ring=ring, requested_at_ms=int(tp.t_ms))
            ddb.log_tile_requested(run_id, tr)
            in_flight[tk] = asyncio.create_task(_fetch_and_record(tk, tr))

        await asyncio.sleep(0)

    if in_flight:
        await asyncio.wait(list(in_flight.values()), timeout=60.0)

    return completions


async def run_experiment(
    *,
    base: BaseConfig,
    exp: ExperimentConfig,
    repo_root: Path,
    interface: str = "lo",
    host: str = "127.0.0.1",
    port: int = 4433,
    mbtiles_path: Optional[Path] = None,
    apply_netem: bool = True,
    dry_netem: bool = False,
) -> None:
    profiles = netem_profiles.load_profiles()
    if exp.netem_profile not in profiles:
        raise KeyError(f"Unknown netem profile: {exp.netem_profile}")
    profile = profiles[exp.netem_profile]

    tiles_path = mbtiles_path or (repo_root / "src" / "qprism" / base.default_tile_source)
    if not tiles_path.is_file():
        raise FileNotFoundError(f"MBTiles not found: {tiles_path}")

    if apply_netem:
        netem_controller.apply_profile(profile, interface=interface, dry_run=dry_netem)

    base.duckdb_path.parent.mkdir(parents=True, exist_ok=True)

    ctx = await _boot_server(exp.scheduler_variant, tiles_path, host, port, repo_root)

    try:
        trace = load_trace(str(exp.trace_path))
        if not trace:
            raise ValueError(f"Trace is empty: {exp.trace_path}")

        scheduler = _make_scheduler(exp.scheduler_variant)

        with DuckDBLogger(base.duckdb_path) as ddb:
            for run_idx in range(exp.runs):
                run_id = ddb.log_run(exp, run_idx=run_idx)
                rng = random.Random(exp.seed_base + run_idx)

                completions = await _run_single_trace(
                    trace,
                    scheduler,
                    exp.scheduler_variant.lower(),
                    ctx.base_url,
                    host,
                    port,
                    run_id,
                    ddb,
                    rng,
                )

                comp_series = compute_completeness(trace, completions)
                for ts_ms, frac in comp_series:
                    ddb.log_viewport_sample(run_id, int(ts_ms), float(frac))

    finally:
        await _shutdown_server(ctx)
        if apply_netem:
            netem_controller.clear(interface=interface, dry_run=dry_netem)
