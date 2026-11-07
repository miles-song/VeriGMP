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
The optimized focused library must contain no executable/data symbols. This is
a focused model gate, not the complete-library performance/acceptance gate.

Executable refinement remains open: linear limb packing and extraction with
caller-owned buffers, checked initialized lengths and capacity, preservation on
errors, permitted input/output aliasing, arbitrary machine-representable
precision and composition with an exact integer product. The mathematical
Seq and finite sums do not authorize materializing polynomial objects or
repeated whole-integer shifts in a hot path. No FFI or arithmetic trust boundary
is introduced by this module.

For a future implementation with retained lengths A and C, coefficient width p,
slot width w and output order D, packing operands and scanning requested slots
can use O((A+C+D)*w) bit work and O((A+C)*w) operand storage; an integer product
adds its multiplication cost and product storage. With
`w=O(p+log L+64)`, this is a candidate construction cost under an explicit
multiplication-cost model. These are analytic design budgets, not checked
operation counts, a composed bit-cost/space theorem or measured performance.
Small-precision, sparse and ordinary-convolution crossovers require measurement.
No benchmark, solver theorem, native-GMP parity or backend replacement follows
from this model.
