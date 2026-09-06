
# Lem — Cognitive Architecture Design Document

**`lem-agent` Subsystem Specification**

Zetetic Works Research Corporation · AI for Physics Neolab · Internal · March 2026 · v0.3

---

## 1. Overview

This document specifies the design of Lem’s cognitive architecture: the investigation loop that determines how the system decomposes questions, gathers evidence, drafts explanations, challenges itself, proposes work, executes approved tasks, and responds.

The original draft had the right instinct — a unified loop with a Generator–Verifier–Reviser (GVR) core — but it blurred an important boundary. It sometimes implied that generated syntheses could create graph nodes during reasoning and only later be “verified.” That is the wrong order for a system that claims to maintain durable scientific memory.

This revision fixes the ordering:

1. **retrieve and assemble evidence into an investigation workspace;**
2. **draft syntheses inside that workspace;**
3. **run GVR inside the workspace;**
4. **admit only approved syntheses to the evidence graph.**

The result is a cognitive architecture that is more conservative where it matters, without becoming timid in reasoning depth.

### 1.1 Design Commitments

**One outer loop, many depths.** Simple fact-finding and long investigations use the same outer state machine. Complexity emerges from gap analysis, disagreement, and execution needs.

**Workspace-first reasoning.** Drafts, objections, intermediate chains of thought, and unresolved alternatives belong to the workspace, not the graph.

**Verification before promotion.** Claims that will become future memory must pass through adversarial review before promotion.

**Blocking objections block promotion.** If the Verifier still raises blocking objections after revision, the draft remains challenged and local unless a human explicitly promotes it as provisional.

**Verifier independence is part of the mechanism.** The Verifier is not just a prompt variant. It uses a different role policy, read-only tool access, and preferably a different model family or provider.

**Claims, observations, and runs are handled differently.** A raw measurement or backend result may be admitted with provenance validation. A synthesized explanation may not.

**Honest abstention is a real outcome.** “Cannot answer with current evidence” is not a failure mode. It is an admissible investigation conclusion when properly supported.

### 1.2 Scope

This document covers:

- the outer investigation state machine;
- the investigation workspace and persistence model;
- phase entry/exit conditions;
- the nested GVR admission loop;
- gap analysis and plateau detection;
- execution planning and approval;
- termination logic and abstention;
- prompt assembly and tool restrictions;
- persistence, pause/resume, and testing strategy.

It does **not** redefine the evidence graph storage model or inference-provider wire formats; those live in the corresponding subsystem documents.

---

## 2. Core Invariants

The cognitive architecture is easiest to understand through its invariants.

### 2.1 Invariant 1 — Drafts Stay Local

All synthesized material begins as a `DraftSynthesis` inside the investigation workspace. This includes:

- explanatory narratives;
- comparison tables;
- hypothesis sets;
- proposed decisions or recommendations;
- reusable report fragments.

No draft enters the evidence graph until an admission decision is made.

### 2.2 Invariant 2 — The Verifier Cannot Mutate Global Memory

The Verifier may inspect:

- the workspace draft;
- admitted graph nodes;
- primary artifacts and external sources available through read-only retrieval tools.

The Verifier may **not**:

- write graph nodes;
- alter the workspace except through its structured report;
- launch execution backends;
- “fix” the draft itself.

That separation keeps critique legible and auditable.

### 2.3 Invariant 3 — Unresolved Blocking Objections Do Not Auto-Promote

Warnings may still permit admission with caveats. Blocking objections do not.

When the iteration budget ends with unresolved blocking objections, the system has three valid outcomes:

- hold the draft as challenged;
- escalate to human review;
- allow human promotion as provisional.

It does **not** silently downgrade the severity and pretend the claim was admitted cleanly.

### 2.4 Invariant 4 — Verification, Confidence, and Freshness Are Separate

The cognitive loop must treat these as separate outputs:

- **confidence** in the current claim;
- **verification status** of the claim at admission time;
- **freshness** of the claim relative to current upstream evidence.

This drives later re-verification behavior and UI communication.

