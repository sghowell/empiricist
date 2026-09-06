
# Lem — Evidence Graph Design Document

**`lem-core` Subsystem Specification**

Zetetic Works Research Corporation · AI for Physics Neolab · Internal · March 2026 · v0.3

---

## 1. Overview

This document specifies the design of Lem’s evidence graph: the durable, queryable record of artifacts, observations, runs, claims, hypotheses, and decisions that future investigations are allowed to rely on.

The key revision in this version is conceptual rather than cosmetic:

> **The evidence graph stores admitted research memory, not every intermediate thought.**

Draft syntheses, unresolved objections, and half-repaired narratives belong in the investigation workspace. The graph holds what has been captured or admitted with enough provenance and review to justify reuse.

This revised design also fixes a second conceptual issue from the original document set: it separates **confidence**, **verification**, **admission**, and **freshness** into distinct axes.

### 1.1 Design Goals

**Auditability.** Every mutation produces an event. Any admitted claim can be traced back to the sources, runs, and verification record that supported its admission.

**Reuse without contamination.** The graph should be safe as prior memory for future investigations. That requires strict handling of drafts, provisional claims, and outdated verification.

**Progressive structure.** The graph should accept lightly structured observations early and richer typed records over time without requiring enum edits for every new physics concept.

**Correct propagation.** When upstream evidence changes, dependent claims become stale and their prior verification becomes outdated in a deterministic, bounded way.

**Explicit identity semantics.** Exact duplicate artifacts/runs and semantically “same question, newer answer” claims are different cases and should not share one overloaded dedup mechanism.

**Good local performance.** The system should remain fast at thousands to low hundreds of thousands of nodes in local and small shared deployments.

### 1.2 What the Graph Does Not Store

The graph is not the place for:

- hidden chain-of-thought or unconstrained scratch reasoning;
- every intermediate prompt/response pair;
- unresolved challenged drafts by default;
- large raw artifacts inlined into node rows;
- provider-specific inference caches.

Those belong in the investigation workspace, event log, or artifact store.

---

## 2. Core Type Hierarchy

### 2.1 Node

```rust
pub struct Node {
    pub id: Ulid,
    pub class: RecordClass,
    pub kind: NodeKind,
    pub summary: String,
    pub confidence: Confidence,
    pub verification: VerificationRecord,
    pub admission: AdmissionStatus,
    pub payload: Option<serde_json::Value>,
    pub references: Vec<Reference>,
    pub created_at: Timestamp,
    pub created_by: Actor,
    pub status: NodeStatus,
    pub exact_hash: Option<ExactHash>,
    pub semantic_key: Option<SemanticKey>,
}
```

This revision introduces four structural changes relative to the earlier draft:

1. `class` is a stable architectural category used for policy and propagation behavior.
2. `verification` is always present as a structured record, even when verification is `NotRequired`.
3. `admission` is separate from verification, allowing explicit human-provisional promotion.
4. `exact_hash` and `semantic_key` replace the earlier single content hash.

### 2.2 RecordClass

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RecordClass {
    Artifact,
    Observation,
    Run,
    Claim,
    Hypothesis,
    Decision,
    ReportFragment,
}
```

`kind` remains extensible and domain-specific. `class` stays small and stable because the system depends on it for policy decisions.

- `Artifact` — a document, notebook snapshot, code commit, image, dataset pointer.
- `Observation` — a specific extracted or user-supplied fact with provenance.
- `Run` — an execution result from a backend such as a simulation, analysis job, or proof check.
- `Claim` — an admitted synthesized statement.
- `Hypothesis` — an admitted explanatory or predictive candidate.
- `Decision` — an admitted recommendation or rationale record.
- `ReportFragment` — a reusable admitted text fragment such as a methods paragraph.

### 2.3 NodeKind

`NodeKind` remains an extensible newtype rather than an enum.

```rust
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct NodeKind(String);

