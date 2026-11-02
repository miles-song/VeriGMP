# Verified In-Place Newton Interpolation

This experiment implements the interpolation component planned for balanced Toom-8 multiplication. Two Rust functions recover six or seven nonnegative integer coefficients from scaled polynomial evaluations. Verus proves that these functions refine input-defined mathematical specifications. This module provides interpolation only—it is not a complete Toom-8 kernel or a performance result. Production dispatch and consumer pins remain unchanged.

## Inputs and Output

For degree `d = 5` or `d = 6`, let `c[0..d]` be nonnegative integer coefficients. Input buffers represent

```text
H(s) = sum(c[j] * 64^(d-j) * s^j, j = 0..d)
```

at nodes `s = 1, 4, 16, 64, 256, 1024`, with `4096` added for degree 6. The coefficients are ghost inputs defined independently of executable output. The contract requires each evaluation to fit its same-length unsigned buffer. On return, buffer `j` represents `c[j]`, with all buffer lengths unchanged. Rust mutable borrows enforce disjoint buffers. Empty buffers represent zero and satisfy the contract when mathematical input conditions hold.

Evaluation equalities and nonnegative-coefficient conditions are formal caller obligations. The ordinary test parser checks structural input shape but does not dynamically validate every mathematical precondition. The independent oracle supplies valid cases. A future Toom-8 evaluation and composition producer must establish these conditions before calling this module.

- [Independent polynomial and phase specifications](candidate/native/specs/toom8_newton.rs)
- [Actual in-place Rust interpolation](candidate/native/verified/toom8_newton.rs)
- [Verified test bridges deriving ghost coefficients from separate inputs](candidate/native/toom8_newton_test_bridge.rs)

## Factored Execution

The runtime first forms divided differences, then converts the Newton basis to monomials by scaled subtraction, and finally removes powers of 64. It updates the caller's six or seven buffers in place, using no runtime dense matrix and allocating no dynamic storage.

There are 72 mathematical updates across both paths: 36 divided-difference updates and 36 Newton-to-monomial updates. They execute 144 primitive calls:

| Primitive | Calls across both paths |
|-----------|-------------------------|
| Exact subtraction | 36 |
| Odd exact division | 36 |
| Power-of-two division within divided differences | 25 |
| Exact scaled subtraction | 36 |
| Final power-of-two coefficient recovery | 11 |
| **Total** | **144** |

The degree-5 path uses 60 calls; the degree-6 path uses 84. Twenty-four phase helpers are marked for inlining and divide the proof into local obligations. Independent audit symbolically applied the actual primitive-call schedule to a scaled Vandermonde basis. Every intermediate coefficient remained an integer, nonnegative, and no larger than the updated buffer's prior value; the final map was the identity.

The proof establishes exact division, subtraction nonnegativity, and actual same-length buffer updates. It does not establish the proposed whole-Toom-8 `12n`/`10n` workspace layouts. A fixed number of linear buffer traversals gives analytic `O(n)` module cost with constant internal storage; no machine-cost theorem or timing claim is made. The saved optimized code contains no allocator, general division instruction, division helper, or per-element bounds-panic path. Contract-related structural assertions remain.

## Frozen Evidence

The accepted original `newton-feature1` report has SHA-256 `7964f375cf33a1dce8ef9195fe76a4ccacfc593eeff2524b999dbefca7e0b514`. The independent audit has SHA-256 `854ecac8bdbc25c963a0aa55fcb4e8343dcc225156a40dffde7ab876211b5a62`.

| Check | Result |
|-------|--------|
| Complete library verification | 425 verified, 0 errors |
| Actual runner verification, including two verified test bridges | 427 verified, 0 errors |
| Code-generation verification, including the same bridges | 427 verified, 0 errors |
| Independent integer cases | 1,087: 529 degree-5 and 558 degree-6 |
| Structural invalid commands | 10, all rejected with exit code 101 |
| Actual-source semantic mutants | 8, all rejected by verification conditions |
| Frozen inputs / tool files / actual runner runtime libraries | 89 / 21 / 3 |
| Recorded commands / bound build artifacts | 27 / 4 |

