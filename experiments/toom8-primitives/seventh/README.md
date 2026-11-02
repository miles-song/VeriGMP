# Seventh odd node from one positive-eight product

This isolated feature computes the seventh input needed by the existing odd Newton interpolator. It uses one actual product at +8, known even coefficients, exact division and scaling. It does not evaluate -8 or add a second point product.

## Actual arithmetic and contract

For the two eight-block input polynomials A and B, let c_d = ∑_{i+j=d} A_i B_j. `positive_product` evaluates A(8) and B(8) from their original full-u64 limbs and calls the verified forced Toom4 multiplier.

`normalize` subtracts the known even contribution ∑_{j=0}^7 c_{2j}·64^j from this product, divides exactly by 8, then multiplies by 64^6. The result is ∑_{j=0}^6 c_{2j+1}·64^{6+j}, the odd Newton node at s=4096. The intermediate nonnegativity, exact division and output capacity are formal proof obligations.

`prepare_seventh` composes the actual positive product and normalization. Its eight even-coefficient buffers remain explicit caller premises tied to the original input blocks. This feature does not yet produce those coefficients inside the same call.

The domain is equal input length n with 7k ≤ n ≤ 8k, full-u64 limbs, including k=0 and an empty final block. Output has 2(k+1) limbs; scratch requires 14(k+1) limbs, excluding output and retained immutable coefficient buffers. Child threshold is at least 24. Rust borrowing separates mutable storage; immutable inputs may overlap.

The ordinary parser checks structural shape. The independent Python corpus supplies numerically correct even coefficients; the parser does not check that mathematical premise. A later actual composed caller must establish it before calling this module.

## Frozen evidence

The accepted gate is `seventh-feature1`:

| Check | Result |
|-------|--------|
| Captured source inputs | 112 |
| Full library / runner / codegen verification | 511 / 511 / 511, zero errors |
| Independent integer cases | 672: 336 positive products and 336 normalized nodes |
| Invalid harness commands | 12 rejected |
| Actual-core semantic mutants | 12 rejected by genuine scoped VC failures |
| Mixed fatal diagnostic fixtures | 108 rejected |
| Tool / actual runner runtime / saved artifact identities | 21 / 3 / 4 |
| Recorded commands | 33, each with return code and log hash |

Independent review recomputed the integer results, checked the supplied even coefficients, and replayed the saved actual runner. Two reachable code-generation roots contain no allocator, general-division instruction/helper, or element-bounds panic. Structural assertions and slice-failure paths remain. No timing was performed.

Both development attempts are retained: six mathematical proofs and three actual-function proofs, all passing. See [scope](scope.json), [saved gate](evidence/verification.json), [independent review](evidence/root-independent-audit.json), [publication map](publication.json), and [development index](development/index.json).

## Audit and reproduce

From the repository root:

```sh
python experiments/toom8-primitives/seventh/audit.py
python experiments/toom8-primitives/seventh/test_prepare_boundaries.py
python experiments/toom8-primitives/seventh/prepare.py --output /tmp/verigmp-seventh
```

The audit validates saved hashes and logs and recomputes independent integer expectations. It does not rerun a verifier or compiled runner. Preparation refuses an existing destination and reconstructs all 112 input files byte for byte.

With the pinned Linux Verus/Rust tools and `VERUS_BIN` set, run a new gate in a fresh directory:

```sh
python experiments/toom8-primitives/seventh/prepare.py --output /tmp/verigmp-seventh-fresh --verify
```

Compiled executables, rlib/vir bodies, and the large oracle output log are omitted; their recorded hashes remain. Host paths in published logs are redacted with original/published SHA mappings. Arithmetic sources remain exact.

The analytic work is one existing full multiplication of k+1 limbs plus linear work. This is not a checked machine-cost theorem. The complete interpolation caller, recursive Toom8, whole-kernel workspace and performance acceptance remain outside this feature. No production default or consumer pin changes.