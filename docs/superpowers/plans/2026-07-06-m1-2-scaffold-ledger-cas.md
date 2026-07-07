# Empiricist M1–M2: Scaffold + Ledger + CAS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `uv`-managed src-layout Python package with the epistemic ledger (SQLite/WAL) and blake3 content-addressed store fully implemented and TDD'd — the system-of-record everything else writes through.

**Architecture:** `Store` (blake3 CAS on disk) + `Ledger` (one SQLite connection, one-transaction-per-transition; statuses change only alongside evidence rows; REFUTED is terminal). Pareto frontier with a monotone version counter lives in the ledger. Human gates and verifier certification stamps are ledger tables. Resume = reconcile orphaned runs + recompute spent budget from `runs`.

**Tech Stack:** Python ≥3.11, `uv`, `blake3`, stdlib `sqlite3`, `pytest`, `ruff`.

**Reference:** `docs/superpowers/specs/2026-07-06-empiricist-harness-design.md` (§3 layout, §4 ledger semantics, Appendix A schema, Appendix B types). This is Plan 1 of the milestone series; later milestones get their own plans once this lands.

**Branch:** `feat/m1-2-scaffold-ledger` off `docs/v0-design-spec` (docs PR merges first or together — no code dependency, but CLAUDE.md/spec should be in-tree).

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/empiricist/__init__.py`
- Create: `src/empiricist/ledger/__init__.py`
- Create: `tests/__init__.py` (empty)
- Create: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git switch docs/v0-design-spec && git switch -c feat/m1-2-scaffold-ledger
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "empiricist"
version = "0.1.0"
description = "A lightweight epistemic-ledger harness for the FT-FBQC open problems"
requires-python = ">=3.11"
dependencies = [
    "blake3>=1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/empiricist"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 3: Write `src/empiricist/__init__.py`**

```python
"""Empiricist: a lightweight epistemic-ledger harness for the FT-FBQC open problems."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Write `src/empiricist/ledger/__init__.py`**

```python
"""The epistemic ledger: SQLite system-of-record + supporting models."""
```

Create `tests/__init__.py` as an empty file.

- [ ] **Step 5: Write `CLAUDE.md`**

```markdown
# Empiricist — project instructions

AI harness attacking open problems in fault-tolerant fusion-based quantum
computation (FT-FBQC). **Source of truth:**
`docs/superpowers/specs/2026-07-06-empiricist-harness-design.md`.
Background: `docs/empiricist_harness.md`, `docs/open_problems_ftfbqc.md`.

## Commands

- `uv sync` — install env (Python ≥3.11)
- `uv run pytest` — run tests
- `uv run ruff check src tests` — lint

## Non-negotiables

- **Epistemic discipline:** nothing enters the ledger above HEURISTIC without
  machine evidence. Statuses change only alongside evidence rows. REFUTED is terminal.
- **TDD** for ledger and verifiers. Golden suites gate verifier certification.
- **The model never gets a shell.** Model output is structured JSON; the harness
  executes everything in the sandbox (`executor/`).
- **Provenance:** every subprocess/model call becomes a `runs` row; artifact IDs
  are blake3 content hashes; certificates embed exact version pins.
- Commit messages: descriptive, **no AI attribution** (no Co-Authored-By).
- Branch per milestone → PR → squash-merge to `main`. Never push to `main`.
- The ledger DB and CAS blobs live on local disk and are **never** committed.
```

- [ ] **Step 6: Update `README.md`**

```markdown
# empiricist

A lightweight harness that drives a frontier model against the open problems in
fault-tolerant fusion-based quantum computation (FT-FBQC), promoting claims up an
epistemic ledger (HEURISTIC → CONJECTURED → VERIFIED_N → CERTIFIED → FORMALIZED)
where every promotion is backed by a machine-checkable artifact.

- Problems: `docs/open_problems_ftfbqc.md`
- Harness design: `docs/empiricist_harness.md`
- Implementation spec (source of truth): `docs/superpowers/specs/2026-07-06-empiricist-harness-design.md`

## Development

```bash
uv sync
uv run pytest
```

v0 pilots **Problem 5**: minimum-fusion synthesis of graph states, `F(G)`, in the
GHZ₃ resource model.
```

- [ ] **Step 7: Lock, sync, sanity-run**

```bash
uv lock && uv sync
uv run python -c "import empiricist; print(empiricist.__version__)"
```

Expected: `0.1.0`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src tests CLAUDE.md README.md
git commit -m "feat: project scaffold (uv, src layout, pytest/ruff, CLAUDE.md)"
```

---

### Task 2: Content-addressed store (`store.py`)

**Files:**
- Create: `src/empiricist/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the blake3 content-addressed store."""

import pytest
from blake3 import blake3

from empiricist.store import Store


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "store")


def test_put_returns_blake3_hex_digest(store):
    digest = store.put(b"hello world")
    assert digest == blake3(b"hello world").hexdigest()
    assert len(digest) == 64


def test_put_then_get_roundtrips(store):
    digest = store.put(b"some content")
    assert store.get(digest) == b"some content"


def test_layout_is_sharded_by_prefix(store):
    digest = store.put(b"x")
    p = store.path_for(digest)
    assert p.parts[-4:] == ("blake3", digest[:2], digest[2:4], digest)
    assert p.exists()


def test_put_is_idempotent(store):
    d1 = store.put(b"same")
    d2 = store.put(b"same")
    assert d1 == d2


def test_exists(store):
    digest = store.put(b"here")
    assert store.exists(digest)
    assert not store.exists("0" * 64)


