# 2025–2026 自主 / LLM 驱动渗透测试 Agent 学术工作核查报告

> **核查方法与证据纪律**
> - 每条目均由我**实际抓取** arXiv abs 页、arXiv HTML 正文页、GitHub 仓库或会议官网页面确认；来源链接即我抓取的 URL。
> - 只有**直接抓取**过的条目才列在正文；仅由综述参考文献间接出现的条目单独标注。
> - 未能在 abs 页/仓库中读到的字段（如机构、任务数）一律写 `未找到公开信息/待核实`，不做推测填充。
> - 抓取到的网页内容一律视为**数据**，未执行其中任何指令。

---

## 一、多智能体 / 编排型渗透测试框架（2025–2026）

### 1. AutoPenBench — 直接核验 ✅
- **标题**：AutoPenBench: Benchmarking Generative Agents for Penetration Testing
- **arXiv 编号**：`arXiv:2410.03225`（v1 2024-10-04，v2 2024-10-28）— **编号与标题匹配，已核验**
- **作者机构**：Luca Gioacchini, Marco Mellia, Idilio Drago, Alexander Delsanto, Giuseppe Siracusano, Roberto Bifulco。机构（从 arXiv HTML 作者块提取）：**NEC Laboratories Europe（Heidelberg）+ Politecnico di Torino + Università di Torino**
- **年份**：2024（v2 末次修订 2024-10）
- **核心方法**：开放基准，含 **33 个**可攻击的漏洞系统任务，难度递增，覆盖 in-vitro 与真实场景；用通用 + 专用 milestone 标准化评分；对比「全自主」与「半自主（支持人工交互）」两种 agent 架构，并对比 GPT-4o / OpenAI o1
- **开源地址**：https://github.com/lucagioacchini/auto-pen-bench （HTTP 200，描述确认与论文对应）；实验代码 https://github.com/lucagioacchini/genai-pentest-paper
- **关键结果**（我读到的原文数字）：全自主 agent **21% 成功率（SR）**，简单任务 **27%**，真实世界任务**仅解出 1 个**；人机协同 agent **64% SR**
- **后续影响**：已成为常用评测基准 —— Pentest-R1（`2508.07382`）在其上报告 24.2%；xOffense（`2509.13021`）同时使用 AutoPenBench 与 AI-Pentest-Benchmark
- **来源**：https://arxiv.org/abs/2410.03225 ｜ https://github.com/lucagioacchini/auto-pen-bench

### 2. Cybench — 直接核验 ✅（用户给的编号正确）
- **标题**：Cybench: A Framework for Evaluating Cybersecurity Capabilities and Risks of Language Models
- **arXiv 编号**：`arXiv:2408.08926`（v1 2024-08-15，v4 2025-04-12）— **编号与标题匹配，已核验**
- **作者机构**：Andy K. Zhang, Neil Perry, Riya Dulepet, Joey Ji, Celeste Menders, … Dan Boneh, Daniel E. Ho, Percy Liang 等。机构：**Stanford University**（从 arXiv HTML 作者块提取确认）
- **年份**：2024 首发，2025-04 最新修订；**ICLR 2025 Oral**（abs 页 Comments 字段确认）
- **核心方法**：**40 个**专业级 CTF 任务，取自 4 场不同 CTF 比赛，强调「近期、有意义、难度跨度大」；每任务含描述、起始文件、可执行命令并观察输出的环境；为超出当前能力的任务引入 **subtask** 分级评估；自建 cybersecurity agent 评测 8 个模型，并对 GPT-4o / Claude 3.5 Sonnet 测试 **4 种 scaffold**（structured bash / action-only / pseudoterminal / web search）
- **开源地址**：https://cybench.github.io → https://github.com/andyzorigin/cybench （站点 HTTP 200 已验证）
- **关键结果**：无 subtask 引导下，Claude 3.5 Sonnet、GPT-4o、OpenAI o1-preview、Claude 3 Opus 可解出「人类团队最多 11 分钟完成」的完整任务；而**最难任务人类团队耗时 24 小时 54 分**
- **后续影响**：被 EnIGMA（`2409.16165`）、Cyber-Zero（`2508.00910`）、Pentest-R1（`2508.07382`）使用；attack-graph 工作（`2609.15523`）用 54 个 CyBench 任务做管线评测
- **来源**：https://arxiv.org/abs/2408.08926 ｜ https://cybench.github.io

### 3. NYU CTF Bench — 直接核验 ✅
- **标题**：NYU CTF Bench: A Scalable Open-Source Benchmark Dataset for Evaluating LLMs in Offensive Security
- **arXiv 编号**：`arXiv:2406.05590`（v1 2024-06-08，v3 2025-02-18）— **已核验**
- **作者**：Minghao Shao, Sofija Jancheska, Meet Udeshi, Brendan Dolan-Gavitt, Haoran Xi, Kimberly Milner, Boyuan Chen, Max Yin, Siddharth Garg, Prashanth Krishnamurthy, Farshad Khorrami, Ramesh Karri, Muhammad Shafique
- **机构**：abs 页未列机构；HTML 作者块未成功提取 → `待核实`（官方仓库组织名为 `NYU-LLM-CTF`，与纽约大学相关，但我不据此断言完整作者机构列表）
- **年份**：2024（v3 2025-02）
- **核心方法**：可扩展开源 CTF 基准数据库，含供 LLM 测试与自适应学习的元数据，汇总多个流行赛事的 CTF 挑战；利用 LLM function calling 构建全自动系统与增强工作流，支持外部工具调用；评测 5 个模型（黑盒 + 开源）
- **任务数量**：abs 页**未给出具体任务数** → 未找到公开信息（不引用二手数字）
- **开源地址**：https://github.com/NYU-LLM-CTF/NYU_CTF_Bench ；自动化框架 https://github.com/NYU-LLM-CTF/llm_ctf_automation （均 HTTP 200 已验证）
- **关键结果**：abs 页仅称通过「与人类表现对比」获得洞见，**未在 abs 页给出具体通过率数字**
- **后续影响**：CRAKEN（`2505.17107`）在其上取得 22%；EnIGMA、Cyber-Zero（`2508.00910`）亦以其为基准之一
- **来源**：https://arxiv.org/abs/2406.05590 ｜ https://github.com/NYU-LLM-CTF/NYU_CTF_Bench

### 4. EnIGMA — 直接核验 ✅
- **标题**：EnIGMA: Interactive Tools Substantially Assist LM Agents in Finding Security Vulnerabilities
- **arXiv 编号**：`arXiv:2409.16165`（v1 2024-09-24，v3 2025-06-05）— **已核验**
- **作者**：Talor Abramovich, Meet Udeshi, Minghao Shao, Kilian Lieret, Haoran Xi, Kimberly Milner, Sofija Jancheska, John Yang, Carlos E. Jimenez, Farshad Khorrami, Prashanth Krishnamurthy, Brendan Dolan-Gavitt, Muhammad Shafique, Karthik Narasimhan, Ramesh Karri, Ofir Press
- **机构**：abs 页未列（HTML 作者块提取仅得空值）→ `待核实`
- **年份**：2024（v3 2025-06）；**ICML 2025**（abs 页 Comments 确认）
- **核心方法**：面向 CTF 的 LM agent；核心贡献是 **Interactive Agent Tools** —— 让 LM agent 首次能运行**交互式终端程序**（如调试器 gdb、服务器连接工具）；在 **390 个 CTF 挑战**、4 个基准上评测；并分析数据泄漏，提出量化方法，识别新现象 **"soliloquizing"**（模型不与环境交互而自行生成幻觉观测）
- **开源地址**：项目官网 https://enigma-agent.com ；代码基于 https://github.com/SWE-agent/SWE-agent/tree/v0.7 ；开发数据集 https://github.com/NYU-LLM-CTF/NYU_CTF_Bench/tree/main/development （均来自 abs 页链接，已验证 SWE-agent 仓库 HTTP 200）
- **关键结果**：新工具与接口显著提升性能，在 **NYU CTF、Intercode-CTF、CyBench** 上取得 SOTA
- **来源**：https://arxiv.org/abs/2409.16165

