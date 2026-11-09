**VeriGMP fundamental optimization design — 2026-11-09**

**Decision**

原主 agent 现在应先实现 **bounded split-sum column multiplication leaf**：保留 radix \(B=2^{64}\)、caller-owned slices 和现有 Karatsuba/Toom recursion，在 leaf 内改为 product scanning；每个 product 的 low/high halves 分别进入两组 bounded accumulators，跨 word 的 carry 只在一个输出 column 完成时归一化。它直接改变 carry dependency 和输出写入次数，作用于大尺寸 recursion 的大量叶子。首批不改 threshold，不加 assembly，不改变 public result semantics。

这是一个可迅速证伪的实现方向，**没有本轮 timing，也没有已证明的 speedup**。Comba 与 delayed-carry accumulation 有明确 prior art；本方案不能以“新的乘法算法”或“首次 delayed carry”发表。可探索的贡献是 full-u64、exact low/full product、bounded scalar accumulator、Verus refinement 和组合性能的具体实现。其学术 novelty 仍待更完整检索与实现结果确认。若“创新性”要求新的 asymptotic bound，本方案尚不满足；不能用新名称掩盖这一点。

交付状态为 **design_only**。本轮没有执行 proof、build、oracle、calibration 或 benchmark，没有改 source、branch、receipt、服务或 emulator，也没有调用其他 agents、CLI agents 或其他聊天。下文 gate 均是原主 agent 后续要执行的工作。

**1. 已核实的边界和 identities**

| 对象 | 实际检查结果 |
|---|---|
| 权威 public checkout | E:/3sat/VeriGMP-scaled-experiments |
| HEAD / main | 7219cbd013dbf323f7121e4a9e197964f55377ca |
| native tree | 72dc8a5da2cbb7eddcdd26c219d50770e8b73b06 |
| 工作区 | 初始与交付前检查均干净；HEAD/main/native tree 未漂移 |
| remote | git@github.com:miles-song/VeriGMP.git |
| GMP algorithm reference | GMP 6.3.0，official release archive SHA-256 a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898；本地 archive 实际 hash 匹配 |
| GMP immutable source node | bc0ec1699e58；官方 raw toom33_mul.c 经 HTTP 读取，hash 与 release/pin 相同 |
| low-square candidate | 9e6b2b6e9ccf90e44ae0260ed921be79502d818e；native a4d704d1c98300cf805286d3cedbd8100d25ad6c；工作区干净 |
| cross-fusion candidate | a2f8eb971a44f7d3e6a4f9555b32a86994da490a；native 0ac6cdffb11a20505b86a75a9ad2ed8323acd971；工作区干净 |
| scoped Toom-4 candidate | 3bceade19b67e3d7140f150e594356270d0ee4b7；native 4f8fd288f3103886d4b60bcd8b3880fdef06334d；工作区干净 |

适用约束来自 E:/3sat/AGENTS.md、E:/3sat/sat-counting-lab-src/AGENTS.md、public checkout/AGENTS.md，以及安装的 karpathy-guidelines。本轮只读取父项目的指导文件，没有读取 VeriCount 私有算法源码，也没有读取旧的 E:/3sat/VeriGMP checkout。candidate 的 source 存在与文档的 static gate 声明，不等于本轮重验或 performance acceptance。

