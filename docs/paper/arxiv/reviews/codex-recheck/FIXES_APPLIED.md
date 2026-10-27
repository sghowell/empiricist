# Fixes applied: Codex recheck

Recheck: `REVIEW.md` in this directory (Codex, gpt-6-astra, maximum reasoning, live web search, read-only;
prompt in `PROMPT.md`, the diff it checked in `review-fixes.diff`). Verdict: all eight mathematical
findings and seven of nine novelty findings resolved; no new mathematical error; Table I, the rank-width
outputs (cross-checked with an independent subset dynamic program), the replays and all 50 manifest hashes
reproduced. Three items remained; all applied.

| # | Finding | Fix |
|---|---|---|
| R1 | The hardness results are about fixed qubit labels: Bell pairs on specified pairs of qubits, and counting labelled graph states under local complementation alone, while the paper identifies isomorphic graphs | The sentence now says "even when the target is a tensor product of Bell pairs on specified pairs of qubits" and "counting the labelled graph states in an orbit under local complementation alone, without identifying isomorphic graphs, is #P-complete" |
| R2 | Hein et al. 2006 chapter metadata available on the publisher's page | Converted to a chapter entry (Quantum Computers, Algorithms and Chaos, Proc. Int. School of Physics "Enrico Fermi" vol. 162, IOS Press, pp. 115-218, 2006, DOI 10.3254/978-1-61499-018-5-115), verified on the IOS Press page |
| R3 | Adcock et al. is in the 2019 journal issue (online 2018) | year 2019 (key renamed Adcock2019hard) |