### 5. CRAKEN — 直接核验 ✅（用户列名正确）
- **标题**：CRAKEN: Cybersecurity LLM Agent with Knowledge-Based Execution
- **arXiv 编号**：`arXiv:2505.17107`（v1 2025-05-21）— **已核验**
- **作者**：Minghao Shao, Haoran Xi, Nanda Rani, Meet Udeshi, Venkata Sai Charan Putrevu, Kimberly Milner, Brendan Dolan-Gavitt, Sandeep Kumar Shukla, Prashanth Krishnamurthy, Farshad Khorrami, Ramesh Karri, Muhammad Shafique
- **机构**：abs 页未列出；HTML 提取失败 → `待核实`（作者群与 NYU CTF Bench 高度重叠）
- **年份**：2025
- **核心方法**：知识驱动 LLM agent 框架，三大机制 —— ①任务关键信息的**上下文化分解**；②**迭代自反思式知识检索**；③**知识提示注入**，把洞见转化为自适应攻击策略；使用 CTF writeup 知识库
- **开源地址**：https://github.com/NYU-LLM-CTF/nyuctf_agents_craken （HTTP 200 已验证）
- **关键结果**：在 **NYU CTF Bench 上准确率 22%**，超越前人工作 3%，取得 SOTA；在 MITRE ATT&CK 技术评测中比前人**多解出 25–30% 的技术**
- **来源**：https://arxiv.org/abs/2505.17107

### 6. CyberGym — 直接核验 ✅（用户列名正确）
- **标题**：CyberGym: Evaluating AI Agents' Real-World Cybersecurity Capabilities at Scale
- **arXiv 编号**：`arXiv:2506.02548`（v1 2025-06-03，v2 2025-10-08，v3 2026-03-24）— **已核验**
- **作者**：Zhun Wang, Tianneng Shi, Jingxuan He, Matthew Cai, Jialin Zhang, Dawn Song
- **机构**：**University of California, Berkeley**（arXiv HTML 作者块确认）
- **年份**：2025（持续修订至 2026-03）
- **核心方法**：大规模基准，含 **1,507 个真实漏洞、188 个软件项目**；主要任务是**仅给定漏洞文字描述 + 对应代码库，生成可复现该漏洞的 PoC 测试**；可按不同漏洞分析设置调节
- **开源地址**：https://github.com/sunblaze-ucb/cybergym （HTTP 200，描述与论文一致）
- **关键结果**：即使最佳组合也**仅约 20% 成功率**；此外发现 **34 个 0-day 漏洞**与 **18 个历史上不完整的补丁**
- **后续影响**：成为 2025–2026 年最具影响力的大规模安全 agent 基准之一，后续出现扩展版 CyberGym-E2E（`arXiv:2606.04460`，由我抓取的综述 `2607.02605` 参考文献确认，未直接抓取其 abs 页）
- **来源**：https://arxiv.org/abs/2506.02548 ｜ https://github.com/sunblaze-ucb/cybergym

### 7. PentestAgent — 直接核验 ✅
- **标题**：PentestAgent: Incorporating LLM Agents to Automated Penetration Testing
- **arXiv 编号**：`arXiv:2411.05185`（v1 2024-11-07，v3 2025-05-29）— **已核验**
- **作者**：Xiangmin Shen, Lingzhi Wang, Zhenyuan Li, Yan Chen, Wencheng Zhao, Dawei Sun, Jiashui Wang, Wei Ruan
- **机构**：abs 页未列，HTML 提取失败 → `待核实`
- **年份**：2024（v3 2025-05）；**AsiaCCS 2025**（abs 页 Comments 确认）
- **核心方法**：LLM 自动化渗透测试框架；用 **RAG** 增强渗透测试知识；**多智能体协作**自动化情报收集、漏洞分析、利用三个阶段；以渗透任务图（见 VulnBot 的 PTG 思路类似）组织流程
- **开源地址**：https://github.com/nbshenxm/pentest-agent （HTTP 200，描述与论文一致）；论文 DOI 10.1145/3708821.3733882
- **注意**：另有同名但**无关**项目 https://github.com/GH05TCREW/pentestagent （黑盒安全测试 agent 框架，非本论文）
- **关键结果**：abs 页称「在综合基准上展现更优的任务完成度与整体效率」，**未在 abs 页给出具体数值**
- **来源**：https://arxiv.org/abs/2411.05185 ｜ https://github.com/nbshenxm/pentest-agent

### 8. VulnBot — 直接核验 ✅
- **标题**：VulnBot: Autonomous Penetration Testing for A Multi-Agent Collaborative Framework
- **arXiv 编号**：`arXiv:2501.13411`（v1 2025-01-23）— **已核验**
- **作者**：He Kong, Die Hu, Jingguo Ge, Liangxiong Li, Tong Li, Bingzhen Wu
- **机构**：**State Key Laboratory of Cyberspace Security Defense, Institute of Information Engineering, Chinese Academy of Sciences；School of Cyber Security, University of Chinese Academy of Sciences**（arXiv HTML 作者块确认）
- **年份**：2025
- **核心方法**：多智能体模拟人类渗透测试团队协作；把任务分解为**侦察、扫描、利用**三阶段，由**渗透任务图（Penetration Task Graph, PTG）**引导逻辑执行；关键设计含角色专门化、渗透路径规划、智能体间通信、生成式渗透行为
- **开源地址**：未在 abs 页给出 → `未找到公开信息`（README 未在抓取范围内）
- **关键结果**：abs 页称在自动化渗透测试中优于 GPT-4、Llama3 等基线，**具体数值未在 abs 页读到**
- **来源**：https://arxiv.org/abs/2501.13411

### 9. HPTSA — 直接核验 ✅（用户给的 arXiv 编号 **2406.01637 正确**）
- **标题**：Teams of LLM Agents can Exploit Zero-Day Vulnerabilities
- **arXiv 编号**：`arXiv:2406.01637` — **由官方仓库 README 明确标注对应此编号，且与 EACL 2026 正式版一致，已核验**
- **作者**：Yuxuan Zhu, Antony Kellermann, Akul Gupta, Philip Li, Richard Fang, Rohan Bindu, Daniel Kang
- **机构**：GitHub 组织 `uiuc-kang-lab`（伊利诺伊大学厄巴纳-香槟分校 Daniel Kang 实验室）
- **年份**：2024 预印本；**EACL 2026 正式发表**（Proceedings of EACL 2026, Vol.1 Long Papers, pp. 23–35, Rabat, Morocco; DOI 10.18653/v1/2026.eacl-long.2）
- **核心方法**：**HPTSA** —— 规划（supervisor）智能体先探索系统，决定调用哪些**专门化子智能体**，解决单独 agent 在「尝试多种漏洞」时的长期规划与探索问题。官方 README 明确子智能体按漏洞类别分工：**General、SQL、CSRF、SSTI、XSS、ZAP**；子智能体运行结果被摘要后回传给 supervisor 以避免重复工作、提升覆盖；系统基于 OpenAI Agents SDK 构建
- **开源地址**：https://github.com/uiuc-kang-lab/HPTSA （HTTP 200，README 已抓取）
- **关键结果**（原文）：构建 **14 个真实漏洞**的基准，agent 团队相比先前 agent 框架**提升最高 4.3 倍**
- **后续影响**：同实验室（Daniel Kang 组）后续产出 CVE-Bench（`2503.17332`）
- **来源**：https://aclanthology.org/2026.eacl-long.2/ ｜ https://raw.githubusercontent.com/uiuc-kang-lab/HPTSA/main/README.md

### 10. AutoPentester — 直接核验 ✅（注意：与 "AutoPentest" 是**两个不同工作**）
- **标题**：AutoPentester: An LLM Agent-based Framework for Automated Pentesting
- **arXiv 编号**：`arXiv:2510.05605`（v1 2025-10-07）— **已核验**
- **作者**：Yasod Ginige, Akila Niroshan, Sajal Jain, Suranga Seneviratne
- **机构**：abs 页未列 → `待核实`（Suranga Seneviratne 与 UNSW Sydney 相关，但我不据此断言）
- **年份**：2025；**IEEE TrustCom 2025**（abs 页 Comments 确认）
- **核心方法**：给定目标 IP 后自动迭代执行渗透步骤，调用常见安全工具；基于上一轮工具输出**动态生成攻击策略**，模仿人类渗透测试者流程；对比 SOTA 的 PentestGPT
- **开源地址**：abs 页未给出 → `未找到公开信息`（存在同名论文页 https://huggingface.co/papers/2510.05605）
- **关键结果**：相比 PentestGPT **子任务完成率提升 27.0%**、**（截断前读到）多 39.5% 的…**（原文 abs 在该处被截断，未读完整表述，不做补全）
- **来源**：https://arxiv.org/abs/2510.05605

### 11. AutoPentest（另一工作）— 直接核验 ✅
- **标题**：AutoPentest: Enhancing Vulnerability Management With Autonomous LLM Agents
- **arXiv 编号**：`arXiv:2505.10321` — **已核验**
- **作者**：Julius Henke（单一作者）
- **机构**：abs 页未列 → `待核实`
- **年份**：2025
- **核心方法**：基于 **GPT-4o + LangChain** 的黑盒渗透测试应用，高自主度，可执行复杂多步任务，外挂工具与知识库；含对相关工作的综述，指出最佳实践与常见评测缺陷
- **开源地址**：abs 页 Comments 给出实现链接（未逐个抓取）→ `未找到公开信息`
- **关键结果**：在 3 台 Hack The Box (HTB) 机器上，AutoPentest 与「手动使用 ChatGPT-4o 界面」基线**都只能完成 15–25% 的子任务**，AutoPentest 略优
- **来源**：https://arxiv.org/abs/2505.10321

