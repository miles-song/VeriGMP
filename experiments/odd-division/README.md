# Odd exact division experiment

This archive preserves a verified low-to-high exact-division implementation for divisors 3, 9 and 15 and its complete performance experiment. The candidate remains experimental: the registered GMP target is **target_not_met**. Production dispatch and consumer dependency pins are unchanged.

The largest tested modular operations improve modestly against the previous experimental control, but 13 smaller groups regress against that control in both runs. The full matrix and all negative results remain available.

## Controls and implementation

| Mode | Name | Meaning |
|---|---|---|
| 0 | Baseline | Canonical production dispatch at `e22a4dd00a28681fd27d68e2a78fa304cf17563e`. |
| 1 | Previous control | Exact frozen source bytes of the entry candidate archived at `3361734df5489e0f4bb316bdff71d02bb7fc6f3a`; it already missed the registered GMP target. |
| 2 | Odd-division candidate | The same entry and recursive policies, using the new exact-division kernel for 3, 9 and 15. |
| 3 | GMP | Full multiplication or squaring, followed by copying the requested low words and masking the top word. |

The frozen measurement reports retain historical `mode_names` display labels. Modes 0–3 have the actual identities in this table, established by their frozen source and linked library hashes; the [machine-readable mapping](mode-identities.json) ties each label to those artifacts. The original scripts, reports and raw CSV bytes remain unchanged.

The [independent specification](overlay/candidate/native/specs/odd_division.rs) states radix-unit identities. The [actual Rust kernel](overlay/candidate/native/verified/odd_division.rs) processes low limbs first with a fixed inverse modulo `B=2^64`. Its scalar relation is `d*q+carry = x+B*next`, with `next<d`. The array invariant composes these relations over prefixes. Exact divisibility of the original integer, cancellation of the radix power modulo d, and the final carry bound imply that the final carry is zero.

The direct helper accepts every u64 input word and every carry smaller than its selected divisor. Exact arrays may be empty. The existing [divide_exact API](overlay/candidate/native/verified/toom_words.rs) retains its complete positive-u64 divisor domain and exact-input precondition; divisors other than 3, 9 and 15 use the existing implementation. No interpolation fusion, threshold change or new trusted arithmetic escape is included.

The loop operates in place with constant runtime temporary storage. The source-level O(n) word-operation derivation is distinct from a checked machine-cost theorem; none is claimed. Product and square entry meanings, borrowing rules and caller scratch capacities remain unchanged at 12n and 10n limbs. The [scope record](scope.json) retains the full Toom-4 recurrence boundary. [Pinned GMP references](gmp-odd-reference.json) document algorithmic references; GMP source code is not copied into this independently implemented and proved kernel.

## Verification evidence

The [final immutable gate](evidence/verification.json) records 234, 276 and 289 verified items for the baseline, previous control and candidate libraries. The candidate runner and codegen crate each contain 289 verified items. Counts cover their imported modules, not only the new routines.

The same snapshot passes 29,900 independent integer cases: the existing 25,062 cases plus 4,838 new scalar, direct-odd and existing-API cases. It rejects 22 invalid runner commands and 30 targeted semantic mutants. Invalid commands are rejected by the test harness; this does not turn a verified function's precondition into an automatic runtime check.

Five existing standalone entry crates also pass fresh verification and optimized compilation: `mac4_bench` has 244 verified items; `square_base_bench`, `toom_codegen`, `toom_words_runner` and `toom_bench` each have 248. Their benchmark programs were not executed by that compatibility check.

The gate binds 225 source inputs, 21 tool files, three runtime libraries, three matching compiled-library/verification-metadata pairs and nine generated artifacts. [Independent prebenchmark review](evidence/root-prebenchmark-audit.json) and the [final local identity audit](evidence/final-audit.json) record these checks. Verus, vstd, Z3, Rust and LLVM remain explicit trusted dependencies; comparison-only GMP FFI and runners remain outside the verified arithmetic core.

The emitted existing-API entry paths specialized to 3, 9 and 15 contain no allocator, general division, per-element bounds panic or external call. This is [reachable assembly inspection](odd_codegen.py), not a formal machine-code proof. The [matched-binary audit](evidence/entry-path-audit.json) finds identical normalized bodies for 12 shared kernels. Address, label and data-reference normalization does not establish timing equivalence or explain the repeated small-size regressions.

## Complete performance result

Two independent complete runs each contain all 52 registered operation/precision groups, four modes and seven repetitions: 1,456 records per run. Mode order rotates by repetition. Inputs, allocation boundaries and output semantics match. Every actual recorded batch is at least 10 ms; the observed minima are 10.013802 ms and 10.005129 ms. The [controller record](evidence/confirmation-window.json) preserves the quiet-process preflight and both run bindings.

All 10 principal workloads exceed GMP in both runs. The 1.2-times-GMP limit fails for 31 of 52 groups in run 1 and 34 in run 2. Baseline regressions number 19 and 17, with 9 repeated in both runs. Previous-control regressions number 23 and 22, with 13 repeated in both runs; 20 groups improve against that control in both runs. These are observed ratios, with no statistical-significance or causal claim.

The following principal matrix gives run 1 / run 2. Ratios below 1 mean a lower candidate median. All rows have `top=63`. These are `mul_mod` and `square_mod` timings against GMP full-then-truncate, not separately measured full-product kernels.

