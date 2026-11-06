# Using VeriGMP

VeriGMP is consumed as a Verus-compiled Rust library: a `.rlib` for the code and a
`.vir` file for its Verus contracts. There is currently no Cargo package, no
crates.io release and no GMP-compatible API. This guide covers the supported
platform, the pinned toolchain, the public functions and their domains, and how
another project should depend on a verified snapshot.

## Platform and prerequisites

The pinned bootstrap supports x86_64 Linux, including WSL. Native Windows, macOS
and other architectures have not been validated by this project's bootstrap;
`scripts/setup_verus.py` exits on them.

Install these first:

- Python 3.12 or newer (`setup_verus.py` uses `hashlib.file_digest`).
- rustup, used to install the pinned Rust toolchain.
- `g++` and `libgmp-dev`. The verification pipeline builds a GMP ABI check and
  benchmark controls; the library itself does not link GMP.

## Pinned toolchain

[native/toolchain.json](../native/toolchain.json) fixes the Rust toolchain
(`1.99.1-x86_64-unknown-linux-gnu`), the Verus release
(`0.2026.10.26.d17fbd0`), its download URL and its archive SHA-256.

```sh
rustup toolchain install 1.99.1 --profile minimal
python3 scripts/setup_verus.py
```

`setup_verus.py` downloads the archive into `deps/verus-download/`, refuses it if
the hash differs and extracts it to `deps/verus/`. It prints the verifier path,
`deps/verus/verus-x86-linux/verus`. It does not edit shell profiles or global
settings.

To use an existing Verus installation, set `VERUS_BIN` to its `verus` executable.
`verify.py` checks that the reported Verus and Rust versions match the pin and
stops otherwise.

## Building and exporting the library

```sh
python3 scripts/verify.py
```

This copies selected repository files into a private temporary snapshot: the
Rust and C++ sources, scripts, JSON pins, top-level documents, `examples/*.rs`
and everything under `docs/`. Files are selected by path pattern, so untracked
files in those locations are included. Every step then runs from that snapshot:
proof and optimized compilation of the library; verification, compilation and
execution of each example against the `.rlib` and `.vir` just produced; the
per-module oracles, mutation checks, code-generation inspection and benchmarks.
It then checks that none of the selected input files or verifier files changed
during the run. Only after all of that does it copy two files into `build/`:

| File | Content |
|---|---|
| `build/libverigmp.rlib` | The library compiled with `-O` |
| `build/verigmp.vir` | The Verus metadata (contracts and specs) for the same compilation |

Evidence goes to `results/verification.json` and per-module subdirectories. For
each example the report records the verified item count, the program output and
the binary's SHA-256, and the run fails if the binary changes while it executes.
`--export-dir DIR` and `--output DIR` move the two locations. Both `build/` and
`results/` are ignored by git. The script prints a JSON summary ending in
`"status": "pass"` and exits nonzero on any failure.

Every run includes the benchmarks; there is no separate proof-only entry point.

## Multiplying and squaring

The public functions are in `verigmp::arithmetic`:

```rust
pub fn workspace_len(n: usize) -> Option<usize>          // Some(12n)
pub fn square_workspace_len(n: usize) -> Option<usize>   // Some(10n)
pub fn mul_mod(dst: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64], top: u32)
pub fn square_mod(dst: &mut [u64], a: &[u64], scratch: &mut [u64], top: u32)
```

With `n = a.len()` and `p = 64*(n-1) + top`, `mul_mod` leaves
`value(dst) = value(a) * value(b) mod 2^p`, and `square_mod` leaves
`value(dst) = value(a)^2 mod 2^p`. Both results are canonical: `value(dst) < 2^p`,
so bits above `top` in `dst[n-1]` are zero.

A minimal program, taken from
[examples/modular_arithmetic.rs](../examples/modular_arithmetic.rs):

```rust
use verigmp::arithmetic;

fn mul_mod(a: &[u64], b: &[u64], top: u32) -> Vec<u64> {
    let n = a.len();
    let words = arithmetic::workspace_len(n).expect("n > 0 and 12n must fit in usize");
    let mut scratch = vec![0u64; words];
    let mut out = vec![0u64; n];
    arithmetic::mul_mod(&mut out, a, b, &mut scratch, top);
    out
}

fn square_mod(a: &[u64], top: u32) -> Vec<u64> {
    let n = a.len();
    let words = arithmetic::square_workspace_len(n).expect("n > 0 and 10n must fit in usize");
    let mut scratch = vec![0u64; words];
    let mut out = vec![0u64; n];
    arithmetic::square_mod(&mut out, a, &mut scratch, top);
    out
}
```

For `a = [3, 1]` and `b = [5, 2]`, `mul_mod(&a, &b, 64)` returns `[15, 11]` and
`square_mod(&a, 64)` returns `[9, 6]`. With `top = 1` the modulus is `2^65` and
the results are `[15, 1]` and `[9, 0]`.

Build and run the example after `verify.py` has exported the library:

```sh
VERUS_BIN="$PWD/deps/verus/verus-x86-linux/verus"
"$VERUS_BIN" examples/modular_arithmetic.rs \
  --import verigmp=build/verigmp.vir \
  --extern verigmp=build/libverigmp.rlib \
  --compile -O -o build/modular-example
./build/modular-example
```

Expected output:

```text
mod 2^128: a*b = [15, 11], a^2 = [9, 6]
mod 2^65:  a*b = [15, 1], a^2 = [9, 0]
600 limbs, top in {1, 37, 64}: (2^38400 - 1)^2 mod 2^p = 1
```

The example also contains a small `verus!` function whose postcondition Verus
proves from the imported `mul_mod` contract; it is the one verified item Verus
reports for this file. The rest of `main` is ordinary Rust: its assertions test
the behavior but are not a proof.

## Choosing `n` and `top`

Every operand, and the output, has exactly `n` limbs. To work modulo `2^p` for a
bit count `p > 0`, choose

```text
n   = (p - 1) / 64 + 1
top = (p - 1) % 64 + 1
```

`verigmp::pow2::precision_layout(p)` computes this pair and is proved to satisfy
`64*(n-1) + top = p` without overflow. Inputs must have exactly `n` limbs, but
they need not be reduced: bits of the last limb above `top` are allowed and
contribute nothing modulo `2^p`.

## Scratch workspace

The caller allocates scratch once and may reuse it for any number of calls.

- `mul_mod` requires `scratch.len() >= 12n`; `square_mod` requires `>= 10n`.
  Larger buffers are fine.
- `workspace_len(n)` returns `None` when `n == 0` or when `12n` would overflow
  `usize`; `square_workspace_len` does the same for `10n`. A `Some` value says the
  size is representable, not that an allocation of that size will succeed.
- Initial scratch contents are irrelevant, and contents after the call are
  unspecified. Only the length is preserved.
- The older `fast_multiply::mul_mod` entry needs only `4n` scratch
  (`fast_multiply::workspace_len`) and always uses Karatsuba. It is kept for
  existing callers. Passing a `4n` buffer to `arithmetic::mul_mod` is outside its
  domain.

## Domains, aliasing and failures

The contracts require:

- `n = a.len() > 0`, `b.len() == n` and `dst.len() == n`;
- `scratch` at least `12n` (product) or `10n` (square) words;
- `1 <= top <= 64`.

Rust borrowing defines the alias rules. `dst` and `scratch` are exclusive mutable
borrows, so neither may overlap an input or each other. `a` and `b` are shared
borrows and may be the same slice; `mul_mod(dst, a, a, ...)` is a valid square
and is covered by the oracle. The initial contents of `dst` do not matter.

A caller written inside Verus must prove these preconditions; the verifier
rejects a call that it cannot show satisfies them. Ordinary Rust callers are not
checked statically. The implementation contains runtime entry assertions on
lengths, `top` and the scratch needed by the path actually taken, and the oracle
confirms that `top = 0`, `top = 65` and a `3n` scratch buffer panic. These checks
are not a full runtime validation of the contract: for example, a product with
`n < 512` takes the Karatsuba path, which asserts only `4n` scratch, so a buffer
between `4n` and `12n` is not rejected there. Size buffers with `workspace_len`
and `square_workspace_len` rather than relying on a panic.

## Using VeriGMP from another project

Depend on one verified commit, build it with the pinned toolchain, and import the
`.rlib` and `.vir` that came out of the same run. A `.vir` from one source
snapshot paired with an `.rlib` from another would let Verus check your code
against contracts that the linked code was never proved to satisfy.

A git submodule pinned to the source baseline:

```sh
git submodule add https://github.com/miles-song/VeriGMP.git third_party/VeriGMP
git -C third_party/VeriGMP checkout bf2821728fb5c7228609c4447327ba95eccdc5c9
git add .gitmodules third_party/VeriGMP
```

Commit `bf2821728fb5c7228609c4447327ba95eccdc5c9` reproduces the library source
used by the frozen benchmark data. Those measurements retain their original
commit identity `ab5eaf670865a4438301b6dce6b4e5175c4a6c22`; the code-equivalence
mapping is recorded in [history-provenance.json](../native/history-provenance.json).
This baseline predates the documentation examples, the proved full-square leaf
and modular subtraction. For those features, pin a later commit whose own
accepted local source gate and independent review cover the consumed API, and
build its matching verified library/metadata pair. A complete-library claim needs
the complete `verify.py` snapshot; CI is supplemental.

Build the dependency into a directory your project owns:

```sh
cd third_party/VeriGMP
rustup toolchain install 1.99.1 --profile minimal
python3 scripts/setup_verus.py
python3 scripts/verify.py --export-dir ../../build/verigmp --output ../../build/verigmp-results
cd ../..
```

Then compile your crate with the same verifier:

```sh
VERUS_BIN="$PWD/third_party/VeriGMP/deps/verus/verus-x86-linux/verus"
"$VERUS_BIN" src/main.rs \
  --import verigmp=build/verigmp/verigmp.vir \
  --extern verigmp=build/verigmp/libverigmp.rlib \
  --compile -O -o build/my-app
```

Use the same Verus release and Rust toolchain for your crate as for the library.
In an integration test, check the actual artifacts rather than the directory
entry: the submodule's checked-out commit, the `"status": "pass"` field and
`library.files` hashes in `build/verigmp-results/verification.json`, and the
hashes of the two files you pass to Verus.

## What is not provided

General division, modular inversion, signed integers, allocation-managing integer
types, string conversion and a GMP-compatible `mpz`/`mpn` interface are not part
of the library. `toom_words::divide_word` divides by an arbitrary word and is
public because interpolation uses it with constants 2 and 3, but it is a
building block, not a general division API.
