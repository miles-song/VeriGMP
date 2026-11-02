# Actual fifteen-coefficient interpolation

This isolated feature starts with two limb arrays and returns all fifteen coefficients of their eight-block polynomial product. The actual caller establishes the numerical premises of both existing Newton interpolators. No coefficient values need to be supplied to the top-level `interpolate` function.

## Actual call chain

Let c_d = ∑_{i+j=d} A_i B_j for the eight blocks of the two inputs. `interpolate` computes the low and high endpoint products, invokes the six positive/negative dyadic pairs and the even Newton consumer, obtains the additional odd node from one +8 product, then calls the odd Newton consumer. It returns c_0 and c_14, c_2, c_4, ..., c_12 in six even buffers, and c_1, c_3, ..., c_13 in seven odd buffers.

For nonempty endpoints, this is exactly 2 + 12 + 1 = 15 child multiplications; empty endpoints are skipped. Children still use the verified forced Toom-4 implementation in this feature. The shared-endpoint function `with_endpoints` retains explicit endpoint-value premises; the top-level function establishes them by actual multiplication.

The domain is full-u64 equal-length inputs with 7k ≤ n ≤ 8k, including k = 0 and an empty final block. Write m = k + 1 and h = n − 7k. The thirteen interior coefficient buffers each have 2m limbs; endpoint buffers have 2k and 2h limbs. Shared scratch has at least 14m limbs. A proved storage inequality is 26m + 2k + 2h + 14m ≤ 44m. This accounts for this caller's separate slices; it is not yet a whole recursive Toom-8 workspace theorem.

Rust borrowing separates mutable buffers; immutable input slices may overlap. Actual evaluation, endpoint subtraction, signs, exact divisions, nonnegative coefficient bounds and Newton node identities are established before the consumers are invoked. The ordinary harness validates structural shapes and executes the top-level caller.

## Frozen evidence

The accepted gate is `interpolation-feature1`:

| Check | Result |
|---|---|
| Captured source inputs | 115 |
| Full library / runner / codegen verification | 514 / 514 / 514, zero errors |
| Independent input-convolution cases | 336 |
| Invalid harness commands | 12 rejected |
| Actual-core semantic mutants | 12 rejected by genuine scoped VC failures |
| Mixed fatal diagnostic fixtures | 108 rejected |
| Tool / actual runner runtime / saved artifact identities | 21 / 3 / 4 |
| Recorded commands | 33, each with return code and log hash |

The independent review recomputed all fifteen coefficients from original inputs and replayed the saved actual runner. Two reachable code-generation roots contain no allocator, general-division instruction/helper, or element-bounds panic. Structural assertions and slice-failure paths remain. No timing was performed.

The single focused development attempt is retained: three caller/storage properties passed. See [scope](scope.json), [saved gate](evidence/verification.json), [independent review](evidence/root-independent-audit.json), [publication map](publication.json), and [development index](development/index.json).

## Audit and reproduce

From the repository root:

```sh
python experiments/toom8-primitives/interpolation/audit.py
python experiments/toom8-primitives/interpolation/test_prepare_boundaries.py
python experiments/toom8-primitives/interpolation/prepare.py --output /tmp/verigmp-interpolation
```

The audit recomputes saved evidence and independent integer expectations; it does not rerun a verifier or compiled runner. Preparation refuses an existing destination and reconstructs all 115 original input files byte for byte.

With the pinned Linux Verus/Rust tools and `VERUS_BIN` set, use a fresh directory for a new gate:

```sh
python experiments/toom8-primitives/interpolation/prepare.py --output /tmp/verigmp-interpolation-fresh --verify
```

Compiled executables, rlib/vir bodies and the large oracle output log are omitted; their hashes remain recorded. Published logs redact host paths with original/published SHA mappings. Arithmetic sources remain exact.

The analytic work is T₄(k) + T₄(h) + 13·T₄(m) + O(k), skipping empty endpoint terms. It is not a checked machine-cost theorem. Product recomposition, actual Toom-8 recursion, complete recursive workspace and performance acceptance remain outside this feature. No production default or consumer pin changes.