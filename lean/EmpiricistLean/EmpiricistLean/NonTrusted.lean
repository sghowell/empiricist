/-
Copyright (c) 2026 Sean Howell. All rights reserved.
Released under the MIT license as described in the file LICENSE.
Authors: Sean Howell
-/
import EmpiricistLean.Basic

/-!
# Non-trusted fixture module

A trivial committed-but-**non-trusted** module carrying no mathematical content.
Its sole purpose is to be the fixture for the import-trust security test
(`test_nontrusted_empiricist_module_still_rejected_by_import_trust`): staging its
compiled olean onto the frozen trusted-lib directory must NOT make
`import EmpiricistLean.NonTrusted` acceptable to the FORMALIZED gate, because it is
deliberately excluded from `_TRUSTED_EMPIRICIST_MODULES`. It is committed (so its
source and olean are on the residue allow-list) but never trusted.
-/

namespace Empiricist

/-- Trivial marker; this module exists only as a non-trusted-import test fixture. -/
theorem nonTrustedFixture : True := trivial

end Empiricist
