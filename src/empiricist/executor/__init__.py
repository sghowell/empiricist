"""The executor: sandboxed subprocess execution and optional run provenance.

The model never gets a shell (spec §6). Everything Empiricist runs —
verifiers, enumerators, solvers, model CLI calls — flows through
runner.execute(), which applies darwin-safe resource limits, the
sandbox seam, and the RSS watchdog. A caller gets a `runs` row only when it
attaches the ledger; tablebase and Lean receipt handoff remain explicit gaps.
"""