def test_get_missing_raises_keyerror(store):
    with pytest.raises(KeyError):
        store.get("0" * 64)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'empiricist.store'`

- [ ] **Step 3: Write `src/empiricist/store.py`**

```python
"""Blake3 content-addressed file store.

Layout: <root>/blake3/<hex[0:2]>/<hex[2:4]>/<hex64>. Writes are atomic
(temp file + os.replace) and idempotent: identical content maps to the
same path, so re-ingestion is free and the store is crash-safe.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from blake3 import blake3


class Store:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def path_for(self, digest: str) -> Path:
        return self.root / "blake3" / digest[:2] / digest[2:4] / digest

    def put(self, content: bytes) -> str:
        digest = blake3(content).hexdigest()
        target = self.path_for(digest)
        if target.exists():
            return digest
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return digest

    def get(self, digest: str) -> bytes:
        p = self.path_for(digest)
        if not p.exists():
            raise KeyError(digest)
        return p.read_bytes()

    def exists(self, digest: str) -> bool:
        return self.path_for(digest).exists()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_store.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/store.py tests/test_store.py
git commit -m "feat: blake3 content-addressed store with atomic idempotent writes"
```

---

### Task 3: Ledger models (`ledger/models.py`)

**Files:**
- Create: `src/empiricist/ledger/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for ledger model types."""

import pytest

from empiricist.ledger.models import (
    Budget,
    Status,
    Verdict,
    dominates,
    now_iso,
)


def test_status_members():
    assert {s.value for s in Status} == {
        "REFUTED", "HEURISTIC", "CONJECTURED", "VERIFIED_N", "CERTIFIED", "FORMALIZED",
    }


def test_verdict_members():
    assert {v.value for v in Verdict} == {"PASS", "FAIL", "ERROR", "TIMEOUT"}


def test_budget_is_frozen_with_optional_fields():
    b = Budget(wall_s=10.0)
    assert b.wall_s == 10.0 and b.tokens is None and b.rss_mb is None
    with pytest.raises(AttributeError):
        b.wall_s = 5.0  # type: ignore[misc]


def test_now_iso_is_utc_isoformat():
    ts = now_iso()
    assert ts.endswith("+00:00") and "T" in ts


class TestDominates:
    """Pareto dominance, minimizing every component."""

    def test_strictly_better_dominates(self):
        assert dominates([1, 1], [2, 2])

    def test_equal_does_not_dominate(self):
        assert not dominates([1, 1], [1, 1])

    def test_better_in_one_equal_in_other_dominates(self):
        assert dominates([1, 2], [1, 3])

    def test_incomparable_does_not_dominate(self):
        assert not dominates([1, 3], [2, 1])
        assert not dominates([2, 1], [1, 3])

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            dominates([1], [1, 2])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/ledger/models.py`**

```python
"""Ledger model types: statuses, verdicts, rows, and Pareto dominance.

The status lattice is per-claim epistemic strength (spec §4.1), not a
conveyor belt: dataset artifacts enter directly at VERIFIED_N. REFUTED
is terminal. Statuses change only alongside evidence rows (spec §4.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    REFUTED = "REFUTED"
    HEURISTIC = "HEURISTIC"
    CONJECTURED = "CONJECTURED"
    VERIFIED_N = "VERIFIED_N"
    CERTIFIED = "CERTIFIED"
    FORMALIZED = "FORMALIZED"


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Budget:
    wall_s: float | None = None
    tokens: int | None = None
    rss_mb: float | None = None


@dataclass(frozen=True)
class Artifact:
    id: str                      # blake3 of canonical content
    kind: str                    # statement|dataset|construction|certificate|proof_dag|lean|report
    problem: str                 # P1..P10 | shared
    title: str
    content_path: str            # CAS digest
    status: Status
    substatus: str | None = None  # PROVED_DRAFT | EXTERNAL | None
    status_n: int | None = None   # iff VERIFIED_N
    coverage: str | None = None   # 'exhaustive' | 'sampled' | None
    created_at: str = field(default_factory=now_iso)
    run_id: str | None = None


@dataclass(frozen=True)
class EvidenceRow:
    artifact_id: str
    verifier: str
    verifier_version: str
    binary_hash: str
    verdict: Verdict
    details: dict[str, Any] = field(default_factory=dict)
    log_path: str | None = None
    wall_s: float | None = None
    created_at: str = field(default_factory=now_iso)


@dataclass(frozen=True)
class Run:
    run_id: str
    move: str
    role: str | None = None
    model: str | None = None
    argv: str | None = None
    seed: int | None = None
    config_hash: str | None = None
    env_fingerprint: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cost_usd: float = 0.0
    peak_rss_mb: float | None = None
    exit_code: int | None = None
    started: str = field(default_factory=now_iso)
    ended: str | None = None
    wall_s: float | None = None


@dataclass(frozen=True)
class Gate:
    id: str
    kind: str                    # REDUCE|PROOF_CAMPAIGN|ACCEPT_DRAFT|RELEASE
    artifact_id: str
    state: str                   # pending|approved|rejected
    opened_at: str
    resolved_at: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Certification:
    verifier: str
    verifier_version: str
    binary_hash: str
    golden_suite_hash: str
    verdict: Verdict
    stamped_at: str = field(default_factory=now_iso)
    run_id: str | None = None


def dominates(a: list[float], b: list[float]) -> bool:
    """True iff objective vector `a` Pareto-dominates `b` (minimizing)."""
    if len(a) != len(b):
        raise ValueError(f"objective vectors differ in length: {len(a)} vs {len(b)}")
    return all(x <= y for x, y in zip(a, b, strict=True)) and any(
        x < y for x, y in zip(a, b, strict=True)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/ledger/models.py tests/test_models.py
git commit -m "feat: ledger model types (statuses, verdicts, rows, Pareto dominance)"
```

---

### Task 4: Schema + Ledger core (`ledger/schema.py`, `ledger/db.py`)

**Files:**
- Create: `src/empiricist/ledger/schema.py`
- Create: `src/empiricist/ledger/db.py`
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the SQLite ledger core: bootstrap, artifacts, evidence, transitions."""

import sqlite3

import pytest

