# Verification

This document states what VeriGMP proves, what it tests, what it measures and
what it trusts. The three kinds of evidence answer different questions and are
kept apart:

- Functional refinement: the executable Rust functions satisfy mathematical
  input/output contracts. Verus checks this.
- Analytic cost bounds: operation counts derived by hand from the source
  recurrences. These are not machine-checked.
- Measured performance: observed timings on stated hardware, reported in
  [benchmarks.md](benchmarks.md).

The current functional-refinement proofs do not establish the cost bound, and a
benchmark says nothing about worst cases.

The frozen low-square candidate reports 234 library verification items,
11,292 integer oracle cases and five new semantic mutants rejected by the proof.
The current Toom/square gate checks those 11,292 cases, including 1,440 direct
low-square cases, plus 12 invalid-input controls and 21 semantic mutations.
The precision layer retains 33 items, 27,193 integer cases, 11 invalid-input
controls and seven mutations. Five precision-layer API controls have matching
normalized instructions, including modular subtraction. A complete-library proof
claim requires the complete fixed-source `verify.py` gate; the frozen isolated
candidate report is separate evidence. Local feature gates and independent Astra
Max review govern incremental merge acceptance. CI is supplemental, and fixed-source
formal batches retain pending status until they pass.

The subtraction chain is `kernel::sub_limb` → `limbs::sub_assign` →
`pow2::sub_mod_assign`. Its contracts cover exact borrow identities and the
canonical Euclidean remainder of a potentially negative difference.
`fast_words::sub_word` reuses the same scalar primitive.

## What a contract says

Each verified function carries `requires` (preconditions) and `ensures`
(postconditions) written in terms of the integer meaning of its slices. For the
public product:

```rust
pub fn mul_mod(dst:&mut[u64], a:&[u64], b:&[u64], scratch:&mut[u64], top:u32)
    requires a@.len()>0, a@.len()==b@.len(), old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=12*a@.len(), 1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(), final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(b@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
```

`value` and `modulus` are spec functions over unbounded integers, defined in
`native/specs/`. The postcondition therefore does not depend on how the
implementation represents intermediate values. Verus proves that every execution
satisfying the preconditions ends in a state satisfying the postconditions. It
also discharges the checked-arithmetic and indexing obligations along the way:
ordinary integer operations cannot overflow and element indices are in range.
Some word operations wrap or truncate on purpose, such as `wrapping_sub` in
`fast_words::sub_word` and narrowing casts that extract a limb from a 128-bit
product. Those carry explicit mathematical contracts relating the wrapped or
extracted word and its borrow or carry to the exact integer result.

## How module properties compose

The proof is built in the same layers as the code (see
[architecture.md](architecture.md)):

1. Models in `native/specs/` define `value`, `radix(n) = 2^(64n)` and
   `modulus(n, top)`, and prove identities about integers alone: splitting a
   number into blocks, the Karatsuba and low-product identities, the five-point
   Toom-3 interpolation equations, coefficient bounds and square symmetry. These
   files have no executable code.
2. Word and slice functions prove contracts such as "the result plus `2^(64n)`
   times the carry equals the exact sum", using loop invariants on prefixes.
3. Evaluation and interpolation prove that their buffers hold particular integer
   expressions of the input blocks. Interpolation receives a ghost sequence of
   the five product coefficients, defined from the input blocks by the model
   formulas, and proves that it leaves `c1`, `c2` and `c3` in its buffers.
4. Recursive multiplication and squaring call those functions and themselves,
   establish every callee precondition at the call site, and combine the callee
   postconditions with a model identity to obtain their own postcondition.
5. The public dispatch composes "correct modulo `2^(64n)`" with "masking the top
   limb is reduction modulo `2^p`".

At no layer is the expected answer defined from the code's own output. A caller
relies only on the callee's contract, so changing a callee's body cannot silently
change what a caller has proved, as long as the callee still verifies.

## Termination and capacity

Every loop and recursive function has a `decreases` measure, and Verus checks
that it strictly decreases. Recursive calls always receive a strictly shorter
input: Toom blocks of at most `ceil(n/3) + 1` limbs, Karatsuba halves and the
low-product parts.

Capacity is part of the contracts. Each recursive call is handed a sub-slice of
its caller's scratch, and the proof shows that the sub-slices fit: the five
point products of `2(k + 1)` words, one or two evaluation buffers of `k + 1`
words, and a remaining region at least as large as the child's own `12` or `10`
times its length. The model lemma `product_capacity` proves that intermediate
Toom values fit those widths. Size computations such as `12*n` are guarded
against `usize` overflow.

## Ghost code and erasure

Spec functions, proof functions, `proof { ... }` blocks and `ghost` variables are
checked by Verus and erased before code generation. They do not appear in the
compiled library. The `Ghost(c)` argument to interpolation carries no run-time
data. The model files compile to nothing executable.

The executable code is ordinary Rust on caller-owned slices, with 128-bit
widening multiplication for word products, exact carries and no allocation.
Runtime checks that do remain in the source, such as entry `assert!`s and slice
splitting, are visible there and are accounted for by the code inspection below.

