# Toom-4 signed evaluation experiment

This archive preserves a verified Rust implementation of single-pass signed Toom-4 evaluation and its complete measured result. Performance remains **target_not_met**. Production dispatch and consumer dependency pins are unchanged.

The implementation reduces selected source-level buffer writes, but two complete timing runs do not establish a stable overall improvement. Across 52 operation/precision groups, the candidate/previous median is 0.99982 in run 1 and 1.00065 in run 2. Twelve groups regress against the previous experimental control in both runs; twelve improve in both. All observations remain available.

## Controls and implementation

| Mode | Name | Meaning |
|---|---|---|
| 0 | Baseline | Canonical production dispatch at `e22a4dd00a28681fd27d68e2a78fa304cf17563e`. |
| 1 | Previous control | Exact frozen source bytes of the interpolation-fusion candidate archived at `6a6cd3509ec42013513eb9793fdae948726722aa`; this experimental control already missed the GMP target. |
| 2 | Signed-evaluation candidate | The same dispatch, recursion, thresholds and interpolation, with signed Toom-4 evaluation replaced by a weighted carry pass and optional in-place negation. |
| 3 | GMP | Full multiplication or squaring, followed by copying the requested low words and masking the top word. |

The [independent specification](overlay/candidate/native/specs/signed_evaluation.rs) defines the integer values `a0-a1+a2-a3` and `8*a0-4*a1+2*a2-a3` from the four input blocks. The [actual implementation](overlay/candidate/native/verified/signed_evaluation.rs) refines these values to a sign and magnitude. All input limbs retain the full u64 domain. The scalar carry contract covers every integer from −5 through 10. A bias of 16 times the word radix makes the signed i128 total nonnegative before its u128 power-of-two split. A prefix invariant composes this scalar equation across the input, and a negative result is converted to magnitude by a verified in-place modular negation.

The existing [Toom-4 evaluation interface](overlay/candidate/native/verified/toom4_evaluate.rs) and its postconditions remain. The new implementation preserves every byte of `tmp`, stronger than the existing length-only postcondition. Rust's exclusive mutable borrows retain the slice aliasing boundary. Empty or shorter top blocks are handled under the existing block-length constraints. No Toom-3 path, interpolation formula or threshold changes are included.

The old path writes `3*(k+1)` limbs across two weighted evaluations and a magnitude subtraction. The new path writes `(1+negative)*(k+1)` limbs: one signed carry pass and, only for a negative value, one negation pass. These source-level counts exclude compiler transformations. Both have an analytic O(k) word-operation bound; the new helper uses O(1) internal extra words. Caller workspace remains 12n limbs for multiplication and 10n for squaring. No scratch allocation has been removed.

The [scope record](scope.json) separates refinement from analytic recurrences and observed timing. The full Toom-4 majorant remains `T_full(n) <= 2T_full(k) + 5T_full(m) + O(n) <= 7T_full(m) + O(n)`, where `k=ceil(n/4)` and `m=k+1`. Low-product and low-square call structures are recorded separately. These are analytic bounds, not checked machine-cost theorems. [Pinned Toom-4](gmp-toom4-reference.json) and [odd-division](gmp-odd-reference.json) references identify relevant GMP sources; the Rust implementations and proofs are independent.

## Verification and generated code

The [immutable gate](evidence/verification.json) records 234, 298 and 311 verified items for the baseline, previous and candidate libraries. The candidate runner and codegen crate each have 311 items; counts include imported modules. The independent integer oracle passes 60,755 cases, including 25,200 new signed-evaluation cases: 21,024 scalar cases, 144 negations and 4,032 array cases. It covers all scalar carry values, full-word boundaries, empty/short top blocks, output canaries and unchanged `tmp` contents. The gate rejects 38 invalid harness commands and 49 targeted semantic mutants through actual verification-condition failures. A harness rejection does not turn a verified function's precondition into a runtime guard.

Five existing standalone entry crates pass fresh verification and optimized compilation: `mac4_bench` has 244 items; `square_base_bench`, `toom_codegen`, `toom_words_runner` and `toom_bench` have 248 each. Their benchmark programs were not executed by this compatibility check.

The gate binds 235 source inputs, 21 tool files, three runtime libraries, three compiled-library/verification-metadata pairs and nine generated artifacts. The [independent prebenchmark review](evidence/independent-prebenchmark-audit.json), [local final audit](evidence/final-audit.json) and raw positive/negative diagnostics are included. Verus, vstd, Z3, Rust and LLVM remain trusted dependencies. Comparator-only GMP FFI and test infrastructure remain outside the verified arithmetic core. No new trust escape is introduced.

