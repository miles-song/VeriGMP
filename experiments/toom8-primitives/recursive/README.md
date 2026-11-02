# Recursive Toom8 full multiplication

This experiment proves the actual recursive fifteen-child Toom8 full-product implementation. Original full-u64 input limbs flow through evaluation, child multiplication, interpolation and recomposition; the actual implementation establishes every numeric helper premise. This feature has no timing result or GMP-parity claim. Dedicated square and low-product routines are separate later features.

## Actual recursion and workspace

The [full-product entry](candidate/native/verified/toom8_recursive_product.rs) accepts positive equal-length inputs, an output of `2*n` limbs, caller scratch of at least `12*n` limbs and an outer threshold at least 56. At or below that threshold it calls the unchanged verified Toom4 kernel with child threshold 24. Existing standalone nonrecursive helpers retain their original domains.

For a recursive call, `k=ceil(n/8)`, `h=n-7*k` and `m=k+1`. The implementation computes endpoint products of lengths `k` and `h` plus thirteen interior products of length `m`. Each child is strictly smaller than `n`. The mutually recursive helper chain has a checked lexicographic decreases measure: input limb count followed by a finite helper rank. A deliberately invalid helper rank is rejected as a termination verification-condition failure.

The coefficient bank occupies `26*m + 2*k + 2*h <= 30*m` limbs. Evaluation operands and a reused `12*m` child workspace need another `14*m`. The actual capacity proof establishes `44*m <= 12*n` for `n>56` and justifies the borrowed disjoint slices through recursive calls. This is a proof of capacity and lifetime use, not a whole-machine memory measurement.

The analytic work bound is `T(n) <= T(k) + T(h) + 13*T(k+1) + O(n) <= 15*T(k+1) + O(n)` at fixed arity and threshold. It describes the actual child sizes but is not checked machine-cost instrumentation or a measured speed result.

## Evidence

The frozen [gate](evidence/verification.json) binds 131 source inputs, 21 tools, three actual runner runtime libraries including the loader, four compiled artifacts and 35 commands. Full library, runner and code-generation builds each verified 537 items with zero errors.

The 612 independent integer products include 306 shared immutable-input cases and sizes up to 4,096 limbs. Threshold and recursive-size boundaries exercise predicted depths from zero through three active Toom8 levels. All 12 malformed harness inputs exited with code 101. Fourteen semantic mutants were rejected, including the explicit termination mutant; all 126 appended fatal-diagnostic combinations were rejected.

The [independent audit](evidence/root-independent-audit.json) rechecked identities and integer expectations, replayed the saved runner, checked malformed inputs and inspected the proof boundary. Two actual code-generation roots passed the no-allocation, no-general-division and no-element-bounds-panic reachability inspection.

[Development evidence](development/index.json) retains the focused three-item proof, the full 537-item proof and the deliberately invalid helper rank. The negative rank experiment is expected rejection, not a successful arithmetic implementation. [Publication mappings](publication.json) preserve source bytes and identify host-path redaction in saved evidence. Compiled binaries and the large oracle-output body are omitted, with hashes retained.

This feature establishes recursive full multiplication. It does not establish low-product or dedicated-square composition, a default dispatch policy, measured GMP parity, a complete machine-cost theorem or an application-level counting complexity claim.

## Reproduce

From the repository root:

```sh
python3 experiments/toom8-primitives/recursive/audit.py
python3 experiments/toom8-primitives/recursive/test_prepare_boundaries.py
python3 experiments/toom8-primitives/recursive/prepare.py --output /tmp/verigmp-recursive
```

The audit rechecks saved identities, strict diagnostics, independent integer expectations and generated-code reachability. Preparation reconstructs all 131 source inputs exactly, refuses existing output directories and rejects escaping destination paths.

For a fresh Linux proof and oracle run, use the pinned Verus toolchain, set `VERUS_BIN` and add `--verify` to the preparation command. Saved-evidence audits and reconstruction do not claim that a complete fresh-reproduction command has already run.