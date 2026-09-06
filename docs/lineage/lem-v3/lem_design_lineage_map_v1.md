# Lem Design Lineage Map

**Zetetic Works Research Corporation / AI for Physics Neolab**

Reading rule: **RLM-style** influence is strongest in context/external-memory strategy; **Aletheia-style** influence is strongest in recursive verification/refinement; **Lem-specific** influence is strongest in admission and epistemic memory semantics. Mixed tags indicate a blended mechanism.

| Mechanism | Tag | Where in docs | Purpose / intended value |
|---|---|---|---|
| Externalized research memory (workspace / graph / artifact registry) | RLM + Lem | Arch 3.1-3.4; Evid 5.3; Inf 9 | Treat research state as an addressable environment rather than one giant prompt; scales long-horizon reasoning and preserves provenance, auditability, and resumeability. |
| Facet decomposition + coverage tracking | RLM | Cog 5.1-5.2; Cog 7.1-7.5 | Break large questions into live subproblems and recurse only where evidence is thin; improves depth control and exposes hidden assumptions. |
| Selective evidence peeking via tools | RLM | Cog 10-11; Arch 6.1; Inf 5 | Pull exact passages, runs, or artifacts on demand instead of stuffing full context; reduces dilution and strengthens traceability. |
| Summary + pointer compression | RLM | Arch 3.1; Cog 10.1; Inf 9.2-9.3 | Compress older context into summaries and stable references while keeping primaries reopenable; lowers token cost without losing auditability. |
| Nested GVR admission loop | Aletheia + Lem | Arch 4.1; Cog 6; PRFAQ: Core Differentiator | Generate, challenge, revise, and only then admit candidate syntheses; improves correctness and prevents sloppy memory promotion. |
| Verifier independence / diversity policy | Aletheia | Arch 4.2; Inf 4.4-4.5; Cog 2.2, 6.3, 11.3 | Make verification a real challenge function instead of a self-echo; reduces correlated errors and superficial passes. |
| Honest abstention / admit failure | Aletheia | Cog 8.2-8.3; Arch 7.1; PRFAQ FAQ | Allow partial answers plus the next-best discriminating action when evidence is insufficient; protects credibility and avoids false certainty. |
| Admission boundary + record classes | Lem | Arch 2.1-2.2, 7.1; Evid 2.2-2.6, 6; MCP 6 | Separate artifacts, observations, and runs from claims, hypotheses, and decisions, and keep challenged drafts local; gives Lem a clean epistemic boundary. |
| Confidence != verification != freshness | Lem | Arch 7.3; Cog 2.4; Evid 2.4-2.8, 7.4 | Separate support strength from challenge depth and staleness; makes status, querying, and re-verification more truthful. |
| Plan -> execute -> observe -> resynthesize | RLM + Aletheia | Arch 6.2; Cog 9.2-9.3; MCP 6 | Turn reasoning into evidence-generating action and loop results back through synthesis and verification; makes Lem a research agent, not just a summarizer. |

Abbreviations: **Arch** = Architecture; **Cog** = Cognitive; **Evid** = Evidence Graph; **Inf** = Inference; **MCP** = Workload Contract. This map is interpretive: it shows strongest design lineage, not exclusive authorship.