[Code inspection](signed_codegen.py) checks the reachable scalar, negation and signed-evaluation functions for unwanted allocation and general division. The [actual matched benchmark inspection](evidence/static-mechanism.json) counts 284 to 153 signed-evaluation instruction lines after excluding `int3` and alignment nops. The [entry-path audit](evidence/entry-path-audit.json) finds matching normalized `mul_mod` and `square_large` entry bodies and 12 shared kernels after normalizing branch and ELF/GOT references. Reference normalization does not establish equality of referenced data bytes or formal machine-code equivalence. Static counts do not prove dynamic operation counts, a memory bottleneck, timing equivalence or causal speedup.

## Complete performance result

Two independent complete runs each contain 52 groups, four modes and seven repetitions: 1,456 batches per run and 2,912 in total. Mode order rotates by repetition. Inputs, precision, output semantics and allocation boundaries match. Every recorded batch lasts at least 10 ms; minima are 10.002904 ms and 10.005125 ms. The [controller record](evidence/confirmation-window.json) retains the quiet preflight and both bindings. Measurement started at 2026-11-01 23:24:55.742100 UTC and ended at 23:26:13.919611 UTC. No result-based rerun or sample selection occurred.

All 10 principal workloads exceed GMP in both runs. The 1.2-times-GMP limit fails for 33 of 52 groups in run 1 and 34 in run 2, with 33 failing in both. Baseline regressions number 17 and 19, with 12 repeated; previous-control regressions number 25 and 27, with 12 repeated. Twelve groups improve against the previous control in both runs. The candidate/GMP median across all 52 groups is 1.23603 / 1.27390; the maximum is 1.97129 / 2.09641. These ratios carry no statistical-significance claim. The [independent postmeasurement audit](evidence/root-performance-audit.json) recomputes all 2,912 records, mode order, medians, failures and repeated outcomes.

The principal matrix gives run 1 / run 2. Values below 1 mean a lower candidate median. Every row has `top=63`. These are `mul_mod` and `square_mod` timings against GMP full-then-truncate, not separately measured full kernels.

| Operation | Limbs | Candidate / baseline | Candidate / previous | Candidate / GMP |
|---|---:|---:|---:|---:|
| mul_mod | 256 | 1.03188 / 1.00936 | 1.02222 / 1.00472 | 1.50718 / 1.52240 |
| mul_mod | 512 | 0.93984 / 0.96235 | 1.00931 / 0.99542 | 1.65319 / 1.67398 |
| mul_mod | 1024 | 0.93832 / 0.92513 | 0.99443 / 1.00254 | 1.75804 / 1.72984 |
| mul_mod | 2048 | 0.90640 / 0.90250 | 0.99490 / 1.00754 | 1.91138 / 1.87980 |
| mul_mod | 4096 | 0.93596 / 0.90982 | 1.00686 / 0.99971 | 1.97129 / 2.09641 |
| square_mod | 256 | 1.03468 / 1.00016 | 1.02478 / 1.00431 | 1.37200 / 1.33134 |
| square_mod | 512 | 0.97382 / 0.97678 | 1.01180 / 1.00381 | 1.40795 / 1.41776 |
| square_mod | 1024 | 0.93454 / 0.95178 | 1.00053 / 1.00405 | 1.71919 / 1.72516 |
| square_mod | 2048 | 0.92832 / 0.92599 | 0.99986 / 0.98306 | 1.74496 / 1.75037 |
| square_mod | 4096 | 0.85182 / 0.85572 | 0.99481 / 1.01477 | 1.83281 / 1.79687 |

Every group that regresses against either control in both runs is shown here. An entry in the other ratio column may be an improvement.

