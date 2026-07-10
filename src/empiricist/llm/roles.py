"""The seven roles (spec §5.4): each a system prompt + sampling policy.

A Role is the frozen policy for one kind of model call. The system_prompt here
is the ROLE CARD; the Context Builder (a later milestone) prepends the frozen
problem spec + verified dependencies to form the full system prompt. Diversity
in SEARCH waves comes from prompt/nonce variation, never temperature (Fable 5
exposes none). v0-active vs deferred-stub is per spec D11.
"""

from __future__ import annotations

from dataclasses import dataclass

from empiricist.llm.models import Effort

_MODEL = "claude-fable-5"


@dataclass(frozen=True)
class Role:
    name: str
    system_prompt: str          # the role card (spec-block prepended later)
    effort: Effort
    k: int  # max samples per wave; the client's semaphore clamps actual concurrency to sustained-k
    active: bool                # False = deferred v0 stub (spec D11)
    model: str = _MODEL


ROLES: dict[str, Role] = {
    "prospector": Role(
        name="prospector",
        system_prompt=(
            "You are the Prospector. Report prior art on the given problem. "
            "Every claim about the literature is EXTERNAL and must cite a source; "
            "you never assert a mathematical fact as established. Output the "
            "external_claims schema."
        ),
        effort=Effort.MEDIUM, k=1, active=False,
    ),
    "toolwright": Role(
        name="toolwright",
        system_prompt=(
            "You are the Toolwright. Write verifier/enumerator code with tests. "
            "Output the code_artifact schema. Your code is never trusted until it "
            "passes its golden suite and is certified by the harness."
        ),
        effort=Effort.HIGH, k=1, active=False,
    ),
    "searcher": Role(
        name="searcher",
        system_prompt=(
            "You are the Searcher. Propose one concrete candidate construction for "
            "the stated objective, in the required canonical form. Favor diversity: "
            "the nonce in your prompt distinguishes your attempt from parallel ones. "
            "Do not explain; emit only the schema."
        ),
        effort=Effort.LOW, k=32, active=True,
    ),
    "conjecturer": Role(
        name="conjecturer",
        system_prompt=(
            "You are the Conjecturer. Given a VERIFIED_N dataset, propose a precise "
            "closed-form statement for a named family and predict its values. State "
            "nothing you cannot check against the data. Favor a family the prompt "
            "does not flag as already-conjectured when one is listed -- a campaign "
            "of restated claims about one family is not progress. Output the "
            "conjecture schema."
        ),
        effort=Effort.MEDIUM, k=8, active=True,
    ),
    "prover": Role(
        name="prover",
        system_prompt=(
            "You are the Prover. Produce a lemma-DAG proof of the frozen statement: "
            "each lemma separately stated with its dependencies. No prose proof; a "
            "structured DAG whose every edge is independently checkable."
        ),
        effort=Effort.MAX, k=1, active=True,
    ),
    "critic": Role(
        name="critic",
        system_prompt=(
            "You are the Critic. You receive a lemma DAG and have no stake in its "
            "correctness. Your only win is a concrete defect: a false lemma (give a "
            "counterexample), an inferential gap (name lemma+line+missing step), or a "
            "definition mismatch. 'Looks correct' is a failure unless you checked "
            "every edge; then emit NO_GAP_FOUND with the edges checked. Never propose "
            "fixes. Output the critique schema."
        ),
        effort=Effort.MAX, k=2, active=True,
    ),
    "formalizer": Role(
        name="formalizer",
        system_prompt=(
            "You are the Formalizer. Emit a Lean 4 module (statement, then proof) "
            "against pinned mathlib, iterating on compiler feedback. Output the "
            "lean_module schema. sorry and native_decide are forbidden."
        ),
        effort=Effort.HIGH, k=1, active=True,
    ),
}


def active_roles() -> list[Role]:
    """Roles exercised in v0 (Prospector + Toolwright are deferred stubs, D11)."""
    return [r for r in ROLES.values() if r.active]
