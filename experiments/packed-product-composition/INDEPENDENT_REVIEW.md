# Independent packed-product acceptance

**ACCEPT for merging the scoped mathematical composition and verified client
witness into main.** No blocking findings remain. The accepted result is exact
full convolution of equal-length canonical nonnegative coefficient arrays,
including empty inputs and the allocated final zero coefficient, through the
actual existing pack, Toom product and extraction calls. It introduces no new
production entry point or dispatch policy.

The reviewed candidate is `0d7d0db8b939229489b3da8fa84d8be5d5356db0`, tree
`5000f7a417926e663602336bd38b5e5f4913060c`. The proof, client and ordinary
control are byte-identical to first source
`886fc176bd542422b00dddd00a8b259c563e0296`. The original focused gate source is
`0daa481d1087d742e55ecb77ca01422a3688f451`. The integration target checked here
is main `98f755792ea5b66456dc330972563714c2ba820d`, whose additions since base
`8cc144b349269d31a59b18838aea28f52645a8fa` are confined to the accepted dense
crossover experiment. Main's added paths and this feature's paths are disjoint.
All existing native Rust sources except the one-line erased-module declaration in
`native/lib.rs` are unchanged from main. No production arithmetic body,
dispatcher, consumer gitlink or GMP adapter is changed.

The review independently checked the mathematical interpretation and the actual
contracts, then replayed the focused acceptance procedure against retained,
hash-checked producer exports. It did not rerun the unchanged complete-library
proof or perform timings. The fresh focused replay passes at the exact reviewed
candidate. Its [raw report](evidence/independent-review-verification.json) has
SHA-256 `38161c8c398464511f4575f12af28ce2107e1e062a87db160716f55114844429`.

The [complete independent replay archive](evidence/independent-review-replay.tar.gz)
retains all 254 files: the fresh source snapshot, compiled libraries and Verus
metadata, generated fixtures and mutants, all raw command logs, runtime
executables, oracle data, complete objects, extracted bodies and the independent
audit programs/results. It is 5,288,894 bytes, SHA-256
`12ac6923eaffab7af74d788d5f3e66c670f9df4c8bce5ceeab8865bee8137347`.
Every member was read back and checked against the
[independent manifest](evidence/independent-review-manifest.json).
The [integrity and fixture audit](evidence/independent-integrity-audit.json) and
[independent replay-log/ELF audit](evidence/independent-replay-audit.json) provide
compact machine-readable results.

The independently completed gates were:

1. Rehash the original report, manifest and 5,325,921-byte archive, then verify
   all 307 member lengths and hashes. Bind all 69 gate-source identities and
   all 69 original producer-source identities to their Git commits. Check all
   retained gate snapshots, the producer's native snapshot, 16 actual tool files
   and all producer/client rlib and vir exports. All 50 native Rust files and
   the toolchain bytes agree between the successful producer and this candidate.
2. Validate the producer's complete `--no-cheating --compile -O` invocation and
   retained `358 verified, 0 errors` result. The enclosing earlier gate correctly
   remains failed because its scratch fixture did not reject the intended
   precondition; its report, fixture and diagnostics remain preserved. That
   later fixture failure does not invalidate the separately completed producer
   proof. Reuse the exact retained producer rlib/vir, with hashes
   `02dabb57ecbee4b82fe99b4ed555cbd892160b999b47d01d9ac0ab9788372d28`
   and `9890ff7d0d62f53101b41089017f913ecd6495421e54c79e2819735c3769ed41`.
3. Independently verify and compile the imported actual-call client: **5 items,
   zero errors**. Compile and run its optimized fixture driver against those
   exact imports. All **476** product cases pass, including all intermediate
   packed/product/output words, input preservation and all seven buffer canaries.
   Re-execute the existing **208** valid layout cases and **18** checked-error
   destination-preservation cases against the same producer.
4. Independently parse all original binary fixtures and recompute expected
   coefficients by diagonal finite sums, distinct from the generator's scatter
   accumulation. Check compact input values, padded operands, whole integer
   products, every coefficient slot and output word, and all JSONL vector hashes.
   This covers **430 nonempty and 46 empty cases**, **19,878 coefficient values**,
   input precision through **4,097 bits**, output precision through **8,201 bits**
   and counts through **1,024**. The newly generated oracle binary and JSONL rows
   exactly reproduce the original retained data.
5. Independently replay both borrow fixtures: shared/mutable overlap rejects
   uniquely with **E0502**, and mutable/mutable overlap with **E0499**. Replay
   the three invalid consumer calls and verify the diagnostics identify the
   intended guard, scratch and output-length preconditions.
