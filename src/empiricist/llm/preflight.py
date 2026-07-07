"""Startup preflight: confirm the model resolves and auth is live (spec §5.3).

One cheap real call ("reply ok"). On the Claude Code subscription path this
catches an unavailable model or a broken login before a campaign starts. (ZDR
is an API-org concern, not the subscription path — relevant only to
AnthropicAPIClient.) Rate-limit / sustained-k probing is a separate, optional
concern deferred to the scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass

from empiricist.llm.models import Effort
from empiricist.llm.roles import Role

_PREFLIGHT_ROLE = Role(
    name="preflight",
    system_prompt="You are a health check. Reply with exactly: ok",
    effort=Effort.LOW, k=1, active=False,
)


class PreflightError(Exception):
    pass


@dataclass(frozen=True)
class PreflightReport:
    model_ok: bool
    cost_usd: float
    session_id: str


async def preflight(client) -> PreflightReport:
    """Run one trivial call; raise PreflightError if the model/auth is unhealthy."""
    result = await client.complete(
        _PREFLIGHT_ROLE, "Reply with exactly: ok", session_id="preflight",
    )
    if result is None or not result.ok:
        raise PreflightError(
            "preflight call did not return a usable response "
            f"(result={'None' if result is None else result.stop_reason})"
        )
    return PreflightReport(
        model_ok=True, cost_usd=result.cost_usd, session_id=result.session_id,
    )