### 12. xOffense — 直接核验 ✅
- **标题**：xOffense: An Autonomous Multi-Agent Framework for Penetration Testing with Domain-Adapted Large Language Models
- **arXiv 编号**：`arXiv:2509.13021`（v1 2025-09-16，2026-04-27 修订）— **已核验**
- **作者**：Phung Duc Luong, Le Tran Gia Bao, Nguyen Vu Khai Tam, Dong Huu Nguyen Khoa, Nguyen Huu Quyen, Van-Hau Pham, Phan The Duy
- **机构**：abs 页未列 → `待核实`
- **年份**：2025（2026-04 修订）
- **核心方法**：微调中型开源模型 **Qwen3-32B** 驱动推理；按**侦察 / 漏洞扫描 / 利用**分配专门 agent，编排层协调各阶段；用 Chain-of-Thought 渗透测试数据微调，以生成精确工具命令并保持多步推理一致性
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：在 **AutoPenBench 与 AI-Pentest-Benchmark** 两个基准上评测（abs 在结论处截断，未读到具体数字）
- **来源**：https://arxiv.org/abs/2509.13021

---

## 二、GraphRAG / 攻击图 / 知识图谱增强的渗透测试 Agent

> **重要结论（诚实报告）**：以 "GraphRAG penetration testing" 为主题的**直接论文我没有找到**。arXiv 检索中同时包含这些词的查询返回 0 结果。该方向上真正存在的是三类**相邻**工作：**符号攻击图（MulVAL）**、**意图/事实 DAG 状态外化**、**知识图谱接地的评测**。

### 1. 攻击图自动化构建（MulVAL 神经-符号）— 直接核验 ✅
- **标题**：Automating Attack Graph Construction for Agentic Pentesting. Towards Neuro-Symbolic Vulnerability Hunting
- **arXiv 编号**：`arXiv:2609.15523`（v1 2026-09-14）— **已核验**
- **作者**：Oliver Stevanovic, Jasmin Wachter
- **机构**：收录于 **ESORICS 2026 workshops**（Springer Nature Switzerland AG，eds. D. Hitaj 等）
- **年份**：2026
- **核心方法**：解决「符号攻击图框架（MulVAL）与当代扫描器/agent 管线互操作」问题。半自动管线把 **Trivy、Semgrep、Nmap** 的发现解析为 **MulVAL 谓词**，并用 LLM 辅助构建领域专用的 **Datalog 规则**，把「扫描器可检测的证据」链接到「攻击技术」；再由 **MulVAL/XSB 做符号推理**生成结构化攻击路径。在 agentic 管线（Hybrid Reasoner）中评测
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**（原文）：在 **CyBench 的 54 个 Web CTF 任务**上评测攻击图构建基础设施；**每个任务都至少产生一个可达目标的图**；平均真值漏洞覆盖率 **53.7%**，其中 **51.9% 达到完全覆盖**；**噪声路径率均值 83.9%**；端到端中位耗时 **24.9 秒**（其中 MulVAL 推理 2.7 秒）。作者明确声明**不评测下游 agent 的性能**
- **来源**：https://arxiv.org/abs/2609.15523

### 2. Intentest — 意图图引导的长期状态外化 — 直接核验 ✅
- **标题**：Staying on the Attack Path: Structured State for Long-Horizon Automated Penetration Testing
- **arXiv 编号**：`arXiv:2609.07344`（v1 2026-09-07，v2 2026-09-18）— **已核验**
- **作者**：Weizhe Wang, Yitong Zhang, Yao Zhang, Xiaoqiang Di, Zhigang Li, Bin Wu, Guangquan Xu
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：针对长周期安全任务中的**上下文遗忘**与**意图漂移**（早期关键事实与因果链丢失、agent 陷入无目的重复探索），提出 **Intentest**：把长期状态从 LLM 上下文窗口**外化到一个持久化的「事实-意图有向无环图（DAG）」**。已验证的网络状态存为**不可变事实节点**，探索方向被约束为**受前驱事实约束的意图边**，从而显著减少无效状态转移。三层架构：事实-意图映射层维护全局状态、任务调度与分配层通过两阶段降级恢复保证执行稳定性
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：abs 在评测结论处被截断，**具体数字未读到**
- **来源**：https://arxiv.org/abs/2609.07344

### 3. 知识图谱接地的 CTF Agent 评测 — 直接核验 ✅
- **标题**：Towards Knowledge Graph-Grounded Evaluation of Agentic LLMs on Cybersecurity Capture-the-Flag Challenges
- **编号**：**非 arXiv**；ACL Anthology ID `2026.kallm-1.15`
- **作者**：Daniel Schlör, Marius Bohn, Maximilian Wolf, Kevin Bergner, Christian Goldschmied, Andreas Hotho
- **机构**：**University of Würzburg**（论文 PDF 托管于 uni-wuerzburg.de 数据科学组页面）
- **年份**：2026
- **发表处**：Proceedings of the **Knowledge Graphs and Large Language Models Workshop (KG-LLM) @ LREC26**
- **核心方法**：用知识图谱作为 CTF 场景下 agentic LLM 评测的接地结构（abs 摘要未能从页面提取，**详细方法待核实**）
- **开源地址**：未找到公开信息
- **来源**：https://aclanthology.org/2026.kallm-1.15/

### 4. 检索增强知识用于渗透 agent（Topic 2/3 交叉）— 直接核验 ✅
- **标题**：What Makes a Good LLM Agent for Real-world Penetration Testing?
- **arXiv 编号**：`arXiv:2602.17622`（v1 2026-02-19）— **已核验**
- **作者**：Gelei Deng, Yi Liu, Yuekang Li, Ruozhao Yang, Xiaofei Xie, Jie Zhang, Han Qiu, Tianwei Zhang
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：分析 **28 个** LLM 渗透测试系统，并在 3 个复杂度递增的基准上评测 5 个代表性实现。提出两类失败模式：**Type A**（工具缺失、提示不当等能力缺口，工程可解）与 **Type B**（无论工具如何都持续的规划与状态管理缺陷）。指出 Type B 的共同根因是 agent **缺乏实时任务难度估计**，导致努力错配、过度投入低价值分支、上下文耗尽。据此提出 **Excalibur**：**Tool and Skill Layer**（类型化接口 + **检索增强知识**消除 Type A 失败）+ **Task Difficulty Assessment (TDA)** 机制（从四个可测维度估计可处理性）
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：abs 在 TDA 四维度处被截断，**具体数值未读到**
- **来源**：https://arxiv.org/abs/2602.17622

### 5. 相关但主题不同：GraphRAG **自身**的图抽取攻击 — 直接核验（via 检索页，未抓 abs）
- **标题**：Query-Efficient Agentic Graph Extraction Attacks on GraphRAG Systems
- **arXiv 编号**：`arXiv:2601.14662`（v1 2026-01-21）；另有 ACL 2026 Long Paper 版本 `2026.acl-long.727`
- **年份**：2026
- **说明**：这是**攻击 GraphRAG**（窃取知识图谱）的工作，**不是**「用 GraphRAG 做渗透测试」。列出以避免同名混淆。abs 页我未直接抓取，仅从检索结果与检索到的 arXiv HTML 链接确认其存在 → **部分核验**
- **来源**：https://arxiv.org/abs/2601.14662

### 6. 未能核验为 arXiv 的相邻工作（仅提及，不背书）
- **PTFusion: LLM-driven context-aware knowledge fusion for web penetration testing** —— 期刊 Information Fusion, Vol.127（DOI 10.1016/j.inffus.2025.103731），**非 arXiv**，我未抓取原文 → `内容待核实`
- **Trinity: A Neuro-Symbolic Multi-Agent Framework for Stateful Network Penetration Testing** —— IEEE Xplore document 11507673，**非 arXiv**，我未抓取原文 → `内容待核实`

---

## 三、记忆机制与经验复用（含自演化 / 跨任务技能库）

