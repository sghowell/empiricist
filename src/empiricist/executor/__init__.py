"""The executor: sandboxed subprocess execution with total provenance.

The model never gets a shell (spec §6). Everything Empiricist runs —
verifiers, enumerators, solvers, model CLI calls — flows through
runner.execute(), which applies darwin-safe resource limits, the
sandbox seam, the RSS watchdog, and emits one runs row per execution.
"""
