# Packed-product composition acceptance protocol

This feature starts from native base
`8cc144b349269d31a59b18838aea28f52645a8fa`. The first fixed mathematical and
actual-call proof source is `886fc176bd542422b00dddd00a8b259c563e0296`.
The gate records its own complete committed source snapshot; later receipt-only
updates may reuse that result only when every native source, client/control and
gate input byte is unchanged, with exact tool, rlib and vir identities retained.
No historical receipt is rewritten.

The exact contract and boundaries are in
[`docs/packed-product-composition.md`](../../docs/packed-product-composition.md).
The candidate adds a ghost native composition module and an external verified
consumer witness. It does not add a production wrapper or change a dispatcher.
Its p is an input integer bound, q is exact output precision, and tensor creation
provenance remains a consuming application's obligation.

Run on x86_64 Linux/WSL from a clean committed checkout:

```sh
python3 -B experiments/packed-product-composition/verify.py \
  --deps-root /path/to/pinned/deps --output /fresh/persistent/evidence
```

The output directory must be outside the checkout and must not already exist.
For gate/receipt-only changes, `--reuse-producer /prior/evidence` can reuse the
complete library build only after checking identical native source inventories
and bytes, toolchain bytes, actual tools/environment, raw successful proof logs
and rlib/vir hashes. The new report names the original build commit and report;
the actual-call client, all oracles, negative fixtures, mutants and generated-code
checks run again. A prior gate's unrelated fixture failure does not invalidate
its separately complete and successful library build.
The gate copies all native Rust sources, the client/control, test/gate sources
and relevant documentation/status into a retained snapshot, checks their bytes
against HEAD, and records every command and raw stdout/stderr hash. It checks
the pinned Verus archive and the installed Verus, rust_verify, Z3, vstd and
builtin/macro artifacts against that archive. It records Rust/LLVM, Python and
binutils identities. No current mutable path can substitute for retained bytes.

The acceptance conditions are:

1. The complete native library verifies with `--no-cheating` and compiles with
   `-O`; its exact rlib and vir export are recorded. The actual-call consumer
   verifies and compiles against precisely those imports. No added proof escape,
   FFI, result assumption, runtime Seq or alternate multiplication is permitted.
2. Python constructs 476 deterministic cases from arbitrary integer coefficients.
   Coefficient widths cover 1 through 4,097 bits, including non-word-aligned
   widths and 64-bit boundaries. Counts cover empty/one and positive shapes
   through 1,024. Consecutive counts straddle guard jumps at q=64,128,192,256;
   slot padding is independently varied. Maximum, zero, impulse, alternating
   and random inputs occur. Two empty cases use the largest 64-bit usize
   precision, including the largest slot width, without a giant allocation.
   Exact expected coefficients come from nested finite sums. A separate Python
   whole-integer product agrees with every slot. Raw binary words and JSONL
   metadata/hash rows are retained, never bounded to u128.
3. The optimized runtime driver calls the verified consumer and compares both
   packed operand buffers, the entire product and every output word against
   those fixtures. It checks input preservation and boundary canaries around
   all seven buffers. Scratch is tested at the minimum capacity and with extra
   limbs. This is correctness execution, with no timing claim.
4. The existing independent layout oracle runs against this same producer rlib:
   208 valid cases and all 18 returned-error/destination-preservation cases.
   Consumer shared-input/mutable-output and mutable/mutable overlap fixtures
   must fail uniquely with Rust E0502 and E0499. Invalid scratch, guard and
   output-length client calls must fail their intended Verus preconditions.
   These do not claim a new runtime error API outside the witness domain.
5. Four fresh semantic mutations must be rejected by complete logical VCs:
   an insufficient guard bound, a nonzero final tail, replacing multiplication
   with squaring, and extracting at input precision. Model mutations use a
   fresh native source copy; executable-call mutations import the original
   exact producer export. Rejection requires exit 1, a unique nonzero-error
   summary and only allowed logical diagnostics. The module note is required
   for partial module verification. Classifier fixtures reject parser/type,
   load, timeout, resource-limit, solver-unknown and panic diagnostics.
6. Verus compiles the client to one optimized object; pinned Rust compiles the
   ordinary control with the same crate name and optimization/codegen options.
   `objdump` identifies the complete `consume` symbol and its size; `objcopy`
   retains exactly that symbol section's bytes. Both full symbol bodies and
   every relocation must match. The four call relocations must be precisely
   two packs, the actual Toom product and extraction. A prefix of disassembly
   or a truncated instruction count is not erasure evidence.

The final report must state the exact source commit and source hashes,
tool/archive identities, producer/client rlib+vir hashes, all raw command logs,
oracle inputs and binaries, logical mutation results and complete-symbol code
evidence. `status=pass` means this scoped local functional gate passed. Independent
Astra Max acceptance, merge and remote confirmation are separate events.
There are no timing/performance or checked global bit/space claims.