### 2.5 Invariant 5 — Observation Can Enter Memory Without Narrative

A simulation run that returns a numeric result is already evidence. It does not require an LLM to narrate it before it becomes memory.

The cognitive loop therefore distinguishes:

- **capture** of raw observations and runs; and
- **interpretation** of those observations.

Only the second class requires GVR for admission.

---

## 3. Outer State Machine

### 3.1 Phases

The top-level loop keeps six phases:

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Phase {
    Assess,
    Investigate,
    Synthesize,
    Plan,
    Execute,
    Respond,
}
```

`Paused` remains an investigation status, not a phase.

### 3.2 Transition Overview

```
ASSESS ───────────────→ INVESTIGATE

INVESTIGATE ─────────→ INVESTIGATE   (gaps remain and retrieval is productive)
INVESTIGATE ─────────→ SYNTHESIZE    (evidence sufficient or plateau reached)

SYNTHESIZE ──────────→ PLAN          (tests / runs needed)
SYNTHESIZE ──────────→ RESPOND       (question answerable now)
SYNTHESIZE ──────────→ RESPOND       (cannot answer conclusion admitted)

PLAN ────────────────→ EXECUTE       (approved)
PLAN ────────────────→ RESPOND       (declined / scoped away)
PLAN ────────────────→ PAUSED        (awaiting approval)

EXECUTE ─────────────→ INVESTIGATE   (new results open new gaps)
EXECUTE ─────────────→ SYNTHESIZE    (new evidence is ready for re-synthesis)

RESPOND ─────────────→ terminal
```

### 3.3 Why Synthesize Still Exists as One Phase

The architecture could split `Synthesize`, `Verify`, and `Admit` into separate outer states. That would make the machine more explicit but also noisier. This revision keeps `Synthesize` as one outer phase because the outer loop cares about *where the investigation is*, not every micro-step of the admission process.

The nested admission machine is where GVR lives.

---

## 4. Investigation Workspace

### 4.1 Workspace Data Model

```rust
pub struct InvestigationWorkspace {
    pub facets: Vec<Facet>,
    pub coverage: Vec<FacetCoverage>,
    pub evidence_slice: Vec<NodeId>,
    pub artifact_refs: Vec<ArtifactRef>,
    pub draft_syntheses: Vec<DraftSynthesis>,
    pub verification_reports: Vec<VerificationReport>,
    pub hypotheses: Vec<HypothesisDraft>,
    pub pending_plan: Option<ExecutionPlanDraft>,
    pub summaries: Vec<ContextSummary>,
    pub cost: InvestigationCostState,
}
```

The workspace is durable. It is persisted after phase transitions, tool calls, GVR iterations, approvals, and execution-status updates.

### 4.2 DraftSynthesis

```rust
pub struct DraftSynthesis {
    pub id: Ulid,
    pub kind: DraftKind,
    pub text: String,
    pub claims: Vec<DraftClaim>,
    pub supporting_nodes: Vec<NodeId>,
    pub assumptions: Vec<AssumptionDraft>,
    pub confidence: DraftConfidence,
    pub created_at: Timestamp,
    pub iteration: u32,
}

pub enum DraftKind {
    DirectAnswer,
    HypothesisSet,
    Recommendation,
    ReportFragment,
    CannotAnswer,
}
```

The important property is that a `DraftSynthesis` is not yet evidence-graph memory. It is an object under review.

### 4.3 Verification Report

```rust
pub struct VerificationReport {
    pub draft_id: Ulid,
    pub verdict: VerificationVerdict,
    pub issues: Vec<VerificationIssue>,
    pub suggested_confidence_adjustments: Vec<ConfidenceAdjustment>,
    pub overall_notes: String,
    pub verifier_provenance: VerifierProvenance,
}

pub enum VerificationVerdict {
    Pass,
    PassWithCaveats,
    Revise,
    Escalate,
}

pub struct VerificationIssue {
    pub dimension: VerificationDimension,
    pub severity: IssueSeverity,
    pub detail: String,
    pub affected_claim_ids: Vec<String>,
    pub evidence_refs: Vec<Reference>,
}