Independent review also inverted the scaled evaluation matrix using exact `Fraction` arithmetic, recovered expected coefficients from evaluation inputs alone, and replayed the saved actual runner. All 1,087 results matched byte for byte. This dense matrix is an independent audit oracle, not production code. Cases cover buffer lengths from 0 through 128, zero, basis, boundary, and mixed coefficient inputs. The harness checks canaries, unchanged coefficient inputs, and the unused seventh buffer on the degree-5 path.

The immutable checker requires exactly one complete zero-error verification summary with exit code 0 for positive runs. Semantic mutants must fail with exit code 1, one partial summary for `toom8_newton`, and actual verification condition diagnostics. Resource, timeout, parser, and loading failures do not count as successful mutation rejection.

- [Accepted report](evidence/verification.json)
- [Independent source, symbolic-schedule, and execution audit](evidence/root-independent-audit.json)
- [Independent polynomial oracle](newton_oracle.py)
- [Full immutable gate](check_newton.py)
- [Six preserved development attempts and source overlays](development/index.json)

Earlier resource-limit failures, an unsupported specification-visibility attempt, and an initial caller compilation failure remain in the archive. The accepted implementation uses explicit local proof phases within the existing resource budget. No assumed lemmas, admitted goals, or external bodies were introduced.

## Source Identity and Reproduction

All executable, specification, proof, checker, and oracle source bytes are preserved exactly, including original line endings. Of 89 frozen inputs, 87 are byte-identical; two provenance-only JSON files have host paths redacted: `parent-newton-proof.json` and `parent-wide-odd-gate.json`. [publication.json](publication.json) records original and published hashes for all archived files. Published logs and reports also redact host paths. Preparation reconstructs the exact code and explicitly redacted provenance; it does not claim to reconstruct original private machine paths.

Audit the saved evidence and prepare a new directory:

```sh
python3 experiments/toom8-primitives/newton/audit.py
python3 experiments/toom8-primitives/newton/prepare.py \
  --output /tmp/verigmp-newton
```

The lightweight audit regenerates integer inputs and expected outputs, recomputes hashes, checks saved proof diagnostics, and inspects saved assembly. It does not execute omitted binaries or rerun the verifier. Preparation refuses an existing directory and records fresh verification as `not_run`. To run a new full candidate gate on Linux:

```sh
export VERUS_BIN=/path/to/pinned/verus
python3 experiments/toom8-primitives/newton/prepare.py \
  --output /tmp/verigmp-newton-verified --verify
```

The [toolchain pin](candidate/native/toolchain.json) is Verus `0.2026.10.26.d17fbd0` with Rust `1.99.1`. The fresh gate records its own complete input, tool, actual runner-runtime, and artifact identities. Its input snapshot contains the two public provenance copies and therefore has different metadata hashes from the original run. The code is unchanged. Neither command performs a benchmark. Archive CI audits and prepares; it does not claim fresh candidate proof verification.

## Remaining Obligations

The module reuses independently verified [full-u64 odd division](../wide-odd/README.md) and existing exact subtraction, scaled subtraction, and power-of-two division. Verus, its standard library, Z3, Rust, LLVM, and the execution environment remain trusted dependencies. The ordinary harness, Python tooling, and code-generation classification remain unverified test infrastructure. Compiled binary and `.rlib`/`.vir` bodies are omitted; their identities and textual assembly are retained, and fresh reproduction rebuilds them.

Whole-Toom-8 evaluation, point-pair construction, recursive composition, actual workspace capacity, and end-to-end performance remain separate work. This balanced interpolation differs from GMP's 16-point interpolation; no implementation-equivalence or performance-parity claim is made. The [repository license](../../../LICENSE) applies, with existing third-party notices retained.
