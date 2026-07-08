/-
Copyright (c) 2026 Sean Howell. All rights reserved.
Released under the MIT license as described in the file LICENSE.
Authors: Sean Howell
-/
import Lean

/-!
# `axiom_audit` — the compiled axiom-SET + statement driver (M8 soundness fix v3)

This is the COMPILED axiom-set and statement authority for the LeanVerifier's
FORMALIZED trust gate. It runs LAST, only AFTER two earlier gates have already
established that the submitted module is kernel-sound:

1. `lake env lean --json -o <olean> <scratch>` compiled the module to an olean
   (any `severity=="error"` / `sorry` warning already rejected there), and
2. `lake env leanchecker <Module>` re-checked THAT olean's own added declarations
   through the REAL Lean kernel, starting from its (trusted, pinned-mathlib)
   imports. This is the trust anchor: it rejects environment-hacking injections
   (`addDeclCore (doCheck := false)`, `Environment.add`, `skipKernelTC`) that give
   a constant a FALSE type but a clean, axiom-free value.

Because the kernel already accepted the olean, THIS driver's job is only the
*epistemic-hygiene* part that leanchecker does not do: report the decl's AXIOM
SET (so the harness whitelist can reject `sorryAx` / `native_decide` / custom
axioms — all of which are kernel-VALID, so leanchecker passes them) and the
decl's resolved STATEMENT (provenance: what was actually proven).

**Why it IMPORTS the compiled olean rather than re-elaborating the source.** The
predecessor computed axioms by re-running `Lean.Elab.runFrontend` on the source.
That re-elaboration is a SECOND, independent frontend run; a source whose
compile-time metaprogramming branches on a clock / nondeterministic input could
make the olean that leanchecker checked (honest branch) DIVERGE from the env the
audit sees (evil branch), certifying a statement leanchecker never validated.
Auditing the SAME single olean artifact leanchecker checked closes that gap: there
is exactly one compiled artifact, and every gate reads it.

**The nonce channel (unchanged trust story).** The harness passes a fresh
unguessable nonce via a file; the driver reads it and DELETES the file BEFORE
`importModules` (importing runs the module's `initialize` blocks, which can do IO).
The whole import runs under `IO.FS.withIsolatedStreams`, so any `initialize`-time
stdout is captured and discarded. The driver then writes EXACTLY ONE line to the
restored real stdout: `AXIOM_AUDIT::<nonce>::{...}`. A source that forges a line
cannot know the nonce, so the harness (`parse_driver_result`) rejects it and the
audit fails closed.
-/

open Lean

namespace AxiomAudit

/-- The framing marker prefixing the driver's single result line. -/
def resultMarker : String := "AXIOM_AUDIT"

/-- Run a `CoreM` action against a fixed environment. Used ONLY to call the
compiled `Lean.collectAxioms` and the pretty-printer; performs no elaboration of
untrusted source. `maxHeartbeats := 0` removes any limit on the axiom walk. -/
def runCoreM {α : Type} (env : Environment) (x : CoreM α) : IO α := do
  let ctx : Core.Context :=
    { fileName := "<axiom_audit>"
      fileMap := default
      options := (maxHeartbeats.set {} 0) }
  Prod.fst <$> x.toIO ctx { env }

/-- The audit result, serialized as the driver's single JSON output line.
`statement` is the decl's resolved, pretty-printed type (empty when not found). -/
structure Result where
  declFound : Bool
  errors : Array String
  axioms : Array String
  statement : String

def Result.toJson (r : Result) : Json :=
  Json.mkObj
    [ ("declFound", Json.bool r.declFound)
    , ("errors", Json.arr (r.errors.map Json.str))
    , ("axioms", Json.arr (r.axioms.map Json.str))
    , ("statement", Json.str r.statement) ]

/-- Write the single nonce-framed result line to the REAL stdout (called only
after `withIsolatedStreams` has restored the stream). -/
def emit (nonce : String) (r : Result) : IO Unit := do
  let out ← IO.getStdout
  out.putStr s!"{resultMarker}::{nonce}::{r.toJson.compress}\n"
  out.flush

/-- Import the already-compiled module (its olean must be on the search path) and
compute, from COMPILED code over the returned `Environment`, the decl's axiom set
and pretty-printed statement. Runs under isolated streams so the module's
`initialize`-time IO cannot reach real stdout. `loadExts := true` so the
pretty-printer has the imported notation available for a referee-readable
statement. -/
unsafe def auditModule (modName declName : Name) : IO (String × Result) :=
  IO.FS.withIsolatedStreams do
    let env ← importModules #[{ module := modName }] {} (loadExts := true)
    match env.find? declName with
    | none => pure { declFound := false, errors := #[], axioms := #[], statement := "" }
    | some ci =>
      let names ← runCoreM env (Lean.collectAxioms declName)
      let fmt ← runCoreM env (Lean.Meta.ppExpr ci.type).run'
      pure { declFound := true, errors := #[], axioms := names.map (·.toString),
             statement := fmt.pretty }

unsafe def mainUnsafe (args : List String) : IO UInt32 := do
  match args with
  | [modStr, declStr, noncePath] =>
    -- Read the harness nonce, then delete its file BEFORE importing the
    -- untrusted module (import runs `initialize` blocks that can do IO). Only a
    -- result line bearing this nonce is trusted by the harness.
    let nonce := (← IO.FS.readFile noncePath).trimAscii.toString
    try IO.FS.removeFile noncePath catch _ => pure ()
    let modName := modStr.toName
    let declName := declStr.toName
    try
      Lean.initSearchPath (← Lean.findSysroot)
      -- Required before `importModules (loadExts := true)`: imported modules run
      -- `initialize` / module init code.
      Lean.enableInitializersExecution
      let (_captured, r) ← auditModule modName declName
      emit nonce r
      pure (0 : UInt32)
    catch e =>
      emit nonce { declFound := false, errors := #[toString e], axioms := #[], statement := "" }
      pure (1 : UInt32)
  | _ =>
    IO.eprintln "usage: axiom_audit <module-name> <fully-qualified-decl> <nonce-file>"
    pure (2 : UInt32)

end AxiomAudit

/-- Entry point. `unsafe` because `Lean.enableInitializersExecution` and
`importModules (loadExts := true)` (imported modules run `initialize` code) are
`unsafe`. -/
unsafe def main (args : List String) : IO UInt32 :=
  AxiomAudit.mainUnsafe args
