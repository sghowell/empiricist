"""Blake3 content-addressed file store.

Layout: <root>/blake3/<hex[0:2]>/<hex[2:4]>/<hex64>. Writes are atomic
(temp file + os.replace) and idempotent: identical content maps to the
same path, so re-ingestion is free and the store is crash-safe against
process death (kill -9); power-loss durability (fsync) is out of scope
for v0.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from blake3 import blake3

_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")


class Store:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def path_for(self, digest: str) -> Path:
        if not _DIGEST_RE.fullmatch(digest):
            raise ValueError(f"not a blake3 hex digest: {digest!r}")
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

    def verify(self, digest: str) -> bool:
        """Re-hash stored content; False on mismatch (bit rot / tampering)."""
        return blake3(self.get(digest)).hexdigest() == digest
