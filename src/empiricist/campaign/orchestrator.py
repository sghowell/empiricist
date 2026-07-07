"""run_campaign (M7 T2, spec §9): the single resumable asyncio loop tying
ENUMERATE (once, idempotent) to SEARCH/CONJECTURE waves under
`Scheduler`/budget control, with PROVE parked at a human gate.

Resume is not a special mode: `CampaignState.load` already reconciles
orphaned runs and `ensure_enumerate` is idempotent, so calling `run_campaign`
again on the same `run_dir` picks the dataset back up unchanged. Generation
numbering resumes too -- `gen` starts at `1 + max(gen for prior "generation"
search_events, default 0)`, so a second `run_campaign` call never re-uses or
collides with a generation number a prior session already logged (CONJECTURE
waves do not consume a generation number; only SEARCH waves do, matching
`search.loop.SearchLoop.run_generation`'s own event log).

Every write happens through `state`'s single `Ledger`/`Population` instance
(the M1-2 single-writer discipline) -- this loop is itself single-threaded
asyncio, so there is no concurrent-writer hazard to guard against here.

**F3Alarm.** `search_move` raises `search.loop.F3Alarm` when the two
certified verifiers disagree -- a machinery fault, not evidence. The loop
that raises it has already written a durable `f3_alarm` search_events row
(spec: the alarm must survive the process it halts) before raising, so this
function's only job on catching it is to stop the world: record it on the
summary and break, no further moves are attempted this session.

**KeyboardInterrupt / any other exception.** The `finally` block always logs
a `campaign_end` search_event (gen=-1, the same out-of-band marker
`CampaignState.load` uses for session boundaries) carrying the summary
dataclass as of whatever point execution reached, then closes the ledger
connection -- so an operator-killed or crashed campaign always leaves an
auditable trail of where it stopped, and the run directory is always safe to
resume.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from empiricist.campaign.moves import (
    conjecture_move,
    dataset_rows,
    ensure_enumerate,
    open_targets,
    search_move,
)
from empiricist.campaign.scheduler import Scheduler
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.ledger.models import Status
from empiricist.llm.client import LLMClient
from empiricist.search.loop import F3Alarm
from empiricist.search.stall import StallDetector

logger = logging.getLogger(__name__)


@dataclass
class CampaignSummary:
    generations: int = 0
    conjecture_waves: int = 0
    conjectured: int = 0
    refuted: int = 0
    exact_upgrades: int = 0
    move_errors: int = 0
    spent_cost_usd: float = 0.0
    stop_reason: str | None = None
    f3_alarm: bool = False


async def run_campaign(run_dir: Path, cfg: RunConfig, client: LLMClient) -> CampaignSummary:
    state = CampaignState.load(run_dir)
    summary = CampaignSummary()
    try:
        dataset_art = ensure_enumerate(state, cfg)  # heavy step, idempotent across resume
        rows = dataset_rows(state, dataset_art)

        stall = StallDetector(
            window=cfg.stall_window_generations, diversity_floor=cfg.diversity_floor
        )
        scheduler = Scheduler(cfg, stall)

        prior_gens = [e.gen for e in state.population.events(trigger="generation")]
        gen = 1 + max(prior_gens, default=0)

        # Move-error isolation (overnight-safety review I2): a transport
        # blip (claude subprocess dies, network hiccup, a malformed envelope
        # crashing a parser edge) must NOT kill an unattended campaign -- it
        # is logged durably (`move_error` search_event), counted as
        # no-progress for the scheduler, and the loop continues. But a
        # PERSISTENTLY broken transport must not spin forever either: the
        # circuit breaker stops the campaign after
        # `cfg.max_consecutive_move_errors` consecutive failed moves
        # (stop_reason='move_errors'). Any successfully completed move
        # resets the streak. Only `Exception` is isolated: F3Alarm keeps
        # its dedicated stop-the-world handling below, and
        # KeyboardInterrupt/SystemExit (BaseException) propagate.
        consecutive_errors = 0

        def note_move_error(move: str, exc: Exception) -> bool:
            """Log + count an isolated move failure; True = breaker tripped."""
            nonlocal consecutive_errors
            consecutive_errors += 1
            summary.move_errors += 1
            logger.warning("campaign: %s move failed (isolated): %r", move, exc)
            state.population.log_event(gen, "move_error", {"move": move, "error": repr(exc)})
            scheduler.record(move, False)
            return consecutive_errors >= cfg.max_consecutive_move_errors

        while True:
            spent = state.ledger.spent()
            summary.spent_cost_usd = spent.cost_usd
            stop = scheduler.should_stop(spent, gen)
            if stop is not None:
                summary.stop_reason = stop
                break

            move = scheduler.next_move()

            if move == "search":
                targets = open_targets(
                    rows, cfg.search_target_n, cfg.targets_per_gen,
                    population=state.population,
                )
                if not targets:
                    scheduler.note_targets_exhausted()
                    continue

                try:
                    report = await search_move(state, cfg, client, gen)
                except F3Alarm:
                    summary.f3_alarm = True
                    summary.stop_reason = "f3_alarm"
                    summary.spent_cost_usd = state.ledger.spent().cost_usd
                    break
                except Exception as exc:
                    if note_move_error("search", exc):
                        summary.stop_reason = "move_errors"
                        break
                    continue

                consecutive_errors = 0
                stall.feed(report)
                scheduler.note_stall("search", stall.assess())
                scheduler.record("search", report.inserted > 0)
                summary.generations += 1
                summary.exact_upgrades += len(report.exact_upgrades)
                gen += 1

            else:  # "conjecture"
                try:
                    arts = await conjecture_move(state, cfg, client)
                except Exception as exc:
                    if note_move_error("conjecture", exc):
                        summary.stop_reason = "move_errors"
                        break
                    continue

                consecutive_errors = 0
                new_conjectured = 0
                new_refuted = 0
                for art in arts:
                    status = state.ledger.get_artifact(art.id).status
                    if status is Status.CONJECTURED:
                        new_conjectured += 1
                    elif status is Status.REFUTED:
                        new_refuted += 1
                summary.conjecture_waves += 1
                summary.conjectured += new_conjectured
                summary.refuted += new_refuted
                scheduler.record("conjecture", new_conjectured > 0)

            scheduler.maybe_open_proof_gate(state.gates, state.ledger)

        summary.spent_cost_usd = state.ledger.spent().cost_usd
    finally:
        # The end-marker write must never mask the exception that got us
        # here (review M3): a failing log_event (e.g. the ledger connection
        # itself is what broke) is reported to stderr, not raised over the
        # original error. state.close() is still guaranteed to run.
        try:
            state.population.log_event(-1, "campaign_end", asdict(summary))
        except Exception as log_exc:
            print(
                f"empiricist: failed to log campaign_end event: {log_exc!r}",
                file=sys.stderr,
            )
        finally:
            state.close()

    return summary
