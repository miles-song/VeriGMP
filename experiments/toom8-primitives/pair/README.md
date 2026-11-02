# Verified Signed Point-Pair Normalization

This component transforms two same-length unsigned limb arrays into a signed sum and difference. Its second entry point divides both results exactly by two. These are verified arithmetic building blocks for balanced Toom-8 interpolation. This feature does not establish the point-product caller's premises, a complete Toom-8 kernel, or a performance result.

## Contract

Let `P` be the initial value of `plus`, `D` the initial value of `minus`, `B = 2^64`, and `n` their common limb length. The interfaces require `D <= P` and `P + D < B^n`. Define `Y = -D` when `negative` is true, and `Y = D` otherwise.

`sum_difference` writes `P + Y` to `plus` and `P - Y` to `minus`. `half_pair` additionally requires `P % 2 == D % 2` and writes `(P + Y) / 2` and `(P - Y) / 2`. Both arrays keep their original lengths. Zero-length arrays are supported. Limb words span the full `u64` domain subject to these value-level preconditions. Rust borrowing keeps the two writable slices disjoint.

- [Independent integer and prefix specifications](candidate/native/specs/toom8_pair.rs)
- [Actual sum/difference and normalization implementations](candidate/native/verified/toom8_pair.rs)
- [Ordinary harness calling the actual functions](candidate/native/toom8_pair_runner.rs)

The sum/difference loop reads both old words before overwriting either. It carries an addition carry and a subtraction borrow, each at most one, and chooses the output order from the sign flag. Its prefix invariants relate the actual arrays to the original inputs. The input bounds imply both final carry and final borrow are zero. The exact-halving caller proves divisibility from matching parity and calls the existing verified exact-division interface twice.

The implementation uses one simultaneous limb traversal followed, for `half_pair`, by two exact-halving traversals. It allocates no heap storage and needs no scratch slice or temporary array. This gives an analytic linear operation count and constant internal storage; it is not a checked machine-cost theorem or a measured speedup. The four inspected optimized entry paths contain no allocator, general division instruction/helper, or per-element bounds-panic path. The explicit equal-length assertion remains. Numeric magnitude, capacity and parity conditions are formal caller obligations; the ordinary test harness validates them separately.

## Frozen Evidence

The accepted original `pair-feature2` report has SHA-256 `26f3fac08d25c94a83f7dc51526903419bd9846b5c84c49ab3f249bcbcb53958`. Its independent audit has SHA-256 `c2d76f67bbe70a2e7fc96ad5b04bb5633604cfa62129eaf3f24f5bf00f4e3234`.

| Check | Result |
| --- | --- |
| Complete library verification | 454 verified, 0 errors |
| Runner verification, for imported modules | 150 verified, 0 errors |
| Code-generation verification, for imported modules | 150 verified, 0 errors |
| Independent integer cases | 10,918 |
| Sum/difference cases | 7,674 |
| Exact-halving cases | 3,244 |
| Invalid harness commands | 12, all exit code 101 |
| Actual-source semantic mutants | 10, all rejected by verification conditions |
| Frozen inputs / tools / actual runner runtime libraries | 91 / 21 / 3 |
| Recorded commands / bound build artifacts | 31 / 4 |

Independent review recomputed the expected results with unbounded integers and replayed the saved actual runner. All 10,918 results and 12 invalid-command rejections matched. The corpus covers both sign directions, zero arrays, long carry and borrow chains, near-capacity sums, equal operands, and lengths from 0 through 256. The harness checks both output boundaries.

- [Accepted gate](evidence/verification.json)
- [Independent source and execution audit](evidence/root-independent-audit.json)
- [Integer oracle](pair_oracle.py)
- [Immutable full checker](check_pair.py)
- [Seven preserved development attempts and source overlays](development/index.json)

The full checker executes its captured checker, oracle and code-generation bytes, and parses captured provenance. Positive proofs require exit code 0 and exactly one complete zero-error summary. Semantic mutations require exit code 1, exactly one partial summary for the intended module, and real verification-condition diagnostics. Nine appended fatal-diagnostic fixtures, including solver `unknown`, `rlimit` and type-check failures, must be rejected even beside a normal verification-condition error. The original feature-1 evidence is retained; feature 2 reran unchanged arithmetic with the repaired checker.

## Reproduce

[publication.json](publication.json) maps the original and published files. All 91 source inputs preserve their original bytes. Host paths are redacted only in published report and log copies. The public audit regenerates expected integer vectors, checks saved diagnostics and source identities, and inspects saved assembly. It does not rerun omitted binaries or proofs.

```sh
python3 experiments/toom8-primitives/pair/audit.py
python3 experiments/toom8-primitives/pair/test_prepare_boundaries.py
python3 experiments/toom8-primitives/pair/prepare.py \
  --output /tmp/verigmp-pair
```

Preparation refuses existing destinations and rejects absolute or escaping source names. A fresh full gate requires Linux and the pinned Verus `0.2026.10.26.d17fbd0` / Rust `1.99.1` toolchain:

```sh
export VERUS_BIN=/path/to/pinned/verus
python3 experiments/toom8-primitives/pair/prepare.py \
  --output /tmp/verigmp-pair-verified --verify
```

The fresh gate records its own source, tool, actual runner-runtime and compiled artifact identities. It does not run benchmarks. Archive CI audits and reconstructs; it does not claim a fresh candidate proof. Executables and compiled `.rlib`/`.vir` bodies are omitted from this archive.

## Remaining Obligations

No assumed lemmas, admitted goals, external bodies, unchecked FFI or assembly enter the arithmetic core. Verus, vstd, Z3, Rust and LLVM remain trusted; Python checkers, ordinary harnesses and assembly classifiers are unverified infrastructure. The [repository license](../../../LICENSE) and retained third-party notices apply.

An actual point-product producer must derive the magnitude, capacity and parity premises from input blocks. That composition, endpoint removal, scaling, Newton caller premises, recomposition and full recursive workspace/cost bounds remain outside this feature. No GMP parity, production-dispatch change or consumer-pin change is claimed.