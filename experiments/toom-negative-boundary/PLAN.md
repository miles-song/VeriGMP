# Toom -1 threshold boundary candidate

Status: experimental source and proof obligations only. No candidate proof,
optimized build, oracle, mutation, codegen, timing, performance acceptance or
independent review is claimed by this document. The production baseline is
public main `338632fef7f0cbe5b442cc6b00b7161bebded647`, native tree
`72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`.

## Candidate and obligations

For full Toom multiplication, write `B = 2^64`, `k = ceil(n/3)`, and
`m = k + 1`. The two magnitude buffers at evaluation point -1 each have `m`
limbs. Only when `k == threshold` and both limb `k` values are zero, multiply
the first `k` limbs and set both remaining product limbs to zero. Every other
case calls the existing `m`-limb recursion. The multiplication is nonnegative;
the pre-existing XOR of evaluation signs remains the sign of the point product.

The refinement argument is:

* If a length-`k+1` value has high limb zero, its integer value equals the
  value of its length-`k` prefix. Multiplication of the prefixes therefore
  equals the original magnitude product and is strictly below `B^(2k)`.
* The short call writes exactly `2k` limbs; explicitly zeroing the remaining
  two limbs makes the complete length-`2m` result equal to that product even
  when the incoming scratch contains nonzero data.
* The existing split of the 12n workspace makes `pm`, both evaluation buffers,
  and `work` disjoint. Immutable source operands may legally alias one another.
  The work slice satisfies the short call's 12k bound because the unchanged
  original call must already satisfy its 12m bound.
* The original non-leaf preconditions imply `k < n`; the shortened call strictly
  decreases the recursion measure. Since `k == threshold`, it dispatches to
  the existing `fast_multiply::full` leaf for this Toom threshold. The public
  capacity, output-size and threshold contracts do not change.

These are arguments and candidate proof code, not proof results. Same-source
Verus must establish every precondition, postcondition and termination claim.

## Reference

The independently written Rust takes inspiration from the length selection in
GMP 6.3.0 `mpn/generic/toom33_mul.c:243-266`; the pinned archive and source
SHA-256 values are in `native/gmp-reference.json`. The source has distinct
`SMALLER_RECURSION` and other branches; no claim is made about which was built
into any comparator binary. GMP is distributed under LGPL-3.0-or-later or
GPL-2.0-or-later; no GMP source code is copied into this implementation.

## Required gates

Freeze the actual source commit, source tree, pinned Verus, Rust and all argv
before running a complete native verification and optimized library build.
Retain raw logs, tool hashes and artifacts, and classify a timeout, tool error
or type error as incomplete rather than as a successful mutation. Reject changes
that require weakening the arithmetic implementation for proof convenience.

An independent arbitrary-integer oracle must run against the actual compiled
Rust calls, with default `mul_mod` sizes 737-746, forced-full sizes 573-577,
both high-limb guards true/false in all four combinations, both evaluation
signs, all-zero/all-one, carry-heavy and poisoned scratch buffers, legal shared
inputs, exact and extra capacities, canaries and invalid-call preservation.
Test top bits 1, 63 and 64. Expected values come only from inputs.

Semantic mutants must include removing either high-limb condition, failing to
zero either product high limb, and changing the point-product sign. A mutant
counts as rejected only on an actual semantic verification failure or an
independent runtime-oracle mismatch, never a parse/type/tool failure or timeout.
Compile-time borrow-overlap negatives are separate alias checks.

Compare candidate and baseline optimized reachable code with exact source and
tool identities. Inspect guard placement, extra bounds checks, branch effects,
calls, unchanged fallback and erased proof code. The source-level mechanism is
not measured performance and no claim about runtime improvement follows from it.

Run a separate, non-instrumented guard-frequency census over frozen generated
operands; compute each operand's -1 integer evaluation from its three input
blocks independently of the kernel and never include the census in timed paths.
Only report its workload and actual input distribution, not a solver frequency.
Representative solver trace distributions are a separate requirement.

## Proposed registered performance scope

No timing or calibration is authorized by this branch preparation. Before a
future measurement freeze the accepted production baseline and candidate source,
builds, harness, corpus and plan; obtain independent review and a host slot.
Include default `mul_mod` n=740-743/top63 on multiple fixed seeds and distinct
constructed guard combinations; use n=737-739 and 744-746 and forced-full
n=573-577 as boundary controls. Retain the existing all-86 regression cells.
Run two independent complete rounds with at least seven accepted samples per
cell/path, 20 ms calibration target, 10 ms minimum sample, paired/rotated
baseline-candidate-GMP order and raw retention. Pre-register which real-input
stratum is primary, per-round GM <= 0.98 and each regression cell <= 1.05;
require baseline-control GM drift within [0.95,1.05] and each control drift
within [0.90,1.10]. Guard-false and neighboring cases remain separate controls.
No pooling of rounds, dropping unfavorable controls or post-hoc dispatch tuning.
Square can reach the modified multiply through its cross product and is not
assumed to be a body-identical negative control.

Keep the trusted GMP solver backend until its separate parity, repeat and
representative solver-trace gates pass. A localized optimization does not by
itself establish GMP parity or SAT-solver speedup.
