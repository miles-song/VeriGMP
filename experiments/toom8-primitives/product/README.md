# Actual input-to-product composition

This experimental feature composes eight-block Toom8 interpolation and exact recomposition over existing Toom4 children. The caller provides original limb inputs. The actual implementation establishes all fifteen coefficient premises and returns their exact full product. This is a single Toom8 split; recursive Toom8, performance acceptance, and production promotion remain outside this scope.

## Interface and workspace

The [verified implementation](candidate/native/verified/toom8_product.rs) exports `balanced` and `full`. Both preserve caller-owned output and scratch lengths and accept full-u64 limb values.

**`balanced`** accepts equal-length inputs with `7*k <= n <= 8*k` (including `k=0` and an empty high block), produces output of `2*n` limbs, and requires scratch of at least `44*(k+1)` limbs. Its child Toom4 threshold is at least 24.

The coefficient bank holds thirteen interior buffers of `2*m` limbs and endpoint buffers of `2*k` and `2*h` limbs, where `m=k+1` and `h=n−7*k`. The bank requires at most `30*m` limbs; the remaining `14*m` is reused during interpolation. Rust's disjoint mutable slices and Verus contracts establish capacity and lifetime obligations.

**`full`** accepts positive equal-length inputs, produces output of `2*n` limbs, requires scratch of at least `12*n` limbs, and takes an outer threshold of at least 56 and a child threshold of at least 24. At or below the outer threshold, the existing Toom4 path executes. Above it, `k=⌈n/8⌉` and the proved inequality `44*(k+1) ≤ 12*n` justifies the `balanced` call. Numeric coefficient buffers are not caller inputs.

For one eight-block split with nonempty endpoints, analytic work is `T4(k) + T4(h) + 13·T4(k+1) + O(n)`. This expression describes children remaining Toom4; it is neither a recursive Toom8 recurrence nor a checked machine-cost theorem. The 12n bound is an actual slice-capacity proof for this composition.

## Evidence

The frozen [verification report](evidence/verification.json) binds 122 captured inputs, 21 tools, three actual runner runtime libraries including the loader, four compiled artifacts, and 35 completed commands. Library, runner, and code-generation builds each verified 525 items with zero errors.

The independent integer oracle covers 696 products: 336 balanced cases and 360 full-wrapper cases, including 288 shared immutable-input cases. It computes expected results directly from original input limbs. All 14 invalid structural inputs exited with code 101. Twelve semantic mutations of the actual caller and capacity obligations produced genuine verification-condition failures; all 108 mixed-diagnostic fixtures were rejected.

The [independent review](evidence/root-independent-audit.json) rechecked identities, integer results, saved runner outputs, and malformed inputs. Three reachable code-generation roots passed inspection for allocator, general-division, and element-bounds-panic paths. Generated-code inspection does not establish speed.

[Development evidence](development/index.json) retains the focused three-item passing proof. The [publication map](publication.json) binds exact source bytes and explicitly redacted host paths. Compiled binaries and the oracle-output body are omitted; their hashes remain in the reports. There was no timing run, default-policy change, or consumer-pin change.

## Reproduce

Run from the repository root:

```sh
python3 experiments/toom8-primitives/product/audit.py
python3 experiments/toom8-primitives/product/test_prepare_boundaries.py
python3 experiments/toom8-primitives/product/prepare.py --output /tmp/verigmp-product
```

The audit rechecks saved identities, strict diagnostics, independent integer expectations, and code-generation reachability. Preparation reconstructs all 122 source inputs exactly and refuses an existing output directory.

For a fresh Linux proof and oracle run, use the repository's pinned Verus toolchain, set `VERUS_BIN`, and add `--verify` to the preparation command. Saved-evidence audits and preparation checks do not claim that a complete fresh-reproduction command has already run.