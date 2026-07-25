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

_FINGERPRINT_PACKAGES = ("empiricist", "blake3", "pytest")


@dataclass(frozen=True)
class RunConfig:
    resource_model: str = "GHZ_3"
    json_retry_count: int = 2
    stall_window_generations: int = 8
    diversity_floor: float = 0.30
    diversity_window: int = 64
    verify_timeout_s: float = 30.0
    transient_cap: int = 4          # minsearch transient component size = n0 + this

    # -- M7 campaign knobs (additive; config_hash covers them automatically) --
    tier0_n: int = 9                 # ENUMERATE: Tier-0 all-merge BFS ceiling
    tier1_n: int = 7                 # ENUMERATE: Tier-1 one-intra-fusion ceiling
    search_target_n: int = 8         # SEARCH: which n's open orbits to target
    targets_per_gen: int = 8         # SEARCH: max targets per generation wave
    conjecture_every: int = 3        # scheduler: CONJECTURE cadence (every N gens)
    max_generations: int | None = None   # inclusive cumulative SEARCH-gen limit
    max_cost_usd: float | None = None    # between-call/wave recorded-cost threshold
    scheduler_patience: int = 3      # scheduler: consecutive no-progress records at a
                                      # move's floor weight (1) before it counts as
                                      # exhausted for the 'stalled_out' stop condition
    max_consecutive_move_errors: int = 3  # orchestrator circuit breaker: consecutive
                                      # isolated move exceptions (transport faults etc.)
                                      # before the campaign stops with 'move_errors'

    def config_hash(self) -> str:
        """Stable blake3 hash of this config's fields and values.

        NOTE: the hash covers the whole config schema+values — adding a field
        changes it. It identifies a config at a code version; do not read
        cross-version hash equality as "same tuning".
        """
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
