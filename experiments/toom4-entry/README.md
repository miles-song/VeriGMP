# Toom-4 entry experiment

**Status: functionally verified; `target_not_met`; production dispatch unchanged.**

This archive evaluates entry dispatch around the forced Toom-4 algorithm. It contains complete sources, proof records, machine-code inspections and both registered timing runs. The experiment does not establish GMP parity or a consistent improvement across sizes.

## What is compared

| Mode | Canonical name | Source and behavior |
|---|---|---|
| 0 | Baseline | Actual production dispatch at `e22a4dd00a28681fd27d68e2a78fa304cf17563e`. |
| 1 | Previous control | The forced Toom-4 algorithm archived at `1e78a6d8edd9c38d87f9578a23dbb1ac49f2c0e1`, with an explicit ghost-only proof stabilization. |
| 2 | Entry candidate | The same recursive algorithms and thresholds, with revised product and square entry functions. |
| 3 | GMP | Full multiplication or squaring, followed by copying the requested low words and masking the top word. |

The previous control is not byte-identical to its original archive. Both experimental libraries contain the same five-line proof addition in `add_shifted`. The [proof context record](proof-context.json), [patch](proof-context.patch) and [original failed gate](attempts/previous-crate-proof-context/verification.json) preserve that distinction. The addition changes no executable statements. Six inspected functions match the original archive after instruction normalization; that comparison is not a formal machine-code equivalence proof.

## Implementation and verification scope

The [entry source](overlay/candidate/native/verified/toom4_candidate.rs) makes two changes. Below 512 limbs, product dispatch calls the original small-product kernel directly. The small square body is inlined, while the large square body remains out of line. Recursive thresholds and split modes remain fixed at the values in [origin.json](origin.json).

The independent meaning remains the input integer product or square modulo `2^(64*(n-1)+top)`. Inputs are nonempty, `top` is between 1 and 64, and slice lengths match. Read-only operands may alias; mutable output and scratch remain exclusive. Verified caller-owned scratch requirements remain 12n limbs for products and 10n for squares.

The [complete gate](evidence/verification.json) records 234 verified items for the baseline, 274 for the previous control, and 276 for the candidate and its runner. These counts cover entire libraries, not newly added routines. The same snapshot passed 25,062 independent integer cases, rejected 8 invalid commands and rejected 20 semantic mutants. It binds 222 input files, imported library/verification pairs, compiler tools, runtime libraries and executable artifacts. [Independent review](evidence/root-independent-audit.json) checked these identities and every retained timing record.

The [matched-binary entry audit](evidence/entry-path-review.json) finds an identical normalized successful small-product trace relative to the baseline. The small square is inlined into the shared benchmark driver and tail-jumps to top-word normalization. Its size decision remains. This does not establish an instruction-identical square path or zero dispatch cost.

The [scope record](scope.json) separates functional refinement, caller-scratch bounds, analytic recurrences and observed timings. The entry changes do not alter the Toom-4 recurrence. No checked execution-cost theorem or application-level complexity guarantee is claimed. Verus, vstd, Z3, Rust and LLVM remain trusted dependencies; GMP FFI appears only in comparison infrastructure.

## Complete measurement outcome

Each of two independent runs records all 52 registered operation/precision groups, four modes and seven repetitions: 1,456 records per run. Modes rotate by repetition. Inputs and output semantics match, allocation occurs outside timing, and every recorded batch lasts at least 10 ms. Actual minimum durations were 10.056772 ms and 10.116950 ms. The [controller record](evidence/confirmation-window.json) preserves the quiet-process preflight and both run identities.

All 10 principal workloads exceed GMP in both runs. The 1.2-times-GMP limit fails for 33 of 52 groups in run 1 and 35 in run 2. The candidate regresses against the baseline in 23 and 24 groups, respectively, with 15 groups regressing in both runs. Against the previous control, 19 and 22 groups regress; 8 regress in both runs, while 19 improve in both. These are observed ratios, without a statistical-significance or causal claim.

