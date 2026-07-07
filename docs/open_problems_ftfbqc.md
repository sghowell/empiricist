# Ten Open Problems in Fault-Tolerant Fusion-Based Quantum Computation, Selected for Machine-Assisted Proof and Discovery

**Working draft, v1. June 9, 2026.**

## Abstract

We compile ten problems in the theory of fault-tolerant fusion-based quantum computation (FBQC) that are, to the best of our knowledge, open as of June 9, 2026, and that we judge unusually well suited to attack by current frontier AI systems: each has a finite combinatorial or algebraic core, admits machine-checkable certificates, and supports a search-then-prove workflow. For each problem we give a complete formal statement, summarize the known partial results, explain why it remains open, sketch the most plausible machine-assisted attack, and assess the feasibility of formalization in Lean 4 (a bonus criterion, not a requirement). The problems span: a rigorous threshold theorem for fusion networks; exact erasure thresholds and their percolation correspondences; optimality of ancilla-boosted linear-optical fusion; the loss-tolerance frontier of ballistic architectures; minimum-fusion synthesis of graph states; proof complexity and confluence of ZX rewriting; a ZX-native fault-tolerance theorem; constant-overhead FBQC from quantum LDPC codes; closing the gap between rigorous and numerical fault-tolerance thresholds for concatenated schemes; and distillation-free universality in fusion networks.

---

## 1. Introduction

Fusion-based quantum computation [1] builds fault tolerance from two primitives: constant-size entangled resource states, and destructive two-qubit entangling measurements (fusions) performed between qubits of different resource states. Probabilistic fusion outcomes, photon loss, and Pauli noise are absorbed directly into the decoding problem rather than handled by repeat-until-success gadgetry. The model now has a substantial theory: a stabilizer formalism with check groups and fusion networks [1], topological instantiations with numerically estimated thresholds [1, 8, 9], encoded and boosted fusions [10, 11, 12], modular and interleaved architectures [13], a unifying ZX-calculus picture of fault tolerance in which FBQC, circuit-based, measurement-based, and Floquet schemes are rewrites of one another [14], and a manufacturable photonic platform [15].

Almost all of this theory is, in the mathematician's sense, unproven. Thresholds are Monte Carlo estimates. The correspondences between fusion networks and statistical-mechanics models are exact in formulation but their critical points are not rigorously located. Optimality claims about linear-optical primitives are verified numerically over restricted ansatz families. This document collects the gaps that we believe are (a) genuinely open, (b) precisely statable, and (c) matched to the current capabilities of AI systems for mathematics: large-scale certified enumeration (in the lineage of SAT-based results such as the Boolean Pythagorean triples theorem and Keller's conjecture in dimension seven), search-then-conjecture-then-prove pipelines for extremal combinatorics (FunSearch, AlphaEvolve), automated rewriting and completion (the Robbins conjecture tradition), olympiad-grade formal proof search (AlphaProof, AlphaGeometry), and LLM-driven Lean 4 formalization on top of mathlib.

**Selection criteria.** Each problem was screened against four criteria.

- **C1 (Open).** No solution or proof is published as of June 9, 2026, to the best of our ability to verify by literature search. Section 5 records the verification caveats; several adjacent problems were excluded because they were recently closed (Section 5.2).
- **C2 (Rigorously statable).** The problem statement below is intended to be complete: a solver should not need to consult this document's authors to know what counts as a solution.
- **C3 (AI attack surface).** There is a credible route in which a current frontier system contributes the decisive step: a certified enumeration, an extremal construction, a dual certificate, a counterexample search, or a formal proof of a finite case analysis.
- **C4 (Formalization, bonus).** Where realistic, we note a path to Lean 4 formalization. Per the brief for this document, C4 never overrides C3: several problems below would be painful to formalize today and are included anyway.

Problems with a ZX-calculus, fusion-network, resource-state, concatenated-code, or non-surface-code character were preferred where this did not conflict with C3.

**Notation.** $[n] = \{1,\dots,n\}$. Pauli group $\mathcal{P}_n$. Graph state $|G\rangle$ for a simple graph $G=(V,E)$: the unique state stabilized by $\{X_v \prod_{u \in N(v)} Z_u\}_{v \in V}$. LC denotes local Clifford equivalence. All logarithms base 2.

---

## 2. The model

### 2.1 Fusion networks and the standard noise model

