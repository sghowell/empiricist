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


def test_path_for_rejects_non_digest_strings(store):
    for bad in ("/etc/passwd", "../../../etc/passwd", "", "aa", "Z" * 64, "0" * 63):
        with pytest.raises(ValueError):
            store.path_for(bad)


def test_get_and_exists_reject_traversal(store):
    with pytest.raises(ValueError):
        store.get("../../../etc/passwd")
    with pytest.raises(ValueError):
        store.exists("/etc/passwd")


def test_empty_content_roundtrips(store):
    digest = store.put(b"")
    assert store.get(digest) == b""


def test_verify_detects_tampering(store):
    digest = store.put(b"honest content")
    assert store.verify(digest)
    store.path_for(digest).write_bytes(b"tampered")
    assert not store.verify(digest)
