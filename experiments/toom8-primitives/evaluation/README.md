# Verified Eight-Block Signed Evaluation

This module evaluates eight unsigned input blocks as a signed weighted sum and returns its sign and magnitude. A verified caller selects homogeneous weights for positive or negative dyadic points. It is an arithmetic component for planned balanced Toom-8 multiplication, not a complete kernel or performance result. Production dispatch and consumer pins are unchanged.

## Contract

The first seven input slices contain `k` limbs each; the eighth has at most `k` limbs. The destination and compatibility scratch slice each contain `k + 1` limbs. All input limbs span the full `u64` domain. For eight nonnegative weights `w[j]`, the generic interface requires each weight to be at most `2^21` and their sum to be less than `2^22`.

For unsigned input-block values `A[j]`, define

```text
E = sum(w[j] * A[j] * sign(j), j = 0..7)
sign(j) = -1 if the point is negative and j is odd; otherwise +1.
```

The function stores `abs(E)` and returns exactly whether `E < 0`. Destination length is preserved, and the entire scratch slice remains unchanged. Empty input blocks are supported, with a one-limb destination containing zero. Rust's borrowing rules separate writable output and scratch from immutable inputs. The proof does not narrow inputs to observed test patterns.

The scalar helper accepts every incoming carry in `[-2^22, 2^22]` and proves

```text
weighted_limb_sum + incoming = low + 2^64 * outgoing
```

with a `u64` low word and outgoing carry in the same interval. The array loop composes this identity, writes the final signed high word, and uses the existing verified in-place negation only when the result is negative. The implementation uses an `i128` weighted total and a fixed radix-multiple bias before unsigned splitting. All intermediate bounds are proved for the stated complete domain.

- [Independent integer and homogeneous specifications](candidate/native/specs/toom8_evaluation.rs)
- [Actual scalar, slice and dyadic implementations](candidate/native/verified/toom8_evaluation.rs)
- [Ordinary validation harness calling the actual implementation](candidate/native/toom8_evaluation_runner.rs)

## Dyadic Caller

For exponent `e = 0, 1, 2, 3`, the caller uses `(p,q) = (2^e,1)` or `(1,2^e)`. It proves each selected weight equals `p^j * q^(7-j)` and meets the generic weight bounds. The resulting magnitude and sign represent

```text
sum(A[j] * (+/-p)^j * q^(7-j), j = 0..7).
```

This includes the required points `+/-1`, `+/-2`, `+/-4`, `+8`, `+/-1/2`, `+/-1/4` and `+/-1/8`; the caller also supports `-8`. The fixed constants are proved from the independent homogeneous formula. Runtime evaluation uses constant word weights, not a dense matrix or runtime exponentiation.

The source traverses each input block once, followed by at most one in-place negation pass. This gives an analytic linear operation count with constant internal storage and no dynamic allocation. The supplied scratch slice remains part of the interface; this feature does not claim to reduce its allocation. No machine-cost theorem or measured speedup is claimed.

The inspected optimized paths cover the generic scalar, generic array, generic dyadic caller and fixed `8`, `-8`, `-1/8` cases. They contain no allocator, general division instruction or division helper, and no per-element bounds-panic path. Implemented structural assertions remain. Generic weight validity is a formal caller obligation, not a claim that the core dynamically checks all mathematical preconditions; the ordinary harness validates its inputs separately.

## Frozen Evidence

The accepted original `evaluation-feature3` report has SHA-256 `c1f218ea0d8eafad460426d6362b9d20d98d98c6afbd8c7794fa0515e47d5c5c`. Its independent audit has SHA-256 `58072e49545a91312a6db1522587cdd36316e62d9e3e78446d022e8cc1457188`.

