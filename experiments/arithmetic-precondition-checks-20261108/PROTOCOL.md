# Checked Karatsuba entry and private recursion

The candidate starts from committed main
`de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9`. Only the
`fast_multiply::full` family changes: the original public signature, mathematical
contract and runtime entry assertions remain, while a private worker implements
the same three-product recursion under the same verified preconditions. Its
length/capacity/threshold facts are proved in ghost code. The arithmetic identity,
scratch layout, base_full, leaf threshold, low-product policies, Toom and square
implementations and all checked-error functions remain unchanged.
The public entry still calls base_full directly when n<=threshold; only a
recursive-sized input enters the private worker. The worker keeps the same
leaf condition for its three recursive children.

The independent mathematical meaning is the existing little-endian integer
interpretation and `value(dst)=value(a)*value(b)`. Every private recursive call
must establish equal positive input lengths, exactly 2n output limbs, at least
3n scratch limbs and threshold >=8. The public entry preserves its existing
pre-write panic checks. Rust slice safety checks remain. No unsafe operation,
unreachable hint, axiom, FFI, additional runtime scan or allocation is permitted
in the arithmetic core. Test-only GMP FFI is outside the verified library.

Static baseline audit retains complete symbol sections, raw bytes, relocations
and full disassembly. It distinguishes contract assertion branches from Rust
slice checks and records wrapper/worker/leaf/caller bodies. Old accepted rlib
evidence may establish unchanged baseline source identity, but before/after
code-generation comparisons use exactly matching compiler/codegen flags.
An ordinary Rust control with the same calls is compared by complete symbol
bytes and normalized relocations, including all recursion and panic paths.
Its external helper calls can inline differently from the actual intra-crate
calls; any such difference is recorded instead of claiming whole-worker byte
identity. The public entry is required to match the ordinary control exactly
after normalizing relocation targets.
No truncated disassembly or instruction-prefix count is evidence.

Before timing, the modified full native library must pass a fresh pinned
`--no-cheating --compile -O` build, with exact source/tool/rlib/vir identities.
Independent Python integers define each expected output. The same optimized
runtime cases also check GMP results, complete output, input preservation,
nonzero initial storage, exact/extra scratch capacities and canaries. Cases
cover leaf/recursive boundaries, odd/even lengths, all difference-sign pairs,
zero/equal/high-carry inputs, top-bit bounds and actual default callers.
The unchanged public panic boundaries and ownership rules are rechecked.
Fresh strict semantic mutants target wrong public-to-private forwarding,
insufficient private scratch assumptions and an incorrect child partition;
only complete logical VC failures count, never tool/type/load/timeout faults.
Independent Astra prereview is required before any benchmark run.

The preregistered measurement shapes are the exact 26 `(n,top)` shapes in
`native/performance-target.json` for actual `arithmetic::mul_mod` and
`arithmetic::square_mod`, plus forced `fast_multiply::full` at threshold 24 for
n in `1,2,7,8,9,23,24,25,31,32,33,47,48,49,63,64,65,127,128,129,191,192,193,
255,256,257,511,512,513,1023,1024,1025,2048,4096`.
The forced full shapes are necessary because a wrapper may affect small calls
and recursive/leaf boundaries differently. Square default is an unchanged
control. The first source-fixed measurement plan is frozen before any timing;
there is no threshold tuning or shape-based dispatch selection in this feature.

Both builds use the same pinned release flags and identical ordinary harness
source, preallocated output/scratch and deterministic input values. Each sample
contains at least 10ms of arithmetic, seven samples per registered shape/path,
with alternating before/after order and a confirming second independent run
using the same binary hashes. All results and regressions are retained; expected
answers are checked outside timing. GMP uses its public full product/square,
followed by the required low-half copy and mask for modular operations.
Calibration, allocation, copying of fixtures and output occur outside accepted
timed samples; `black_box` protects runtime inputs and outputs.

No timing may start until root grants the coordinated quiet benchmark window;
concurrent M0/M6 proofs currently make this a semantic/static-only stage.
A smaller worker or fewer entry branches is not a speed result. Promotion
requires a candidate/baseline geometric mean <=0.97 over all registered forced
full-product sizes n>24, and every registered cell median <=1.05 of baseline,
in each of the two independent runs. All 86 cell ratios are retained, including
unchanged square controls; failure of either criterion leaves the candidate an
experiment/no-go. Universal GMP parity, solver performance, composed bit-cost
and peak-space theorems are not established by this local change.
