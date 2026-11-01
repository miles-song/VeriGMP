# VeriGMP

VeriGMP develops fast multiprecision arithmetic in Rust with Verus proofs of the
actual executable functions. It adopts algorithm and storage strategies from GMP
and measures the resulting implementation against GMP and ordinary Rust controls.

The current library provides borrowed-slice addition, normalization modulo `2^p`,
schoolbook multiplication, difference-form Karatsuba and truncated low-product
recursion. Inputs and outputs use little-endian 64-bit words. The caller owns
output and reusable workspace; recursive multiplication does not allocate.

This is an independent experimental arithmetic library, not verification of GMP's
implementation or a complete GMP-compatible API. Performance parity is not claimed.
Toom, specialized squaring and further word-level optimizations are in development.

## Verified contracts

For `B=2^64`, the representation is `value(a)=sum(a[i]*B^i)`.

| Operation | Result | Required workspace |
|---|---|---|
| Addition | Exact sum with final carry | Constant auxiliary storage |
| Full multiplication | `value(out)=value(a)*value(b)` | `3n` words plus `2n` output |
| Low multiplication | Product modulo `B^n` | `4n` words plus `n` output |
| Modular multiplication | Canonical product modulo `2^(64*(n-1)+top)` | Same as low multiplication |

Lengths, positive precision, exclusive mutable borrows and capacity conditions are
part of the contracts. Inputs may have noncanonical high words and the initial
output may be arbitrary. `workspace_len` checks whether the requested workspace
length can be represented; it does not promise successful memory allocation.

The default policy uses Karatsuba threshold 24, low-product threshold 64 and short
block ratio 11/36. Fixed-threshold source recurrences analytically yield
`O(n^log2(3))` word operations. Recursive capacity and termination obligations are
checked, while a composed closed-form cost theorem remains open. Current scope is
recorded in [native/proof-status.json](native/proof-status.json).

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
semantics. The GMP baseline calls public `mpn_mul_n` and then truncates/masks its
full product; its internal allocation is not instrumented. Dynamic-threshold
controls are distinguished from compiler-specialized default dispatch.

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