pub enum IssueSeverity {
    Warning,
    Blocking,
}
```

### 4.4 Admission Decision

```rust
pub enum AdmissionDecision {
    Admit {
        caveats: Vec<String>,
    },
    HoldAsChallenged {
        blocking_issues: Vec<VerificationIssue>,
    },
    EscalateToHuman {
        reason: String,
    },
}
```

This type is the conceptual hinge of the revised design. The GVR loop does not just output “approved / not approved.” It outputs a concrete admission decision.

---

## 5. Phase Definitions

## 5.1 Assess

**Purpose:** turn the user request into an investigation skeleton.

**Primary outputs:**
- intent and scope;
- first-pass facet decomposition;
- initial evidence-graph trace;
- initial confidence about whether the answer may already exist.

**Tools:** `evidence_search`, `evidence_trace`, lightweight artifact lookup

**Model role:** assessor / decomposer (fast profile)

**Exit condition:** at least one gap-analysis round is initialized.

Assess never answers the question directly. Even apparently trivial questions advance to Investigate, although the later phases may be very short.

### 5.2 Investigate

**Purpose:** assemble an evidence slice sufficient to support, refute, or bound an answer.

**Core loop:**
1. choose target facets;
2. retrieve artifacts or graph nodes;
3. extract observations where appropriate;
4. update coverage and novelty metrics;
5. repeat while evidence gain remains worthwhile.

**Tools:** `kb_search`, `kb_fetch`, `artifact_fetch`, `evidence_search`, `evidence_trace`, deterministic extraction helpers, `observation_create`

**Model roles:** retriever / extractor / gap analyst

**Important correction:** Investigate may create **artifact**, **observation**, or **run** records. It does **not** create admitted claim nodes. If the model summarizes evidence during retrieval, that summary remains workspace-local unless and until admitted later.

### 5.3 Synthesize

Synthesize is the phase where the system turns the current evidence slice into one of three outcomes:

- a direct answer;
- a hypothesis or recommendation set that implies a plan;
- an admissible “cannot answer with current evidence” conclusion.

Synthesize contains the nested GVR admission loop.

### 5.4 Plan

**Purpose:** design the minimum useful next action.

A plan may include:

- compute-backed runs;
- targeted retrieval actions;
- artifact comparison work;
- formal checks;
- report drafting tasks;
- in future phases, hardware or facility proposals.

The plan phase produces an `ExecutionPlanDraft` and uses backend `validate` calls to price and normalize concrete actions.

### 5.5 Execute

**Purpose:** perform approved actions and turn outcomes into evidence.

Execute is allowed to create **run** records directly in the graph because they are observational outputs from backends. It may also create artifact references to logs, plots, tables, and raw result files.

It does not admit new synthesized claims by itself. Any interpretation of execution results must flow back through Synthesize.

### 5.6 Respond

**Purpose:** communicate the state of the investigation clearly and truthfully.

Respond may present:

- admitted claims and their confidence;
- caveats and outdated dependencies;
- challenged drafts that were *not* admitted;
- proposed next steps;
- cost and provenance summary.

Respond is where the user sees the result, but not where the epistemic state is decided.

---

## 6. The Nested GVR Admission Loop

### 6.1 Substate Machine

Inside Synthesize, the following nested state machine runs:

```
DRAFT → VERIFY → [REVISE → VERIFY]* → ADMIT / HOLD / ESCALATE
```

### 6.2 Generate

Generation produces a draft from the evidence slice, not a final answer.

**Tools:** read-only graph/artifact access, workspace reads, optional local structuring helpers

**Model role:** generator

**Constraints:**
- must enumerate assumptions;
- must attach supporting node references to each nontrivial claim;
- must produce structured claims, not only free text;
- may not create graph nodes.

### 6.3 Verify

Verification is a distinct model call with a distinct tool policy.

**Tools:** read-only only — graph search/trace, artifact fetch, source fetch, optional limited external retrieval

**Model role:** verifier

**Default policy:**
- prefer a different provider/model family from the Generator when available;
- lower temperature or deterministic settings;
- output must conform to the `VerificationReport` schema;
- no editing of the draft.

**Verification dimensions:**

| Dimension | What the Verifier asks |
|---|---|
| **Evidence support** | Does each claim actually follow from the cited evidence? |
| **Assumption explicitness** | What had to be true for this reasoning to work, and was it stated? |
| **Internal consistency** | Do the claims cohere with one another? |
| **Graph consistency** | Does this draft conflict with admitted graph memory, and if so is that conflict acknowledged? |
| **Confidence calibration** | Is the stated confidence stronger than the evidence warrants? |
| **Decision / action soundness** | If the draft recommends work, is the recommendation logically tied to the evidence and uncertainty? |

The sixth dimension is added in this revision because scientific advice is often not just descriptive. Recommendations deserve direct scrutiny too.

### 6.4 Revise

Revision is targeted. The Reviser receives:

- the current draft;
- the structured verifier report;
- the relevant evidence slice.

The Reviser’s job is to address specific objections while preserving what already passed.

**Tools:** same read-only evidence access as Generator, plus workspace mutation only

**Model role:** reviser

**Compute policy:** escalate effort with repeated blocking objections, but do not change the admission rules.

### 6.5 Admission

Once verification returns `Pass` or `PassWithCaveats`, the system constructs the corresponding global node(s) and admits them to the graph with verification metadata attached.

When verification returns `Revise`, the system loops.

When verification returns `Escalate`, or when iteration limits are exhausted with unresolved blocking issues, the system produces either:

- `HoldAsChallenged`, or
- `EscalateToHuman`.

### 6.6 Reference Implementation Sketch

```rust
async fn synthesize_with_gvr(
    &self,
    investigation: &mut Investigation,
    ui: &dyn AgentUI,
) -> Result<SynthesisPhaseResult, AgentError> {
    let evidence = self.gather_evidence_slice(investigation)?;
    let mut draft = self.generate_draft(&evidence, investigation).await?;

    for iteration in 0..self.config.gvr.max_iterations {
        let report = self.verify_draft(&draft, &evidence, investigation).await?;
        investigation.workspace.verification_reports.push(report.clone());
        ui.show_verification(&report).await;

        match report.verdict {
            VerificationVerdict::Pass => {
                let admission = self.admit_draft(&draft, &report, investigation, vec![]).await?;
                return Ok(SynthesisPhaseResult::Admitted(admission));
            }
            VerificationVerdict::PassWithCaveats => {
                let caveats = collect_caveats(&report);
                let admission = self.admit_draft(&draft, &report, investigation, caveats).await?;
                return Ok(SynthesisPhaseResult::Admitted(admission));
            }
            VerificationVerdict::Revise if iteration + 1 < self.config.gvr.max_iterations => {
                draft = self.revise_draft(&draft, &report, &evidence, iteration).await?;
            }
            VerificationVerdict::Revise | VerificationVerdict::Escalate => {
                let decision = self.make_admission_decision(&draft, &report)?;
                return Ok(SynthesisPhaseResult::NotAdmitted(decision));
            }
        }
    }

    unreachable!("loop exits by return");
}
```

### 6.7 Why Auto-Commit on Failure Was Removed

The original draft allowed admission with caveats after max iterations even when objections remained. That is too permissive for global memory.

This revision narrows that behavior:

- **warnings** may yield admission with caveats;
- **blocking objections** yield hold or escalation, not silent promotion.

That preserves the user’s ability to see incomplete reasoning while protecting future investigations from inheriting it as trusted memory.

---

## 7. Gap Analysis and Sufficiency

### 7.1 Facets

A facet is an independently investigable aspect of the question.

```rust
pub struct Facet {
    pub id: Ulid,
    pub description: String,
    pub priority: FacetPriority,
    pub query_terms: Vec<String>,
}

