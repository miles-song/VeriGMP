# Toom-4 interpolation fusion experiment

This archive preserves an actual Rust refinement for four fused scaled-subtraction groups inside Toom-4 interpolation and its complete experiment. The candidate remains experimental: **target_not_met**. Neither production dispatch nor consumer dependency pins are promoted.

The source transformation removes eight selected buffer passes per interpolation node, but the two complete timing runs do not establish a stable overall improvement. Across the 52 groups, the candidate/previous median is 0.99846 in run 1 and 1.00221 in run 2. Sixteen groups regress against the previous experimental control in both runs. All results remain available.

## Controls and implementation

| Mode | Name | Meaning |
|---|---|---|
| 0 | Baseline | Canonical production dispatch at `e22a4dd00a28681fd27d68e2a78fa304cf17563e`. |
| 1 | Previous control | Exact frozen source bytes of the odd-division candidate archived at `6d4d967d69d1c1928f0394b1c2c3a348bd99537c`; this experimental control already missed the GMP target. |
| 2 | Fusion candidate | The same entry, recursion and threshold policies, with exactly four scaled-subtraction groups fused inside Toom-4 interpolation. |
| 3 | GMP | Full multiplication or squaring, followed by copying the requested low words and masking the top word. |

The [generic helper](overlay/candidate/native/verified/scaled_subtraction.rs) refines the independently stated integer equation `value(dst_after) = value(dst_before) - word * value(rhs)`. Its domain preserves every u64 multiplier, including zero and MAX, empty inputs, and any right operand no longer than the destination, under the nonnegative-result precondition. Rust's exclusive mutable borrow protects the output from aliasing the immutable input.

One combined carry is bounded by `word`. The proof covers the full-u64 corner where the wide product's high word equals `word`: its low word must then be zero, so the subsequent subtraction cannot borrow. Thus `high + borrow` remains representable even when `word=MAX`. A prefix invariant relates the partial destination and carry to the original integer difference; the final nonnegative bound eliminates the carry. The function body is reused from the previously verified public single-carry experiment, with provenance and the exact body hash in [origin.json](origin.json).

The four [interpolation updates](overlay/candidate/native/verified/toom4_interpolate.rs) are `pmh -= 64*z0`, `p2 -= 4*c2`, `p2 -= 16*c4`, and `p2 -= 64*z6`. Each replaces copy-pad, scale and subtract passes with one pass. All existing interpolation postconditions remain, including `scratch=c3` and `p2=3*c3`. Scratch has not been removed, and caller capacities remain 12n limbs for multiplication and 10n for squaring. No Toom-3 path or threshold changes are included.

The helper uses constant temporary runtime storage and has an analytic O(n) word-operation bound. The [scope record](scope.json) keeps the full Toom-4 majorant `T_full(n) <= 2T_full(k) + 5T_full(m) + O(n) <= 7T_full(m) + O(n)`, where `k=ceil(n/4)` and `m=k+1`; low-product and low-square call structures are recorded separately. These derivations are not checked machine-cost theorems. [Pinned Toom-4 references](gmp-toom4-reference.json) and [odd-division references](gmp-odd-reference.json) identify the GMP sources used as algorithmic references; this archive contains independent Rust implementations and proofs.

## Verification and generated code

The [immutable gate](evidence/verification.json) records 234, 289 and 298 verified items for the baseline, previous and candidate libraries. The candidate runner and codegen crate each have 298 verified items; counts cover imported modules, not just the new helper. The gate passes 35,555 independent integer cases, including 5,655 new helper cases, rejects 30 invalid harness commands and rejects 40 targeted semantic mutants. A harness rejection does not turn a verified function's precondition into a runtime guard.

Five existing standalone entry crates pass fresh verification and optimized compilation: `mac4_bench` has 244 items, and `square_base_bench`, `toom_codegen`, `toom_words_runner` and `toom_bench` have 248 each. Their benchmark programs were not executed by that compatibility check.

The gate binds 230 source inputs, 21 tool files, three runtime libraries, three compiled-library/verification-metadata pairs and nine generated artifacts. [Independent prebenchmark review](evidence/root-prebenchmark-audit.json) additionally replays all 5,655 new helper cases against independently computed integer answers. The [local identity audit](evidence/final-audit.json) and the raw positive and negative logs are included. Verus, vstd, Z3, Rust and LLVM remain trusted dependencies. Comparison-only GMP FFI and the test infrastructure are outside the verified arithmetic core; no new arithmetic trust escape is introduced.

