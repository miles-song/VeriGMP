# VeriGMP

VeriGMP develops fast multiprecision arithmetic in Rust with Verus proofs of the
actual executable functions. It adopts algorithm and storage strategies from GMP
and measures the resulting implementation against GMP and ordinary Rust controls.

The current library provides borrowed-slice addition, normalization modulo `2^p`,
schoolbook multiplication, difference-form Karatsuba, five-point Toom-3,
dedicated recursive squaring and truncated low-product recursion. Inputs and outputs use little-endian 64-bit words. The caller owns
output and reusable workspace; recursive multiplication does not allocate.

This is an independent experimental arithmetic library, not verification of GMP's
implementation or a complete GMP-compatible API. Performance parity is not claimed.
Architecture-specific assembly, symmetry-specialized basecase squaring, higher
Toom variants and FFT remain outside the implemented scope.

## Verified contracts

For `B=2^64`, the representation is `value(a)=sum(a[i]*B^i)`.

| Operation | Result | Required workspace |
|---|---|---|
| Addition | Exact sum with final carry | Constant auxiliary storage |
| Karatsuba full multiplication | `value(out)=value(a)*value(b)` | `3n` words plus `2n` output |
| Karatsuba low/modular multiplication | Product modulo `B^n` or `2^p` | `4n` words plus `n` output |
| Toom full/low multiplication | Full product or low `n` words | `12n` words plus output |
| Toom full/low square | Full square or low `n` words | `10n` words plus output |
| `arithmetic::mul_mod` | Canonical product modulo `2^(64*(n-1)+top)` | `12n` words plus `n` output |
| `arithmetic::square_mod` | Canonical square at the same precision | `10n` words plus `n` output |
| MAC4 row candidate | Exact `old(out)+word*prefix(rhs)` with final carry | Constant auxiliary storage |

Lengths, positive precision, exclusive mutable borrows and capacity conditions are
part of the contracts. Inputs may have noncanonical high words and the initial
output may be arbitrary. `workspace_len` checks whether the requested workspace
length can be represented; it does not promise successful memory allocation.

The production API is `arithmetic::mul_mod` and `arithmetic::square_mod`.
`arithmetic::workspace_len(n)` and `square_workspace_len(n)` return checked sizes.
The product dispatcher retains Karatsuba below 512 words and uses Toom above that
boundary, with Toom threshold 192, low threshold 128 and short-block ratio 9/40.
The square dispatcher uses threshold 192, low threshold 64 and ratio 11/36.
These are fixed measured policies, not universal optimum claims. The original
`fast_multiply` API retains its `4n` workspace and Karatsuba behavior.

Toom splits the input polynomial into three blocks, evaluates at `0, 1, -1, 2`
and infinity, recursively multiplies five point values, interpolates with exact
divisions by 2 and 3, and recomposes shifted coefficients. Separate models establish
coefficient meaning and bounds before executable evaluation, interpolation and
recursion are composed. Squaring evaluates each point once and computes each low
cross product once, adding it twice. Its leaf multiplication is still the general
basecase. The proved MAC4 candidate is benchmarked but disabled in the default
path because local measurements did not show a consistent improvement. Its
compiled loop still retains element bounds checks; the production product/square
call graphs are inspected separately and have no such checks.

For fixed thresholds, the Toom source recurrence analytically yields
`O(n^log3(5))`, approximately `O(n^1.465)`, word operations. It uses linear scratch
and logarithmic recursive depth. Capacity and termination obligations are checked;
a composed closed-form cost theorem remains open. This arithmetic bound does not
establish the complexity or correctness of an application using the library.
Current scope is recorded in [native/proof-status.json](native/proof-status.json).

## Reproduce verification and experiments

On x86_64 Linux, including WSL, install Python 3.12+, `g++`, `libgmp-dev` and rustup.
The Rust/Verus versions and verifier archive hash are pinned in
[native/toolchain.json](native/toolchain.json).

```sh
rustup toolchain install 1.99.1 --profile minimal
python3 scripts/setup_verus.py
python3 scripts/verify.py
```

`VERUS_BIN` can select an existing matching installation. The verifier runs proofs,
optimized builds, independent Python-integer checks, semantic mutations, reachable
assembly inspection and interleaved benchmarks from one private input snapshot.
Evidence is written to `results/verification.json` and per-module subdirectories.
The compiled library and corresponding Verus metadata are exported together to
`build/`; use `--export-dir` and `--output` to place them elsewhere.

Benchmarks retain full CSV observations, pin a CPU and compare identical result
semantics. The GMP baselines call public `mpn_mul_n` or `mpn_sqr` and then truncate/mask their
full results; its internal allocation is not instrumented. Dynamic-threshold
controls are distinguished from compiler-specialized default dispatch. The Toom
comparison measures algorithm changes against the previous verified Karatsuba
entry and GMP; it does not isolate the cost of proof annotations. The MAC4 row
comparison includes the original loop and GMP `mpn_addmul_1`. Raw timing data and
source/tool hashes are retained in the workflow artifacts; a passing run does not
require a noisy machine to reproduce a particular speedup.

## Trust and provenance

The core uses no assumed/external arithmetic implementation. Verus, its vstd
specifications, Z3, Rust/LLVM and the runtime platform remain trusted. Test I/O,
Python oracles, ordinary controls and GMP benchmark FFI are outside the functional
proof boundary. Compilation is tied to the same source and tool identities as
verification; downstream consumers must preserve that connection.

GMP 6.3.0 source references and adopted strategies are pinned in
[native/gmp-reference.json](native/gmp-reference.json). The Rust implementation and
proofs are independently written. This repository's code is under the
[MIT license](LICENSE); third-party implementations are not bundled into the core.