pub enum FacetPriority {
    Critical,
    Important,
    Optional,
}
```

### 7.2 Coverage

```rust
pub struct FacetCoverage {
    pub facet_id: Ulid,
    pub status: CoverageStatus,
    pub supporting_nodes: Vec<NodeId>,
    pub note: Option<String>,
}

pub enum CoverageStatus {
    Covered,
    PartiallyCovered,
    Uncovered,
    Unretrievable,
}
```

### 7.3 Recommendation

```rust
pub enum GapRecommendation {
    ContinueRetrieval { target_facets: Vec<Ulid> },
    AdvanceToSynthesis { reason: String },
    Escalate { reason: String },
}
```

### 7.4 Facet Evolution

Facet decomposition is not static. New facets may appear when:

- evidence reveals hidden assumptions;
- two sources disagree in a way that creates a new question;
- an execution result opens an unexpected line of inquiry.

The gap-analysis prompt is therefore allowed to add, merge, and downgrade facets.

### 7.5 Sufficiency Standard

The system advances to Synthesize when one of the following is true:

1. all critical facets are covered;
2. retrieval has plateaued and the remaining gaps are explicitly representable;
3. a decisive run result has arrived;
4. the best honest conclusion is “cannot answer yet / with current evidence.”

This keeps the system from chasing theoretical completeness when the evidence frontier is already legible.

---

## 8. Plateau Detection and Termination

### 8.1 Plateau Metrics

After each Investigate round, the agent records:

- new admitted observations or runs brought into scope;
- number of facets moved to better coverage states;
- novelty score of retrieved artifacts;
- contradiction count;
- whether new execution opportunities were discovered.

A plateau is declared when multiple rounds fail to improve critical coverage meaningfully.

### 8.2 Hard Stops vs Honest Stops

The system distinguishes:

- **hard stops** — cost ceiling, time ceiling, authorization ceiling;
- **honest stops** — evidence frontier reached, useful abstention produced, question resolved.

The distinction appears in the final investigation summary.

### 8.3 Cannot Answer as a First-Class Outcome

```rust
pub struct CannotAnswerOutcome {
    pub reason: String,
    pub what_was_checked: Vec<NodeId>,
    pub missing_facets: Vec<Facet>,
    pub suggested_next_actions: Vec<String>,
}
```

A `CannotAnswerOutcome` still passes through GVR because it is a synthesized conclusion about the state of the evidence. Once admitted, it becomes durable memory that future investigations can build on or challenge.

---

## 9. Planning and Execution

### 9.1 Planning Heuristic

The planning policy ranks candidate actions by:

1. **falsification value** — could this kill the leading hypothesis?
2. **discrimination value** — could this separate live alternatives?
3. **information density per unit cost** — how much uncertainty reduction per dollar/hour?
4. **confirmatory value** — useful but lowest priority when discrimination is available.

### 9.2 GVR-Lite for Plans

Plans are not pure claims and not pure runs. They sit in between. This revision therefore uses a lighter review path for plans:

- backend `validate` checks parameter correctness, runtime, and cost;
- a planning verifier checks that the proposed action actually answers the scientific question it claims to answer.

This is effectively a **GVR-lite** path specialized for action proposals.

### 9.3 Execute and Return-to-Synthesis

Execute may produce:

- successful run records;
- failed run records;
- timeout records;
- artifacts such as plots or raw tables.

After execution, the loop usually returns to Synthesize rather than Respond directly, because the new runs still need interpretation and admission.

The only case where Execute can jump straight to Respond is when the user asked purely for backend execution status and no interpretation.

---

## 10. Prompt and Context Assembly

### 10.1 Four-Layer Prompt Assembly

The prompt stack remains useful, but it is reinterpreted slightly in this revision:

1. **system identity** — Lem’s role and epistemic commitments;
2. **role prompt** — generator, verifier, reviser, planner, narrator, etc.;
3. **investigation context** — facets, evidence slice, workspace summaries, prior reports;
4. **task instruction** — the exact job for this call.

Caching opportunities, where supported by providers, are an implementation optimization. The cognitive design does not depend on them.

### 10.2 Example System Commitments

The system prompt should communicate at least these commitments:

- ground claims in evidence;
- distinguish observation from inference;
- expose assumptions;
- abstain honestly when evidence runs out;
- never present challenged drafts as admitted conclusions.

### 10.3 Role Prompt Differences

The Verifier prompt should be allowed to sound different from the Generator prompt. Symmetry is not the goal.

**Generator:** completeness, clarity, explicit assumptions, candidate structure.

**Verifier:** fault finding, unsupported claim detection, contradiction surfacing, confidence skepticism, action skepticism.

**Reviser:** targeted repair while preserving what passed.

---

## 11. Tool Access Policy

### 11.1 Phase-Restricted Tools

| Phase / subphase | Tool classes allowed |
|---|---|
| Assess | graph search / trace, lightweight artifact lookup |
| Investigate | retrieval, artifact fetch, deterministic extraction, observation creation |
| Synthesize / Generate | read-only evidence + workspace mutation only |
| Synthesize / Verify | read-only evidence and primary-source retrieval only |
| Synthesize / Revise | read-only evidence + workspace mutation only |
| Plan | backend describe / validate, graph search, cost lookup |
| Execute | backend launch / status, run-record creation, artifact registration |
| Respond | graph trace, report drafting, presentation helpers |

### 11.2 Why Generator and Reviser Lost `evidence_create`

The original drafts gave Generate and Revise permission to create evidence nodes directly. That contradicts the admission model.

This revision removes direct graph-write capability from those subphases. They write drafts to the workspace instead. Graph writes happen only through explicit admission or through observation/run capture paths.

### 11.3 Verifier Tool Asymmetry

The Verifier is intentionally allowed to inspect primary sources independently, including sources the Generator summarized imperfectly. This asymmetry is a feature, not a bug. It increases the chance that citation drift or omitted caveats are caught before promotion.

---

## 12. Authority, Pause, and Resume

### 12.1 Investigation Status

```rust
pub enum InvestigationStatus {
    Active,
    Paused(PauseReason),
    Completed,
    Abandoned,
}
```

### 12.2 Pause Triggers

An investigation pauses when:

- explicit user approval is required and not yet granted;
- a compute or policy ceiling is reached;
- the user explicitly pauses the investigation;
- a challenged draft is escalated for human review.

### 12.3 Resume Semantics

Resumption restores:

- current phase;
- workspace state;
- pending approvals;
- backend job watchers;
- last admitted nodes and verification reports.

Because drafts remain local until admitted, resume is especially important: unfinished reasoning should not have to be redone from scratch.

---

## 13. Evaluation and Testing

### 13.1 What to Measure

The strongest tests of this architecture are not generic QA benchmarks. They are process metrics such as:

- false-admission rate for seeded unsupported claims;
- verifier catch rate on omitted assumptions;
- rate of stale verified nodes successfully re-verified after upstream changes;
- cost per useful investigation outcome;
- percentage of challenged drafts that were correctly held rather than admitted;
- user trust and correction burden.

### 13.2 Unit and Integration Tests

Core categories:

- phase transitions and pause/resume correctness;
- workspace serialization and replay;
- GVR branching behavior;
- tool restriction enforcement;
- backend validation and planning review;
- cannot-answer admission path;
- re-synthesis after execution;
- human override to provisional promotion.

### 13.3 Seeded-Fault Scenarios

This architecture especially needs seeded-fault tests such as:

- citation is correct source but wrong interpretation;
- one hidden assumption is omitted;
- two claims are individually plausible but jointly inconsistent;
- recommendation solves the wrong problem;
- execution result contradicts an older admitted claim and should trigger re-verification.

---

## 14. Summary

The revised cognitive architecture keeps the original ambition — a unified scientific agent loop — while making the most important internal boundary explicit:

> **Lem reasons in the workspace, verifies in the workspace, and only then promotes admitted conclusions into durable memory.**

That makes the GVR loop structurally meaningful, not merely aspirational.
