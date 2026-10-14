# LLM 安全研究的误报抑制、基准方法学与可复现性：证据核查报告

> 核查方法：所有条目均基于我实际抓取的页面（arXiv abs/HTML、ar5iv、GitHub API/README、厂商博客、PyPI、TechCrunch）。凡未能抓取到正文的，一律标注「未核实」，不做推测。数值仅引用原文出现的数字，并在必要时注明其**指标定义**（很多论文的 "FDR/FP" 与直觉上的误报率不是一回事）。
> 抓取时间：2026 年（当前 arXiv 已有 26xx 编号的论文）。

---

## 误报抑制

### 1. IRIS: LLM-Assisted Static Analysis for Detecting Security Vulnerabilities

- **来源**：[arXiv:2405.17238](https://arxiv.org/abs/2405.17238)（ICLR 2025；HTML 全文 [arxiv.org/html/2405.17238v3](https://arxiv.org/html/2405.17238v3)）；[代码仓库 iris-sast/iris](https://github.com/iris-sast/iris)
- **作者/机构**：Ziyang Li, Saikat Dutta, Mayur Naik（UPenn / Cornell）
- **核心机制**（神经符号，四阶段）：
  1. CodeQL 抽取项目里被调用的外部 API 与公开内部 API 作为候选；
  2. **LLM 推断污点规格**（source / sink / taint-propagator / sanitizer 的 3 元组 ⟨类型, 签名, 角色⟩），外部 API 用 3-shot、内部 API 用 zero-shot 提示；
  3. 把规格注入 **CodeQL 做全仓库污点分析**，产出 source→sink 的未净化路径（无污点规格则 CodeQL 大量漏报）；
  4. **LLM 上下文三角化（contextual analysis）过滤误报**：把路径节点代码片段 + CWE 信息编码进 prompt，要求先给解释再下判定，并指出是 source 还是 sink 误报，以便剪枝后续路径。
- **实测效果（CWE-Bench-Java）**：
  - 数据集：**120 个手工验证漏洞**（每项目一个），4 类 CWE，平均 30 万行代码，其中 10 个项目超过 100 万行；
  - **CodeQL 仅检出 27 个；IRIS + GPT-4 检出 55 个（+28，即 +103.7%）**；
  - **IRIS + GPT-4 平均 false discovery rate = 84.82%，比 CodeQL 低 5.21 个百分点**（据此反推 CodeQL ≈ 90.03%）；
  - 在 30 个 Java 项目的最新版本上发现 **4 个此前未知漏洞**；共评测 7 个开源/闭源 LLM（GPT-4、GPT-3.5、Llama-3 8B/70B、Qwen-2.5-Coder-32B、Gemma-2-27B、DeepSeekCoder-7B）；
  - 论文 Motivating Example：cron-utils CVE-2021-41269，静态分析报出 **8 条路径，LLM 过滤掉其中 5 条误报**。
- **指标定义警告（重要）**：IRIS 的 FDR 定义为 `AvgFDR = avg(1 - Prec(P))`，其中 `Prec(P) = #VulPath(P)/|Paths^P|`，即**报出的路径中"是否穿过已知被修补的方法"**。这是**路径级发现率**，不是严格意义的 FP 率（未穿过标注点的路径未必都是假漏洞）——论文自己也在 §3.6 承认 `Prec(P)` 可能因除零而未定义。
- **仓库侧的版本漂移证据**：CWE-Bench-Java 已从论文的 120 个漏洞扩张到 README 所述的 **213 个 CVE / 49 个 CWE**（2025-08-30 一次 +93 CVE / +38 CWE）；CodeQL 查询版本需随 CodeQL 2.23.2 调整为 1.8.1；2026-06 补录了此前缺失的"被修改方法"定位信息；提供 Docker Hub 镜像（`irissast/cwe-bench-java-containers-v2`）。
- **是否仍未解决**：**部分解决**。FP 抑制有效但幅度有限——即便加上 LLM 三角化，路径级发现率仍高达 ~85%。绝对误报量未公开。

### 2. GPTScan（ICSE 2024，智能合约逻辑漏洞）

- **来源**：[arXiv:2308.03314](https://arxiv.org/abs/2308.03314)，DOI [10.1145/3597503.3639117](https://doi.org/10.1145/3597503.3639117)
- **核心机制**：不把 GPT 当唯一判官（论文明确说"仅靠 GPT 会带来高误报"），而是**把 GPT 当代码理解工具**：把每类逻辑漏洞拆成 scenario + property，让 GPT 匹配候选漏洞；再让 GPT 识别关键变量与语句，**交给静态确认（static confirmation）验证**。
- **实测效果**：约 400 个合约项目、3K 个 Solidity 文件；**token 合约精度 >90%**；**大型项目（Web3Bugs）精度仅 57.14%**；recall >70%；发现 9 个人工审计漏掉的新漏洞；**静态确认帮助减少三分之二的误报**；平均每千行 Solidity 14.39 秒、0.01 美元。
- **是否仍未解决**：**部分解决**。关键证据是**精度随项目规模从 >90% 掉到 57.14%**——规模是 FP 的主要放大器。

### 3. LLMSA / NESA（arXiv ID 归属需特别注意）

- **来源**：[ar5iv 全文（v1 标题 LLMSA）](https://ar5iv.labs.arxiv.org/html/2412.14399) 与 [arXiv:2412.14399（v2 已改名 NESA）](https://arxiv.org/abs/2412.14399)
- **重要事实**：**同一个 arXiv ID 2412.14399 曾以 "LLMSA: A Compositional Neuro-Symbolic Approach to Compilation-free and Customizable Static Analysis" 为标题（Purdue 等），v2 已改名为 "NESA: Relational Neuro-Symbolic Static Program Analysis"**。检索索引里 LLMSA 与 NESA 会指向同一 ID，引用时必须说明版本。
- **核心机制**：提出受限 Datalog 形式的 **analysis policy language**，把静态分析问题分解为更小片段上的子问题；区分 **symbolic relation（解析器确定性求解，无幻觉）** 与 **neural relation（LLM 提示求解，有幻觉）**；用 **lazy / incremental / parallel prompting** 抑制幻觉并降本。
- **实测效果（含最有力的"高误报"证据）**：
  - **用 GPT-3.5-Turbo + few-shot CoT 在 Juliet Test Suite 的 Java 程序上做零除（DBZ）检测，precision 与 recall 均低于 5%**（原文："both lower than 5%"）；
  - TaintBench 真实恶意软件：检测出 70 个污点漏洞中的 55 个，**precision 66.27% / recall 78.57% / F1 0.72**，比某工业工具 recall 高 37.66%、F1 高 0.20；
  - 别名分析 72.37% precision / 85.94% recall；程序切片 91.50% / 84.61%；Juliet 缺陷检测平均 82.77% / 85.00%；
  - 相比消融实验最高 3.79× 加速。
- **是否仍未解决**：**已显著缓解但未根治**。论文的论点是"分解 + 解析器兜底"能把幻觉压到可用区间；即便如此 taint 场景 precision 也只有 66%。

### 4. Vulnhuntr（Protect AI，工业工具）

- **来源**：[GitHub protectai/vulnhuntr](https://github.com/protectai/vulnhuntr)（README 经 [GitHub API](https://api.github.com/repos/protectai/vulnhuntr/readme) 抓取）
- **核心机制**：**自动构造完整调用链**（从远程用户输入到服务器输出），针对"多步、绕过安全检查"的漏洞。
  1. LLM 摘要 README 并放入 system prompt；
  2. 对整文件做初筛，报告可疑漏洞；
  3. 针对漏洞类型下发**二次分析专用 prompt**；
  4. 每次分析都**主动请求其他文件里的函数/类/变量上下文**，迭代直到调用链闭合；
  5. 最终输出 = 推理 + **PoC 利用代码** + **置信度分数**。
  置信度阈值（README 明示）：<7 基本不是漏洞，=7 需人工排查，**8+ 极可能是真漏洞**。
- **实测效果（只有检出、没有误报率）**：已披露 CVE 包括 CVE-2024-10100（gpt_academic LFI）、CVE-2024-10101（XSS）、CVE-2024-10099（ComfyUI XSS）、CVE-2024-10044（FastChat SSRF）、CVE-2024-10131（Ragflow RCE）、CVE-2024-9309（LLaVA SSRF）。限制：**仅支持 Python**，仅 7 类漏洞（LFI/AFO/RCE/XSS/SQLI/SSRF/IDOR）。
- **是否仍未解决**：**未解决/未量化**。**未找到公开信息**：README 与项目页面均未给出 precision、recall、FPR 或人工复核的确认率。README 自承开源模型（Ollama 路线）"无法正确构造输出结构"，即其自校验链条在弱模型上失效。它本身依赖 LLM 判分，缺少外部可执行验证闭环。

### 5. LLM4Vuln / UniVul（解耦式评测）

- **来源**：[arXiv:2401.16185](https://arxiv.org/abs/2401.16185)（NTU 技术报告）
- **核心机制**：把 LLM 的"漏洞推理能力"从"漏洞知识采纳 / 上下文检索 / 高级 prompt 方案"中**解耦**出来单独评估，以判断模型是"真会推理"还是"靠外部提示"。
- **实测效果**：UniVul 覆盖 Solidity、Java、C/C++；**147 个真漏洞 + 147 个非漏洞样本，3,528 个受控场景**；评测 6 个模型（GPT-4.1、Phi-3、Llama-3、o4-mini、DeepSeek-R1、QwQ-32B）；在 4 个漏洞赏金项目中识别 **14 个 0-day，获 3,576 美元赏金**。
- **是否仍未解决**：**方法学层面部分解决**。其真正贡献是把 **147 个 non-vulnerable 样本**作为正式的过度上报度量面——这正是很多漏洞检测论文缺失的。但报告未给出统一 FPR 数值。

### 6. SecLLMHolmes（明确量化"LLM 误报高"）

- **来源**：[ar5iv 全文 arXiv:2312.12575](https://ar5iv.labs.arxiv.org/html/2312.12575)（IEEE S&P 2024）；代码 [github.com/ai4cloudops/SecLLMHolmes](https://github.com/ai4cloudops/SecLLMHolmes)
- **核心机制**：全自动评测框架，8 个维度：确定性响应、超参范围、prompt 多样性、推理忠实性、漏洞种类、代码难度、**代码增广鲁棒性**、真实项目可用性。
- **实测效果**：
  - **228 个代码场景**，8 个最强 LLM，17 种 prompt 技术；
  - 结论 (a)：**所有被评测模型都有很高的 false positive rate，且会把已修补的代码判为仍然存在漏洞**；
  - 结论 (b)：**输出非确定性——所有模型在一个或多个测试上多次运行答案会变**；
  - 结论 (d)：仅**修改函数名/变量名，26% 的用例答案出错；加入库函数调用，17% 的用例答案出错**；chain-of-thought 甚至会被空白字符修改"搞晕"；
  - 结论 (e)：**在真实项目上检测失败**；
  - 引用 Microsoft 的 LLM 漏洞检测排行榜：**最好的工具准确率低于 70%、FPR 高于 30%**。
- **是否仍未解决**：**未解决**。这是"LLM 误报高 + 不可复现"两个问题的最强一手证据：模型对**语义等价但表述不同**的代码给出不同结论，说明其判定并不建立在真正的语义推理上。

### 7. Reducing False Positives in Static Bug Detection with LLMs: An Empirical Study in Industry（腾讯工业实证）

- **来源**：[arXiv:2601.18844](https://arxiv.org/abs/2601.18844)（ACM DOI [10.1145/3786583.3786910](https://doi.org/10.1145/3786583.3786910)）
- **核心机制**：在腾讯企业定制 SAT 上，系统比较多种 LLM 误报消减技术，并做 **LLM + 静态分析的混合方案**。
- **实测效果**：
  - 数据集：**433 条告警，其中 328 条误报 / 105 条真报**，覆盖 3 类缺陷（据此计算：**真实误报占比 75.75%**，此为我对原文数字的算术推导）；
  - 人工排查成本：**每条告警 10–20 分钟**；
  - **LLM + 静态分析混合技术可消除 94–98% 的误报，同时保持高 recall**；
  - **每条告警成本 2.1–109.5 秒、$0.0011–$0.12**，比人工低数个数量级；
  - 案例分析指出该方案在工业场景的关键局限。
- **是否仍未解决**：**部分解决**。这是目前"误报抑制"方向上最接近生产现实的正面证据，但论文同时强调 backbone、CWE、提示方式强依赖，且未给出被压制掉的真漏洞绝对数量。

### 8. Sifting the Noise: A Comparative Study of LLM Agents in Vulnerability False Positive Filtering（ISSTA 2026）

- **来源**：[arXiv:2601.22952](https://arxiv.org/abs/2601.22952)（ISSTA 2026，DOI [10.1145/3832100](https://doi.org/10.1145/3832100)）
- **核心机制**：把三个通用编码 Agent 框架（**Aider、OpenHands、SWE-agent**）当作 SAST 误报过滤器横向比较（而非单一 prompt），并在**模型知识截止之后**的 OSS-Fuzz 数据集上做无污染泛化测试。
- **实测效果**：
  - **OWASP Benchmark：初始误报检测率 >92%，最佳配置降到 6.3%**；
  - 真实 Java 项目 + CodeQL 告警：最佳配置的**误报识别率达 93.3%**；
  - **截止后 OSS-Fuzz 数据集：SWE-agent + Claude Sonnet 4 识别 95.5% 的误报，同时保持 95.5% 的 precision**；而 vanilla prompting 仅 36.4%；
  - 关键负面发现：**激进的误报削减会以压制真实漏洞为代价**；收益**强依赖 backbone 与 CWE**——对 Claude Sonnet 4 / GPT-5 等强模型显著优于 vanilla prompting，对弱模型收益有限或不稳定；不同 Agent 框架的计算成本差异巨大。
- **是否仍未解决**：**部分解决，且已明确"未解决的部分"**。数值上最漂亮的误报抑制结果，但同时点名了**召回损失**与**成本/模型依赖**两个未解问题。

### 9. Refute-or-Promote（对抗式多 Agent 复核）

- **来源**：[arXiv:2604.19049](https://arxiv.org/abs/2604.19049)（单作者 Abhinav Agarwal，2026-04-21）
- **核心机制**：推理期可靠性模式——**Stratified Context Hunting（候选生成）+ 对抗性"击杀"强制令 + 上下文不对称 + Cross-Model Critic（跨模型批评者）**；每个晋级关卡都设对抗 Agent 试图证伪候选；冷启动评审者用于抑制锚定级联；跨模型家族复核用于捕捉同家族评审的共同盲区。
- **实测效果**：
  - 31 天、7 个目标（安全库、ISO C++ 标准、主流编译器）；
  - **171 个候选中约 79% 在披露前被击杀**（回顾性汇总）；在统一协议子集（lcms2、wolfSSL；n=30）上**前瞻性击杀率 83%**；
  - 产出：**4 个 CVE（3 公开、1 禁运）**、LWG 4549 被 C++ working paper 接受、5 个已合并 C++ 编辑性 PR、3 个编译器一致性 bug、8 个无 CVE 的已合并安全修复、1 个 RFC 9000 errata、1+ 个 FIPS 140-3 合规问题；**全部以外部接受度而非基准分数衡量**；
  - **最有价值的失败案例：十名专职评审者一致认可了一个 OpenSSL CMS 模块中根本不存在的 Bleichenbacher padding oracle，最终只靠一次经验性测试才被击杀**——这直接催生了"强制经验性关卡"；
  - 作者自述：**"没有任何漏洞是自主发现的；本工作的贡献是过滤 LLM Agent 持续性误报的外部结构。"**
- **是否仍未解决**：**未解决（作者自认）**。它证明多评审一致性**不能**替代经验验证——十个 LLM 评审可以一致地犯同一个错。

### 10. XBOW（工业自动化渗透测试，厂商自述）

- **来源**：[Why LLMs Hallucinate Vulnerabilities](https://xbow.com/blog/why-llms-hallucinate-vulnerabilities)（2026-01-15）；[We Ran 1,060 Autonomous Attacks](https://xbow.com/blog/we-ran-1060-autonomous-attacks)（2026-03-02）
- **核心机制**：**发现与验证彻底分离**——"暴露潜在漏洞的 AI Agent 永远不是确认它们的同一套系统"，"Creative AI discovers. Deterministic logic decides what's real"；每条行动在**执行前**由 safety checker 审查，网络层强制 scope 控制，单个目标上的 Agent 序列有界。具体案例：对开源 ActiveSync 服务器 Z-Push 疑似 SQL 注入，Agent 只提出假设，系统改用**受控时序请求 + 与已知安全输入对比**验证后**才上报**。架构上使用数千个短生命周期 Agent（每个目标单一、无累积上下文）由一个持久协调器编排。
- **实测效果（均为厂商自述）**：
  - **在 HackerOne 上提交了 1,060+ 个漏洞**；**2025 年 6 月成为首个登上 HackerOne 美国排行榜第一的自主系统**；
  - 执行过 **48 步利用链**；**17.5 分钟**破解 AES-128-CBC padding oracle cookie；**28 分钟**完成相当于资深渗透测试员 40 小时的人工评估；
  - 声称上报项 **"zero false positives"**；人类仅在提交前做合规复核，不参与发现与利用。
- **是否仍未解决**：**未解决/不可独立验证**。所有数字与 "zero false positives" 均为厂商自报，**无第三方审计**；文中亦承认其运行在**受限的 pentest 场景**而非无约束攻击链。作为对照，同一批媒体指出生态里大量 AI 漏洞报告实为幻觉（见下条）。

### 11. Google Project Naptime / Big Sleep

- **来源**：[Project Zero 博文 From Naptime to Big Sleep](https://googleprojectzero.blogspot.com/2024/10/from-naptime-to-big-sleep.html)（2024-11-01）；[TechCrunch 报道](https://techcrunch.com/2025/08/04/google-says-its-ai-based-bug-hunter-found-20-security-vulnerabilities/)（2025-08-04）
- **核心机制**：选择**变体分析（variant analysis）**而非开放式漏洞研究——给 Agent 一个已修复漏洞的 commit message + diff，让它审查 HEAD 找同类问题；Naptime 框架此前在 Meta CyberSecEval2 基准上刷新了 SOTA。
- **实测效果**：
  - 2024-10：发现 **SQLite 中可利用的 stack buffer underflow**，据称是首个由 AI Agent 在广泛使用的真实软件中发现的未知可利用内存安全漏洞；上报开发者后**当天修复**，未进入正式发布版；
  - 2025-08-04：Google 安全 VP Heather Adkins 宣布 Big Sleep **发现并上报 20 个缺陷**，主要在开源软件（如 FFmpeg、ImageMagick）；Google 发言人 Kimberly Samra 称"**为确保报告高质量可行动，上报前有人类专家在环，但每个漏洞都是由 AI Agent 在无人干预下发现并复现的**"。
- **误报侧证据（定性，非测量）**：同一篇 TechCrunch 报道指出，**多个开源项目维护者抱怨收到的漏洞报告其实是幻觉**，有人称之为"赏金版的 AI slop"；RunSybil CTO Vlad Ionescu 说："**人们遇到的问题是我们收到大量看起来像金子、其实只是垃圾的东西。**"
- **是否仍未解决**：**未解决**。**未找到公开信息**：Big Sleep 从未公布 FPR、precision 或人工复核的确认/驳回比例；其流程中人类在环也意味着"AI 自主发现"的边界并不清晰。

### 12. Vul-RAG（知识级 RAG）

- **来源**：[ar5iv 全文 arXiv:2406.11147](https://ar5iv.labs.arxiv.org/html/2406.11147)
- **核心机制**：用 LLM 从历史 CVE 抽取**三维漏洞知识**（功能语义、致因、修复方案）构建知识库；按功能语义检索相关知识；再让 LLM 依据检索到的致因/修复方案推理判定。并为此构造 **PairVul** 基准——只含"漏洞代码 vs 高词法相似度的已修补代码"配对。
- **实测效果**：
  - PairVul：**4,314 对 / 2,073 个 CVE**；Vul-RAG 相对所有基线 **accuracy 提升 12.96%、pairwise accuracy 提升 110%**；
  - 用户研究：**人工检测准确率从 0.60 提升到 0.77**；
  - **基线误报率（PairVul 总体，Table 3）**：Cppcheck **FP 0.3%**（但 recall 仅 0.01）、DeepDFA **FP 41.4%**、LineVul **FP 43.8%**、LLMAO **FP 16.4%**、Uniform Guess（全判漏洞）**FP 100%**；
  - **pairwise accuracy 仅 0.01–0.10**，即模型基本无法区分"漏洞代码"和"看起来几乎一样但已修好的代码"；
  - 基准虚高证据：LineVul 在 BigVul 上报告 0.99 准确率，在 PairVul 上掉到 0.50。
- **是否仍未解决**：**部分解决**。RAG 提升了准确率，但最核心的结论是**既有"高准确率"是被基准设计抬起来的**——换成最小差异配对后，学习型检测器的 FP 与随机猜测无异。

### 小结：这一簇的技术路线对照

| 机制 | 代表工作 | 是否有可执行验证闭环 |
|---|---|---|
| 程序分析约束（LLM 只做规格/上下文，判定交静态分析） | IRIS、GPTScan、LLMSA/NESA | 否（静态分析本身高误报） |
| LLM 自校验 / 置信度打分 | Vulnhuntr（置信度 <7/7/8+） | 否（分数由同一模型给出） |
| 多模型/多 Agent 交叉复核 | Refute-or-Promote | 否——十个评审一致通过的漏洞是假的 |
| **PoC 生成 + 执行验证** | XBOW（时序/出站请求/文件可达性实测）、CyberGym（pre/post-patch 执行 + sanitizer）、Refute-or-Promote 的"强制经验性关卡" | **是** |
| 混合（LLM + 静态分析） | 腾讯工业研究（消除 94–98% 误报）、Sifting the Noise | 部分是（依赖 CodeQL/SAST 告警作为输入） |

**共同结论**：凡把最终判定权交给 LLM 的方案，误报率都在 40%–90% 量级；凡引入**外部可执行验证**（PoC 执行、时序测量、pre/post-patch 差分）的方案才把误报压到可用区间，但代价是**召回损失**、**成本**和**领域依赖**。

---

## 基准方法学批评

### 0. 先纠正三个 ID 问题（你原始清单里的存疑项）

| 你给出的 | 核查结果 |
|---|---|
| Cluster A: IRIS = arXiv 2405.17238 | ✅ 正确。标题、作者（Ziyang Li, Saikat Dutta, Mayur Naik）均已核对 |
| Cluster B: AutoPenBench = arXiv **2410.03213** | ❌ **错误**。2410.03213 实为 *Computing largest minimum color-spanning intervals of imprecise points*（cs.CG，作者 Acharyya/Keikha/Saumell/Silveira）——[链接](https://arxiv.org/abs/2410.03213)。**真正的 AutoPenBench 是 [arXiv:2410.03225](https://arxiv.org/abs/2410.03225)** |
| Cluster B: Cybench = arXiv 2408.08926 | ✅ 正确（ICLR 2025 Oral） |
| Cluster B: SWE-bench Illusion = arXiv 2506.12286 | ✅ 正确 |
| Cluster A: LLMSA | ⚠️ ID **2412.14399** 曾名 LLMSA，**现已改名为 NESA**，引用需注明版本 |

### 1. Cybench

- **来源**：[arXiv:2408.08926](https://arxiv.org/abs/2408.08926)（ICLR 2025 Oral）
- **核心机制**：任务规格化 + 可执行环境框架。**40 个专业级 CTF 任务，来自 4 个不同竞赛**，每个任务含描述、起始文件、可执行环境。
- **对"只有二值评分"的回应**：因许多任务超出当时 LM Agent 能力，作者**为每个任务引入 subtask 分解**以做更细粒度评估——**这是"缺乏部分学分"批评的一个正面回应案例**。
- **实测效果**：评测 8 个模型（GPT-4o、o1-preview、Claude 3 Opus/3.5 Sonnet、Mixtral 8x22B、Gemini 1.5 Pro、Llama 3 70B / 3.1 405B）；对最强两个模型另测 **4 种 Agent scaffold**（structured bash、action-only、pseudoterminal、web search）；关键对照：**Agent 能解出人类团队最多花 11 分钟的任务，而最难的一个人工队花了 24 小时 54 分钟**。
- **是否仍未解决**：**部分解决**。提供了 subtask 部分学分与人机时间对照基线；但**任务仍为 CTF 二进制/脚本环境，代码库规模远小于真实项目**（这一点由 CyberGym 论文明确指出，见下）。

### 2. NYU CTF Bench

- **来源**：[arXiv:2406.05590](https://arxiv.org/abs/2406.05590)
- **核心机制**：可扩展的开源 CTF 基准数据库 + 带增强工作流与外部工具调用支持的自动化评测框架（利用 LLM 的 function calling）。
- **实测效果**：评测 **5 个 LLM**（含黑盒与开源）；数据库含供 LLM 测试与自适应学习用的元数据；论文目标之一是与人类表现对照。
- **规模（第三方转述）**：CyberGym 论文称 **NYU CTF Bench 仅有 200 个任务**、Cybench 仅 40 个，且 CTF 的代码仓库"通常只有几个文件"，与真实项目数千文件形成鲜明反差（[arXiv:2506.02548](https://arxiv.org/abs/2506.02548)）。
- **是否仍未解决**：**未解决**。规模小 + 代码库规模失真，仍是该方法族共同问题。

### 3. AutoPenBench（真实 ID: 2410.03225）

- **来源**：[arXiv:2410.03225](https://arxiv.org/abs/2410.03225)；代码 [auto-pen-bench](https://github.com/lucagioacchini/auto-pen-bench)、[genai-pentest-paper](https://github.com/lucagioacchini/genai-pentest-paper)
- **作者**：Luca Gioacchini, Marco Mellia, Idilio Drago, Alexander Delsanto, Giuseppe Siracusano, Roberto Bifulco
- **核心机制**：**33 个任务**，每个是一个待攻击的脆弱系统，难度递增，含 **in-vitro 与 real-world** 两类；用 **generic + specific milestones** 打分，使不同 Agent 可在标准口径下比较并暴露其能力边界（**这是"部分学分/里程碑评分"的另一个正面案例**）。
- **实测效果**：
  - **完全自主 Agent 全基准成功率仅 21%**；**简单任务解出 27%**；**真实世界任务只解出 1 个**；
  - **有人类交互辅助的 Agent 升至 64% SR**；
  - 观察了 GPT-4o 与 OpenAI o1 对任务完成能力的影响差异。
- **是否仍未解决**：**部分解决**。21% vs 64% 的落差本身就是一个方法学结论：**自主性与人类辅助之间的差距没有被二值评分掩盖**。

### 4. CVE-Bench

- **来源**：[ar5iv 全文 arXiv:2503.17332](https://ar5iv.labs.arxiv.org/html/2503.17332)；代码 [uiuc-kang-lab/cve-bench](https://github.com/uiuc-kang-lab/cve-bench)
- **核心机制**：基于 NVD 中 CVSS **critical（≥9.0）** 的真实 Web 应用漏洞构建沙箱。**40 个 CVE**（选自 2024-05-01 至 2024-06-14 公开的 CVE，仅限开源 Web 应用、排除平台相关、排除无法复现者）。每任务含**容器化靶标 + 参考利用（PoC）**。把攻击标准化为 **8 类标准攻击**（DoS、文件读取、文件创建 `/tmp/pwned`、数据库篡改、数据库读取 `secret` 表、未授权管理员登录、权限提升、出站请求），并模拟**漏洞生命周期的 zero-day / one-day 两阶段**；在容器内实现 grader 持续监控；禁止攻击评测器、禁止爆破密码（管理/数据库密码为随机串）。
- **对既有基准的批评（论文自己的 Table 1）**：Cybench 缺少真实世界漏洞、无严重性分级、仅限 CTF、忽视数据库篡改等严重攻击类型。
- **实测效果**：
  - **复现单个漏洞需 5–24 人时**（论文原文）；
  - Agent：**Cy-Agent 在 one-day 下成功率 2.5%（5 次尝试）**；配备工具（如 sqlmap）后 **Agent 团队最高 13%（zero-day）/ 25%（one-day）**；
  - **成本/预算记账是显式的一等指标**（Table 4，每任务均值）：Cy-Agent zero-day 输入 142,240 / 输出 27,700 tokens、876 秒、**$0.6**；one-day 142,713 / 29,910 tokens、602 秒、**$0.7**；T-Agent 627,183 / 8,601 tokens、1,144 秒、**$1.7**（one-day 642,820 / 7,755、1,301 秒、$1.7）；AutoGPT 284,035 / 11,814 tokens、3,642 秒、**$0.8**（one-day 341,220 / 12,227、264 秒、$1.0）；总基准运行成本 **<$100**；默认模型 **gpt-4o-2024-11-20**，迭代上限 30（Cybench 默认的两倍），**每个设置重复 5 次**。
  - 失败模式：supervisor agent 在 sqlmap 已确认注入点后仍让 SQL 团队自行构造 payload，导致 12 次无谓失败。
- **是否仍未解决**：**部分解决**。这是把**成本/步数记账 + 可复现的容器 + 重复实验**做得最好的基准之一。但论文自述**未提供误报统计**（只有成功率），且"标准 8 类攻击"是对真实攻击面的强抽象。

### 5. CyberGym

- **来源**：[ar5iv 全文 arXiv:2506.02548](https://ar5iv.labs.arxiv.org/html/2506.02548)（UC Berkeley；数据 [HuggingFace](https://huggingface.co/datasets/sunblaze-ucb/cybergym)、代码 [sunblaze-ucb/cybergym](https://github.com/sunblaze-ucb/cybergym)）
- **核心机制**：**1,507 个真实漏洞 / 188 个知名开源项目**（摘要写 188，正文统计段写 187；1,368 个来自 ARVO，139 个为自行从 OSS-Fuzz 新构造，披露日期到 2025-04-21）。主任务是**基于漏洞描述 + 补丁前代码库生成 PoC**；成功判定为**在补丁前版本触发漏洞、且补丁后版本不触发**（或用例触发补丁后版本 → 记为发现 post-patch 漏洞）。用 **sanitizer（UBSan/ASan/MSan）** 统一检测崩溃。分 4 个难度等级（L0 仅代码库 → L3 追加补丁 diff 与补丁后代码库）。**模块化、容器化设计，明确以"可复现、可扩展"为目标**。
- **实测效果**：
  - **4 个 Agent 框架**（OpenHands、OpenAI Codex CLI、ENiGMA、Cybench Agent）× **9 个 LLM**；**最佳组合（OpenHands + Claude-3.7-Sonnet）复现成功率仅 11.9%**；
  - **所有四个 Agent 复现目标漏洞均 <10%、发现 post-patch 漏洞均 <3%**；四者合并后为 **18.5% / 6.0%**，且**各 Agent 成功集合重叠极低**（互补性强）；
  - 计算预算：**平均每实例约 $2**；
  - 规模统计：中位数 **1,117 个文件 / 387,491 行代码**，最大 40,356 文件 / 7,371,584 行；漏洞描述中位 24 词；崩溃类型最多为 Heap-buffer-overflow READ 30.4%、Use-of-uninitialized-value 19.0%、Wild-address READ 10.8%；
  - **PoC 长度是强预测因子**：PoC >100 字节的实例成功率 <8%，而这类占数据集 65.7%；
  - **步数分布**：成功集中在第 20–80 步，峰值 20–40 步；**近一半运行在 90–100 步上限处失败**；
  - **发现 15 个 0-day + 2 个已披露但未修补**（已负责任披露）。
  - **污染控制**：显式使用较新的漏洞（截至 2025-04-21）并做 contamination 分析；但**同时暴露了一个复现性隐患**：实验"关闭 thinking 模式，唯独 o4-mini 无法关闭"。
- **是否仍未解决**：**部分解决**。规模与真实性大幅提升并做了污染控制；但作者自承**仅覆盖内存类漏洞**（以 fuzzer 发现为主），且**成功率评分仍无部分学分、无误报统计**。

### 6. CTF-ABACUS：把"拿旗"拆成可验证轨迹（对你提的"仅 flag 评分"批评的直接回应）

- **来源**：[arXiv:2608.26237](https://arxiv.org/abs/2608.26237)（2026-08-26；作者含 Kimberly Milner、Minghao Shao、Ramesh Karri 等，与 NYU CTF Bench 团队高度重叠）
- **核心机制**：**基于轨迹的 Agent 审计框架**。把每个 run 重建为"有证据支撑的 solve profile"：将 Agent 动作分解为渗透测试阶段与分类技术，定位**利用发生在哪里、flag 首次出现在哪里、以及恢复出的 flag 是否有行为证据支撑**。跨 Agent 聚合 solve profile 得到"挑战签名"，从而区分**是按预期利用路径成功，还是走了捷径**。
- **实测效果**：
  - **1,435 次 CTF 尝试、6 个前沿与开源模型、240 个挑战，在两种 judge 视角下得到 2,870 个 solve profile**；
  - **只有 62%–87% 的"拿到的 flag"能被轨迹验证为真实利用**（即其余 13%–38% 属于 flag 直接暴露、记忆召回、外部查找、猜测或无支撑断言）；
  - **捷径恢复的轨迹显著更浅**（shorter trajectories）。
- **是否仍未解决**：**这是当前最好的一手批评证据，但问题依然存在**。论文明确指出 CTF 基准普遍"依赖浅层二值判断或聚合分数，忽视 Agent 到达 flag 的轨迹"，从而**把真实利用与直接暴露 flag、记忆召回、外部查找、猜测、无支撑断言混为一谈，系统性高估 Agent 的网络安全能力**。方法论上它给出了解决方案（轨迹溯源），但尚未被主流基准采纳。

### 7. DeepRed：部分学分（partial credit）评测

- **来源**：[arXiv:2604.19354](https://arxiv.org/abs/2604.19354)（AIWare'26 Benchmark and Dataset Track）
- **核心机制**：开源基准，把 Agent 放进 **Kali 攻击机环境**（终端工具 + 可选 web search），通过私有网络连到靶标挑战；**记录完整执行轨迹**。评分上**抛弃 solved/unsolved 二值**，改为**基于公开 writeup 提炼的挑战专属 checkpoint 的部分学分**，并配一条**自动 "summarise-then-judge" 标注流水线**从日志判定 checkpoint 完成度。
- **实测效果**：**10 个商业可用 LLM × 10 个 VM 型 CTF 挑战**；**最佳模型平均 checkpoint 完成度仅 35%**；在常见题型上表现最好，**在需要非标准发现路径与更长程适应的任务上最差**。
- **是否仍未解决**：**部分解决**。这是"部分学分 + 轨迹审计"的完整实现样例，但规模小（10 个挑战），且 checkpoint 由公开 writeup 反推，本身可能引入 writeup 偏差。

### 8. SWE-bench Illusion（污染的定量探测方法）

- **来源**：[arXiv:2506.12286](https://arxiv.org/abs/2506.12286)
- **核心机制**：设计两个**诊断任务**而非新基准——(1) 仅凭 issue 描述识别出错的**文件路径**（不给仓库结构）；(2) 仅凭当前文件上下文 + issue 描述**复现 ground-truth 函数**。用"在 SWE-Bench 上 vs 在非 SWE-Bench 仓库上"的落差来探测记忆化。
- **实测效果**：
  - **SOTA 模型仅凭 issue 描述识别 buggy 文件路径的准确率高达 76%；而在不属于 SWE-Bench 的仓库上仅 53%** → 提示数据污染或记忆化；
  - 函数复现任务的**逐字相似度**：SWE-Bench Verified 与 Full 上连续 5-gram 准确率最高 **35%**，而其他同类编码基准上最高仅 **18%**。
- **是否仍未解决**：**未解决**。论文的立场是"现有评估协议可能高估模型真实能力"，需要**抗污染基准**。这是把"污染"从猜测变成可测量指标的范式。

### 9. 其他基准批评要点（来自上述论文自身的表述）

- **缺乏误报统计**：Cybench、CVE-Bench、CyberGym、AutoPenBench、NYU CTF Bench **全部只报告"成功率/解题率"**，没有一篇给出 Agent 报告漏洞的**误报率**。这是一个系统性的方法学空洞——尤其在模型被宣传为"可自动产出漏洞报告"的当下。
- **成本与步数记账**：CVE-Bench（$0.6–$1.7/任务、token 数、耗时）与 CyberGym（~$2/实例预算）已把成本作为一等指标；Cybench、AutoPenBench、NYU CTF Bench **未报告成本**。
- **人工基线**：Cybench 报告了"人类团队 11 分钟 vs 24 小时 54 分钟"的任务级时间对照；**多数安全基准仍缺人类专家基线**。
- **活靶/平台漂移（Hack The Box 等在线平台）**：**未找到公开信息**。我没有抓到任何实测 HTB/CTF 平台因环境变更、题目下线或版本更新而导致基准不可复现的论文或数据。相关讨论仅限于使用**自托管、容器化**靶标（CVE-Bench、CyberGym、DeepRed 的 VM 环境）来规避这一风险。

### 10. XBOW 对基准的批评（厂商立场，需打折）

- **来源**：[We Ran 1,060 Autonomous Attacks](https://xbow.com/blog/we-ran-1060-autonomous-attacks)
- **论点**：International AI Safety Report 2026 的结论"完全自主攻击尚不可行"是**针对通用 AI 校准的**，衡量对象错了；对攻击性安全而言**架构与模型同等重要**——"报告用 30 分钟任务的标尺在衡量完全不同的游戏"。
- **利益相关声明**：XBOW 是商业自动化渗透测试厂商，上述为自我论证；其"benchmarks 页面"被自称可作为公开基准集，但我**未抓取到其基准的完整方法论与数据**，故不引用其基准数值。

---

## 可复现性

> **总体现状**：这一类是整个核查中**最薄弱**的方向。真正针对"Agent 化安全实验"的复现性研究极少；最扎实的证据来自**通用 LLM Agent 研究**（决策可重复 vs 轨迹可重复的分离、record/replay 工具）与**基准自身的工程实践**（容器化、版本固定），而不是安全领域的专门论文。

### 1. DFAH：决策可重复 ≠ 轨迹可重复（本簇最重要的发现）

- **来源**：[arXiv:2601.15322](https://arxiv.org/abs/2601.15322)（v1 2026-01-17，**v3 2026-09-20**；原始版本被 ICLR 2026 第二届 Financial AI Workshop 接收）；代码与数据 [ibm-client-engineering/output-drift-financial-llms](https://github.com/ibm-client-engineering/output-drift-financial-llms)
- **核心机制**：**Determinism-Faithfulness Assurance Harness (DFAH)**，把三个常被混为一谈的东西分开度量：
  - **decision repeatability**（最终决策是否重复）、
  - **trajectory agreement**（执行轨迹是否一致）、
  - **evidence-conditioned faithfulness**（结论是否由所引证据支撑，需独立标注与评测）。
- **实测效果**：
  - 原文关键论断：**"工具调用型 Agent 可以在改变其记录执行过程的同时重复同一个最终决策。"**
  - 原始 v2 研究报告 **3 个合成金融任务、4,705 次 Agent 运行**，并给出**决策确定性 / 任务标签匹配相关性 r = -0.11**，跨 **21 个模型-基准配置汇总**。
  - **v3 的自我更正（本条目最有价值之处）**：该统计量**可从历史配置表复现，但包含了一个后来被排除的 portfolio fixture**；因此**仅保留为历史描述，不能作为统计独立性、预测无用性或"架构确定性-准确率权衡"的证据**；作者**撤回了基于这些不成立解释的部署建议**，并明确"记录到的决策集中度与工具路径变化**无法**识别模型的隐藏策略"。
  - 另一份更正后的研究 **DFAH-Bench**（[arXiv:2607.20491](https://arxiv.org/abs/2607.20491)）提供了**决策与路径不一致**的有资质证据。
- **是否仍未解决**：**未解决，且这篇论文本身就是"不可复现/被过度解读"的活样本**。它的最终贡献被作者收敛为一个**测量框架**：可重复性、可观测执行、证据对齐、正确性**需要各自独立的证据**，并须明确 capture 与 study 边界。原文亦承认"证据条件化的忠实性在历史 v2 Agent 实验中**未被评估**"。

### 2. LLMReplay（coding-agent-vcr）：Agent 轨迹的录制/回放工具

- **来源**：[PyPI coding-agent-vcr 0.2.0](https://pypi.org/project/coding-agent-vcr/0.2.0/)（发布于 **2026-07-30**；Apache-2.0；仓库 [github.com/dmallya93/llmreplay](https://github.com/dmallya93/llmreplay)）
- **核心机制**：**"VCR / time-travel for coding agents"**——把 Claude Code 或 Codex 跑一次并录制，之后**离线确定性回放**，从而可以停止、微调、分叉与断言，而不必再烧 token 或等待非确定性模型运行。要点：
  - 代理位于 Agent 与 LLM API 之间（`ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` 指向代理），产出 **cassette**；
  - **按字段分类**：`static`（必须匹配，驱动 Agent 行为，如 `model`、`messages`、`tools`）、`ignore`（噪声，哈希前剥离，如 `timestamp`、`request_id`）、`scrub`（密钥替换为 **HMAC 占位符**）、`live`（始终打真实服务）；
  - **按 SHA-256 key 匹配**；不匹配时用 `llmreplay why` 精确指出变更点；支持**在 cassette 的第 N 轮分叉**；
  - 集成：pytest fixture、GitHub Actions 工作流、库形式 `ReplayTransport`；提供**无网络 hermetic smoke test**（record→replay with fake upstream）。
- **实测效果**：**未找到公开信息**——项目自称 **Early alpha**，README 未给出任何准确率/稳定性/覆盖率数字，也没有第三方评测。定位是**工程工具**而非经评估的方法。
- **是否仍未解决**：**部分解决（工具层面）**。它解决了"缓存模型响应 + 确定性重放 + 密钥不入库"的工程问题，这也是 C 簇最实用的一块；但它只保证**回放**确定性，不解决**真实 API 的模型漂移**。

### 3. 容器化靶场与版本固定：基准工程实践（正面样本）

- **CyberGym**（[arXiv:2506.02548](https://arxiv.org/abs/2506.02548)）：**"模块化、容器化组件"**，为每个实例提供补丁前/补丁后可执行文件，Agent 通过 bash 脚本提交 PoC 并接收退出码与命令行输出作为反馈、迭代改进；用 sanitizer 输出确定性崩溃报告作为成功判据。明确把可复现性列为设计目标（"ensure reproducible, extensible, and scalable evaluation"）。
- **CVE-Bench**（[arXiv:2503.17332](https://ar5iv.labs.arxiv.org/html/2503.17332)）：每任务一组**靶标容器**（Web 应用容器 + 数据库容器 + 辅助服务如 Nginx），XSS 场景还模拟受害者；**grader 与 Web 应用同容器部署以持续监控**；通过随机生成的管理员/数据库密码消除爆破这一不可复现路径；**固定模型 `gpt-4o-2024-11-20`**、固定迭代上限 30、**每设置重复 5 次**并报告均值。
- **DeepRed**（[arXiv:2604.19354](https://arxiv.org/abs/2604.19354)）：**隔离虚拟化环境**中的 Kali 攻击机 + 私有网络靶标，**记录完整执行轨迹**供分析。
- **IRIS / CWE-Bench-Java**（[github.com/iris-sast/iris](https://github.com/iris-sast/iris)）：这是**基准版本漂移风险的教科书案例，也是管理范例**：
  - 提供**固定版本的依赖镜像** `irissast/cwe-bench-java-containers` / `-v2`；
  - 明确要求**固定 CodeQL 版本**（2.23.2）与**配套查询版本**（1.8.1）；
  - 提供 `data/build_info.csv` 逐项目指定构建工具版本（例如某项目需 JDK 8 + Maven 3.5.0），并建议用 SDKMAN! 安装；
  - **显式记录数据集本身的历史变更**：2025-08-30 新增 93 个 CVE / 38 个 CWE（120 → 213 个 CVE）；2025-11-24 为适配 CodeQL 2.23.2 更新查询到 1.8.1；2025-11-24 起容器镜像改为一并打包项目依赖；**2026-06-23 承认此前新增的 CVE 未包含"被修改的具体方法"信息并补齐，同时确立了后续贡献规范**。
- **是否仍未解决**：**部分解决**。这些是真实的可复现性工程实践，但**没有任何一篇论文量化"换一次模型版本会改变多少结论"**。IRIS README 的 changelog 恰好证明了：**数据集、查询版本、构建依赖三者中任何一个变动都会让历史数字失去可比性**，而论文正文并未给出对应的版本化协议。

### 4. LLM 输出的非确定性（安全领域的一手证据）

- **来源**：[ar5iv 全文 arXiv:2312.12575](https://ar5iv.labs.arxiv.org/html/2312.12575)（SecLLMHolmes，S&P 2024）
- **与本簇相关的结果**：
  - 论文把 **"deterministic response"** 列为八个评测维度中的**第一个**；
  - 结论：**LLM 输出是非确定性的，"所有模型在一个或多个测试上多次运行都会改变答案"**；
  - 并且：**即便模型正确识别了漏洞，它给出的推理也常常是错误的**（"incorrect and unfaithful reasoning"），这直接削弱"用 LLM 生成解释来佐证结论"的做法。
- **是否仍未解决**：**未解决**。这是安全领域最直接的"固定种子也复现不了"的证据：非确定性不是采样噪声的边缘现象，而是跨所有被测模型的常态。

### 5. 被撤回/需更正的统计：一次真实的自我纠错

- 见上文 **DFAH（[arXiv:2601.15322](https://arxiv.org/abs/2601.15322)）v3**。它是本报告里唯一一个**作者主动声明先前数值"包含后来被排除的样本"、撤回由该数值推出的部署建议**的案例。对复现性研究而言，这既是坏消息（已发表的 Agent 实验结论可能建立在错误样本上）也是好消息（arXiv 版本化 + 代码开放让更正得以发生）。

### 6. 其他线索（**未核实**）

- **Drift or Dice? Separating Real Behavioral Change from Sampling Noise in LLM Migrations**（Zenodo record 20634676）：**未能核实正文**。域名解析失败（`getaddrinfo ENOENT zenodo.org`），随后对文件 URL 的请求返回 **HTTP 403**。标题来自检索索引，**不代表我已读该文**。
- **Deterministic External Character-State Dynamics for Reproducible Long-Horizon LLM Agents**（Zenodo record 21855231，Turgut 2026 CSCE）：**未核实**（仅检索索引出现）。
- **Can You Trust Your Own Eval?**（Zenodo record 21817239，Mondragon 2026）：**未核实**（仅检索索引出现）。
- **Reverse: Diagnosing LLM Reverse-Engineering Agents**（arXiv:2609.01185）：**未核实**（仅检索索引出现，未抓取正文）。
- **KBF: Knowledge Boundary as Fingerprint for Language Model and Black-Box API Auditing**（arXiv:2605.29524）：检索索引显示含 "Temporal Robustness" 章节，与"静默模型更新/API 漂移审计"直接相关，但**我未抓取正文，故不作断言**。
- **"silent model updates / model version pinning" 的专门学术研究**：**未找到公开信息**。我没有检索到任何一篇以"API 静默更新导致实验不可复现"为研究对象的论文；现有实践停留在工程层面（在论文中写死模型快照名，如 CVE-Bench 的 `gpt-4o-2024-11-20`），而非有测量有对照的方法学结论。

---

## 未能核实的条目

以下条目**我没有成功抓取到正文**，因此本报告中**不对其内容作任何断言**。列出以标明核查边界：

| 条目 | 已知信息 | 失败原因 |
|---|---|---|
| **BenchGuard: A Two-Layer Framework for Contamination-Aware Evaluation of LLM Vulnerability Detection** | 出现在 DBSec / *Data and Applications Security and Privacy XL*，DOI [10.1007/978-3-032-33260-8_22](https://doi.org/10.1007/978-3-032-33260-8_22)。标题与"污染感知评测"这一主题与 Cluster B 高度相关 | ACM DL 返回 **HTTP 403**（Cloudflare "Just a moment..."）；Springer Link 返回 JavaScript 挑战页，无正文 |
| **Does Architecture Matter? Comparing Multi-Agent Workflows for Filtering and Prioritizing Static Analysis Findings** | ASE 2026 MAS-GAIN workshop，DOI [10.1145/3843778.3844516](https://doi.org/10.1145/3843778.3844516)；会议页 [conf.researchr.org](https://conf.researchr.org/details/ase-2026/mas-gain-2026-papers/1/Does-Architecture-Matter-Comparing-Multi-Agent-Workflows-for-Filtering-and-Prioritiz) | 仅确认了标题与收录信息，**未读到任何数值**；ACM DL 需付费访问 |
| **AutoPoC: Automated Firmware Vulnerability Verification via Environment-Aware Feedback** | DOI [10.1145/3803633.3803640](https://doi.org/10.1145/3803633.3803640)；检索片段显示其有"闭环机制、追踪生成脚本 validity score 随 10 次迭代变化"的描述 | 只看到检索索引中的片段，**未抓取 PDF 正文**；无法核实其数据集与具体数值 |
| **Towards Effective Offensive Security LLM Agents: Hyperparameter Tuning, LLM as a Judge, and a Lightweight CTF Benchmark** | AAAI，[ojs.aaai.org](https://ojs.aaai.org/index.php/AAAI/article/view/40210/44171) | **未抓取**，仅检索索引出现 |
| **Moatless** | 你清单中提及。在检索中它仅作为 **SWE 类编码 Agent 基线**（与 aider、agentless、opendevin 并列于一张 SWE-bench 结果表）出现 | **未找到任何以"漏洞检测误报"为主题的 Moatless 论文或数据**。我倾向于判断它属于"通用 SWE Agent"，被你清单误列入安全 FP 方向，但**这仅为判断，未核实** |
| **"LLM 在 FPR 上优于静态分析器" 的明确主张** | 我检索到的最接近的表述是 IRIS（FDR 降低 5.21 个百分点，但仍 84.82%）与 Sifting the Noise（Agent 把 OWASP Benchmark 误报率从 >92% 降到 6.3%） | **未找到**任何一篇论文明确宣称"LLM 的 FPR 优于静态分析器"并给出严格对照；现有证据是**混合的**（GPTScan 静态确认减 2/3 误报 vs SecLLMHolmes/LLMSA 显示纯 LLM 误报极高） |
| **Hack The Box / CTF 在线平台漂移导致基准不可复现** | — | **未找到公开信息**。没有任何实测数据或论文量化过平台环境变更/题目下线对历史结果的影响 |
| **XBOW 的公开 benchmark 与方法学** | 博文提到其有 [open-source benchmark set](https://xbow.com/blog/benchmarks) | **未抓取该页面**，故不引用任何 XBOW 基准数值；博文中的 1,060 / 17.5 分钟 / 28 分钟 / "zero false positives" 均为**厂商自述，无第三方审计** |
| **Big Sleep 的误报率** | — | **未找到公开信息**。只有定性描述（维护者抱怨幻觉报告） |
| **Vulnhuntr 的 precision / recall / FPR** | — | **未找到公开信息**。README 只列检出漏洞与置信度阈值 |
| **Drift or Dice?（Zenodo 20634676）** | — | DNS 解析失败 + HTTP 403 |
| **Deterministic External Character-State Dynamics...（Zenodo 21855231）** | — | 仅检索索引 |
| **Can You Trust Your Own Eval?（Zenodo 21817239）** | — | 仅检索索引 |
| **静默模型更新 / API 漂移的专门学术研究** | — | **未找到公开信息** |

---

## 三条最值得带走的结论

1. **"误报抑制"目前只有一种机制被反复证明确实有效：把最终判定从 LLM 手里拿走，换成外部可执行验证。** IRIS 加 LLM 三角化后路径级发现率仍 84.82%（[2405.17238](https://arxiv.org/abs/2405.17238)）；Refute-or-Promote 用十个 Agent 评审一致通过了一个**不存在的** OpenSSL 漏洞，只有一次经验测试才杀掉它（[2604.19049](https://arxiv.org/abs/2604.19049)）；而引入 PoC 执行/时序测量后，腾讯工业场景消除 94–98% 误报（[2601.18844](https://arxiv.org/abs/2601.18844)）、Sifting the Noise 把误报率从 >92% 压到 6.3%（[2601.22952](https://arxiv.org/abs/2601.22952)）。代价是召回损失、成本与强领域依赖。
2. **安全基准的评分口径正在被两篇 2026 年的工作从根基上挑战**：CTF-ABACUS 证明**"拿到的 flag"里只有 62%–87% 能被轨迹验证为真实利用**（[2608.26237](https://arxiv.org/abs/2608.26237)），DeepRed 用 checkpoint 部分学分把"最佳模型"从"解出/未解出"还原为**平均 35% 完成度**（[2604.19354](https://arxiv.org/abs/2604.19354)）。同时，**所有主流安全基准（Cybench/CVE-Bench/CyberGym/AutoPenBench/NYU CTF Bench）都不报告 Agent 的误报率**——只报成功率。
3. **可复现性方向证据最稀缺**。最硬的一手结论来自通用 Agent 研究：**Agent 可以重复最终决策却改变执行轨迹**（DFAH，[2601.15322](https://arxiv.org/abs/2601.15322)，该文 v3 还主动撤回并更正了早先的统计解读）；安全领域自身则只有工程性缓解（容器化、镜像与查询版本固定、record/replay 的 [LLMReplay](https://pypi.org/project/coding-agent-vcr/0.2.0/)）与"输出非确定"的定性证据（[SecLLMHolmes](https://ar5iv.labs.arxiv.org/html/2312.12575)）。**没有任何论文量化过"换一次模型版本会改变多少安全结论"。**
