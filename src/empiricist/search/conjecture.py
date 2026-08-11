"""Conjecture mining + deterministic auto-ATTACK (M6 T4, spec §9): mine
closed-form claims about named graph families from the `VERIFIED_N` dataset,
then falsify them against the dataset's OWN exact rows, proven lower bounds,
and the two hard invariants (`F === N-3 (mod 3)`, `F >= N-3`) -- never
against model output.

**Orbit-id finding (verify-before-code, per the plan):** `domain.p5.dataset.
build_dataset` stamps every row's `orbit_id` as `enumerate_connected_orbits(n)
.orbit_root(cert).hex()` -- a union-find ROOT certificate in that per-n
enumeration's own namespace (see `dataset.py`'s module docstring and
`tablebase.py`'s A4 note: the tablebase machinery deliberately never calls
`lc_orbit_key`, since walking a full LC orbit is exactly the BFS cost that
identity is designed to avoid in the hot loop). `lc_orbit_key` (canonical.py)
is a DIFFERENT identity for the same equivalence classes: the lexicographic
MINIMUM iso-certificate over the whole LC orbit. These two ids are NOT
interchangeable strings -- empirically confirmed by probing a real small
dataset (`tier0_search(6)` + `tier1_search(6)` -> `build_dataset`): for
every family/n pair, `enumerate_connected_orbits(n).orbit_root(cert(family_
graph)).hex()` matches the row's `orbit_id` exactly, while `lc_orbit_key
(family_graph) == row["orbit_id"]` fails for every row except one (cycle at
n=5, a coincidence -- the union-find root the BFS happened to pick for that
orbit was also its lexicographic minimum, not a general fact). So
`family_table` below matches a
programmatically-generated family graph to its dataset row the way the plan
anticipates: rebuild each row's own `GraphState` from `representative_edges`,
compute ITS `lc_orbit_key`, and compare that to the family graph's
`lc_orbit_key` -- both computed via the SAME independent identity scheme,
never touching `orbit_id` at all. This costs one LC-orbit BFS per row (cached
per `n` across families in one `family_table` call) rather than a second
`enumerate_connected_orbits` pass (which would additionally require `geng`/
`nauty-geng` on PATH or fall back to itertools -- avoided entirely here).

Trust discipline (unchanged from the plan): `attack` reads ONLY the dataset's
own exact rows, proven lower bounds, and the mod-3/floor invariants as ground
truth -- it never trusts `ConjectureOut.predicted_values` or any other model
output (malformed keys, an empty prediction set, and unknown families are
refuted defensively rather than allowed to raise -- see `attack`'s gate 0).
Promotion additionally requires GROUNDING: at least one prediction must have
matched an exact table row (see `attack`'s docstring -- an unfalsifiable/
unanchored claim is not 'consistent with a VERIFIED_N dataset' and never
earns CONJECTURED). `submit` writes to the ledger only via `ingest_artifact`
+ `record_evidence` (the single-writer discipline), landing a survivor at
`CONJECTURED` and a falsified claim at `REFUTED` with the exact
counterexample recorded as evidence.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import uuid
from dataclasses import dataclass

from blake3 import blake3
from pydantic import ValidationError

from empiricist.domain.p5 import P5_PROBLEM_VERSION
from empiricist.domain.p5.canonical import lc_orbit_key
from empiricist.domain.p5.graphstate import GraphState
from empiricist.ledger.db import Ledger
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import Artifact, EvidenceRow, Status, Verdict
from empiricist.llm.client import LLMClient
from empiricist.llm.roles import ROLES
from empiricist.llm.schemas import ConjectureOut
from empiricist.store import Store
from empiricist.verifiers.base import module_source_hash

_ATTACK_VERIFIER = "auto_attack"
_ATTACK_VERSION = "1.0"
# Ties the evidence row's binary_hash to the actual falsification code (this
# module) -- same discipline dataset.py/loop.py use for their own evidence.
_ATTACK_BINARY_HASH = module_source_hash(sys.modules[__name__])

# The programmatic generators family_table/mine/attack know about. "star" is
# K_{1,n-1}; "complete" is K_n. Order here is the order dataset_summary
# prints them in.
FAMILIES: tuple[str, ...] = ("path", "cycle", "star", "complete")

_FAMILY_MIN_N: dict[str, int] = {"path": 1, "cycle": 3, "star": 1, "complete": 1}


def family_graph(family: str, n: int) -> GraphState | None:
    """The canonical representative of `family` at size `n`, or None if
    `family` is unknown or `n` is invalid for it (cycle needs n>=3; the
    others accept n>=1 -- a single isolated vertex, degenerate but valid).
    """
    min_n = _FAMILY_MIN_N.get(family)
    if min_n is None or not isinstance(n, int) or n < min_n:
        return None
    if family == "path":
        edges = [(i, i + 1) for i in range(n - 1)]
    elif family == "cycle":
        edges = [(i, (i + 1) % n) for i in range(n)]
    elif family == "star":
        edges = [(0, i) for i in range(1, n)]
    else:  # "complete" (the only remaining key in _FAMILY_MIN_N)
        edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    return GraphState(n=n, edges=edges)


def _rows_by_n(dataset_rows: list[dict]) -> dict[int, list[dict]]:
    by_n: dict[int, list[dict]] = {}
    for row in dataset_rows:
        by_n.setdefault(row["n"], []).append(row)
    return by_n


def _row_lc_keys(rows_for_n: list[dict]) -> list[tuple[str, dict]]:
    """(lc_orbit_key, row) for every row at one n -- the expensive half of
    the match (one LC-orbit BFS per row), computed once per n and reused
    across every family `family_table` is asked about."""
    out = []
    for row in rows_for_n:
        g = GraphState(n=row["n"], edges=[tuple(e) for e in row["representative_edges"]])
        out.append((lc_orbit_key(g), row))
    return out


def _lookup_row(
    dataset_rows: list[dict],
    family: str,
    n: int,
    *,
    cache: dict[int, list[tuple[str, dict]]] | None = None,
) -> dict | None:
    """The dataset row (if any) whose orbit matches `family_graph(family, n)`,
    matched by comparing `lc_orbit_key`s (see module docstring) -- never by
    `orbit_id`. `cache` (n -> [(key, row), ...]) lets repeated lookups across
    families for the same n reuse the per-row `lc_orbit_key` computation.

    Bails out BEFORE computing any `lc_orbit_key` (an LC-orbit BFS -- cheap
    for the small n this dataset covers, but genuinely unbounded for an n
    the dataset has no rows for at all, e.g. a conjecture predicting past
    the dataset's range) when there is nothing at `n` to compare against.
    """
    rows_at_n = [r for r in dataset_rows if r["n"] == n]
    if not rows_at_n:
        return None
    g = family_graph(family, n)
    if g is None:
        return None
    key = lc_orbit_key(g)
    if cache is not None:
        if n not in cache:
            cache[n] = _row_lc_keys(rows_at_n)
        candidates = cache[n]
    else:
        candidates = _row_lc_keys(rows_at_n)
    for row_key, row in candidates:
        if row_key == key:
            return row
    return None


def family_table(
    dataset_rows: list[dict], families: list[str] | tuple[str, ...] = FAMILIES
) -> dict[str, dict[int, int | tuple[int, None]]]:
    """Per-family, per-n table of what the dataset knows: `F` (an int) for
    an exact row, or `(lower_bound, None)` for an open row. Only `n`s present
    in `dataset_rows` AND valid for that family are included -- an n with no
    matching orbit (shouldn't happen for a dataset whose rows partition every
    connected orbit at each n, per `build_dataset`'s own assertion) is
    silently skipped rather than raising, since `family_table` is a reporting
    view, not a validator.
    """
    by_n = _rows_by_n(dataset_rows)
    ns = sorted(by_n)
    row_key_cache: dict[int, list[tuple[str, dict]]] = {}

    table: dict[str, dict[int, int | tuple[int, None]]] = {}
    for family in families:
        per_n: dict[int, int | tuple[int, None]] = {}
        for n in ns:
            row = _lookup_row(dataset_rows, family, n, cache=row_key_cache)
            if row is None:
                continue
            per_n[n] = row["F"] if row["exact"] else (row["lower_bound"], None)
        table[family] = per_n
    return table


def dataset_summary(
    dataset_rows: list[dict], families: list[str] | tuple[str, ...] = FAMILIES
) -> str:
    """Compact text table of `family_table(dataset_rows, families)` plus the
    two hard invariants, for the Conjecturer's prompt."""
    table = family_table(dataset_rows, families)
    lines = ["VERIFIED_N dataset summary (F = minimum verified fusion count for the orbit):"]
    for family in families:
        per_n = table.get(family, {})
        if not per_n:
            continue
        cells = []
        for n in sorted(per_n):
            v = per_n[n]
            cells.append(f"n={n}: F>={v[0]} (open)" if isinstance(v, tuple) else f"n={n}: F={v}")
        lines.append(f"{family}: " + ", ".join(cells))
    lines.append(
        "Invariants that hold for EVERY orbit (checked by auto-ATTACK, not "
        "optional): F(N) === N-3 (mod 3); F(N) >= N-3."
    )
    return "\n".join(lines)


_TITLE_FAMILY_RE = re.compile(r"^Conjecture: (\S+) F\(N\) = ")


def _conjectured_families(ledger: Ledger) -> set[str]:
    """Families with at least one CONJECTURED statement artifact already in
    `ledger` -- read off the artifact TITLE (`submit`'s `f"Conjecture:
    {family} F(N) = {closed_form}"` convention), not the CAS content: `mine`
    has no `Store` handle, and the title's leading family token is exactly
    as reliable (it's derived from the same `conj.family` at submit time,
    and a CONJECTURED artifact's family is always one `attack` could ground,
    i.e. always in `FAMILIES`). Used for the diversity nudge below --
    finding nothing to parse in a malformed/legacy title is silently
    skipped, not raised (a reporting nudge, not a correctness gate)."""
    families: set[str] = set()
    for art in ledger.find_artifacts(kind="statement", problem="P5", status=Status.CONJECTURED):
        m = _TITLE_FAMILY_RE.match(art.title)
        if m:
            families.add(m.group(1))
    return families


async def mine(
    client: LLMClient, dataset_rows: list[dict], *, k: int | None = None,
    ledger: Ledger | None = None,
) -> list[ConjectureOut]:
    """Sample `k` (default `ROLES["conjecturer"].k`) nonce-diversified
    Conjecturer prompts over `dataset_summary(dataset_rows)`, returning every
    schema-valid `ConjectureOut` produced. Never trusted downstream without
    `attack`.

    `ledger`, when given, does double duty (both pass-throughs are the
    caller's ledger, e.g. `campaign.moves.conjecture_move`'s `state.ledger`):

    - forwarded to `client.complete_many` so every Conjecturer sample is
      billed and provenance-recorded as a `runs` row, same discipline
      `SearchLoop.run_generation` already applies to Searcher calls (M9
      live-campaign finding: this was previously omitted, so conjecturer
      spend was untracked).
    - queried via `_conjectured_families` for a DIVERSITY NUDGE: the prompt
      lists families already CONJECTURED elsewhere in the campaign and asks
      the model to prefer an uncovered one. This is a prompt-level nudge
      ONLY -- it does not restrict `conj.family` to anything, since a
      genuinely new closed form for an already-covered family is still
      legitimate and `attack` grounds whatever comes back regardless (M9
      live-campaign finding: without this, the Conjecturer fixated on one
      family and 10 waves reworded the same claim in prose).
    """
    role = ROLES["conjecturer"]
    k_eff = k if k is not None else role.k
    summary = dataset_summary(dataset_rows)
    covered = _conjectured_families(ledger) if ledger is not None else set()
    nudge = (
        f"Already-conjectured families in this campaign: {', '.join(sorted(covered))}. "
        "Prefer a DIFFERENT family from that list; propose one of them again only "
        "if you have a genuinely new closed form for it.\n"
        if covered else ""
    )

    def build_prompt(nonce: str) -> str:
        return (
            f"[nonce {nonce}]\n{summary}\n"
            "Propose ONE precise closed-form conjecture for F(N) for exactly ONE "
            "of the families tabulated above (path, cycle, star, or complete). "
            "Predict F for EVERY n shown in that family's row -- state nothing "
            "you cannot check against the table.\n"
            f"{nudge}"
            'Emit exactly one ConjectureOut JSON object: {"family": str, '
            '"closed_form": str, "predicted_values": {"<n>": int, ...}, '
            '"confidence": float}.\n'
            f"nonce: {nonce}"
        )

    prompts = [build_prompt(uuid.uuid4().hex) for _ in range(k_eff)]
    results = await client.complete_many(role, prompts, schema=ConjectureOut, ledger=ledger)

    conjectures: list[ConjectureOut] = []
    for result in results:
        if not result.has_artifact:
            continue
        try:
            conjectures.append(ConjectureOut.model_validate(result.parsed))
        except ValidationError:
            continue
    return conjectures


@dataclass(frozen=True)
class AttackReport:
    survived: bool
    checks: int
    counterexample: str | None


def attack(conj: ConjectureOut, dataset_rows: list[dict]) -> AttackReport:
    """The deterministic falsifier (never trusts `conj`; ground truth is
    ONLY the dataset's own exact rows/bounds and the two hard invariants).

    Gate 0 -- shape sanity (all model-supplied, all refuted rather than
    raised; no exception ever escapes the falsifier):

    - empty `predicted_values` -> refuted, "no predictions offered" (a
      conjecture that predicts nothing can never be falsified, so it can
      never be promoted either).
    - any key that is not an integer literal (`int()` fails, e.g.
      `"eight"` or `""`) -> refuted, "malformed prediction key ...".
    - a family not in `FAMILIES` -> refuted, "unknown family ..." (zero
      table lookups are possible for it, so nothing could ever ground it).

    Then, for each predicted `(n, F_pred)` pair, in ascending n order, run
    checks in this fixed sequence and stop at the FIRST failure:

    1. mod-3 ladder: `F_pred === n-3 (mod 3)`.
    2. floor: `F_pred >= n-3`.
    3. table: if `family_graph(conj.family, n)` matches a dataset row --
       `F_pred == row["F"]` if the row is exact, else `F_pred >= row[
       "lower_bound"]` if the row is open (a prediction below a PROVEN bound
       is refuted just as surely as a wrong exact value).

    **Grounding requirement (M6 T5 review I2):** surviving every check is
    NOT enough -- promotion to CONJECTURED requires at least one GROUNDED
    check: an exact-row comparison that ran and passed. A conjecture whose
    every prediction falls outside the dataset's exact rows (out-of-range
    n, or overlap only with open rows) contradicts nothing but is also
    consistent-with nothing -- and spec §9's bar for CONJECTURED is
    'consistent with a VERIFIED_N dataset', which an ungrounded claim
    cannot meet. Such a conjecture reports `survived=False` with
    counterexample "no prediction overlaps the exact table (ungrounded)"
    (kept binary per the AttackReport API; the string documents that this
    is a non-promotion, not a contradiction).

    `checks` counts every comparison actually performed (the falsification
    effort) -- 0 for a gate-0 refutation, 1 or 2 for a value refuted early,
    up to 3 per n for a value that survives all the way through the table
    check (or 2 per n if that n has no matching row in the dataset, e.g. n
    outside the dataset's range). Survivors get `counterexample=None`.
    """
    if not conj.predicted_values:
        return AttackReport(
            survived=False, checks=0, counterexample="no predictions offered"
        )

    predictions: list[tuple[int, int]] = []
    for n_str, f_pred in conj.predicted_values.items():
        try:
            n_parsed = int(n_str)
        except ValueError:
            return AttackReport(
                survived=False,
                checks=0,
                counterexample=f"malformed prediction key {n_str!r}",
            )
        predictions.append((n_parsed, f_pred))
    predictions.sort()

    if conj.family not in FAMILIES:
        return AttackReport(
            survived=False, checks=0, counterexample=f"unknown family {conj.family!r}"
        )

    checks = 0
    grounded = 0  # exact-row comparisons that ran AND passed
    for n, f_pred in predictions:
        checks += 1
        if f_pred % 3 != (n - 3) % 3:
            return AttackReport(
                survived=False,
                checks=checks,
                counterexample=(
                    f"n={n}: predicted F={f_pred} violates F === N-3 (mod 3) "
                    f"(N-3={n - 3})"
                ),
            )

        checks += 1
        if f_pred < n - 3:
            return AttackReport(
                survived=False,
                checks=checks,
                counterexample=f"n={n}: predicted F={f_pred} < floor N-3={n - 3}",
            )

        row = _lookup_row(dataset_rows, conj.family, n)
        if row is None:
            continue

        checks += 1
        if row["exact"]:
            if f_pred != row["F"]:
                return AttackReport(
                    survived=False,
                    checks=checks,
                    counterexample=(
                        f"n={n}: predicted F={f_pred}, actual (exact) F={row['F']}"
                    ),
                )
            grounded += 1
        else:
            if f_pred < row["lower_bound"]:
                return AttackReport(
                    survived=False,
                    checks=checks,
                    counterexample=(
                        f"n={n}: predicted F={f_pred} < proven lower bound "
                        f"{row['lower_bound']} (actual F unknown)"
                    ),
                )

    if grounded == 0:
        return AttackReport(
            survived=False,
            checks=checks,
            counterexample="no prediction overlaps the exact table (ungrounded)",
        )
    return AttackReport(survived=True, checks=checks, counterexample=None)


def _canonical_conjecture_json(conj: ConjectureOut) -> bytes:
    return json.dumps(
        conj.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _semantic_conjecture_key(conj: ConjectureOut) -> bytes:
    """`conj`'s MATH identity -- `(family, predicted_values)` ONLY, with the
    prose `closed_form` deliberately excluded (M9 live-campaign finding: a
    live overnight run produced 10 CONJECTURED artifacts that were all the
    SAME claim -- `family='path'`, the same `predicted_values` -- reworded
    10 different ways, because the old id hashed the full `ConjectureOut`
    including that prose, so cosmetic restatements earned distinct blake3
    ids and all landed as separate artifacts). `confidence` is also excluded
    -- it is the model's self-report, not part of the claim. Canonical JSON
    (sorted keys) so `predicted_values` dict insertion order never perturbs
    the digest."""
    return json.dumps(
        {"family": conj.family, "predicted_values": conj.predicted_values},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def conjecture_artifact_id(conj: ConjectureOut) -> str:
    """The blake3 digest of `conj`'s MATH identity (see
    `_semantic_conjecture_key`) -- the artifact id a submitted `conj` would
    receive, WITHOUT any CAS or ledger write. This is a deliberate exception
    to spec §4.2 rule 1 (id == canonical content) for `statement` artifacts
    ONLY: the CAS content `submit` stores is still the FULL `ConjectureOut`
    (closed_form prose included, via `content_path`) -- only the `id`/dedup
    key is reduced to the semantic tuple, so two conjectures that predict
    the same F for the same family collapse to ONE artifact regardless of
    how differently worded their closed_form is. Callers
    (`campaign.moves.conjecture_move`, `submit`) use this SAME function so
    the identity agrees everywhere: an already-submitted conjecture (by
    math, not by prose) is detected before spending an attack on it.
    """
    return blake3(_semantic_conjecture_key(conj)).hexdigest()


def submit(ledger: Ledger, store: Store, conj: ConjectureOut, report: AttackReport) -> Artifact:
    """Ingest `conj` as a `statement` artifact at `HEURISTIC`, then record
    `report` as `auto_attack` evidence -- promoting to `CONJECTURED` on
    survival or `REFUTED` (terminal) with the counterexample on falsification.
    Returns the artifact as ingested (its `.status` is the pre-evidence
    HEURISTIC snapshot; re-read via `ledger.get_artifact` for the post-
    evidence status, same convention as `search.loop`'s exact-upgrade path).

    **Idempotent on duplicates -- SEMANTIC, not byte-identical (M9 live-
    campaign fix).** The artifact id is `conjecture_artifact_id(conj)`, a
    hash of `(family, predicted_values)` only (see its docstring) -- so a
    model that re-mines yesterday's MATH, worded differently (the common
    case both after `resume` and within a single wave's k>1 nonce-diversified
    samples), must not crash the campaign on the artifacts PRIMARY KEY, and
    must not land a second CONJECTURED artifact either. If the artifact
    already exists, submit SHORT-CIRCUITS: it returns the existing artifact
    AS STORED (its `.status` is the current post-evidence status, e.g.
    CONJECTURED or REFUTED, not a fresh HEURISTIC snapshot) and records NO
    second evidence row -- the original falsification effort stands;
    re-deriving the same claim is not new evidence about it. The CAS content
    under that id is whichever phrasing was submitted FIRST -- a later
    semantic duplicate's own closed_form prose is never written. Belt-and-
    braces: a concurrent insert between the existence check and the ingest
    still collides on the PRIMARY KEY, so `sqlite3.IntegrityError` is
    additionally caught and resolved to the existing row.
    """
    art_id = conjecture_artifact_id(conj)
    try:
        return ledger.get_artifact(art_id)  # duplicate: short-circuit, no new evidence
    except KeyError:
        pass

    content = _canonical_conjecture_json(conj)  # full content, incl. closed_form -- for the CAS
    try:
        art = ingest_artifact(
            ledger,
            store,
            content=content,
            kind="statement",
            problem="P5",
            problem_version=P5_PROBLEM_VERSION,
            title=f"Conjecture: {conj.family} F(N) = {conj.closed_form}",
            status=Status.HEURISTIC,
            artifact_id=art_id,
        )
    except sqlite3.IntegrityError:
        # Raced with another insert of the same MATH -- the row that won
        # IS this conjecture's claim (its own phrasing may differ).
        return ledger.get_artifact(art_id)
    ledger.record_evidence(
        EvidenceRow(
            artifact_id=art.id,
            verifier=_ATTACK_VERIFIER,
            verifier_version=_ATTACK_VERSION,
            binary_hash=_ATTACK_BINARY_HASH,
            verdict=Verdict.PASS if report.survived else Verdict.FAIL,
            details={"checks": report.checks, "counterexample": report.counterexample},
        ),
        new_status=Status.CONJECTURED if report.survived else Status.REFUTED,
    )
    return art
