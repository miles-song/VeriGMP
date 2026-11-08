# Cross-reconstruction comparison

Status: preparation only. No timing is authorized by this document. The
baseline proof source is `2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba`; current
public main is `bf1bc40946967581852dd3b675db8140d757574e`. Their identical
native tree is `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`. The build receipt
binds a per-file Git blob and SHA-256 mapping from both proof snapshots to their
commits, and records that the candidate changes only `native/verified/fast_words.rs`.
Each timing receipt must record current local, remote-tracking and actual
public GitHub main refs before and after the run and require the same native tree; refresh the baseline
if production native sources have changed. The candidate library is
`d6a17984c758dab825339d0eab8562f21c5fa24b`. The actual remote is queried before
and after the measurement window. Build the two benchmark binaries
from the separately verified, optimized rlib/VIR pairs, using the same committed
driver, compiler, linker, shared GMP and flags. `build.py` checks and records
those identities. Check each binary's disassembly and resolved call paths
before interpreting a measurement. The source change applies to Karatsuba
product and square, while the main policy's large modular product uses Toom-3.

`prepare.py` freezes deterministic binary inputs. The full-product group calls
`fast_multiply::full` and `square::full` at thresholds 24 and 192. The default
group calls the actual `arithmetic::mul_mod` and `arithmetic::square_mod`
entry points. It includes every registered key shape, top widths 1, 63 and 64,
the 511/512/513 dispatch boundary, odd/even recursion boundaries and sizes up
to 4096 limbs. Aligned and opposed half-operand signs, random, zero, all-ones
and equal inputs are included at selected sizes; equal multiplication uses
actual shared immutable input slices. Full products have top width 64. Every
cell preallocates equal input, output and required scratch outside the timed
region. The same binary input bytes and operation are used on both sides.

Before timing, `verify.py` must complete every cell for each binary. It invokes
the same driver in `check` mode, which does not read a clock, and compares the
entire output with GMP's independent `mpn_mul_n` or `mpn_sqr` result, truncating
and masking for modular semantics. It records the exact command, input hash,
output and exit status for each check. Every later calibration and sample
also verifies that input's result against GMP both before and after its timed
loop. Any mismatch, missing cell, changed identity, or failure invalidates the
run. In addition, each binary and cell executes a two-iteration `warmup_check`
without reading a clock and compares its result to GMP. GMP is the correctness
oracle here, not the measured competitor.

Both binaries and the loader inspection process run under the same complete
environment allowlist: `PATH=/usr/bin:/bin`, `LANG=C`, `LC_ALL=C`, and
`TZ=UTC`. All other variables are absent, including every `LD_*` variable
(`LD_LIBRARY_PATH`, `LD_PRELOAD`, `LD_AUDIT`, and related options) and
`GLIBC_TUNABLES`. Under this exact environment and the selected CPU affinity,
resolve and hash the actual dynamic dependencies of both binaries before and
after each session, including GMP and the dynamic loader. The paths and hashes
must match each other and the frozen build. Record the `ldd` output and the
presence and hashes of the loader cache and system preload file. A changed
loader configuration, unresolved dependency, mismatched path or hash
invalidates the session. The GMP preflight uses and checks the same environment.

Preparation from the committed harness, with the pinned Rust and Verus tools on
`PATH` and appropriate Git worktree environment:

```sh
python3 experiments/cross-fusion-20261109/benchmark/prepare.py /tmp/cross-fusion-inputs
python3 experiments/cross-fusion-20261109/benchmark/build.py \
  --baseline-evidence /mnt/e/3sat/VeriGMP-cross-fusion-baseline-fresh-20261109 \
  --candidate-evidence /mnt/e/3sat/VeriGMP-cross-fusion-fresh-evidence-d6a1798 \
  --rustc /mnt/e/3sat/VeriCount/deps/rustup/toolchains/1.99.1-x86_64-unknown-linux-gnu/bin/rustc \
  --verus-deps /mnt/e/3sat/VeriCount/deps/verus/verus-x86-linux \
  --output /tmp/cross-fusion-build
python3 experiments/cross-fusion-20261109/benchmark/verify.py \
  --manifest /tmp/cross-fusion-inputs/manifest.json --build /tmp/cross-fusion-build/build.json \
  --output /tmp/cross-fusion-preflight
```

The retained build artifacts include whole-binary symbol tables and
disassemblies. Independently inspect both actual benchmark binaries to confirm
that full product and square reach `combine_cross`, and that the default
multiply and square operations reach their policy branches and relevant
recursive paths. Record the inspected addresses and any inlining or indirect
relocations; a symbol's presence alone is insufficient. A static reviewer
must approve the protocol, inputs, proof bindings and code generation before
any timing. An explicit root authorization must then bind the hashes of the
manifest, build receipt and successful preflight receipt.

## Measurement plan

Run on one x86-64 Linux/WSL installation and the same physical machine. Stop
other heavy jobs, select one allowed logical CPU, reserve its sibling where
possible and record its sibling topology. Fix the host power plan and avoid
changing software, CPU policy or machine state between A and B. The driver
pins each measured process to the selected WSL CPU and checks its reported
affinity. WSL virtual CPU affinity does not guarantee a corresponding fixed
Windows physical CPU; record that limitation and do not claim host isolation.
Start `host_monitor.ps1` and `wsl_monitor.py` before the session, point both at
the same new stop marker, and give `measure.py` their output paths with
`--host-telemetry` and `--wsl-telemetry`. Stop them only after the session has
completed, and retain their final records. Each monitor targets one sample per
second; actual timestamps, not the requested interval, must show continuous
coverage of the complete session with no gap greater than two seconds and no
sample collection taking longer than two seconds. The host captures native
system-wide process CPU counters and physical memory, and `wsl -l -v` plus the
host power plan before and after. The WSL monitor captures `/proc` process
identities and cumulative CPU, `/proc/stat`, and CPU and memory PSI. The runner
records each child PID, start ticks, lifetime and CPU consumption. Monitoring
overhead counts as competition. Record available WSL CPU frequency and thermal
readings before and after every invocation. Missing required telemetry is
inconclusive; a coverage gap, changed distribution inventory or changed power
plan invalidates the entire session.

