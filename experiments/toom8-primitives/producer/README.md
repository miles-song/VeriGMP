# Verified Eight-Block Signed Product Producer

This experiment verifies a Rust composition from two equal-length multiprecision integers to one signed point pair. It establishes magnitude, parity, and capacity premises for the existing pair-normalization kernel directly from input blocks and computed products, without requiring an unverified caller to supply output properties.

The accepted immutable gate is `producer-feature1`: **472 / 472 / 472** verified items in library, runner, and code-generation builds; **2,640** independent integer oracle cases; **12** rejected malformed runner inputs; **8** semantic mutations rejected by verification conditions. Independent review re-executed the saved runner against all cases and malformed inputs, and confirmed rejection of **72** combinations of real verification-condition logs with appended fatal diagnostics.

## Arithmetic and Interfaces

`candidate/native/verified/toom8_producer.rs` implements `weighted_pair`. Inputs are equal-length full-u64 slices with `7*k ≤ n ≤ 8*k`, including `k=0` and an empty final block. The eight nonnegative weights obey the existing evaluation contract: each is at most `2^21`, with sum below `2^22`. The child threshold is at least 24. Mutable outputs and workspace are disjoint from each other and the immutable inputs; the two immutable inputs may overlap.

Writing each input as eight base-`B^k` blocks, `weighted_pair` performs four signed evaluations, two existing verified full products, simultaneous sum/difference, and exact halving. The two outputs are the even and odd diagonal weighted sums defined independently from input blocks. The actual producer proofs establish nonnegative positive evaluations, domination of negative magnitudes, product parity, and output capacity before invoking the normalization helper.

`candidate/native/specs/toom8_convolution.rs` independently groups the 64 block products into fifteen convolution coefficients. Its weighted-product bridge carries an explicit multiplicative-weight premise. Establishing that premise for the concrete dyadic points belongs to the next module; it is not assumed here.

## Space, Work, and Code Generation

With `m = k+1`, the interface requires **14*m** scratch words: two m-word evaluation buffers and at least 12*m words for the child kernel. Two separate outputs each have 2*m words. This is a local workspace theorem, not a complete whole-kernel 12*n/10*n schedule.

Local analytic work is `2*T_existing_full(m) + O(k)`. The children in this composition are the existing forced Toom-4 full-product kernel. Complete recursive Toom-8 implementation still requires decreasing calls, recomposition, and whole-kernel cost and lifetime arguments.

The accepted code-generation inspection follows three entry paths and finds no allocator call, general-division instruction or helper, or element bounds panic. Structural contract and slice checks remain. A private non-inlined pair-normalization helper preserves the full existing contract and permits the compiler to remove observed limb bounds guards. Its call overhead has not been timed. Textual assembly inspection is not machine-code equivalence or a performance result.

## Evidence and Reproduction

- `publication.json` maps exact arithmetic and checker sources and sanitized saved logs to original and published hashes.
- `evidence/verification.json` binds the accepted input snapshot, tools, runner runtime dependencies, commands, and artifacts.
- `evidence/root-independent-audit.json` records the independent review and saved-runner replay.
- `development/index.json` retains all **12** development attempts, including failed proofs and failed code-generation inspections. Successful proof status alone does not imply the inspection passed.

Run the public saved-evidence audit and reconstruction checks from the repository root:

```sh
python3 experiments/toom8-primitives/producer/audit.py
python3 experiments/toom8-primitives/producer/test_prepare_boundaries.py
python3 experiments/toom8-primitives/producer/prepare.py --output /tmp/verigmp-producer
```

The archive audit recomputes independent input and expected-output hashes and checks saved proof, code-generation, and review evidence. It does not execute omitted binaries or perform a fresh proof. `prepare.py` reconstructs the exact accepted source bytes in a new directory and rejects path traversal and an existing destination. For a fresh full proof/oracle/mutation gate, use the pinned Verus/Rust toolchain, set `VERUS_BIN` to its verifier, and run:

```sh
python3 /tmp/verigmp-producer/check_producer.py fresh-public-run
```

Compiled executables, rlib/vir artifacts, and large oracle-output logs are omitted; their recorded hashes remain. Host paths in saved text are redacted with explicit original/published hash mappings. Arithmetic sources retain exact bytes. `scope.json` is an immutable pre-gate record; completion of this module is supported by the accepted verification and independent-review records.

No benchmark was run for this feature. Complete Toom-8 recursion, endpoint/scaling callers, full interpolation/recomposition, global scratch lifetimes, and performance acceptance remain open. The production main/default backend and consumer pin are unchanged.