[native/performance-target.json](https://github.com/miles-song/VeriGMP/blob/7219cbd013dbf323f7121e4a9e197964f55377ca/native/performance-target.json) 的目标确为：

- 两类 principal workloads：mul_mod、square_mod；n=256/512/1024/2048/4096，top=63；每个 workload median candidate/GMP ≤1.0。
- 每个 registered key shape median ≤1.2 GMP；每 shape 七次采样、每 accepted batch ≥10 ms，第二次独立运行确认。
- comparator 是 public mpn_mul_n/mpn_sqr 的 full product 加 low-half copy 和 mask。不能改成 GMP internal mullo 来重定义既有目标。
- scoped optimization 可独立验收，不必等待整体 parity；替换 solver backend 仍需完整目标和 frozen representative exact arithmetic traces。

已保存 host receipt 显示 AMD Ryzen 7 7745HX，8 cores/16 logical processors，WSL2 Linux 6.6.87.2，单核 L1d 32 KiB、L2 1 MiB，共享 L3 32 MiB。flags 包含 bmi2/adx/avx512ifma。它们是已保存观察，不能证明当前频率、空闲程度、实际 codegen 或某次 GMP dispatch。不能因为 flags 存在就引入未验证 intrinsic/assembly。

tool pin 为 Verus 0.2026.10.26.d17fbd0、commit d17fbd0c58abf0d5e86825ea64b96aba72b1b31f；Rust 1.99.1-x86_64-unknown-linux-gnu。冻结 receipt 中 rustc SHA-256 b53b780f77f952062f8ca8a3b70aef2390b1e45ad91939be94afdc9543026853，LLVM library ed06fbed8d297efa92979aeb227a4ce5b87b1a462d0aeac66d093300fad74824，GMP libgmp.so.10.5.0 为 0ccdfb6d6f5c039465f6d002cf7e4c072d48ac6a2cffc8dd6c748dec31592804。这些来自公开 receipt；没有访问该 receipt 所列的私有工程路径。本轮没有运行工具二进制复核版本。

**2. 当前成本结构：能确定什么，不能确定什么**

[native/verified/arithmetic.rs:23](https://github.com/miles-song/VeriGMP/blob/7219cbd013dbf323f7121e4a9e197964f55377ca/native/verified/arithmetic.rs#L23)：

- mul_mod 的 n<512 调用 Karatsuba-backed low recursion，full threshold=24、low_limit=64、short fraction=11/36。
- n≥512 使用 Toom-3-backed low recursion，full threshold=192、low_limit=128、short fraction=9/40。
- square_mod 使用 full-square threshold=192、low_limit=64、short fraction=11/36；已有 triangular full/low square leaves。

[toom_low.rs:35–52](https://github.com/miles-song/VeriGMP/blob/7219cbd013dbf323f7121e4a9e197964f55377ca/native/verified/toom_low.rs#L35) 先算 \(M(k)\)，其中 \(h=\lfloor9n/40\rfloor,\ k=n-h\)，产生 2k words，复制前 n words，然后算两个 h-word low products。其精确 identity 是
\[
AB\bmod B^n =
\bigl(A_0B_0+B^k((A_1B_{0,h}+A_{0,h}B_1)\bmod B^h)\bigr)\bmod B^n.
\]
这里 \(A=A_0+B^kA_1\)，\(B=B_0+B^kB_1\)，\(A_{0,h}=A_0\bmod B^h\)。\(2k\ge n\) 消去 high-high term。square 已经只算一个 low cross product，并加两次；这不是新的机会。

n=4096 multiplication 的 h=921、k=3175：central full product 输出 6350 words，仅留 4096，2254 output words 最终丢弃。**丢弃这些 words 不代表能删除同样比例的 point multiplications**；Toom interpolation 仍依赖全部五个 point values。square 的 h=1251、k=2845，丢弃 central full-square 的1594 words。

[toom_multiply.rs:25–85](https://github.com/miles-song/VeriGMP/blob/7219cbd013dbf323f7121e4a9e197964f55377ca/native/verified/toom_multiply.rs#L25) 使用 k=ceil(n/3)、m=k+1，五个 product buffers 各2m，加 ax/bx 各m，再复用 child work；三个 interior products 一律按 m limbs 递归。interpolation 后先 zero(dst)，再做五个 add_shifted。toom_square 对应代码相同，但仅一个 evaluation operand。constant /2、/3 的源码形式不证明存在硬件 DIV 热点；已有 exact-by3 负实验也不支持继续以此为首要方向。

[fast_multiply.rs:22–75](https://github.com/miles-song/VeriGMP/blob/7219cbd013dbf323f7121e4a9e197964f55377ca/native/verified/fast_multiply.rs#L22) 与 [multiply.rs:14–70](https://github.com/miles-song/VeriGMP/blob/7219cbd013dbf323f7121e4a9e197964f55377ca/native/verified/multiply.rs#L14) 的 leaf 是 row-wise MAC：
\[
t=a_i b_j+dst_{i+j}+carry,\quad dst_{i+j}=t\bmod B,\quad carry=\lfloor t/B\rfloor.
\]
first row 已直接写出，不需要再提出“去掉 first-row zero”。mac4 只是相同 carry chain 的四次展开。fast_words::add_extended 已通过 add_small 在 carry=0 时停止；不能把它描述成无条件扫描整个 tail。

静态展开当前默认调用树得到：

| public workload | n | leaf word multiplications | multiplication-leaf dst reads | multiplication-leaf dst writes | 改为 column 后这些 leaf 的 dst writes |
|---|---:|---:|---:|---:|---:|
| mul_mod | 256 | 18,186 | 17,238 | 19,042 | 1,804 |
| mul_mod | 512 | 51,530 | 49,030 | 53,800 | 4,770 |
| mul_mod | 1024 | 146,237 | 139,764 | 152,506 | 12,742 |
| mul_mod | 2048 | 418,838 | 399,306 | 437,958 | 38,652 |
| mul_mod | 4096 | 990,025 | 927,970 | 1,051,712 | 123,742 |
| square_mod | 256 | 9,396 | 2,118 | 2,414 | 296 |
| square_mod | 512 | 23,553 | 6,946 | 7,786 | 840 |
| square_mod | 1024 | 70,161 | 20,856 | 23,234 | 2,378 |
| square_mod | 2048 | 208,690 | 63,906 | 70,902 | 6,996 |
| square_mod | 4096 | 514,422 | 173,574 | 193,588 | 20,014 |

计数口径：word multiplication 含 triangular square leaf；dst traffic 列只含 general multiplication leaves，不含 square leaves、evaluation、interpolation、recursion recombination 或 compiler spills。full row leaf n 有 n² products、n(n−1) dst reads、n²+n dst writes；low row leaf 有 n(n+1)/2 products、n(n−1)/2 dst reads、n(n+1)/2 writes。column full/low 写2n/n words。表中column列是假设替换全部general multiplication leaves的参照；首批固定scope之外的leaf仍保留row路径，不能把全列节省都记入首批候选。4096 mul的实际leaf sizes全部处于首批scope。以上是源码层操作计数，不是 cache miss、DRAM bytes、cycle profile 或 machine-checked cost theorem。column scanning 可能增加 a-operand reads：row 可复用一个 a_i，而 column 同时读取两个 operands；不能把减少的 dst reads 全当成总 load 节省。

复现此表不需要执行 arithmetic：递归计数 K(n)=2K(ceil(n/2))+K(floor(n/2))，n≤24 用 basecase；T(n)=T(k)+T(n−2k)+3T(k+1)，n≤192 用K；low 用上述实际 split/limit；square 用相同递归的 square cost，并将 low-square cross 交给一般 low multiplication。plan.json 保留完整 leaf histogram。4096 mul 的3933个 full leaves 中，3143个是15 limbs；不能只 benchmark 16/32/64等整齐尺寸。4096 square 中 general-mul leaf products 为183,721，占其514,422 total word products约35.7%；只优化 general leaves不会覆盖剩余 square leaf 工作。

理论上 full Toom-3 的 recurrence 为5T(n/3+O(1))+O(n)，指数log_3(5)≈1.465；low recursion 是 M((1−a)n)+2L(an)+O(n)。没有 profiling 时，不能断言 carry、store 或 interpolation 哪一项占 wall time 的主要百分比；本设计选择的是覆盖大量执行工作的机制，不是假装已定位 cycle-level bottleneck。

**3. 证据状态和已排除的重复工作**

- 历史 cutoff9 数据基于 c083839dc07f9b0cffea1a52cd6810d817105355。23-limb square candidate/baseline=0.67094、0.64362；64-limb=0.55281、0.52958。4096 mul candidate/GMP=2.32965、2.35900；square=2.17283、2.14129。这些是旧 snapshot 的观察，不能标为 current-main fresh timing。
- fused-interpolation timing archive 两轮 primary GM=0.9823753468、0.9863431240，均未满足≤0.98；run2 worst=1.0629641214>1.05；control drift 也失败。native baseline tree 与本轮 main相同，但 receipt 对 captured baseline HEAD 4510b46e、publication baseline bf1bc409 分别记载，不能压成“在7219cbd运行的新测试”。该负实验的原始声明和来源应保留。
- exact-by3 E1 的 primary GM=1.003475113457792、0.999232749796327；NO-GO。doubled-cross W1=0.9914866040028288、0.9832239874205505；NO-GO。combination 也有独立失败 gate。它们不应以新名字重新进入首批计划。
- 已只读检查 low-square25..64 的专用 dispatch、cross-fusion 的 combine_cross 变体，以及 Toom-4 candidate wrapper：mul n≥2048、square n≥1024 才切换。未复验其静态证据，也没有看到足以在本轮宣告 current performance acceptance 的证据。
- 还检查了公开 Toom8 recursive/recomposition experiment 文档。十五个 child products 和十五系数 shifted-add recomposition 已有实验；“加入Toom8”本身不能当作本设计的原创方向。
- 核心与实验源搜索没有发现本方案这种 full-u64 bounded split-sum column leaf；这只是已检查范围内的结果，不是历史或全世界不存在的证明。packed consumer 的u128 coefficient accumulator 是另一种有界 coefficient workload，不能直接承接任意u64 limb products。
- main中native tree一致可用于绑定历史证据的适用源码范围，仍不能替代本候选的新 executable、codegen、同机 repeat与组合实验。

**4. 优先级**

| Rank | 机制 | 要消除的成本 | 即时价值 / 主要风险 |
|---|---|---|---|
| 1 | bounded split-sum column leaf | 每个 word product 的完整 carry feedback；重复 dst read-modify-write | 覆盖整个 recursion 的叶子，O(1)额外存储，易做小实验；u128 lowering/寄存器 spill可能抵消 |
| 2 | single-write recomposition + requested-prefix output | Toom输出zero、重复shifted-add、central full-output materialization和copy | 不改 interpolation identity；作用于full/low/square；收益受 linear overhead份额限制 |
| 3 | exact two-prime NTT/CRT large path | 用新的 convolution algorithm替换大量递归 word multiplications | asymptotic路线；4096可能尚无 crossover，证明与workspace变更较大 |
| 4 | bounded top-carry peeling | 把k+1 recursive point product变成k-word product+小carry correction | 靠近特定 recursion尺寸才可能收益；correction可使总工作增加，优先级较低 |

前三条分别改变 leaf carry/dataflow、跨层 memory scheduling、large-operation algorithm。第四条给出具体 representation/work-avoidance 备选，但静态判断不足以推荐抢先实施。所有排名是工程判断，不是 measured ranking。

**5. Rank 1 — 首批 implementation package**

**5.1 独立规格、输入域与 identity**

首批内部函数建议放在 native/verified/column_multiply.rs，独立规格放 native/specs/column_product.rs，模块由 native/lib.rs 导出。不要改 multiply::mac：原 row implementation保留作fallback与独立 differential reference。

统一数学规格允许 operands长度r,s≤128，r,s>0，输入每 limb 任意u64；dst长度q满足0<q≤r+s：
\[
A=\sum_{i=0}^{r-1}a_iB^i,\quad C=\sum_{j=0}^{s-1}b_jB^j,\quad
dst=(AC)\bmod B^q.
\]
q=r+s时由range得到完整精确乘积。首批export仅equal-length full(q=2n)和low(q=n)；rectangular specialization随后再接，不把现有public接口的equal-length前提偷偷扩大。public function原来的任意长度contract必须保留，超出candidate范围继续走原算法。

定义未归一化column
\[
D_k=\sum_{\substack{0\le i<r,\ 0\le j<s\\i+j=k}}a_i b_j.
\]
设C_0=0，每轮
\[
d_k=(C_k+D_k)\bmod B,\quad C_{k+1}=\lfloor(C_k+D_k)/B\rfloor.
\]
对任意k：
\[
\sum_{t<k}d_tB^t+B^k C_k=\sum_{t<k}D_tB^t.
\]
k=q时，所有没处理的terms都是B^q倍数，所以low result精确。完整输出要处理r+s columns，最后一个column没有product但必须flush carry；不能只写r+s−1 words。

为避免D_k可能超过u128，绝不把两个任意u128 products直接相加。拆每个product：
\[
p_i=\ell_i+B h_i,\quad 0\le \ell_i<B,\quad 0\le h_i<B.
\]
两个独立lane各自累加low/high halves。归一化时
\[
L=(C_k\bmod B)+L_0+L_1,\quad
H=\lfloor C_k/B\rfloor+H_0+H_1+\lfloor L/B\rfloor;
\quad d_k=L\bmod B,\ C_{k+1}=H.
\]
这是精确integer identity，不是近似carry或概率correctness。

**5.2 伪代码**

以下伪代码强调数据依赖，实际Verus代码使用安全slice indexing和固定scalar locals；两lane不能实现成Vec或动态数组。

~~~rust
fn column_prefix(dst, a, b) {
    // r,s in 1..=128, 0<q<=r+s; dst disjoint from a,b
    let mut carry: u128 = 0;
    for k in 0..q {
        let start = if k >= s { k - (s - 1) } else { 0 };
        let end = min(k + 1, r); // exclusive; can be <= start at final column
        let (mut l0, mut h0, mut l1, mut h1) = (0u128, 0u128, 0u128, 0u128);
        let mut i = start;
        while i + 1 < end {
            let p0 = (a[i] as u128) * (b[k-i] as u128);
            let p1 = (a[i+1] as u128) * (b[k-i-1] as u128);
            l0 += (p0 as u64) as u128;
            h0 += p0 >> 64;
            l1 += (p1 as u64) as u128;
            h1 += p1 >> 64;
            i += 2;
        }
        if i < end {
            let p = (a[i] as u128) * (b[k-i] as u128);
            l0 += (p as u64) as u128;
            h0 += p >> 64;
        }
        let low_sum = (carry as u64) as u128 + l0 + l1;
        let next = (carry >> 64) + h0 + h1 + (low_sum >> 64);
        dst[k] = low_sum as u64;
        carry = next;
    }
}
~~~

实际首先可以为equal-length低半区与高半区分别写loops，消除每column的min/max；保留同一个规格。上述伪代码中的i+1、k+1安全来自≤256的域，不靠wrapping或unchecked flags。若subslice长度为0，统一helper可拒绝该域；现有允许empty的public reference接口保持原语义，不越权改变。

关键区别：mac4的每次乘法结果进入下一个MAC的carry；这里lane中的product与之前column carry无关，carry只在column末尾参与。虽然各lane仍有addition recurrence，完整宽carry feedback的scope已改变。编译器是否能利用这种独立性必须看optimized assembly，不能由Rust代码宣布已经得到双ADX chain。

**5.3 Bounds、容量和别名**

令N=min(r,s)≤128。由D_k≤N(B−1)²及归纳C_k≤N(B−1)，得到C_{k+1}≤N(B−1)。每个half sum最多128(B−1)，low_sum<129B，next的保守独立上界<130B，均远小于2^128。这里carry本身可能有超过64个有效bits，必须用u128；把carry改成u64会截断真实结果。

dst只写、不读旧值；a与b允许同一个immutable slice，dst与任一input不允许overlap；safe Rust的借用约束自然表达。不得为了“in-place支持”引入unsafe别名。没有额外scratch，现有4n/12n/10n workspace API保持不变。寄存器locals为O(1)，worst-case额外栈也O(1)；实际spill数量是codegen验收项目。q的每一个word都要写，包括高位0，不能保留旧dst尾部。

首批candidate dispatch预声明：full leaf 8≤n≤24；low leaf 32≤n≤128；范围外原row实现。这个scope避免将inner-loop setup推广到极小case，沿用原recursion thresholds；它不是从后验timing挑选胜出尺寸。若需改变scope，应另立新candidate和新的预声明实验。

**5.4 Verus refinement obligations**

- input-independent D_k/spec convolution定义、索引bijection与sum decomposition；不能把期望答案定义成执行后的dst。
- 每个u64×u64 product分解为low+Bh；每lane loop覆盖准确、无遗漏、无重复、奇数tail正确。
- 两lane partial sums与数学sum的对应、所有u128 adds/muls/shifts/range obligations；证明C可能大于u64但不超过N(B−1)。
- outer invariant如5.1；untouched input与already-written prefix的frame；最后empty column正确。
- low truncation正确、完整product range消去最后carry；normalize_top保持模2^{64(n−1)+top}，top=64不得shift by64。
- equal-length wrappers与existing base_full/base_low contract完全一致；fallback覆盖candidate域之外；termination和machine-length safety。
- ghost Seq、sum、visit counters必须全部erase；不将loop invariant变成runtime遍历。无assume/admit、external body、custom axiom、FFI、unchecked verification flags。
- 分别报告实际refinement、解析word-operation cost、完整算法bit complexity。leaf仍O(rs) word multiplications；在固定64bit字长和固定scope下，existing recursive asymptotic不变，额外live space O(1)。这不是已验证的cost theorem。

**5.5 最小强信号实验与立即停止条件**

不要先搭新benchmark平台。原主 agent 实现一个leaf helper、两个wrapper、有限runner分支，复用现有身份绑定与计时机制。先用静态codegen排除每product重新形成完整carry chain、重复MUL、heap allocation、runtime ghost materialization、inner-loop bounds panic或大面积spill；若codegen无法表达预期结构，先修一个明确结构问题，不开启threshold sweep。

一次小screen只测forced full n=15、20和forced low n=46、115，固定dense random与all-max两类input，当前row vs新column，7次≥10ms samples，输入、preallocation、compiler flags一致、交错顺序。四个尺寸来自实际recursion或principal low leaves，不是power-of-two样例。两种数据都参与；不能只挑随机case掩盖worst carry。

**建议的工程go门槛**：四尺寸、两数据类的cell median ratios geometric mean≤0.90，且每cell≤1.03。门槛是“值得投入下一阶段”的预先决策标准，不是预测可得到10% gain，也不是native/performance-target.json的替代。失败则记录NO-GO，停止本实现的扩展；不通过反复重跑等待好结果。一次与明确codegen原因对应的改写可作为新candidate，但必须保留原负结果。不同语义/带宽counter不是继续投入的理由。

screen通过后，先integrate上述固定scope，测current default mul_mod n=512、4096及square_mod n=4096；这一步确定leaf收益能否穿过recursive overhead。如果mul两个case没有可重复的≥3% reduction，暂不扩大至所有组合；square作为regression约束保留。没有leaf profile时，也不要把leaf GM当成whole-operation GM。

**5.6 Production gates**

- 在同一immutable candidate native tree上完成Verus实际entry refinement和release compile；同source的rmeta/rlib/vstd工具身份匹配。
- independent exact-integer oracle覆盖full与low；small lengths穷尽selected limb alphabet {0,1,B−1,B−2,2^63}，large随机/alternating/all-max/one-hot/long-carry。检查a=b、leading zeros、odd lengths、dirty dst、short capacity rejection，所有合法返回分支。
- 长度至少含0/1/2（按各API合法性）、7/8/9、13/14/15/16、19/20/21、23/24/25、31/32/33、35、45/46/47、63/64/65、95/96/97、114/115/116、127/128/129；integration还含所有registered key shapes和recursion cutoff±1。top=1/63/64，并覆盖noncanonical input top bits。
- semantic mutation：漏odd tail、lane1下标错一位、把carry缩成u64、漏carry>>64、漏low_sum>>64、p high shift改63、full不flush最后word、low多写一word、mask错一bit。证明或oracle必须给出语义失败；timeout/tool error不算rejection。
- codegen逐个forced root和default root检查：无ghost/heap/general division；宽乘积只计算一次，实际loops和store边界与设计一致，检查scalar accumulator spill与panic paths；不强求出现某个ISA mnemonic才叫正确。
- 候选局部验收建议：当前main为baseline，mul_mod五个principal cells的GM≤0.97，且目标scope内每principal cell≤1.0；全部registered operations/key shapes对current baseline≤1.05。两次独立run分别满足，不能pooled才过。若只能一个更窄scope稳定胜出，应以新冻结scope重新验证。
- 同时继续报告每cell candidate/GMP；整体parity仅在原registered 1.0/1.2 gates和第二run均过时成立。scoped feature失败/通过与backend promotion分开。
- 需要独立代码/证明/性能review后，按repo允许的小步提交与remote确认流程合入；本设计不充当实现后的独立review。

**6. Rank 2 — Single-write recomposition 与 requested-prefix output**

这是较高确定性的work avoidance：先保持五个point products与现有interpolation不变，只替换已恢复coefficients到dst的数据流，随后消除low wrapper不需要的full output。与已失败fused-interpolation不同，本路线不融合除法或scaled subtraction。

令Q=B^k，input polynomial product系数c0..c4满足
\[
AB=\sum_{j=0}^{4}c_jQ^j,\quad
c_0,c_4<Q^2,\ c_1,c_3<2Q^2,\ c_2<3Q^2.
\]
定义c_j的radix-B words，缺失word按0。输出word t为
\[
u_t=carry_t+\sum_{j=0}^{4}c_j[t-jk],\quad
dst_t=u_t\bmod B,\ carry_{t+1}=\lfloor u_t/B\rfloor.
\]
因此可顺序覆盖dst，而不zero、不读旧dst、不做五轮shifted-add。coefficients非负，最终低q words恰为AB mod B^q。不能在interpolation尚未结束时随意截断point values：除2/3与signed intermediate依赖guard信息。

首批函数 native/verified/toom_recompose.rs::write_prefix(dst,p0,p1,pm,p2,p4,k)。实际不使用“每word循环五个动态sources”的低效实现。按k-word bands展开：band t的普通位置只加c_t的low block和c_(t−1)的high block；band首位额外加入c_(t−2)[2k]。恢复后的coefficients都有c_j[2k+1]=0；证明这些bounds后不读padding。两stream加carry用u128即可，guard≤2，保守carry≤3。边界band与短c4用单独tail处理，不在每个inner iteration反复做5个bounds判断。

scratch初始沿用现有p0/p4/p1/pm/p2/ax/bx/work layout；先不把coefficients放进dst，避免unsafe overlap与复杂生命周期。这样第一步只有一个consumer helper的证明。平衡n=3k时，现有recomposition约6k zero stores+10k shifted-add stores及约10k dst reads；新write约6k stores、0 old-dst reads，仍需读相同coefficients。这里忽略O(1)guards和carry tails，不能据此称whole-multiply省62.5%。

第二步为central full product引入prefix entry：dst长度q≤2m时，保持child full computations和interpolation，最后只write q words。toom_low::low不再分配2k-word product再copy前n words，而直接写n-word dst；square_low同理。对未进入Toom的小size，使用scratch中的full product加copy fallback即可，不能强行改低层算法。新prefix helper可保持12m（square10m）capacity bound：小size fallback用2m temporary+3m Karatsuba scratch足够；递归Toom沿用现有bank。去掉的是外层2k temporary的同时存活与copy，以及不需要的final output suffix；**没有减少五个point product数量**。

GMP 6.3.0已把v0/v1/vinf放在output相邻区域，并将interpolation与recomposition交织，使用saved overlap words。见[toom33_mul.c:248](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/toom33_mul.c#l248)及[toom_interpolate_5pts.c:129](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/toom_interpolate_5pts.c#l129)。本方案第一步用disjoint immutable coefficient bank和一次write实现同类节流；不是声称发明output placement。完整GMP式overlap scheduling可减少bank，但暂不作为首批需求。

Refinement重点：input-defined coefficient意义、padding为0、高guard bound、band覆盖/无遗漏、q处截断、任意old dst不影响结果、coefficients只读、odd split和短a2/b2、index/size overflow。mutation至少包括漏c2 top guard、band offset错一、末尾short c4截断、保留旧dst word。复杂度仍O(n)recomposition与O(n)peak storage；若第二步减少live temporary，需要另给实际lifetime recurrence，不把workspace API上界下降当成已发生。

最小实验：原主 agent 对同一恢复好的合法coefficient bank比较old zero+5 adds与新write，先用full n=193/769/3175和prefix q对应真实low调用；然后一组full/low default 1024、4096。建议helper GM≤0.80且whole-operation至少3%才扩大；否则它可能只是一个low-overhead kernel里的局部漂亮数字。fresh coefficient generation不放入helper计时，但最终whole-operation必须包含所有evaluation/interpolation/child work。oracle用独立input-derived convolution，不让两个recomposer的共同错误互相验证。Production沿用第5.6节通用gates，并覆盖q=k−1/k/k+1、2k−1/2k/2k+1、2m、各band首尾和已有combined dispatch。

与Toom-4的组合需要一个七系数版本及新的guard/overlap数证明，不能直接以五系数helper替换。与Toom8已存在的十五系数recomposition同理。不同arity的单写recomposition属于同一机制，但每个消费者独立refine和measure。

**7. Rank 3 — Exact NTT/CRT large-operation path**

这是扩展large path的算法方向，优先级低于可快速实施的前两项。目标是突破只使用Toom-3的递归work，不是重新命名已有scoped Toom-4/Toom8实验。

建议有限域原型：把每u64 limb精确拆成4个radix \(R=2^{16}\) digits。长度r,s limbs对应La=4r、Lb=4s digits，补0至N=next_power_of_two(La+Lb−1)。使用p1=167772161=5·2^25+1、p2=469762049=7·2^26+1，primitive root3；这两个prime/root在[AtCoder Library v1.5.1 internal_math](https://github.com/atcoder/ac-library/blob/d8ca7f26686f6c78d15d13ca438ea866526e87fb/atcoder/internal_math.hpp#L132)有明确源记录，tag resolved commit d8ca7f26686f6c78d15d13ca438ea866526e87fb。实际production证明仍须闭合primality/root-order certificate，不能把“库中写了常量”当成Verus axiom。

各prime做forward A、forward B、pointwise multiply、inverse和乘N^{-1}，得到convolution residues。若
\[
\min(La,Lb)(R-1)^2 < P=p_1p_2,
\]
CRT唯一恢复非负integer coefficient：
\[
c_t=r_{1,t}+p_1\left((r_{2,t}-r_{1,t})p_1^{-1}\bmod p_2\right),\quad 0\le c_t<P.
\]
之后\(v_t=c_t+carry_t,\ d_t=v_t\bmod R,\ carry_{t+1}=\lfloor v_t/R\rfloor\)，每4digits打包回u64，最后做precision mask。负difference必须canonicalize；这不是浮点FFT，不存在rounding许可。

4096等长输入时La=Lb=16384、N=32768，coefficient bound=70,366,596,710,400，P=78,812,994,116,517,889，唯一性有充分余量。每个prime residue product小于p2²<2^58，u64容纳；CRT coefficient与carry也需单独bounds。使用proved Barrett/Montgomery或常量mod reduction；不能让generic u128 DIV落入每个butterfly。roots、twiddles和inverse constants均固定并验证；没有运行时“试到一个可用prime”为止的策略。

重要反证：最简单radix-2实现的4096 mul需6 transforms，共1,474,560 butterflies，另外65,536 pointwise modular products；square可省一个forward每prime，仍有983,040 butterflies。它们不是相同成本的word MAC，也不能推出比当前990,025 word products快。N=32768还有power-of-two jumps、twiddle traffic和conversion成本，因此不能承诺4096 crossover。更大的长度或优化过的radix-4/SIMD可能更合适，但不以未验证intrinsics绕过core。

scratch方案必须明确类型：两N-word transform buffers复用两个primes，另存prime1所需coefficients（full La+Lb−1，low只需4q）。纯u64 scratch实现需2N+coefficient_count words，4096 low为81,920 words=640 KiB，超过当前mul API的12n=49,152 words。第一版应是独立caller-owned workspace API，提供checked workspace_len_ntt；不要在现有scratch不足时偷偷allocate。若以后用u32 buffers减半内存，给出新的typed API；不能未经证明unsafe reinterpret u64 scratch。twiddle tables另计live space，首次setup成本与可复用plan的timing边界都预先登记。

GMP的大尺寸方案是Schönhage–Strassen式Fermat/negacyclic FFT，evaluation arithmetic利用2的幂实现shift/add，不是上述双word-prime NTT。参见[GMP 6.3.0 FFT说明](https://gmplib.org/manual/FFT-Multiplication)。[mul_n.c](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/mul_n.c)有更高Toom和FFT dispatch；Zen3参数表只是某配置的例子，不能宣称本机GMP恰在某阈值选FFT。NTT、CRT和常量reduction均是既有技术，不主张数学原创。

最小falsifier：先只实现一个固定prime的verified transform和完整两prime composition于n=4096；证明/独立oracle通过后，测包括pack、所有transforms、CRT、carry/unpack的总成本。若不超过current Toom3并有明显余量，再看8192/16384是否形成稳定crossover；若4096失败，不因此扩展生产scope或把更大尺寸胜出算作registered4096通过。长路线可以单独接受“仅大于某已验证规模”的scope，但全1.0/1.2目标仍单列。

Production correctness：inverse(forward(x))、convolution identity、zero padding免cyclic alias、CRT uniqueness、carry packing、short operands、q截断、workspace overflow、root-order/primality实际证书、所有mod reduction bounds。mutation包括错root/inverse、漏N^{-1}、CRT符号错误、padding N少一倍、coefficient capacity不足、漏carry。bit cost有限域实现为O(N log N)固定字运算与O(N)storage；固定两个prime只覆盖显式root-order/coefficient bound域，不能外推为任意规模整数乘法。域外fallback至现有精确算法；若要无界渐近结论，另设计增长prime/递归transform与成本证明。

low residue不能直接用N=La的cyclic convolution：上半项会wrap进低半项。第一版仅省高系数CRT/unpack，不宣称truncated NTT。GMP comparison仍保持原public comparator。NTT进入的shape通常绕过Toom-4与column leaf，所以收益不能相乘；dispatch下两条路径互斥。

**8. Rank 4 — Bounded top-carry peeling**

现有三个interior Toom3 point products总用m=k+1。evaluation最高word已数学上界很小：+1≤2，−1 magnitude≤1，+2≤6。写X=x+αQ，Y=y+βQ，Q=B^k：
\[
XY=xy+Q(\alpha y+\beta x)+\alpha\beta Q^2.
\]
先recursive full(x,y,k)，再在高k words上做一次fused small-coefficient correction，最后写guard，避免把小scalar当成完整额外limb参与递归。

~~~text
full(P[0:2k], x[0:k], y[0:k], child_scratch)
carry = 0
for i in 0..k:
    t = P[k+i] + alpha*y[i] + beta*x[i] + carry  // exact u128
    P[k+i] = t mod B
    carry = t div B
P[2k] = alpha*beta + carry
P[2k+1] = 0
~~~

α,β≤6时carry≤12，guard≤48，与XY<49Q²吻合。negative point product仍由原sign bit进入interpolation；这里仅乘magnitudes。square correction为2αx，不能重复算两次full product。scratch保持原2(k+1)-word output与evaluation arrays，各区disjoint。

GMP [toom33_mul.c:255–310](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/toom33_mul.c#l255)已有SMALLER_RECURSION条件实现与−1的短长度选择。它不是本方案原创，且不能认定measured GMP启用了可选宏。

不宜现在优先：少一个recursive limb并不自动省工作。例k=24，current full(25)用Karatsuba叶乘count=2·13²+12²=482；peel后full(24)已有576个word products，再加correction。因此“避免threshold crossing”有时会更慢。即使一般scalar correction用小常量，Verus的范围证明也不保证LLVM知道它能省成shift/add。只在既有full family与实际child sizes显示有余量时做固定shape实验。

最小falsifier选实际k=132、265、1059及相邻192/193边界，fixed αβ=(0,0),(1,1),(2,2),(6,6)，当前full(k+1) vs peeled。所有类别都保留，先验证nontrivial high scalar cases而非只测0。证明identity、u128 bound、未修改低k前缀、guard写入、padding/frame、sign兼容；mutate漏αβ、漏一cross、小carry上界、−1sign。若没有consistent gain，维持现状。Production依第5.6节且使用all-valid full-u64 evaluation inputs，不能仅用小top input。

可与column leaf叠加，但缩短child size会改变leaf histogram；必须重测。Toom-4有不同evaluation weights与top bounds，不能直接复制≤6假设。此路线与D2可语义组合；它们可能竞争相同linear-overhead预算，不能简单相乘收益。

**9. 与已有候选的组合及SAT transfer边界**

| 组合 | 可以组合的条件 | 不成立的推断 |
|---|---|---|
| D1 + Karatsuba cross-fusion | D1改变leaf，cross-fusion改变combine_cross；独立scope与同tree proofs可组合 | 改了leaf成本，旧threshold或旧gain仍最优 |
| D1 + low-square25..64 | 保留dedicated square leaf；D1只改变其调用到的general cross/full leaves | 把low-square替换成一般mul(a,a)后仍保留square收益 |
| D1 + scoped Toom-4 | child full/low确实到达common leaf；在新full tree上重验 | Toom-4减少leaf数量，因此两个独立百分比可直接相乘 |
| D2 + Toom-4/Toom8 | 为7/15 coefficients各证明bounds、band schedule与prefix语义 | 五系数recomposer能直接处理任意arity |
| D3 + 现有Toom | 按长度/shape选一条exact path；域外fallback | 在同一shape上NTT与Toom4收益叠加 |
| D4 + D1/D2 | guard correction与word representation一致，重新测组合 | 名义递归长度更短就必然更快 |

原主 agent 只对已经独立有信号的组合做2×2实验：T00 current，T10新候选，T01已验收候选，T11组合；同inputs、metadata和精确语义，报告T11/T00、T11/T01及interaction=T11*T00/(T10*T01)。对于尚未performance-accepted的候选，组合结果仍不能倒推出单项已接受。先做最相关一对，避免把8-way组合矩阵或监控工程变成主体。

SAT transfer仅讨论通用exact整数workload：

- **Exact full products**：D1直接保持2n-word result；D2 full输出须保留所有carry；D3只有CRT coefficient上界闭合才是exact full product。任何low-only结果都不能代替整数完整积。
- **Residue products mod 2^p**：D1可只走需要的columns；D2可只write prefix后mask；输入允许未mask的top bits，因为模同态保留正确结果。D3仍需防cyclic alias，不可直接缩短transform。输入的创建精度/lift contract属于caller，kernel优化不能用更高精度重算表达式。
- **Unequal operands**：public当前fast接口主要equal-length。D1的D_k规格天然支持r≠s，但首批wrapper不承诺全库rectangular API；极不平衡r≫s时column setup和两operand loads可能不如row或mul_word，必须单独dispatch。D2需已有unequal Toom decomposition，不能只把short operand补成最大n后声称有效；D3的N取决于r+s并受power-of-two jumps影响，1×n不适合transform。
- 不做零稀疏、相同operand、residue valuation、batch重用或真实SAT长度分布的未经验证假设。若caller能明确提供已证明的有效长度，可后续减少zero padding；本轮没有私有trace，因此不能估算SAT end-to-end speedup。
- Exact counting/completeness要求每次算术结果保持原契约；减少输出precision只能由caller的数学contract授权。复杂度分别记bit length、coefficient bound、precision、full/low模式和peak simultaneously-live workspace；不能用unit-cost arithmetic掩盖增长。
- solver traces应在调参前冻结，并记录operation、输入/输出length、precision、签名语义、正确结果hash和allocation边界即可；无需公开或读取私有算法源。通过library gates不等于solver已接受。

**10. 连贯的三阶段执行顺序**

1. **Leaf first**：原主 agent 在新的隔离实验checkout（以最新main重新核对）独立编写D1 spec+helper+两个wrappers。先实际refinement/independent oracle和codegen，再做第5.5节八cell强信号screen。本design本身不授权创建别的agents或暂停服务；host操作沿用原主任务的实际授权。
2. **Integrate and accept a scope**：screen过后固定candidate native tree，接入full8..24/low32..128，完成default parents与registered boundary/regression两轮；只组合一个已独立接受的最相关候选。若D1已无强信号则止损，下一优先D2的single-write helper，而不是反复微调D1 thresholds。性能足够即按scoped feature合入，不等整体GMP parity。
3. **Large path evolution**：D2可在相同coefficients contracts下去掉low central temporary；仅当仍有大尺寸缺口且前两项数据表明有必要，再建设独立D3 NTT workspace/transform/CRT路径。D4只在静态child-size差异与小screen支持时进入，不作为默认里程碑。

**明确next action**：从7219cbd及其实际后继main重新核对source，新增column_product规格与column_multiply helper；首先证明“任意u64输入、N≤128、two split-half lanes、carry为u128”的column invariant，并输出一个full15/20、low46/115 forced-entry comparison executable供原主 agent测试。不要把scale-subtract、exact-by3或cross-fusion改名纳入这一提交。

**11. Sources、assumptions与缺口**

主要外部来源全部为primary source；下面只用于算法/实现事实，不把其旧timing外推为本机速度：

- GMP 6.3.0 [official archive](https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz)，本地 E:/3sat/VeriGMP-optimization-opportunities-20261108/gmp-6.3.0.tar.xz 的hash已核实。
- GMP immutable [mul_basecase.c](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/mul_basecase.c)、[mullo_n.c](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/mullo_n.c)、[toom33_mul.c](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/toom33_mul.c)、[toom3_sqr.c](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/toom3_sqr.c)、[interpolate_5pts.c](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/generic/toom_interpolate_5pts.c)。本地release-source对应文件和public pin一致；selected SHA-256见plan.json。
- GMP [Zen3 addmul_1 wrapper](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/x86_64/zen3/addmul_1.asm)包含coreibwl版本；[coreibwl实现](https://gmplib.org/repo/gmp/file/bc0ec1699e58/mpn/x86_64/coreibwl/addmul_1.asm)实际有MULX/ADCX/ADOX调度。只说明source差异，不认定measured binary选了该kernel。
- [GMP multiplication algorithms](https://gmplib.org/manual/Multiplication-Algorithms)、[FFT multiplication](https://gmplib.org/manual/FFT-Multiplication)，文档标识GNU MP 6.3.0。
- Brumnik, Kovtun, Okhrimenko, Kavun, “Techniques for Performance Improvement of Integer Multiplication in Cryptographic Applications”, Mathematical Problems in Engineering 2014, article863617，[publisher primary article](https://onlinelibrary.wiley.com/doi/10.1155/2014/863617)，尤其Algorithm2的modified Comba/delayed carry。其Win32/GMP4.1.2比较不能当作Zen4/GMP6.3.0速度证据；这里只用于否定“首次发明”的claim。
- P.G.Comba, “Exponentiation Cryptosystems on the IBM PC”, IBM Systems Journal29(4),526–538,1990，[DOI](https://doi.org/10.1147/sj.294.0526)。本轮检索到原文abstract及publisher引用；原PDF全文fetch失败，所以没有依据它断言详细实现或性能。
- AtCoder Library v1.5.1，peeled commit d8ca7f26686f6c78d15d13ca438ea866526e87fb：[convolution.hpp](https://github.com/atcoder/ac-library/blob/d8ca7f26686f6c78d15d13ca438ea866526e87fb/atcoder/convolution.hpp)、[internal_math.hpp](https://github.com/atcoder/ac-library/blob/d8ca7f26686f6c78d15d13ca438ea866526e87fb/atcoder/internal_math.hpp)。用于prime/root和NTT/CRT prior art；本方案两prime bounded integer reconstruction是独立推导，不直接复制convolution_ll的三prime signed64实现。

Local evidence：
E:/3sat/VeriGMP-scaled-experiments/docs/data/2026-11-02-low-square-cutoff9/{metadata.json,performance-summary.json}；
experiments/acceptance/fused-interpolation-20261108/timing-20261109/{README.md,runs/summary.json,receipts/identity-pre-timing.json,receipts/host-window-start.json}；
experiments/acceptance/{arithmetic-negative-20261108,exact-by3-negative-20261109}/RESULTS.md；
experiments/toom8-primitives/{recursive,recomposition}/README.md。
其中旧gmp-internals.md只作导航；本报告关键source差异已重新读取实际source。

当前缺口：没有cycle profile；没有D1–D4实现或新性能数据；没有当前GMP binary配置/实际dispatch的完整确认；没有这批设计的machine-checked cost theorem；没有private SAT workload分布与frozen consumer acceptance；没有足以认定学术新颖性的全面prior-art检索。proof/toolchain claims来自既有pin和receipts，不是本轮新运行。rank与go门槛属于本次设计判断，所有速度收益仍待falsification。

独立实现须遵守适用license。参考GMP策略不授权直接搬运GPL/LGPL assembly；若使用第三方代码，另行保留准确版本与license并评估兼容性。首选从上述identities独立写Rust和proof。

