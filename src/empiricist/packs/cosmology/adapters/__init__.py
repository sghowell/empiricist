"""Contract adapters: the death_and_gravity checkers that do not themselves expose
`REPORT` / `build_report()` / `validate_report()` (the P8(b) base chain's `p8.verify` and
`p8.verify_all`), presented in that contract so `ReplayVerifier` can run them. Each adapter
is the thinnest possible wrapper over the vendored code: it recomputes what the checker
recomputes and compares exactly. SOURCES.md says so."""
