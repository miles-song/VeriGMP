# Exact packed-product composition

`native/specs/packed_product.rs` connects the independent
[finite convolution model](packed-convolution.md) to compact coefficient buffers.
The verified client in
[`experiments/packed-product-composition/consumer.rs`](../experiments/packed-product-composition/consumer.rs)
then calls the actual `pack_coefficients`, `toom_multiply::full` and
`extract_coefficients` functions. It proves exact polynomial multiplication for
equal-length nonnegative canonical inputs at arbitrary limb precision. The
client is a composition witness, outside the production API; the new native
module contains only erased specifications and proofs.

For n coefficients per input, p is the supplied input coefficient bound and q
is the exact output precision. Let `c_p=ceil(p/64)`, `c_q=ceil(q/64)` and let s
be the aligned slot width in limbs. The preconditions are:

- p and q are positive; s is at least both c_p and c_q.
- Both input slices contain exactly n compact c_p-limb coefficients, each in
  `[0,2^p)`. This representation invariant is maintained by the caller; the
  runtime performs no repeated coefficient scan or mask.
- For positive n, `q>=2p` and `n<=2^(q-2p)`. Empty inputs need no guard bound.
- The two packed buffers have n*s limbs each, the product has 2*n*s limbs,
  output has 2*n*c_q limbs, and scratch has at least 12*n*s limbs.
  Actual slice lengths also impose the machine address/capacity limits.
- Rust's safe mutable and shared slice borrows enforce the ownership/alias
  boundaries. Buffers and scratch belong to the caller.

The polynomial interpretation reads input coefficient i from compact chunk i;
the expected output is the independently defined finite sum
`c[k]=sum(a[i]*b[k-i])`, with zero extension outside each input. It never refers
to executable output. The result has 2*n coefficients, including the final
zero coefficient at index 2*n-1 for positive n. All output chunks are canonical
q-bit integers. There is no u128 or fixed coefficient-bit ceiling in the proof.
Empty inputs produce empty output; multiplication is skipped because the
existing integer multiplication API requires a positive limb count.

Packing's established slot equality identifies the two actual packed integers
with the polynomial evaluations in radix `2^(64*s)`. The verified Toom call
provides the integer product, with its positive length and scratch obligations
discharged from the client's slice preconditions. The guard bound makes every
finite convolution coefficient less than `2^q<=2^(64*s)`, so no carry crosses
a slot. Complete limb slots are canonical radix digits, and uniqueness of
radix extraction identifies every product slot with the corresponding finite
sum. The actual extraction contract transfers those slots to compact q-bit
chunks. Thus the witness discharges the intermediate mathematical lemmas'
product-value and slot-equality premises using the actual calls; the final
convolution equation is not a caller precondition.

The witness returns `Ok` throughout its verified domain. It is not a new
general-purpose checked wrapper: behavior outside those preconditions has no
composition claim. The existing layout APIs retain all their checked error
variants and destination-preservation contracts. Their runtime oracle separately
checks invalid precision, narrow slots, multiplication overflow and source or
destination length errors, including machine-limit metadata. Noncanonical
coefficient values remain outside the APIs' explicitly stated value domain.

The generic arithmetic theorem preserves the supplied integer representatives.
It does not establish a tensor's creation history. A SAT caller that binds p to
creation precision must separately prove descriptor provenance, the appropriate
lift/reduction and the connection between those representatives and its tensor
semantics. q is convolution output precision, not a change to input provenance.

The source-bound acceptance procedure is
[`experiments/packed-product-composition/PROTOCOL.md`](../experiments/packed-product-composition/PROTOCOL.md).
It builds the complete native library and imports its matching compiled library
and Verus metadata into the actual-call client. The independent Python oracle
uses finite sums and arbitrary integers, with non-word-aligned and large
precisions, guard-word transitions, empty/positive cases, all intermediate
buffers and canaries. Focused semantic mutations and rejected invalid calls
must produce complete logical VC failures; parse errors, timeouts, solver
limits and load failures do not count. Optimized generated code is checked by
comparing the complete consumer symbol bytes and every relocation against a
plain client with the same calls.

All polynomial sequences, finite sums, theorem calls and ghost state erase.
There is no new production dispatch, backend, allocation, batching or caching
policy and no new performance measurement or claim. An analytic sum of caller
buffers at their specified capacities is `16*n*s+2*n*(c_p+c_q)` words: inputs,
two packed operands, product, scratch and output. Oversized caller scratch adds
its excess. This is a buffer budget, not a checked peak-live-space theorem.
The established packing/extraction operation counts do not close the composed
bit-cost proof. Unequal/truncated polynomial consumer composition, global bit
and peak-space theorems, SAT integration and a measured production strategy
remain open. Independent final Astra acceptance is required before merging.