For either host non-WSL processes or WSL non-benchmark processes, cumulative
CPU above 0.2 logical CPUs for at least five consecutive seconds invalidates
the session. Host idle and the single identified `vmmemWSL` aggregate are
excluded from the host competitor total; its CPU is retained separately. A WSL
benchmark child is excluded only by its PID and start ticks. A PID that
vanishes while reading `/proc` is attributable only to a unique recorded
benchmark child whose lifetime contains that event; otherwise the session is
inconclusive. The WSL aggregate CPU check reports a conservative lower bound on
CPU not explained by observed processes or overlapping benchmark children;
that lower bound above 0.2 CPUs for five consecutive seconds also invalidates
the session. Sustained host physical-memory load at least 90%, or WSL memory
PSI `some avg10` at least 5%, for five seconds invalidates the session. A
failed affinity check or observed thermal/power throttling invalidates it too.

After both monitors have stopped, run `review_telemetry.py --report REPORT
--build BUILD --output REVIEW`. Its receipt hashes the session report, raw
observations, build and both complete monitor logs, checks their byte stability,
and retains process-level deltas, inventory and limitations. A
`pass_pending_independent_review` is not acceptance: an independent reviewer
must inspect the inventories, load and pressure records, processes, source
identities and whole-session coverage. Guest `/proc` does not identify
processes in other distributions or VMs; the host WSL aggregate is retained but
does not provide per-process isolation. Processes entirely between snapshots
can be missed. This machine has no reliable observed actual frequency or
temperature; report throttling as unknown, never as excluded.

For each cell, calibrate both builds, use the larger iteration count for both,
and in every sample process run an untimed warmup of exactly that count with
the same buffers and operation, checking the warmup output against GMP,
and require every retained sample to last at least 10 ms. Four blocks each
contain either ABBA or BAAB, alternating by cell, block and run; run 2 reverses
the order. If a sample is too short, retain it as invalid and repeat its entire
block at doubled count. A block's candidate/baseline ratio is the geometric
mean of its two candidate samples divided by that of its two baseline samples;
the cell result is the median of its four block ratios. Each order occurs
twice. Within each order, its larger block ratio divided by its smaller ratio
must be at most 1.02; also, the larger of the two order-specific geometric
means divided by the smaller must be at most 1.02. A cell that fails either
test marks that cell unstable rather than averaging away the discrepancy. Continue
collecting the entire session and retain all raw invocations, calibration
histories, rejected blocks, outputs and telemetry. Unstable cells may be shown
for exploration but cannot support acceptance. Run both `full` and `default`
groups in two independent quiet sessions; stop on execution or environment
failures rather than omitting cells. These measurements compare
the proposed change with current VeriGMP, and cannot establish GMP parity.

An entire session may be rerun in full at most once, and only for at least one
unstable cell or a documented environmental violation. A retry must
reference the original report and use the same build, inputs, group, run and
CPU. For an environmental violation, an independent host-review JSON must have
`status: environment_violation`, the original `report_sha256`, and a concrete
reason supported by retained telemetry. The runner atomically records its
one retry claim alongside the first report, so it cannot start another retry
from that report. Preserve the first attempt, retry, host review and all raw
data; once retried, use the retry as the session result and never select the
more favorable attempt. Cells that remain unstable are inconclusive, as is a
retry that violates environmental criteria.

Before collecting any timing, use these fixed decision thresholds. For an
eligible production region, each included actual-default cell must improve by
at least 3% in both independent runs (median ratio at most 0.97), and each
order's geometric mean must be at most 0.98 in each run; do not extrapolate
between unmeasured sizes or input patterns. For all measured registered key
shapes, neighboring boundary cells and the forced full-product/square cells,
reject a region with any regression greater than 3% in either run (median ratio
or either order's geometric mean above 1.03). An isolated beneficial cell without both adjacent measured sizes is
insufficient to select a dispatch region. Missing or noisy evidence is
inconclusive. These thresholds apply to this candidate against its baseline;
all library-wide GMP gates and independent review still apply separately.
Every cell required for a declared region, its adjacent measured sizes and its
key regression checks must be present and stable in both sessions. Production
acceptance uses a preregistered target region and independent confirmation.
If exploratory results determine a new dispatch region, first freeze that
region and modified candidate source, rebuild and redo GMP preflight, then run
new independent confirmation. Preserve all exploratory raw data.

## Toom-4 combination

The default Toom-3 path does not measure Toom-4. Before claiming a Toom-4
combination result, select and freeze the exact Toom-4 overlay and its policy,
then create four separately source-bound, verified and optimized builds:
baseline, fusion alone, Toom-4 alone, and fusion plus Toom-4. Use the same
oracle-checked inputs, allocation, compiler, CPU and telemetry, and a
counterbalanced four-build order. Compare the combined build with both
single-feature controls on the same Toom-4-relevant full and modular paths,
including 512/513 and 1024/2048/4096 and top 1/63/64, in two sessions. Apply
the same 3% improvement and regression limits to each declared region and
retain all four raw datasets. Overlay selection, composite proofs, the
four-build runner and measurements remain pending; neither the default group
nor the current two-build harness satisfies this gate.