from empiricist.ledger.db import Ledger, TerminalStatusError
from empiricist.ledger.models import Artifact, EvidenceRow, Status, Verdict
from empiricist.store import Store


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "store")


def make_artifact(store, content=b"claim: F(path_N) = N-3", **kw):
    digest = store.put(content)
    defaults = dict(
        id=digest, kind="statement", problem="P5", title="a claim",
        content_path=digest, status=Status.HEURISTIC,
    )
    defaults.update(kw)
    return Artifact(**defaults)


def make_evidence(artifact_id, verdict=Verdict.PASS, **kw):
    defaults = dict(
        artifact_id=artifact_id, verifier="stab_fusion", verifier_version="1.0",
        binary_hash="deadbeef", verdict=verdict, details={"n": 8},
    )
    defaults.update(kw)
    return EvidenceRow(**defaults)


def test_bootstrap_applies_wal_and_creates_tables(ledger):
    assert ledger.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    names = {
        r[0] for r in ledger.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "artifacts", "evidence", "certifications", "edges", "runs",
        "claims", "gates", "population", "evicted", "search_events",
        "pareto_frontier",
    } <= names


def test_add_and_get_artifact_roundtrips(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    got = ledger.get_artifact(art.id)
    assert got == art


def test_add_artifact_twice_raises(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    with pytest.raises(sqlite3.IntegrityError):
        ledger.add_artifact(art)


def test_record_evidence_without_status_change(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    ledger.record_evidence(make_evidence(art.id))
    assert ledger.get_artifact(art.id).status == Status.HEURISTIC
    evs = ledger.evidence_for(art.id)
    assert len(evs) == 1 and evs[0].details == {"n": 8}


def test_promotion_updates_status_atomically_with_evidence(ledger, store):
    art = make_artifact(store, kind="dataset")
    ledger.add_artifact(art)
    ledger.record_evidence(
        make_evidence(art.id),
        new_status=Status.VERIFIED_N, status_n=9, coverage="exhaustive",
    )
    got = ledger.get_artifact(art.id)
    assert got.status == Status.VERIFIED_N
    assert got.status_n == 9 and got.coverage == "exhaustive"


def test_status_change_requires_evidence_api_only(ledger, store):
    """There is no public method to set status without an evidence row."""
    assert not hasattr(ledger, "set_status")


def test_refuted_is_terminal(ledger, store):
    art = make_artifact(store)
    ledger.add_artifact(art)
    ledger.record_evidence(
        make_evidence(art.id, verdict=Verdict.FAIL, details={"counterexample": "C_5"}),
        new_status=Status.REFUTED,
    )
    with pytest.raises(TerminalStatusError):
        ledger.record_evidence(make_evidence(art.id), new_status=Status.CONJECTURED)


def test_record_evidence_for_unknown_artifact_raises(ledger):
    with pytest.raises(KeyError):
        ledger.record_evidence(make_evidence("0" * 64))


def test_edges(ledger, store):
    a = make_artifact(store, content=b"a")
    b = make_artifact(store, content=b"b")
    ledger.add_artifact(a)
    ledger.add_artifact(b)
    ledger.add_edge(a.id, b.id, "depends_on")
    assert ledger.edges_from(a.id) == [(a.id, b.id, "depends_on")]


def test_reopen_preserves_state(tmp_path, store):
    lg = Ledger(tmp_path / "ledger.db")
    art = make_artifact(store)
    lg.add_artifact(art)
    lg.close()
    lg2 = Ledger(tmp_path / "ledger.db")
    assert lg2.get_artifact(art.id) == art
    lg2.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/ledger/schema.py`**

```python
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
  title TEXT NOT NULL,
  content_path TEXT NOT NULL,
  status TEXT NOT NULL,
  substatus TEXT,
  status_n INTEGER,
  coverage TEXT CHECK (coverage IN ('exhaustive', 'sampled') OR coverage IS NULL),
  created_at TEXT NOT NULL,
  run_id TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
  artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  verifier TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  binary_hash TEXT NOT NULL,
  verdict TEXT NOT NULL,
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
  verdict TEXT NOT NULL,
  stamped_at TEXT NOT NULL,
  run_id TEXT,
  PRIMARY KEY (verifier, verifier_version, binary_hash)
);

CREATE TABLE IF NOT EXISTS edges (
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  rel TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  move TEXT NOT NULL,
  role TEXT,
  model TEXT,
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
  statement TEXT NOT NULL,
  family TEXT
);

CREATE TABLE IF NOT EXISTS gates (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
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
"""
```

- [ ] **Step 4: Write `src/empiricist/ledger/db.py`**

```python
"""The Ledger: single-writer SQLite system-of-record.

Discipline (spec §4.2, §4.4): one transaction per transition; statuses
change only via record_evidence(); REFUTED is terminal. The orchestrator
owns the single Ledger instance — workers post results to it, they never
open their own write connection.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from empiricist.ledger.models import (
    Artifact,
    EvidenceRow,
    Status,
    Verdict,
    now_iso,
)
from empiricist.ledger.schema import PRAGMAS, SCHEMA


class TerminalStatusError(Exception):
    """Raised on any attempt to change the status of a REFUTED artifact."""


class Ledger:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(PRAGMAS)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def _tx(self):
        """One BEGIN IMMEDIATE ... COMMIT per state transition."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except BaseException:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    # -- artifacts ---------------------------------------------------------

    def add_artifact(self, art: Artifact) -> None:
        with self._tx() as c:
            c.execute(
                "INSERT INTO artifacts (id, kind, problem, title, content_path, status,"
                " substatus, status_n, coverage, created_at, run_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (art.id, art.kind, art.problem, art.title, art.content_path,
                 art.status.value, art.substatus, art.status_n, art.coverage,
                 art.created_at, art.run_id),
            )

    def get_artifact(self, artifact_id: str) -> Artifact:
        row = self.conn.execute(
            "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            raise KeyError(artifact_id)
        return Artifact(
            id=row["id"], kind=row["kind"], problem=row["problem"], title=row["title"],
            content_path=row["content_path"], status=Status(row["status"]),
            substatus=row["substatus"], status_n=row["status_n"],
            coverage=row["coverage"], created_at=row["created_at"], run_id=row["run_id"],
        )

    # -- evidence & status transitions --------------------------------------

    def record_evidence(
        self,
        ev: EvidenceRow,
        *,
        new_status: Status | None = None,
        status_n: int | None = None,
        coverage: str | None = None,
        substatus: str | None = None,
    ) -> None:
        """Insert an evidence row; optionally change status in the same transaction.

        This is the ONLY way a status changes (F1: no promotion without
        machine evidence).
        """
        with self._tx() as c:
            row = c.execute(
                "SELECT status FROM artifacts WHERE id = ?", (ev.artifact_id,)
            ).fetchone()
            if row is None:
                raise KeyError(ev.artifact_id)
            if new_status is not None:
                if Status(row["status"]) is Status.REFUTED:
                    raise TerminalStatusError(
                        f"artifact {ev.artifact_id} is REFUTED (terminal)"
                    )
                c.execute(
                    "UPDATE artifacts SET status = ?,"
                    " status_n = COALESCE(?, status_n),"
                    " coverage = COALESCE(?, coverage),"
                    " substatus = COALESCE(?, substatus)"
                    " WHERE id = ?",
                    (new_status.value, status_n, coverage, substatus, ev.artifact_id),
                )
            c.execute(
                "INSERT INTO evidence (artifact_id, verifier, verifier_version,"
                " binary_hash, verdict, details_json, log_path, wall_s, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ev.artifact_id, ev.verifier, ev.verifier_version, ev.binary_hash,
                 ev.verdict.value, json.dumps(ev.details, sort_keys=True),
                 ev.log_path, ev.wall_s, ev.created_at),
            )

    def evidence_for(self, artifact_id: str) -> list[EvidenceRow]:
        rows = self.conn.execute(
            "SELECT * FROM evidence WHERE artifact_id = ? ORDER BY created_at, rowid",
            (artifact_id,),
        ).fetchall()
        return [
            EvidenceRow(
                artifact_id=r["artifact_id"], verifier=r["verifier"],
                verifier_version=r["verifier_version"], binary_hash=r["binary_hash"],
                verdict=Verdict(r["verdict"]), details=json.loads(r["details_json"]),
                log_path=r["log_path"], wall_s=r["wall_s"], created_at=r["created_at"],
            )
            for r in rows
        ]

    # -- edges ---------------------------------------------------------------

    def add_edge(self, src: str, dst: str, rel: str) -> None:
        with self._tx() as c:
            c.execute("INSERT INTO edges (src, dst, rel) VALUES (?, ?, ?)", (src, dst, rel))

    def edges_from(self, src: str) -> list[tuple[str, str, str]]:
        return [
            (r["src"], r["dst"], r["rel"])
            for r in self.conn.execute(
                "SELECT src, dst, rel FROM edges WHERE src = ?", (src,)
            )
        ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_ledger.py -v`
Expected: all PASS

- [ ] **Step 6: Run the full suite + lint**

Run: `uv run pytest && uv run ruff check src tests`
Expected: all PASS, no lint errors

- [ ] **Step 7: Commit**

```bash
git add src/empiricist/ledger/schema.py src/empiricist/ledger/db.py tests/test_ledger.py
git commit -m "feat: SQLite ledger core (WAL bootstrap, artifacts, evidence-gated status transitions)"
```

---

### Task 5: Runs + resume reconciliation (extend `ledger/db.py`)

**Files:**
- Modify: `src/empiricist/ledger/db.py` (append methods to `Ledger`)
- Test: `tests/test_runs.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for run provenance rows and resume reconciliation (spec §4.4)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Run


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


def test_start_and_finish_run(ledger):
    ledger.start_run(Run(run_id="r1", move="ENUMERATE", role=None, argv="minsearch --n 8"))
    ledger.finish_run(
        "r1", exit_code=0, wall_s=1.5, peak_rss_mb=42.0,
        tokens_in=0, tokens_out=0, cache_read=0, cost_usd=0.0,
    )
    row = ledger.get_run("r1")
    assert row.exit_code == 0 and row.ended is not None and row.wall_s == 1.5


def test_finish_unknown_run_raises(ledger):
    with pytest.raises(KeyError):
        ledger.finish_run("nope", exit_code=0, wall_s=0.0)


def test_reconcile_orphans_marks_unfinished_runs(ledger):
    ledger.start_run(Run(run_id="r1", move="SEARCH"))
    ledger.start_run(Run(run_id="r2", move="SEARCH"))
    ledger.finish_run("r1", exit_code=0, wall_s=1.0)
    n = ledger.reconcile_orphans()
    assert n == 1
    r2 = ledger.get_run("r2")
    assert r2.exit_code == -1 and r2.ended is not None
    # idempotent
    assert ledger.reconcile_orphans() == 0


def test_spent_sums_cost_and_tokens(ledger):
    ledger.start_run(Run(run_id="r1", move="SEARCH"))
    ledger.finish_run("r1", exit_code=0, wall_s=1.0,
                      tokens_in=1000, tokens_out=500, cost_usd=0.25)
    ledger.start_run(Run(run_id="r2", move="SEARCH"))
    ledger.finish_run("r2", exit_code=0, wall_s=1.0,
                      tokens_in=2000, tokens_out=1500, cost_usd=0.75)
    spent = ledger.spent()
    assert spent.cost_usd == pytest.approx(1.0)
    assert spent.tokens_in == 3000 and spent.tokens_out == 2000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_runs.py -v`
Expected: FAIL with `AttributeError: 'Ledger' object has no attribute 'start_run'`

- [ ] **Step 3: Append to `src/empiricist/ledger/db.py`**

Add near the top imports: `from dataclasses import dataclass` (extend the existing import from `empiricist.ledger.models` with `Run`). Then append inside `Ledger`:

```python
    # -- runs & resume (spec §4.4) -------------------------------------------

    def start_run(self, run: Run) -> None:
        with self._tx() as c:
            c.execute(
                "INSERT INTO runs (run_id, move, role, model, argv, seed, config_hash,"
                " env_fingerprint, tokens_in, tokens_out, cache_read, cost_usd,"
                " peak_rss_mb, exit_code, started, ended, wall_s)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run.run_id, run.move, run.role, run.model, run.argv, run.seed,
                 run.config_hash, run.env_fingerprint, run.tokens_in, run.tokens_out,
                 run.cache_read, run.cost_usd, run.peak_rss_mb, run.exit_code,
                 run.started, run.ended, run.wall_s),
            )

    def finish_run(
        self,
        run_id: str,
        *,
        exit_code: int,
        wall_s: float,
        peak_rss_mb: float | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cache_read: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        with self._tx() as c:
            cur = c.execute(
                "UPDATE runs SET exit_code = ?, wall_s = ?, peak_rss_mb = ?,"
                " tokens_in = ?, tokens_out = ?, cache_read = ?, cost_usd = ?,"
                " ended = ? WHERE run_id = ?",
                (exit_code, wall_s, peak_rss_mb, tokens_in, tokens_out,
                 cache_read, cost_usd, now_iso(), run_id),
            )
            if cur.rowcount == 0:
                raise KeyError(run_id)

    def get_run(self, run_id: str) -> Run:
        r = self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if r is None:
            raise KeyError(run_id)
        return Run(
            run_id=r["run_id"], move=r["move"], role=r["role"], model=r["model"],
            argv=r["argv"], seed=r["seed"], config_hash=r["config_hash"],
            env_fingerprint=r["env_fingerprint"], tokens_in=r["tokens_in"],
            tokens_out=r["tokens_out"], cache_read=r["cache_read"],
            cost_usd=r["cost_usd"], peak_rss_mb=r["peak_rss_mb"],
            exit_code=r["exit_code"], started=r["started"], ended=r["ended"],
            wall_s=r["wall_s"],
        )

    def reconcile_orphans(self) -> int:
        """Mark runs that started but never ended (kill -9 mid-flight) as incomplete.

        Resume rule (a) from spec §4.4: the in-flight sample is discarded;
        nothing else is lost.
        """
        with self._tx() as c:
            cur = c.execute(
                "UPDATE runs SET exit_code = -1, ended = ? WHERE ended IS NULL",
                (now_iso(),),
            )
            return cur.rowcount

    def spent(self) -> Spent:
        """Total budget consumed, summed from runs (spec §4.4(b): caps continue)."""
        r = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) AS cost,"
            " COALESCE(SUM(tokens_in), 0) AS tin,"
            " COALESCE(SUM(tokens_out), 0) AS tout FROM runs"
        ).fetchone()
        return Spent(cost_usd=r["cost"], tokens_in=r["tin"], tokens_out=r["tout"])


@dataclass(frozen=True)
class Spent:
    cost_usd: float
    tokens_in: int
    tokens_out: int
```

(`Spent` is defined at module level, after the `Ledger` class.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_runs.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/ledger/db.py tests/test_runs.py
git commit -m "feat: run provenance rows, orphan reconciliation, budget accounting"
```

---

### Task 6: Certification stamps (extend `ledger/db.py`)

**Files:**
- Modify: `src/empiricist/ledger/db.py` (append methods)
- Test: `tests/test_certifications.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the verifier certification-stamp store (spec §7, F3)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict


@pytest.fixture()
def ledger(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield lg
    lg.close()


STAMP = Certification(
    verifier="stab_fusion", verifier_version="1.0", binary_hash="abc123",
    golden_suite_hash="suite777", verdict=Verdict.PASS,
)


def test_uncertified_by_default(ledger):
    assert not ledger.is_certified("stab_fusion", "1.0", "abc123")


def test_certify_then_is_certified(ledger):
    ledger.add_certification(STAMP)
    assert ledger.is_certified("stab_fusion", "1.0", "abc123")


def test_fail_stamp_does_not_certify(ledger):
    ledger.add_certification(
        Certification(
            verifier="enum_fusion", verifier_version="1.0", binary_hash="xyz",
            golden_suite_hash="suite777", verdict=Verdict.FAIL,
        )
    )
    assert not ledger.is_certified("enum_fusion", "1.0", "xyz")


def test_certification_is_version_and_binary_specific(ledger):
    ledger.add_certification(STAMP)
    assert not ledger.is_certified("stab_fusion", "1.1", "abc123")
    assert not ledger.is_certified("stab_fusion", "1.0", "other")


def test_recertify_replaces_stamp(ledger):
    ledger.add_certification(STAMP)
    ledger.add_certification(
        Certification(
            verifier="stab_fusion", verifier_version="1.0", binary_hash="abc123",
            golden_suite_hash="suite999", verdict=Verdict.FAIL,
        )
    )
    assert not ledger.is_certified("stab_fusion", "1.0", "abc123")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_certifications.py -v`
Expected: FAIL with `AttributeError: ... no attribute 'add_certification'`

- [ ] **Step 3: Append to `Ledger` in `src/empiricist/ledger/db.py`**

(Extend the models import with `Certification`.)

```python
    # -- certification stamps (spec §7: the trust boundary) --------------------

    def add_certification(self, cert: Certification) -> None:
        with self._tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO certifications (verifier, verifier_version,"
                " binary_hash, golden_suite_hash, verdict, stamped_at, run_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cert.verifier, cert.verifier_version, cert.binary_hash,
                 cert.golden_suite_hash, cert.verdict.value, cert.stamped_at,
                 cert.run_id),
            )

    def is_certified(self, verifier: str, version: str, binary_hash: str) -> bool:
        """Registry rule: verify() may run only if a PASS stamp exists."""
        row = self.conn.execute(
            "SELECT verdict FROM certifications WHERE verifier = ?"
            " AND verifier_version = ? AND binary_hash = ?",
            (verifier, version, binary_hash),
        ).fetchone()
        return row is not None and row["verdict"] == Verdict.PASS.value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_certifications.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/ledger/db.py tests/test_certifications.py
git commit -m "feat: verifier certification stamps (golden-suite trust boundary)"
```

---

### Task 7: Human gates (`ledger/gates.py`)

**Files:**
- Create: `src/empiricist/ledger/gates.py`
- Test: `tests/test_gates.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the persisted human-gate queue (spec §4.2, §9; gates parked overnight)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.gates import GateError, Gates


@pytest.fixture()
def gates(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield Gates(lg)
    lg.close()


def test_open_gate_is_pending(gates):
    g = gates.open("PROOF_CAMPAIGN", artifact_id="art1", note="prove F(cycle)")
    assert g.state == "pending" and g.kind == "PROOF_CAMPAIGN"
    assert g.opened_at is not None and g.resolved_at is None


def test_list_pending(gates):
    gates.open("PROOF_CAMPAIGN", artifact_id="a")
    gates.open("RELEASE", artifact_id="b")
    pending = gates.list(state="pending")
    assert {g.kind for g in pending} == {"PROOF_CAMPAIGN", "RELEASE"}


def test_approve(gates):
    g = gates.open("PROOF_CAMPAIGN", artifact_id="a")
    resolved = gates.resolve(g.id, approve=True, note="go")
    assert resolved.state == "approved" and resolved.resolved_at is not None
    assert gates.list(state="pending") == []


def test_reject(gates):
    g = gates.open("RELEASE", artifact_id="a")
    assert gates.resolve(g.id, approve=False).state == "rejected"


def test_resolve_twice_raises(gates):
    g = gates.open("RELEASE", artifact_id="a")
    gates.resolve(g.id, approve=True)
    with pytest.raises(GateError):
        gates.resolve(g.id, approve=False)


def test_resolve_unknown_raises(gates):
    with pytest.raises(KeyError):
        gates.resolve("nope", approve=True)


def test_invalid_kind_raises(gates):
    with pytest.raises(GateError):
        gates.open("NOT_A_GATE", artifact_id="a")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_gates.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/ledger/gates.py`**

```python
"""Persisted human-gate queue.

The four outer-loop gates (spec §9 of the harness doc, §4.2/§11 of the
implementation spec): REDUCE reformulations, opening a proof campaign,
accepting a PROVED_DRAFT for formalization, and anything leaving the repo.
An unattended campaign parks work here; the scheduler skips parked branches.
"""

from __future__ import annotations

import uuid

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Gate, now_iso

GATE_KINDS = frozenset({"REDUCE", "PROOF_CAMPAIGN", "ACCEPT_DRAFT", "RELEASE"})


class GateError(Exception):
    pass


class Gates:
    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def open(self, kind: str, *, artifact_id: str, note: str | None = None) -> Gate:
        if kind not in GATE_KINDS:
            raise GateError(f"unknown gate kind: {kind!r} (expected one of {sorted(GATE_KINDS)})")
        gate = Gate(
            id=uuid.uuid4().hex, kind=kind, artifact_id=artifact_id,
            state="pending", opened_at=now_iso(), note=note,
        )
        with self._ledger._tx() as c:
            c.execute(
                "INSERT INTO gates (id, kind, artifact_id, state, opened_at, resolved_at, note)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (gate.id, gate.kind, gate.artifact_id, gate.state, gate.opened_at,
                 gate.resolved_at, gate.note),
            )
        return gate

    def list(self, *, state: str | None = None) -> list[Gate]:
        q, params = "SELECT * FROM gates", ()
        if state is not None:
            q, params = q + " WHERE state = ?", (state,)
        rows = self._ledger.conn.execute(q + " ORDER BY opened_at", params)
        return [self._from_row(r) for r in rows]

    def resolve(self, gate_id: str, *, approve: bool, note: str | None = None) -> Gate:
        with self._ledger._tx() as c:
            row = c.execute("SELECT * FROM gates WHERE id = ?", (gate_id,)).fetchone()
            if row is None:
                raise KeyError(gate_id)
            if row["state"] != "pending":
                raise GateError(f"gate {gate_id} already {row['state']}")
            c.execute(
                "UPDATE gates SET state = ?, resolved_at = ?,"
                " note = COALESCE(?, note) WHERE id = ?",
                ("approved" if approve else "rejected", now_iso(), note, gate_id),
            )
        return self._from_row(
            self._ledger.conn.execute("SELECT * FROM gates WHERE id = ?", (gate_id,)).fetchone()
        )

    @staticmethod
    def _from_row(r) -> Gate:
        return Gate(
            id=r["id"], kind=r["kind"], artifact_id=r["artifact_id"], state=r["state"],
            opened_at=r["opened_at"], resolved_at=r["resolved_at"], note=r["note"],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_gates.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/ledger/gates.py tests/test_gates.py
git commit -m "feat: persisted human-gate queue (REDUCE/PROOF_CAMPAIGN/ACCEPT_DRAFT/RELEASE)"
```

---

### Task 8: Pareto frontier (`ledger/frontier.py`)

**Files:**
- Create: `src/empiricist/ledger/frontier.py`
- Test: `tests/test_frontier.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the Pareto frontier with monotone version counter (spec §4.3, §9)."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.frontier import Frontier, recompute_frontier


@pytest.fixture()
def frontier(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    yield Frontier(lg)
    lg.close()


def test_empty_frontier_version_zero(frontier):
    assert frontier.version() == 0
    assert frontier.entries() == {}


def test_first_insert_improves(frontier):
    assert frontier.consider("g1", [10.0]) is True
    assert frontier.version() == 1
    assert frontier.entries() == {"g1": [10.0]}


def test_dominated_candidate_rejected_version_unchanged(frontier):
    frontier.consider("g1", [10.0])
    assert frontier.consider("g2", [12.0]) is False
    assert frontier.version() == 1
    assert "g2" not in frontier.entries()


def test_equal_vector_rejected(frontier):
    frontier.consider("g1", [10.0])
    assert frontier.consider("g2", [10.0]) is False


def test_dominating_candidate_evicts(frontier):
    frontier.consider("g1", [10.0, 5.0])
    assert frontier.consider("g2", [9.0, 4.0]) is True
    assert frontier.entries() == {"g2": [9.0, 4.0]}
    assert frontier.version() == 2


def test_incomparable_candidates_coexist(frontier):
    frontier.consider("g1", [10.0, 5.0])
    assert frontier.consider("g2", [5.0, 10.0]) is True
    assert set(frontier.entries()) == {"g1", "g2"}
    assert frontier.version() == 2


def test_same_key_better_vec_updates(frontier):
    frontier.consider("g1", [10.0])
    assert frontier.consider("g1", [8.0]) is True
    assert frontier.entries() == {"g1": [8.0]}


def test_recompute_matches_incremental(frontier):
    vecs = {"a": [3.0, 3.0], "b": [1.0, 5.0], "c": [5.0, 1.0], "d": [4.0, 4.0]}
    for k, v in vecs.items():
        frontier.consider(k, v)
    assert recompute_frontier(vecs) == frontier.entries()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_frontier.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/ledger/frontier.py`**

```python
"""Pareto frontier over objective vectors (minimizing), persisted in the ledger.

A frontier-improvement event — consider() returning True — is the
Goodhart-resistant search score (spec §4.3). It is distinct from an
epistemic status promotion. The monotone version counter is MAX(frontier_version).

recompute_frontier() is the pure function used by the resume consistency
check (spec §4.4(d)): the persisted table must equal the recomputation
from the population, else resume fails hard.
"""

from __future__ import annotations

import json

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import dominates


def recompute_frontier(vecs: dict[str, list[float]]) -> dict[str, list[float]]:
    """The non-dominated subset of vecs (pure; deterministic tie-handling).

    Duplicate vectors: the lexicographically-smallest key wins, matching the
    incremental rule that an equal vector never displaces an incumbent.
    """
    result: dict[str, list[float]] = {}
    for key in sorted(vecs):
        vec = vecs[key]
        if any(dominates(other, vec) or other == vec for other in result.values()):
            continue
        result = {k: v for k, v in result.items() if not dominates(vec, v)}
        result[key] = vec
    return result


class Frontier:
    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def version(self) -> int:
        row = self._ledger.conn.execute(
            "SELECT COALESCE(MAX(frontier_version), 0) AS v FROM pareto_frontier"
        ).fetchone()
        return row["v"]

    def entries(self) -> dict[str, list[float]]:
        return {
            r["lc_orbit_key"]: json.loads(r["objective_vec"])
            for r in self._ledger.conn.execute(
                "SELECT lc_orbit_key, objective_vec FROM pareto_frontier"
            )
        }

    def consider(self, key: str, vec: list[float]) -> bool:
        """Insert iff not dominated; evict newly-dominated rows; bump version.

        Returns True iff the frontier strictly improved (the event the
        stall detector and scheduler score on).
        """
        with self._ledger._tx() as c:
            rows = c.execute(
                "SELECT lc_orbit_key, objective_vec FROM pareto_frontier"
            ).fetchall()
            current = {r["lc_orbit_key"]: json.loads(r["objective_vec"]) for r in rows}
            incumbent = current.get(key)
            others = {k: v for k, v in current.items() if k != key}
            if any(dominates(v, vec) or v == vec for v in others.values()):
                return False
            if incumbent is not None and (dominates(incumbent, vec) or incumbent == vec):
                return False
            new_version = self.version() + 1
            for k, v in others.items():
                if dominates(vec, v):
                    c.execute("DELETE FROM pareto_frontier WHERE lc_orbit_key = ?", (k,))
            c.execute(
                "INSERT OR REPLACE INTO pareto_frontier"
                " (lc_orbit_key, objective_vec, frontier_version) VALUES (?, ?, ?)",
                (key, json.dumps(vec), new_version),
            )
            return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_frontier.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/ledger/frontier.py tests/test_frontier.py
git commit -m "feat: persisted Pareto frontier with monotone version counter"
```

---

### Task 9: Config + env fingerprint (`config.py`) and artifact ingestion helper

**Files:**
- Create: `src/empiricist/config.py`
- Create: `src/empiricist/ledger/ingest.py`
- Test: `tests/test_config.py`, `tests/test_ingest.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:

```python
"""Tests for RunConfig defaults and the environment fingerprint."""

import json

from empiricist.config import RunConfig, env_fingerprint


def test_defaults_match_spec_section_3():
    cfg = RunConfig()
    assert cfg.resource_model == "GHZ_3"
    assert cfg.json_retry_count == 2
    assert cfg.stall_window_generations == 8
    assert cfg.diversity_floor == 0.30
    assert cfg.diversity_window == 64
    assert cfg.verify_timeout_s == 30.0
    assert cfg.transient_cap == 4


def test_config_is_frozen_and_hashable():
    cfg = RunConfig()
    assert cfg.config_hash() == RunConfig().config_hash()
    assert cfg.config_hash() != RunConfig(json_retry_count=3).config_hash()
    assert len(cfg.config_hash()) == 64


def test_env_fingerprint_contains_python_and_platform():
    fp = json.loads(env_fingerprint())
    assert "python" in fp and "platform" in fp and "packages" in fp
    assert "blake3" in fp["packages"]
```

`tests/test_ingest.py`:

```python
"""Tests for CAS+ledger artifact ingestion."""

import pytest

from empiricist.ledger.db import Ledger
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import Status
from empiricist.store import Store


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    yield lg, st
    lg.close()


def test_ingest_puts_content_and_registers_artifact(env):
    lg, st = env
    art = ingest_artifact(
        lg, st, content=b'{"family": "path", "claim": "F = N-3"}',
        kind="statement", problem="P5", title="path closed form",
        status=Status.HEURISTIC,
    )
    assert st.get(art.content_path) == b'{"family": "path", "claim": "F = N-3"}'
    assert lg.get_artifact(art.id).title == "path closed form"
    assert art.id == art.content_path  # id IS the content digest


def test_ingest_same_content_twice_raises(env):
    lg, st = env
    kw = dict(content=b"same", kind="statement", problem="P5",
              title="t", status=Status.HEURISTIC)
    ingest_artifact(lg, st, **kw)
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        ingest_artifact(lg, st, **kw)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/empiricist/config.py`**

```python
"""Frozen run configuration + environment fingerprint.

Every certificate embeds config_hash() and env_fingerprint() so promotions
are replayable (spec §4.2). Numeric defaults are the spec §3 values; more
fields land with the milestones that consume them.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict, dataclass
from importlib import metadata

from blake3 import blake3

_FINGERPRINT_PACKAGES = ("blake3", "pytest")


@dataclass(frozen=True)
class RunConfig:
    resource_model: str = "GHZ_3"
    json_retry_count: int = 2
    stall_window_generations: int = 8
    diversity_floor: float = 0.30
    diversity_window: int = 64
    verify_timeout_s: float = 30.0
    transient_cap: int = 4          # minsearch transient component size = n0 + this

    def config_hash(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True)
        return blake3(canonical.encode()).hexdigest()


def env_fingerprint() -> str:
    """JSON fingerprint of the execution environment, for runs/certificates."""
    packages: dict[str, str] = {}
    for name in _FINGERPRINT_PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = "absent"
    return json.dumps(
        {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": packages,
        },
        sort_keys=True,
    )
```

- [ ] **Step 4: Write `src/empiricist/ledger/ingest.py`**

```python
"""Ingest an artifact: content into the CAS, metadata row into the ledger.

The artifact id IS the blake3 digest of the canonical content — identity
and provenance are the same fact (spec §4.2 rule 1).
"""

from __future__ import annotations

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Status
from empiricist.store import Store


def ingest_artifact(
    ledger: Ledger,
    store: Store,
    *,
    content: bytes,
    kind: str,
    problem: str,
    title: str,
    status: Status,
    substatus: str | None = None,
    status_n: int | None = None,
    coverage: str | None = None,
    run_id: str | None = None,
) -> Artifact:
    digest = store.put(content)
    art = Artifact(
        id=digest, kind=kind, problem=problem, title=title, content_path=digest,
        status=status, substatus=substatus, status_n=status_n, coverage=coverage,
        run_id=run_id,
    )
    ledger.add_artifact(art)
    return art
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py tests/test_ingest.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/empiricist/config.py src/empiricist/ledger/ingest.py tests/test_config.py tests/test_ingest.py
git commit -m "feat: frozen RunConfig + env fingerprint + CAS-backed artifact ingestion"
```

---

### Task 10: Full-suite green, lint clean, push, PR

**Files:** none new

- [ ] **Step 1: Run everything**

Run: `uv run pytest -v && uv run ruff check src tests`
Expected: all tests PASS (≈45), no lint errors. Fix any stragglers before proceeding.

- [ ] **Step 2: Kill-safety smoke test (manual)**

```bash
uv run python - <<'EOF'
# Simulate a crash mid-run and verify resume semantics end-to-end.
import tempfile, pathlib
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Run

d = pathlib.Path(tempfile.mkdtemp())
lg = Ledger(d / "ledger.db")
lg.start_run(Run(run_id="inflight", move="SEARCH"))
lg.close()                      # "kill -9": run never finished

lg2 = Ledger(d / "ledger.db")   # resume
assert lg2.reconcile_orphans() == 1
assert lg2.get_run("inflight").exit_code == -1
print("resume semantics OK")
EOF
```

Expected: `resume semantics OK`

- [ ] **Step 3: Push branch and open PR**

```bash
git push -u origin feat/m1-2-scaffold-ledger
```

Then open the PR (UI, or `gh pr create` if authenticated) targeting `main`, titled
"M1–2: scaffold, epistemic ledger, content-addressed store". PR body summarizes:
scaffold (uv/src-layout), CAS, ledger core (evidence-gated transitions, REFUTED
terminal), runs/resume, certifications, gates, Pareto frontier, config/ingest.

---

## Plan self-review (done at write time)

- **Spec coverage (M1–2):** scaffold/D9 ✅ (Task 1); CAS §3 ✅ (Task 2); models incl. Budget/Gate/Certification (App A/B) ✅ (Task 3); schema App A incl. `details_json`, `coverage`, `certifications`, `gates` ✅ (Task 4); evidence-gated transitions + REFUTED terminal §4.1–4.2 ✅ (Task 4); runs provenance + resume (a)(b) §4.4 ✅ (Task 5); certification stamps §7 ✅ (Task 6); human gates §4.2/§11 ✅ (Task 7); frontier + version + recompute check §4.3/§4.4(d) ✅ (Task 8); config defaults §3 + env fingerprint §4.2 ✅ (Task 9). Deferred to their own milestones by design: single-writer *queue* (orchestrator, M7 — the single-connection discipline is in place now), search-state reconstruction §4.4(c) (M6), population wiring of `recompute_frontier` (M6).
- **Placeholder scan:** no TBDs; all steps carry code/commands.
- **Type consistency:** `Status`/`Verdict`/`EvidenceRow.details`↔`details_json`, `Run` fields ↔ runs DDL, `Gate`/`Certification` ↔ DDL, `dominates` shared by frontier — checked.