**Definition 2.1 (Fusion network).** A *fusion network* is a tuple $\mathrm{FN} = (V, \{|R_v\rangle\}_{v\in V}, F)$ where each $v \in V$ carries an $n_v$-qubit stabilizer resource state $|R_v\rangle$ with stabilizer group $S_v$; the qubit set is $Q = \bigsqcup_v Q_v$; and $F$ is a partition of a subset $Q_F \subseteq Q$ into *fusions*, unordered pairs $f = \{q, q'\}$ with $q, q'$ in distinct resource states. Performing fusion $f$ means destructively measuring the commuting pair $M_f = \{X_q X_{q'},\, Z_q Z_{q'}\}$ (a Bell-basis measurement). Qubits in $Q \setminus Q_F$ are ports (logical interface) or are measured in fixed single-qubit bases.

Let $\mathcal{M} = \langle \bigcup_f M_f \rangle$ be the group generated by the fusion observables. The *check group* is $C(\mathrm{FN}) = \big(\prod_v S_v\big) \cap \mathcal{M}$: products of resource-state stabilizers that are simultaneously products of fusion observables. Each element of $C$ imposes a deterministic parity on the corresponding subset of fusion outcome bits; these parities are the checks of the decoding problem. Logical information is carried by *correlation operators*, elements of $\prod_v S_v$ supported on ports after multiplication by elements of $\mathcal{M}$. For the topological networks below, the checks organize into two chain complexes (primal and dual *syndrome graphs*), each fusion contributing one outcome bit (one edge) to each. See [1] for the full construction; nothing below requires more than this interface.

**Definition 2.2 (Standard fusion noise model $\mathrm{NM}(p_E, p_F, p_P)$).** Independently for each fusion: with probability $p_E$ both outcome bits are erased (full erasure: photon loss); with probability $p_F$ the $X\!\otimes\!X$ bit is erased and the $Z\!\otimes\!Z$ bit is retained (heralded fusion failure; the failure basis is a design choice and may be randomized or biased [1, 8]); each retained bit is independently flipped with probability $p_P$. All erasures are heralded.

This is the hardware-agnostic model of [1]. The linear-optical instantiation maps an unboosted dual-rail Bell measurement to $p_F = 1/2$, boosting with a Bell pair to $p_F = 1/4$ [10], and per-photon loss $\eta$ to fusion erasure $p_E = 1 - (1-\eta)^{c}$ with $c$ the photon count entering the fusion.

**Definition 2.3 (Memory experiment, threshold).** Fix a one-parameter family $\mathrm{FN}_L$ (for instance $L \times L \times L$ blocks of the 6-ring network of [1]) encoding one logical qubit with fault distance $d(\mathrm{FN}_L) = \Theta(L)$, together with a decoder family $\mathcal{D}_L$. The logical error probability is $P_L(p_E, p_F, p_P)$. A point $(p_E,p_F,p_P)$ is *correctable* (for the family and decoder) if $P_L \to 0$; the *threshold surface* is the boundary of the correctable region; the scheme has a *threshold* if the correctable region contains a neighborhood of the origin intersected with the positive octant.

**The 6-ring network $\mathrm{FN}_6$.** Resource states are 6-qubit ring graph states; fusions tile them into a structure whose primal and dual syndrome graphs are those of a 3D cell complex of Raussendorf-Harrington-Goyal type [1, 16]. Numerically estimated thresholds for $\mathrm{FN}_6$ [1]: $p_E^{\mathrm{th}} \approx 11.98\%$ per fusion (with $p_F = p_P = 0$), $p_P^{\mathrm{th}} \approx 1.07\%$ (with $p_E = p_F = 0$), marginal fusion-failure threshold $43.2\%$ with (2,2)-Shor encoded fusions, and, in the linear-optical model, $10.4\%$ loss per fusion ($2.7\%$ per photon) with boosted fusions. Tailored variants reach failure thresholds above $25\%$ at nonzero loss [8], and generalized-Shor encoded fusions reach $13.97\%$ loss per photon numerically [11]. **Every number in this paragraph is a Monte Carlo estimate.**

### 2.2 ZX preliminaries

We use the ZX-calculus in its standard presentation (spiders, Hadamards; soundness and completeness results [20, 21, 22]), extended by classical outputs to represent quantum instruments, and the Pauli-web formalism for fault tolerance [14]: a *Pauli web* is an assignment of Pauli labels to a subset of edges of a Clifford ZX diagram consistent at every spider (even own-color legs, all-or-none opposite-color legs, with the $\pm\pi/2$ refinements); *detecting regions* are closed webs whose outcome parities are deterministic; faults are Pauli assignments to edges; the *fault distance* is the minimum weight of an undetectable fault acting nontrivially on the logical class. Sign conventions and the fault-equivalence relation follow [23]. Fusion networks, stabilizer circuits, MBQC patterns, and Floquet codes are all instances [14].

---

## 3. The problems

For each problem: **Status: open** means we could not locate a published solution as of June 9, 2026 (see Section 5 for the verification protocol and its limits).

---

### Problem 1. A threshold theorem for fusion networks

**Setting.** $\mathrm{FN}_6$ memory experiment (Definitions 2.1 to 2.3), noise $\mathrm{NM}(p_E, p_F, p_P)$, $T = L$ rounds.

> **Problem 1.**
> **(i) Existence.** Prove that there exist a polynomial-time decoder family $\mathcal{D}_L$ and constants $p^* > 0$, $c > 0$, $L_0$ such that for all $(p_E, p_F, p_P)$ with $p_E + p_F + p_P < p^*$ and all $L \ge L_0$, the logical error probability of the $\mathrm{FN}_6$ memory experiment under $\mathrm{NM}(p_E,p_F,p_P)$ satisfies $P_L \le e^{-cL}$.
> **(ii) Quantitative.** Exhibit a machine-checkable certificate proving that the correctable region contains the point $(p_E, p_F, p_P) = (0.04,\, 0,\, 0.003)$, that is, within a factor of three of the numerical estimates $(0.1198, \cdot, 0.0107)$ of [1].

**Known results.** Rigorous threshold theorems exist for concatenated circuit-model schemes [24, 25], for the surface code under independent Pauli noise via Peierls-type counting [26], for maximum-likelihood erasure decoding of 2D surface codes (exactly: threshold $= 1/2$) [27], and for cluster-state MBQC under local noise models that do not include loss or heralded gate failure [28, 29]. None of these covers $\mathrm{NM}$: heralded fusion failure erases one of the two outcome bits of a fusion (an anisotropic erasure correlated between the primal and dual syndrome graphs), full fusion erasure removes one edge from each graph simultaneously, and Pauli noise flips retained bits. All published FBQC threshold values [1, 8, 9, 11] are Monte Carlo estimates. We are not aware of any published rigorous threshold theorem for the FBQC noise model.

**Why open.** Part (i) requires a Peierls/self-avoiding-walk counting argument over connected fault clusters in a 3D cell complex carrying two coupled syndrome graphs, combined with a peeling or union-find analysis for the erasure component; the pieces exist separately, the assembly does not. Part (ii) is where the difficulty concentrates: naive union bounds land one to two orders of magnitude below the Monte Carlo values, and closing the constant-factor gap requires optimizing the counting (cluster decompositions, weighted enumeration of lattice animals on the explicit $\mathrm{FN}_6$ complex).

**AI attack surface.** The proof of (i) is generative but formulaic once the right cluster decomposition is fixed; an LLM-plus-verifier loop targeting a fully explicit counting proof is realistic. Part (ii) is a certificate-generation problem: enumerate (with symmetry reduction) connected subgraphs of the $\mathrm{FN}_6$ syndrome complex up to a cut-off size, bound the tail analytically, and emit a proof object. The precedent is the computer-assisted combinatorial analysis already used for circuit-model bounds [24].

**Formalization.** Medium. Requires finite graph combinatorics, union bounds, and geometric series; all available in mathlib. The main cost is encoding the $\mathrm{FN}_6$ complex; once encoded, Problem 2 reuses it.

**Status: open.**

---

### Problem 2. Exact erasure thresholds and the percolation correspondence

**Setting.** Erasure-only noise ($p_F = p_P = 0$), maximum-likelihood (ML) decoding. Define $T_E(\mathrm{FN}) = \sup\{p_E : P_L^{\mathrm{ML}} \to 0\}$.

> **Problem 2.**
> **(i) Correspondence.** Prove that $T_E(\mathrm{FN}_6)$ equals the critical probability of an explicit boundary-crossing bond-percolation process on the $\mathrm{FN}_6$ primal syndrome graph, in exact analogy with the 2D theorem $T_E(\text{surface code}) = p_c(\text{bond}, \mathbb{Z}^2) = 1/2$ [27, 30].
> **(ii) Value.** Determine $T_E(\mathrm{FN}_6)$ in closed form, or produce rigorously certified bounds $a \le T_E(\mathrm{FN}_6) \le b$ with $b - a \le 0.01$ bracketing the Monte Carlo estimate $0.1198$ [1].

**Known results.** For erasures, ML decoding fails if and only if the erased set supports a representative of a logical operator; this reduces (i) to a percolation crossing statement, proven in 2D via planar duality and Kesten's theorem [27, 30]. In 3D no exact percolation threshold is known for any standard lattice (the cubic bond value $\approx 0.2488$ is numerical), planar duality is unavailable, and the best rigorous bounds for 3D thresholds remain crude relative to numerics. Elementary comparisons (branching-process upper bounds on connectivity; embedded 2D slabs) give rigorous but loose two-sided bounds.

**Why open.** Part (i) likely yields to known techniques but has not been written for the FBQC complexes, where the relevant homology is of a 3-complex with boundary and the failure event is a relative-cycle crossing. Part (ii) inherits the central open problem of 3D percolation: locating critical points rigorously.

**AI attack surface.** Certified bounds via lattice-animal enumeration, the substitution method, or coupling arguments are certificate problems: enormous, mechanical enumerations with trivially checkable outputs. This is exactly the regime where SAT-style and Lean-verified mass case analysis has already delivered results out of human reach. Improving the rigorous window around a 3D critical point, on a lattice that quantum computing actually cares about, is a well-scoped target with a clear success metric.

**Formalization.** Low to medium. Full percolation theory in Lean is heavy; the enumerative certificates (finite counting plus a verified tail bound) are not.

**Status: open.** (Both parts; (i) plausibly nearer than (ii).)

---

### Problem 3. Optimality of ancilla-boosted linear-optical fusion

**Setting.** Dual-rail photonic qubits. A *Bell-measurement scheme with $k$ ancilla photons* is a tuple $(m, U, |A\rangle, f)$: $m$ optical modes; a passive linear interferometer $U \in \mathrm{U}(m)$; an ancilla state $|A\rangle$ of exactly $k$ photons on modes $5,\dots,m$ (arbitrary, possibly entangled); photon-number-resolving detection on all output modes; an assignment $f$ from detection patterns $\mathbf{n} \in \mathbb{N}^m$ to $\{\Phi^+, \Phi^-, \Psi^+, \Psi^-, \perp\}$. The scheme is *unambiguous* if $\Pr[\mathbf{n} \mid B] > 0$ and $f(\mathbf{n}) = B' \ne \perp$ imply $B' = B$ for all Bell states $B$. Its success probability is $p = \min_B \sum_{\mathbf{n}: f(\mathbf{n}) = B} \Pr[\mathbf{n} \mid B]$. Define
$$p^*(k) = \sup \{ p : \text{unambiguous schemes with } k \text{ ancilla photons} \}.$$

> **Problem 3.**
> **(i)** Determine $p^*(1)$. (Conjecture: $p^*(1) = 1/2$, i.e., a single ancilla photon is useless.)
> **(ii)** Prove or refute $p^*(2) = 3/4$, with the supremum over all passive interferometers and all two-photon ancilla states, not only polarization- or rail-structure-preserving ones.
> **(iii)** Determine the asymptotics of $1 - p^*(k)$. Known constructions give $1 - p^*(k) \le 1/(k+2)$ along $k = 2^N - 2$ [31]. Decide whether $1 - p^*(k) = e^{-\Theta(k)}$ is achievable, or prove a lower bound $1 - p^*(k) = \Omega(1/\mathrm{poly}(k))$.
> **(iv)** Prove a computable a priori bound $m \le g(k)$ on the number of modes that suffices to achieve $p^*(k)$ to within any $\epsilon$, thereby rendering each $p^*(k)$ computable in principle.

**Known results.** $p^*(0) = 1/2$ exactly [32]. No perfect linear-optical Bell measurement exists, even with arbitrary ancillas, photon-number resolution, and conditional dynamics [33, 34]; hence $p^*(k) < 1$ for all $k$. Grice: $p^*(2) \ge 3/4$ with a Bell-pair ancilla, and $p^*(2^N - 2) \ge 1 - 2^{-N}$ [31]. Ewert and van Loock: $3/4$ with four unentangled single photons [35]. Optimality of these schemes is proven only within the restricted class of polarization-preserving interferometers [36]; outside that class only numerical evidence exists, including evidence that one ancilla photon does not help [36, 37]. Experiment: $57.9\%$ measured, $5/8$ theoretical for the implemented scheme [37]. Squeezing-assisted variants exceed $1/2$ by other means [38].

**FBQC relevance.** $p_F = 1 - p^*$ enters every loss and failure budget in Section 2; the (2,2)-Shor 6-ring tolerates marginal $p_F \le 43.2\%$, but the photon cost of boosting (hence the loss exponent $c$ in $p_E = 1-(1-\eta)^c$) is governed by exactly the tradeoff that $p^*(k)$ quantifies.

**AI attack surface.** For fixed small $(k, m)$ the optimization is finite-dimensional and semialgebraic: the unambiguity constraints are polynomial identities in the entries of $U$ and the ancilla amplitudes, and the objective is polynomial. Sum-of-squares / SDP relaxations give dual certificates, that is, machine-checkable upper bounds on $p^*(k)$; symmetry reduction (mode permutations, phase gauge) makes moderate sizes feasible. This is one of the cleanest "find a certificate a human has not found" targets in quantum information. Part (iv) is the structural lemma that would convert the numerics of [36] into theorems.

**Formalization.** Medium to high for certificates: an exact rational SOS certificate verifies in Lean by linear algebra over $\mathbb{Q}$. The analytic reduction in (iv) is conventional functional analysis.

**Status: open.** (All parts; (ii) is the headline.)

---

### Problem 4. The loss-tolerance frontier of ballistic FBQC

**Setting.** Linear-optical FBQC, ballistic class $\mathcal{B}_n$: resource states drawn from a finite library of states on at most $n$ dual-rail photons each (encoded-fusion photons counted against $n$); a static fusion layout (no adaptive interferometer reconfiguration; classical information flows only into the decoder); photon-number-resolving detection; independent loss $\eta$ per photon, applied to every photon between preparation and detection; otherwise ideal operations. Let
$$\lambda^*(n) = \sup\{\eta : \text{some scheme in } \mathcal{B}_n \text{ has } P_L \to 0 \text{ at per-photon loss } \eta\}.$$

> **Problem 4.**
> **(i)** Prove $\lambda^*(n) < 1/2$ with an explicit gap $1/2 - \lambda^*(n) \ge f(n) > 0$ for every finite $n$, or prove $\lim_{n \to \infty} \lambda^*(n) = 1/2$ within the ballistic class.
> **(ii)** Determine the rate: find $f$ with $1/2 - \lambda^*(n) = \Theta(f(n))$.
> **(iii)** Certified achievability: prove (not estimate) $\lambda^*(n_0) \ge 0.05$ for an explicit $n_0$.

**Known results.** $\eta \ge 1/2$ is unconditionally fatal for any architecture: at $50\%$ loss the environment receives as much amplitude as the computer, and tolerance would violate no-cloning (equivalently, the erasure channel at $\eta = 1/2$ has zero quantum capacity). Adaptive measurement-based protocols with tree codes tolerate $\eta \to 1/2$ as the tree size diverges [39], but they are adaptive and outside $\mathcal{B}_n$. Inside the FBQC class, the best published values are Monte Carlo: $2.7\%$ per photon (boosted, 6-ring) [1] and $13.97\%$ per photon (generalized-Shor encoded fusion) [11], with no rigorous achievability statement and no nontrivial upper bound $\lambda^*(n) \le 1/2 - f(n)$ known for any finite $n$.

**Why open.** Upper bounds require localizing an information-theoretic argument to finite gadgets under heralded loss, which no one has done quantitatively; lower bounds require Problem-1-style machinery applied to encoded-fusion networks.

**AI attack surface.** Two-sided. Upper bounds: adversary-strategy search over finite fusion gadgets, with SDP certificates bounding recoverable information at given $\eta$ and $n$. Lower bounds: FunSearch/AlphaEvolve-style search over encoded-fusion families scored by certified (not sampled) decoding analyses, coupled to the enumeration machinery of Problems 1 and 2.

**Formalization.** Low to medium. Finite-gadget certificates: yes. Capacity arguments: expensive today.

**Status: open.** (All parts.)

---

### Problem 5. Minimum-fusion synthesis of graph states

**Setting.** Unbounded supply of $|\mathrm{GHZ}_3\rangle$ (LC-equivalent to the 3-vertex star and triangle graph states). Free operations: single-qubit Cliffords and Pauli-frame tracking. The costly operation is a *fusion*: a destructive Bell measurement $\{X\!\otimes\!X, Z\!\otimes\!Z\}$ on one qubit from each of two disjoint components, with the standard induced transformation on graph states (the post-measurement state is again a graph state, up to local Cliffords, on the remaining qubits; all four outcomes are LC-equivalent, so the success branch may be fixed without loss of generality; probabilistic compilation is a separate layer above this problem). For a connected simple graph $G$ on $N \ge 3$ vertices define
$$F(G) = \min\{\,\#\text{fusions producing a state LC-equivalent to } |G\rangle\,\}.$$

> **Problem 5.**
> **(i) Complexity.** Determine the computational complexity of $\mathrm{FUSION\text{-}COST} = \{(G, t) : F(G) \le t\}$. (Conjecture: NP-complete.)
> **(ii) Structure.** Determine $F$ exactly for natural families: paths, cycles, trees, the $L \times L$ 2D cluster state, the unit cells and bulk lattices of $\mathrm{FN}_6$ and Raussendorf-type complexes, and complete bipartite graphs. Even the 2D cluster family is open.
> **(iii) Extremal.** Determine the growth of $\mu(N) = \max\{F(G) : |V(G)| = N\}$.

**Lower bound (folklore, two lines).** If $g$ GHZ$_3$ states are consumed and $f$ fusions performed, photon counting gives $N = 3g - 2f$, and connectivity of the output forces $f \ge g - 1$; eliminating $g$ yields $F(G) \ge N - 3$ for every connected $G$, with equality exactly when a schedule exists in which every fusion merges two components and the final graph is LC-correct.

**Known results.** Exact minimum-fusion values for all graph states up to 8 qubits (about $2.8 \times 10^7$ non-isomorphic states) were computed by dynamic programming over LC orbits in the closely related model where the inputs are emitter-generated caterpillar states rather than GHZ$_3$ [40]; the authors derive graph-theoretic bounds for larger states and note the optimization is "likely computationally hard," with no proof. Adjacent hardness results: deciding transformability of graph states under local Cliffords, local Pauli measurements, and classical communication is NP-complete, and counting LC-equivalent graph states is #P-complete [41]; optimal emitter scheduling for deterministic generation is NP-hard [42]. None of these resolves (i).

**AI attack surface.** This is the closest analog in the list to the extremal-combinatorics successes of program search. The pipeline is complete: extend exact ground truth past 8 qubits with SAT/ILP and orbit-aware dynamic programming; mine the data for closed forms per family; search schedules with RL or evolutionary program search; then prove the conjectured formulas by induction. Both the upper-bound constructions and the lower-bound arguments are finite and checkable.

**Formalization.** High. SimpleGraph and the LC relation are formalizable in mathlib today; the fusion rule is a finite combinatorial relation; the counting lower bound is arithmetic plus connectivity induction. A Lean-verified value of $F$ for a named lattice family would be a clean first.

**Status: open.** (All parts.)

---

### Problem 6. Proof complexity and confluence of ZX rewriting

**Setting.** Clifford+T ZX diagrams (phases in $\frac{\pi}{4}\mathbb{Z}$); a finite ruleset $R$ complete for the fragment, for definiteness the Jeandel-Perdrix-Vilmart rules [21]. For semantically equal diagrams $D_1 = D_2$ let $\ell_R(D_1, D_2)$ be the minimum derivation length.

> **Problem 6.**
> **(i) Proof complexity.** Does there exist a polynomial $p$ such that for all semantically equal Clifford+T diagrams of size at most $s$, $\ell_R(D_1, D_2) \le p(s)$? Prove a polynomial upper bound, or exhibit a family with superpolynomial $\ell_R$. Determine whether the answer is ruleset-independent (up to polynomial overhead) across complete finite rulesets.
> **(ii) Confluence.** Does there exist a finite, terminating, confluent rewrite system that is complete for (a) the stabilizer fragment, (b) the Clifford+T fragment? (Partial progress: confluence of a reduced stabilizer system in the Heisenberg picture; the general question is open.)
> **(iii) Extraction.** Characterize the ZX diagrams from which a unitary circuit can be extracted in polynomial time. Generalized flow and Pauli flow are sufficient; general extraction is #P-hard [43]. Within the gflow class, determine the complexity of extracting a circuit with the minimum number of two-qubit gates.

**Known results.** Completeness: stabilizer fragment [20], Clifford+T and universal fragments [21, 22]. Extraction #P-hardness [43] and the flow-based extraction toolchain [44, 45]. Recently, a complete rewrite theory for *fault equivalence* of Clifford diagrams was given [23], and matchability-preserving, detector-aware rewrites with fault-tolerant circuit extraction were developed for the phase-free fragment [46]; these show the rewrite-theoretic layer of this area is currently movable, but neither resolves (i) or (ii).

**Why open.** Superpolynomial lower bounds in (i) are proof-complexity results and correspondingly hard; the polynomial direction is open simply because no normalization strategy with certified polynomial length is known beyond stabilizer diagrams. Confluence fails for the naive rulesets (spider unfusion and color change run forever) and no completed system is known.

**AI attack surface.** (ii) is Knuth-Bendix completion, the founding workload of automated reasoning (the Robbins conjecture was settled by exactly this kind of equational search); critical-pair analysis of candidate completed systems is mechanical and verifiable. For (i), machine search contributes both directions: finding short derivations at scale (training data and upper-bound evidence) and constructing candidate hard families (e.g., diagrams encoding pigeonhole-style tautologies) for lower-bound attempts.

**Formalization.** High for definitions and for any completed system found: rewrite systems are the native habitat of proof assistants, and a Lean-verified confluence proof via critical pairs is a standard exercise pattern at unusual scale.

**Status: open.** (All parts; (iii)'s general hardness is settled, its characterization and optimization questions are not.)

---

### Problem 7. A ZX-native fault-tolerance theorem

**Setting.** Clifford ZX instrument diagrams with Pauli webs, detecting regions, fault equivalence, and fault distance as in Section 2.2 [14, 23]. Call a family $\{D_L\}$ *$(\Delta, w, r)$-bounded* if spider degree is at most $\Delta$ and there is a generating set of detecting regions each of weight at most $w$ and diameter at most $r$ in the diagram metric. Call it *matchable* if every edge lies in at most two generating detecting regions [46]. Faults: i.i.d. edge depolarization at rate $p$ (each edge independently receives a uniformly random nonidentity Pauli with probability $p$).

> **Problem 7 (conjecture to be proven, refuted, or repaired).** For every $(\Delta, w, r)$ there exists $p^*(\Delta, w, r) > 0$ such that every $(\Delta, w, r)$-bounded, matchable family $\{D_L\}$ with fault distance $d(D_L) \ge \kappa L$ admits a polynomial-time decoder with logical fault probability $P_{\mathrm{fail}}(D_L) \le A e^{-\alpha d(D_L)}$ for all $p < p^*$, with $A, \alpha$ depending only on $(\Delta, w, r, \kappa)$.
> **Sub-problems.** **(i)** Prove the matchable case. **(ii)** Drop matchability: with generating regions of weight $\le w$, prove a threshold with a possibly inefficient decoder (hypergraph decoding). **(iii)** Extend Pauli webs and fault distance beyond the Clifford fragment, where they are currently undefined [46]. **(iv)** Show the threshold is an invariant of the fault-equivalence class: rewrites preserving the $(\Delta, w, r)$ bounds preserve $p^*$ up to constants [23].

**Known results.** The unification program expresses circuit-based, measurement-based, fusion-based, and Floquet fault tolerance as ZX diagrams with detecting regions [14]; detector-aware and matchability-preserving rewrites with fault-tolerant extraction exist for the phase-free fragment, with extension to Clifford and beyond stated as open [46]; fault equivalence has a complete Clifford rewrite theory [23]. Every known instance of the conjecture (surface code, $\mathrm{FN}_6$, honeycomb) has numerically established thresholds, and some have rigorous proofs in their native formalisms; no diagram-level sufficient condition with a proof exists. A proof in sufficient generality subsumes Problem 1.

**Why open.** The statement itself had no precise formulation until the 2023-2026 Pauli-web literature stabilized the definitions; the remaining work is a counting argument on a decoding (hyper)graph derived from the diagram, plus the invariance theory in (iv).

**AI attack surface.** The definitions are finite and crisp, which enables the most undervalued machine contribution: adversarial search for counterexamples to candidate theorem statements (small diagram families satisfying the hypotheses with vanishing thresholds would force repairs to the conjecture before proof effort is spent). The proof skeleton, once hypotheses are correct, is cluster counting as in Problem 1, mechanical and certifiable.

**Formalization.** Medium. The definitions (graphs, $\mathbb{F}_2$ linear algebra, webs as cocycles) are formalizable now; the statement alone is a worthwhile Lean artifact.

**Status: open.** (All parts.)

---

### Problem 8. Constant-overhead fusion-based quantum computation

**Setting.** Fusion-network families with constant-size resource states, $n$ resource states, $k$ logical qubits, fault distance $d$, noise $\mathrm{NM}$.

> **Problem 8.** Determine whether there exist constants $c$, $R > 0$, $\alpha > 0$, $p^* > 0$ and a family $\mathrm{FN}_n$ such that: resource states are drawn from a finite library of states on at most $c$ qubits; $k(\mathrm{FN}_n) \ge R\,n$; $d(\mathrm{FN}_n) \ge n^\alpha$; there is a polynomial-time decoder with $P_{\mathrm{fail}} \le e^{-\Omega(n^\alpha)}$ for all $(p_E, p_F, p_P)$ below $p^*$; and (computation version) a universal set of logical operations is implementable by composing such networks with constant-factor rate loss. The memory version drops the last condition.

**Known results.** The circuit-model analog is resolved: constant-overhead fault tolerance [47, 48], asymptotically good quantum LDPC codes [49], and constant-space-overhead schemes with improved time overhead [50]. Foliation lifts any CSS code to a cluster state of degree bounded by the maximum check weight plus two [51], and bounded-degree cluster states decompose into constant-size resource states joined by fusions; what is missing is the fault-tolerance analysis under $\mathrm{NM}$, where fusion failure erases syndrome information anisotropically and the foliated-qLDPC decoding problem under correlated erasure has no proven threshold. Numerical case studies exist for small bivariate-bicycle instances in an emitter-assisted, repeat-until-success architecture [52], which is evidence of practicality, not a theorem and not ballistic. A plausibly necessary ingredient, worth isolating as a sub-problem: do codes with single-shot structure (confinement or soundness) yield provable fusion-erasure thresholds under foliation?

**Why appealing.** This is the FBQC analog of the constant-overhead theorem, and it may be *easier* in one respect than Problem 2: the relevant syndrome graphs are expanders rather than Euclidean lattices, and percolation on expanders admits rigorous spectral control unavailable in 3D Euclidean geometry.

**AI attack surface.** Construction search over product codes and fusion layouts scored by certified parameters (distance, expansion, check weight: all $\mathbb{F}_2$ linear algebra, exactly checkable); then an erasure-threshold counting argument on expander syndrome graphs, which is a finite-certificate problem.

**Formalization.** Medium. The coding-theoretic layer ($\mathbb{F}_2$ linear algebra, expansion certificates) is formalizable; the full threshold proof is a larger project.

**Status: open.** (Memory and computation versions.)

---

### Problem 9. Closing the rigorous-numerical threshold gap for concatenated schemes

**Setting.** Circuit-level independent depolarizing noise in the standard location model [24]: each circuit location (preparation, gate, measurement, wait) fails independently with probability $\varepsilon$, failures depolarizing on the location's support. A scheme's accuracy threshold $\varepsilon_0(S)$ is the supremum of $\varepsilon$ for which $S$ simulates arbitrary $\mathrm{poly}$-size circuits to any accuracy with polylogarithmic overhead.

> **Problem 9.** Exhibit a fault-tolerance scheme $S$ together with a rigorous, machine-verifiable proof that $\varepsilon_0(S) \ge 10^{-2}$ against independent depolarizing circuit noise. Intermediate target: $\varepsilon_0(S) \ge 3 \times 10^{-3}$, a 2.4x improvement on the current record.

**Known results.** Rigorous records: $2.73 \times 10^{-5}$ for adversarial local stochastic noise, by computer-assisted combinatorial analysis [24]; $1.04 \times 10^{-3}$ for independent stochastic noise via the postselected (Knill-style) construction [25]; $0.67 \times 10^{-3}$ adversarial and $1.25 \times 10^{-3}$ depolarizing for the Fibonacci scheme [53]. Numerical estimates sit an order of magnitude higher: Knill's postselection-heavy estimates in the percent range [54], and circuit-level surface-code estimates near $1\%$. The gap has been explicitly flagged as a major open question since 2005 [55] and the rigorous record has not moved in over fifteen years.

**Why open.** The Aliferis-Gottesman-Preskill method reduces threshold bounds to counting malignant fault sets inside extended rectangles; pushing the counted level deeper, handling postselection conditioning rigorously, and optimizing gadget designs all explode combinatorially, and the human appetite for this ran out around 2009.

**AI attack surface.** This is the purest "industrialize a known proof method" problem on the list: malignant-set counting is a finite case analysis begging for #SAT with symmetry reduction; gadget design (ancilla verification circuits, decoding choices) is discrete search with a certificate-checkable objective; and the whole pipeline matches the template of machine-verified mass case analyses (four color, Kepler/Flyspeck, Keller in dimension seven, Boolean Pythagorean triples). Concatenated, non-surface-code constructions are the natural substrate, which is also where FBQC-style encoded fusions concatenate.

**Formalization.** High, and arguably the point: an end-to-end Lean-verified threshold theorem with an explicit constant would simultaneously raise the record and create the verification infrastructure that Problems 1, 2, and 7 reuse.

**Status: open.** (Both targets.)

---

### Problem 10. Distillation-free universality in fusion networks

**Setting.** Extend Definition 2.1 to allow a finite library $\mathcal{L}$ of constant-size resource states that need not be stabilizer states (for example, a 6-ring with one $T$-rotated leg, or CCZ-type states), and single-qubit measurements drawn from a fixed finite set of bases; fusions remain Bell-type. Noise: each resource state suffers an independent, arbitrary CPTP perturbation of diamond-norm size at most $\varepsilon_0$ (preparation noise), and fusions suffer $\mathrm{NM}(p_E,p_F,p_P)$. "Without distillation" is formalized as a volume condition: the spacetime network volume per logical non-Clifford gate at fault distance $d$ is $O(d^3)$ with constants independent of the target logical error, that is, non-Clifford gates cost $O(1)$ times the Clifford gate volume at the same distance, with no $\mathrm{polylog}(1/\epsilon)$ factory overhead.

> **Problem 10.** Prove or refute: there exist a finite library $\mathcal{L}$ of constant-size resource states, a fusion-network family, a polynomial-time decoder, and constants $\varepsilon^* > 0$, $p^* > 0$ such that the family implements a universal logical gate set with every logical operation suffering error at most $e^{-\Omega(d)}$ whenever $\varepsilon_0 < \varepsilon^*$ and $(p_E,p_F,p_P) < p^*$, under the volume condition above. A clean no-go under a precisely delimited model class would equally count as a solution.

**Remarks on the statement.** Some non-stabilizer element is forced: stabilizer resource states with Bell fusions and Pauli measurements are Gottesman-Knill simulable, hence non-universal. The question is whether the non-stabilizer element can live in constant-size resource states and be protected by the network itself, with a threshold theorem, at constant overhead. The asymptotic-rate motivation for avoiding distillation has recently evaporated: constant-overhead distillation ($\gamma = 0$) is now achieved even for qubits [56, 57]. What remains open is architectural and rigorous: magic state cultivation delivers striking circuit-model numerics with no threshold proof [58]; asymptotically good codes with transversal non-Clifford gates exist (2024-2025 constructions); 3D topological measurement-based schemes with transversal $T$ suggest a route; no fusion-network construction, and no proof in any of these directions, exists.

**AI attack surface.** Gadget search: small non-stabilizer resource states plus fusion patterns whose detecting structure covers non-Clifford faults, validated by exact small-distance simulation; the candidates feed the rigorous half, which couples to Problems 1 and 7 (a Pauli-web theory extended past Clifford, sub-problem 7(iii), is the missing language). The no-go direction is also searchable: model classes where constant-depth ballistic preparation of magic with exponentially small error is provably impossible.

**Formalization.** Low to medium today; the definitions formalize, the proofs are far.

**Status: open.** (Both directions.)

---

## 4. Summary

| # | Problem | Angle | Core type | Primary AI modality | Lean feasibility |
|---|---|---|---|---|---|
| 1 | Threshold theorem for $\mathrm{FN}_6$ | fusion networks | counting proof | proof generation + certified enumeration | Medium |
| 2 | Exact erasure thresholds | fusion networks, percolation | stat-mech / enumeration | certificate generation | Low-Medium |
| 3 | Boosted-fusion optimality $p^*(k)$ | linear optics, resource states | semialgebraic optimization | SOS/SDP dual certificates | Medium-High |
| 4 | Loss-tolerance frontier $\lambda^*(n)$ | fusion networks | two-sided bounds | gadget search + entropic certificates | Low-Medium |
| 5 | Minimum-fusion synthesis $F(G)$ | resource states, graph theory | extremal combinatorics | search, conjecture, prove | High |
| 6 | ZX proof complexity and confluence | ZX-calculus | rewriting theory | Knuth-Bendix completion, derivation search | High |
| 7 | ZX-native fault-tolerance theorem | ZX-calculus, fusion networks | theory + counting | counterexample search + proof generation | Medium |
| 8 | Constant-overhead FBQC | qLDPC, non-surface-code | coding theory | construction search + certified parameters | Medium |
| 9 | Rigorous $10^{-2}$ threshold | concatenated codes | massive case analysis | #SAT + Lean-verified enumeration | High |
| 10 | Distillation-free FBQC universality | resource states, magic | existence / no-go | gadget search + exact simulation | Low-Medium |

Dependencies worth exploiting: 9 builds verification infrastructure reused by 1, 2, and 7; 7 subsumes 1 if proven generally; 7(iii) is the language prerequisite for 10; 2 and 8 share the erasure-percolation machinery, with 8 on friendlier (expander) geometry.

---

## 5. Verification caveats and exclusions

### 5.1 Protocol and limits

Openness (criterion C1) was checked on June 9, 2026 by literature search over arXiv, journal, and indexing sources, seeded by each problem's canonical references and recent citing works. Two limits apply. First, search recall is imperfect: a 2026 preprint with nonstandard terminology could be missed, so any serious investment should begin by re-verifying C1 (each statement above is self-contained precisely to make that audit easy). Second, several of these problems are folklore-adjacent: partial results may exist in theses or appendices without being findable by topic search. Claims of the form "no published proof exists" are made to the best of our knowledge and flagged with hedging where the risk is highest (Problems 1(i) and 2(i), where known techniques plausibly extend and the open content is partly that nobody has written the proof, and fully the quantitative parts).

### 5.2 Excluded because recently closed (a calibration sample)

The pace of the field is the main threat to C1, so we record problems that would have appeared on this list two years ago and are now closed: the optimal magic-state distillation exponent, resolved with $\gamma = 0$ at constant overhead, including for qubits [56, 57]; the hardness of general ZX circuit extraction, settled as #P-hard [43]; a complete rewrite theory for fault equivalence of Clifford ZX diagrams [23]; and asymptotically good qLDPC codes [49]. Each closure reshaped, rather than removed, the neighboring open territory, which is reflected in Problems 6, 7, 8, and 10.

---

## References

[1] S. Bartolucci, P. Birchall, H. Bombín, H. Cable, C. Dawson, M. Gimeno-Segovia, E. Johnston, K. Kieling, N. Nickerson, M. Pant, F. Pastawski, T. Rudolph, C. Sparrow, "Fusion-based quantum computation," Nature Communications 14, 912 (2023). arXiv:2101.09310.

[2] R. Raussendorf, H. J. Briegel, "A one-way quantum computer," Phys. Rev. Lett. 86, 5188 (2001).

[3] R. Raussendorf, J. Harrington, K. Goyal, "A fault-tolerant one-way quantum computer," Ann. Phys. 321, 2242 (2006).

[4] M. Varnava, D. E. Browne, T. Rudolph, "How good must single photon sources and detectors be for efficient linear optical quantum computation?" Phys. Rev. Lett. 100, 060502 (2008).

[5] D. Herrera-Martí, A. G. Fowler, D. Jennings, T. Rudolph, "Photonic implementation for the topological cluster-state quantum computer," Phys. Rev. A 82, 032332 (2010).

[6] M. Gimeno-Segovia, P. Shadbolt, D. E. Browne, T. Rudolph, "From three-photon GHZ states to ballistic universal quantum computation," Phys. Rev. Lett. 115, 020502 (2015).

[7] H. Bombín, C. Dawson, R. V. Mishmash, N. Nickerson, F. Pastawski, S. Roberts, "Logical blocks for fault-tolerant topological quantum computation," PRX Quantum 4, 020303 (2023). arXiv:2112.12160.

[8] K. Sahay, J. Claes, S. Puri, "Tailoring fusion-based error correction for high thresholds to biased fusion failures," Phys. Rev. Lett. 131, 120604 (2023). arXiv:2301.00019.

[9] S. Paesani, B. J. Brown, "High-threshold quantum computing by fusing one-dimensional cluster states," Phys. Rev. Lett. 131, 120603 (2023). arXiv:2212.06775.

[10] W. P. Grice, "Arbitrarily complete Bell-state measurement using only linear optical elements," Phys. Rev. A 84, 042331 (2011).

[11] "Encoded-fusion-based quantum computation for high thresholds with linear optics," arXiv:2408.01041 (2024).

[12] F. Ewert, P. van Loock, "3/4-efficient Bell measurement with passive linear optics and unentangled ancillae," Phys. Rev. Lett. 113, 140403 (2014).

[13] H. Bombín, I. H. Kim, D. Litinski, N. Nickerson, M. Pant, F. Pastawski, S. Roberts, T. Rudolph, "Interleaving: modular architectures for fault-tolerant photonic quantum computing," arXiv:2103.08612 (2021).

[14] H. Bombín, D. Litinski, N. Nickerson, F. Pastawski, S. Roberts (alphabetical authorship varies by version), "Unifying flavors of fault tolerance with the ZX calculus," Quantum 8 (2024). arXiv:2303.08829.

[15] PsiQuantum team, "A manufacturable platform for photonic quantum computing," arXiv:2404.17570 (2024).

[16] R. Raussendorf, J. Harrington, K. Goyal, "Topological fault-tolerance in cluster state quantum computation," New J. Phys. 9, 199 (2007).

[20] M. Backens, "The ZX-calculus is complete for stabilizer quantum mechanics," New J. Phys. 16, 093021 (2014).

[21] E. Jeandel, S. Perdrix, R. Vilmart, "A complete axiomatisation of the ZX-calculus for Clifford+T quantum mechanics," LICS 2018. arXiv:1705.11151.

[22] A. Hadzihasanovic, K. F. Ng, Q. Wang, "Two complete axiomatisations of pure-state qubit quantum computing," LICS 2018.

[23] "Completeness for fault equivalence of Clifford ZX diagrams," arXiv:2510.08477 (2025).

[24] P. Aliferis, D. Gottesman, J. Preskill, "Quantum accuracy threshold for concatenated distance-3 codes," Quantum Inf. Comput. 6, 97 (2006). arXiv:quant-ph/0504218.

[25] P. Aliferis, D. Gottesman, J. Preskill, "Accuracy threshold for postselected quantum computation," Quantum Inf. Comput. 8, 181 (2008). arXiv:quant-ph/0703264.

[26] E. Dennis, A. Kitaev, A. Landahl, J. Preskill, "Topological quantum memory," J. Math. Phys. 43, 4452 (2002).

[27] N. Delfosse, G. Zémor, "Linear-time maximum likelihood decoding of surface codes over the quantum erasure channel," Phys. Rev. Research 2, 033042 (2020).

[28] M. A. Nielsen, C. M. Dawson, "Fault-tolerant quantum computation with cluster states," Phys. Rev. A 71, 042323 (2005). arXiv:quant-ph/0405134.

[29] P. Aliferis, D. W. Leung, "Simple proof of fault tolerance in the graph-state model," Phys. Rev. A 73, 032308 (2006).

[30] H. Kesten, "The critical probability of bond percolation on the square lattice equals 1/2," Comm. Math. Phys. 74, 41 (1980).

[31] W. P. Grice, Phys. Rev. A 84, 042331 (2011). (Same as [10]; ancilla hierarchy.)

[32] J. Calsamiglia, N. Lütkenhaus, "Maximum efficiency of a linear-optical Bell-state analyzer," Appl. Phys. B 72, 67 (2001).

[33] N. Lütkenhaus, J. Calsamiglia, K.-A. Suominen, "Bell measurements for teleportation," Phys. Rev. A 59, 3295 (1999).

[34] H. A. Zaidi, P. van Loock, "Beating the one-half limit of ancilla-free linear optics Bell measurements," Phys. Rev. Lett. 110, 260501 (2013). arXiv:1301.2749.

[35] F. Ewert, P. van Loock, Phys. Rev. Lett. 113, 140403 (2014). (Same as [12].)

[36] A. Olivo, F. Grosshans, "Ancilla-assisted linear optical Bell measurements and their optimality," Phys. Rev. A 98, 042323 (2018).

[37] M. J. Bayerbach, S. E. D'Aurelio, P. van Loock, S. Barz, "Bell-state measurement exceeding 50% success probability with linear optics," Science Advances 9, eadf4080 (2023). arXiv:2208.02271.

[38] See also pre-detection squeezing approaches, e.g. arXiv:1809.09264.

[39] M. Varnava, D. E. Browne, T. Rudolph, "Loss tolerance in one-way quantum computation via counterfactual error correction," Phys. Rev. Lett. 97, 120501 (2006).

[40] M. C. Löbl, S. X. Chen, S. Paesani, A. S. Sørensen, "Generating graph states with a single quantum emitter and the minimum number of fusions," Phys. Rev. A 111, 052604 (2025). arXiv:2412.04587.

[41] A. Dahlberg, J. Helsen, S. Wehner, "How to transform graph states using single-qubit operations: computational complexity and algorithms," Quantum Sci. Technol. / Quantum 4, 348 (2020) and companion works.

[42] B. Li, S. E. Economou, E. Barnes, "Photonic resource state generation from a minimal number of quantum emitters," npj Quantum Information 8, 93 (2022).

[43] N. de Beaudrap, A. Kissinger, J. van de Wetering, "Circuit extraction for ZX-diagrams can be #P-hard," ICALP 2022. arXiv:2202.09194.

[44] R. Duncan, A. Kissinger, S. Perdrix, J. van de Wetering, "Graph-theoretic simplification of quantum circuits with the ZX-calculus," Quantum 4, 279 (2020).

[45] M. Backens, H. Miller-Bakewell, G. de Felice, L. Lobski, J. van de Wetering, "There and back again: a circuit extraction tale," Quantum 5, 421 (2021).

[46] M. Schweikart, L. Grans-Samuelsson, A. Kissinger, B. Rodatz, "Preserving MWPM decodability in fault-equivalent rewrites" (working title per public draft), submitted to QPL 2026. arXiv:2603.19522.

[47] D. Gottesman, "Fault-tolerant quantum computation with constant overhead," Quantum Inf. Comput. 14, 1338 (2014). arXiv:1310.2984.

[48] O. Fawzi, A. Grospellier, A. Leverrier, "Constant overhead quantum fault-tolerance with quantum expander codes," FOCS 2018. arXiv:1808.03821.

[49] P. Panteleev, G. Kalachev, "Asymptotically good quantum and locally testable classical LDPC codes," STOC 2022. arXiv:2111.03654.

[50] H. Yamasaki, M. Koashi, "Time-efficient constant-space-overhead fault-tolerant quantum computation," Nature Physics 20, 247 (2024). arXiv:2207.09611.

[51] A. Bolt, G. Duclos-Cianci, D. Poulin, T. M. Stace, "Foliated quantum error-correcting codes," Phys. Rev. Lett. 117, 070501 (2016).

[52] "Fusion-based implementation of qLDPC codes with quantum emitters," npj Quantum Information (2026). arXiv:2509.17223.

[53] P. Aliferis, J. Preskill, "Fibonacci scheme for fault-tolerant quantum computation," Phys. Rev. A 79, 012332 (2009).

[54] E. Knill, "Quantum computing with realistic noisy devices," Nature 434, 39 (2005).

[55] B. W. Reichardt, "Fault-tolerance threshold for a distance-three quantum code," arXiv:quant-ph/0509203 (2005); see its concluding discussion.

[56] A. Wills, M.-H. Hsieh, H. Yamasaki, "Constant-overhead magic state distillation," arXiv:2408.07764 (2024); Nature Physics (2025).

[57] Companion constructions of asymptotically good qubit codes with transversal CCZ (2024-2025); see citations within [56].

[58] C. Gidney, N. Shutty, C. Jones, "Magic state cultivation: growing T states as cheap as CNOT gates," arXiv:2409.17595 (2024).

---

*Status of every problem was verified against the literature on June 9, 2026; reference details for a small number of 2025-2026 preprints (notably [11], [23], [46], [52]) were taken from indexing snippets and should be confirmed against the arXiv records before citation in formal work.*
