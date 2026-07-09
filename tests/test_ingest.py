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


def test_ingest_artifact_id_override_decouples_id_from_content_digest(env):
    """The documented exception (spec §4.2 rule 1): a caller-supplied
    `artifact_id` overrides `id`, but `content_path` is ALWAYS the true
    content digest -- content stays genuinely retrievable at content_path
    even when `id` is something else entirely (used by
    `search.conjecture.submit` for semantic conjecture dedup)."""
    lg, st = env
    content = b'{"family": "path", "claim": "F = N-3"}'
    art = ingest_artifact(
        lg, st, content=content, kind="statement", problem="P5",
        title="path closed form", status=Status.HEURISTIC,
        artifact_id="semantic-id-not-a-content-hash",
    )
    assert art.id == "semantic-id-not-a-content-hash"
    assert art.content_path != art.id
    assert st.get(art.content_path) == content
    assert lg.get_artifact(art.id).content_path == art.content_path
