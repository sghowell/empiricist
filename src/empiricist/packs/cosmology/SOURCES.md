# Sources of the `cosmology` pack

The pack wraps death_and_gravity's certificate replay checkers. Everything under
`checkers/death_and_gravity/` is **copied verbatim** from the research repository
`~/dev/research/death_and_gravity` (branch `empiricist-claims-import`), laid out exactly
as there, because each checker locates its pinned certificate, its prior certificates and
the source files it hashes into the certificate relative to its own `__file__`. A replay
checker's value is that it is the code the certificates were produced against: nothing
here is edited, reformatted or "improved". `vendor.py` performs the copy and rewrites the
manifest section of this file; the origin commit is recorded there.

## The checker contract

Every `<package>.verify` module exposes `REPORT` (the pinned certificate path),
`build_report()` (an exact, read-only replay) and `validate_report(expected, actual)`
(raises `ValueError`, `KeyError`, `TypeError` or `AssertionError` on any difference). The
research repository runs them through `tools/empiricist_check.py` (exit 0 on an exact
reproduction, exit 3 otherwise); `replay.py`'s `ReplayVerifier` runs the same two calls on
the bytes of a committed certificate and maps them to PASS / FAIL / ERROR.

The vendored packages are top-level names (`p8`, `p8a`, `p8a_radiation`, ...). `vendored.py`
serves them through a meta-path finder ahead of `sys.path`, so the code that runs is the
code the verifier identity hashes, whatever `PYTHONPATH` says.

## Contract adapters (`adapters/`)

The P8(b) base chain's checkers, `p8.verify` (the S0 anchor) and `p8.verify_all` (the
complete chain of six certificates), predate the contract: they expose `CERTIFICATE` /
`report()` / `check_certificate()` and `ROOT` / `derivation_report()` / `build_reports()` /
`check_reports()`. `adapters/p8_s0.py`, `adapters/p8_s1.py` and `adapters/p8_chain.py`
present them as `REPORT` / `build_report()` / `validate_report()`, calling the vendored
functions unchanged and comparing exactly, as the checkers' own `--check` modes do. The
chain adapter accepts a certificate iff it equals one of the six rebuilt reports. These
adapters are the pack's code (hashed into the identity as the checker module); the vendored
`p8` package is not touched.

## Goldens

- PASS goldens are the pinned certificates themselves, read from the vendored tree.
- FAIL goldens under `goldens/<verifier>/` are mutated certificates: the research
  repository's own fixtures (`claims/fixtures/<package>/fail-mutated*.json`, which set
  `status` to `MUTATED_FOR_EMPIRICIST_FAIL_FIXTURE`) where it declares a command verifier,
  and mutations minted by `vendor.py` for the checkers it does not (one certified value
  changed; the file says which). A FAIL golden fails *through the checker*, never through
  malformed JSON.

## Vendored files

Origin: `~/dev/research/death_and_gravity (branch empiricist-claims-import)` at commit `e04bb6cf1f6f63da59ec9e2d2d8f26b57b6d0c21`; copied by `vendor.py` into `checkers/death_and_gravity/` (171 files).

### FAIL goldens