[Reachable code inspection](fusion_codegen.py) covers the generic full-u64 helper and constant 4/16/64 specializations: no allocator, general division or per-element bounds panic is present. The existing length-precondition panic remains. This is assembly inspection, not a machine-code proof.

The [actual matched-binary inventory](evidence/fusion-mechanism-audit.json) counts 40 to 32 selected source operations, 1,242 to 923 interpolation instructions after removing `int3` and alignment nops, and 81 to 59 backward branches. The multiply-instruction count stays 19. The [entry audit](evidence/entry-path-audit.json) finds matching normalized `mul_mod` and `square_large` entry bodies and 12 shared kernels. Static counts do not establish dynamic instruction counts, memory bottlenecks, timing equivalence or causal speedup.

## Complete performance result

Two independent complete runs each contain 52 operation/precision groups, four modes and seven repetitions: 1,456 recorded batches per run. Mode order rotates by repetition. Inputs, precision, output semantics and allocation boundaries match. Every actual batch lasts at least 10 ms; minima are 10.016769 ms and 10.022112 ms. The [controller record](evidence/confirmation-window.json) preserves the quiet preflight and both bindings. No result-based rerun or sample selection occurred.

All 10 principal workloads exceed GMP in both runs. The 1.2-times-GMP limit fails for 32 of 52 groups in run 1 and 34 in run 2, with 32 failing in both. Baseline regressions number 17 and 28, with 13 repeated; previous-control regressions number 25 and 28, with 16 repeated. Fifteen groups improve against the previous control in both runs. The candidate/GMP median across all 52 groups is 1.25451 / 1.26963; the maximum is 2.08164 / 2.05968. These ratios do not carry a statistical-significance claim.

The principal matrix gives run 1 / run 2. Values below 1 mean a lower candidate median. All rows have `top=63`. These are `mul_mod` and `square_mod` timings against GMP full-then-truncate, not separately measured full kernels.

| Operation | Limbs | Candidate / baseline | Candidate / previous | Candidate / GMP |
|---|---:|---:|---:|---:|
| mul_mod | 256 | 0.99742 / 0.98394 | 0.99512 / 0.99826 | 1.47704 / 1.49298 |
| mul_mod | 512 | 0.98295 / 0.96515 | 0.99288 / 0.99572 | 1.70267 / 1.68181 |
| mul_mod | 1024 | 0.93632 / 0.97063 | 0.97030 / 0.97222 | 1.76307 / 1.80114 |
| mul_mod | 2048 | 0.90430 / 0.89879 | 0.99648 / 0.97124 | 1.89910 / 1.88294 |
| mul_mod | 4096 | 0.90662 / 0.90297 | 0.99423 / 0.94568 | 2.08164 / 2.05968 |
| square_mod | 256 | 0.99824 / 1.01235 | 0.98606 / 1.03257 | 1.33863 / 1.36267 |
| square_mod | 512 | 0.93443 / 0.95873 | 0.95370 / 0.93815 | 1.41474 / 1.41855 |
| square_mod | 1024 | 0.94577 / 0.92514 | 1.02158 / 0.98673 | 1.71019 / 1.65191 |
| square_mod | 2048 | 0.93109 / 0.92134 | 0.97256 / 0.96705 | 1.79647 / 1.69567 |
| square_mod | 4096 | 0.85727 / 0.84079 | 0.96988 / 0.97825 | 1.84092 / 1.83190 |

Every group that regresses against either control in both runs is shown here. An entry in the other ratio column may be an improvement.

