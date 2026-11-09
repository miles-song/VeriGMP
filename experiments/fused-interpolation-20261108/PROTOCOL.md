# Fused shifted subtraction：source-ready protocol

本候选从 commit `4510b46e4010dd287c9cf760f0195f2edc32e1f7`、
tree `d8bb9a0f95160a2e260f7b9f276cb4fd0a867778` 建立。
baseline native tree 为 `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`，
继续复用其经 source/tool/export identity 核对的 358-item producer。
W1/W2 的历史 NO-GO 保持有效；本候选不包含两者。

## 唯一实现变化与输入意义

`toom_interpolate::interpolate` 的两个
`copy_pad -> scale_exact -> sub_exact` pipeline 分别替换为
`sub_shifted_exact(p2,z4,4)` 与 `sub_shifted_exact(p2,pm,1)`。
`sub_exact(p2,z0)`、所有其他运算、调用顺序、递归、threshold、split、mask、
default dispatch、所有既有 API 与 scratch domain 均保持原样。
`scratch` 参数及其原有长度检查保留。

令 `B=2^64`，`V(a)=sum(a[i]*B^i)`，`f(1)=2`、`f(4)=16`。
helper 的契约是：`shift` 为 1 或 4，`len(dst)>=len(rhs)`，
`V(old dst)>=f(shift)*V(rhs)`，则 `V(new dst)=V(old dst)-f(shift)*V(rhs)`，
切片长度不变。`V(old dst)<B^len(dst)` 由表示得出，因此前提同时保证
shifted RHS 可装入 destination，且数学差非负。输入切片不变；没有额外数值 domain。
空切片、隐式 high zeros、等长或较短 RHS 均在定义域内。

每次迭代使用 `shift_word` 的关系
`shifted+B*next_carry=f(shift)*rhs_word+carry`，并复用已验证的
`fast_words::sub_word`：`low-B*next_borrow=dst_word-shifted-borrow`。
独立的 loop invariant 为
`prefix(dst,i)-B^i*(borrow+carry)=prefix(old dst,i)-f(shift)*extended(rhs,i)`。
`carry<f(shift)`、`borrow<=1` 和未写 suffix 的 frame 一并保持。
结束时利用输出范围与非负精确差推出两个 scalar 均为零。
这些关系只依赖输入整数，不以 executable output 定义期望结果。

runtime 是单个正向 limb loop，使用 borrowed slices 和 O(1) scalar scratch。
shift、OR、borrow 操作之外的整数模型与 proof block 均须擦除。
不允许为 proof 增加 runtime passes、bigint、allocation、copy 或其他算法。

## 先于 timing 的验收

source `cb9f26860accdfb3471e5e668b42a6a732da3608` 的 focused frontend/type/helper
gate 为37 verified、0 errors，属于 `--verify-module toom_words` partial verification。
完整 native proof、optimized build、runtime oracle、mutants 与 codegen 仍按下列顺序
在 root 的 resource slot 内验收；focused gate 不赋予 `impl_refined` 或性能状态。
root 的 independent Astra Max prereview 与最终 performance protocol 审核完成前不得
开始 timing。所有后续 Verus invocation 均显式指定 `--num-threads 2`。

1. 冻结 clean source HEAD/tree、全部 native files、experiment inputs、
   baseline/candidate native manifests、diff 及其 SHA-256。检查 native diff
   只涉及 `toom_words.rs` 和 `toom_interpolate.rs`，其余 native bytes 与 baseline
   相同，既有函数契约不变。完整保存 stdout/stderr、退出码、实际命令与时间戳。
2. pinned Verus `0.2026.10.26.d17fbd0` / Rust `1.99.1`：
   完整 candidate `native/lib.rs --no-cheating --compile -O`，导出匹配的
   `libverigmp.rlib` 与 `verigmp.vir`。不 hardcode 验证条目数；记录实际完整 summary。
   固定 archive、verus、rust_verify、Z3、vstd、Rust、LLVM 和 GMP 动态库 hashes。
   对 baseline 重用的 358-item producer 逐项核对源字节、tool hashes、rlib/vir hashes。
3. 将同一个 candidate rlib/vir 用于 direct helper、verified interpolation bridge、
   full/forced/default multiplication 与 square 的 optimized runtime runner。
   independent Python arbitrary integers 产生完整输入和期望值，GMP 仅作额外 control。
   两个 producer 执行同一批 fixture。保留完整输出、fixture/binary hashes、canaries、
   nonzero initial output/scratch、只读输入不变、exact/extra workspace 的结果。
4. helper 覆盖 shifts 1/4、empty、RHS 0/短/等长、shift carry 1..15、等式边界、
   high-word capacity 边界、长 borrow chains、carry 与 borrow 同时存在；
   interpolation 覆盖 `negative` 两支、zero signed evaluation、系数容量边界、
   短/空 z0/z4。full/default 覆盖所有 registered shapes、递归边界、n mod 3、
   input alias `a==b` 及 top 1..64。调用必须保留原有 scratch capacity。