| Operation | Limbs | Top | Candidate / baseline | Candidate / previous | Repeats against |
|---|---:|---:|---:|---:|---|
| mul_mod | 23 | 63 | 1.01647 / 1.00744 | 1.01727 / 0.99580 | Baseline |
| mul_mod | 24 | 63 | 1.01095 / 1.01250 | 1.00094 / 0.99236 | Baseline |
| mul_mod | 25 | 63 | 1.00744 / 1.01442 | 1.01569 / 0.98467 | Baseline |
| mul_mod | 65 | 63 | 1.01015 / 0.99372 | 1.00928 / 1.01315 | Previous |
| mul_mod | 127 | 63 | 1.00416 / 1.00032 | 0.99801 / 1.00080 | Baseline |
| mul_mod | 129 | 63 | 0.99739 / 0.97325 | 1.00673 / 1.00287 | Previous |
| mul_mod | 256 | 63 | 1.03188 / 1.00936 | 1.02222 / 1.00472 | Both |
| mul_mod | 511 | 63 | 1.01746 / 1.00039 | 1.00851 / 0.99000 | Baseline |
| mul_mod | 513 | 63 | 0.99266 / 0.94799 | 1.02998 / 1.00154 | Previous |
| square_mod | 23 | 63 | 0.98047 / 0.97792 | 1.01819 / 1.00317 | Previous |
| square_mod | 24 | 63 | 1.00492 / 1.02100 | 1.02339 / 1.00944 | Both |
| square_mod | 63 | 63 | 1.00752 / 1.02147 | 1.01960 / 1.01180 | Both |
| square_mod | 65 | 63 | 1.00302 / 1.00231 | 1.01654 / 0.99027 | Baseline |
| square_mod | 128 | 63 | 1.01039 / 1.01464 | 0.98605 / 1.01430 | Baseline |
| square_mod | 193 | 63 | 0.99933 / 1.00115 | 1.00324 / 1.02444 | Previous |
| square_mod | 256 | 63 | 1.03468 / 1.00016 | 1.02478 / 1.00431 | Both |
| square_mod | 511 | 63 | 1.00028 / 1.00825 | 0.99042 / 0.99555 | Baseline |
| square_mod | 512 | 63 | 0.97382 / 0.97678 | 1.01180 / 1.00381 | Previous |
| square_mod | 1024 | 63 | 0.93454 / 0.95178 | 1.00053 / 1.00405 | Previous |
| square_mod | 1025 | 63 | 0.93967 / 0.96234 | 1.00177 / 1.00667 | Previous |

The raw [first run](evidence/default1/benchmark.csv) and [confirmation run](evidence/default2/benchmark.csv), [all 104 summarized groups](evidence/performance-summary.json), [complete repeated-outcome lists](evidence/performance-comparison.json) and [sealed receipt](evidence/measurement-result.json) retain every registered result. The original receipt's external SHA-256 is `19bc77db784a58d32925a38cc3871ce4052a1f707d2bfc943e194c5a97ca587c`; it contains no self-hash field. Its historical pending-review field is preserved; the later independent postmeasurement audit records the completed review. Performance remains **target_not_met**, with no promotion.

## Reproduce

The public audit uses Python 3.12 and needs no verifier or benchmark binary:

```sh
python3 experiments/toom4-signed-eval/audit.py
python3 experiments/toom4-signed-eval/prepare.py --output /tmp/verigmp-signed-prepare
```

Preparation reconstructs all 235 frozen inputs exactly from the pinned commit and overlays, and refuses to overwrite an existing directory. The [preparation record](reconstruction-check.json) checks source reconstruction; it is not a fresh proof or timing replay. A full proof and timing replay from this public archive has not been run.

For a fresh gate, use x86-64 Linux or WSL, GMP development libraries and the [pinned toolchain](../../native/toolchain.json). Install Verus with `python3 scripts/setup_verus.py`, follow the [verification instructions](../../docs/verification.md), and set `VERUS_BIN` to its executable. Use a new output directory for every command:

```sh
python3 experiments/toom4-signed-eval/prepare.py --output /tmp/verigmp-signed-proof --verify
python3 experiments/toom4-signed-eval/prepare.py --output /tmp/verigmp-signed-timing --benchmark
```

`--benchmark` first runs a fresh gate, then attempts the two registered complete runs and recomputes their matrix. It requires a quiet CPU 0 window. Failed preflight and acceptance attempts remain failure records. The saved matched-binary entry inventory is historical inspection evidence; the public gate regenerates its own proof, oracle, mutation and codegen checks.

## Archive boundary

[publication.json](publication.json) maps original and published hashes. Rust, Python and raw CSV bytes remain exact. Selected historical host paths in reports, logs and assembly listings become logical placeholders. Executables, libraries and the large oracle output are represented by digests and rebuilt during fresh verification. Independent audit results have no private application code or dependencies.

The failed first focused development proof, subsequent successful focused proof and successful library proof are retained as historical records. The immutable final gate is the accepted source snapshot. This archive contains generic arithmetic only. Production `native/` and `scripts/` trees are unchanged.