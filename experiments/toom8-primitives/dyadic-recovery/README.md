# Scoped dyadic recovery gate

This directory records a reviewable scoped progress slice for the existing
Toom-8 dyadic recovery work. It checks the generic proof exports and the
actual consumer present in the frozen interpolation candidate. It also checks
that the saved optimized assembly contains neither proof-only symbol names nor
the allocation, general-division, and element-bounds helpers rejected by the
interpolation code-generation inspector.

The consumer path is:

```text
toom8_interpolation::interpolate
  -> toom8_even::with_endpoints
     -> toom8_normalization::with_endpoints
        -> toom8_dyadic_producer::dyadic_pair
  -> toom8_seventh::prepare_seventh
  -> toom8_newton::odd
```

The six dyadic pairs and one positive-eight point provide the interior nodes;
the actual caller computes the two endpoint products. Its existing contracts
map the independent fifteen-coefficient convolution to six even and seven odd
buffers, with endpoint buffers returned separately. The fifteen recovered
coefficients are the low endpoint, six even, seven odd, and high endpoint.
The generic proof exports remain ghost/spec inputs to those calls. The dyadic
producer and interpolation stages use the existing inlining annotations where
present; the public Newton consumers are ordinary runtime functions. The saved
optimized assembly is the erasure check for the complete path, so an absent
Newton symbol is evidence of inlining in that snapshot, not a source-level
claim that every consumer carries an inline attribute.

Run the scoped audit from the repository root:

```sh
python experiments/toom8-primitives/dyadic-recovery/check_dyadic_recovery.py
```

The command exits 0 when all source, archive, fresh evidence, and consumer
observation checks pass, indicating successful scoped evidence consistency
audit. Discrepancies exit 1. Exit 0 is not backend promotion acceptance.

The default wrapper reads the frozen VeriCount source and status receipt
recorded at commit `8ba9253946783ce84c00f6218f9cd538e8bb8ef2` on 2026-11-03.
It records file SHA-256 for `native/proof-status.json`, `native/arithmetic.rs`,
`native/trusted/gmp_backend.rs`, `native/integer_backend.rs`, and `.gitmodules`,
with VeriGMP gitlink at `c083839dc07f9b0cffea1a52cd6810d817105355`. The frozen
receipt shows no Rust pattern matching `toom8|dyadic_pair|dyadic.recovery` in
`native` or `refinement` roots. M7 status is `spec_only` with remaining work
on integrality/precision/recovery model and native refinement. M8 status is
`conditional_composition` with remaining work to instantiate Problem/value
functions with concrete network semantics, compose the accepted guarded
exhaustive leaf with the whole constructor and actual M4-M7 modules, and prove
the recursive threshold certificate, child shrinkage, local decomposition,
same-combiner execution, and executable termination. The recorded consumer uses
the trusted GMP backend through `native/trusted/gmp_backend.rs`.
The frozen receipt is not a compiled dependency check.

The default audit requires Python only, no private consumer clone or current
proof tool installation. Supply `--consumer-repo ../VeriCount` to check a live
repository; actual HEAD may advance if the recorded source hashes, M7/M8 and
backend authority fields, gitlink, and reference scan still match. The output
records actual and receipt HEADs and proof-status hashes separately.
Supply `--dyadic-report /path/to/dyadic/verification.json`
and `--interpolation-report /path/to/interpolation/verification.json` to audit
raw gate reports; each supplied report directory must contain inputs, logs,
candidate.vir, libcandidate.rlib, oracle-runner, and codegen.s alongside the
report. Supply `--fresh-evidence /path/to/folder` to audit a bundle with
manifest.json and evidence.zip.

The 2026-11-03 run is recorded in
[`evidence/check-20261103.json`](evidence/check-20261103.json). It ran against
source commit `c3f5db9a015a1aa71e1d4ebb0c815a7c5b8a4633`, returned code 0, and
records the SHA-256 of the command report, checker, and scope manifest. That
command audited saved source and archives and required the local
sat-counting-lab-src directory. It did not execute a fresh proof or runner.

The fresh 2026-11-03 verification is recorded in
[`evidence/fresh-20261103/`](evidence/fresh-20261103/). It ran against source
commit `5cfde6a630591080c330ac09177977c539bd3a55` on linux_x86_64 via WSL.
The dyadic gate verified three entries (library, runner build, codegen build)
with 478 items per entry across 102 source inputs, producing 2688 oracle cases,
12 invalid commands, and 8 semantic mutants rejected. The interpolation gate
verified three entries with 514 items per entry across 115 source inputs,
producing 336 oracle cases, 12 invalid commands, and 12 semantic mutants
rejected. The archive evidence.zip is 6818712 bytes with SHA-256
`89e2fe8be6f21afd58b0ad0e73852183487a837a670d21c6da600233f7b774c4`.

The wrapper audits this fresh evidence by checking report hashes, input counts,
tool identities (21 tool files and 3 runtime libraries each, captured execution
versions tied to logs; the archive does not contain tool binaries), and
independently recomputing oracle transcripts against the current Python model
for all 2688 dyadic and 336 interpolation cases. An additional independent
buffer-layout implementation checks 336 interpolation cases. The wrapper does
not rerun the native gate binaries or reread current installed tool binaries.
Codegen inspection is textual optimized assembly audit and confirms
no allocator, general division, or element-bounds panic in inspected reachable
optimized paths; length/slice guards and memset remain. This is no
machine-code equivalence or timing result. The coordinating agent executed the
fresh gates; independent acceptance is pending.

## Acceptance boundary

The fresh scoped verification pass is pending independent review:

| Gate | Current result |
| --- | --- |
| Generic proof exports and actual runtime consumer | Pass in the verified candidate source |
| Independent coefficient-to-buffer mapping | Pass, 336 cases |
| Static proof-symbol and helper erasure check | Pass on saved optimized assembly |
| Fresh Verus/Rust proof and runner | Pass at source commit `5cfde6a` |
| Independent review | Pending |
| Performance timing | Missing; no benchmark run |
| SAT M7/M8 consumer promotion | Blocked; M7 is `spec_only`, M8 is `conditional_composition`, and no dyadic consumer is pinned |
| Solver consumer acceptance | Blocked; no compiled dependency check, no solver integration test |

The feature does not modify `native/`, the SAT repository, production dispatch,
or consumer dependency pins. It is not a solver backend acceptance and it does
not establish complete Toom-8 recursion, recomposition, low-product or square
composition, whole-workspace bounds, or GMP parity. This scope is experiments
only. Replacing the solver's trusted GMP backend requires meeting every
registered library performance gate, an independent confirming run, semantic
compatibility, and frozen representative solver traces. Accepting an individual
optimization for native production dispatch requires reproducible performance
gains on declared workloads, scoped dispatch when gains depend on input shape,
and relevant boundary/regression/combination measurements; overall GMP parity
is not a prerequisite for that acceptance.
