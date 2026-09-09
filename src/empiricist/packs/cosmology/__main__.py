"""Stopgap driver: certify, promote with, and reverify by a cosmology pack verifier in a
research repository.

On this branch core's `claims certify-verifier`, `claims promote` and `claims reverify`
resolve only command verifiers declared under `claims/verifiers/` (M24a Task 2, the
pack-resolution step, has not landed). Until it does, this module hands the pack verifier
*object* to the same core functions and nothing else: `certify_pack_verifier` runs the
golden suite and stamps the repository registry; `promote` still checks the stamp, the
standing, the lock and the receipt, and runs the verifier itself. A declaration of the
same name in the repository shadows the pack verifier and is refused here (the research
repository is the authority on what it runs).

    python -m empiricist.packs.cosmology certify --repo . cosmo_p8_s0
    python -m empiricist.packs.cosmology promote --repo . --id P8-0 --level CERTIFIED \\
        --verifier cosmo_p8_s0 --evidence problems/P8/certificates/s0-identities.json \\
        --receipt <receipt id>
    python -m empiricist.packs.cosmology reverify --repo . [--id P8-0]

Delete this module when core resolves pack verifiers.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from empiricist.claims.model import ClaimSchemaError
from empiricist.claims.promote import PromotionRefused, promote, reverify
from empiricist.packs import certify_pack_verifier, installed_packs, resolve_pack_verifier


def _declared(repo: Path, name: str) -> bool:
    return (repo / "claims" / "verifiers" / f"{name}.yaml").is_file()


def _refuse_shadowed(repo: Path, name: str) -> None:
    if _declared(repo, name):
        raise PromotionRefused(
            f"{name} is declared under claims/verifiers/ in this repository; that declaration "
            "shadows the pack verifier -- use `empiricist claims` for it"
        )


def cmd_certify(args: argparse.Namespace) -> int:
    _refuse_shadowed(args.repo, args.name)
    stamp, problems = certify_pack_verifier(args.repo, args.name)
    if stamp is None:
        print("certify: FAILED")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"certify: {stamp.name} v{stamp.version} [{stamp.binary_hash[:12]}] stamped "
          f"(pack {stamp.pack})")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    _refuse_shadowed(args.repo, args.verifier)
    v = resolve_pack_verifier(args.repo, args.verifier)
    if v is None:
        raise PromotionRefused(f"no installed pack declares a verifier named {args.verifier!r}")
    c = promote(args.repo, claim_id=args.claim_id, level=args.level, verifier=v,
                evidence_path=args.evidence, receipt_id=args.receipt, n=args.n,
                coverage=args.coverage)
    print(f"promote: {c.id} -> {c.level} ({c.standing})")
    return 0


def cmd_reverify(args: argparse.Namespace) -> int:
    objects = {
        name: factory(args.repo)
        for m in installed_packs().values()
        for name, factory in m.verifiers.items()
        if not _declared(args.repo, name)
    }
    outcomes = reverify(args.repo, claim_id=args.claim_id, verifiers=objects)
    for cid, out in sorted(outcomes.items()):
        print(f"reverify: {cid}: {out}")
    return 0 if all(o == "re-verified" for o in outcomes.values()) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m empiricist.packs.cosmology", description=__doc__.split("\n\n")[0]
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("certify", help="run a pack verifier's golden suite and stamp it")
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("name")
    p = sub.add_parser("promote", help="raise a claim's level by running a pack verifier")
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--id", required=True, dest="claim_id")
    p.add_argument("--level", required=True)
    p.add_argument("--verifier", required=True, help="a pack verifier name (cosmo_...)")
    p.add_argument("--evidence", required=True, help="repo-relative certificate path")
    p.add_argument("--receipt", default=None)
    p.add_argument("--n", type=int, default=None)
    p.add_argument("--coverage", default=None)
    p = sub.add_parser("reverify", help="re-run pack verifiers for STALE (or one) claim")
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--id", default=None, dest="claim_id")
    args = parser.parse_args(argv)
    try:
        return {"certify": cmd_certify, "promote": cmd_promote, "reverify": cmd_reverify}[
            args.command
        ](args)
    except (PromotionRefused, ClaimSchemaError) as exc:
        print(f"{args.command}: refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
