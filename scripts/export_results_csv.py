import csv, os, argparse
from qprism.experiments.analysis import compute_run_metrics, aggregate_metrics
import duckdb

def export(db_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    conn = duckdb.connect(db_path, read_only=True)
    runs = conn.execute("SELECT run_id FROM runs").fetchall()
    per_run = [compute_run_metrics(conn, run_id) for (run_id,) in runs]
    summary = aggregate_metrics(per_run)

    for metric, data in summary.items():
        with open(os.path.join(out_dir, f"{metric}.csv"), 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "mean", "stdev", "count"])
            writer.writerow([metric, data['mean'], data['stdev'], data['count']])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    export(args.db, args.out)


