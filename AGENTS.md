# VeriGMP development contract

Use the installed karpathy-guidelines skill when available. The current user's
instructions take precedence. This repository owns general multiprecision
arithmetic; application-specific mathematics belong in consuming projects.

VeriGMP continues implementing and verifying performance improvements. Its
registered target is principal-workload median time no greater than GMP, with
every key shape at most 1.2 times GMP under native/performance-target.json.
GMP is a comparator, not a ceiling. The consuming solver's policy of recording
optimizations for a later version does not defer arithmetic work in this library.
Use miles-song <2324715854@qq.com> as both author and committer, without coauthor
trailers, for this task's new commits.

## Refinement and performance

1. Define integer meanings and algebraic identities independently of executable
   outputs. Compose module properties, then prove actual Rust functions refine
   them using Verus contracts, invariants and termination measures.
2. Separate functional refinement, resource bounds, asymptotic cost derivations
   and observed performance. Do not call an analytic recurrence a checked cost
   theorem or a benchmark a worst-case bound.
3. Never weaken an implementation to accommodate a proof tool. Use caller-owned
   slices, scratch reuse, wide multiplication, exact carries and efficient
   algorithms. Ghost/spec/proof objects must erase from optimized code.
4. No assume/admit, external bodies, custom axioms, hidden FFI or unchecked
   verification flags in the arithmetic core. Verus/vstd/Z3/Rust/LLVM remain
   explicit trusted dependencies. Benchmark-only GMP FFI is outside that core.
5. Algorithms inspired by GMP must have a pinned source reference and an
   independent implementation/proof. Preserve all applicable license notices.
6. Each optimization needs same-source verification and optimized compilation,
   independent integer oracles, boundary/alias/capacity coverage, semantic
   mutation rejection, code generation inspection and honest benchmarks.
   Timeouts and tool/parse errors are not successful mutation detection.
7. Test default dispatch as well as parameterized alternatives. Match inputs,
   output semantics, allocation boundaries and compiler information in controls;
   retain raw repeated observations. Do not claim universal GMP parity.
8. Before pushing, obtain independent review, verify one immutable input snapshot,
   record actual source/tool identities and check remote CI. Never force push.
   Incremental backup and publication of this repository are user-authorized.
9. Consumers must pin verified commits. Check their actual compiled dependency,
   gitlink, source bytes and tool identity; a directory entry alone is not an
   integration test.

## Module boundaries

- `native/specs`: integer interpretation, range/decomposition and algebraic identities.
- `native/verified/kernel.rs`: scalar words and carry primitives.
- `native/verified/limbs.rs`, `pow2.rs`, `fast_words.rs`: slice arithmetic and precision.
- `native/verified/multiply.rs`: schoolbook reference/basecase.
- `native/verified/fast_multiply.rs`: complete and low-product recursion and dispatch.
- `specs/toom.rs`, `toom_blocks.rs`, `square.rs`: independent polynomial,
  decomposition, capacity and symmetry models.
- `verified/toom_evaluate.rs`, `toom_interpolate.rs`, `toom_words.rs`: exact
  evaluation and interpolation properties, signed magnitude and coefficient bounds.
- `verified/toom_multiply.rs`, `toom_low.rs`: recursive composition. Ghost
  coefficients must be defined from input blocks, with all helper preconditions
  established by the caller; never define correct answers from executable output.
- `verified/square.rs`, `toom_square.rs`, `square_low.rs`: symmetry refinements.
  Retain the distinction between dedicated recursion and a specialized leaf kernel.
- `specs/square_base.rs`, `verified/square_base.rs`: independent triangular-square
  identity and its actual full-square leaf implementation.
- `verified/arithmetic.rs`: measured fixed production policy; forced alternatives
  and actual default dispatch both require oracle and codegen coverage.
- `verified/mac4.rs`: measured candidate only. A proven optimization must still
  improve runtime before replacing the default path.
- `native/lib.rs`: library entry, compiled and exported with its Verus metadata.
- Runners, controls, benchmark FFI and Python scripts are unverified test infrastructure.

The public claim is the exact scope in `native/proof-status.json`. An imported
Verus contract must be paired with the compiled library from the same verified
source snapshot. Preserve explicit length, alias, precision and capacity domains.
