"""The three v0 machine moves as idempotent, budgeted functions over a
`CampaignState` (M7 T1, spec §9 plan): ENUMERATE (once, the heavy step),
SEARCH (one generation wave), CONJECTURE (mine + auto-ATTACK + submit).

**ensure_enumerate's idempotency contract.** A VERIFIED_N dataset artifact
for (P5, kind='dataset') already in the ledger IS the campaign's ENUMERATE
step having already run -- `ensure_enumerate` returns it without redoing any
work, so a resumed campaign (or a scheduler that calls it as a precondition
before every SEARCH/CONJECTURE move) never re-runs Tier-0/Tier-1. The only
path that re-derives the dataset is a genuinely empty ledger. If that
re-derivation lands on content that was already ingested under a prior,
crashed attempt (identical dataset bytes -> identical blake3 digest -> the
same artifact id, spec §4.2 rule 1), `ingest_dataset`'s `ledger.add_artifact`
raises `sqlite3.IntegrityError` on the PRIMARY KEY collision; that is not a
failure, it is the crash-and-rerun case working as designed -- caught here
and resolved by loading the already-ingested artifact by its content digest.

**open_targets' lc_orbit_key finding (verify-before-code, M6 carryover).**
`domain.p5.dataset.build_dataset` stamps every row's `orbit_id` in the
tablebase's own union-find/enumerate-root namespace (see `dataset.py`'s and
`search/conjecture.py`'s module docstrings) -- NOT the LC-orbit canonical key
`SearchLoop`/`verify_agreed` compare against (`stab_fusion`'s `lc_orbit_key`
of the *achieved* graph state, spec D5). A `TargetSpec.lc_orbit_key` built
from `row["orbit_id"]` would never match an exact-upgrade hit, silently
disabling the exit criterion. So `open_targets` recomputes the true key from
each row's `representative_edges` via `canonical.lc_orbit_key`, the same
function `StabFusionVerifier.verify` uses on the achieved graph -- when a
Searcher candidate's claimed target graph is exactly (or LC-equivalent to)
the row's representative, the two keys are computed identically and match.
"""

from __future__ import annotations

import json
import logging
import sqlite3

from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.dataset import build_dataset, ingest_dataset, to_canonical_json
from empiricist.domain.p5.graphstate import GraphState
from empiricist.domain.p5.localcomp import OrbitTooLarge
from empiricist.domain.p5.tablebase import tier0_search, tier1_search
from empiricist.ledger.models import Artifact, Status
from empiricist.llm.client import LLMClient
from empiricist.search.conjecture import attack, conjecture_artifact_id, mine, submit
from empiricist.search.database import Population
from empiricist.search.loop import GenerationReport, SearchLoop, TargetSpec
from empiricist.verifiers.enum_fusion import EnumFusionVerifier
from empiricist.verifiers.stab_fusion import StabFusionVerifier

logger = logging.getLogger(__name__)

_FUSION_VERIFIERS = (StabFusionVerifier, EnumFusionVerifier)


def ensure_certified(state: CampaignState) -> None:
    """Certify both fusion verifiers iff either lacks a current PASS stamp.

    Idempotent: `Registry.verify` (and therefore `verify_agreed`) would
    raise `UncertifiedVerifierError` for an unstamped verifier, so this is
    the move that must run before any verification touches real work -- but
    re-certifying an already-stamped verifier is harmless (certify() always
    re-runs the golden suite and upserts the same PASS stamp), just wasted
    effort, so we check first via `ledger.is_certified` rather than
    certifying unconditionally on every call.
    """
    for verifier_cls in _FUSION_VERIFIERS:
        verifier = verifier_cls()
        if not state.ledger.is_certified(verifier.name, verifier.version, verifier.binary_hash):
            state.registry.certify(verifier)


def ensure_enumerate(state: CampaignState, cfg: RunConfig) -> Artifact:
    """Return the campaign's VERIFIED_N P5 dataset artifact, running
    ENUMERATE (Tier-0 + Tier-1 + build + ingest) only if one doesn't already
    exist in the ledger. See module docstring for the idempotency and
    crash-recovery contracts.
    """
    existing = state.ledger.find_artifacts(
        kind="dataset", problem="P5", status=Status.VERIFIED_N
    )
    if existing:
        return existing[-1]  # find_artifacts orders oldest->newest

    ensure_certified(state)

    tier0 = tier0_search(cfg.tier0_n)
    tier1 = tier1_search(cfg.tier1_n)
    dataset = build_dataset(tier0, tier1)

    try:
        return ingest_dataset(state.ledger, state.store, dataset, state.registry)
    except sqlite3.IntegrityError:
        # Documented recovery path: identical dataset content was already
        # ingested (a prior attempt got as far as the CAS/ledger write and
        # then crashed before whatever else the caller intended, or a race
        # with another process) -- the artifact id IS the content digest, so
        # re-deriving the SAME dataset and re-computing that digest recovers
        # the exact row `find_artifacts` would have found if this call had
        # started a moment later.
        content = to_canonical_json(dataset)
        digest = state.store.put(content)
        return state.ledger.get_artifact(digest)


def dataset_rows(state: CampaignState, artifact: Artifact) -> list[dict]:
    """The dataset artifact's `rows` list, read back from the CAS (the
    canonical JSON shape `domain.p5.dataset.build_dataset`/`to_canonical_json`
    produce: `{"schema_version", "n_max", "tier1_n_max", "per_n_totals",
    "rows"}`)."""
    content = state.store.get(artifact.content_path)
    return json.loads(content)["rows"]


