# Exact packed-product functional acceptance receipt

Local focused acceptance passes for gate source
`0daa481d1087d742e55ecb77ca01422a3688f451`, based on
`8cc144b349269d31a59b18838aea28f52645a8fa`, on branch
`codex/packed-product-refinement-20261108`. The proof, actual-call client and
plain control bytes remain those first fixed at
`886fc176bd542422b00dddd00a8b259c563e0296`.
The final receipt/documentation commit changes no verified Rust or executable
gate source.
Independent final Astra Max acceptance, merge and push remain pending.

The [mathematical contract](../../docs/packed-product-composition.md) proves that
the actual efficient pack -> `toom_multiply::full` -> extract calls return the
independently defined finite convolution for equal-length canonical nonnegative
inputs, at arbitrary limb precision. The output contains 2*n coefficients with
the appropriate final zero tail. Empty input is included. All guard, machine
length, positive-Toom and scratch obligations are discharged in the client;
expected coefficients are defined solely from the input integers. There is no
new production API, dispatch, backend, allocation or runtime scan.

The [raw report](evidence/verification.json) has SHA-256
`e64a33d921810b456e343de139ccff96b4be484adc93e0cf642229fbc3568fe8`.
The [complete evidence archive](evidence/source-bound-gate.tar.gz) contains the
source snapshot, rlib/vir exports, actual runtime executables, raw oracle words
and JSONL rows, generated invalid-call/alias fixtures, semantic mutant sources,
all stdout/stderr logs, complete objects and extracted symbol bodies. It also
retains the original producer build report/logs and native source snapshot.
The archive is 5,325,921 bytes, with SHA-256
`844e1f9e16889d8c81deb73a42692c4c9d6bbdc8248e14e3b5f0e0af82574f23`.
The [member manifest](evidence/manifest.json) records every member's size and
SHA-256; all 307 members were read back and matched against it.
The external immutable copies remain at
`E:/3sat/VeriGMP-packed-product-evidence-20261108/gate-2` and `gate-1`.
Neither evidence archive nor proof requires an old removed checkout.

The producer's full `--no-cheating --compile -O` build verified 358 library
items at `b8f0c60c274d42c52dd65b2ee07d0c1a852df164`. The subsequent complete
focused gate reused that separately successful producer build after checking
all native Rust and toolchain source bytes, actual pinned tools, raw proof logs
and exact rlib/vir identities. The original enclosing gate stopped at a test
fixture; its report and diagnostics remain preserved. The passing gate verified
and compiled the actual-call client against those exact imports: 5 items,
zero errors. It also verified and compiled the optimized client object: 5 items,
zero errors. No unchanged producer proof replay was needed.

| Artifact | SHA-256 |
| --- | --- |
| `native/specs/packed_product.rs` | `f792932175cc64633ea19bf19229e61100962d19bedfbc3923bd4f925e526658` |
| actual-call `consumer.rs` | `d3206a0211ad54af0fa457f554b7a4b0a929c52a31b7d3dcb1bc5d8e703b6b1c` |
| ordinary `control.rs` | `43be821ac6c70faf3be533adaf4d3c4f2630c8db854b160f32a798f316cc3731` |
| producer `libverigmp.rlib` | `02dabb57ecbee4b82fe99b4ed555cbd892160b999b47d01d9ac0ab9788372d28` |
| producer `verigmp.vir` | `9890ff7d0d62f53101b41089017f913ecd6495421e54c79e2819735c3769ed41` |
| client `libpacked_product_consumer.rlib` | `26c8d64b1199cf02815abe28bab0ce08252569b2f41a47ed59c8bea8d2185ced` |
| client `consumer.vir` | `138b6031e25418940843631f7a35207e7b05e2dd354ed0321019a2b293f1e44d` |
| raw arbitrary-precision fixture words | `81ad095353e892d813811aa4eb9fcb78d0779b73bc9501eb94ed6bf97d9f31b2` |

The pinned runtime is Verus `0.2026.10.26.d17fbd0`, Rust `1.99.1`, x86_64
Linux/WSL. The pinned Verus archive has SHA-256
`361674d05f0c1b2c9c3f4d5bc56a8fb2ab9241ed0cceca27780668c292bb4940`.
The report records hashes of the actual Verus, rust_verify, Z3, vstd, builtin
and macro artifacts, Rust/LLVM, Python and binutils. Installed Verus artifacts
match their archive members. These tools and the Rust/LLVM compilation chain
remain explicit trusted dependencies; no FFI or new arithmetic axiom is added.

The passing checks are:

- 476 deterministic Python arbitrary-integer finite-sum cases, also checked
  against whole-integer products and every exact radix digit. They include
  coefficient precision through 4,097 bits, counts through 1,024, non-word-aligned
  precision, slot-word/guard transitions, variable padding, maximum/zero/random
  and structured inputs, and empty inputs with usize::MAX precision/slot width.
  The optimized actual-call driver matches both packed operands, complete
  integer products and all extracted output words, with input preservation,
  all-buffer canaries and minimum/oversized scratch coverage.
- The same producer passes the existing layout oracle's 208 valid cases and
  all 18 checked-error/destination-preservation cases. Mutable/shared and
  mutable/mutable overlap fixtures reject uniquely with E0502 and E0499.
  Three invalid consumer calls fail their intended guard, scratch or output
  preconditions, each by a complete logical VC failure.
- Four semantic mutants reject logically: insufficient guard and nonzero final
  tail each give `7 verified, 1 errors` with the exact partial-module note;
  square-instead-of-product and extraction-at-input-precision each give
  `4 verified, 1 errors`. All exit with code 1, one verification summary and
  allowed logical diagnostics only. The two strict result classifiers pass
  25 fixtures rejecting parser/type, timeout, resource, solver-unknown, panic,
  loading and duplicate-summary cases.
- The complete `packed_product_consumer::consume` object section is 286 bytes
  in both verified and ordinary clients, with body SHA-256
  `fba40c21cc8ccfffc0d3408d176b1c1daa3cb8a21e9c737a426b314614b2729b`.
  All bytes and all four relocation rows match: two pack calls at offsets 0x45
  and 0x82, actual Toom multiplication at 0xeb, and extraction at 0x10b.
  Both complete objects also match, SHA-256
  `6623199f86c49cd38e8ddcb756ba3fb45ee6780ce9b225a34bacde599567ac3b`.
  The evidence uses complete symbol sizes and raw bytes, with no truncated
  disassembly inference. No mathematical Seq, finite sum, proof call or extra
  traversal survives in this client.

There is no performance measurement or dispatch-policy conclusion in this
feature. The generic p-bound describes supplied canonical integer
representatives; a SAT caller still establishes descriptor provenance,
creation-precision lift/reduction and tensor semantics. Unequal/truncated
consumer composition, a composed worst-case bit-cost and peak-live-space
theorem, SAT integration and the overall GMP target remain open. The analytic
nominal buffer sum `16*n*s+2*n*(ceil(p/64)+ceil(q/64))` words, plus excess caller
scratch, is not a checked peak-space theorem. Documentation/status links pass
the focused gate; this repository has no `scripts/verify_documentation.py`.
