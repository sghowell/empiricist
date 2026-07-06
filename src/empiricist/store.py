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
