"""Rate-limit recognition for the model loops.

The documented signature of a throttled Claude Code call (the M9 and M20b
operational notes): the process exits non-zero almost instantly with zero output
tokens. Churning rounds against it wastes the round budget and pollutes the
history with NO_ARTIFACT entries. The loops instead back off and retry the SAME
round (a distinct run_id per attempt keeps every provider receipt), then abort
the task -- never an F3 alarm, and never a silent skip -- once the policy's
attempts are exhausted.
"""
from __future__ import annotations

from dataclasses import dataclass

from empiricist.ledger.models import Run

THROTTLE_MAX_WALL_S = 5.0


def is_throttled_run(run: Run) -> bool:
    """True iff `run` shows the rate-limit signature: non-zero exit, zero
    output tokens, and a wall time under `THROTTLE_MAX_WALL_S`. An unfinished
    run (`exit_code is None` / `wall_s is None`) is never throttled."""
    return (
        run.exit_code not in (0, None)
        and run.tokens_out == 0
        and run.wall_s is not None
        and run.wall_s < THROTTLE_MAX_WALL_S
    )


@dataclass(frozen=True)
class ThrottlePolicy:
    """Exponential backoff: `base_s * 2**(attempt-1)`, capped at `max_s`, for
    at most `max_attempts` attempts of one round."""

    base_s: float = 60.0
    max_s: float = 900.0
    max_attempts: int = 5

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_s < 0 or self.max_s < 0:
            raise ValueError("delays must be non-negative")

    def delay(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt is 1-based")
        return min(self.max_s, self.base_s * (2 ** (attempt - 1)))


# Module-level singleton default for the loops' `throttle=` parameter (ruff B008:
# no calls in argument defaults). Immutable, so sharing it is safe.
DEFAULT_THROTTLE = ThrottlePolicy()
