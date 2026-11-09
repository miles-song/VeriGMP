# Fused interpolation：untimed static gates

当前状态为 **完整 native proof 与 functional/static gates 通过；independent review
与 timing eligibility 待定**。没有执行 candidate benchmark，包括 calibration；本包
不提供 measured improvement、GO 或 GMP parity 结论。main baseline 和 W1/W2 NO-GO
保持有效。

arithmetic source 为 `3a836713adbb0a6632f5131e8d57c97296d22f62`，commit tree
`96bd28b9bc45702e1d7f6c8e9a60d7653f2cd941`，native tree
`212dd5d00d4b2159abd4627a6aaec8b16a1157e5`，native manifest SHA-256
`d9d91876478ba6c8bcc9324a05a3bd303c1d2c4d9becd620d256a32ce3ddf72b`。
native diff 仍只有 `toom_words.rs` 与 `toom_interpolate.rs`；既有 API/scratch domain、
threshold/split/default dispatch 未改变。

完整 candidate 使用 pinned Verus/Rust、`--no-cheating --compile -O --num-threads 2`，
唯一完整 summary 为 **369 verified、0 errors**，returncode 0、stderr empty、无 timeout。
该 scope 与先前37/0 focused partial gate 分开。baseline 358-item producer 逐项绑定
同源、同 tool、同 rlib/vir 与原 full-proof logs 后复用，没有重证 baseline。

两个 optimized producers 各通过4,036个独立 Python arbitrary-integer fixtures，
GMP 额外检查完整或 truncated result。coverage 包含 direct helper、independent
coefficient interpolation、actual default/forced mul/square、capacity/canaries、
nonzero 初值、input preservation、合法 immutable/disjoint aliases 和 pre-write panic
boundaries。3个重叠 borrow fixture 精确产生 E0502/E0499/E0499；2个 verified negative
clients 产生严格 precondition VC rejection。wrong-shift、lost-shift-carry、lost-borrow
与 zero-scalar-shift-carry 四个 mutants 均满足 strict semantic rejection，完整 logs
中没有把 parse/type/load/timeout/rlimit/unknown 当成功。

library 完整 function sections 为156→157。interpolate 为1679→1215 bytes；
unchanged-source Toom callers 也发生 compiler context 变化：toom_multiply::full
2640→2672、toom_square::full 2299→2286，bytes 和 normalized relocations 均不同。
新增 `shift_factor` 是26-byte cold spec panic stub：没有 library incoming reference，
不可从两个 actual default arithmetic roots 到达，最终 benchmark executable 中已无
该 symbol。实际 interpolation body 中两个 fused helpers 被 inline，旧 copy/scale
pipeline 调用消失，未出现 allocation/FFI/spec-integer materialization。原 divide by2/3
等其他运算保留。

control identity 逐 cell 保留完整 library footprint、body/relocation comparison 和最终
symbol addresses/sizes/alignment/raw bodies。按 source dispatch 排除不活跃入口分支
后，61/71 controls 的完整 library bodies 与 normalized relocations 相同；另外10个
default square controls（65、127、128、129、191、192、193、255、256、257，top63）
会进入改变的 Toom full caller，即使它们没有 interpolation visits，也不能宣称其
whole-function footprint byte-identical。footprint 对内部 data-dependent branches
作保守 overapproximation，没有 executed-instruction trace 的主张。最终 executable
raw bodies 与 absolute layout identity 对71 controls 均为 false；完整 `.text`、symbols、
readelf、relocations 与 disassembly 已保留。不能把未来差异全部归因于4L loop visits。

`codegen-01` 的 ELF stdout 展示 decode failure、`codegen-02` 尾部 metadata import
failure、`codegen-03` 对 stub 形式的错误断言，以及 `codegen-04` 的保守初版 metadata
均完整保留。canonical `codegen-05` 只从既有完整 codegen 和冻结 preflight schedule
整理 metadata，没有重编译或调整 native inline/padding。完整 proof/correctness 没有
因 metadata 修复而重跑。

`receipts` 下是 canonical JSON 的逐字节副本。`evidence.zip` 保留943个 source、
driver、完整 commands/logs、rlib/vir、objects、fixtures、失败 attempts 与 codegen
artifacts；`manifest.json` 为每个 entry 记录 size/SHA-256。所有 static binding 均由
真实 assets 重新检查。两个 benchmark binary 只完成编译，没有执行。

| Canonical artifact（archive-relative） | SHA-256 |
| --- | --- |
| `full-native.json` | `e73252c3da01bb60f05db5753a4815f0470d2796da558f93229567698964329b` |
| `untimed-01/verification.json` | `dc43436ff9a7bb487125639bcc5c3a71d13c08ab79cf17c6a3b0b9f6807eb278` |
| `codegen-05/verification.json` | `63fd8dedcafcbff4daefdad61940d0a09fb0925ddc1e1a9ce59a27ad61447603` |
| `codegen-05/control-identity.json` | `22b4a942cbb1fd89bb70daf54b3d642ec36dd305dab7436024fe077fddf59630` |
| `build-identity-01/bench-build.json` | `bac446bdf52f2a9ce6babb653019427d3f65ec36c90de68b5a8459ae945a62c4` |
| `build-identity-01/identity.json` | `2ef03539dfb28375a6de5ff09a7fad03245fcc9cd5c26447d775a73900c5ff01` |
| `build-identity-01/verification.json` | `43e8589a9a8b62f8befdb6c92f5b88e450d587c14638ef44ef4b7a20d2c8dffb` |
| `evidence.zip`（22,552,926 bytes） | `77116e0a56509aa4b09c238733e6ad41af0b023b01ceb2c56ac5c7ee7463416f` |

timing 仍须同一 independent Astra 明确 READY、root 接受已披露的 caller/layout
differences，并授予 bounded quiet window。原86 cells、两次独立完整 run、每 run
primary15 GM<=0.98、all86 worst<=1.05 和 baseline drift criteria 均保持登记值。