5. error/domain/alias gates：unsupported shift 和 RHS 太长在 helper 写入前 panic；
   interpolation 原有所有 length/scratch 边界在写入前 panic；
   数值 underflow 与 shifted overflow 是 contract violation，以 negative verified
   client 验证 precondition 拒绝，不将其误报为原 API 的 runtime error。
   Rust ownership 拒绝 dst/rhs、p1/pm/scratch 的可写重叠；合法同 allocation 的
   disjoint slices 与重复 immutable inputs 须执行通过。workspace query 覆盖
   0、1、MAX/12、MAX/12+1、MAX/10、MAX/10+1、MAX。
6. strict semantic mutants 在独立 snapshot 内运行，保留完整逻辑 VC summary：
   wrong-shift：首个 call 的 4 改为 1；lost-shift-carry：`carry=next_carry` 改为 0；
   lost-borrow：`borrow=next_borrow` 改为 0。额外 scalar carry mutant 将 `high` 改为 0。
   用现有 `packed-convolution/verus_logs.py` classifier，要求唯一 partial summary、
   returncode 1、正数逻辑 VC errors 和精确 module note。timeout、rlimit、unknown、
   parse/type/load/tool error 均不算检测成功；先执行 classifier self-check。
7. 两个 producer 用匹配的 compiler/codegen flags 输出完整 object/assembly。
   保存完整 symbol sections、bytes、relocations 和 disassembly，不使用截断文本。
   检查 actual default roots `arithmetic::mul_mod` / `square_mod` 到 interpolation 的
   callgraph，确认 fused helper 在需要的路径 inline，原两个 scratch pipeline 消失，
   shift 为常量 1/4，proof 无 runtime 对象，无新增 allocation/FFI/division/extra pass。
   保留现有除 2/3 与其他调用；并不声称全库无 division。
   below-Toom controls 的执行 codegen identity 需核对，若 compiler 引起非局部差异，
   必须完整报告后再由 root 决定是否允许 timing。

全部 positive/negative gates、baseline/candidate/tool identities、完整 logs 与
codegen evidence 在第一次 calibration 前冻结。source 或 harness 如需修改，
重做受影响 gates 并产生新 source identity；保留先前 evidence。

## Analytic mechanism

令单次 interpolation 的 slice length 为 L。每条旧 pipeline 的 copy、scale、sub
各访问 L 个 destination positions，共 3L loop visits；新 helper 为 L。
两处合计从 6L 减为 2L，删除 4L loop visits、4L scratch stores 和 4L scratch reads。
新 helper 直接读取 RHS，每 limb 保存 destination；额外 runtime storage 为 O(1)。
scratch API 与 allocation budget 不缩小。这里是 source-level analytic operation count，
不是 checked cost theorem、动态 instruction count 或 measured speedup。

## Prospective performance protocol（等待 root 最终审核）

历史 [all-cell-ratios.csv](../acceptance/arithmetic-negative-20261108/all-cell-ratios.csv)
中，W1 square 2048 的 candidate/baseline 为 `0.9358223093 -> 1.0096072756`，
W2 square 1024 的 both/baseline 为 `0.9698891578 -> 1.0306073850`。
这些 sign reversals 要求独立判定两次 run，并检查 control identity 与 host drift；
不能仅以某个尺寸或一次 run 的收益作结论，也不能据此放宽本候选的预登记 thresholds。

复用已登记的 `arithmetic-precondition-checks-20261108/bench.rs` 与 `measure.py`
原始 86-cell harness，seed `20261108`，相同输入、compiler flags、preallocated buffers
和结果语义。34 个 forced `fast_multiply::full(threshold=24)` cells 加上
`native/performance-target.json` 的 26 个 default mul、26 个 default square cells。
所有 original shapes、below-Toom controls 和 GMP path 保留；不做 threshold tuning。

primary set 固定为 top=63 的 15 个实际执行 Toom interpolation 的 cells：

- default mul：512、513、1023、1024、1025、2048、4096。
- default square：511、512、513、1023、1024、1025、2048、4096。

baseline/candidate/GMP 每 cell interleave；baseline/candidate 次序随 repetition
交替，GMP 位置按原 harness 轮换。每 path 独立 calibration，七个 repetition，
每个 accepted arithmetic sample 至少 10ms，calibration 与短样本 retry 全部保留。
计时外验证完整结果；`black_box` 保护 runtime inputs/outputs。沿用原 GMP public
mpn full product/square，再作必要 low-half copy/mask。allocation 与 fixture setup
在 timing 外；不更改两方 allocation boundaries。

