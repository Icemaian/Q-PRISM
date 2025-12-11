CREATE SEQUENCE seq_run_id START 1;

CREATE TABLE runs (
	run_id INTEGER PRIMARY KEY DEFAULT nextval('seq_run_id'),
	experiment_name TEXT,
	scheduler_variant TEXT,
	netem_profile TEXT,
	trace TEXT,
	seed INTEGER,
	notes TEXT
);

CREATE TABLE tile_requests (
	run_id INTEGER REFERENCES runs(run_id),
	tile_id TEXT,
	zoom INTEGER,
	ring INTEGER,
	requested_at INTEGER,
	PRIMARY KEY (run_id, tile_id, requested_at)
);

CREATE TABLE tile_completions (
	run_id INTEGER REFERENCES runs(run_id),
	tile_id TEXT,
	zoom INTEGER,
	ring INTEGER,
	requested_at INTEGER,
	completed_at INTEGER,
	cancelled BOOLEAN,
	bytes_transferred INTEGER,
	PRIMARY KEY (run_id, tile_id, requested_at)
);

CREATE TABLE viewport_samples (
	run_id INTEGER REFERENCES runs(run_id),
	ts_ms INTEGER,
	completeness DOUBLE
);
