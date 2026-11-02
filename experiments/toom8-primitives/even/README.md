# Even-coefficient caller

This isolated feature connects actual dyadic products to the existing even Newton interpolator. It starts with two input limb arrays and returns the six even interior coefficients of their degree-14 convolution. The arithmetic is proved; this archive contains no performance measurement and does not select a production backend.

## Actual call chain

For eight input blocks A_0,...,A_7 and B_0,...,B_7, let c_d=sum_{i+j=d} A_i B_j. The shared-endpoint function `with_endpoints` creates the six normalized dyadic node pairs at s=1,4,16,64,256,1024, proves nonnegative coefficient and exact node premises, and calls the existing even Newton implementation. Its outputs are c_2,c_4,c_6,c_8,c_10,c_12. The six normalized odd nodes are retained for a later odd caller.

`prepare_even` computes c_0 and c_14 from actual endpoint blocks first, then calls `with_endpoints`. Nonempty endpoints account for two child multiplications and the six positive/negative pairs for twelve. Empty endpoints are skipped. Children use the previously verified forced Toom4 implementation.

The arithmetic contract permits full-u64 limbs, equal input length n, and 7*k <= n <= 8*k, including k=0 and an empty final block. The twelve mutable output buffers each have 2*(k+1) limbs. The shared-endpoint core requires 14*(k+1) scratch limbs; the self-contained entry requires 18*(k+1), excluding those twelve outputs. Rust borrowing separates mutable storage, while immutable input slices may overlap.

The lower shared-endpoint entry requires mathematically correct endpoint values. The self-contained entry establishes them from actual inputs. The ordinary harness checks structural shape; formal numeric premises are proved by the actual caller.

## Frozen evidence

The accepted gate is `even-feature1`:

| Check | Result |
| --- | --- |
| Captured source inputs | 108 |
| Full library / runner / codegen verification | 502 / 502 / 502, zero errors |
| Independent integer cases | 336 |
| Invalid harness commands | 12 rejected |
| Actual-core semantic mutants | 10 rejected by genuine scoped VC failures |
| Mixed fatal diagnostic fixtures | 90 rejected |
| Tool / actual runner runtime / saved artifact identities | 21 / 3 / 4 |
| Recorded commands | 31, each with return code and log hash |

The independent review recomputed all integer results and replayed the saved actual runner. Two reachable code-generation roots contain no allocator, general-division instruction/helper, or element-bounds panic. Explicit structural assertion and slice-failure paths remain. This inspection is not machine-code equivalence or a timing result.

All three development attempts are retained: the first caller-capacity precondition failure, the successful focused proof, and successful full code-generation verification. No failed attempt is counted as acceptance.

See [scope](scope.json), [saved gate](evidence/verification.json), [independent review](evidence/root-independent-audit.json), [source/hash publication map](publication.json), and [development index](development/index.json).

## Audit and reproduce

From the repository root:

```sh
python experiments/toom8-primitives/even/audit.py
python experiments/toom8-primitives/even/test_prepare_boundaries.py
python experiments/toom8-primitives/even/prepare.py --output /tmp/verigmp-even
```

The audit recomputes saved evidence and independent integer expectations; it does not rerun a verifier or compiled runner. Preparation refuses an existing destination and reconstructs all 108 original input files byte for byte.

With the pinned Linux Verus/Rust tools and `VERUS_BIN` set, use a fresh output directory for an actual new gate:

```sh
python experiments/toom8-primitives/even/prepare.py --output /tmp/verigmp-even-fresh --verify
```

Compiled executables, rlib/vir bodies, and the large oracle output log are omitted. Recorded artifact hashes remain available. Published logs redact host paths with original/published SHA mappings; arithmetic sources remain exact.

The seventh odd node, odd interpolation caller, complete product recomposition, recursive Toom8, full recursive workspace and cost proof, and performance acceptance are outside this feature. No production default or consumer pin changes.