| Operation | Limbs | Top | Candidate / baseline | Candidate / previous | Repeats against |
|---|---:|---:|---:|---:|---|
| mul_mod | 1 | 1 | 0.99505 / 1.00304 | 1.01760 / 1.00719 | Previous |
| mul_mod | 23 | 63 | 1.01664 / 1.01496 | 1.02646 / 1.00002 | Both |
| mul_mod | 24 | 63 | 1.01991 / 0.98069 | 1.02645 / 1.00565 | Previous |
| mul_mod | 25 | 63 | 1.00455 / 1.00859 | 1.00964 / 1.00694 | Both |
| mul_mod | 63 | 63 | 0.99786 / 1.02094 | 1.01684 / 1.02032 | Previous |
| mul_mod | 128 | 63 | 1.03838 / 1.03418 | 1.00536 / 1.02337 | Both |
| mul_mod | 129 | 63 | 0.99723 / 1.01300 | 1.00355 / 1.02416 | Previous |
| mul_mod | 191 | 63 | 1.00673 / 1.01761 | 1.00897 / 1.01154 | Both |
| mul_mod | 193 | 63 | 1.00817 / 1.00436 | 1.01347 / 1.01190 | Both |
| mul_mod | 257 | 63 | 1.01352 / 1.00622 | 1.00695 / 0.99378 | Baseline |
| square_mod | 1 | 1 | 0.95193 / 0.99612 | 1.00226 / 1.01746 | Previous |
| square_mod | 2 | 1 | 0.94674 / 0.95764 | 1.01135 / 1.00509 | Previous |
| square_mod | 24 | 63 | 0.98503 / 1.03106 | 1.00523 / 1.00753 | Previous |
| square_mod | 25 | 63 | 1.00340 / 1.02716 | 1.02843 / 1.00911 | Both |
| square_mod | 63 | 63 | 1.02606 / 0.96702 | 1.01032 / 1.00624 | Previous |
| square_mod | 128 | 63 | 1.01526 / 1.04822 | 0.99026 / 1.03343 | Baseline |
| square_mod | 129 | 63 | 1.00592 / 1.01619 | 1.01132 / 1.01103 | Both |
| square_mod | 191 | 63 | 1.02200 / 1.00618 | 0.99816 / 1.01055 | Baseline |
| square_mod | 192 | 63 | 1.01732 / 1.02519 | 1.00637 / 1.01431 | Both |
| square_mod | 193 | 63 | 1.02293 / 1.01601 | 1.01743 / 0.98991 | Baseline |
| square_mod | 255 | 63 | 1.00548 / 1.01280 | 1.01779 / 0.98997 | Baseline |

The raw [first run](evidence/default1/benchmark.csv) and [confirmation run](evidence/default2/benchmark.csv), [all 104 summarized groups](evidence/performance-summary.json), [complete repeated-outcome lists](evidence/performance-comparison.json) and [sealed result receipt](evidence/measurement-result.json) retain every registered result. An [independent final audit](evidence/root-performance-audit.json) rechecks all 2,912 raw records and the final receipt identity. The receipt's external SHA-256 is `9d65657902cadc76e3abf68b8ca4da71e638b1b4c391a481607f6e4047f466e1`; it contains no self-hash field. Performance remains **target_not_met**, and the candidate is not promoted.

## Reproduce

The public audit uses Python 3.12 and needs no verifier or benchmark binary:

```sh
python3 experiments/toom4-fusion/audit.py
python3 experiments/toom4-fusion/prepare.py --output /tmp/verigmp-fusion-prepare
```

Preparation reconstructs all 230 frozen input files exactly from the pinned commit and overlays, and refuses to overwrite an existing directory. Preparation passes on Windows and in an [independent Linux clone of the baseline with the public archive](reconstruction-linux-check.json). The [preparation record](reconstruction-check.json) is a source-reconstruction check, not a fresh proof or timing replay. A full proof and timing replay from this public archive has not been run.

For a fresh gate, use x86-64 Linux or WSL, GMP development libraries and the [pinned toolchain](../../native/toolchain.json). Install Verus with `python3 scripts/setup_verus.py`, follow the [verification instructions](../../docs/verification.md), and set `VERUS_BIN` to its executable. Use a new output directory for every command:

```sh
python3 experiments/toom4-fusion/prepare.py --output /tmp/verigmp-fusion-proof --verify
python3 experiments/toom4-fusion/prepare.py --output /tmp/verigmp-fusion-timing --benchmark
```

`--benchmark` first runs a fresh gate, then attempts the two registered complete runs and recomputes their matrix. It requires a quiet CPU 0 window. Failed preflight and acceptance attempts remain failure records. After a fresh gate, run `audit_entry_paths.py` followed by `audit_fusion_mechanism.py` inside the reconstructed output directory to regenerate the optional matched-binary inspection, using GNU objdump and readelf.

## Archive boundary

[publication.json](publication.json) maps original and published hashes. Rust, Python and raw CSV bytes remain exact. Selected historical host paths in reports, logs and assembly listings become logical placeholders. Executables, libraries and the large oracle output are represented by digests and rebuilt by fresh verification. Independent audit results are included without private application code or dependencies.

The earlier development gate and retained launcher diagnostics are included as historical records; the final gate is the accepted source snapshot. The unsealed development result draft is explicitly excluded from final receipt identity; [measurement-result-seal.json](evidence/measurement-result-seal.json) binds both its original bytes and the final receipt. This archive contains generic arithmetic only. Production `native/` and `scripts/` trees are unchanged.