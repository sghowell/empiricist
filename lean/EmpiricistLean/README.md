# EmpiricistLean

Pinned `lake` + `mathlib` project used by the Empiricist project's Lean
verifier (M8). Mathlib is pinned to a specific release tag via
`lakefile.toml`'s `[[require]]` block (`lake-manifest.json` is the
committed pin — do not `lake update` casually).

`EmpiricistLean/Basic.lean` holds the pipeline's first FORMALIZED scaffold
lemma: a connected simple graph on a finite vertex set has at least
`|V| - 1` edges, proved sorry-free against the pinned mathlib.

Build artifacts (`.lake/`, including the multi-GB mathlib `oleans`) are
gitignored and fetched locally via `lake exe cache get`; they are not
versioned.