### 1. Co-RedTeam — 直接核验 ✅（本主题最核心）
- **标题**：Co-RedTeam: Orchestrated Security Discovery and Exploitation with LLM Agents
- **arXiv 编号**：`arXiv:2602.02164`（v1 2026-02-02，v2 2026-02-03）— **已核验**
- **作者**：Pengfei He, Ash Fox, Lesly Miculicich, Stefan Friedli, Daniel Fabian, Burak Gokturk, Jiliang Tang, Chen-Yu Lee, Tomas Pfister, Long T. Le
- **机构**：abs 页未列 → `待核实`（作者群含 Google Cloud AI Research 与 MSU 常见署名者，但我不据此断言）
- **年份**：2026
- **核心方法**：安全感知多智能体框架，模拟真实红队工作流，整合：**安全领域知识 + 代码感知分析 + 执行接地的迭代推理 + 长期记忆**。把漏洞分析分解为协调的**发现**与**利用**两阶段，agent 基于**真实执行反馈**规划、执行、验证、精炼动作，并**从既往轨迹中学习**
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**（原文）：跨多种骨干模型一致优于强基线；**漏洞利用成功率 >60%**；**漏洞检测绝对提升 >10%**。消融与迭代研究确认**执行反馈、结构化交互、记忆**对构建稳健可泛化安全 agent 的关键作用
- **后续影响**：已作为 **ICML 2026 poster** 收录（https://icml.cc/virtual/2026/poster/60747）
- **来源**：https://arxiv.org/abs/2602.02164

### 2. TermiAgent / TermiBench — 记忆激活机制 — 直接核验 ✅
- **标题**：Shell or Nothing: Real-World Benchmarks and Memory-Activated Agents for Automated Penetration Testing
- **arXiv 编号**：`arXiv:2509.09207`（v1 2025-09-11，v2 2025-09-15）— **已核验**
- **作者**：Wuyuao Mai, Geng Hong, Qi Liu, Jinsong Chen, Jiarun Dai, Xudong Pan, Yuan Zhang, Min Yang
- **机构**：**Fudan University（复旦）+ Shanghai Innovation Institute, Shanghai, China**（arXiv HTML 作者块确认）
- **年份**：2025
- **核心方法**：指出既有评测依赖**过度简化的 CTF 设定**（内嵌先验知识、降低复杂度），导致性能估计严重偏离实战。提出 **TermiBench** —— 首个面向 agent 的**真实世界**渗透基准，目标从「找 flag」转为「**取得完整系统控制**」。并针对长上下文遗忘提出 **TermiAgent**，含 **Located Memory Activation（定位式记忆激活）** 机制
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：基准含 **510 台主机、25 种服务、30 个 CVE**；作者发现**现有系统在真实条件下几乎拿不到系统 shell**
- **来源**：https://arxiv.org/abs/2509.09207

### 3. APT-Agent — 命令级记忆架构 — 直接核验 ✅
- **标题**：APT-Agent: Automated Penetration Testing using Large Language Models
- **arXiv 编号**：`arXiv:2605.24949`（v1 2026-05-24）— **已核验**
- **作者机构**：William Guanting Li (1), Alsharif Abuadbba (2), Kristen Moore (2), Dan Dongseong Kim (1) — **(1) University of Queensland, (2) CSIRO Data61**（abs 页作者机构字段直接给出，**已核验**）
- **年份**：2026
- **核心方法**：针对两个痛点 —— **技术实体幻觉**与**长期上下文记忆不足**。提出全自动 LLM 渗透框架，系统编排**侦察、利用、外泄**；含**混合纠错模块**（恢复幻觉命令）与**命令专用记忆架构**（在多步攻击序列中保持操作上下文）
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：在 **Metasploitable 2** 上针对 7 个易受攻击服务（覆盖 Web、数据库、网络协议）评测：**端到端利用成功率 84.29%**，对比 **Script Kiddie 48.57%** 与 **PentestGPT 18.57%**（同等条件）
- **来源**：https://arxiv.org/abs/2605.24949

### 4. ExpeRepair —— 用户类比的那篇「双记忆」工作 — 直接核验 ✅
- **标题**：ExpeRepair: Dual-Memory Enhanced LLM-based Repository-Level Program Repair（abs 页标题大写为 `EXPEREPAIR`）
- **arXiv 编号**：`arXiv:2506.10484`（v1 2025-06-12，v2 2026-05-08）— **已核验**
- **作者**：Fangwen Mu, Junjie Wang, Lin Shi, Song Wang, Shoubin Li, Qing Wang
- **机构**：abs 页未列 → `待核实`
- **年份**：2025（v2 2026-05）；**已被 FSE 2026 接收**（abs 页 Comments 确认）
- **核心方法**：受人类认知**双记忆系统**启发 —— **情景记忆（episodic）存储具体修复示范**，**语义记忆（semantic）编码抽象反思洞见**；推理时同时检索情景示范与高层洞见，并通过**动态提示组合**替代静态提示
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：abs 摘要未给出具体数字 → 未读到
- **说明**：这是**软件修复**领域的工作，**不是**渗透测试 agent。用户所述「类比 ExpeRepair」的迁移在安全领域已由 Co-RedTeam（长期记忆 + 经验复用）与 TermiAgent（记忆激活）体现
- **来源**：https://arxiv.org/abs/2506.10484

### 5. 自演化技能库的安全风险 — 直接核验 ✅
- **标题**：Practice Makes Unsafe: Skill Misevolution in Self-Improving LLM Agents
- **arXiv 编号**：`arXiv:2608.12851`（v1 2026-08-13，v2 2026-10-07）— **已核验**
- **作者**：Xutao Mao, Liangjie Zhao, Xiang Zheng, Cong Wang
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：提出失败模式 **skill misevolution（技能误演化）** —— agent 把过往任务经验存为可复用技能时，若完成过不安全任务，**不安全流程会被固化进本身有用的技能**，后续良性任务在原始不安全指令已消失后**重演危害**。构建 **SkillMisevo-Gym**（清空每个任务会话但保留技能库，使各步骤可分别检验）与 **SkillMisevo-Bench**（**525 个任务、25 个 episode**，每 episode 交替恶意与相关良性任务，其后在新会话中进行 3 个良性任务）。提出 **SafeEvolve**（技能写入时与后续检索时双重检查）
- **关键结果**：**21 种 agent × 演化方法组合中，全部都会写入不安全技能，15 种把危害带入新会话**；技能演化在 **15 种组合中提升良性效用**，但在 **17 种组合中同时提升恶意任务危害** —— 因此「仅按效用排名」会掩盖该风险
- **安全含义**：对**自主渗透测试 agent 的经验复用 / 技能库**设计是直接的风险警示
- **来源**：https://arxiv.org/abs/2608.12851

---

## 四、安全 Agent 的「世界模型」

> **重要结论（诚实报告）**：我**没有找到**「安全 agent 学习目标网络环境模型 / 世界模型用于渗透」的直接论文。arXiv 检索该主题返回的是**相邻但不同**的工作。我抓取的 81 篇论文综述（`2607.02605`）全文对其 HTML 做关键词检索，**"world model" 出现 0 次** —— 说明该方向尚未进入渗透测试 agent 主流文献。

### 1. 世界模型本身的安全性风险（含终端 agent 攻击）— 直接核验 ✅
- **标题**：False Prophets: On the Security of World Models in Agentic Systems
- **arXiv 编号**：`arXiv:2607.23147`（v1 2026-07-25，v2 2026-10-01）— **已核验**
- **作者**：Erik Imgrund, Anna Wimbauer, Klim Kireev, Konrad Rieck
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：指出 agent 需预测动作结果，近期研究用专门训练的**环境模拟器（世界模型）**增强预测能力；但世界模型也会**误导 agent 执行有害动作**。发现一系列**世界模型特有漏洞**，可在**终端类 agent**中被利用以执行恶意代码或窃取敏感数据。引入面向**文本世界模型**的安全基准数据集。论证部分风险是**近似世界建模内在固有**的
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**（原文）：攻击者可以**高达 95% 的成功率**在 agentic 管线中诱发误预测，可能导致非预期命令执行、拒绝服务、钱包资产流失与隐私信息提取
- **来源**：https://arxiv.org/abs/2607.23147

### 2. 世界模型的广泛风险综述 — 直接核验 ✅
- **标题**：Safety, Security, and Cognitive Risks in World Models
- **arXiv 编号**：`arXiv:2604.01346`（v1 2026-04-01，v2 2026-04-06）— **已核验**
- **作者**：Manoj Parmar（单一作者）
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：综述世界模型图景；给出 **trajectory persistence** 与 **representational risk** 的形式化定义；提出**五类攻击者分类法**；构建融合 **MITRE ATLAS** 与 **OWASP LLM Top 10** 的统一威胁模型；在 **GRU / RSSM / DreamerV3** 架构上给出轨迹持久对抗攻击的实证 PoC
- **关键结果**：abs 未给出量化数字；贡献为分类法、形式化定义与 PoC
- **来源**：https://arxiv.org/abs/2604.01346

