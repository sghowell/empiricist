"""Repository-wide test guards."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_claims_repo_from_env(monkeypatch):
    """An `EMPIRICIST_CLAIMS_REPO` in the developer's shell must never make unrelated
    ingest tests write claim files into a real repository."""
    monkeypatch.delenv("EMPIRICIST_CLAIMS_REPO", raising=False)
