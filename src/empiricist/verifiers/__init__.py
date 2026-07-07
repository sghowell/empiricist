"""verifiers/: the trust boundary (spec §7).

Verifiers are the only code path licensed to turn "an engine claims X" into
"the ledger records X as PASS/FAIL/ERROR" -- and even that license is itself
gated: a Verifier's verify() may run only after Registry.certify() has proven
it correctly PASSES and FAILS every case in a mutation-resistant golden suite
(verifiers/goldens.py), and only for as long as its (name, version,
binary_hash) triple's stamp remains valid against the LIVE golden suite (a
changed suite invalidates every existing stamp -- spec §7's golden_suite_hash
rule, checked by registry.Registry.verify against goldens.suite_hash()).
binary_hash ties the stamp to the verifier's own source AND its wrapped
engine's source, so any edit -- to the verifier or the engine it drives --
silently and immediately revokes trust rather than leaving a stale PASS on
the books.

Two independently-implemented fusion verifiers live here: stab_fusion.py
wraps engine A (StimEngine, domain/p5/fusion_stim.py); enum_fusion.py wraps
engine B (GF2Engine, domain/p5/fusion_gf2.py). Their agreement
(registry.verify_agreed) is F3 (two independent implementations, no shared
transition code) made concrete: a construction only counts as verified when
both certified, independently-implemented engines agree on the post-fusion
LC-orbit key.
"""

from __future__ import annotations
