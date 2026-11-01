# VeriGMP development contract

Use the installed karpathy-guidelines skill when available. The current user's
instructions take precedence. This repository owns general multiprecision
arithmetic; application-specific mathematics belong in consuming projects.

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
- Further Toom and squaring modules must expose their evaluation/interpolation or
  symmetry properties before composing recursive refinement.
- `native/lib.rs`: library entry, compiled and exported with its Verus metadata.
- Runners, controls, benchmark FFI and Python scripts are unverified test infrastructure.

The public claim is the exact scope in `native/proof-status.json`. An imported
Verus contract must be paired with the compiled library from the same verified
source snapshot. Preserve explicit length, alias, precision and capacity domains.
