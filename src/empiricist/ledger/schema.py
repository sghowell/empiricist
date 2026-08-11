"""SQLite DDL for the epistemic ledger (spec Appendix A)."""

PRAGMAS = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=10000;
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  problem TEXT NOT NULL,
  problem_version TEXT NOT NULL DEFAULT 'legacy',
  title TEXT NOT NULL,
  content_path TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN
    ('REFUTED','HEURISTIC','CONJECTURED','VERIFIED_N','CERTIFIED','FORMALIZED')),
  substatus TEXT,
  status_n INTEGER,
  coverage TEXT CHECK (coverage IN ('exhaustive', 'sampled') OR coverage IS NULL),
  created_at TEXT NOT NULL,
  run_id TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
  artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  claim_id TEXT REFERENCES claims(id),
  run_id TEXT REFERENCES runs(run_id),
  verifier TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  binary_hash TEXT NOT NULL,
  golden_suite_hash TEXT,
  verdict TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','ERROR','TIMEOUT')),
  details_json TEXT NOT NULL DEFAULT '{}',
  log_path TEXT,
  wall_s REAL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS certifications (
  verifier TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  binary_hash TEXT NOT NULL,
  golden_suite_hash TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','ERROR','TIMEOUT')),
  stamped_at TEXT NOT NULL,
  run_id TEXT,
  PRIMARY KEY (verifier, verifier_version, binary_hash)
);

CREATE TABLE IF NOT EXISTS certification_attempts (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  verifier TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  binary_hash TEXT NOT NULL,
  golden_suite_hash TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','ERROR','TIMEOUT')),
  stamped_at TEXT NOT NULL,
  run_id TEXT
);

CREATE TABLE IF NOT EXISTS edges (
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  rel TEXT NOT NULL CHECK (rel IN ('depends_on','refutes','generalizes','formalizes','golden_for'))
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  move TEXT NOT NULL,
  role TEXT,
  model TEXT,
  provider TEXT,
  reasoning_mode TEXT,
  reasoning_effort TEXT,
  auth_route TEXT,
  request_digest TEXT,
  response_digest TEXT,
  argv TEXT,
  seed INTEGER,
  config_hash TEXT,
  env_fingerprint TEXT,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  cache_read INTEGER NOT NULL DEFAULT 0,
  cost_usd REAL NOT NULL DEFAULT 0.0,
  peak_rss_mb REAL,
  exit_code INTEGER,
  started TEXT NOT NULL,
  ended TEXT,
  wall_s REAL
);

CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  problem TEXT NOT NULL DEFAULT 'legacy',
  problem_version TEXT NOT NULL DEFAULT 'legacy',
  statement TEXT NOT NULL,
  family TEXT,
  metric TEXT,
  scope_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS gates (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('REDUCE','PROOF_CAMPAIGN','ACCEPT_DRAFT','RELEASE')),
  artifact_id TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','approved','rejected')),
  opened_at TEXT NOT NULL,
  resolved_at TEXT,
  note TEXT
);

CREATE TABLE IF NOT EXISTS population (
  lc_orbit_key TEXT PRIMARY KEY,
  island INTEGER NOT NULL,
  cell TEXT NOT NULL,
  objective_vec TEXT NOT NULL,
  cert_hash TEXT,
  hit_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS evicted (
  lc_orbit_key TEXT NOT NULL,
  reason TEXT NOT NULL,
  dominated_by TEXT,
  ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_events (
  gen INTEGER NOT NULL,
  trigger TEXT NOT NULL,
  detail TEXT,
  ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pareto_frontier (
  lc_orbit_key TEXT PRIMARY KEY,
  objective_vec TEXT NOT NULL,
  frontier_version INTEGER NOT NULL
);

-- rowid may not appear in index DDL; SQLite indexes on rowid tables already
-- end with the implicit rowid tiebreaker, so (artifact_id, created_at)
-- satisfies "ORDER BY created_at, rowid" within an artifact with no sort.
CREATE INDEX IF NOT EXISTS idx_evidence_artifact
  ON evidence(artifact_id, created_at);

CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
"""
