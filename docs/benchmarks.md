# Benchmarks

The benchmarks answer one practical question: on a stated machine, how long do
VeriGMP's default product and square take compared with its own earlier code,
with parameterized alternatives and with GMP computing the same result? They are
observations on one machine. They are not worst-case bounds, not a measure of
proof overhead and not evidence of parity with GMP.

## Published data sets

The frozen baseline data set in [docs/data/2026-11-01/](data/2026-11-01/) was
produced from source commit `ab5eaf670865a4438301b6dce6b4e5175c4a6c22`. The
reachable code-equivalent identity is `bf2821728fb5c7228609c4447327ba95eccdc5c9`,
recorded in [history-provenance.json](../native/history-provenance.json). The raw
observations and their original execution identities remain fixed:

### Baseline (2026-11-01)

| Item | Value |
|---|---|
| CPU | AMD Ryzen 7 7745HX, measurement pinned to CPU 0 |
| System | WSL2, Linux 6.6.87.2, glibc 2.39 |
| Rust | rustc 1.99.1 with LLVM 23.1.1, compiled by Verus 0.2026.10.26.d17fbd0 with `-O` |
| GMP | 6.3.0 runtime and header; ABI check built with C++ compiler 13.3.0 |
| Seed | 16438731 |
| Repetitions | 7 per mode and shape, each batch calibrated to at least 10 ms |

[benchmark.csv](data/2026-11-01/benchmark.csv) holds every raw repetition: the
columns are `square, limbs, top, threshold, low_limit, mode, repetition,
iterations, ns`, where `ns` is the total time of a batch of `iterations` calls.
[metadata.json](data/2026-11-01/metadata.json) records the median per call for
each group, the source file hashes, tool file hashes, linked library hashes and
the CSV hash.