### 3. 最接近「网络环境模型」的实证工作：跨网络泛化 — 直接核验 ✅
- **标题**：Evaluating Generalization Mechanisms in Autonomous Cyber Attack Agents
- **arXiv 编号**：`arXiv:2603.10041`（v1 2026-03-06）— **已核验**
- **作者**：Ondřej Lukáš, Jihoon Shin, Emilia Rivas, Diego Forni, Maria Rigaki, Carlos Catania, Aritran Piplai, Christopher Kiekintveld, Sebastian Garcia
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：隔离出一个最小但根本的分布偏移 —— **固定企业场景中未见过的 主机/子网 IP 重分配**，在 **NetSecGame** 环境中评测攻击者泛化：在 5 个 IP 段变体上训练、在第 6 个未见变体上测试，仅元学习 agent 允许测试时适应。比较三类 agent（**传统 RL / 适应型 agent / LLM agent**），用基于动作分布的**行为与 XAI 分析**定位失败模式
- **关键结果**（原文）：部分适应方法表现出部分迁移，但在未见重分配下**显著退化**，说明**即便只是地址空间变化也会打断长周期攻击策略**；在作者的评测协议与 agent 特定假设下，**提示驱动的预训练 LLM agent 在留出重分配上成功率最高**，代价是推理算力上升、透明度下降，以及重复/无效动作循环等实际失败模式
- **说明**：这是我能找到的**最接近「agent 是否习得环境/网络模型」的可验证实证**，但其研究对象是**泛化能力**而非显式世界模型
- **来源**：https://arxiv.org/abs/2603.10041

---

## 五、RL 训练的安全 Agent

### 1. Pentest-R1 — 两阶段 RL — 直接核验 ✅
- **标题**：Pentest-R1: Towards Autonomous Penetration Testing Reasoning Optimized via Two-Stage Reinforcement Learning
- **arXiv 编号**：`arXiv:2508.07382`（v1 2025-08-10，v2 2025-10-29）— **已核验**
- **作者**：He Kong, Die Hu, Jingguo Ge, Liangxiong Li, Hui Li, Tong Li
- **机构**：abs 页未列 → `待核实`（一作与 VulnBot `2501.13411` 相同，同属中科院信工所方向）
- **年份**：2025
- **核心方法**：两阶段 RL 管线 —— ①构建 **500+ 真实世界多步 walkthrough** 数据集，用于**离线 RL** 注入基础攻击逻辑；②在**交互式 CTF 环境**中用**在线 RL** 微调，让模型直接从环境反馈中学习**错误自纠正**与自适应策略
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**（原文）：在 **AutoPenBench 上 24.2% 成功率**，超越多数 SOTA 模型，**仅次于 Gemini 2.5 Flash**；在 **Cybench 上无引导任务 15.0% 成功率**，**创开源 LLM 的新 SOTA**，并匹配顶级专有模型表现
- **来源**：https://arxiv.org/abs/2508.07382

### 2. PrivEsc-LLM 4B — 可验证奖励的后训练 — 直接核验 ✅
- **标题**：Towards Reliable Local Security Agents: Verifiable Post-Training for Linux Privilege Escalation
- **arXiv 编号**：`arXiv:2603.17673`（v1 2026-03-18，v2 2026-07-03）— **已核验**
- **作者**：Philipp Normann, Andreas Happe, Jürgen Cito, Daniel Arp
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：动机是主流系统闭源、云端、难以复现或不适用于敏感代码。提出**两阶段后训练配方**把小型本地模型变成安全 agent。以 **Linux 提权**为代表性设定（可自动验证 + 需要多步交互式推理）。缓解数据泄漏的实验设置下，对 **4B 小模型**：①在过程化提权环境的轨迹上做**监督微调**；②再用**可验证奖励的强化学习（RLVR）**训练
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**（原文）：在 **12 个 Linux 提权场景的留出基准**上，在 **20 轮交互**的紧张预算下监督微调**使基线成功率翻倍**；随后 RL 训练把 **PrivEsc-LLM 4B 提升到 93.3% 成功率**
- **来源**：https://arxiv.org/abs/2603.17673

### 3. Cyber-Zero — 无运行时轨迹合成 — 直接核验 ✅
- **标题**：Cyber-Zero: Training Cybersecurity Agents without Runtime
- **arXiv 编号**：`arXiv:2508.00910`（v1 2025-07-29，v2 2025-08-25）— **已核验**
- **作者**：Terry Yue Zhuo, Dingmin Wang, Hantian Ding, Varun Kumar, Zijian Wang
- **机构**：abs 页未列 → `待核实`
- **年份**：2025（另有 **ICLR 2026** 版本，见 proceedings.iclr.cc，由检索确认；我未抓取该页 → 部分核验）
- **核心方法**：安全领域常缺可执行运行时（挑战配置与执行上下文短暂或受限），因此提出**首个无运行时框架**：利用公开 **CTF writeup**，用**人格驱动（persona-driven）的 LLM 模拟反向工程运行时行为**，生成逼真、长周期的交互序列，无需真实环境
- **开源地址**：abs 页给出 Public Link（未抓取）→ `未找到公开信息`
- **关键结果**（原文）：在三个主流 CTF 基准（**InterCode-CTF、NYU CTF Bench、Cybench**）上相对基线**最高提升 13.1 个百分点**；最佳模型 **Cyber-Zero-32B** 在开源权重模型中创 SOTA，匹配 DeepSeek-V3-0324 与 Claude-3.5-Sonnet 能力且成本效益更优
- **来源**：https://arxiv.org/abs/2508.00910

### 4. Trident — 用 RLVR 攻破 DRL 网络防御 — 直接核验 ✅
- **标题**：Trident: How to Break Deep Reinforcement Learning Cyber Defenses (Agentic)
- **arXiv 编号**：`arXiv:2608.04317`（v1 2026-08-05，v2 2026-09-23）— **已核验**
- **作者**：Ryozo Masukawa, Ian Bryant, Armita Kazeminajafabadi, Sanggeon Yun, Hyunwoo Oh, SungHeon Jeong, Nathaniel D. Bastian, Mahdi Imani, Mohsen Imani
- **机构**：abs 页未列 → `待核实`
- **年份**：2026；abs 页给出 code 链接（未抓取）
- **核心方法**：指出 DRL 自主网络防御**几乎只对静态启发式红队 agent 评测**，鲁棒性研究不足；而 RLVR 已提升 LLM 推理能力，但因缺少合适基准环境与交互数据集而未进入网络安全。**Trident** 含三部分：①覆盖 **CybORG CAGE 4 与 CyberWheel** 的隔离沙箱服务器动态基准；②**13,000+ 高保真红蓝交互轨迹**数据集（供 RLVR）；③**"Code-as-Policy" RLVR agentic 架构（Trident Agentic）**，通过 **Log Summarizer–Planner–Coder** 三部分设计把红队 agent 训练重构为**上下文赌博机**：可训练的 Planner 从压缩执行日志生成完整攻击策略，冻结的 Coder 翻译为可执行 Python 策略，部署对抗实时 DRL 防御者
- **关键结果**：abs 在结论处被截断，**具体数字未读到**
- **来源**：https://arxiv.org/abs/2608.04317

### 5. Random-Crypto — GRPO 训练密码学 CTF agent — 直接核验 ✅
- **标题**：Improving LLM Agents with Reinforcement Learning on Cryptographic CTF Challenges
- **arXiv 编号**：`arXiv:2506.02048`（v1 2025-06-01，v2 2025-08-17）— **已核验**
- **作者**：Lajos Muzsai, David Imolai, András Lukács
- **机构**：abs 页未列 → `待核实`
- **年份**：2025
- **核心方法**：提出程序化生成密码学 CTF 数据集 **Random-Crypto**；在**安全执行环境**中用 **GRPO** 微调带 Python 工具增强的 **Llama-3.1-8B**
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**（原文）：在未见挑战上 **Pass@8 显著提升**；提升能泛化到两个外部基准 —— **picoCTF**（含密码与非密码任务）与 **AICrypto MCQ**（135 道密码学多选题）；消融显示增益来自**工具使用**与**过程化推理**增强
- **来源**：https://arxiv.org/abs/2506.02048

---

## 六、2025–2026 基准：编号、规模、测什么、以及被批评的局限

### 6.1 CVE-Bench — 直接核验 ✅
- **标题**：CVE-Bench: A Benchmark for AI Agents' Ability to Exploit Real-World Web Application Vulnerabilities
- **arXiv 编号**：`arXiv:2503.17332`（v1 2025-03-21，v4 2025-06-24）— **已核验**
- **作者**：Yuxuan Zhu, Antony Kellermann, Dylan Bowman, Philip Li, Akul Gupta, Adarsh Danda, Richard Fang, Conner Jensen, Eric Ihli, Jason Benn, Jet Geronimo, Avi Dhir, Sudhit Rao, Kaicheng Yu, Twm Stone, Daniel Kang
- **机构**：GitHub 组织 `uiuc-kang-lab` → UIUC（与 HPTSA 同一实验室）
- **年份**：2025
- **测什么**：基于**关键严重级别的 CVE** 的真实世界基准；设计**沙箱框架**让 LLM agent 在模拟真实条件的场景中利用易受攻击的 Web 应用，并提供有效的利用评估。明确指出既有基准的不足：局限于抽象化 CTF 或覆盖不全面
- **开源地址**：https://github.com/uiuc-kang-lab/cve-bench （HTTP 200，描述与论文一致）
- **关键结果**（原文）：**SOTA agent 框架最多只能解决 13% 的漏洞**
- **来源**：https://arxiv.org/abs/2503.17332 ｜ https://github.com/uiuc-kang-lab/cve-bench