6. Independently replay all four semantic mutants. Insufficient guard and
   nonzero final tail each yield **7 verified, 1 error** with the precise
   partial-module note. Product replaced by squaring and extraction at input
   precision each yield **4 verified, 1 error**. All exit with code 1 and
   complete logical VC diagnostics; parser/type, resource, timeout, unknown,
   loading and panic failures are excluded. The gate's two strict classifiers
   also pass their **25** self-check fixtures.
7. Reverify and compile the optimized client object (**5 items, zero errors**)
   and independently compile the ordinary control. In addition to the gate's
   binutils comparison, parse the ELF64 section, symbol and relocation records
   directly. The complete sole function has size **286 bytes**, equal to its
   full section size. Both original and freshly rebuilt whole objects are
   byte-identical, SHA-256
   `6623199f86c49cd38e8ddcb756ba3fb45ee6780ce9b225a34bacde599567ac3b`.
   Their complete body SHA-256 is
   `fba40c21cc8ccfffc0d3408d176b1c1daa3cb8a21e9c737a426b314614b2729b`.
   All four relocations match, including type and addend: packs at **0x45** and
   **0x82**, actual Toom multiplication at **0xeb**, extraction at **0x10b**;
   each is `R_X86_64_GOTPCREL` with addend -4. No truncated disassembly is used.

The functional interpretation is substantive. `packed_product.rs:10` defines
coefficients from compact input chunks; `:22` defines the output using the
existing independent finite-sum convolution. The product-value premise of
`:58` is discharged in `consumer.rs:48-85` by the two actual packing contracts,
the limb/radix interpretation and the actual multiplication postcondition. The
desired convolution equality is not a caller precondition.

For positive n, the guard gives `2^q >= n*2^(2p)`. Canonical inputs yield the
strict coefficient bound `coefficient <= n*(2^p-1)^2 < 2^q`, and the slot domain
gives `q <= 64*s`. Existing no-carry and digit-extraction lemmas consequently
identify every full product slot with the finite sum. Actual extraction then
preserves these values in compact q-bit chunks. The final zero coefficient is
proved explicitly. Empty input bypasses the positive-length multiplication
call and has empty product/output. Arithmetic and length safety follow from the
caller-owned slice capacities and 12*n*s scratch premise.

The accepted executable domain is exactly the documented canonical/guard/length
domain. `consume` proves `Ok` there; its logically unreachable error branches
are discharged through the existing layout error contracts. This witness does
not create an out-of-domain checked runtime wrapper. There is no fixed u128
precision restriction, but machine parameters, slice lengths and available
storage still bound any execution. Safe Rust borrowing supplies the alias
boundary. The generic p bound describes supplied integer representatives;
creation history, precision lift/reduction and SAT tensor meaning remain the
caller's responsibility.

Complete object equality establishes that the witness's specifications, proof
calls and otherwise unused length reads add no runtime work relative to the
ordinary client under the pinned optimized build. The existing production
function bodies remain unchanged. This review makes no new wall-clock speedup,
production-policy, solver-performance or GMP-parity claim. The documented
nominal caller-buffer sum is an analytic storage budget, not a checked composed
peak-space theorem. Unequal/truncated consumer composition and composed bit-cost
and peak-live-space theorems remain open.

The fresh replay command was:

```text
wsl -d Ubuntu -- taskset -c 2-15 python3 -B /mnt/e/3sat/VeriGMP-packed-product-refinement-20261108/experiments/packed-product-composition/verify.py --deps-root /mnt/e/3sat/VeriGMP-low-square-gated/deps --reuse-producer /mnt/e/3sat/VeriGMP-packed-product-independent-final-20261108/reused-producer --output /mnt/e/3sat/VeriGMP-packed-product-independent-final-20261108/focused-replay
```

The derived reuse directory combines the original producer report and successful
proof logs from `producer-origin/` with the identical producer rlib/vir retained
under `gate-2/`. Their hashes were checked before use, so the replay does not
depend on the original one-way execution paths. The independent audit source is
retained under `independent-audit/` in the new archive. Fresh output directories
are required for any replay; historical evidence is never overwritten.

All four candidate commits have the required miles-song author/committer and
no coauthor trailer. This review's additions preserve every original acceptance
artifact. The current proof-status record links this decision; pending-review
wording in historical source snapshots and the original local receipt remains
historical. No merge or push is performed by the reviewer.
