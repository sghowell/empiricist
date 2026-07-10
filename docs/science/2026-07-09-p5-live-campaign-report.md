# Empiricist Campaign Report

- Run directory: `runs/p5-live`
- Config hash: `9a173c548200768af131e965e18cb2fa893786cbc9a198b84ef043c8182f537f`
- Environment: python 3.11.14 (main, Dec  9 2025, 19:11:45) [Clang 21.1.4 ]; platform macOS-26.2-arm64-arm-64bit
- Total spend: $140.9915 (55206 input tokens, 2204416 output tokens)

## Per-role spend

| Role | Runs | Cost (USD) | Tokens in | Tokens out |
|---|---|---|---|---|
| conjecturer | 144 | 9.5750 | 5118 | 118197 |
| searcher | 1440 | 131.4164 | 50088 | 2086219 |

## Claims

| ID | Kind | Title | Status | Status N | Coverage |
|---|---|---|---|---|---|
| `dc8649519e5f` | dataset | GHZ3 min-fusion tablebase: F(G) for connected orbits, n=3..9 | VERIFIED_N | 9 | exhaustive |
| `b29cbaab38c0` | construction | SEARCH exact upgrade: orbit 000000000000 F=8 | HEURISTIC | - | - |
| `28a137365e1a` | construction | SEARCH exact upgrade: orbit 000000000000 F=8 | HEURISTIC | - | - |
| `30b3f164629e` | construction | SEARCH exact upgrade: orbit 000000000000 F=8 | HEURISTIC | - | - |
| `10dfdce91915` | statement | Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 (paths attain the universal lower bound F(N) >= N-3, and n-3 === n-3 (mod 3) satisfies the congruence invariant) | CONJECTURED | - | - |
| `6631c12f436f` | statement | Conjecture: path F(N) = F(N) = N - 3 for all N >= 3 | CONJECTURED | - | - |
| `d97a28d0955e` | statement | Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 (path family attains the universal lower bound F(N) >= N-3 with equality; congruence F(N) === N-3 (mod 3) holds trivially) | CONJECTURED | - | - |
| `8ee55e65bdd2` | statement | Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 | CONJECTURED | - | - |
| `107267174623` | statement | Conjecture: path F(N) = F(N) = N - 3 for all N >= 3 (the path orbit attains the universal lower bound F(N) >= N-3, and N-3 ≡ N-3 (mod 3) automatically) | CONJECTURED | - | - |
| `75a953ef0513` | statement | Conjecture: path F(N) = F(N) = N - 3 for all N >= 3 (achieves the universal lower bound F(N) >= N-3 with equality, and trivially satisfies F(N) === N-3 mod 3) | CONJECTURED | - | - |
| `3f0d80f0bae8` | statement | Conjecture: path F(N) = F(N) = N - 3 | CONJECTURED | - | - |
| `e2a5d0ea878e` | construction | SEARCH exact upgrade: orbit 000000000000 F=8 | HEURISTIC | - | - |
| `375f9685f8b7` | statement | Conjecture: path F(N) = F(n) = n - 3 | CONJECTURED | - | - |
| `c8c94e51d0ef` | statement | Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 | CONJECTURED | - | - |
| `2a84ece822a7` | statement | Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 (the path orbit attains the universal lower bound F(N) >= N-3 with equality, consistent with F(N) ≡ N-3 (mod 3)) | CONJECTURED | - | - |
| `716793e3d9c3` | statement | Conjecture: star F(N) = F(n) = n - 3 for all n >= 3 | CONJECTURED | - | - |
| `401d7bd3d4d9` | statement | Conjecture: complete F(N) = F(N) = N - 3 for all N >= 3 (the complete graph K_N achieves the universal lower bound F(N) >= N-3 with equality) | CONJECTURED | - | - |
| `90c1fdcadf65` | statement | Conjecture: cycle F(N) = F(n) = n - 3 for n <= 4; F(n) = n for n >= 5 (equivalently F(n) = (n-3) + 3*[n>=5]) | CONJECTURED | - | - |
| `235f4cd05ecb` | construction | SEARCH exact upgrade: orbit 000000000000 F=9 | HEURISTIC | - | - |
| `960c7fec66c8` | construction | SEARCH exact upgrade: orbit 000000000000 F=10 | HEURISTIC | - | - |
| `b8fe46d3ec0d` | construction | SEARCH exact upgrade: orbit 000000000000 F=10 | HEURISTIC | - | - |

## Provenance (VERIFIED_N / CERTIFIED / FORMALIZED)

## Certifications (trust boundary, spec §7)

| Verifier | Version | Binary hash | Golden suite | Verdict | Stamped at |
|---|---|---|---|---|---|
| enum_fusion | 1.0 | `42c3d85a0bda` | `fbc0b1971c84` | PASS | 2026-07-08T04:03:21.831172+00:00 |
| stab_fusion | 1.0 | `962180adf8eb` | `fbc0b1971c84` | PASS | 2026-07-08T04:03:21.817407+00:00 |

### dataset: GHZ3 min-fusion tablebase: F(G) for connected orbits, n=3..9 (`dc8649519e5f`)

- Status: **VERIFIED_N**, n=9, coverage=exhaustive
- CAS digest: `dc8649519e5f86948a4283118b979fd958511687731bdb5ddc78c11956571f25` (exists in store: True)

Evidence:

| Verifier | Version | Binary hash | Verdict | Wall (s) | Details |
|---|---|---|---|---|---|
| p5_tablebase_dataset_ingest | 1.0 | `d98b7e0ef605` | PASS | - | `{"exact_rows_verified":185,"golden_suite_hash":"fbc0b1971c844d1e998d2c8766c6829bfe4497f9d6e91a1c98b4321661d665a2","per_n":{"3":{"open":0,"tier0":1,"tier1":0,"total":1},"4":{"open":0,"tier0":2,"tier1":0,"total":2},"5":{"open":0,"tier0":3,"tier1":1,"total":4},"6":{"open":1,"tier0":8,"tier1":2,"total":11},"7":{"open":4,"tier0":15,"tier1":7,"total":26},"8":{"open":59,"tier0":42,"tier1":0,"total":101},"9":{"open":336,"tier0":104,"tier1":0,"total":440}},"witness_verifiers":["stab_fusion","enum_fusion"]}` |

## CONJECTURED

- **Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 (paths attain the universal lower bound F(N) >= N-3, and n-3 === n-3 (mod 3) satisfies the congruence invariant)** (`10dfdce91915`)
  - Statement: `{"closed_form":"F(n) = n - 3 for all n >= 3 (paths attain the universal lower bound F(N) >= N-3, and n-3 === n-3 (mod 3) satisfies the congruence invariant)","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(N) = N - 3 for all N >= 3** (`6631c12f436f`)
  - Statement: `{"closed_form":"F(N) = N - 3 for all N >= 3","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 (path family attains the universal lower bound F(N) >= N-3 with equality; congruence F(N) === N-3 (mod 3) holds trivially)** (`d97a28d0955e`)
  - Statement: `{"closed_form":"F(n) = n - 3 for all n >= 3 (path family attains the universal lower bound F(N) >= N-3 with equality; congruence F(N) === N-3 (mod 3) holds trivially)","confidence":0.95,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(n) = n - 3 for all n >= 3** (`8ee55e65bdd2`)
  - Statement: `{"closed_form":"F(n) = n - 3 for all n >= 3","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(N) = N - 3 for all N >= 3 (the path orbit attains the universal lower bound F(N) >= N-3, and N-3 ≡ N-3 (mod 3) automatically)** (`107267174623`)
  - Statement: `{"closed_form":"F(N) = N - 3 for all N >= 3 (the path orbit attains the universal lower bound F(N) >= N-3, and N-3 \u2261 N-3 (mod 3) automatically)","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(N) = N - 3 for all N >= 3 (achieves the universal lower bound F(N) >= N-3 with equality, and trivially satisfies F(N) === N-3 mod 3)** (`75a953ef0513`)
  - Statement: `{"closed_form":"F(N) = N - 3 for all N >= 3 (achieves the universal lower bound F(N) >= N-3 with equality, and trivially satisfies F(N) === N-3 mod 3)","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(N) = N - 3** (`3f0d80f0bae8`)
  - Statement: `{"closed_form":"F(N) = N - 3","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(n) = n - 3** (`375f9685f8b7`)
  - Statement: `{"closed_form":"F(n) = n - 3","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(n) = n - 3 for all n >= 3** (`c8c94e51d0ef`)
  - Statement: `{"closed_form":"F(n) = n - 3 for all n >= 3","confidence":0.95,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: path F(N) = F(n) = n - 3 for all n >= 3 (the path orbit attains the universal lower bound F(N) >= N-3 with equality, consistent with F(N) ≡ N-3 (mod 3))** (`2a84ece822a7`)
  - Statement: `{"closed_form":"F(n) = n - 3 for all n >= 3 (the path orbit attains the universal lower bound F(N) >= N-3 with equality, consistent with F(N) \u2261 N-3 (mod 3))","confidence":0.97,"family":"path","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: star F(N) = F(n) = n - 3 for all n >= 3** (`716793e3d9c3`)
  - Statement: `{"closed_form":"F(n) = n - 3 for all n >= 3","confidence":0.93,"family":"star","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: complete F(N) = F(N) = N - 3 for all N >= 3 (the complete graph K_N achieves the universal lower bound F(N) >= N-3 with equality)** (`401d7bd3d4d9`)
  - Statement: `{"closed_form":"F(N) = N - 3 for all N >= 3 (the complete graph K_N achieves the universal lower bound F(N) >= N-3 with equality)","confidence":0.97,"family":"complete","predicted_values":{"3":0,"4":1,"5":2,"6":3,"7":4,"8":5,"9":6}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)
- **Conjecture: cycle F(N) = F(n) = n - 3 for n <= 4; F(n) = n for n >= 5 (equivalently F(n) = (n-3) + 3*[n>=5])** (`90c1fdcadf65`)
  - Statement: `{"closed_form":"F(n) = n - 3 for n <= 4; F(n) = n for n >= 5 (equivalently F(n) = (n-3) + 3*[n>=5])","confidence":0.75,"family":"cycle","predicted_values":{"3":0,"4":1,"5":5,"6":6,"7":7,"8":8,"9":9}}`
  - Falsification effort: 21 check(s) survived (verifier=auto_attack, verdict=PASS)

## REFUTED

_(none)_

## Gates

### Pending

| ID | Kind | Artifact | Opened at | Note |
|---|---|---|---|---|
| 30375c34d03f475b8f23c60ddb79e10e | PROOF_CAMPAIGN | `10dfdce91915` | 2026-07-09T20:35:30.524819+00:00 | parked: >=1 CONJECTURED artifact awaiting a human-approved PROVE campaign |

### Resolved

_(none)_

## Search summary

- Generations run: 45
- Population size: 8
- Exact upgrades: 7
- Stall / alarm events:
  - _(none)_