## No proof escapes in the core

`verify.py` rejects any source under `native/` that contains `assume(`, `admit(`,
`axiom(`, `verifier::external_body`, `verifier::external_fn_specification`,
`verifier::external`, `verifier::trusted` or `verifier::verify = false`. This is
a source pattern guard for those named annotations, not a detector of every
possible escape; the development contract also prohibits hidden FFI and custom
axioms, and review checks for them. The attributes that remain,
`verifier::rlimit` and `verifier::spinoff_prover`, change solver resource limits
and query partitioning, not what is proved.

## Testing against independent oracles

Proofs are checked against tests that use a separate notion of correctness:
Python's arbitrary-precision integers. A Verus-compiled runner reads commands,
calls the real library functions, and prints results that `verify.py` compares
line by line with values computed in Python.

The current Toom/square oracle has 11,292 cases and sizes up to 4,097 limbs.
Its existing cases use seed 20261101; the 1,440 direct low-square cases use seed
20261103. Coverage includes:

- the default dispatch and forced recursion with thresholds 24 and 192, all three
  low-product splits and Karatsuba squaring;
- sizes on both sides of every threshold and every residue of `n mod 3`;
- block patterns that make the evaluation at -1 negative or zero;
- all-ones inputs that create full carry chains, and every `top` from 1 to 64 at
  1, 25 and 513 limbs;
- `mul_mod(dst, a, a, ...)` with the same input slice twice;
- output and scratch prefilled with nonzero words, exact scratch length, and
  sentinel words on both sides of both buffers that must remain unchanged;
- the MAC4 row candidate including an empty tail, and `divide_word`
  quotient/remainder.

Twelve malformed commands must each produce no output and a nonzero exit, including
`top = 0`, `top = 65`, `3n` scratch, thresholds below the contract minimum and
divisor 0 and empty full-square or low-square inputs.

The earlier modules (limbs, `pow2`, schoolbook multiplication, Karatsuba) keep
their own oracles, mutation checks and inspections, and `verify.py` reruns all of
them on the same snapshot. A pass means every module passes.

## Mutation checks

A test suite can pass because it is too weak. A mutation check changes one line
of a verified file in a way that makes it wrong, reruns Verus and requires a
semantic failure: a nonzero exit, at least one reported verification error and a
diagnostic such as "postcondition not satisfied". Timeouts, resource-limit
messages and parse errors do not count as detection; they fail the run.

The current gate requires semantic rejection of all 21 mutations below. The five
low-square mutations target `square_base` after complete positive library and
runner verification; the remaining mutations check the complete runner imports.

| Mutation | Change |
|---|---|
| `wrong_evaluation_sign` | Sign of the product at -1 inverted |
| `omit_top_padding` | High product padding not cleared |
| `wrong_coefficient_offset` | Coefficient 3 added at offset `2k` instead of `3k` |
| `wrong_high_coefficient` | Interpolation scales `c4` by 8 instead of 16 |
| `wrong_exact_division` | Division by 2 instead of 3 |
| `wrong_evaluation_point` | Evaluation uses `x` instead of `x*x` |
| `wrong_difference_sign` | Karatsuba-square difference sign inverted |
| `negative_square_product` | Toom square gives the -1 square the evaluation's sign |
| `missing_double_cross` | Low square adds the cross product once |
| `drop_carry` | MAC4 resets one propagated carry to zero |
| `omit_tail` | MAC4 skips its last word |
| `wrong_default_precision` | Default product ignores `top` |
| `omit_square_cross_double` | Full-square cross contribution is not doubled |
| `wrong_square_diagonal` | A diagonal uses the input word instead of its square |
| `drop_square_row_carry` | Full-square cross-row carry is replaced by zero |
| `drop_square_diagonal_carry` | Full-square diagonal carry is reset to zero |
| `omit_low_cross_row` | Low-square skips its last cross-product row |
| `truncate_retained_row` | Low-square shortens a retained cross-product row |
| `drop_low_row_carry` | Low-square cross-row carry is replaced by zero |
| `omit_odd_diagonal` | Odd-length low square omits its final diagonal |
| `drop_odd_output` | Odd-length low square overwrites its final output word with zero |

## Toom-8 dyadic recovery (experiments)

The repository contains experimental Toom-8 dyadic recovery and interpolation
lemmas in `experiments/toom8-primitives/dyadic-recovery/`. Fresh verification
at source commit `5cfde6a` on linux_x86_64 via WSL verified three entries
(library, runner build, codegen build) for dyadic with 478 items per entry
across 102 source inputs, producing 2688 oracle cases, and three entries for
interpolation with 514 items per entry across 115 source inputs, producing
336 oracle cases. The scoped audit confirms generic proof exports,
coefficient-to-buffer mapping for fifteen recovered coefficients (low endpoint,
six even, seven odd, high endpoint), and static erasure for the caller path
`toom8_interpolation::interpolate -> toom8_even::with_endpoints ->
toom8_normalization::with_endpoints -> toom8_dyadic_producer::dyadic_pair`
plus seventh/Newton odd. Codegen inspection is textual optimized assembly
audit; length/slice guards remain.

