import argparse
import asyncio
from pathlib import Path
from qprism.config import load_base_config, load_experiment_config
from qprism.experiments.run import run_experiment

def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single Q-PRISM experiment YAML")
    parser.add_argument(
        "--experiment",
        required=True,
        help="Path to one experiment YAML, e.g. src/qprism/configs/experiments/qprism_full.yaml",
    )
    parser.add_argument("--interface", default="lo", help="tc interface for netem (default: lo)")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=4433, help="Server port for H3 (default: 4433)")
    parser.add_argument(
        "--mbtiles",
        default=None,
        help="Override MBTiles path (default: base.yaml default_tile_source)",
    )
    parser.add_argument("--no-netem", action="store_true", help="Do not apply tc netem")
    parser.add_argument("--dry-netem", action="store_true", help="Print tc commands only")
    args = parser.parse_args()

    repo = _repo_root()
    base = load_base_config()
    exp = load_experiment_config(Path(args.experiment))
    mbtiles_path = Path(args.mbtiles) if args.mbtiles else None

    asyncio.run(
        run_experiment(
            base=base,
            exp=exp,
            repo_root=repo,
            interface=args.interface,
            host=args.host,
            port=args.port,
            mbtiles_path=mbtiles_path,
            apply_netem=(not args.no_netem),
            dry_netem=args.dry_netem,
        )
    )

if __name__ == "__main__":
    main()