- `goldens/cosmo_p8a/fail-mutated.json` <- `claims/fixtures/p8a/fail-mutated.json` (sha256 7aa8e04ca35b021888c1ea4a8baf32635bfe78f1d56eb8aa89a7aca954f5bcb9)
- `goldens/cosmo_p8a_asymptotics/fail-mutated.json` <- `claims/fixtures/p8a_asymptotics/fail-mutated.json` (sha256 ce6fff9e2a6211af4a409fe25269aa38c55328dc33422fc3f54ee5003fd03fc0)
- `goldens/cosmo_p8a_backreaction/fail-mutated.json` <- `claims/fixtures/p8a_backreaction/fail-mutated.json` (sha256 8e51426c921063b5a16f6f639a1d90dc877bb7ac7d67cb24154a4434d31449c2)
- `goldens/cosmo_p8a_radiation/fail-mutated.json` <- `claims/fixtures/p8a_radiation/fail-mutated.json` (sha256 6c1881f4295d7b0c2ff573bebe53842d26edf33d58fe585066e71aa21d47708a)
- `goldens/cosmo_p8a_reference/fail-mutated.json` <- `claims/fixtures/p8a_reference/fail-mutated.json` (sha256 3e0e2b258a081298b55da3bf2a85c0f07c9045c39b68df6d76ba7799ebe4a066)
- `goldens/cosmo_p8a_remainder/fail-mutated-status.json` <- `claims/fixtures/p8a_remainder/fail-mutated-status.json` (sha256 722657218240e4ed69ee53aef6337ed7ec6a729d910b87a21f4dec16d9a73d1c)
- `goldens/cosmo_p8a_response/fail-mutated.json` <- `claims/fixtures/p8a_response/fail-mutated.json` (sha256 b4c1c5ed31417d269277ea3984e80ff3313d5be50f7878b664880af4de346e7e)
- `goldens/cosmo_p8_chain/fail-mutated.json`: `problems/P8/certificates/classification.json` with `counts/M0/E` set to `11` (sha256 1eaef88e2ca5d130b54a6e16807f119d0ef57dfd82112a6b4d9a516c92be8439)
- `goldens/cosmo_p8_s0/fail-mutated.json`: `problems/P8/certificates/s0-identities.json` with `benchmark_Hdot0_pinned` set to `'1/376'` (sha256 6e435ce4d9ff128b10411cfd5265d004275f303f10a370df6594130616d475d4)
- `goldens/cosmo_p8_s1/fail-mutated.json`: `problems/P8/certificates/s1-derived-action.json` with `exact_residuals/ADM/__first__` set to `'1'` (sha256 918f8d316d2b598f6e1692c0cebb1411e12e68e6c43673bba978233e5c8f36ad)

### Files (path, sha256)

