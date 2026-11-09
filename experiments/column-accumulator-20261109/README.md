# Bounded split-sum column prototype

This is an unverified, independently written Rust prototype. Production native
source and default dispatch are unchanged. Its registered broad investment
screen is **NO-GO**: all 224 calls completed, but the eight-cell geometric mean
candidate/baseline ratio was 1.1295737903 (limit 0.90), with worst cell
1.5521974802 (limit 1.03). The completed independent review approves retaining
the negative experiment. There is no candidate formal proof or production claim.
The [portable results archive](results/RESULTS.md) retains every sample, exact
inputs, original source/build/oracle identities, controllers and both reviews.

The design baseline was public main `7219cbd013dbf323f7121e4a9e197964f55377ca`,
native tree `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`. The actual measured
prototype source is `8df6f173040f8cc9a0957420be9dfb832fe26807`, with the same
native tree. The independent [design](DESIGN.md) and [design plan](design-plan.json)
retain their original design-time wording and do not claim completed proof.

For radix `B=2^64`, arbitrary u64 limbs and positive operand lengths at most
128, define `A=sum(a[i]*B^i)`, `C=sum(b[j]*B^j)` and the independent convolution
`D[k]=sum(a[i]*b[j] : i+j=k)`. The requested q output words mean
`(A*C) mod B^q`, where `1 <= q <= len(a)+len(b)`.

Let carry C0 be zero. Each output column uses
`d[k]=(Ck+D[k]) mod B`, `C(k+1)=floor((Ck+D[k])/B)`. Consequently,
`sum(d[t]*B^t : t<k)+B^k*Ck=sum(D[t]*B^t : t<k)`.
The full product flushes one final column with no input products.

The implementation splits each 128-bit word product into its two 64-bit halves.
Two fixed scalar lanes accumulate low and high halves separately in u128.
At column end, low-half sums join the low word of the incoming carry; high-half
sums join its high word and the new low-sum carry. No full product is added to
another arbitrary u128 product. With at most 128 terms, each half sum is at most
`128*(B-1)` and the column carry is at most `128*(B-1)`. These are mathematical
design bounds; machine-checked refinement is pending.

The registered performance screen covered full products at 15 and
20 limbs, low products at 46 and 115 limbs, each with deterministic random and
all-max inputs. It compared the existing row kernel and this column kernel with
identical input bytes and preallocated caller buffers, using seven alternating
ABBA/BAAB blocks, or 14 batches per side per cell. Each batch had to last at least
10 ms. The prospectively fixed go threshold was a
geometric mean of cell median candidate/baseline ratios at most 0.90 and every
cell at most 1.03. That broad scope failed. Low-115 random/all-max ratios of
0.7898951721/0.7667612222 are a prospective scoped hypothesis only; retained
sample variation and the broad failure prevent accepted performance claims.
The screen is an investment decision, not a GMP-parity or production gate.

The direct prototype supports rectangular operands and arbitrary requested
prefixes within its bounded domain. Its historical production proposal retained
equal-length wrappers and existing thresholds: full leaves 8..=24, low leaves
32..=128, with the existing row implementation elsewhere. The failed broad
screen does not justify implementing that proposal. Any narrower follow-up
requires a new prospective experiment.

Comba and delayed-carry multiplication have prior art. This prototype makes no
claim to invent those algorithms or improve asymptotic multiplication bounds.
It tests a concrete bounded full-u64 split-sum layout and its potential benefit
through the existing Karatsuba and Toom recursion.
