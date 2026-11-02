# Scoped dyadic recovery gate

This directory records a reviewable scoped progress slice for the existing
Toom-8 dyadic recovery work. It checks the generic proof exports and the actual
consumer already present in the frozen interpolation candidate. It also checks
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
buffers, with endpoint buffers returned separately. The generic proof exports
remain ghost/spec inputs to those calls. The dyadic producer and interpolation
stages use the existing inlining annotations where present; the public Newton
consumers are ordinary runtime functions. The saved optimized assembly is the
erasure check for the complete path, so an absent Newton symbol is evidence of
inlining in that snapshot, not a source-level claim that every consumer carries
an inline attribute.

Run the scoped audit from the repository root:

```sh
python experiments/toom8-primitives/dyadic-recovery/check_dyadic_recovery.py
```

The 2026-11-03 run is recorded in
[`evidence/check-20261103.json`](evidence/check-20261103.json). It ran against
source commit `c3f5db9a015a1aa71e1d4ebb0c815a7c5b8a4633`, returned code 0, and
records the SHA-256 of the command report, checker, and scope manifest.

The audit runs the saved interpolation and dyadic archive audits, then
independently recomputes all 336 interpolation cases from the command inputs.
It records M7/M8 status from the separate `sat-counting-lab-src` checkout and
the registered GMP target from `native/performance-target.json`. It does not
rerun Verus, compile the Rust runner, or claim a benchmark. The report therefore
ends in `scoped_progress` with promotion disabled even when the source,
historical evidence, static erasure, and independent mapping checks pass.

## Acceptance boundary

The saved archive evidence is useful for source and call-chain review:

| Gate | Current result |
| --- | --- |
| Generic proof exports and actual runtime consumer | Pass in the saved candidate source |
| Independent coefficient-to-buffer mapping | Pass, 336 cases |
| Static proof-symbol and helper erasure check | Pass on saved optimized assembly |
| Fresh Verus/Rust proof and runner | Blocked; toolchain is unavailable locally and this audit does not substitute for it |
| GMP performance baseline and parity | Blocked; no fresh benchmark, registered target remains unmet |
| SAT M7/M8 consumer promotion | Blocked; M7 is `spec_only`, M8 is `conditional_composition`, and no dyadic consumer is pinned |

The feature does not modify `native/`, the SAT repository, production dispatch,
or consumer dependency pins. It is not a solver backend acceptance and it does
not establish complete Toom-8 recursion, recomposition, low-product or square
composition, whole-workspace bounds, or GMP parity.