原 harness 每次 invocation 都启动一个独立 process，baseline/candidate/GMP 没有放在
同一 process 内交错。每个 process 重新生成同一 fixture，在 timing 前后核对 GMP
答案；calibration process 用 doubling ladder 达到 20ms，之后每个 sample process
使用已登记 iterations，低于 10ms 时保留短样本并按原规则 doubling retry。
每 cell 三个 calibration process，七轮各三个 accepted sample process；每个完整 run
固定 258 calibrations 和 1,806 accepted samples，加上所有 retained retries。
固定 cell 次序沿用原 harness，两个 run 均不按第一轮结果调整次序。

raw validation 采用 [RAW_FORMAT.md](RAW_FORMAT.md) 的固定状态机与外部冻结 receipt。
`stdout_hex` 必须严格解码并逐字段等于 result 的 iterations/ns/checksum/calibration；
每次 argv 绑定 frozen binary、cell/seed/GMP selector 与 calibration/retry count。
validator 精确消费原86-cell顺序、258 calibrations、1,806 accepted samples和所有
短样本 retries，重算全部 medians/ratios/gates。`summarize.py` 必须接收外部 `--build`
及 root/independent pre-timing receipt 登记的 `--build-sha256`，核对 source/tool/
producer/rlib/vir/GMP/binary/完整 gate logs；不能只比较两个 run 自填的 metadata。
synthetic validator 自检不执行 benchmark，不构成 timing 或性能证据。

timing eligibility 要先冻结 `control-identity.json`：列出两个完整 library object 与
两个最终 executable 的所有 arithmetic symbol sections、alignment、addresses、sizes、
raw bytes、normalized relocations、callgraph 和最终 `.text` layout hashes。
对 71 个 analytic schedule 不执行 interpolation 的 control cells，逐项列出其到达的
arithmetic bodies，明确报告 body identity、relocation identity、layout identity 的
true/false，不能因 source 相同就填 true。interpolation 的预期变化单列。
如 control arithmetic body/relocation 有非预期差异，先停在 untimed gate；完整记录后
由 root 与 independent reviewer 在 timing 前裁决。即使 bodies 相同，非相同的
最终 code layout 仍须披露，不能把所有差异归因于 loop visits。

host 与 baseline validation 的预登记 proposal 为：沿用 CPU 8（不可用时需在首次
calibration 前由 root 另行冻结 CPU），read-only 记录 host/WSL/kernel/CPU topology、
SMT siblings、affinity、governor、frequency/thermal observations、`/proc/stat`、
`/proc/loadavg` 以及 Windows host 的 process/CPU observations。root 协调整个 quiet
window；期间不得并行 proof、build 或其他 benchmark，不修改系统 power/security
settings。run 1 与 run 2 分别独立启动 measurement process；每次前后重验
source/binary/tool/GMP hashes 和 affinity。两个完整 run 合计 quiet window 上限为
480 秒；达到上限即停止并保留已收集 evidence，不自动延长或启动替代 run。

baseline 校验先要求 358-item producer 的精确 source/tool/export 绑定，以及所有
86 cells 的完整 Python/GMP correctness。两次 run 之间，71 个 control cells 的
baseline median `run2/run1` geometric mean 须在 `[0.95,1.05]`，每个 control 的
ratio 须在 `[0.90,1.10]`；同时记录 baseline/GMP drift，不以其取代固定判断。
超过范围则标注 `baseline_drift`，performance ratios 和所有失败照常保留，但本次
因果性能结论不可晋升。binary/tool/GMP/source/affinity 变化、预登记 window 超时、
校验失败、measurement process error 或已记录的并发重负载属于 infrastructure
failure。frequency/thermal/load observations 本身只作证据，不在看到 candidate
结果后发明新的异常排除规则。不能因 candidate ratio 不理想而将 run 标作 invalid。

固定同一 CPU affinity、同机 quiet window、相同冻结 binary hashes，执行两个完整且
独立的 run。两个 run 都独立计算每 cell 的七样本 median 和 candidate/baseline ratio。
每个 run 都须满足：primary 15-cell geometric mean `<=0.98`，全部 86 cells
最差 median ratio `<=1.05`。GMP ratios 完整报告，但不参与本候选增益判定。
不能将两次 run 的中位数或 ratio 先合并再绕过其中一次失败。

任一 criterion 失败则保留 NO-GO experiment，candidate 不启用；不按结果删 cells、
修改 source/threshold、调参数或补跑挑选更好 outcomes。只有预先定义并完整记录的
基础设施故障可交由 root 判断 run 是否 invalid；保留所有原始 outcomes，且不自动
补跑。新的 measurement 必须单独登记并保留本次记录；两个 run 不能合并取代各自 gates。
结论仅覆盖这台机器、这些输入与冻结构建，不推断 universal GMP parity 或 solver parity。