impl NodeKind {
    pub fn new(s: &str) -> Result<Self, ValidationError> {
        // snake_case, lowercase, 1..=64 chars
    }
}
```

Examples:

- `paper`
- `notebook_snapshot`
- `extracted_measurement`
- `simulation_run`
- `threshold_estimate`
- `analysis_claim`
- `report_methods_fragment`

The important distinction is:

- `class` determines system behavior;
- `kind` determines domain meaning.

### 2.4 Confidence

```rust
pub struct Confidence {
    pub level: ConfidenceLevel,
    pub rationale: String,
    pub basis: Vec<EvidenceBasis>,
    pub assumptions: Vec<Assumption>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum ConfidenceLevel {
    Speculative = 0,
    Low = 1,
    Moderate = 2,
    High = 3,
}
```

**`Verified` is intentionally removed from `ConfidenceLevel`.**

That earlier design overloaded two different ideas:

- “we are epistemically confident in this claim,” and
- “this claim went through adversarial review.”

A claim can be adversarially verified **and still only moderate confidence** because the evidence base is thin or conditional.

### 2.5 VerificationRecord

```rust
pub struct VerificationRecord {
    pub requirement: VerificationRequirement,
    pub status: VerificationStatus,
    pub metadata: Option<VerificationMetadata>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum VerificationRequirement {
    NotRequired,
    Required,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum VerificationStatus {
    NotRequired,
    Verified,
    VerifiedWithCaveats,
    Challenged,
    Outdated,
}
```

Interpretation:

- `NotRequired` — applies to artifacts, observations, and raw runs by default.
- `Verified` — passed admission with no unresolved issues.
- `VerifiedWithCaveats` — admitted but caveats remain visible.
- `Challenged` — globally visible only if a human promoted the claim provisionally.
- `Outdated` — was once verified, but upstream change requires re-verification.

### 2.6 AdmissionStatus

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AdmissionStatus {
    Accepted,
    Provisional,
}
```

Most nodes are `Accepted`. `Provisional` exists for the important but exceptional case where a human intentionally promotes a challenged draft into the graph. This is allowed, but it is explicit and queryable.

### 2.7 VerificationMetadata

```rust
pub struct VerificationMetadata {
    pub passed: bool,
    pub iterations: u32,
    pub issues: Vec<VerificationIssueRecord>,
    pub objections_resolved: Vec<String>,
    pub remaining_caveats: Vec<String>,
    pub verified_at: Timestamp,
    pub generator_model: Option<String>,
    pub verifier_model: Option<String>,
    pub reviser_model: Option<String>,
    pub independence_policy: String,
}
```

This revision expands provenance slightly so that later audits can answer not only “was it verified?” but also “under what independence policy and with which model stack?”

### 2.8 References and Locators

The earlier draft’s `Reference` enum is extended with locators because evidence-first memory without fine-grained location quickly degrades into citation theater.

```rust
pub struct Reference {
    pub source: ReferenceSource,
    pub locator: Option<SourceLocator>,
    pub excerpt_hash: Option<String>,
}

pub enum ReferenceSource {
    Artifact { artifact_id: Ulid },
    Node { id: Ulid },
    Url { url: String, accessed_at: Timestamp },
    Run { run_id: String, backend: String },
    Literature { citation_key: String },
    User { name: String, note: Option<String> },
}

pub enum SourceLocator {
    Document {
        page: Option<u32>,
        section: Option<String>,
        span: Option<String>,
    },
    Code {
        repo: String,
        commit: String,
        path: String,
        line_start: Option<u32>,
        line_end: Option<u32>,
    },
    Dataset {
        table: Option<String>,
        row: Option<String>,
        column: Option<String>,
    },
    NotebookCell {
        notebook_id: String,
        cell_id: String,
    },
    Figure {
        label: String,
    },
    Other(String),
}
```

### 2.9 Actor

```rust
pub enum Actor {
    User { name: String },
    LemSession { investigation_id: Ulid, phase: String },
    BackendRun { run_id: String, backend: String },
    Import { source: String },
    System { component: String },
}
```

### 2.10 NodeStatus

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NodeStatus {
    Active,
    Stale,
    Invalidated,
    Superseded,
}
```

Status remains a lifecycle/freshness field. It is deliberately not used for verification or admission semantics.

---

## 3. Identity Model

The original draft used a single `content_hash` field for multiple jobs. This revision separates two different identities.

### 3.1 ExactHash

`ExactHash` answers:

> Is this artifact or run result byte-equivalent to one we already have?

It is appropriate for:

- artifact snapshots;
- exact result files;
- backend run payloads;
- imported structured records where identity really is exact content.

```rust
pub struct ExactHash(String); // hex-encoded blake3
```

### 3.2 SemanticKey

`SemanticKey` answers:

> Is this node the current answer to the same scientific question as another node?

It is appropriate for canonicalized claim-like nodes such as:

- a current best threshold estimate for a named setup;
- a current recommendation record for a given decision scope;
- a current methods fragment keyed to a specific experiment configuration.

```rust
pub struct SemanticKey(String); // canonical key material, then hashed
```

### 3.3 Why the Distinction Matters

A raw run and a canonical estimate are not the same thing.

Bad behavior in the earlier design:

- a new simulation with more samples could automatically supersede an older run record;
- this risked hiding raw empirical history behind semantic deduplication.

Revised behavior:

- **run records are immutable observations** and dedupe only by exact identity;
- **canonical claim nodes** may supersede one another by semantic key.

That preserves empirical history and still allows “current best answer” nodes to stay tidy.

### 3.4 Example Semantic Key Policy

A domain pack can define semantic keys for eligible `Claim`, `Hypothesis`, `Decision`, or `ReportFragment` nodes.

For example:

```rust
// threshold_estimate claim key
{
    "kind": "threshold_estimate",
    "architecture": "...",
    "noise_model": "...",
    "decoder_family": "...",
    "parameter_regime": "..."
}
```

A `simulation_run` node would **not** use that same semantic key. It would have an exact hash and a run ID, but no supersession semantics.

---

## 4. Edge Model

### 4.1 Edge

```rust
pub struct Edge {
    pub id: Ulid,
    pub source: Ulid,
    pub target: Ulid,
    pub kind: EdgeKind,
    pub metadata: Option<serde_json::Value>,
    pub created_at: Timestamp,
    pub created_by: Actor,
}
```

### 4.2 EdgeKind

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EdgeKind {
    DependsOn,
    DerivedFrom,
    Supersedes,
    Contradicts,
}
```

The earlier minimal edge set is retained because it is sufficient if used carefully:

- `DependsOn` — argumentative or evidentiary dependence;
- `DerivedFrom` — computational or transformation lineage;
- `Supersedes` — newer canonical answer replacing older canonical answer;
- `Contradicts` — incompatibility requiring explicit attention.

### 4.3 Invariants

1. `DependsOn` and `DerivedFrom` must not create cycles.
2. `Supersedes` is only allowed between nodes with compatible `class` and identical `kind`.
3. `Contradicts` is stored as directed but treated as symmetric in queries.
4. Duplicate edges are forbidden.
5. A node may not edge to itself.

### 4.4 Why `supports` Was Not Added

A tempting extension is a dedicated `Supports` edge. This revision declines to add it because:

- `DependsOn` already captures the propagation semantics needed for “this claim relies on this evidence”;
- introducing both often causes teams to split semantically similar links inconsistently;
- additional edge kinds should be added only when they produce distinct behavior, not just nicer language.

---

## 5. Storage Schema

### 5.1 Tables

```sql
CREATE TABLE nodes (
    id                    TEXT PRIMARY KEY,
    class                 TEXT NOT NULL,
    kind                  TEXT NOT NULL,
    summary               TEXT NOT NULL,
    confidence_json       TEXT NOT NULL,
    verification_requirement TEXT NOT NULL,
    verification_status   TEXT NOT NULL,
    verification_json     TEXT,
    admission_status      TEXT NOT NULL,
    payload               TEXT,
    references_json       TEXT NOT NULL,
    created_at            TEXT NOT NULL,
    created_by_json       TEXT NOT NULL,
    status                TEXT NOT NULL,
    exact_hash            TEXT,
    semantic_key          TEXT,
    updated_at            TEXT NOT NULL
);

CREATE INDEX idx_nodes_class ON nodes(class);
CREATE INDEX idx_nodes_kind ON nodes(kind);
CREATE INDEX idx_nodes_status ON nodes(status);
CREATE INDEX idx_nodes_verification_status ON nodes(verification_status);
CREATE INDEX idx_nodes_admission_status ON nodes(admission_status);
CREATE INDEX idx_nodes_exact_hash ON nodes(exact_hash) WHERE exact_hash IS NOT NULL;
CREATE INDEX idx_nodes_semantic_key ON nodes(semantic_key) WHERE semantic_key IS NOT NULL;

CREATE TABLE edges (
    id           TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    target       TEXT NOT NULL,
    kind         TEXT NOT NULL,
    metadata     TEXT,
    created_at   TEXT NOT NULL,
    created_by   TEXT NOT NULL,
    UNIQUE(source, target, kind)
);

CREATE INDEX idx_edges_source ON edges(source);
CREATE INDEX idx_edges_target ON edges(target);
CREATE INDEX idx_edges_kind ON edges(kind);

CREATE TABLE assumptions (
    id           TEXT PRIMARY KEY,
    node_id       TEXT NOT NULL,
    description  TEXT NOT NULL,
    status       TEXT NOT NULL,
    source_json  TEXT
);

CREATE INDEX idx_assumptions_node ON assumptions(node_id);
CREATE INDEX idx_assumptions_status ON assumptions(status);

CREATE TABLE events (
    id               TEXT PRIMARY KEY,
    timestamp        TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    target_id        TEXT NOT NULL,
    target_type      TEXT NOT NULL,
    actor_json       TEXT NOT NULL,
    before_json      TEXT,
    after_json       TEXT NOT NULL,
    investigation_id TEXT
);

CREATE INDEX idx_events_target ON events(target_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);

CREATE VIRTUAL TABLE nodes_fts USING fts5(
    summary,
    content='nodes',
    content_rowid='rowid'
);
```

### 5.2 Query-Friendly Columns vs JSON

Compared with the earlier draft, this schema deliberately pulls more fields into first-class columns:

- `class`
- `verification_requirement`
- `verification_status`
- `admission_status`
- `exact_hash`
- `semantic_key`

These fields are queried often enough that keeping them only inside JSON would make filtering clumsy and brittle.

### 5.3 Workspace Is Stored Separately

The investigation workspace is persisted, but it is not part of the graph schema proper. It belongs in `investigations` and related tables, not in `nodes`.

This keeps global research memory and investigation-local memory separate both conceptually and physically.

---

## 6. Admission and Mutation APIs

### 6.1 Graph Lifecycle

```rust
pub struct Graph {
    conn: rusqlite::Connection,
}

impl Graph {
    pub fn open(path: &Path) -> Result<Self, GraphError>;
    pub fn open_memory() -> Result<Self, GraphError>;
}
```

### 6.2 Creation APIs by Semantics

The revised API surface is more explicit about semantic intent:

```rust
impl Graph {
    pub fn create_artifact(&mut self, req: CreateArtifactRequest) -> Result<Node, GraphError>;
    pub fn create_observation(&mut self, req: CreateObservationRequest) -> Result<Node, GraphError>;
    pub fn create_run_record(&mut self, req: CreateRunRecordRequest) -> Result<Node, GraphError>;
    pub fn admit_synthesis(&mut self, req: AdmitSynthesisRequest) -> Result<Node, GraphError>;
    pub fn promote_provisional(&mut self, req: PromoteProvisionalRequest) -> Result<Node, GraphError>;
}
```

The earlier generic `create_node` is flexible but too permissive for the architecture this system wants. A graph API that does not encode the semantic differences between observations, runs, and admitted syntheses invites misuse.

### 6.3 Admission Request

```rust
pub struct AdmitSynthesisRequest {
    pub class: RecordClass,                // Claim, Hypothesis, Decision, ReportFragment
    pub kind: NodeKind,
    pub summary: String,
    pub payload: Option<serde_json::Value>,
    pub confidence: Confidence,
    pub references: Vec<Reference>,
    pub supporting_nodes: Vec<Ulid>,
    pub verification: VerificationMetadata,
    pub semantic_key: Option<SemanticKey>,
    pub actor: Actor,
}
```

`admit_synthesis` performs atomically:

- node creation;
- verification record attachment;
- dependency edge creation;
- event logging;
- optional supersession if a prior accepted node shares the same semantic key and policy allows replacement.

### 6.4 Provisional Promotion

```rust
pub struct PromoteProvisionalRequest {
    pub kind: NodeKind,
    pub class: RecordClass,
    pub summary: String,
    pub confidence: Confidence,
    pub references: Vec<Reference>,
    pub verification: VerificationMetadata,
    pub justification: String,
    pub actor: Actor,
}
```

This is intentionally explicit. Human override should feel different from routine admission.

---

## 7. Propagation and Re-verification

### 7.1 Propagation Triggers

Propagation runs when:

1. node status changes to `Stale` or `Invalidated`;
2. confidence level decreases;
3. an assumption becomes `Questioned` or `Invalidated`;
4. a `Supersedes` edge changes which canonical answer should be considered current.

### 7.2 Propagation Rule

Propagation follows only `DependsOn` and `DerivedFrom` edges.

For each downstream node reached:

- if `status == Active`, set `status = Stale`;
- if `verification.requirement == Required` and `verification.status` is `Verified` or `VerifiedWithCaveats`, set `verification.status = Outdated`;
- emit events for each mutation.

### 7.3 Formal Guarantees

Because `DependsOn` and `DerivedFrom` form a DAG:

- propagation terminates;
- propagation is idempotent;
- propagation is bounded to the reachable dependency subgraph;
- propagation can run atomically within a transaction.

### 7.4 Why `Outdated` Matters

Without `Outdated`, the UI and downstream logic only know that a node is stale. That misses a key epistemic distinction:

- a node can be stale because one supporting detail changed; or
- a node can be stale *and* its prior adversarial check is no longer current.

`Outdated` is the latter. It is the signal that re-verification, not merely rereading, is required.

### 7.5 Supersession Behavior

Supersession should only be used for nodes meant to represent a current canonical answer.

When `A supersedes B`:

- `B.status = Superseded`;
- dependents are *not* silently rewired destructively;
- new dependency edges may be added from dependents to `A` if policy calls for it;
- downstream nodes are marked stale/outdated because their canonical support changed.

The original draft preserved old edges for history. This revision keeps that behavior.

---

## 8. Query API

### 8.1 Filters

```rust
pub struct NodeFilter {
    pub classes: Option<Vec<RecordClass>>,
    pub kinds: Option<Vec<NodeKind>>,
    pub statuses: Option<Vec<NodeStatus>>,
    pub admission: Option<Vec<AdmissionStatus>>,
    pub verification_status: Option<Vec<VerificationStatus>>,
    pub min_confidence: Option<ConfidenceLevel>,
    pub semantic_key: Option<SemanticKey>,
    pub limit: Option<usize>,
    pub offset: Option<usize>,
    pub order_by: OrderBy,
}
```

### 8.2 Queries That Matter Operationally

The graph must support questions such as:

- show all active admitted claims on a topic;
- show all provisional nodes;
- show all verified-with-caveats nodes;
- show all outdated decisions caused by a changed run result;
- find all current canonical answers for a semantic key family;
- trace why a claim is stale.

### 8.3 Dependency Trace

```rust
pub struct DependencyTrace {
    pub root: Ulid,
    pub nodes: Vec<Node>,
    pub edges: Vec<Edge>,
    pub truncated: bool,
}
```

This remains a core affordance because the graph’s value is not just storage but explanation.

---

## 9. Event Log

### 9.1 Event Types

```rust
pub enum EventType {
    NodeCreated,
    SynthesisAdmitted,
    NodeProvisionallyPromoted,
    NodeStatusChanged,
    NodeConfidenceChanged,
    NodeVerificationChanged,
    NodeMarkedOutdated,
    EdgeCreated,
    EdgeRemoved,
    PropagationTriggered,
    AssumptionStatusChanged,
}
```

### 9.2 Guarantees

Every mutation path inserts its event in the same transaction as the mutation. No graph change should exist without a corresponding event.

### 9.3 Reconstruction

Because events contain `before_json` and `after_json`, the graph can reconstruct:

- when a claim was first admitted;
- what caveats it had then;
- when it became outdated;
- what upstream change triggered the stale state;
- whether it was ever provisional.

---

## 10. Error Handling and Invariants

### 10.1 Error Types

Representative errors include:

```rust
#[derive(Debug, thiserror::Error)]
pub enum GraphError {
    #[error("node not found: {0}")]
    NodeNotFound(Ulid),

    #[error("cycle detected: {source} -> {target}")]
    CycleDetected { source: Ulid, target: Ulid },

    #[error("duplicate edge: {source} -> {target} ({kind:?})")]
    DuplicateEdge { source: Ulid, target: Ulid, kind: EdgeKind },

    #[error("invalid supersession: class or kind mismatch")]
    InvalidSupersession,

    #[error("provisional promotion requires explicit justification")]
    MissingProvisionalJustification,

    #[error("verification metadata inconsistent with admission request")]
    InvalidVerificationState,

    #[error("database error: {0}")]
    Database(#[from] rusqlite::Error),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}
```

### 10.2 Invariants Worth Enforcing in Code

- `Claim`, `Hypothesis`, `Decision`, and `ReportFragment` nodes must not be created with `VerificationRequirement::NotRequired`.
- `Artifact`, `Observation`, and `Run` nodes default to `VerificationRequirement::NotRequired`.
- `AdmissionStatus::Provisional` requires `VerificationStatus::Challenged`.
- `VerificationStatus::Outdated` is only valid when `VerificationRequirement::Required`.
- `semantic_key`-driven supersession is only allowed for eligible classes.
- `Run` nodes are never auto-superseded by semantic key.

---

## 11. Testing Strategy

### 11.1 Unit Tests

- creation by record class;
- verification/admission invariants;
- exact-hash deduplication;
- semantic-key supersession for canonical claims only;
- propagation and outdated-verification marking;
- provisional promotion behavior;
- query filters and FTS;
- event completeness.

### 11.2 Property Tests

- propagation terminates on random DAGs;
- `Outdated` only appears on required-verification nodes;
- exact-hash identity is deterministic;
- semantic-key supersession never targets `Run` class nodes.

### 11.3 Scenario Tests

- updated run result makes a verified claim stale and outdated;
- challenged draft promoted provisionally stays queryable as provisional;
- two exact-duplicate artifacts collapse while two distinct runs with same scientific target do not;
- semantic-key replacement preserves full historical chain.

---

## 12. Summary

The revised evidence-graph design sharpens the system into something safer and more reusable.

Three design decisions matter most:

1. **global memory stores admitted research memory, not every draft;**
2. **verification is separate from confidence and freshness;**
3. **raw empirical history and canonical synthesized answers use different identity rules.**

Those changes make the graph a better scientific memory substrate for Lem and for the broader Zetetic Works research environment.
