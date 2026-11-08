# Packed-layout crossover sweep

## Scope

This is an experiment-only measurement of two pack-and-consume paths from the
reviewed base commit fe9081f1a1d4075f74a46cdd66d97145d065c5ad. It changes no
library dispatch or production code. Both paths use the same compact inputs,
preallocated buffers, exact full-product consumer, and exact coefficient
extraction:

1. layout: the checked packed_layout::pack_coefficients API for both operands.
2. bulk_zero: checked layout sizing, a whole-destination zero fill, and the
   same coefficient copies performed by the API.

Each path invokes verigmp::toom_multiply::full with threshold 24 and its 12n
scratch contract, then calls packed_layout::extract_coefficients with
q = 2p + ceil(log2(n)). Source and destination buffers, input rings, workspaces,
the result dump, and the 64 MiB eviction buffer are allocated before timing.
Input generation, output dumping, cross-path checks, Python oracle checks, cache
preparation, and result hashing are outside the timed batches.

## Registered shapes

Input precisions are p = 7, 17, 29, 30, and 53 bits. For each precision, the
registered counts are:

- discovery: every n from 1 through 35; 125 through 131; and 509 through 515.
- held-out confirmation: 60 through 69; 253 through 259; and 1019 through 1024.

There are 49 discovery counts and 23 confirmation counts, for 360 total
count/precision shapes. The split is fixed before timing. It includes exact
powers and neighborhoods of 32, 64, 128, 256, 512, and 1024. The discovery
split contains the p=30 one-slot/two-slot transition at n=16/17. The held-out
split contains the p=29 transition at n=64/65. For each shape, the report
records q, required guard bits ceil(log2(n)), available slot margin
64*slot_words - 2p, and the remaining margin 64*slot_words - q.

Each shape is measured in two phases:

- reuse: one fixed input pair, warmed before timing.
- streaming: a rotating ring of 32 pre-generated input pairs; before each
  warm-up, calibration, and measured batch, touch one word per cache line in a
  preallocated 64 MiB buffer. Eviction work is outside timing. This is an
  eviction-cycled condition, not a claim that each call starts from DRAM.

Modes are interleaved in rotated order. Each group has seven measured
repetitions, each at least 10 ms. Calibration targets 25 ms. Short attempts are
retained and retried at double batch length. Two independent processes are run
per split, rebuilding the release executable each time. The paired runs must
have identical executable hashes, input hashes, exact result dumps, and
oracle-check receipts.

## Correctness and source binding

The Rust harness asserts exact equality between both paths for every one of the
32 inputs at every shape. It retains every extracted word in a framed binary
result dump. The first run per split is checked coefficient by coefficient by
an independent Python arbitrary-precision convolution oracle. The second
process must reproduce the first result dump byte for byte. Inputs and results
are hashed in addition to direct word comparison.

The measurement driver requires a same-commit packed-layout refinement gate,
checks the pinned Verus/Rust toolchain, binds all measured sources to the
committed tree, and checks that every Toom/Karatsuba full-product source blob
matches mainline baseline
8da9dc207d8cae7c0b64aa0d370d1fa7ca2585aa.

## Decision rule

The primary metric is the ratio of per-group medians:

    layout_over_bulk_zero = median(layout ns/call) / median(bulk_zero ns/call)

The group is a registered shape, cache phase, and independent run. A ratio
below 1 favors the checked layout API. Results are not pooled across precision,
count, phase, or slot width before checking regressions.

A universal path is called robust only when it has at least a 1% geometric-mean
gain and has no median regression in any registered shape/phase in either
independent run across both splits. Otherwise no universal winner is claimed.

A hybrid is eligible only if a simple predicate, selected from the discovery
split alone, has no median regression versus bulk_zero in any discovery group
in either run and at least a 1% geometric-mean gain. The allowed predicates
are fixed here:

- slot_words == 1, or slot_words >= 2;
- n <= one of 16, 32, 64, 128, 256, or 512;
- remaining slot margin >= one of 4, 8, 12, 16, 20, 24, 32, 48, or 56 bits.

Either branch may select layout; the other branch selects bulk_zero. Both
branches must cover at least three distinct discovery counts and two
precisions. Among eligible rules, choose the lowest geometric-mean ratio;
ties prefer fewer predicate parameters, then the order listed above. The rule
is frozen in a selection receipt before examining confirmation timings.

The held-out confirmation runs cannot change the predicate. A hybrid is
accepted only as an experiment candidate if it has no median regression versus
bulk_zero in every held-out shape/phase in either confirmation run and retains
at least a 1% geometric-mean gain on held-out groups. Failure or absence of a
discovery candidate means no robust hybrid policy is established. No result
from an earlier 14-shape sweep is used to choose a predicate or threshold.

The stratified report includes precision, count band, slot words, remaining
margin bin, and cache phase. These summaries describe this fixed matrix; they
are not fitted performance laws or worst-case guarantees.

## Commands

The pinned dependency directory is supplied by the caller. From WSL:

    python3 experiments/packed-crossover-sweep-20261108/run_sweep.py \
      --deps-root /mnt/e/3sat/VeriGMP-low-square-gated/deps \
      --layout-gate /mnt/e/3sat/VeriGMP-packed-crossover-evidence-20261108/layout-gate \
      --output /mnt/e/3sat/VeriGMP-packed-crossover-evidence-20261108/train-a \
      --run-id train-a --split discovery --cpu 0

Use the same command for train-b with --reference-run pointing to train-a.
After the two discovery runs, run analyze.py --select and preserve the
selection receipt before executing confirmation-a and confirmation-b. The
first confirmation run performs the Python oracle check; the second uses
--reference-run to require byte-identical outputs.
