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