The principal matrix reports run 1 / run 2. Ratios below 1 mean a lower candidate median time. All rows use `top=63`; the [full 104-group summary](evidence/performance-summary.json) includes every other registered size and precision.

| Operation | Limbs | Candidate / baseline | Candidate / previous control | Candidate / GMP |
|---|---:|---:|---:|---:|
| Product | 256 | 0.98456 / 0.97045 | 0.99896 / 0.99919 | 1.48063 / 1.43026 |
| Product | 512 | 1.02167 / 1.00794 | 0.98649 / 1.01254 | 1.75700 / 1.79091 |
| Product | 1024 | 0.97625 / 0.98293 | 1.01531 / 0.99620 | 1.80750 / 1.79902 |
| Product | 2048 | 0.88700 / 0.94004 | 1.00826 / 1.02334 | 1.94198 / 1.98628 |
| Product | 4096 | 0.92079 / 0.95068 | 0.98696 / 1.00727 | 2.05763 / 2.12144 |
| Square | 256 | 1.00492 / 1.00945 | 0.98756 / 0.99463 | 1.32160 / 1.34150 |
| Square | 512 | 0.98988 / 0.96990 | 0.99041 / 0.99880 | 1.48010 / 1.46055 |
| Square | 1024 | 0.95423 / 0.91472 | 1.00867 / 0.97828 | 1.67312 / 1.67921 |
| Square | 2048 | 0.94567 / 0.95533 | 0.98696 / 0.97515 | 1.79492 / 1.84979 |
| Square | 4096 | 0.92295 / 0.87411 | 1.02478 / 0.97154 | 1.94814 / 1.86558 |

The raw data are [run 1](evidence/default1/benchmark.csv) and [run 2](evidence/default2/benchmark.csv). The [comparison record](evidence/performance-comparison.json) retains all repeated regressions. No result-based rerun or selection was performed. Small-path instruction changes therefore remain an experimental result, not a production promotion.

## Reproduce and audit

The archive audit uses Python 3.12 and requires no verifier or benchmark binary:

```sh
python3 experiments/toom4-entry/audit.py
python3 experiments/toom4-entry/prepare.py --output /tmp/verigmp-entry-prepare
```

The preparation command reconstructs all 222 frozen input files exactly from the pinned Git commit and published overlays. It refuses to overwrite an existing output directory. Exact preparation was tested on Windows and from a fresh Linux clone; the [reconstruction record](reconstruction-check.json) states its scope. A full proof and timing replay from the public clone has not been run.

For a fresh gate, use x86-64 Linux or WSL, GMP development libraries and the [pinned verifier/Rust toolchain](../../native/toolchain.json). Install the verifier with `python3 scripts/setup_verus.py`, following the [verification instructions](../../docs/verification.md), then set `VERUS_BIN` to the printed executable. Use a new output directory for each command:

```sh
python3 experiments/toom4-entry/prepare.py --output /tmp/verigmp-entry-proof --verify
python3 experiments/toom4-entry/prepare.py --output /tmp/verigmp-entry-timing --benchmark
```

`--benchmark` first performs a fresh gate, then attempts both registered runs and recomputes the complete matrix. It requires a quiet CPU 0 window. A failed preflight or runtime check remains a failure record; it does not become performance acceptance.

## Archive boundaries

[publication.json](publication.json) maps original and published hashes. Recorded Rust, Python and raw CSV bytes are preserved exactly. Selected host paths in historical reports, logs and assembly listings are replaced with logical placeholders. Executables, libraries and the large oracle output are represented by hashes and regenerated during verification. The failed proof context and rejected preliminary helper layout remain in the [failed gate](attempts/previous-crate-proof-context/verification.json) and [helper-layout record](attempts/split-both-helpers/report.json).

The production `native/` tree remains unchanged. This archive contains generic arithmetic sources and evidence only. Its measured target remains `target_not_met`.