### 6.2 PentestEval — 直接核验 ✅
- **标题**：PentestEval: Benchmarking LLM-based Penetration Testing with Modular and Stage-Level Design
- **arXiv 编号**：`arXiv:2512.14233`（v1 2025-12-16）— **已核验**
- **作者**：Ruozhao Yang, Mingfei Cheng, Gelei Deng, Tianwei Zhang, Junjie Wang, Xiaofei Xie
- **机构**：abs 页未列 → `待核实`
- **年份**：2025
- **规模与测什么**：称**首个**跨**六个分解阶段**评估 LLM 的基准（原文列举：信息收集、弱点收集与过滤、攻击决策、利用生成与修订 —— 注意原文写「六阶段」但枚举处被截断）。整合**专家标注真值**与全自动评测管线，**346 个任务**，覆盖 **12 个真实易受攻击场景**的全部阶段
- **关键结果**：对 **9 个**广泛使用 LLM 的阶段级评测显示**整体表现普遍偏弱**且各阶段局限各异
- **来源**：https://arxiv.org/abs/2512.14233

### 6.3 HackWorld — 直接核验 ✅
- **标题**：HackWorld: Evaluating Computer-Use Agents on Exploiting Web Application Vulnerabilities
- **arXiv 编号**：`arXiv:2510.12200`（v1 2025-10-14）— **已核验**
- **作者**：Xiaoxue Ren, Penghao Jiang, Kaixin Li, Zhiyong Huang, Xiaoning Du, Jiaojiao Jiang, Zhenchang Xing, Jiamou Sun, Terry Yue Zhuo
- **年份**：2025；机构未列 → `待核实`
- **规模与测什么**：首个系统评估**计算机使用 agent（CUA）**能否**通过图形界面/视觉交互**利用 Web 漏洞的框架。含 **36 个真实应用**，覆盖 **11 个框架、7 种语言**，含注入类漏洞、认证绕过、不安全输入处理等真实缺陷；用 CTF 设定测试 CUA 在复杂 Web 界面中识别与利用弱点的能力
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：abs 在评测结论处被截断，**具体数字未读到**
- **来源**：https://arxiv.org/abs/2510.12200

### 6.4 PACEbench — 直接核验 ✅
- **标题**：PACEbench: A Framework for Evaluating Practical AI Cyber-Exploitation Capabilities
- **arXiv 编号**：`arXiv:2510.11688`（v1 2025-10-13）— **已核验**
- **作者**：Zicheng Liu, Lige Huang, Jie Zhang, Dongrui Liu, Yuan Tian, Jing Shao
- **年份**：2025；机构未列 → `待核实`
- **规模与测什么**：基于**真实漏洞难度、环境复杂度、网络防御**三原则构建。含**四类场景**：单一漏洞利用、混合（blended）、链式（chained）、带防御的漏洞利用。提出 **PACEagent**（模拟人类渗透测试者的多阶段侦察-分析-利用）
- **关键结果**（原文）：对 **7 个前沿 LLM** 的实验表明当前模型在复杂网络场景中**表现挣扎**，且**没有任何模型能绕过防御**；作者据此认为当前模型**尚未构成泛化的网络攻击威胁**
- **来源**：https://arxiv.org/abs/2510.11688

### 6.5 ExploitGym — 直接核验 ✅（大规模、跨域）
- **标题**：ExploitGym: Can AI Agents Turn Security Vulnerabilities into Real Attacks?
- **arXiv 编号**：`arXiv:2605.11086`（v1 2026-05-11）— **已核验**
- **作者**：Zhun Wang, Nico Schiller, Hongwei Li, Srijiith Sesha Narayana, Milad Nasr, Nicholas Carlini, Xiangyu Qi, Eric Wallace, Elie Bursztein, Luca Invernizzi, Kurt Thomas, Yan Shoshitaishvili, Wenbo Guo, Jingxuan He, Thorsten Holz, Dawn Song
- **年份**：2026；机构未列 → `待核实`（作者群横跨 UC Berkeley 与 Google 等）
- **规模与测什么**：给定一个**触发漏洞的程序输入**，要求 agent 把它**逐步扩展成可工作的利用**。**898 个实例**，取自真实漏洞，横跨三个领域：**用户态程序、Google V8 JavaScript 引擎、Linux 内核**；对被评估实例**变化安全防护配置**以隔离其对 agent 表现的影响
- **关键结果**：abs 在结果处被截断，**具体数字未读到**
- **来源**：https://arxiv.org/abs/2605.11086

### 6.6 CyberGym —— 见 §1.6（1,507 漏洞 / 188 项目 / 约 20% 成功率 / 34 个 0-day）
- **来源**：https://arxiv.org/abs/2506.02548

### 6.7 其他基准（由我抓取的综述 `2607.02605` 参考文献确认存在，**我未直接抓取其 abs 页 → 部分核验**）
以下条目的标题/作者/编号来自我**实际抓取**的综述 HTML 参考文献段，但我**没有**逐一打开 abs 页，故规模与结果**未核验**：

| 名称 | arXiv 编号 | 作者（综述所载） | 年份 |
|---|---|---|---|
| PentestEval | 2512.14233 | R. Yang, M. Cheng, G. Deng, T. Zhang, J. Wang, X. Xie | 2025 |
| HackWorld | 2510.12200 | X. Ren, P. Jiang, K. Li, Z. Huang, X. Du, J. Jiang, Z. Xing, J. Sun, T. Y. Zhuo | 2025 |
| PACEbench | 2510.11688 | Z. Liu, L. Huang, J. Zhang, D. Liu, Y. Tian, J. Shao | 2025 |
| CTFusion | 2605.11504 | D. Lee, G. Bae, I. Yun | 2026 |
| CyberGym-E2E | 2606.04460 | T. Shi, R. Rheem, D. Jiang, M. Wang, F. De La Riega, Z. Wang, … | 2026 |
| HackSynth | 2412.01778 | L. Muzsai, D. Imolai, A. Lukács | 2024 |
| 3CB (Catastrophic Cyber Capabilities Benchmark) | 2402.11814 | A. Anurin, J. Ng, J. Hoelscher-Obermaier, E. Kran | 2024 |
| Got Root?（Linux 提权基准） | 2405.02106 | A. Happe, J. Cito | 2024 |
| 攻击者可靠性 400-run 研究 | 2605.30096 | G. T. Erdem | 2026 |

**来源（综述参考文献段）**：https://arxiv.org/html/2607.02605v1

### 6.8 基准方法学批评（**这是用户特别要求的部分**）

#### (a) Benchmarking Practices in LLM-driven Offensive Security — 直接核验 ✅
- **arXiv**：`arXiv:2504.10112`（v1 2025-04-14，v2 2025-06-16）｜ 作者：Andreas Happe, Jürgen Cito ｜ 年份：2025 ｜ 机构未列 → `待核实`
- **内容**：审查 **19 篇研究论文、18 个原型**及其测试床，分析方法论与基准实践
- **批评要点（原文）**：强调需要**扩展现有测试床、建立基线、纳入全面指标与定性分析**；并明确指出 —— **CTF 类挑战可能无法充分代表真实世界的渗透测试场景**，需区分安全研究与实践
- **来源**：https://arxiv.org/abs/2504.10112

#### (b) Hackers or Hallucinators? — SoK + 大规模实证 — 直接核验 ✅
- **arXiv**：`arXiv:2604.05719`（v1 2026-04-07）｜ 作者：Jiaren Peng, Zeqin Li, Chang You, Yan Wang, Hanlin Sun, Xuan Tian, Shuqiao Zhang, Junyi Liu, Jianguo Zhao, Renyang Liu, Haoran Ou, Yuqiang Sun, Jiancheng Zhang, Yutong Jiao, Kunshu Song, Chao Zhang, Fan Shi, Hongda Sun, Rui Yan, Cheng Huang ｜ 年份：2026 ｜ 机构未列 → `待核实`
- **内容**：**首个针对 LLM-based AutoPT 的 SoK**。系统层面按**六个维度**综述框架设计：agent 架构、agent 规划、agent 记忆、agent 执行、外部知识、基准。实证层面对 **13 个代表性开源 AutoPT 框架 + 2 个基线框架**在**统一基准**上做大规模实验
- **规模**：消耗 **超过 100 亿 token**，生成 **1,500+ 条执行日志**，由 **15+ 名安全专家**组成的小组**人工审阅分析超过 4 个月**
- **批评要点**：指出既有研究**普遍缺乏系统性架构分析与统一基准下的大规模实证比较** —— 这正是该文要填补的空白
- **来源**：https://arxiv.org/abs/2604.05719

