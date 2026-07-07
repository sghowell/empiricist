/-
Copyright (c) 2026 Sean Howell. All rights reserved.
Released under the MIT license as described in the file LICENSE.
Authors: Sean Howell
-/
import Lean

/-!
# `axiom_audit` — the compiled axiom-audit driver (M8 soundness fix)

This is the COMPILED authority for the LeanVerifier's FORMALIZED trust gate.
The in-band `#print axioms <decl>` approach it replaces is UNSOUND: any surface
the harness re-elaborates in the tainted environment (`#print`, `#eval`,
`run_cmd`, macros) is attacker-shadowable, so a submitted source can redefine
the `#print axioms` command (`elab "#print " "axioms" ... => logInfo "clean"`)
or spoof its output and certify `theorem two : (1:Nat)=2 := evil.elim`.

This driver computes the axiom set from COMPILED code that walks the real kernel
environment (`Lean.collectAxioms`, exactly what `Lean.Elab.Command.elabPrintAxioms`
calls), never from a re-elaboratable command. It:

1. Reads a fresh harness nonce from a file and DELETES that file BEFORE
   elaborating the untrusted source, so the source's compile-time IO can never
   learn it (even reading `IO.getArgs` yields only a path to an already-deleted
   file). Only a result line bearing this nonce is trusted by the harness — so a
   direct `/dev/stdout` write followed by `IO.Process.exit` still cannot forge
   an accepted result.
2. Elaborates the source with `Lean.Elab.runFrontend` — the exact frontend
   `lean --json` uses (proper import loading, async elaboration, and per-command
   compile-time-stdout capture). The whole call runs under
   `IO.FS.withIsolatedStreams`, so the frontend's own diagnostic report (which is
   where a source's `#eval`-printed fake axiom line lands, as INFORMATION-level
   message data) is captured into a string we DISCARD; it can never reach the
   driver's real stdout, and we never parse it for the axiom decision.
3. From compiled code over the returned `Environment`: looks up the decl (absent,
   or the frontend reported errors → FAIL CLOSED) and calls `Lean.collectAxioms`.
   `sorryAx` and `native_decide`'s synthesized per-decl axioms appear naturally,
   so the harness whitelist check catches them.
4. Emits EXACTLY ONE nonce-framed JSON line to the real (restored) stdout AFTER
   the frontend returns:
   `AXIOM_AUDIT::<nonce>::{"declFound":…,"errors":[…],"axioms":[…]}`.

Any exception fails closed: a nonce-framed `{"declFound":false,"errors":[…],…}`
line is still emitted (so the harness sees structured evidence) and the process
exits nonzero. The harness also imposes its own timeout.
-/

open Lean

namespace AxiomAudit

/-- The framing marker prefixing the driver's single result line. -/
def resultMarker : String := "AXIOM_AUDIT"

/-- Run a `CoreM` action against a fixed environment. Used ONLY to call the
compiled `Lean.collectAxioms`; performs no elaboration. `maxHeartbeats := 0`
removes any limit on the axiom walk. -/
def runCoreM {α : Type} (env : Environment) (x : CoreM α) : IO α := do
  let ctx : Core.Context :=
    { fileName := "<axiom_audit>"
      fileMap := default
      options := (maxHeartbeats.set {} 0) }
  Prod.fst <$> x.toIO ctx { env }

/-- The audit result, serialized as the driver's single JSON output line. -/
structure Result where
  declFound : Bool
  errors : Array String
  axioms : Array String

def Result.toJson (r : Result) : Json :=
  Json.mkObj
    [ ("declFound", Json.bool r.declFound)
    , ("errors", Json.arr (r.errors.map Json.str))
    , ("axioms", Json.arr (r.axioms.map Json.str)) ]

/-- Best-effort extraction of `.error`-severity diagnostic strings from the
frontend's captured `--json` report, for the human-readable `errors` field. This
is COSMETIC: the security decision is `runFrontend` returning `none` (errors) vs
`some env`; a source can only ADD messages, never turn a real error into `some`.
A source's `#eval` output is captured by the frontend as INFORMATION-severity
message data, so it is ignored here. -/
def extractErrors (captured : String) : Array String := Id.run do
  let mut errs : Array String := #[]
  for line in captured.splitOn "\n" do
    if errs.size ≥ 5 then
      break
    match Json.parse line with
    | .ok j =>
      match j.getObjValAs? String "severity", j.getObjValAs? String "data" with
      | .ok "error", .ok d => errs := errs.push d
      | _, _ => pure ()
    | .error _ => pure ()
  return errs

/-- Write the single nonce-framed result line to the REAL stdout (called only
after `withIsolatedStreams` has restored the stream). -/
def emit (nonce : String) (r : Result) : IO Unit := do
  let out ← IO.getStdout
  out.putStr s!"{resultMarker}::{nonce}::{r.toJson.compress}\n"
  out.flush

/-- Elaborate `source` with the real frontend under isolated streams, returning
the captured report and the resulting environment (`none` iff the frontend
reported errors). -/
unsafe def elaborate (source : String) (fileName : String) :
    IO (String × Option Environment) :=
  IO.FS.withIsolatedStreams
    (Elab.runFrontend source {} fileName `AxiomAuditScratch (jsonOutput := true))

unsafe def mainUnsafe (args : List String) : IO UInt32 := do
  match args with
  | [filePath, declStr, noncePath] =>
    -- Read the harness nonce, then delete its file BEFORE touching the
    -- untrusted source, so compile-time IO can never read it (even reading
    -- `IO.getArgs` yields only a path to an already-deleted file). Only a
    -- result line bearing this nonce is trusted by the harness.
    let nonce := (← IO.FS.readFile noncePath).trimAscii.toString
    try IO.FS.removeFile noncePath catch _ => pure ()
    let declName := declStr.toName
    try
      Lean.initSearchPath (← Lean.findSysroot)
      -- Required before `importModules (loadExts := true)`: the frontend runs
      -- `initialize`/module init code while importing mathlib.
      Lean.enableInitializersExecution
      let source ← IO.FS.readFile filePath
      let (captured, envOpt) ← elaborate source filePath
      let r : Result ← match envOpt with
        | some env =>
          let declFound := env.contains declName
          if declFound then
            let names ← runCoreM env (Lean.collectAxioms declName)
            pure { declFound := true, errors := #[], axioms := names.map (·.toString) }
          else
            pure { declFound := false, errors := #[], axioms := #[] }
        | none =>
          let errs := extractErrors captured
          let errs := if errs.isEmpty then #["frontend reported errors"] else errs
          pure { declFound := false, errors := errs, axioms := #[] }
      emit nonce r
      pure (0 : UInt32)
    catch e =>
      emit nonce { declFound := false, errors := #[toString e], axioms := #[] }
      pure (1 : UInt32)
  | _ =>
    IO.eprintln "usage: axiom_audit <file.lean> <fully-qualified-decl> <nonce-file>"
    pure (2 : UInt32)

end AxiomAudit

/-- Entry point. `unsafe` because `Lean.enableInitializersExecution` and
`Lean.Elab.runFrontend` (needed for mathlib-importing sources whose modules run
`initialize` code) are `unsafe`. -/
unsafe def main (args : List String) : IO UInt32 :=
  AxiomAudit.mainUnsafe args
