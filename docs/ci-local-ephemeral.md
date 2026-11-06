# Running arithmetic CI on a local ephemeral runner

The arithmetic workflow supports a manual local runner when a GitHub-hosted
runner is unavailable. Pushes, pull requests, and the default manual choice
continue to use `ubuntu-24.04`. A manual run with `runner_kind=local-ephemeral`
requires all four labels: `self-hosted`, `Linux`, `X64`, and
`verigmp-ephemeral`. The repository-specific label separates this workload from
other local runner routes.

The local route has not yet been registered or dispatched for this VeriGMP
workflow. Static workflow validation does not establish a successful remote run.

## Runner requirements

Use a repository-scoped ephemeral GitHub Actions runner on x86_64 Linux. Its
operator registers it for one reviewed run with the `verigmp-ephemeral` label,
using the existing trusted registration process. Registration, credentials,
runner shutdown, and workspace cleanup remain operator responsibilities.
The workflow requests only `contents: read`; checkout disables persistent Git
credentials. It adds no external credential or authentication configuration.

The runner must already have `rustup`, a C++17 compiler exposed as `c++`, `ldd`,
GMP development headers and the GMP shared library. The local preflight checks
the tools and compiles and runs `native/controls/gmp_abi.cpp`, including its
64-bit, zero-nail GMP ABI assertions. Missing tools, headers, libraries, or a
failed ABI probe cause a clear failure before proof work. The local route does
not run `sudo`, install system packages, or change authentication settings.
The hosted route retains its `g++` and `libgmp-dev` apt installation.

Both routes use the existing pinned checkout, Python setup, cache, and artifact
actions. Python setup selects 3.12. Rust toolchain installation reads
`native/toolchain.json`, installs that exact toolchain, and prints `rustc -vV`.
The job sets `CARGO_HOME` to `${{ github.workspace }}/deps/cargo` and `RUSTUP_HOME`
to `${{ github.workspace }}/deps/rustup`; existing user Rust homes and shell
profiles are unaffected. `rustup` itself must already be on the runner's PATH.

## Dispatch and evidence

After independent review and publication of the workflow, select the reviewed
ref in the Actions UI and choose `local-ephemeral`, or dispatch that ref with:

```sh
gh workflow run verify.yml --ref "$REVIEWED_REF" -f runner_kind=local-ephemeral
```

The local job has a 120-minute limit to allow the full serial proof workload
and its benchmarks. Hosted jobs retain the 25-minute limit. The Python gates'
individual command timeouts are unchanged. Reserve a quiet timing window before
starting the job: the gate includes benchmarks, and unrelated proof or benchmark
processes can contaminate their measurements.

The command remains `python3 scripts/verify.py`. It freezes one source snapshot,
checks the actual Verus and Rust identities, proves and compiles the library
and imported examples, and runs every module gate for limbs, power-of-two
precision, multiplication, recursive multiplication, Toom, and squares. Those
gates retain independent integer oracles, invalid-input checks, semantic
mutations, optimized code inspection, tuning, and repeated benchmark workloads.
The workflow does not use the targeted gate's optional no-timing mode.

Only `deps/verus-download` is cached, with a key derived from
`native/toolchain.json`. `scripts/setup_verus.py` checks the archive's pinned
SHA-256 even on cache hits before extracting it. Proof reports, compiled
arithmetic, or benchmark results are not reused as cached gate outcomes.
The full gate records actual source and tool hashes and produces new raw
observations. The `arithmetic-refinement-linux` artifact uploads `results/`
even after a failure; missing results are an artifact error.

A successful run establishes the recorded source-bound gate on that runner.
Its timings describe its hardware and load. It does not replace the separate
matched ABBA/BAAB acceptance data, establish library-wide GMP parity, promote
the GMP backend replacement, or close the native performance target.