- `problems/P8/FORMULATION.md` 73dd18f7a4b56a0205f9fbc6a4b09b213a3c280b3f0274414a255635b04e2b09
- `problems/P8/README.md` f4cbd40df05d1504aac9a493052ffeba504e73db5c36a6e4a886f1b4865aeeee
- `problems/P8/a/FORMULATION.md` e0e4bd0d9b04213567ded0f8e57b48b0de44833c205c072b4610a6d12c75ed45
- `problems/P8/a/README.md` 00c0d6651f4d051a90e39a79e954f6d5e0de5108c5dfaae75163b510363556ae
- `problems/P8/a/applicability/FORMULATION.md` 429676d3f8192cb1009d71ca9a9cafe7370223b0be2c0ae2cd3f7a225b97fe80
- `problems/P8/a/applicability/README.md` a0e12daa207ad9358ba024ab246de82ecbcaf4831fa461db2a50f012e121327d
- `problems/P8/a/applicability/certificates/radiation-qsei.json` 1a7369c03a25787c04fac0bf38189206e5331e43d3e48306a9ebb187763e9ed2
- `problems/P8/a/applicability/notes/derivation.md` 8b809ddc958eee442ce78ffa6b27971f60656127788e0d14041c2ee17ea790ba
- `problems/P8/a/applicability/notes/sources.md` 439333b8bdf36b794b29e6c444359179c088e72311283e035a16e2d3b9e3c356
- `problems/P8/a/applicability/reference/FORMULATION.md` 8eae6abbfdacdf538cf542c3e71478824140ead5ea699e9f0d41d9b6af85ae95
- `problems/P8/a/applicability/reference/README.md` 985925efd91d8bbee5f830de4fe1852b7fa968c6ad6c9216de7648776d13e85d
- `problems/P8/a/applicability/reference/asymptotics/FORMULATION.md` 0891f0a33a5c76eef3113e2667acaf726d64094674f5d500c651e502065a958b
- `problems/P8/a/applicability/reference/asymptotics/README.md` 5be946c621e004a7439f7200fa90541bbb289429ce68aa4b41577b41a2b7aac8
- `problems/P8/a/applicability/reference/asymptotics/backreaction/FORMULATION.md` dd3a0f1521c4234fee47f296768061cdd1d97e13d915c84967151983f27c64d9
- `problems/P8/a/applicability/reference/asymptotics/backreaction/README.md` e9d75a59e12ef1e12f17c595507bb9495836d6d5c4227bfb27b6dbd66d7b0d89
- `problems/P8/a/applicability/reference/asymptotics/backreaction/certificates/radiation-backreaction.json` a7e1766a16778920c5784b9c52f997497a6e22259c48d956c8ca50ca60770930
- `problems/P8/a/applicability/reference/asymptotics/backreaction/notes/proof.md` 64f5e3c58433d655ffe53cd5dfc31307a2b24fa3cc984578e796a55576c11fff
- `problems/P8/a/applicability/reference/asymptotics/backreaction/notes/sources.md` a70b6e4b58b38f8b2900fc2493e0dadafe2b00f78a7d4dea9be23dd46fba6abb
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/FORMULATION.md` 6d6b9763d4c8ead9f34e522d34a531e3deb8e849bbec57f7f9be2cda5f7cc319
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/README.md` aef086df80989a5df867aa52c773f3511ce661e001418baeeedbecde432b5c06
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/certificates/radiation-response.json` 1101c2c2977716ef3bcf452ab02f69abb91ba43c7720df0920384099a1c1e868
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/notes/proof.md` 8cff5d0a71bc5af87600328a88deeacc2608eb9f0320004ab2cf45196d6c8398
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/notes/sources.md` 77e075195483e0f2a659369453b03ce3297f90d428425b40724407e9bd55c48c
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/FORMULATION.md` bb415f07620ef7a0119cf94397cb1384f993109cd11309fe0e112924cf216eaf
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/README.md` 237bd4c2ca5ac1360a4c3d6ee0cd235c009cf43153c386c811c7afffe84140e5
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/certificates/radiation-remainder.json` cc4ec02bcb23e0ef01d0fb58ad4b95a3bb602a5bbbfc6871d044b2a09a78e963
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/notes/proof.md` 1de4b521475f7f7a0351255198523fed745adee91896ab955544e483ecc21025
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/notes/sources.md` 840140d97eb09d333dd338bdb768759ea6a6067a25de563f051b3a707dfbfbc6
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src/p8a_remainder/__init__.py` 445e3bcbaef2e7237be4d5eb1d586ed01fe2b4136705e4a03bba0f27ba31e138
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src/p8a_remainder/geometry.py` da3ef861345571d4a385163adfccb52c629cf8e7eb31add3c2280298cd84538a
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src/p8a_remainder/independent.py` 1c780c415e8886655ae9edce8affc6fc983890a59f8a0c26eecbaa82dd49787c
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src/p8a_remainder/kernel.py` e3b6c036d569220b92eb919dda9544b820582f2f4724d8062590ffd282b78299
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src/p8a_remainder/mode_bounds.py` 17a95d9d2604a31304dfa725429c5d8ec4ed92868c223b33c511fcd2c9c5134e
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src/p8a_remainder/stress.py` d6e55f4312a877eaa5b88af2685946c22945fb20ee31f3a5d8520794f8ea6e74
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src/p8a_remainder/verify.py` ead0aa7554986474cbdeb58614674943f7f5487c170c19ca37869bede737114d
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/tests/conftest.py` 9564c7ee5ab1f018ca3e060e3862ec5aaaf73b706c3b88170f77c3ec5ba32b67
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/tests/test_remainder_gelfand_dikii_audit.py` ced02dbcdccddb1d0d85431484356059abd5935f122fe6776dcfc6447e981390
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/tests/test_remainder_geometry.py` 89c7dcc04d646cc7fac0460cb574783d3f3dab78a313ff5c75cfd61c31f3aab8
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/tests/test_remainder_modes.py` abc9bf366b6bea5b202ad64fe4bba35bd2ae450c1567d5e9c994ec7a89b42e71
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/tests/test_remainder_report.py` 20df5927bf300aba5b9aa32f2c505e6e1c619ac592e859e03ad9797b3ee23719
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/tests/test_remainder_stress.py` 00b14a6de2b18cdf239d27293db394324a8bfc4045960758d825288be6967bbd
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/src/p8a_response/__init__.py` ca8f009b7a2043f48e37c7498c735de9bd885c6dba796b64267d9c2b1bba11e7
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/src/p8a_response/defects.py` 695c9391ac47844f44f1c57a07eb89ee4b52a82c4d48c83bed7924cfb702aa81
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/src/p8a_response/independent.py` 84623b5e705f92f4f9d7fcc5e6154590619e93ba30eeea1a9d07dae6c8fefabb
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/src/p8a_response/kernel.py` 1a79571d0d2cc0aed28927a9e24618de0e7e3fa3582bdff7d39177c0dd1c89d2
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/src/p8a_response/preparation.py` 5cc645951d6e77967e933e09c657ff2aeea754642c37b793a72844dfcc6135b1
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/src/p8a_response/response.py` 17c4fe87f526f807fdcd23c5dfe9ccafe6f3a23fa14dc461dcda29765daba3b9
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/src/p8a_response/verify.py` 2f5e34bcfbcd5c3561c6c683b02cd1642ce187883d08c8a16dc8dc162a1d0e97
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/tests/conftest.py` 012d88037aeecc7d17e58aecfeb5a33a5127b092579fc1d4e92f036f868500cb
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/tests/test_response_geometry_audit.py` 88e3de84d5dabaa4f10fc64e6ed51a8557896b79d051e53e41fc8c2c9185bc81
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/tests/test_response_kernel.py` 1c450e1992635ab99ece51cde6abcfeab0b2764eb8ddeb1393c619ffa5d4cf3b
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/tests/test_response_preparation.py` dd44379fcd21ee1e45f24ff691b041b804c0ace5ba86e6de3270f80fa4b34e62
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/tests/test_response_report.py` 3484b083dcbb9c2f2d610691369901953dd2ab30e000ea3cd9d4caa82142cf1e
- `problems/P8/a/applicability/reference/asymptotics/backreaction/response/tests/test_response_stress.py` cef927653e9b3b88b2b8ecee0414f483f38d0ab0ef8693126e4ddde4c7267e06
- `problems/P8/a/applicability/reference/asymptotics/backreaction/src/p8a_backreaction/__init__.py` b0ecbea9f2591158606c52713692b4938f21749c83f70efd332870d09659f010
- `problems/P8/a/applicability/reference/asymptotics/backreaction/src/p8a_backreaction/bounds.py` a1146eb934221014792fe3682a792c23c33c80d9113bec2564a3d03910da02b2
- `problems/P8/a/applicability/reference/asymptotics/backreaction/src/p8a_backreaction/dynamics.py` b8c5fab4eb94d2f1e9eb2a3d28da104c6c0de46cc78aee0f05f7f94d06e4fde2
- `problems/P8/a/applicability/reference/asymptotics/backreaction/src/p8a_backreaction/independent.py` 6d2804aae08dc6e31a57ffb4c3d24532517c83ba4cb524d73d5590177224a9ec
- `problems/P8/a/applicability/reference/asymptotics/backreaction/src/p8a_backreaction/verify.py` 37e3e29f6978f0eaecf3b87a802fc0909f545529082866a8cc31b5a43eae1b9e
- `problems/P8/a/applicability/reference/asymptotics/backreaction/tests/conftest.py` 1624f5580712ca83ea40bcc2d0478c3716ec7ff6285171cdd923413606e978e5
- `problems/P8/a/applicability/reference/asymptotics/backreaction/tests/test_backreaction_bounds.py` 3c7c69b7a5e28573640d44f505eacc817d43d84673b85d9f5a556bdeb07ba2a7
- `problems/P8/a/applicability/reference/asymptotics/backreaction/tests/test_backreaction_dynamics.py` 06fbc5ad4205704560296c5e1d3e225ab3e1efe1fbe6ccbe035f4bbd415dc488
- `problems/P8/a/applicability/reference/asymptotics/backreaction/tests/test_backreaction_report.py` 10b3bec7861a38a3d221102228161491be652052e84aebf9036f9b600b837ffe
- `problems/P8/a/applicability/reference/asymptotics/certificates/radiation-asymptotics.json` 05d8484a9f39cc4c47a6a6441d7ab589aea78ca449773bdc3cad72bd42dc5eec
- `problems/P8/a/applicability/reference/asymptotics/notes/proof.md` e11fd7bc4105dca34295af3e6946c55748ade183128b85dbf7c4606763aa7231
- `problems/P8/a/applicability/reference/asymptotics/notes/sources.md` 83c744846f42325a96f06f51ec8cf586696c6d98ffe4c0cbefed726af797f870
- `problems/P8/a/applicability/reference/asymptotics/src/p8a_asymptotics/__init__.py` e73217cb21af6779a95f411cdd02314840b9663d7f1fb40a80fd3600af7fb5e9
- `problems/P8/a/applicability/reference/asymptotics/src/p8a_asymptotics/bounds.py` 7ea18693f592a88528497070f71dab8ebf1445599821e3108f8f527540c9efef
- `problems/P8/a/applicability/reference/asymptotics/src/p8a_asymptotics/extension.py` e739a0226630118758c61622014c355cf4b57d122609b1595845f97d893eab32
- `problems/P8/a/applicability/reference/asymptotics/src/p8a_asymptotics/independent.py` 3074726f48311aad7e62977f45442286b525103fcc11bc596ee33db2c6f184ac
- `problems/P8/a/applicability/reference/asymptotics/src/p8a_asymptotics/scaling.py` f8c2dbb28109f11b5776d9999d9d539e2a5b389915713c079ecf447b546a361a
- `problems/P8/a/applicability/reference/asymptotics/src/p8a_asymptotics/verify.py` e51261c0d65842acec3f3735b672dbbac59f1e09e6fa10bd4c954bf7459c4038
- `problems/P8/a/applicability/reference/asymptotics/tests/conftest.py` 33d8421e621ec5bdcf440cd262477c5a6d8aa89670cfdc7ee179856bba35d1a8
- `problems/P8/a/applicability/reference/asymptotics/tests/test_asymptotics_bounds.py` b6fab17afe8e0254551edbe2f7db5f9de33e3162153f1f5bd8586a51c482146b
- `problems/P8/a/applicability/reference/asymptotics/tests/test_asymptotics_extension.py` 64d80ac29934c2f9d90e2a475be76ac5070bb6e0d8f56e54cb42efe0737f9d36
- `problems/P8/a/applicability/reference/asymptotics/tests/test_asymptotics_report.py` e17ff764dd7aa9370d147b4d6acdfcd720f1a27b81c34d1d173dad881d281b44
- `problems/P8/a/applicability/reference/asymptotics/tests/test_asymptotics_scaling.py` 784c91e883441ab07b5fa7b7030d95ad8f5face2910947d19ead78733b7adbb4
- `problems/P8/a/applicability/reference/certificates/radiation-reference.json` dc762112cdd2a5c0330f12d8bf157e27f5bae10d31cafa3b877cbce6eaa92b31
- `problems/P8/a/applicability/reference/notes/derivation.md` 6093848a52e4a5d3786c73f3cc9d9ca76f533927adfa4729ffd04e93f1cc2a46
- `problems/P8/a/applicability/reference/notes/sources.md` a76f5f48880c6bb1c30af640a0114c343c12fcdb6017519c55f0c8c9e720bd03
- `problems/P8/a/applicability/reference/src/p8a_reference/__init__.py` 1718740c46a43ee6e68d8e1140df7caa11b707a5e7b0ec003da465ac854d6d63
- `problems/P8/a/applicability/reference/src/p8a_reference/bridge.py` dd32634935f6277bd900204271d5df3dac19ff398f39c0ab58f5b728906bd461
- `problems/P8/a/applicability/reference/src/p8a_reference/independent.py` 81d8d04a0574f0c4085194bb0bf5283897659112cf3c26ec4488f6144c7b019c
- `problems/P8/a/applicability/reference/src/p8a_reference/stress.py` 46b334c85855a940b3802182bc54dfddc8e7bcdc993e0867defe73fb6fb1c830
- `problems/P8/a/applicability/reference/src/p8a_reference/verify.py` 6b06da5ae4b3158016c2f8a5dfcdc755f172aff2ae8bf016069593956855162f
- `problems/P8/a/applicability/reference/tests/conftest.py` e80bab489e0b782a8e2c754ddfa58f550e38d49145b8cff93ee53891deec2f98
- `problems/P8/a/applicability/reference/tests/test_reference_bridge.py` a75a48c09ad8206075444349f3c48fb91f0c00d46b6a850d687accb42bedaa73
- `problems/P8/a/applicability/reference/tests/test_reference_report.py` 9ca41258eac9ec35851281e49ac9e43d617bcdc018c4ceb4470b2fd4bfaf64ed
- `problems/P8/a/applicability/reference/tests/test_reference_stress.py` fa292097d2390eb73cbf26e6dc72c8d13cc57d2d59a2c0c343a7e9f75c337fcc
- `problems/P8/a/applicability/src/p8a_radiation/__init__.py` b1d9605705c4dfcfd6c2fa6d4888ff5c441dda78a89216f0f5421778dc4ae85b
- `problems/P8/a/applicability/src/p8a_radiation/functional.py` 22e474981be78c44b894a4a9833f8789c512cf28a6a50325871aa3e1d31aeecb
- `problems/P8/a/applicability/src/p8a_radiation/independent.py` 3294292be19eee08e7da1b0694172ff86eb945eaddbed2d93bd1a22cda9864a2
- `problems/P8/a/applicability/src/p8a_radiation/radiation.py` 74e160fbaef94035cd409b3140abce5a38c707a1bcfb23138c34e2e9faa21dd3
- `problems/P8/a/applicability/src/p8a_radiation/validated.py` 10f9b3269e4943d13b44a2a342d9caea028a376b82b485c90cf8617a35bf38a0
- `problems/P8/a/applicability/src/p8a_radiation/verify.py` a64f6a8fe8e8154491da913d895fdb77b9d60ed3b321ae8d144d406c72a60956
- `problems/P8/a/applicability/src/p8a_radiation/windows.py` 69edf84c8508c36b46c0171208eff6c8db9db27c552b37c58324ed5709e42093
- `problems/P8/a/applicability/tests/conftest.py` f8ccc83c080622b025666fb6125bf4679e50df1f884e0de683aab609daf4d10b
- `problems/P8/a/applicability/tests/test_radiation_derivation.py` 96fcaece50da1506e6ccd9a0a0978414f1ff247557d0b4c08fe1f29af19c9719
- `problems/P8/a/applicability/tests/test_radiation_report.py` e022bcd463f7ea84c5406bca54d78e8e90048fe081a16527ab9f18a746b25764
- `problems/P8/a/applicability/tests/test_radiation_windows.py` 8e34d21f211fe4fe5c4c19a9b6234efaa3ce984885fb5683a3117e2352231a7d
- `problems/P8/a/certificates/focusing.json` f719c98068848003e296260d3ff6b03d32acad40662b9c9980f61c39175f209e
- `problems/P8/a/notes/focusing.md` 98bea029773ac2382da256177be0a8909f14e013e75242f1071f4d53e2acbc96
- `problems/P8/a/notes/sources.md` ea521f4fb6d3097b5f8f4e1c91a16da2d59500c564c5f22bbd933ff6d26d46b8
- `problems/P8/a/src/p8a/__init__.py` cbaa4156bb86ae9e2320ecbf99503486cb3eafcc826858967846a9ad7b623570
- `problems/P8/a/src/p8a/focusing.py` 6b1aae949b9e2f8445d4e01e95830826fa275c4853a394b166483e5c90339015
- `problems/P8/a/src/p8a/geometry.py` 22a0b47d237a81770658e2485d61c40e6fbba4eb32289d5f2eae1d052b8089fc
- `problems/P8/a/src/p8a/independent.py` 3601d87c7276a6772c02d6a6406f20d0250f5f71296e5b75b4576eeb0d3d350e
- `problems/P8/a/src/p8a/partition.py` e916c069908fce9565c90e4e852f198c10b008fc0059b32c154bb7f637511ae4
- `problems/P8/a/src/p8a/validated.py` b2a91fc87b2cd398e28bebac458077ad692fb4fa6862dc7de3cf32308e80c463
- `problems/P8/a/src/p8a/verify.py` a5f620920c3d96d8eefe77e829e5b648eb7aae626fd9ca8b58d759940ac8f066
- `problems/P8/a/tests/conftest.py` 7a53035ca4de6b2b74d4e2af6be557da2016abd76d6d1b9f30df025776701eb9
- `problems/P8/a/tests/test_a_focusing.py` 668e36568cf9aa99603cd9ca96e5d59988eb316ed6cd94886841984b7648eda8
- `problems/P8/a/tests/test_a_partition.py` 224146f76e3247cd5bfd5ef45b6cc5dac96d65e036d9858661989f7f7dda3803
- `problems/P8/a/tests/test_a_report.py` 1c38f2ad8b4ce80234057492f006d0889cf9d1d18b72101bcb6e6c891b6ff040
- `problems/P8/certificates/a25-regression.json` da71a4a1112880bb78e20f70e26b82e8e5592f8578b5a0d9e5ac32cbe6bccdb7
- `problems/P8/certificates/classification.json` 4e82b45d3d1daed0a5e4698f1dd39fa51e2eb09b6efcf3cf5caac3a12d45dec8
- `problems/P8/certificates/s0-identities.json` f5e689c8b5210cbcc67df1e10cc5a33d4132cae64804990c0878984a725ea5ae
- `problems/P8/certificates/s1-derived-action.json` 86aae6bcd32873fceba7c95114c1862ba018aa333ff9837597b8b93780b01554
- `problems/P8/certificates/witness-C.json` 87614638d5aa203d4975f38754657cf86e63be7c82d58aa30196656c68a9e56f
- `problems/P8/certificates/witness-CD_matter.json` caf8c8e688a7565b9d00f921c099a28da00f97522ed26ad182a8227eb80cd4dd
- `problems/P8/certificates/witness-D.json` 85439806078f2c88bf5aadd87794536269ad1ff16fa10fc7078732700f30d7de
- `problems/P8/notes/WORKING.md` ba9411b20c6f4fd0b82430fefc086d50919d8dc24c5d1fc024ada5800b37b1a5
- `problems/P8/notes/literature-digest.md` 7c1d6a20cfebb3097ef7365f712f9788414f00284db5a6cdd1677efa74e59e49
- `problems/P8/notes/s0-opening.md` 9d6980e9724acb4f3085587b90d93a860ac9f90a2b2002b3b513ed67bb4e59b0
- `problems/P8/notes/s1-derived-action.md` 98199bc728d8f3814e872c7d8854bbd1c091c041b2d1b3a5806ac5b4a99035c9
- `problems/P8/notes/s2-benchmarks.md` 84bb7c3e16e03418c97b09962a18115249898762b57e3398a9f5473dec102161
- `problems/P8/notes/s2-rational-witnesses.md` af742957982ae1197fd15f6676a201e312a0b7e40e082de9cc291f9b78664ef1
- `problems/P8/notes/s3-classification.md` 484d96d7aa3c737a76091e3d5b2e10385ed56e3a5cb74054497fb63a0be02611
- `problems/P8/notes/s4-review.md` 7b653e2eb475d7e930ae92c1e30d6de6004c6ff229fc78f66eb153c591363d6f
- `problems/P8/src/p8/__init__.py` b962dfaf86febf70dc0de1a8dd392ab9db977cba0e09648080f3536ab8e3c0fd
- `problems/P8/src/p8/a25_certificate.py` d9f8c6a73840fd6a2d7bdbd47349b6a9fa18aa578ceb02ec7f2c8f389da85839
- `problems/P8/src/p8/adm.py` 0ee205adc3cba5f6ebfcb046e647ef7790e3890d3f0d7ab3d3462500aeaf9f02
- `problems/P8/src/p8/benchmark.py` 6d291b597aaa75175e969eea98cf07036318acab6ba3d632caf59501c9295b86
- `problems/P8/src/p8/candidate_cert.py` bd5f8d43eb6bef4fa5ab0f9dd9c02e0239d9f10fe22594149829df3e75f7fd26
- `problems/P8/src/p8/coupled.py` 12671e2b1baaceb1ca1b01663c02d5ed2ffc753240533fbdae4d095859d8c194
- `problems/P8/src/p8/covariant.py` fa69b61732a1245541ff53e99e0c999b43559d6b783fd5d639604c73f1cd249e
- `problems/P8/src/p8/exclusions.py` 735c7da7bd3f00e4d31d9bce6946b799e13f02c8c48780db2ea1c0232b21b79b
- `problems/P8/src/p8/gamma.py` 5e411e649be38bcdea745e8602840fd1e1fe774608798a6948ceb88dbfe35bfe
- `problems/P8/src/p8/horndeski.py` 2d7feaf0c0b04a5501db4af82e5147214f9bc8636fa8778a20cb5518b7ffa6cb
- `problems/P8/src/p8/independent_sigma.py` b198cf82356defe50e5dd866ff4246382ca64fcad41a0bb4d4fce95365fe1ef0
- `problems/P8/src/p8/jets.py` 6cec1342446622ece78fa53fe6f8cec8e625edcc0b971c187885d9023dc368b7
- `problems/P8/src/p8/matter.py` bd4328057bb3c36e03eccfcd7c734fd8f7e2be600155607bd37b50b21347916b
- `problems/P8/src/p8/quadratic.py` e9b72be7a5aa0bc3e7a99b6e29513b5c68db4e0f3e29aa0019f70db7fc2b4fce
- `problems/P8/src/p8/rational_candidates.py` 009a2a8f9b1f0c171fcc1af0eaffbf8877a6e801d9987d5af4d5ec9fd32002ba
- `problems/P8/src/p8/regressions.py` 9de645bb5f4dbea50f6e9fda106db27fa79323a8beb533203a988665eefde5c7
- `problems/P8/src/p8/signs.py` a1226b67f7b483015a2c459eecfefebd58fafc0dce6441ad7a2ac4d5009ed306
- `problems/P8/src/p8/strong_gravity.py` b30a9dc2432bc6c019f0d34ffa6817a376962e32425f64e8ea65081927a3544a
- `problems/P8/src/p8/tensor.py` 3bc4a2345e30c3ad93960532b011eb65e65b637e15c34ffc7ac75f355c36c1cc
- `problems/P8/src/p8/tilted_hessian.py` 6d981ad4f7210ff60ea1c916c7764dbda12e4fda9f2016a946db290abb62b145
- `problems/P8/src/p8/verify.py` ff7b3fc4eda66a7835d99eef3958f710fdb295dbccbcd9f91fefeac65b03c035
- `problems/P8/src/p8/verify_all.py` 152aecb85d9cba01fa829b8870400e0613820f0a0326503d8ad821492273147b
- `problems/P8/tests/conftest.py` 8224029389c1b92c9a368e61859d786b9240cd6851be937489350e0a08c33296
- `problems/P8/tests/test_a25_certificate.py` 2fb9806b7e9e303409cbc7f5987fd3789a820c7d5711dc462682130be6f299e6
- `problems/P8/tests/test_benchmark.py` eea3917844475b2f866c4418a7c169e208750a479da596eac1f6c64f3df6c7c3
- `problems/P8/tests/test_candidate_cert.py` 6da7ba085177f5af11f404e603c31e44f699befac418b932619f022521b2813f
- `problems/P8/tests/test_certificate.py` 910c883ce921344d3f88b7fb6d7bf1898d7a98ab189d90ab9f1b390d0c8d8412
- `problems/P8/tests/test_complete_chain.py` ef74b74348f6a92d314da9019558a32f538f04e8a7d5f6e4b40e8ca1591ce36a
- `problems/P8/tests/test_coupled.py` a5f21daf5a774fa15221dd6d01c304528fd3172d27b4972511a7ffb122edc0d2
- `problems/P8/tests/test_covariant.py` c702b1c712686d917b48547afc819b3bee822e54daeb7c5a4e67af6676ca3f9e
- `problems/P8/tests/test_exclusions.py` 4014ba75b80221ba1d1a676bf0842dc8c7bd8e0af96bb40dc54bc377e89a785a
- `problems/P8/tests/test_gamma.py` de948d96dc9e2ae3f1cc8ec77f52910c2eb3a3234e757d19376b8bb59cefe02d
- `problems/P8/tests/test_horndeski.py` 72f75800215badbcd53a79d3830ff27ca55078b3d0012f9e7f353b129ca3255a
- `problems/P8/tests/test_matter.py` 2711a7c000b0149832c129f3b81f600e2d57f9aa8bf35a9253d1ac0b1e296fab
- `problems/P8/tests/test_quadratic.py` 0bf8f98068b6ddf3669548150e8c0369b1869231de6f6a663a8b2f6805e06d3b
- `problems/P8/tests/test_rational_candidates.py` b43e6232063146911849d350b2c67d9f7377e1dd6815912c88bf851a0ddfebeb
- `problems/P8/tests/test_regressions.py` 453ae6e27b3a604b913f2661d4db8bf6b55d8b43a3c0379de9586f2e4253c0ff
- `problems/P8/tests/test_signs.py` 31ed35642816d4c1b24a6010452722a70e63779d4e4bb83ebb2d0c8f27f3e913
- `problems/P8/tests/test_strong_gravity.py` 8cffd7b9d0d53dbac6be0a31b5aa89e33cf57c207ca62b21467c18ce764be735
- `problems/P8/tests/test_tensor.py` 2d48772a28c7ca9625c0b1282332af7d3f8ee24c83064041578bb112c4f726e3
- `problems/P8/tests/test_tilted_hessian.py` 1548a342ffd8bfd4d1717e7e3481cfe0040aa28d6cd210671968eb3dd2296804
- `uv.lock` 83af0a0a6d4d56b568c6f4949e489041f656da38c1701d26e486b6d8adc78fe3