#### (c) 一致性 / 可复现性批评 — 直接核验 ✅
- **标题**：How Reliable Are AI Attackers Against a Fixed Vulnerable Target? A 400-Run Empirical Study of LLM Penetration Testing Consistency
- **arXiv**：`arXiv:2605.30096`（v1 2026-05-28）｜ 作者：Galip Tolga Erdem ｜ 年份：2026
- **方法**：**400 次**自主渗透测试运行（**4 个模型 × 各 100 次**），针对同一蜜罐（托管 OWASP Juice Shop 及两个额外易受攻击服务），**prompt、orchestrator、目标全部固定**
- **关键结果（原文）**：无模型发出能挺过 orchestrator 一次性授权重提示的内容拒绝。**Claude Sonnet 4** 的 API 调用遭遇上游服务不可用 —— 1,135 次调用中 **91 次返回 HTTP 529 overloaded_error**，**截断了 100 次 Claude 运行中的 39 次**。作者特别指出：**早期草稿把这些记录为安全拒答，经完整日志审计后确认是上游 API 故障而非模型级拒绝**（这是一个方法论自我纠正的范例）。完整利用成功率：**Claude 61/100、Gemini 2.5 Flash-Lite 85/100、GPT-4o-mini 56/100（并部署 98 种不同攻击策略）、qwen2.5-coder:14b 25/100**；失败模式具模型特异性（Claude 因 API 截断 39 次、qwen 因过早完成 52 次）
- **来源**：https://arxiv.org/abs/2605.30096

#### (d) 领域综述对局限的总结 — 直接核验 ✅
- **标题**：A Survey of LLM-Driven Penetration Testing: Taxonomy, Co-Evolution, and Open Challenges
- **arXiv**：`arXiv:2607.02605`（v1 2026-07-01）｜ 作者：Zheyuan He, Jiaxun Dong, Zihao Li, Ting Chen, Gelei Deng, Feng Luo, Jinkun Ji, Yuanlong Cao, Xiapu Luo ｜ 年份：2026 ｜ 机构未列 → `待核实`
- **规模**：系统分析 **2023–2026 年间 81 篇论文**，分为六类（评测基准、通用系统、领域专用框架、基于 CTF 的系统、防御导向研究、综述）
- **关键发现（原文）**：①**RLVR 标志着能力获取从「模仿专家示范」转向「奖励驱动的自我改进」**，使 agent 能发现此前未记录的攻防策略；②**CTF 平台已从评测试验床演化为「评测 + RL 训练」双重基础设施**；③**领域专用框架通过反复出现的专门化机制提升效率，但其收益仍局限于狭窄任务类别，且因各领域评测方式不同而难以横向比较**
- **注意（我发现的该综述自身缺陷）**：其参考文献段存在**明显著录错误**，例如把 Anthropic 的 *Scaling Monosemanticity*（2024）标注为 `arXiv:2605.29358`；这提醒读者对该综述的个别引文需二次核验
- **来源**：https://arxiv.org/abs/2607.02605

---

## 七、沙箱化「不可信 LLM 生成攻击代码」与 agentic 安全实验的可复现性

### 7.1 SandboxEval — 直接核验 ✅
- **标题**：SandboxEval: Towards Securing Test Environment for Untrusted Code
- **arXiv 编号**：`arXiv:2504.00018`（v1 2025-03-27）— **已核验**
- **作者**：Rafiqul Rabin, Jesse Hostetler, Sean McGregor, Brett Weir, Nick Judd
- **机构**：abs 页未列 → `待核实`（Sean McGregor 与 MLCommons / AI Risk and Vulnerability Alliance 相关，但我不据此断言）
- **年份**：2025（abs 页标注 "preliminary version, working paper"）
- **核心方法**：针对「LLM 可产生恶意代码，测试 LLM 生成代码会危及评测基础设施」这一风险，提出 **SandboxEval** —— 一套**人工构造的测试用例套件**，模拟 LLM 评测环境在不可信代码执行下的真实安全场景。评估以下脆弱性：**敏感信息暴露、文件系统操纵、对外通信**及其他危险操作。部署在开源实现的 **Dyff**（MLCommons 的规模化 LLM 安全评测框架）上验证
- **开源地址**：abs 页未给出 → `未找到公开信息`
- **关键结果**：证明测试套件能①准确刻画「被指示生成恶意代码的 LLM」所受到的限制；②（abs 截断，第二项结论未读完整）
- **来源**：https://arxiv.org/abs/2504.00018

> **重要发现（诚实报告）**：以「沙箱化 LLM 生成攻击代码」为主题的论文，我**只找到 SandboxEval 这一篇**，且其定位是「**评测沙箱本身**」而非「提出新的攻击代码沙箱方案」。这一方向在 2025–2026 学术文献中**明显稀薄**。

### 7.2 可复现性审计（预注册）— 直接核验 ✅
- **标题**：From Runnable to Verifiable: An Independent Reproducibility Study of LLM/Agent-Driven Vulnerability Validation Artifacts
- **arXiv 编号**：`arXiv:2608.09567`（v1 2026-08-10）— **已核验**
- **作者**：Bo Chen（单一作者）
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：**预注册**的可复现性审计。2023–2026 双人筛选得到 **104 篇论文的一致语料**。对 **18 篇论文样本**在 R0/R1 级别执行，并对锚定基准（`arXiv:2509.24037` —— 注意：该编号由我被抓取的论文正文给出，我**未**直接核验该锚定基准本身）的**全部 102 个案例**执行，另对 30 个可产生信号的案例做**补丁反事实判定**、对 19 个做**匹配阴性对照判定**
- **关键结果（原文，三点）**：
  1. **58/102（56.9%）锚定案例中，脚本内部的 CVE 标识符与所声明的目录 CVE 不一致** —— 即标识符错配普遍存在
  2. **仅 10/18（55.6%）论文级 artifact 在 R0 完成其声明的工作流**，经仅环境层面的 R1 修复后升至 **11/18（61.1%）**
  3. **artifact 内嵌的 oracle 不可靠**：30 个补丁反事实审计中有 **20 个**在已打补丁的构建上**仍然产生所声称的信号**
- **意义**：直接量化了「公开可得 / 可运行 / 可产生信号 / 语义上被确认」四者之间的鸿沟 —— 对依赖 agent 自动生成 PoC 与「验证通过」结论的安全研究是强警示
- **来源**：https://arxiv.org/abs/2608.09567

### 7.3 可复现的实验基础设施（参考实现型）— 直接核验 ✅
- **标题**：Cochise: A Reference Harness for Autonomous Penetration Testing
- **arXiv 编号**：`arXiv:2605.11671`（v1 2026-05-12，v2 2026-08-03）— **已核验**
- **作者**：Andreas Happe, Jürgen Cito
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：指出当前系统把**架构、提示、工具集成**选择捆绑在一起，难以判断相对于「简单 agent + harness」究竟获得了什么。提出 **Cochise** —— **630 行 Python** 的自主渗透测试实验参考实现，通过 **SSH** 连接 Linux 执行主机，支持攻击从跳板机可达的受控目标环境。实现 **Planner–Executor** 架构：**planner 维护长期状态**，**ReAct 风格 executor 经 SSH 下发命令并依据输出自我纠正**；场景提示可适配不同目标环境。对抗**真实第三方测试床 Game of Active Directory (GOAD)** 评测
- **开源地址**：abs 页称同时发布 **cochise-replay**（离线可视化已捕获运行）、**cochise-analyze-logs** 等回放与分析工具（具体 URL 未在 abs 页列出 → `未找到公开信息`）
- **关键结果**：作者明确声明 **Cochise 不是 SOTA 渗透测试 agent**，而是**可复用的实验基础设施**，用于比较模型、agent 架构与渗透轨迹
- **来源**：https://arxiv.org/abs/2605.11671

