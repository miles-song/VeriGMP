The final performance decision is **NO-GO for promotion** of the private
Karatsuba recursion candidate. The two completed measurements are accepted as
valid negative evidence under the frozen protocol. Neither run establishes the
required improvement; the first also violates the registered regression ceiling.
This review does not accept the candidate native implementation for main.

The reviewed candidate is `905edec767a9e5eeee838e083cad93e027d73c51`, tree
`1d0c3f0a8fd014a180358500f589c342c33207b3`, with native source
`b31fbce898054f6db668277f8a4da88f94c95aa2`. Its baseline is
`de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9`. The candidate was clean when
captured for this independent audit. All 50 native Rust files match both the
fixed native source and the prior static review identities. Only
`native/verified/fast_multiply.rs` differs from baseline. The installed
karpathy-guidelines and code-review-and-quality skills and applicable AGENTS.md
contracts were applied.

| Frozen rule, applied independently in each run | Run 1 | Run 2 |
| --- | ---: | ---: |
| Geometric mean, candidate/baseline over all 27 forced full-product cells with n > 24; required <= 0.97 | 0.9997460919631549 — FAIL | 1.0028851442261115 — FAIL |
| Maximum candidate/baseline median across all 86 cells; required <= 1.05 | 1.0554729047100921 — FAIL | 1.0455882132295198 — PASS |
| Cells exceeding 1.05 | 1 | 0 |
| Cells exceeding 1.00, all retained | 44 | 43 |
| Promotion under both rules | NO-GO | NO-GO |

The first run's ceiling failure is forced `fast_multiply::full`, n=191,
top=64, threshold=24. Its baseline median is 13,686.3076171875 ns/op and
candidate median 14,445.52685546875 ns/op, a 5.54729047100921% regression.
The second run's maximum occurs in the unchanged default square control,
n=23, top=63: baseline 145.68330001831055 ns/op and candidate
152.3247413635254 ns/op. That 4.55882132295198% difference is retained;
it does not establish a change to square semantics or a repeatable square
regression. The registered decisions require no attribution of measurement
variation to particular instructions. Dropping the square controls, averaging
the two runs, tuning a threshold, or repeating until a pass would not satisfy
this experiment's contract.

The independent replay consumed every raw record. Each run has 6,192 records
forming 2,064 complete invocation/outcome/result triples: 258 calibration
processes and 1,806 accepted sample processes. The exact expected set is
34 forced full-product cells, 26 registered default multiply cells and
26 registered default square cells, each with three comparator paths and
seven accepted repetitions. All 602 per-cell/repetition order checks per run
pass: baseline/candidate relative order alternates strictly and the GMP
insertion rotates without changing that order. Every argv, operation, size,
top precision, seed, binary path, iteration count and CPU setting agrees with
the frozen plan. There are no missing, duplicated, extra or unregistered calls.

All raw processes returned zero and report no timeout. stdout/stderr bytes
match the retained hexadecimal encodings, every JSON result matches its raw
stdout, and stderr is empty. All 3,561 and 3,565 internal calibration ladder
steps are retained and follow doubling from one iteration to the first batch
of at least 20 ms. No short sample, retry, failure or parse failure occurs in
either measured run. The minimum accepted arithmetic duration is
18,567,032 ns in Run 1 and 18,613,079 ns in Run 2, above the required 10 ms.
The accepted arithmetic totals are 50,074,715,024 ns and 49,855,492,110 ns.
Calibration arithmetic totals are 14,369,309,650 ns and 14,405,356,324 ns.
These totals fit within the recorded process windows.

Medians were reconstructed from exact rational ns/iteration values, with all
86 cell summaries per run agreeing with the saved reports. Both geometric
means were calculated independently from the reconstructed medians. The full
172 rows, including every positive regression, are in
`audit-output/all-cells.csv` and `audit-output/all-cells.json`; individual
accepted sample selection and raw line numbers are in
`audit-output/sample-selection.csv`. No timing or calibration executable was
run by this reviewer.

The frozen harness checks complete output against GMP before and after timing,
with fixture construction, allocation, result checking and printing outside
the measured arithmetic loop. It uses preallocated caller buffers and
`black_box` for runtime inputs and outputs. The modular GMP comparison includes
the required low-half copy and precision mask. This review independently
regenerated all 86 deterministic inputs and their exact integer product or
square in Python, retaining input and full expected-output hashes. Their
checksums match every one of the 4,128 raw process results. Raw stdout retains
checksums rather than full output vectors; the complete-vector assertion is
established by the bound harness source and successful executions. The prior
static acceptance separately retains full Python/GMP output comparisons and
boundary checks. No new claim of full-output serialization is made.

The same release binaries and library/Verus metadata pairs are bound in both
runs, checked against the frozen build manifest and their actual copied bytes.
The benchmark source is identical in the build and candidate checkout; the
50 native source identities agree with the prereview. Compiler flags and
tool identities remain those accepted in the static review. The original
359/0 candidate proof is reused at its exact source identity; this audit does
not rerun or broaden that proof, and does not transfer its item count to a
restored baseline source. The earlier static review remains
`STATIC / MEASUREMENT-PLAN ACCEPT`, with performance acceptance false.

The host receipt records two separate, sequential measurement controllers on
the same AMD Ryzen 7 7745HX / WSL2 environment, both targeting logical CPU 8.
The frozen harness calls `sched_setaffinity(0, {8})` before each successful
child exec; the host probe reports CPU 8 online and allowed. The observations
bind emulator PID 17360/start ticks 639296423233476241 and qemu PID 11540/start
ticks 639296423237280818 to stable process paths and image hashes. Both
NtSuspend calls returned zero. All 1 and 132 threads respectively were observed
suspended before timing and after each run, with no CPU-time increase between
those observations. Both NtResume calls returned zero after Run 2 and both
processes were observed no longer fully suspended. The recorded pause periods
are 201.482420 s and 201.474969 s. ADB PID 30904 was excluded and retains the
same recorded identity. This supports the recorded target-process pause and
restoration; it does not prove global absence of interference, fixed CPU
frequency, physical-core isolation, or a future quiet window. This reviewer
did not suspend, resume, stop or launch those processes.

The separate registered GMP target remains unmet. All ten principal
multiply/square workload ratios exceed 1.0 in each run. Their ranges are
1.2946552211730071–2.1974083734186465 and
1.307722430062473–2.309784682430908. Of the 52 registered key operation/shape
cells, 34 and 32 respectively exceed 1.2 times GMP. These are measured-platform
results; no universal parity or solver performance claim follows. The
consuming solver continues using its trusted GMP backend pending the entirely
separate compatibility, full parity and frozen solver-trace acceptance.

The required disposition is to retain this candidate and every raw observation
as an experiment/no-go. An evidence-only integration may restore all production
native files to the exact baseline and publish accurate negative-result
documentation with the immutable evidence. Its exact package, restored source
tree, documentation and status require a separate packaging review; this
performance review does not preapprove uninspected packaging changes. No main
edit, reviewer commit, merge or push was performed.

`replay_audit.py` is a standard-library-only offline checker. Extract the review
archive and run `python replay_audit.py --output replay-output` in a fresh output
directory. It reads only saved evidence, checks frozen identities, regenerates
the independent integer fixtures, and reproduces the raw-record, ordering,
median, threshold and host-receipt audits. It never executes a benchmark.
`review-evidence-members.json` records each payload's length and SHA-256;
`review-package.json` binds the final archive and this review's receipts.
The full prior proof/static package remains separately preserved at its
original immutable hash; the compact performance package carries its review,
identity records, manifest and archive hash without duplicating its 396 members.
