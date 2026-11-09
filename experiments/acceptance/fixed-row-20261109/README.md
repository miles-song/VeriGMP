# Fixed-row public acceptance evidence

Status: `measured/go_pending_final_independent_acceptance`. GMP parity and solver backend substitution are both **false**. Root owns the final combined independent feature review and acceptance decision.

Arithmetic source is `d12759a022d2e285d0bc6b5869ccfb5c1d85f665`, native tree `5790ad2fbadc9877332124c6a66ae3b70b016d03`. The baseline public source is `a32f84f1825e8c95bbf35f81fd6a3aad6e666f91`, native tree `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`. Its retained collector summary names another commit with those same native bytes; the original summary remains unchanged.

`index.json` maps every ZIP member to its exact original byte length, SHA256 and original path. `retained-evidence.zip` contains the original raw observations, frozen plans, pre/postflight reports, canonical loader manifests, host/window/resume receipts, actual driver/wrapper/watchdog, public arithmetic inputs and harnesses, runner binaries, proof logs and source snapshots, and candidate/baseline rlib/vir pairs. Readable audit results are in `audit-result.json`; top-level file hashes are in `artifact-seal.json`.

| Phase | Cells | Raw observations | Principal GM new/old | Worst cell new/old | Minimum batch |
| --- | ---: | ---: | ---: | ---: | ---: |
| principal/leaves run1 | 26 | 728 | 0.925632747 | 1.029152507 | 35.754047 ms |
| boundaries run1 | 36 | 1008 | — | 1.020433344 | 27.659370 ms |
| principal/leaves run2 | 26 | 728 | 0.917712314 | 1.019035930 | 36.892222 ms |
| boundaries run2 | 36 | 1008 | — | 1.027441675 | 30.084902 ms |

All 3,472 observations are retained. Each cell has seven ABBA/BAAB blocks and fourteen observations per arm; the second run reverses the initial orientation. The eight principal cells cover 1024/4096 limbs, random/max patterns, multiplication/square. Eighteen forced leaf cells cover 14–16, 19–24 limbs and random/max patterns. The 36 boundary cells cover multiplication/square at 63–65, 127–129, 191–193, 511–513, 1023–1025 and 4095–4097 limbs. Counts and order are fixed in the original plans. CPU8, `PATH=/usr/bin:/bin`, `LANG=C`, `LC_ALL=C` apply. The predeclared gates are principal GM ≤0.97, every declared cell ≤1.03, and every batch ≥10 ms; all four retained phases satisfy them.

Run the portable auditor from the repository root with Python 3 and its standard library:

```text
python -B experiments/acceptance/fixed-row-20261109/audit.py
```

It reads retained bytes only. It verifies member hashes, actual fixed cell/count/order schedules, checksums, fourteen observations per arm, raw medians and geometric means, minimum batch durations, complete postflight tool keys, canonical linkage equality, source/proof-pair bindings, nonoverlapping observed windows, resume success and positive emulator CPU advance. It also checks the mutation supplement against original raw diagnostics and mutated source bytes. It never runs any retained executable, proof tool or benchmark. Its SHA checks establish agreement with this committed manifest; they are not an external signature.

The primary `candidate/full-r05-toolbound` receipt records strict full-library **371 verified, 0 errors**, optimized compilation and paired export, 58 native source hashes, 111 contemporaneous tool hashes, explicit environment, and equal resolved compiler/sysroot observations before/after with Rust 1.99.1. Candidate pair SHA256 values are `2d533b2038d572b6ab7d79295dec53143f7b7a5cde654ca5763f3695c6aec7c8` (rlib) and `a53e2cfa19826103656eafcb0ff97bf0d4928e6fd3ffcc90f5eba5511d708d18` (vir). Baseline proof is 358/0, paired rlib `174a7e55056b622cee5a9974d353532867ceea809ec6cd11ac43a39136acb36f` and vir `99dacd6bb1535d651339c859d9853558499e4555a65104a0ec79987f51c055d6`.

Historical `full-r04` keeps its original 54-tool map and missing environment/resolved Rust binding qualification. Later r05 evidence does not upgrade r04 provenance. Early fixed-r01/r02/r03 proof receipts/logs and both rejected measurement plans r00/r01 are retained. Both measurement rejections occurred before acceptance sampling and record **zero samples**.

The local gate supplement reports four genuine **fixed_row module** semantic VC rejections, each 12 verified/1 error: omitted accumulator, wrong initial carry, wrong first-row carry store, and wrong added-row carry store. The original classifier recorded the last two as `not_detected` because it omitted `requires not satisfied`; those original records and the failed five-attempt group remain unchanged. The fifth `dispatch-omit15` attempt contains a failed postcondition plus a resource-limit diagnostic and remains **unaccepted**. This is no full-library mutation-verification claim. The separate public gate package is `experiments/fixed-row-20261109/`; retained local receipts preserve its runtime, imported-consumer and codegen qualifications.

Original static review, provenance addendum, measurement prescreen, and completed-performance review plus its recalculation script/results are retained unchanged. The completed-performance review accepts the declared performance evidence; it does not substitute for final combined feature acceptance. Independent Astra Max was requested, and the retained reviews disclose that runtime identity is unexposed.

All four observed Windows windows were below 120 seconds (80.9681, 105.2242, 72.2968, 103.6700 seconds), with normal finally resume status zero and positive subsequent CPU advance. The actual wrapper has a 120-second owned-command timeout and a 140-second independent resume watchdog. These are retained observations and software mechanisms; no hard real-time deadline guarantee is inferred.

Only public VeriGMP arithmetic material and measurement/provenance metadata are included. VeriCount-named dependency paths remain metadata; private solver sources and M3 data are excluded. Tool binaries and shared dependencies are omitted, while their recorded identity maps remain. This archive audit does not rerun or independently re-establish proof, runtime correctness, cost bounds, universal GMP parity, or backend acceptance.
