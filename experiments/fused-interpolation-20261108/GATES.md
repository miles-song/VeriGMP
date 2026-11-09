# Source-ready gate entry points

本目录冻结 source 与可执行 test inputs。`cb9f268` 的 focused frontend/type/helper
gate 已通过37/0 partial verification；完整 native proof、optimized compilation、
native oracle、mutant proof、codegen 与 timing 尚未完成。所有后续命令在 root 分配
的 resource slot 内运行，stdout/stderr 必须完整落盘并绑定 source/tool hashes。
所有后续 Verus invocation 必须显式传入 `--num-threads 2`。

`preflight.py --output <fresh-external-directory> --require-clean` 只运行 Python、
read-only Git 与 fixture 生成。输出包含完整 source/native/input
manifests、`core.diff`、4,036 个 fixture、602 个 harness order fixtures 的检查结果、
15 个 primary / 71 个 control 的 analytic interpolation schedule、严格 classifier self-check
及 raw validator 的 synthetic adversarial checks，不执行 benchmark。
oracle fixture 定义与 runtime operations 为：

| op | 输入意义与结果 |
| --- | --- |
| 0 | `dst - (rhs << shift)`；shift 1/4，完整非负 integer difference |
| 1 | 五个独立非负系数生成 evaluation inputs，恢复 c1/c2/c3 |
| 2 | actual default `arithmetic::mul_mod`，含合法 shared immutable input |
| 3 | actual default `arithmetic::square_mod` |
| 4 | forced `toom_multiply::full`，threshold 24 |
| 5 | forced `toom_square::full`，threshold 24 |
| 6 | unchanged `fast_multiply::full` control，threshold 24 |

heavy gate 的顺序固定如下：

1. 用 source-ready HEAD 的 Git blobs 建立 external snapshot。读取固定
   `native/toolchain.json`，核对 Verus archive、解包的 executables/vstd 与 Rust/LLVM
   hashes。baseline producer 必须绑定 native tree `72dc8a5d...`、358-item 完整
   summary、相同 tool hashes 和 exact rlib/vir；核对其完整原 proof logs。
2. source 冻结且获得 root 的 resource slot 后，优先以 `--verify-module toom_words
   --num-threads 2 --no-cheating` 运行不带 compile 的 focused frontend/type/helper
   gate；type/parse failure 不能被计作 proof failure 或 mutant detection。
   不使用 unchecked verification flags，不将 focused gate 当作完整库证明。
   然后对 candidate snapshot 的 `native/lib.rs` 使用以下 flags 完整验证并优化编译，
   不使用 module filtering：`--crate-name verigmp --crate-type lib --no-cheating
   --compile -O --num-threads 2 --export <candidate>/verigmp.vir -o <candidate>/libverigmp.rlib`。
   CPU set 由 root 的 resource slot 明确给定。
   记录唯一完整 `verification results:: N verified, 0 errors` 和所有输出。
3. 对两个 producer 分别以 `--no-cheating --compile -O --num-threads 2 --crate-type lib
   --crate-name fused_bridge --extern verigmp=<producer>/libverigmp.rlib
   --import verigmp=<producer>/verigmp.vir -L dependency=<producer>` 编译并验证
   同一份 `bridge.rs`。输出 `libfused_bridge.rlib`。其 coefficients 的 Ghost meaning
   从 c0..c4 输入切片定义，不从 interpolation 结果定义。
4. 用 pinned Rust 编译同一份 `runtime.rs`：`-O --edition=2024
   -L dependency=<verus-runtime> -L dependency=<producer>
   --extern verigmp=<producer>/libverigmp.rlib
   --extern fused_bridge=<bridge>/libfused_bridge.rlib`。
   baseline 额外使用 `--cfg baseline`，仅让 direct-helper test 调用原 pipeline；
   所有真实 interpolation/default/full 调用仍使用对应 producer。
   对两个 binary 执行同一份 `oracle/cases.bin`。GMP FFI 只在 unverified runner。
5. 编译 negative Rust ownership fixtures，精确检查 E0502（dst/rhs）与 E0499
   （p1/pm 或 p1/scratch）。构造 verified negative client modules，让无 underflow
   保证或 shifted RHS 超过 capacity 的输入调用新 helper，要求严格 precondition VC
   rejection。不能将 contract violation 宣称成原来不存在的 runtime error。
6. 用 `mutations.prepare(frozen_native,fresh_external_directory)` 生成四个独立
   mutant snapshots。逐个使用 `mutants.json` 的 flags（显式 `--num-threads 2`）；
   调用 `packed-convolution/verus_logs.strict_semantic_rejection`
   分类完整 logs。positive full build 必须先成功。无 timeout/parse/type/load/rlimit
   fault 才能计为逻辑检测；保留每个 mutant 的源 hash、完整日志与退出码。
7. 核对两方 codegen flags。用 `ar t` / `ar p` 从精确 rlib 提取完整 object；
   如果不是单个 object，停下并适配完整多 object audit，不能只挑一个。
   `combination-20261108/codegen.py` 可比较完整 sections/relocations/disassembly，
   其 source hash 已纳入 preflight。额外按 PROTOCOL.md 完成 actual default callgraph、
   最终 executable layout、71 个 controls 的逐项 identity 与 proof-erasure audit。
   不能把报告中的 boolean 从 source equality 推测出来。
8. 以相同 pinned `-O --edition=2024` flags 与各自 rlib 编译原始
   `arithmetic-precondition-checks-20261108/bench.rs`。在 timing 外保存 ldd、GMP ABI、
   linked library hashes、所有工具与 host identity，生成兼容原 `measure.py` 的
   `bench-build.json` 和 `identity_receipt`，严格使用 [RAW_FORMAT.md](RAW_FORMAT.md)
   的 schema、source/tool/producer/log artifact references 和 exact compile argv。
   `key_shapes` 保持原26 shapes。此时仍不执行 benchmark binary。
9. 通过 independent Astra Max 审查、root 最终 protocol 审核并冻结所有 gate logs、
   inputs、tools、exports、binaries、control identity 和 host checks 后，才允许在
   quiet window 中执行原始 `measure.py` 两次；每次必须完整 86 cells。
   `summarize.py --run1 <folder> --run2 <folder> --build <frozen-build.json>
   --build-sha256 <root/independent-frozen-digest> --output <fresh-report.json>`
   重算 raw medians、15-cell primary geometric mean、86-cell worst regression 和
   跨 run baseline drift；不运行或重试 measurement，也不合并两次 run 的判据。

`source_ready` 只表示当前源码与上述 prospective gates 可供独立审查，未赋予任何
`impl_refined`、runtime correctness、measured improvement 或 GMP parity 状态。
