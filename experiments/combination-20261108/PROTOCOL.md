# Four-cell combination registration

This prospective experiment does not change the accepted historical
checked-recursion **NO-GO** at main
`515f1efa0d79bcb73272df9f54917f156decf1e1`. It asks whether the two fixed
changes interact when both are reached. It does not authorize threshold,
dispatch, API, representation, cache or input-shape tuning.

## Exact arithmetic matrix

Every cell starts from all 57 tracked native files at baseline
`515f1efa0d79bcb73272df9f54917f156decf1e1` (50 Rust files).

| Cell | Doubled-cross factor | Recursion-check factor | Native file overrides |
| --- | --- | --- | --- |
| `baseline` (00) | off | off | none |
| `double` (10) | on | off | `native/specs/square.rs` and `native/verified/square_low.rs` exactly from `f46b835cb8f812293924418abc42a39978d78694` |
| `checks` (01) | off | on | `native/verified/fast_multiply.rs` exactly from `b31fbce898054f6db668277f8a4da88f94c95aa2` |
| `both` (11) | on | on | union of the preceding three immutable overrides |

The baseline tree, original source snapshots, three overrides and the complete
four native manifests are retained. Public requires/ensures, integer meanings,
precision, ownership, error behavior and workspace contracts stay fixed. The
added independent doubled-sum lemma is exactly the standalone model, not a new
definition of an executable result. Existing producer proofs may be reused for
00/10/01 only after exact source, tool and rlib/vir identity checks. The new
combined 11 crate must pass a fresh complete `--no-cheating --compile -O` proof.
Historical source metadata is provenance, not a fresh proof count for a cell.

The common measurement binary source is the unchanged `bench.rs` from main's
reviewed checked-recursion experiment. The low-square fixtures are copied byte
for byte from doubled-cross gate
`9c1d6f001520c382e117f3d86e488c71834e1bc7`; their identities are checked at
prepare time. No private solver source is copied into this public repository.

## Reachability and hypotheses

The relevant default path is `arithmetic::square_mod -> square_low::low`.
For n>64 it computes `h=floor(11*n/36)` and one h-limb cross product through
`toom_low::low`. At h>64 that function computes a full lower block through
`toom_multiply::full`; below the fixed Toom threshold 192 this enters
`fast_multiply::full(...,24)`. A block above 24 reaches the private recursion
worker. At n=255, h=77 and this full block has 54 limbs. Both factors therefore
execute on one concrete call. All registered square shapes from 255 upward
reach both factors. The smaller square shapes and multiplication paths retain
their roles as controls; codegen effects are inspected even for unchanged
source callers.

The independent loop-visit model records exact recursion lengths, schoolbook
scalar multiply counts, full-entry/worker visits and correction limb visits.
It is an analytic control-flow count with its branch expressions checked against
the fixed source; it is not an instrumented execution, a machine-instruction
count or a formal cost theorem. A doubled correction replaces two h-limb
updates by one h-limb update. The recursion factor removes repeated public
assertions but adds a public-to-worker call/frame and may change inlining.
Potential cache/instruction interactions may help or hurt; isolated source or
code-size gains do not establish timing improvement.

For an m-limb truncated-square base case, the cross-product slices perform
`sum(i=1..m-1, min(i,m-i)) = floor(m*m/4)` scalar multiplications. The
two-word diagonal loop and its odd-length tail perform `ceil(m/2)` more.
The exact total is `floor(m*m/4)+ceil(m/2)`: 25 at m=9 and 1,056 at m=64.
Untimed fixtures enumerate the loop's actual scalar pairs and compare them
with all unordered pairs whose positions lie below the retained output radix.

## Frozen measurements and decision rules

Before any calibration or timing: freeze all four source manifests, successful
producer exports, proof/raw oracle and codegen receipts, operation counts,
common harness, compiled binary hashes, toolchain and platform metadata, and
this protocol. Independent Astra prereview and the main agent's explicit
coordinated quiet-window grant are prerequisites. Never overlap these timings
with proof, build, emulator or other known CPU-heavy jobs. The external host
receipt records the actual quiet-window observations and any restoration.

