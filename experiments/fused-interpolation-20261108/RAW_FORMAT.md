# Frozen raw validation contract

`raw_validate.py` 和 `summarize.py` 只读取 evidence，不执行、补跑或 retry benchmark。
原始 `arithmetic-precondition-checks-20261108/bench.rs` 与 `measure.py` 不变。
`test_raw_validate.py` 只生成 synthetic JSON；其通过不能代替 native correctness、
optimized compilation、codegen、independent review 或 timing。

`summarize.py` 必须同时取得两个 run 目录、外部冻结的 build 与 root/independent
pre-timing receipt 登记的 digest：

```sh
python3 experiments/fused-interpolation-20261108/summarize.py \
  --run1 <complete-run-1> --run2 <complete-run-2> \
  --build <frozen-bench-build.json> --build-sha256 <independently-frozen-sha256> \
  --output <fresh-adjudication.json>
```

两个 `measurement.json` 内嵌的 build 必须等于此外部文件，`build_sha256` 必须等于
外部登记 digest。仅让两个内嵌 metadata 彼此相等不够。所有被引用的 artifact 使用
`{"path":"<absolute Linux path>","sha256":"<64 lowercase hex>"}`，validator
重新读取并核对每个 artifact。不能用事后生成的新 metadata 为不同 binary 背书。

`bench-build.json` 的 schema 为 `fused-interpolation-bench-build-v1`；必需字段为
`status="static_pass"`、`seed=20261108`、`cell_count=86`、`key_shapes`（原26 shapes，
固定顺序）、`source_head`、`source_tree`、`identity_receipt` 和 `binaries`。
`binaries.baseline/candidate` 各含 `path`、`sha256`、`library_sha256`、`gmp_path`、
`gmp_sha256`、`argv` 和 `build_command`。`build_command` 含 `argv`、`returncode=0`、
`stdout` 与 `stderr` artifact references。两个 executable 使用同一 GMP hash。

identity receipt 的 schema 为 `fused-interpolation-identity-v1`，`status="static_pass"`。
它包含以下固定结构：

- `sources.baseline/candidate`：`head`、`tree`、`root`、`native_tree`、
  `native_manifest_sha256` 与完整 `files`。`files` 的 key 为 `native/...`，value 为
  artifact reference，路径必须等于 `root/key`。validator 从实际 bytes 重算 Git
  blob/tree SHA-1 与 SHA-256 manifest。baseline native tree 固定 `72dc8a5d...`，
  candidate native tree 固定 `212dd5d0...`，不从 measurement 输出定义来源。
- `tools`：Verus、rust_verify、Z3、vstd、builtin/macro、pinned archive、Rustup、Rustc、
  LLVM、rustc_driver、Python、Git、ar、objdump、objcopy 的 artifact references。
  完整 labels 由 `raw_validate.PROOF_TOOLS` 和 `validate_build` 的 required set 定义。
  当前工具 hashes 必须匹配既有 baseline receipt；archive 必须匹配 native pin。
- `inputs`：所有 experiment inputs 的 repository-relative name 到 artifact reference
  的映射；至少包含原 bench/measure、本 validator、summarizer 和 PROTOCOL。执行中的
  validator/summarizer/PROTOCOL bytes 必须匹配冻结 inputs。
- `producers.baseline/candidate`：`native_tree`、`native_manifest_sha256`、
  `tools_sha256`（仅 `PROOF_TOOLS`）、`receipt`、`rlib`、`vir`、`verified_items` 和
  `proof`。`proof` 含实际 `argv`、`cwd`、`returncode`、完整 stdout/stderr artifact。
  两个 proof 都必须具有唯一完整的零 error summary；focused summary 不合格。
  baseline 固定到已接受的 358-item receipt SHA-256
  `e64a33d921810b456e343de139ccff96b4be484adc93e0cf642229fbc3568fe8`，
  并逐项核对其实际 Rust/tool/export/原命令/原 logs；不重新证明 baseline。
  candidate 必须精确使用当前 snapshot 与 pinned tool 的完整 proof argv，包含
  `--no-cheating --compile -O --num-threads 2`，并导出对应 rlib/vir。
- `gate_receipts`：`correctness`、`semantic_mutants`、`domain_alias_capacity`、
  `control_identity`、`host` 的完整 receipt artifacts。hash binding 不代替 reviewer
  对这些 gate 结论的检查；timing 仍需 Astra 明确 READY 与 root quiet-window grant。

candidate complete proof argv 的顺序固定为：Verus、`native/lib.rs`（或该 snapshot
的 absolute path）、`--crate-type lib --crate-name verigmp --no-cheating --compile -O
--num-threads 2 --export <vir> -o <rlib>`。两方 bench compile argv 固定为：
Rustup、`run 1.99.1-x86_64-unknown-linux-gnu rustc <bench.rs> -O --edition=2024
-L dependency=<verus directory> -L dependency=<producer directory>
--extern verigmp=<rlib> -o <binary>`。完整 build stdout/stderr 保留。

raw 的验证为有序状态机。固定34 forced-full cells，然后原26 default mul cells，
再26 default square cells。每 cell 先 baseline/candidate/GMP 三次 calibration，再
按原 `sample_paths` 顺序消费七轮。GMP 使用 baseline executable。每条 invocation
argv 必须精确等于冻结 binary、cell、seed、GMP selector、当前 count、`registered`。
每条 outcome 的 stdout/stderr text 必须等于相应 hex bytes 的既有 decode 语义；
stdout 严格 UTF-8 JSON 只能含 `iterations/ns/checksum/calibration`，必须逐字段等于
result。拒绝重复 JSON key、NaN、非整数 count/duration/checksum 与失败/timeout。

calibration argv count 为零，ladder 从1逐次 doubling；之前 steps 的 duration 必须
小于20ms，最后一步必须达到20ms且精确等于返回 iterations/ns。非 calibration 的
ladder 必须为空，iterations 必须等于 requested count。样本小于10ms时，只允许
同 cell/path/repetition 紧邻一次或多次 count doubling retry；达到10ms后不许继续
retry，增加后的 count 延续至后续 repetition。所有 calibration、短样本与 retries
的 checksum 也必须与该 cell 的所有 accepted paths/GMP 一致。

每个完整 run 必须恰有258 calibrations、1,806 accepted samples和所有 retained
retries；不能有剩余、重复、缺失或重排 records。validator 从 accepted raw values
重算七样本 median、candidate/baseline 与 candidate/GMP ratios，再逐字段检查
原 summaries，最后分别计算每个 run 的15-cell GM、86-cell worst 和跨 run drift。
不能让报告内自填的 median、ratio 或 verdict 替代 raw 重算。
