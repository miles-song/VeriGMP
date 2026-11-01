# Contributing to VeriGMP

VeriGMP's value comes from the evidence attached to its code. A change is complete
when its property is stated independently, its Rust implementation is proved to
refine that property, its performance has been measured honestly and its scope is
described truthfully. This guide describes that workflow. The repository's
[AGENTS.md](AGENTS.md) is the full development contract and takes precedence where
the two differ.

## Scope

This repository owns general multiprecision arithmetic on little-endian `u64`
limbs. Mathematics specific to one application belongs in the consuming project.
Algorithms inspired by GMP are welcome, but the Rust implementation and proof
must be written independently, and the GMP source files consulted must be pinned
by hash in [native/gmp-reference.json](native/gmp-reference.json). Preserve every
applicable license notice.

## Working on one module

Each module has one responsibility and a contract that its callers rely on; the
mapping is in [docs/architecture.md](docs/architecture.md) and in the module
boundaries section of AGENTS.md. Work in this order:

1. State the property first. Add or extend spec and proof functions in
   `native/specs/` that describe the integer meaning and the algebraic identity,
   for example a new interpolation equation or a coefficient bound. These must
   not refer to any executable output.
2. Write the executable function in `native/verified/`, with `requires` and
   `ensures` in terms of `value`, `radix` and `modulus`, and with loop invariants
   and `decreases` measures.
3. Establish every callee precondition at the call site. When a ghost value such
   as Toom coefficients is needed, define it from the input blocks, never from
   the result.
4. Keep explicit length, alias, precision and capacity domains in the contract.
   Do not widen a domain without proving it.

Register a new module in [native/lib.rs](native/lib.rs) and in the runner, codegen
and benchmark crates that should exercise it, and update
[native/proof-status.json](native/proof-status.json).

## Preserve performance

Do not slow the implementation down to make a proof easier. Keep caller-owned
slices and scratch reuse, 128-bit widening multiplication, exact carries and the
efficient algorithm. Ghost, spec and proof code must erase from optimized output.
If a proof seems to need an allocation, an extra copy or a weaker algorithm,
look for a stronger invariant or lemma instead.

A proved optimization does not replace the default path unless it is measurably
faster. The MAC4 row unrolling is the standing example: it is proved and
measured, and it stays a candidate because it did not show a consistent win.

## No proof escapes

The arithmetic core may not use `assume`, `admit`, custom axioms,
`external_body`, external function specifications, `verifier::verify = false`,
hidden FFI or any other unchecked verification flag. `scripts/verify.py` applies
a limited source guard: it rejects the named annotations `assume(`, `admit(`,
`axiom(`, `verifier::external_body`, `verifier::external_fn_specification`,
`verifier::external`, `verifier::trusted` and `verifier::verify = false` in
`native/`. It cannot detect every hidden FFI call, custom axiom or unchecked
flag, so review must confirm the rest. A resource-limit attribute is acceptable
when it only changes solver effort.

## Running the pipeline

On x86_64 Linux or WSL with the prerequisites from
[docs/usage.md](docs/usage.md):

```sh
rustup toolchain install 1.99.1 --profile minimal
python3 scripts/setup_verus.py
python3 scripts/verify.py
```

This is the required full acceptance gate. It verifies and compiles from one
immutable snapshot, builds and runs the examples, reruns every module's oracle,
mutations, code inspection and benchmarks, and fails if the selected input files
or verifier files change during the run. During development, focused Verus
commands on one module or the documented example compile are useful for quick
iteration, but they do not replace this gate. A change is not ready until the
gate reports `"status": "pass"`.

Do not change [native/toolchain.json](native/toolchain.json) casually. A new
Verus or Rust version needs its own full run, a new archive hash and updated
benchmark metadata.

## Evidence for a change

A new or changed function needs evidence beyond its proof:

- Oracle cases compared with Python integers, covering threshold boundaries,
  `n mod 3` residues where blocks are involved, all-ones carry chains, negative
  or zero evaluations, every `top`, empty or short tails, identical input
  slices, nonzero initial output and scratch, exact scratch length and sentinel
  words around every buffer.
- Malformed commands that must be rejected without output.
- At least one semantic mutation per new property, rejected with a verification
  error. Timeouts, resource limits and parse errors are not detection.
- If the change reaches the default path, code-generation inspection of the
  actual default dispatch, as well as any forced alternative being promoted.
- Benchmarks against the previous verified path, the relevant forced
  alternatives and GMP, with matching inputs, output semantics and allocation
  boundaries, and with all raw repetitions kept.

## Describing results

Keep three kinds of claims separate: functional refinement (proved), analytic
cost (derived by hand) and measured performance (observed on stated hardware).
Do not call a recurrence a checked cost theorem or a benchmark a worst-case
bound. Report slower results alongside faster ones, and do not claim universal
GMP parity. Counts such as verified items or oracle cases belong to a specific
commit.

## Review and publication

Before a change is pushed, it needs an independent review of the proof, the
evidence and the documentation claims, and a passing local `verify.py` run on
one immutable input snapshot whose actual source and tool identities have been
checked. After pushing, confirm that the remote CI run of
[.github/workflows/verify.yml](.github/workflows/verify.yml) passes for that
commit before describing it as accepted or ready for consumers. History is never
rewritten with a force push.

Consumers must pin a verified commit and use the `.rlib` and `.vir` produced by
the same verified run. Changing an exported contract affects every caller that
imports it.
