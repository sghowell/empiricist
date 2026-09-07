"""Repository-wide test guards."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_claims_repo_from_env(monkeypatch):
    """An `EMPIRICIST_CLAIMS_REPO` in the developer's shell must never make unrelated
    ingest tests write claim files into a real repository."""
    monkeypatch.delenv("EMPIRICIST_CLAIMS_REPO", raising=False)


@pytest.fixture(autouse=True)
def _no_live_builtin_identities(monkeypatch):
    """Unit tests stamp stub identities for `lean` and the certificate checkers; the
    live verifiers installed on the developer's machine must not make those stamps
    read as drift. The drift test patches `builtin_identity` itself."""
    monkeypatch.setattr("empiricist.claims.check.builtin_identity", lambda name: None)
