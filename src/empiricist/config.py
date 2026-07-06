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
