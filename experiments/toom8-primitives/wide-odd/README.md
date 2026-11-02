# Verified odd exact division for balanced Toom-8

This archive contains a verified Rust primitive for exact division by a positive odd `u64`, with a supplied inverse modulo `2^64`. It also contains a verified constant-inverse caller for `3, 15, 63, 255, 1023, 4095`—the odd factors needed by planned balanced Toom-8 interpolation. The implementation processes limbs from low to high and writes the quotient in place.

This is one arithmetic module, not a complete Toom-8 multiplication algorithm. No performance measurement was run for this feature. Production dispatch and consumer pins are unchanged; GMP parity is not established.

## Contract and implementation

Let `B = 2^64`, let `a` be the unsigned little-endian integer represented by a slice, and let `d` be the divisor. The generic interface requires `0 < d ≤ u64::MAX`, a `u64` inverse `inv` satisfying `(d · inv) mod B = 1`, and `a mod d = 0`. It returns the same-length slice representing `a / d`. These preconditions include `d = 1` and `d = u64::MAX`; they do not limit the generic routine to the six Toom constants. Empty slices represent zero.

For each input limb `x` and incoming carry `c < d`, the implementation computes `q = (x − c) · inv mod B` using wrapping word operations. A `u128` multiply and addition establish `d·q + c = x + B·c_next`, with `c_next < d`. The proof covers the full `u64` divisor and carry ranges, including the overflow boundary. The prefix invariant composes this scalar relation across the slice. Exactness of the original input and cancellation of powers of `B` modulo `d` imply that the final carry is zero. The constant-family caller proves its own inverse precondition before invoking the generic implementation.

- [Independent integer specifications](candidate/native/specs/wide_odd_division.rs)
- [Actual Rust implementation and refinement proofs](candidate/native/verified/wide_odd_division.rs)
- [Actual test caller](candidate/native/wide_odd_runner.rs)
- [Optimized code-generation caller](candidate/native/wide_odd_codegen.rs)

The executable path allocates no dynamic storage. Its loop visits each limb once, so the source-level operation count is linear in slice length with constant auxiliary storage. This is an operation-count argument, not a mechanized cost theorem or a measured speedup. The inspected optimized roots contain no general division instruction, allocator call, or per-element bounds-panic path. The generic interfaces retain their implemented structural checks, such as a positive divisor. Inverse validity and exact divisibility remain formal caller obligations; the generic core does not dynamically check all mathematical preconditions. The ordinary test runner adds explicit input validation.

## Frozen evidence

The accepted gate is `wide-odd-feature5`. The original verification report has SHA-256 `fa6d57852c5bb56598c233eb4d4fef0672658d16eb1ccbc8b8165f974e44f82a`. Its independent audit has SHA-256 `06caf6cfe2ee3556a4af10808cac0e8b49783e7b062ff9c002f86bb3875de304`. Published report and log copies redact host paths; [publication.json](publication.json) maps every original hash to its published hash. All 78 accepted source files are preserved byte for byte.

| Check | Result |
| --- | --- |
| Complete library verification | 327 verified, 0 errors |
| Actual runner verification | 24 verified, 0 errors |
| Code-generation caller verification | 24 verified, 0 errors |
| Independent integer cases | 28,308 |
| Scalar word cases | 16,480 |
| Generic odd-divisor array cases | 11,024 |
| Toom constant-family array cases | 798 |
| Inverse-constant cases | 6 |
| Invalid harness commands | 17, all rejected with exit code 101 |
| Actual-source semantic mutants | 8, all rejected by verification conditions |
| Immutable inputs / tool files / actual runner runtime libraries | 78 / 21 / 3 |
| Recorded commands / bound build artifacts | 34 / 4 |

The checker requires a zero process exit code and exactly one complete zero-error summary for each positive verification. Negative checks require exit code 1, exactly one partial summary for the intended module, and actual verification-condition diagnostics; syntax, loading, timeout and resource failures do not count as successful mutation rejection.

The independent audit regenerated all 28,308 expected integer results and replayed the bound actual runner, matching the frozen output byte for byte. It also checked all 17 invalid commands. This archive's lightweight `audit.py` recomputes the integer inputs and expected outputs and inspects saved evidence; it does not rerun omitted executables or the verifier.

- [Accepted verification report](evidence/verification.json)
- [Independent source, tool, runtime and execution audit](evidence/root-independent-audit.json)
- [Independent integer oracle](wide_odd_oracle.py)
- [Full immutable verification gate](check_wide_odd.py)
- [Code-generation inspection](wide_odd_codegen.py)
- [Historical attempts and exact source overlays](development/index.json)

Eight earlier development attempts remain available, including failed proofs and checker failures. Feature 4 passed its arithmetic checks, but feature 5 completed explicit command return-code records, strict positive-summary classification and direct runner-loader identity binding. Feature 5 is the accepted evidence boundary. Historical attempts can be reconstructed from the accepted sources plus their listed overlays.

## Reproduce

From this repository checkout, audit the published records and reconstruct the accepted sources into a new directory:

```sh
python3 experiments/toom8-primitives/wide-odd/audit.py
python3 experiments/toom8-primitives/wide-odd/prepare.py \
  --output /tmp/verigmp-wide-odd
```

Preparation refuses an existing output directory. It copies the 78 exact inputs and records `fresh_verification: not_run`. To execute the full proof, oracle, mutation and code-generation gate, use Linux with the pinned Verus and Rust toolchains available through the normal environment:

```sh
export VERUS_BIN=/path/to/pinned/verus
python3 experiments/toom8-primitives/wide-odd/prepare.py \
  --output /tmp/verigmp-wide-odd-verified --verify
```

The pin is [native/toolchain.json](candidate/native/toolchain.json): Verus `0.2026.10.26.d17fbd0`, Rust `1.99.1`. The gate discovers and hashes the tools and the actual runner's dynamic libraries, including the ELF loader, for the new run. It preserves every new command, return code, log and artifact identity. It never runs a benchmark. Archive CI audits and reconstructs the evidence; it does not claim a fresh candidate proof run.

## Trust and scope

The arithmetic core contains no assumed lemmas, admitted goals, external bodies, unchecked FFI or assembly. Verus, its standard library, Z3, Rust, LLVM and the execution environment remain trusted dependencies. Runners, Python oracles, archive tools and code-generation classifiers are unverified test infrastructure. The proof concerns the actual Rust functions on their stated domains, rather than an output-defined specification.

The archive includes textual assembly and exact artifact identities; compiled executables, `.rlib`/`.vir` bodies and large oracle-output logs are omitted. Fresh reproduction rebuilds them. The generic odd-division implementation and proof are independent Rust code. [Pinned GMP references](gmp-odd-reference.json) document the comparison source; no GMP implementation is copied into this module. The repository's [MIT license](../../../LICENSE) applies to this code, with existing third-party notices retained.

Whole-Toom-8 evaluation, composition, recursive multiplication, workspace capacity and measured end-to-end performance remain separate obligations.