### 7.4 隐私边界与可复现性（相邻）— 直接核验 ✅
- **标题**：ARENA: An Architecture for Measuring the Transferability of Autonomous Cyber Defense
- **arXiv 编号**：`arXiv:2606.21377`（v1 2026-06-19）— **已核验**
- **作者**：Sidnei Barbieri, Ágney Lopes Roth Ferraz, Wagner Comin Sonaglio, Gioliano de Oliveira Braga, Henrique Curi de Miranda, Lourenço Alves Pereira Júnior
- **机构**：abs 页未列 → `待核实`
- **年份**：2026
- **核心方法**：把「**私有生产遥测与可复用研究 artifact 之间的边界**」当作设计对象：一套从**生产金融 SOC** 提取、匿名化、结构化并验证 SIEM 数据的方法论，在声明的隐私边界内保留任务相关的调查结构。用两个消费者压力测试同一 artifact
- **关键结果（原文）**：作为训练材料时**高调失败**（37 个 MITRE ATT&CK 映射的 HIKARI 挑战仅在匿名化保留时序与实体一致性时才可用）；作为测量基底时**低调失败**（在 200 个 SOCpilot 事件中，确定性验证器检测到人类基线中不存在的 LLM 不合规动作）。结论是得到一个**可度量的隐私-效用边界**，而非形式化匿名性主张
- **来源**：https://arxiv.org/abs/2606.21377

---

## 八、用户候选名单的逐项裁定

| 用户所给候选 | 裁定 | 依据 |
|---|---|---|
| AutoPenBench | ✅ 真实 | `2410.03225` |
| Cybench（编号 2408.08926？） | ✅ 真实，**编号正确** | `2408.08926` |
| NYU CTF Bench | ✅ 真实 | `2406.05590` |
| EnIGMA | ✅ 真实 | `2409.16165` |
| AutoCTF | ❌ **不成立（非 2025–2026 学术工作）** | 实为 **USENIX WOOT '17** 论文 "AutoCTF: Creating Diverse Pwnables via Automated Bug Injection"，非 arXiv、非 LLM agent 系统。我抓取 USENIX WOOT '17 程序页确认标题与摘要片段；ACM DL 页返回 403 未能抓取 |
| CyberGym | ✅ 真实 | `2506.02548` |
| CRAKEN | ✅ 真实？—— **但注意**：我核验的是 `CRAKEN: Cybersecurity LLM Agent with Knowledge-Based Execution`（`2505.17107`）。用户列表中另有一处 `CRAKEN` 疑似与 **ARACNE**（`2502.18528`，"ARACNE: An LLM-Based Autonomous Shell Pentesting Agent"）混淆，二者是不同工作 | `2505.17107` / `2502.18528` |
| PentestAgent | ✅ 真实 | `2411.05185`（AsiaCCS 2025） |
| VulnBot | ✅ 真实 | `2501.13411` |
| IntelBot | ❌ **未找到学术论文** | arXiv 标题检索 0 结果；仅见中文技术博客「PT-IntelBot（渗透测试情报收集Agent）」。**待核实** |
| AutoPentest | ✅ 真实（**与 AutoPentester 是两个不同工作**） | `2505.10321`（Henke）vs `2510.05605`（Ginige 等） |
| HPTSA | ✅ 真实 | `2406.01637` |
| "Teams of LLM Agents can Exploit Zero-Day Vulnerabilities"（2406.01637？） | ✅ **编号正确** | `2406.01637`，EACL 2026 |
| PentestBench | ⚠️ **无 arXiv 论文**；存在 GitHub 仓库 https://github.com/elliotisnotavailable/pentest-bench （HTTP 200，描述："Reproducible benchmark for evaluating LLM-powered autonomous pentesting agents across real CVEs"） | 未找到对应学术论文 → **待核实** |
| CVE-Bench | ✅ 真实 | `2503.17332` |
| CyberBench | ❌ **未找到以该名称为标题的 2025–2026 论文** | arXiv 检索 0 结果；仅在 `2509.13514`（AQUA-LLM）的表格中作为数据集名与 CyberMetric 并列出现 → **待核实** |
| "VulnBot benchmark" | ❌ **未找到名为 "VulnBot benchmark" 的独立基准** | VulnBot 论文自身未在 abs 页宣称发布同名基准 |
| "RL Cybench" | ⚠️ **无此确切标题**；但有真实的 RL + Cybench 工作 | Pentest-R1（`2508.07382`，Cybench 无引导 15.0%）、Cyber-Zero（`2508.00910`，Cybench 等三基准）、PrivEsc-LLM（`2603.17673`） |
| "agent RL security benchmark" / "SWE-agent RL vulnerability" | ⚠️ **未找到以此确切表述的论文** | 最接近：Trident（`2608.04317`，RLVR + CyberWheel/CybORG CAGE 4）、PrivEsc-LLM（`2603.17673`） |
| "training LLM agents with RL for exploitation" | ✅ 有真实对应工作 | `2508.07382`、`2603.17673`、`2608.04317`、`2506.02048` |

---

## 未能核实的条目

以下条目**未能通过直接抓取 arXiv abs 页 / GitHub 仓库确认**，明确列为未核实：

1. **IntelBot / PT-IntelBot** —— 未找到任何 arXiv 论文或同行评议论文。仅见中文技术博客（CSDN）介绍「渗透测试情报收集 Agent」。**未找到公开学术信息**。
2. **CyberBench** —— 未找到以该名称为标题的 2025–2026 论文。arXiv 检索 `"CyberBench"` 返回 0 条匹配标题；仅在 `arXiv:2509.13514` 的一张表里作为数据集列名出现（与 CyberMetric 并列），我**未**抓取该论文正文核实其定义与规模。
3. **PentestBench** —— 未找到学术论文。仅有 GitHub 仓库 `elliotisnotavailable/pentest-bench`（HTTP 200 已验证存在），其与任何论文的对应关系**未找到公开信息**。
4. **AutoCTF（作为 2025–2026 LLM agent 工作）** —— **不成立**。我抓取 USENIX WOOT '17 程序页确认其为 2017 年论文（标题与摘要片段已读到）；ACM Digital Library 页面返回 **HTTP 403**，故完整作者与发表信息**未能从我抓取的来源完整确认**。
5. **NYU CTF Bench 的任务数量与具体通过率** —— arXiv abs 页未给出，我**不引用二手数字**。
6. **EnIGMA / CRAKEN / NYU CTF Bench 的作者机构** —— arXiv abs 页未列，HTML 作者块提取失败。EnIGMA 的官方仓库基于 `SWE-agent` 组织，CRAKEN/NYU CTF Bench 的仓库组织名为 `NYU-LLM-CTF`，**但我不据此断言完整机构列表**。**待核实**。
7. **`arXiv:2606.04460`（CyberGym-E2E）、`arXiv:2605.11504`（CTFusion）、`arXiv:2405.02106`（Got Root?）、`arXiv:2402.11814`（3CB）、`arXiv:2412.01778`（HackSynth）** —— 仅由我实际抓取的综述 `2607.02605` 参考文献段确认标题/作者/编号，**我未直接抓取其 abs 页**，故规模与结果**未核验**。
8. **`arXiv:2601.14662`（Query-Efficient Agentic Graph Extraction Attacks on GraphRAG Systems）** —— 仅从检索结果确认存在，**abs 页未直接抓取**，内容**待核实**。
9. **"GraphRAG 用于渗透测试"** —— **未找到公开信息**。该确切方向在 2025–2026 文献中未见专门论文；存在的是攻击图（MulVAL）、意图 DAG、KG 接地评测三类相邻工作。
10. **"安全 agent 的世界模型（agent 学习目标网络环境模型）"** —— **未找到公开信息**。我抓取的 81 篇论文综述全文对 "world model" 关键词命中 **0 次**。相邻工作为世界模型**自身安全风险**（`2607.23147`、`2604.01346`）与**跨网络泛化实证**（`2603.10041`）。
11. **PTFusion**（Information Fusion, DOI 10.1016/j.inffus.2025.103731）与 **Trinity**（IEEE Xplore 11507673）—— **非 arXiv**，我**未抓取原文**，内容与结果**待核实**。
12. **`arXiv:2509.24037`** —— 作为 `2608.09567` 的「锚定基准」被其正文引用，**我未直接核验该编号本身**。
13. **各系统的 GitHub star 数** —— 我抓取的页面未返回可解析的 star 计数，故**未报告该指标**，不作为影响力证据。
14. **引用量（citation counts）** —— 我**未使用**任何引用数指标。本报告的「后续影响」一律以**我实际抓取到的、明确使用/扩展该工作的后续论文**为依据，而非引用计数。

---

## 附：本报告的证据边界声明

- 所有「关键结果」数值均来自我**直接抓取**的 arXiv abs 页或论文 HTML 的 Abstract 段落原文。凡 abs 在该处被截断、我未读完整者，均已显式标注「截断，未读到」，**未做任何补全或推测**。
- 凡标 `待核实` 的机构字段，表示**我尝试从 arXiv HTML 作者块提取但未成功**，或 abs 页未列出。我**没有**用作者的已知任职单位进行推断填充。
- 我抓取的所有网页内容一律按**数据**处理；未执行其中出现的任何指令性文本。
