"""SearchLoop (M6 T3, spec §9): the SEARCH generation cycle.

One generation = k Searcher prompts (nonce-diverse, round-robin over
`targets`) -> `client.complete_many` -> per candidate: parse/screen (never
trusted) -> `verify_agreed` (the certified A/B pair) -> population insert +
evidence. Every per-candidate failure mode is counted and isolated -- a
malformed or wrong candidate never crashes the wave -- EXCEPT engine
disagreement (`verify_agreed`'s F3 alarm, spec §7): that is a machinery
fault, not evidence about the candidate, and immediately aborts the whole
generation via `F3Alarm` so a human/orchestrator can stop the world.

Trust discipline: no model output is ever used directly. A `ConstructionOut`
becomes a domain `Construction` only via `to_construction`'s SCREEN gate
(schemas.py); a `Construction` only enters the population after a PASS from
`verify_agreed` (the certification-gated agreement of BOTH independent
fusion verifiers, verifiers/registry.py). CAS/ledger writes go through the
single-writer `Ledger`.

Exact-upgrade detection: when a PASS's achieved LC-orbit key equals one of
`targets`' `lc_orbit_key` AND the achieved fusion count equals that target's
`target_f`, this is the scientific payload (the plan doc's payload 1): a
previously-open orbit now has a certified F=N witness. That event is
recorded durably -- a small `construction`-kind artifact (the model's own
validated JSON) ingested at `Status.HEURISTIC`, plus a `verify_agreed`
evidence row (verdict PASS) referencing it -- gated on `population.consider`
reporting an actual improvement (`improved=True`): a byte-identical
re-submission of an already-known witness is a `population` "duplicate", not
new evidence, and re-ingesting the SAME content would collide with the CAS
artifact's PRIMARY KEY (an artifact's id IS its content digest, spec §4.2)
and raise `sqlite3.IntegrityError` -- gating on `improved` sidesteps that
collision by construction, not by catching it. The DATASET row's own status
change stays deferred to the M7 orchestrator (this module only emits the
evidence + the report).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass

from pydantic import ValidationError

import empiricist.verifiers.registry as _registry_module
from empiricist.ledger.db import Ledger
from empiricist.ledger.ingest import ingest_artifact
from empiricist.ledger.models import EvidenceRow, Status, Verdict
from empiricist.llm.client import LLMClient
from empiricist.llm.roles import ROLES
from empiricist.search.database import Population
from empiricist.search.schemas import ConstructionOut, ScreenReject, to_construction
from empiricist.store import Store
from empiricist.verifiers.base import module_source_hash
from empiricist.verifiers.registry import Registry, verify_agreed

_VERIFY_AGREED_VERSION = "1.0"
# Ties the evidence row's binary_hash to the actual code that decides
# agreement (verify_agreed lives in verifiers/registry.py) -- consistent
# with base.module_source_hash's "editing this source mints a new identity"
# discipline used for real Verifiers.
_VERIFY_AGREED_BINARY_HASH = module_source_hash(_registry_module)


@dataclass(frozen=True)
class TargetSpec:
    n: int
    lc_orbit_key: str            # the target orbit identity
    representative_edges: tuple  # sorted edge tuples for the prompt
    known_bound: str             # e.g. "F >= 8 (Tier-0 unreachable)" or "best known F = 6"
    target_f: int                # the fusion count a success would establish (e.g. N for open)


class F3Alarm(Exception):
    """verify_agreed reported engine disagreement -- one certified engine is
    wrong. Stop the world."""


@dataclass(frozen=True)
class GenerationReport:
    gen: int
    sampled: int
    no_artifact: int
    screened_out: int            # ScreenReject count
    verify_fail: int
    verify_error: int            # non-disagreement errors
    inserted: int                # population.consider -> True
    duplicates: int              # consider -> False
    exact_upgrades: tuple        # (target lc_orbit_key, achieved F) pairs hitting target_f
    screen_reasons: tuple        # distinct reasons observed


def _canonical_construction_json(out: ConstructionOut) -> bytes:
    """Deterministic CAS content for a PASSing candidate: the model's own
    schema-validated output (steps/target as it emitted them), canonically
    ordered so identical proposals content-address to the same artifact."""
    return json.dumps(
        out.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class SearchLoop:
    def __init__(
        self,
        client: LLMClient,
        ledger: Ledger,
        store: Store,
        registry: Registry,
        population: Population,
        *,
        island: int = 0,
    ) -> None:
        self._client = client
        self._ledger = ledger
        self._store = store
        self._registry = registry
        self._population = population
        self._island = island

    def build_prompt(self, target: TargetSpec, nonce: str) -> str:
        edges = ", ".join(f"({a},{b})" for a, b in target.representative_edges)
        return (
            f"[nonce {nonce}]\n"
            f"Target orbit: n={target.n} qubits, representative edges: [{edges}]. "
            f"Known bound: {target.known_bound}. A verified construction reaching "
            f"fusion_count={target.target_f} establishes F={target.target_f} for "
            "this orbit.\n"
            "Emit exactly one ConstructionOut JSON object: "
            '{"resources": int, "steps": [{"op": "fuse"|"lc", "args": [int, ...]}], '
            '"target_n": int, "target_edges": [[int, int], ...]}. '
            'A "fuse" step takes 2 distinct workspace qubit ids; a "lc" step '
            "(local complementation) takes 1.\n"
            "Workspace layout: resource i is a fresh GHZ3 star on qubits 3*i, "
            "3*i+1, 3*i+2 (star/center qubit at 3*i, leaves 3*i+1 and 3*i+2).\n"
            "Physics hints: the reachable fusion count F obeys F mod 3 == "
            "(N - 3) mod 3 (the mod-3 ladder, N = target_n); the winning shape is "
            "usually all merge-fusions first (joining every resource into one "
            "component) followed by AT MOST ONE intra-component fusion at the end "
            "to reach F = N.\n"
            f"nonce: {nonce}"
        )

    async def run_generation(
        self, gen: int, targets: list[TargetSpec], *, k: int | None = None
    ) -> GenerationReport:
        if not targets:
            raise ValueError("run_generation requires at least one TargetSpec")

        role = ROLES["searcher"]
        k_eff = k if k is not None else role.k
        prompts = [
            self.build_prompt(targets[i % len(targets)], uuid.uuid4().hex)
            for i in range(k_eff)
        ]
        results = await self._client.complete_many(
            role, prompts, schema=ConstructionOut, ledger=self._ledger
        )

        target_by_key = {t.lc_orbit_key: t for t in targets}

        # complete_many (M4) returns only non-None results, so the samples
        # that produced NOTHING AT ALL (refusal at the transport layer, a
        # timeout, an unparseable envelope) are exactly the ones missing from
        # `results` -- count those, then add every returned result that
        # completed but produced no usable structured artifact.
        no_artifact = len(prompts) - len(results)
        screened_out = 0
        verify_fail = 0
        verify_error = 0
        inserted = 0
        duplicates = 0
        exact_upgrades: list[tuple[str, int]] = []
        screen_reasons: list[str] = []

        for result in results:
            if not result.has_artifact:
                no_artifact += 1
                continue

            try:
                parsed_out = ConstructionOut.model_validate(result.parsed)
            except ValidationError as exc:
                screened_out += 1
                screen_reasons.append(f"schema: {exc}")
                continue

            try:
                construction = to_construction(parsed_out)
            except ScreenReject as exc:
                screened_out += 1
                screen_reasons.append(exc.reason)
                continue

            verdict_result = verify_agreed(self._registry, construction)

            if verdict_result.verdict is Verdict.ERROR:
                if verdict_result.details.get("disagreement"):
                    raise F3Alarm(verdict_result.details)
                verify_error += 1
                continue

            if verdict_result.verdict is Verdict.FAIL:
                verify_fail += 1
                continue

            # PASS: both certified engines agree this candidate reaches its
            # claimed target's LC orbit.
            achieved_key = verdict_result.details["stab_fusion_key"]
            f = construction.fusion_count
            cert_json = _canonical_construction_json(parsed_out)
            cert_hash = self._store.put(cert_json)
            improved = self._population.consider(
                achieved_key, self._island, f"n{construction.target.n}", [f], cert_hash
            )
            if improved:
                inserted += 1
            else:
                duplicates += 1

            target = target_by_key.get(achieved_key)
            if improved and target is not None and f == target.target_f:
                exact_upgrades.append((target.lc_orbit_key, f))
                art = ingest_artifact(
                    self._ledger, self._store, content=cert_json, kind="construction",
                    problem="P5",
                    title=f"SEARCH exact upgrade: orbit {achieved_key[:12]} F={f}",
                    status=Status.HEURISTIC,
                )
                self._ledger.record_evidence(EvidenceRow(
                    artifact_id=art.id,
                    verifier="verify_agreed",
                    verifier_version=_VERIFY_AGREED_VERSION,
                    binary_hash=_VERIFY_AGREED_BINARY_HASH,
                    verdict=Verdict.PASS,
                    details={
                        "achieved_key": achieved_key,
                        "f": f,
                        "target": asdict(target),
                        "upgrade": True,
                    },
                ))

        report = GenerationReport(
            gen=gen,
            sampled=len(prompts),
            no_artifact=no_artifact,
            screened_out=screened_out,
            verify_fail=verify_fail,
            verify_error=verify_error,
            inserted=inserted,
            duplicates=duplicates,
            exact_upgrades=tuple(exact_upgrades),
            screen_reasons=tuple(dict.fromkeys(screen_reasons)),
        )
        self._population.log_event(gen, "generation", asdict(report))
        return report
