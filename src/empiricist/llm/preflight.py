"""Startup preflight: confirm model, auth, and structured output (spec §5.3).

One cheap real call requests a tiny strict schema. This catches an unavailable
model, broken auth, or structured-output integration failure before a campaign
wave becomes the integration test. It does not measure sustainable concurrency;
provider rate limits and the client's configured semaphore cap must be validated
separately.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, ValidationError

from empiricist.ledger.db import Ledger
from empiricist.llm.models import Effort
from empiricist.llm.roles import Role


class PreflightCanary(BaseModel):
    """Minimal closed schema shared by every supported model transport."""

    model_config = ConfigDict(extra="forbid", strict=True)

    ok: bool


_PREFLIGHT_ROLE = Role(
    name="preflight",
    system_prompt="You are a startup health check. Return only the required schema.",
    effort=Effort.LOW, k=1, active=False,
)


class PreflightError(Exception):
    pass


@dataclass(frozen=True)
class PreflightReport:
    model_ok: bool
    cost_usd: float
    session_id: str


async def preflight(client, *, ledger: Ledger | None = None) -> PreflightReport:
    """Run one strict-schema call; raise if any startup integration is unhealthy."""
    result = await client.complete(
        _PREFLIGHT_ROLE,
        'Return {"ok": true} using the required schema.',
        session_id="preflight",
        schema=PreflightCanary,
        run_id=f"preflight-{uuid.uuid4().hex}" if ledger is not None else None,
        ledger=ledger,
    )
    if result is None or not result.has_artifact:
        raise PreflightError(
            "preflight structured-output canary did not return a usable artifact "
            f"(result={'None' if result is None else result.stop_reason})"
        )
    try:
        canary = PreflightCanary.model_validate(result.parsed)
    except ValidationError as exc:
        raise PreflightError(
            "preflight structured-output canary failed local schema validation"
        ) from exc
    if canary.ok is not True:
        raise PreflightError("preflight structured-output canary returned ok=false")
    return PreflightReport(
        model_ok=True, cost_usd=result.cost_usd, session_id=result.session_id,
    )
