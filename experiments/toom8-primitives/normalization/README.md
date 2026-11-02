# Actual Endpoint Removal and Newton-Node Normalization

This module derives six normalized Newton node pairs from actual input blocks, endpoint products and dyadic point products. It proves each subtraction remains nonnegative, each division is exact, and each final scale fits the existing output capacity.

The accepted immutable gate is `normalization-feature1`: **500 / 500 / 500** verified items in library, runner and code-generation builds; **2,016** independent integer cases; **12** rejected malformed runner inputs; **12** semantic mutations rejected by genuine verification conditions. Independent review recomputed and replayed every saved actual-runner case, and checked **108** mixed-fatal diagnostic combinations.

## Six Node Pairs

Let `c[0]..c[14]` be the independently defined convolution of the two eight-block inputs. For `p/q` equal to `1/8, 1/4, 1/2, 1, 2, 4`, set `s=64*p²/q²`, giving the six integer nodes `1, 4, 16, 64, 256, 1024`. The output values are

```
N_even(s) = sum(c[2*j+2] * 64^(5-j) * s^j, j=0..5)
N_odd(s)  = sum(c[2*j+1] * 64^(6-j) * s^j, j=0..6).
```

The actual code removes `c[0]*q^14` and `c[14]*p^14` from the homogeneous even product, divides by `(p*q)²`, and scales by `(64/q²)^5`. It divides the homogeneous odd product by `p*q` and scales by `(64/q²)^6`. All constants and exactness conditions are proved for the six supported points. Ghost lemmas connect these values to the existing Newton module's six initial state expressions; this feature does not yet call Newton interpolation.

## Actual Interfaces and Storage

`candidate/native/verified/toom8_normalization.rs` provides three layers:

- `normalize` consumes proven raw node values and correct endpoint coefficient buffers.
- `with_endpoints` generates the actual point products and derives raw-node conditions. Its endpoint buffers must contain the two input-defined endpoint products.
- `prepare_pair` computes those endpoints itself, then calls the shared-endpoint interface.

The full-u64 input domain is unchanged: equal lengths with `7*k <= n <= 8*k`, including `k=0` and an empty last block. Empty endpoints are handled without invoking a nonempty multiplication routine. The child threshold is at least 24. Mutable output/workspace borrows are disjoint from each other and immutable inputs; immutable inputs may overlap.

With `m=k+1`, outputs are two separate **2*m** slices. The shared-endpoint interface requires **14*m** scratch words; the self-contained interface requires **18*m**, split into **2*k** low-endpoint words, **2*h** high-endpoint words and at least **14*m** child workspace, with `h=n-7*k`.

Local analytic work is `2*T_existing_full(m)+O(k)` with shared endpoints, or `T_existing_full(k)+T_existing_full(h)+2*T_existing_full(m)+O(k)` for the self-contained interface, skipping empty endpoint products. Children remain the existing verified full-product kernel. A complete caller can reuse two endpoints across all six pairs and retain the intended **2+12+1=15** child-product design; this feature neither implements that complete caller nor claims a whole-kernel cost/lifetime theorem.

Three inspected machine-code entry paths have no allocator, general-division instruction/helper or element bounds panic. Structural contract/slice checks remain. This static inspection is not a benchmark or machine-code equivalence proof.

## Saved Evidence and Reproduction

`publication.json` maps exact source bytes and sanitized logs to original/published hashes. `evidence/verification.json` binds sources, tools, actual runner runtime libraries, commands and compiled artifact identities. `evidence/root-independent-audit.json` records independent integer recomputation and saved-runner replay.

`development/index.json` retains all **six** development attempts, including algebra and precondition failures and a resource-limit failure. The resource failure is preserved as a failed attempt, never accepted as semantic mutation rejection.

```sh
python3 experiments/toom8-primitives/normalization/audit.py
python3 experiments/toom8-primitives/normalization/test_prepare_boundaries.py
python3 experiments/toom8-primitives/normalization/prepare.py --output /tmp/verigmp-normalization
```

The public audit regenerates independent input and expected-output hashes and checks saved evidence. It does not rerun omitted executables or perform a new proof. Reconstruction restores the exact accepted input bytes in a new directory and rejects path traversal or an existing destination. With the pinned Verus/Rust toolchain and `VERUS_BIN` configured:

```sh
python3 /tmp/verigmp-normalization/check_normalization.py fresh-public-run
```

Compiled executables, rlib/vir bodies and large oracle-output logs are omitted; their hashes remain. Host paths are redacted with explicit mappings; arithmetic source bytes are preserved. The frozen `scope.json` is a pre-gate record, while accepted verification and review evidence establish this module's completion.

No benchmark was run. Actual even/odd Newton callers, seventh odd node, recomposition, recursive full/low/square kernels, complete workspace lifetimes and performance acceptance remain separate features. Production main/default and consumer pins are unchanged.