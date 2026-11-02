# Dedicated recursive Toom8 full square

This experiment proves a dedicated fifteen-child recursive full-square implementation. Each point is evaluated once, then passed to an actual recursive square; it is not a generic product called with duplicate operands. All numeric interpolation and recomposition premises are established by the implementation. This feature contains no timing result or GMP-parity claim.

## Contract, recursion and workspace

The [full-square entry](candidate/native/verified/toom8_recursive_square.rs) accepts a positive length `n` of arbitrary `u64` limbs, output of `2*n` limbs, caller scratch of at least `10*n` limbs and an outer threshold at least 56. At or below the threshold it uses the previously verified dedicated Toom4 square with fixed leaf threshold 24. Original standalone helpers and the accepted multiplication path are unchanged.

Above the threshold, `k=ceil(n/8)`, `h=n-7*k` and `m=k+1`. Endpoint squares have lengths `k` and `h`; thirteen interior squares have length `m`. All child sizes are strictly smaller than `n`. The actual mutual recursion decreases a lexicographic pair of input length and finite helper rank.

Only one evaluated operand of `m` limbs is needed per point. Together with reusable `10*m` child workspace it occupies `11*m` limbs. The coefficient bank occupies at most `30*m` limbs. The actual proof establishes `41*m <= 10*n` for the recursive branch and justifies the borrowed disjoint slices and reused lifetimes.

The analytic work bound is `S(n) <= S(k) + S(h) + 13*S(k+1) + O(n)` at fixed arity and threshold. This is an analytic recurrence, not checked machine-cost instrumentation or a measured performance result.

## Evidence

The frozen [gate](evidence/verification.json) binds 140 inputs, 21 tools, three actual runner runtime libraries including the loader, four compiled artifacts and 35 completed commands. Full library, runner and code-generation builds each verified 549 items with zero errors.

The independent integer oracle checks 765 squares, including zero, maximal, even-block-only, odd-block-only and random inputs, with 153 cases per pattern. Cases reach 4,096 limbs and cover thresholds 56, 96 and 192 and predicted recursive depths zero through three. All 12 malformed harness inputs exited with code 101. Fourteen genuine semantic failures include an actual caller termination mutant; all 126 appended fatal-diagnostic combinations were rejected.

The [independent audit](evidence/root-independent-audit.json) rechecked identities, integer outputs and the saved executable and examined the unchanged proof boundary. Two reachable code-generation entries passed inspection for allocator, general-division and element-bounds-panic paths. Such inspection does not establish speed.

[Development evidence](development/index.json) retains the focused three-item square caller and full 549-item library proofs. [Publication mappings](publication.json) preserve exact sources and identify host-path redaction in evidence. Compiled binaries and the large oracle-output body are omitted, with their hashes retained.

Dedicated low-square composition, production policy, timing, GMP parity and whole-machine cost remain outside this feature. Neither production defaults nor consumer pins change.

## Reproduce

From the repository root:

```sh
python3 experiments/toom8-primitives/square/audit.py
python3 experiments/toom8-primitives/square/test_prepare_boundaries.py
python3 experiments/toom8-primitives/square/prepare.py --output /tmp/verigmp-square
```

The audit rechecks saved identities, strict diagnostics, independent integers and code-generation reachability. Preparation reconstructs all 140 source inputs exactly and rejects existing or escaping output paths.

For a fresh Linux proof and oracle run, use the pinned Verus toolchain, set `VERUS_BIN` and add `--verify` to the preparation command. The saved-evidence audit and reconstruction do not claim that the complete fresh-reproduction command has already run.
