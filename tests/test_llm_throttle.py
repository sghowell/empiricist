"""Rate-limit signature + backoff policy shared by the model loops."""
from __future__ import annotations

import pytest

from empiricist.ledger.models import Run
from empiricist.llm.throttle import THROTTLE_MAX_WALL_S, ThrottlePolicy, is_throttled_run


def _run(**kw) -> Run:
    base = dict(run_id="r", move="SAMPLE", exit_code=1, tokens_out=0, wall_s=0.4)
    base.update(kw)
    return Run(**base)


def test_throttle_signature():
    assert is_throttled_run(_run())
    assert not is_throttled_run(_run(exit_code=0))
    assert not is_throttled_run(_run(tokens_out=12))
    assert not is_throttled_run(_run(wall_s=30.0))
    assert not is_throttled_run(_run(wall_s=THROTTLE_MAX_WALL_S))
    assert not is_throttled_run(_run(exit_code=None))
    assert not is_throttled_run(_run(wall_s=None))


def test_policy_backoff_doubles_and_caps():
    p = ThrottlePolicy(base_s=60.0, max_s=900.0, max_attempts=5)
    assert [p.delay(a) for a in (1, 2, 3, 4, 5)] == [60.0, 120.0, 240.0, 480.0, 900.0]
    with pytest.raises(ValueError):
        p.delay(0)


def test_policy_rejects_nonsense():
    with pytest.raises(ValueError):
        ThrottlePolicy(max_attempts=0)
    with pytest.raises(ValueError):
        ThrottlePolicy(base_s=-1.0)