Use seed 20261108 and the unchanged fixture generator for every binary.
Measure the exact existing 86 operation/shape cells: forced full product at
threshold 24 for n in
`1,2,7,8,9,23,24,25,31,32,33,47,48,49,63,64,65,127,128,129,191,192,193,
255,256,257,511,512,513,1023,1024,1025,2048,4096`, plus actual default
`mul_mod` and `square_mod` at all 26 shapes in
`native/performance-target.json`. Each cell measures 00,10,01,11 and GMP on one
predetermined CPU. GMP performs public full multiplication/squaring followed
by required low-half copy and mask for the modular operations. Preallocation,
oracle generation and result checking stay outside accepted timed batches.

Two separately launched complete runs use the same frozen binaries, seed,
compiler flags and CPU. Seven accepted samples per path/cell must each reach
10ms. Counts are calibrated separately for all five paths; all calibration
iterations, short attempts, stdout/stderr bytes, process failures and accepted
samples remain fsynced durable raw records. Process timeout/nonzero exit,
malformed output, checksum mismatch, source/binary changes, unavailable CPU,
or a failed quiet-window prerequisite stops the run and leaves its failure
visible. Retry only a sample shorter than 10ms, by doubling its count; never
rerun a completed unfavorable/noisy run or drop a cell.

For repetition r and cell index i, rotate `[00,10,01,11]` left by `(i+r)%4`,
reverse the arithmetic order when `(r+run_phase)%2==1`, then insert GMP at
`(i+r+run_phase)%5`. Run phases are fixed at 0 and 1. Calibration order is
`00,10,01,11,GMP`. Report full raw data, every median and every regression.
The unmodified ordinary benchmark uses `-O --edition=2024`, pinned Rust
1.99.1, pinned Verus `0.2026.10.26.d17fbd0`, x86_64 Linux/WSL, and its recorded
GMP 6.3.0 ABI. The current host is AMD Ryzen 7 7745HX; the actual host/kernel,
CPU topology, affinity, tool/loaded-library hashes and build flags are frozen
in the premeasurement receipt. CPU selection is operational, never selected
from timing results.

Predeclare the primary interaction subset as default `square_mod`, top63,
n=`255,256,257,511,512,513,1023,1024,1025,2048,4096`. Apply all three gates
separately to each completed run:

1. Geometric mean T11/T00 over this fixed 11-cell subset <=0.98.
2. Geometric mean T11/T10 over the same subset <=0.99, establishing that
   adding the recursion factor to doubled-cross has a reproducible benefit.
3. Every one of the 86 T11/T00 and T11/T10 median ratios <=1.05.

Failure of any gate in either run leaves the combination **NO-GO**. A measured
interaction alone is exploratory, not acceptance. Retain T10/T00, T01/T00,
T11/T00, T11/T10, T11/T01, and interaction `(T11*T00)/(T10*T01)` for every
cell; report all 52 default cells versus GMP and the ten registered principal
workloads separately. Historical recursion criteria and results remain intact.
No averaging across runs, postselection, threshold fitting, GMP parity, default
dispatch change or main merge follows automatically from this experiment.

## Time, space, precision, caching and SAT boundary

The full/Toom/low multiplication recurrences and exact arithmetic products
are unchanged. One square correction traverses h words instead of 2h words;
the digit computation includes an exact two-bit carry. The unchanged caller
contracts reserve 10n scratch for low square, 12n for default low multiplication
and 3n for forced full multiplication. Extra loop scalars are O(1); recursive
stack frames and compiled inlining may differ and are reported separately.
These facts do not prove complete bit-cost or peak-live-space bounds.

No memoization or persistent cache is added. Fixture and scratch reuse is
identical for all cells. Measure ordinary warm-loop throughput under the frozen
binary/CPU contract; no claim about cold caches, other machines or all input
families follows. Top precision and final masking are identical. No tensor
creation-precision contract changes.

Current solver arithmetic traces use ring add/multiply (including GMP
`add_product`), not a demonstrated dedicated square primitive. A library
square win does not establish SAT reachability or SAT speedup. Solver semantics,
representative frozen traces, time/space and integration acceptance remain
separate. The solver retains trusted GMP.