The GitHub Actions run
[41305241146](https://github.com/miles-song/VeriGMP/actions/runs/41305241146)
confirms the proof, oracle and source identities for the same code on a CI
runner. That run also produces its own timings, which come from different
hardware and are not the numbers below.

## Reproducing

```sh
rustup toolchain install 1.99.1 --profile minimal
python3 scripts/setup_verus.py
python3 scripts/verify.py
```

The benchmarks run as part of verification, from the same source snapshot that
was proved and with binaries whose hashes are checked before and after timing.
Outputs appear in `results/toom/`: `benchmark.csv` (the same format as the
published file), `tuning.csv` (a three-repetition scan over Toom thresholds 96,
192 and 384 and low thresholds 64 and 128), `mac4.csv` and the medians in
`verification.json`. A passing run checks completeness and correctness; it does
not require a noisy machine to reproduce any particular speedup.

## What is measured

Every mode computes the same thing: the product or square of `n`-limb inputs
modulo `2^p`, with `p = 64*(n-1) + top`, written as `n` canonical limbs. Most
shapes use `top = 63`; the 1- and 2-limb shapes also use `top = 1` and `top = 64`.

| Mode | Name | What runs |
|---|---|---|
| 0 | `previous_karatsuba` | `fast_multiply::mul_mod`, the verified Karatsuba entry that preceded Toom-3. For squares it is called with `a` as both operands. |
| 1 | `low_9_40` | Toom low product or low square with short ratio 9/40 |
| 2 | `low_11_36` | Same with ratio 11/36 |
| 3 | `full_then_truncate` | Full Toom product or square, then copy the low `n` limbs and mask |
| 4 | `gmp_full_then_truncate` | GMP `mpn_mul_n` or `mpn_sqr` computing the full `2n`-limb result, then copy the low `n` limbs and mask with VeriGMP's verified normalization |
| 5 | `default` | `arithmetic::mul_mod` or `arithmetic::square_mod` |

The `threshold` and `low_limit` columns record the scan context of each row (192
and 128 in the published set). Modes 1 and 2 use both values at run time. Mode 3
uses the Toom threshold but computes a full product, so it ignores `low_limit`.
Modes 0, 4 and 5 ignore both. Mode 5 is the actual public dispatch, whose thresholds
are compile-time constants: for products, Karatsuba below 512 limbs and Toom 192/128
with ratio 9/40 above; for squares, Toom 192/64 with ratio 11/36. A forced mode with
the same numbers is a different compilation of the call graph, which is why the
default is measured directly.

GMP's public `mpn` interface has no low-half product, so mode 4 computes twice
as many output limbs as the other modes need. That is the semantic match
available through public GMP functions, not a comparison with GMP's internal
`mpn_mullo_n`. The extra work is a plausible reason the default product is faster
than mode 4 at 1, 2, 23, 24 and 25 limbs; the measurements do not isolate it.

Timing boundaries:

- Included: the call, internal copying, zero filling, top-limb normalization and
  dispatch. For mode 4, the copy out of GMP's full result and the mask.
- Excluded: allocation of input, output and scratch buffers (allocated once per
  shape, outside timing), input generation and I/O.
- Not instrumented: any allocation GMP performs internally.

All six modes share the same inputs, output buffer and scratch buffer. Each
mode's result is compared with GMP's before calibration and after every recorded
timed batch; the calibration batches that choose the iteration count are not
compared individually.
Within each repetition the modes run in a rotated order, so no mode always runs
first, and all modes run in one process on one pinned CPU.

## Products

Median nanoseconds per call, `top = 63`. Ratios are default divided by the
comparison, so values above 1 mean the default is slower.

| Limbs | Previous Karatsuba | Default | GMP full, truncated | Default / previous | Default / GMP |
|---:|---:|---:|---:|---:|---:|
| 128 | 5,616 | 5,566 | 4,696 | 0.99 | 1.19 |
| 256 | 17,039 | 16,794 | 11,393 | 0.99 | 1.47 |
| 512 | 57,016 | 59,054 | 33,291 | 1.036 | 1.77 |
| 513 | 53,605 | 54,795 | 32,097 | 1.022 | 1.71 |
| 1024 | 166,084 | 160,656 | 84,993 | 0.97 | 1.89 |
| 2048 | 551,838 | 499,474 | 233,894 | 0.91 | 2.14 |
| 4096 | 1,668,281 | 1,344,900 | 601,961 | 0.81 | 2.23 |

Below 512 limbs the default runs the same Karatsuba algorithm as mode 0. The
differences there reflect dispatch and compiler specialization as well as timing
variability; these measurements do not separate the two. At 512 limbs, the
first measured size where the default switches to Toom-3, it is 3.6% slower than
the Karatsuba path it replaced, and 2.2% slower at 513 limbs. At the measured
sizes from 1,023 to 4,096 limbs the default is faster, by 5.3% at 1,023 limbs
and 19% at 4,096.

At 512 limbs the forced 11/36 split took 53,926 ns, 8.7% less than the default's
9/40 split, while forced 9/40 took 58,857 ns. The fixed 9/40 choice is therefore
not the fastest observed option at every size. At 4,096 limbs the relation
reverses: forced 9/40 took 1,352,642 ns and 11/36 took 1,426,639 ns.

At the measured sizes from 63 to 4,096 limbs the default takes 1.16 to 2.23
times as long as the GMP baseline, and the ratio is larger at the larger sizes
in this table. GMP uses architecture-specific assembly
and higher-order algorithms that VeriGMP does not implement.

## Squares

| Limbs | Previous Karatsuba product | Default square | GMP square, truncated | Default / previous | Default / GMP |
|---:|---:|---:|---:|---:|---:|
| 128 | 5,302 | 4,570 | 2,666 | 0.86 | 1.71 |
| 256 | 18,371 | 15,611 | 8,329 | 0.85 | 1.87 |
| 512 | 59,766 | 47,410 | 26,337 | 0.79 | 1.80 |
| 1024 | 196,529 | 147,074 | 66,081 | 0.75 | 2.23 |
| 2048 | 591,239 | 422,636 | 176,482 | 0.71 | 2.39 |
| 4096 | 1,743,828 | 1,175,505 | 469,172 | 0.67 | 2.51 |

At every measured size from 64 to 4,096 limbs, the dedicated square is faster
than the previous generic product with equal operands, by 14% at 128 limbs and
33% at 4,096 limbs. Below that it is mixed: 1.1% to 2.3% slower at 23, 24 and
63 limbs, 3% to 4% slower at 1 limb, equal at 2 limbs and faster at 25 limbs.
At the measured sizes from 23 to 4,096 limbs it takes 1.30 to 2.51 times as long as
GMP's `mpn_sqr` baseline.

The published benchmark data used generic multiplication at full-square leaves
and low-square leaves. The current verified implementation uses a proved
triangular full-square kernel from eight limbs, and a proved triangular low-square
kernel from nine limbs for computing only the lower n limbs, while retaining
generic multiplication below 9 limbs for low squares and below 8 limbs for full
squares. See [the 2026-11-02 measurement](#incremental-measurements-2026-11-02).

### Incremental measurements (2026-11-02)

The dataset in [docs/data/2026-11-02-low-square-cutoff9/](data/2026-11-02-low-square-cutoff9/)
measures the low-square triangular symmetric kernel at cutoff 9. It compares
baseline commit `c083839dc07f9b0cffea1a52cd6810d817105355` with that baseline plus
the frozen five-file candidate patch identified in the metadata. It uses the same
hardware, matching result semantics and 7 repetitions per group; each recorded batch lasted at least
10 ms (minimum observed 10,012,950 ns). Two complete actual-dispatch runs and two
dense boundary runs (sampled square sizes from 3 to 128 limbs) yielded 3,486 raw records across both
products and squares. The complete measurement metadata and verification report are
at [metadata.json](data/2026-11-02-low-square-cutoff9/metadata.json) and the
[performance-summary.json](data/2026-11-02-low-square-cutoff9/performance-summary.json).

On the sampled dense square sizes within 9 to 64 limbs, both runs improve:
candidate-over-baseline ratios range from 0.536746 to 0.951054. In the two complete
actual-dispatch runs, the 23-limb square takes 33–36% less time and the 64-limb
square takes 45–47% less time. These are measured samples, not every integer size.
Registered principal workloads (256, 512, 1024, 2048, 4096 limbs at top 63) remain
unsatisfactory at the target. At 4096 limbs, products take 2.330 and 2.359 times GMP
in the two runs; squares take 2.173 and 2.141 times GMP. The performance target is
not met. A complete-library proof claim separately requires complete fixed-source
verification; frozen isolated measurements do not establish it. Local feature
acceptance requires independent review; CI is supplemental.

The isolation and measurements serve as same-source evidence that the new kernel
computes correctly (verified oracle cases and mutation detection) and improves the
low-square path on the measured machine. All regression results across both runs are
preserved in the full dataset, including measurements at sizes above 64 limbs
where the default low-square entry follows the existing recursive path.

To reconstruct the baseline and frozen candidate from a clone and repeat this
comparison, use a new output directory and an available logical CPU:

```sh
python3 docs/data/2026-11-02-low-square-cutoff9/reproduce.py \
  --output build/reproduced-low-square --cpu 0
```

The script checks the captured source identities, rebuilds and verifies both
library/metadata pairs, and repeats the two complete and two dense measurements.
The published reports retain the paths of the original measurement machine;
new output belongs to the reproduction run and does not replace those reports.

## Performance target

Feature acceptance and backend replacement have separate performance criteria.
A feature can merge into main once it shows reproducible gains against the
current implementation on declared workloads, passes relevant regression and
combination measurements, and passes the necessary local correctness/oracle and
mutation gates plus independent Astra Max review. Bind proof claims to same-source
verification; formal obligations may be batched on fixed commits and remain pending
until proved. CI is supplemental and does not block development or merge. Define
the workload and comparison before
timing, retain all raw repetitions and reject contaminated measurements as
confirmation. A design's expected gain alone is insufficient. If gains apply
only to some input shapes, enable the feature only for those shapes. An
individual feature need not first meet the overall GMP target below.

The registered target governs library parity and the additional prerequisites
for replacing a consuming solver's trusted GMP backend. Accepted incremental
features and archived experiments do not by themselves meet that target.

[performance-target.json](../native/performance-target.json) registers the
workloads before target evaluation. Each principal workload must have a median
time at most GMP's; every other registered key shape must be within 1.2 times GMP.
Inputs, precision, result semantics and caller allocation boundaries must match.
Seven repetitions are retained for every group, and each recorded batch must
last at least 10 ms. Calibration alone does not establish that requirement.
The historical 2026-11-01 dataset follows its original calibration protocol and
does not establish this stricter duration requirement. The cutoff9 dataset does
meet the recorded-duration requirement; its runtime ratios still fail the target.

Run acceptance and evaluate its bound observations:

```sh
python3 scripts/verify.py --output results/acceptance-1 --export-dir build/exports-1
python3 scripts/check_performance_target.py \
  --csv results/acceptance-1/toom/benchmark.csv \
  --evidence results/acceptance-1/verification.json
```

The evaluator checks the CSV hash, source snapshot, evaluator and target identity,
group coverage, repetition counts and actual durations. It compares the median
of per-operation times, `ns / iterations`, for the default implementation and
GMP. A second independent acceptance run can be supplied through
`--confirmation-csv` and `--confirmation-evidence`; confirmation requires the
same source, tools, platform and actual linked-library builds.

Results are `invalid_evidence`, `target_not_met`, `provisional_library_pass` or
`confirmed_library_pass`. `--require-library-target` returns a failure status
unless the last state is reached. A library pass alone never authorizes replacing
the solver's GMP backend: semantic compatibility and frozen representative solver
traces are separate requirements. The target remains unmet. GMP is a baseline
for future verified algorithms, not a limit on attainable performance.

## MAC4 row candidate

`mac4.rs` is a proved four-word unrolling of the multiply-accumulate row. Its
benchmark compares it with the original verified row loop and with GMP's
`mpn_addmul_1` at 15 lengths from 1 to 512 limbs. Every mode starts from the
same destination, runs the same iteration count, and has its destination reset
outside timing; final states are compared. In local measurements the unrolled
row did not show a consistent improvement over the original loop, so the
default path does not use it. The MAC4 timings are written to
`results/toom/mac4.csv` and are not part of the frozen data set.

## Reading the results

- The comparison with mode 0 measures an algorithm change between two verified
  implementations. Comparing with GMP measures the remaining gap to a mature
  library computing the same result through its public API. Neither isolates the
  cost of proof annotations, which are erased before compilation; an unverified
  Toom-3 with identical code was not measured.
- Differences of a few percent should be read with care. No dedicated
  variability study was run, and modes that share an algorithm can still differ
  in dispatch and code generation.
- Results on other CPUs, compilers or GMP builds may differ, including in which
  split or threshold is fastest.