def open_targets(
    rows: list[dict], n: int, cap: int, population: Population | None = None
) -> list[TargetSpec]:
    """Up to `cap` `TargetSpec`s for the open (unresolved, `exact=False`)
    orbits at size `n`, sorted by `(n, orbit_id)` for determinism.

    `target_f = n` (an F=N witness is the exact upgrade this establishes,
    spec's mod-3 ladder); `known_bound` is rendered from the row's own
    `lower_bound`. `lc_orbit_key` is recomputed from `representative_edges`
    (see module docstring) -- an LC-orbit BFS per candidate row, which can in
    principle raise `OrbitTooLarge` for a pathological n; such a row is
    skipped (logged, not raised) rather than aborting the whole wave, since
    every OTHER open orbit at this n is still a legitimate target. Empirically
    verified at n=8 (the campaign's default `search_target_n`): all 59 open
    rows compute a key without hitting the default cap.

    **Solved-orbit filtering (overnight-safety review I3).** When
    `population` is given, an orbit whose `lc_orbit_key` already holds a
    population elite with `objective_vec[0] <= target_f` is DROPPED: a
    certified witness at (or below) the target fusion count already exists,
    so re-targeting it every generation is pure wasted spend. This is also
    what makes the orchestrator's targets-exhausted path genuinely
    reachable -- once every open orbit at `n` is solved, the filtered list
    is empty and the scheduler drops SEARCH from rotation. A witness ABOVE
    `target_f` (e.g. an F=n+3 construction for an orbit whose F=n question
    is still open, mod-3 ladder) does NOT drop the target: the bound the
    campaign is after has not been reached. Solved orbits do not consume
    `cap` slots.
    """
    open_rows = sorted(
        (r for r in rows if r["n"] == n and not r["exact"]),
        key=lambda r: (r["n"], r["orbit_id"]),
    )

    targets: list[TargetSpec] = []
    for row in open_rows:
        if len(targets) >= cap:
            break
        g = GraphState(n=row["n"], edges=[tuple(e) for e in row["representative_edges"]])
        try:
            key = lc_orbit_key(g)
        except OrbitTooLarge:
            logger.warning(
                "open_targets: orbit %s at n=%d exceeded the LC-orbit cap -- "
                "skipping this target (it stays open for a future generation)",
                row["orbit_id"], n,
            )
            continue
        if population is not None:
            elite = population.get(key)
            if (
                elite is not None
                and elite.objective_vec
                and elite.objective_vec[0] <= row["n"]  # target_f = n for open rows
            ):
                logger.info(
                    "open_targets: orbit %s at n=%d already solved "
                    "(population elite F=%s <= target %d) -- dropped",
                    row["orbit_id"], n, elite.objective_vec[0], row["n"],
                )
                continue
        targets.append(
            TargetSpec(
                n=row["n"],
                lc_orbit_key=key,
                representative_edges=tuple(tuple(e) for e in row["representative_edges"]),
                known_bound=f"F >= {row['lower_bound']}",
                target_f=row["n"],
            )
        )
    return targets


async def search_move(
    state: CampaignState, cfg: RunConfig, client: LLMClient, gen: int
) -> GenerationReport:
    """One SEARCH generation: targets = the open orbits at `cfg.search_
    target_n` still unsolved in the population (see `open_targets`'s
    solved-orbit filtering), capped at `cfg.targets_per_gen`; run
    `SearchLoop.run_generation` against them. Ensures ENUMERATE has run
    (idempotent) so this is safe to call as the campaign's very first move."""
    artifact = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, artifact)
    targets = open_targets(
        rows, cfg.search_target_n, cfg.targets_per_gen, population=state.population
    )
    if not targets:
        raise ValueError(
            f"search_move: no open targets at n={cfg.search_target_n} -- "
            "every orbit at that n is already resolved (dataset-exact or "
            "population-solved), or every open orbit there exceeded the "
            "LC-orbit cap (see open_targets)"
        )
    loop = SearchLoop(client, state.ledger, state.store, state.registry, state.population)
    return await loop.run_generation(gen, targets)


async def conjecture_move(
    state: CampaignState, cfg: RunConfig, client: LLMClient
) -> list[Artifact]:
    """One CONJECTURE wave: mine conjectures from the dataset, auto-ATTACK
    each, and submit every one (survivors land CONJECTURED, falsified ones
    land REFUTED -- both are progress events; the scheduler decides what
    counts toward the exit criterion). Ensures ENUMERATE has run (idempotent)
    so this is safe to call as the campaign's very first move too.

    **Duplicate conjectures are skipped, not resubmitted (overnight-safety
    review C1).** A re-mined byte-identical conjecture (the common case
    after `resume`: the model rediscovers yesterday's closed form) already
    has its artifact + evidence in the ledger; it is detected up front via
    `conjecture_artifact_id` (before spending an attack on it), logged, and
    EXCLUDED from the returned list -- so the orchestrator's per-wave
    progress count sees only genuinely NEW artifacts and a wave of pure
    re-discoveries correctly reads as no progress. (`submit` itself is also
    duplicate-safe -- see its docstring -- this check just avoids the
    wasted attack and keeps the return-list semantics honest.)"""
    artifact = ensure_enumerate(state, cfg)
    rows = dataset_rows(state, artifact)
    conjectures = await mine(client, rows)
    artifacts: list[Artifact] = []
    for conj in conjectures:
        art_id = conjecture_artifact_id(conj)
        try:
            existing = state.ledger.get_artifact(art_id)
        except KeyError:
            existing = None
        if existing is not None:
            logger.info(
                "conjecture_move: duplicate conjecture (artifact %s already %s) -- skipped",
                art_id[:12], existing.status.value,
            )
            continue
        report = attack(conj, rows)
        artifacts.append(submit(state.ledger, state.store, conj, report))
    return artifacts
