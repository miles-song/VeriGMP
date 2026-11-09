# Bounded split-sum column prototype

This is an unverified, independently written Rust prototype. Production native
source and default dispatch are unchanged. Its selection order is prototype,
integer oracle and boundaries, performance screen, then Verus refinement and
production acceptance if the measurements justify that work.

The baseline is public main `7219cbd013dbf323f7121e4a9e197964f55377ca`, native tree
`72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`. The independent design is retained at
`E:/3sat/VeriGMP-fundamental-optimization-design-20261109/DESIGN.md`.

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

The first performance screen is fixed before timing: full products at 15 and
20 limbs, low products at 46 and 115 limbs, each with deterministic random and
all-max inputs. Compare the existing row kernel and this column kernel with
identical input bytes and preallocated caller buffers. Seven interleaved samples
of at least 10 ms per cell are required. The prospective go threshold is a
geometric mean of cell median candidate/baseline ratios at most 0.90 and every
cell at most 1.03. A failure stops expansion of this candidate. This is a decision
to invest in refinement, not a GMP-parity gate or production acceptance.

The direct prototype supports rectangular operands and arbitrary requested
prefixes within its bounded domain. The first production proposal, if justified,
will retain equal-length wrappers and existing thresholds: full leaves 8..=24,
low leaves 32..=128, with the existing row implementation elsewhere.

Comba and delayed-carry multiplication have prior art. This prototype makes no
claim to invent those algorithms or improve asymptotic multiplication bounds.
It tests a concrete bounded full-u64 split-sum layout and its potential benefit
through the existing Karatsuba and Toom recursion.