| Check | Result |
| --- | --- |
| Complete library verification | 447 verified, 0 errors |
| Runner verification, for its imported arithmetic modules | 72 verified, 0 errors |
| Code-generation verification, for its imported arithmetic modules | 72 verified, 0 errors |
| Independent integer cases | 14,156 |
| Scalar cases | 8,532 |
| Generic weighted-array cases | 2,160 |
| Dyadic-array cases | 3,456 |
| Weight-family cases | 8 |
| Invalid harness commands | 16, all rejected with exit code 101 |
| Actual-source semantic mutants | 12, all rejected by verification conditions |
| Frozen inputs / tools / actual runner runtime libraries | 87 / 21 / 3 |
| Recorded commands / bound build artifacts | 37 / 4 |

The [original mathematical review](evidence/prior-independent-mathematical-audit.json) reconstructed full input integers, evaluated signed rational points with exact `Fraction` Horner arithmetic and applied the homogeneous scale. The hardened gate received a fresh independent review using unbounded signed weighted sums and direct homogeneous dyadic weights. Both reviews replayed their saved actual runner: all 14,156 results matched, and all 16 invalid commands were rejected. Cases include zero and maximum words, extreme carries, one- and two-position weight boundaries, short final blocks, negative and zero results, and lengths from 0 through 128. The harness checks output canaries, input preservation and unchanged scratch.

- [Accepted verification report](evidence/verification.json)
- [Independent mathematical and actual execution audit](evidence/root-independent-audit.json)
- [Independent integer oracle](evaluation_oracle.py)
- [Full immutable gate](check_evaluation.py)
- [Fourteen preserved development attempts and source overlays](development/index.json)

Positive verification requires exit code 0 and exactly one complete zero-error summary. Each semantic mutant must produce exit code 1, one partial summary for `toom8_evaluation` and actual verification-condition errors. Resource, timeout, parser and loading failures are rejected as invalid mutation evidence. Historical proof failures and the feature-1 checker filename error remain available. Feature 3 reran the complete gate after the checker repair: captured checker, oracle, codegen and origin bytes were executed or parsed from the frozen snapshot, and mixed fatal diagnostics were rejected. The arithmetic implementation was unchanged. Feature 2 evidence remains preserved as a historical attempt.

## Reproduce

[publication.json](publication.json) maps original and published identities. All 87 frozen source inputs are byte-identical, including original line endings. Published report and log copies redact host paths. The Python archive audit regenerates expected values and checks saved evidence; actual runner replay was performed only by the independent review. Reconstruct the exact source bundle into a new directory:

```sh
python3 experiments/toom8-primitives/evaluation/audit.py
python3 experiments/toom8-primitives/evaluation/prepare.py \
  --output /tmp/verigmp-evaluation
```

The lightweight audit recomputes independent integer vectors and hashes, checks saved verification diagnostics and inspects saved assembly. It does not execute omitted binaries or rerun the verifier. Preparation refuses an existing directory and records fresh verification as `not_run`.

For a fresh full gate on Linux, make the pinned Verus and Rust toolchains available through the normal environment:

```sh
export VERUS_BIN=/path/to/pinned/verus
python3 experiments/toom8-primitives/evaluation/prepare.py \
  --output /tmp/verigmp-evaluation-verified --verify
```

The [pin](candidate/native/toolchain.json) is Verus `0.2026.10.26.d17fbd0` and Rust `1.99.1`. The fresh gate records its own complete source, tool, actual runner-runtime and artifact identities, including the ELF loader. It never performs a benchmark. Archive CI audits and reconstructs; it does not claim a fresh candidate proof run. Compiled executables and `.rlib`/`.vir` bodies are omitted; their recorded identities and textual assembly are retained.

## Remaining Obligations

The arithmetic core contains no assumed lemmas, admitted goals, external bodies, unchecked FFI or assembly. Verus, its standard library, Z3, Rust, LLVM and the execution environment remain trusted dependencies. Ordinary runners, Python tooling and assembly classifiers remain unverified test infrastructure. The [repository license](../../../LICENSE) applies, with third-party notices retained.

The [Newton interpolation module](../newton/README.md) is separately verified. Point-product and signed-pair composition must still establish its formal input conditions. Whole-kernel recomposition, recursive workspace bounds and measured `mul_mod`/`square_mod` performance remain open. This feature does not claim GMP parity or justify promoting the experimental backend.