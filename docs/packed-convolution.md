# Exact packed convolution model

`packed_convolution` is an erased mathematical interface for clients that want
to multiply finite coefficient arrays using an integer product. Its status is
`model_proved`. It supplies no runtime polynomial multiplication, packing or
extraction function and changes no arithmetic dispatch.

`coefficient(a,c,k)` is the independent finite sum of `a[i]*c[k-i]` over all
input indices `i`, with out-of-range terms equal to zero. `convolution(a,c)` has
`a.len()+c.len()` coefficients, including a harmless final zero. The general
`convolution_product` theorem proves

```text
packed(convolution(a,c),B) = packed(a,B) * packed(c,B),
packed(a,B) = sum_i a[i] * B^i.
```

This identity covers arbitrary signed integer coefficients and arbitrary
integer B. It does not assume a correct output or a convolution identity.

For canonical input coefficients `0 <= a[i],c[j] < m`, let
`L = min(a.len(),c.len())`. The model counts the actual overlap of the index
intervals and proves every coefficient lies in `0..=L*(m-1)^2`. If `m>=1`,
`B>0` and `B>=L*m*m`, every coefficient is strictly below B, including when
one input is empty. `packed_convolution_extract` therefore proves that slot k
of the exact integer product is the mathematical convolution coefficient.
When `m` divides B, `packed_convolution_residue` also proves that the product
quotient modulo m directly gives that coefficient modulo m.

For `m=2^p`, positive p and `L<=2^g`, `guard_bits` proves that
`w>=2*p+g` suffices for `B=2^w`. Choosing `g=ceil(log2(L))` when `L>0` gives
the intended width. Computing that ceiling efficiently is a future executable
obligation. `word_aligned_guard` connects this result to `B=radix(slot_limbs)`
when `64*slot_limbs>=2*p+g`. Guard bits create spacing only; the input
coefficient representatives retain their original precision and meaning.

`retained(a,D)` takes the first `min(a.len(),D)` coefficients. The truncation
theorems prove that truncating both inputs preserves every coefficient below D.
`truncated_extract` combines truncation, guard sufficiency and residue extraction
for indices within the retained product's allocated slots. `coefficient_zero`
supplies zero beyond its support. Empty inputs and D=0 have zero packed product;
neither case needs a positive-L logarithm.

The interpretation function `slots(words,s,n)` reads n consecutive, little-endian
slots of s limbs each as mathematical integers. `slots_prefix` and
`slots_integer` prove that packing those coefficients in radix `2^(64*s)`
equals the corresponding limb prefix or complete limb integer. All lengths
and indices in this model are mathematical naturals. This theorem does not
establish a machine-capacity check or an executable borrow/alias contract.

The focused gate is:

```sh
python3 experiments/packed-convolution/verify.py \
  --deps-root /path/to/pinned/deps --output /fresh/persistent/evidence
```

It requires a clean committed worktree and uses the installed Windows Git for a
Windows-managed worktree when available under WSL; otherwise it translates the
actual Git worktree pointer for Linux Git. It verifies the resolved worktree
root and checks source bytes against HEAD, and records source and tool hashes.
It verifies and compiles the same focused
model with optimization, exports its library and proof metadata, verifies
Python-generated exact fixtures against that export, runs independent Python
integer checks and requires logical rejection of four semantic mutations.
Timeouts, parse failures and verifier resource limits do not count as rejection.
The gate compiles an imported client containing ghost finite sums and theorem
calls and checks its actual optimized body against an ordinary identity control:
both must contain the same move/return instructions. No coefficient object,
traversal or proof call survives in that body. An exported Verus library can
retain defensive panic stubs for spec/proof names; these are not executable
implementations of the mathematics. This is a focused model gate, not the
complete-library performance/acceptance gate.

`verified/packed_layout.rs` contains an experimental borrowed-slice candidate.
`checked_layout` keeps coefficient precision p separate from the aligned slot
width, obtains the coefficient limb count from the existing precision helper,
and checks both `count * coefficient_limbs` and `count * slot_limbs` before
returning exact buffer lengths. `pack_coefficients` copies compact coefficient
limbs into caller-owned slots and explicitly zeros guard/padding limbs.
`extract_coefficients` copies only the coefficient limbs from caller-owned
slots. Both validate exact slice lengths before their first write and preserve
the destination on every returned error. Rust's safe mutable/shared slice
borrows exclude input/output overlap at the call boundary.

Canonical p-bit coefficient chunks and canonical p-bit packed slots with zero
guard/padding limbs are explicit Verus domain preconditions. The runtime does
not scan those values; the caller must already maintain the representation
invariant. For non-word-aligned p, canonical input chunks have zero unused top
bits, so no runtime mask or precision change is needed. Slot padding does not
change creation precision.

The pinned same-source Verus/Rust gate now passes the functional refinement and
runtime checks for this candidate: the library build verified 348 items, the
independent integer oracle covered 208 valid and 18 error-preservation cases,
the borrow-overlap fixture was rejected by Rust, and three scoped semantic
mutants were rejected by complete logical VCs. The candidate is recorded as
`impl_refined`; optimized code-generation comparison, checked cost bounds and
independent Astra acceptance remain pending. It does not include product
composition or alter arithmetic dispatch, and is not a performance claim.
The mathematical Seq and finite sums do not authorize materializing polynomial
objects or repeated whole-integer shifts in a hot path. No FFI or arithmetic
trust boundary is introduced by this module.

For retained lengths A and C, coefficient width p, slot width w and output order
D, the candidate's source loops copy A+C coefficient chunks and zero at most
(A+C)*(w-ceil(p/64)) padding words; extraction copies at most D*ceil(p/64)
words. Erased loop counters prove exact copied, written and zeroed word totals;
they are not a bit-cost or peak-live-space theorem. Operand and packed-result
storage is caller-owned and proportional to the supplied slice lengths; the
functions allocate no heap storage. A product
routine would add its multiplication cost and product buffer. With
`w=O(p+log L+64)`, this is an analytic construction budget under an explicit
multiplication-cost model, not a composed bit-cost/space theorem or measured
performance. Small-precision, sparse and ordinary-convolution crossovers require
measurement. No benchmark, solver theorem, native-GMP parity or backend
replacement follows from this model.