Dyadic recovery and interpolation primitives were verified with Verus from
source commit `5cfde6a630591080c330ac09177977c539bd3a55` on linux_x86_64 via
WSL. The two dated verification runs are registered in
`experiments/toom8-primitives/dyadic-recovery/scope.json` with pinned source
commit, verifier platform, archive SHA-256/size, and report hashes binding
original tool identity, logs, and artifacts. The audit wrapper in that
directory validates archive integrity and report provenance against the
registered hashes but does not execute Verus or establish performance
acceptance.

The feature is pending independent review. It does not modify production
dispatch or establish complete recursive Toom-8 implementation. The frozen
VeriCount consumer receipt at commit `8ba9253` reports M7 status `spec_only`
and M8 status `conditional_composition` with no dyadic reference in native
modules. Solver consumer acceptance is blocked. See
[`experiments/toom8-primitives/dyadic-recovery/README.md`](../experiments/toom8-primitives/dyadic-recovery/README.md)
for scoped audit details.

## Inspecting the generated code

The proof covers source-level Rust semantics. To check that the optimized default
path does not reintroduce costs the design avoids, `verify.py` compiles the same
source snapshot with `-O --emit=asm` through a small crate that exports
`verified_product` and `verified_square`, wrappers around `arithmetic::mul_mod`
and `arithmetic::square_mod`. It then walks every function reachable from those
two symbols and fails if it finds:

- a call to an allocator (`__rust_alloc`, `malloc`, `free` and similar);
- a hardware `div` instruction or a 128-bit division helper;
- a `panic_bounds_check` call, which is the per-element bounds check;
- a call to an unrecognized external function. Only `memcpy`, `memset`, `core`
  panic entry points and the slice-range failure handler are accepted.

At the baseline, the reachable set has 12 functions and the only external
targets are `memcpy`, `memset`, `core` panic entry points and the slice-range
failure handler. Those remaining checks are intentional: entry assertions,
slice-region checks for `split_at_mut` and subslicing, the copies the algorithm
requires and zero fills of padding.

At the current state, low-square also fills initial words and calls the triangular
function at the chosen cutoff.

This inspection applies to the fixed product and square dispatch. It does not
cover `toom_words::divide_word` called with an arbitrary divisor, which divides
128-bit values in its source. Inside the default path it is inlined with the
constant divisors 2 and 3, and the inspected assembly contains no division
instruction or helper. The inspection runs on a separate compilation of the same
snapshot and flags, not on the bytes of the exported `.rlib`.

The MAC4 candidate is inspected separately and does retain per-element bounds
checks on this compiler. It is not selected by default, because local
measurements did not show a consistent improvement over the original carry loop.

## What is trusted

The functional claim holds only if these components are correct:

- Verus, including its translation of Rust to verification conditions, its ghost
  erasure and the `vstd` library specifications and lemmas;
- the Z3 SMT solver;
- rustc and LLVM, which compile the verified source to machine code;
- the operating system, hardware and runtime libraries that run it.

The pinned Verus archive is checked by SHA-256 before extraction, and
`verify.py` records the hashes of the verifier, solver and `vstd` files and
checks that they did not change during the run.

Outside the functional proof boundary, and not verified: the runners, the
benchmark programs, the ordinary Rust controls, the C++ GMP ABI check, the
benchmark-only GMP FFI calls and the Python scripts and oracles. They produce
evidence; they are not part of the library.

## What is not claimed

- No proof about the compiler's output or the machine code. The code inspection
  above is a check, not a proof.
- No constant-time or side-channel property. Run time depends on `n` and the
  dispatch branch, and also on operand values: helpers such as the comparison
  `fast_words::less`, the negative evaluation and carry handling can take
  data-dependent branches.
- No machine-checked cost theorem. The `O(n^log3(5))` bound is analytic.
- No complexity or correctness result for an application that uses the library,
  beyond what its own proofs establish from these contracts.
- No verification of GMP, and no GMP performance parity.

The machine-readable scope is
[native/proof-status.json](../native/proof-status.json). The historical benchmark
snapshot `ab5eaf6` reports 199 library items, 9,648 oracle cases and 12 mutations;
its reachable code-equivalent identity is `bf28217`, recorded in
[history-provenance.json](../native/history-provenance.json). The frozen cutoff9
candidate and the current gate contents are identified separately above.
Verification items are not counts of public functions.

An isolated checked-recursion candidate passed its source-bound 359-item proof,
but failed the predeclared performance gates in both independent runs. Its
production source was rejected and restored exactly to the baseline; the
current production proof/status does not inherit the candidate's 359-item count.
The evidence-only result, full raw runs, source restoration hashes and offline
checker are in
[the no-go experiment package](../experiments/acceptance/arithmetic-precondition-checks-20261108/RESULTS.md).