| Operation | Limbs | Candidate / baseline | Candidate / previous | Candidate / GMP |
|---|---:|---:|---:|---:|
| mul_mod | 256 | 0.99962 / 1.00164 | 1.01471 / 1.00509 | 1.47596 / 1.46913 |
| mul_mod | 512 | 0.98351 / 0.97179 | 0.98534 / 0.99240 | 1.69826 / 1.71534 |
| mul_mod | 1024 | 0.98806 / 0.93823 | 1.02393 / 0.98049 | 1.88958 / 1.77183 |
| mul_mod | 2048 | 0.91864 / 0.90107 | 0.99425 / 0.95789 | 1.93318 / 1.90626 |
| mul_mod | 4096 | 0.92527 / 0.91744 | 0.97933 / 0.98368 | 2.09346 / 2.09208 |
| square_mod | 256 | 0.95113 / 0.99292 | 0.99816 / 1.00908 | 1.32445 / 1.29690 |
| square_mod | 512 | 0.98315 / 0.96864 | 0.98090 / 0.99993 | 1.47387 / 1.45749 |
| square_mod | 1024 | 0.95126 / 0.96794 | 1.00083 / 0.99597 | 1.71289 / 1.70694 |
| square_mod | 2048 | 0.98013 / 0.97513 | 1.01900 / 0.97997 | 1.88189 / 1.88099 |
| square_mod | 4096 | 0.88220 / 0.88102 | 0.98450 / 0.96681 | 1.84208 / 1.83882 |

Every group that regresses against either control in both runs is listed here. The final column identifies the repeated regression; a ratio shown in another column may be an improvement.

| Operation | Limbs | Top | Candidate / baseline | Candidate / previous | Repeats against |
|---|---:|---:|---:|---:|---|
| mul_mod | 1 | 64 | 1.01120 / 1.00131 | 1.00429 / 1.01373 | Both |
| mul_mod | 24 | 63 | 1.00455 / 1.01664 | 0.96832 / 0.97617 | Baseline |
| mul_mod | 127 | 63 | 1.02825 / 0.98577 | 1.03015 / 1.01481 | Previous |
| mul_mod | 128 | 63 | 1.00529 / 1.01554 | 0.98544 / 0.98789 | Baseline |
| mul_mod | 129 | 63 | 1.04324 / 1.04979 | 1.02731 / 1.01742 | Both |
| mul_mod | 192 | 63 | 1.07194 / 1.00549 | 1.06591 / 1.00986 | Both |
| mul_mod | 255 | 63 | 1.01676 / 0.99792 | 1.02465 / 1.01443 | Previous |
| mul_mod | 256 | 63 | 0.99962 / 1.00164 | 1.01471 / 1.00509 | Previous |
| mul_mod | 511 | 63 | 1.00694 / 1.02283 | 1.01074 / 1.01577 | Both |
| square_mod | 2 | 1 | 0.95388 / 0.93322 | 1.03154 / 1.00337 | Previous |
| square_mod | 25 | 63 | 0.99203 / 0.97646 | 1.00033 / 1.00379 | Previous |
| square_mod | 63 | 63 | 0.99534 / 1.01095 | 1.00771 / 1.03931 | Previous |
| square_mod | 128 | 63 | 1.04564 / 1.06125 | 1.02593 / 1.01086 | Both |
| square_mod | 193 | 63 | 1.00115 / 1.00737 | 0.97965 / 0.99667 | Baseline |
| square_mod | 257 | 63 | 1.00352 / 1.01445 | 1.02117 / 1.02715 | Both |
| square_mod | 511 | 63 | 1.01058 / 0.99819 | 1.00144 / 1.00671 | Previous |

Raw data are [run 1](evidence/default1/benchmark.csv) and [run 2](evidence/default2/benchmark.csv). The [full 104-group summary](evidence/performance-summary.json), [complete repeated-outcome lists](evidence/performance-comparison.json) and [independent raw-data audit](evidence/root-performance-audit.json) preserve every registered result. No result-based rerun or sample selection was performed. The candidate is not promoted to production.

## Reproduce

The archive audit uses Python 3.12 and needs no verifier or benchmark binary:

```sh
python3 experiments/odd-division/audit.py
python3 experiments/odd-division/prepare.py --output /tmp/verigmp-odd-prepare
```

Preparation reconstructs all 225 frozen input files exactly from the pinned commit and published overlays and refuses to overwrite an existing directory. It was tested on Windows and from an independent Linux clone; the [reconstruction record](reconstruction-check.json) states that scope. A full proof and timing replay from the public clone has not been run.

For a fresh gate, use x86-64 Linux or WSL, GMP development libraries and the [pinned toolchain](../../native/toolchain.json). Install the verifier with `python3 scripts/setup_verus.py`, follow the [verification instructions](../../docs/verification.md), and set `VERUS_BIN` to its executable. Use a new output directory for each command:

```sh
python3 experiments/odd-division/prepare.py --output /tmp/verigmp-odd-proof --verify
python3 experiments/odd-division/prepare.py --output /tmp/verigmp-odd-timing --benchmark
```

`--benchmark` first performs a fresh gate, then attempts the two complete registered runs and recomputes their matrix. It requires a quiet CPU 0 window. A failed preflight or check remains a failure record. After a fresh gate, `python3 /tmp/verigmp-odd-proof/audit_entry_paths.py` regenerates the optional matched-binary inspection using GNU objdump and readelf.

## Archive boundary

[publication.json](publication.json) maps original and published hashes. Recorded Rust, Python and raw CSV bytes remain exact. Selected host paths in historical reports, logs and assembly listings are replaced by logical placeholders. Executables, libraries and the large oracle output are represented by hashes and rebuilt during fresh verification. Independent audit results are included without private application code or dependencies.

The [initial parse failure](attempts/parse1/diagnostic.log), [development proof failures](attempts/development2/diagnostic.log) and [earlier gate before legacy-entry coverage](attempts/initial-gate-before-legacy-imports/evidence/verification.json) remain available. The final gate includes all five corrected standalone imports. The production `native/` and `scripts/` trees remain unchanged; this archive contains generic arithmetic sources and evidence only.
