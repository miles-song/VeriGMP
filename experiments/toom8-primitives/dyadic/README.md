# Actual Dyadic Product-to-Coefficient Bridge

This module closes the explicit weight-compatibility premise of the previous actual product producer. It selects the real dyadic weights, proves their homogeneous product identity, invokes the existing verified weighted producer, and returns the even and odd parts of the independently defined fifteen-coefficient input convolution.

The accepted immutable gate is `dyadic-producer-feature1`: **478 / 478 / 478** verified items in the full library, runner and code-generation builds; **2,688** independent integer cases; **12** rejected malformed runner inputs; **8** semantic mutations rejected by genuine verification conditions. Independent review recomputed all expected values and replayed the saved actual runner. It also confirmed rejection of **72** mixed-fatal diagnostic combinations.

## Model and Actual Interface

For integer exponent `0 <= t <= 3`, the point is `p/q = 2^t` or `1/2^t`. The actual eight selected weights are `p^i * q^(7-i)`. The new proof establishes, for every `0 ≤ i, j < 8`,

```text
w[i] * w[j] = p^(i+j) * q^(14-i-j).
```

If the independent convolution coefficients are `c[0]..c[14]`, the output integers are the even-degree and odd-degree parts of `sum(c[d] * p^d * q^(14-d), d=0..14)`. The coefficients are defined from input blocks, never from executable outputs.

`candidate/native/verified/toom8_dyadic_producer.rs` implements `dyadic_pair`. Inputs retain the full-u64 domain, equal lengths and `7*k ≤ n ≤ 8*k`, including `k=0` and an empty eighth block. It accepts both reciprocal directions, integer exponents from 0 through 3, and a child threshold of at least 24. Mutable output/workspace borrows remain disjoint from each other and the immutable inputs; the immutable inputs may overlap.

The function derives the weight compatibility at the actual call site. Its returned coefficient-level identities therefore have no caller-supplied point-product correctness premise.

## Storage, Work and Evidence Limits

The inherited interface uses **14\*m** scratch words and two separate **2\*m** outputs, where `m = k+1`. The actual numerical work remains four signed evaluations, two existing verified full products, and pair normalization: local analytic work `2*T_existing_full(m) + O(k)`. The extra coefficient bridge is ghost proof. This module does not implement complete Toom8 recursion or establish a whole-kernel workspace/cost theorem.

Three inspected entry paths contain no allocator, general-division instruction/helper or element bounds panic. Structural contract/slice checks remain. Assembly inspection is a saved static check, not a measured speed result or machine-code equivalence proof.

- `publication.json` maps original and published hashes; arithmetic and checker source bytes are exact.
- `evidence/verification.json` binds the accepted source, tools, commands, actual runner runtime libraries and compiled artifact identities.
- `evidence/root-independent-audit.json` records the independent arithmetic and saved-runner review.
- `development/index.json` retains both focused development snapshots.

Run the public audit and reconstruction checks from the repository root:

```sh
python3 experiments/toom8-primitives/dyadic/audit.py
python3 experiments/toom8-primitives/dyadic/test_prepare_boundaries.py
python3 experiments/toom8-primitives/dyadic/prepare.py --output /tmp/verigmp-dyadic
```

The archive audit regenerates independent input/expected-output hashes and checks saved proof, mutation and code-generation evidence. It does not perform a new proof or execute the omitted binaries. Reconstruction creates the exact accepted source bytes in a new directory and rejects escaping paths or an existing destination. With the pinned Verus/Rust toolchain and `VERUS_BIN` configured, run a fresh full gate with:

```sh
python3 /tmp/verigmp-dyadic/check_dyadic_producer.py fresh-public-run
```

Compiled executables, rlib/vir bodies and large oracle-output logs are omitted; recorded hashes remain. Saved host paths are redacted with explicit original/published mappings. The frozen `scope.json` records the pre-gate state; accepted verification and independent review support module completion.

No benchmark was run. Endpoint removal/scaling, actual Newton callers, recomposition, recursive full/low/square kernels and performance acceptance remain separate work. Production main/default and consumer pins are unchanged.