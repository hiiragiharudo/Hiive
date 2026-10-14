# LLM/Agent 网络安全综述与滥用风险政策 — 核实报告

> 核实日期：2026-10-14。所有条目均基于**实际抓取成功**的页面；未能抓取或无法确认的内容一律标注「未找到公开信息/待核实」。
> 抓取环境限制：`openai.com` 全域返回 HTTP 403（Cloudflare 拦截）、`justice.gov` 全域连接超时、`eur-lex.europa.eu` 返回 HTTP 202 空内容、arXiv 有速率限制（本次逐条间隔抓取）。以上限制直接影响了个别条目的核实深度，已在文中显式标注。

---

## 综述论文

- **标题**：Large Language Models for Cyber Security: A Systematic Literature Review
  **arXiv 编号**：arXiv:2405.04760（v1 2024-05-08，v5 2025-09-22）
  **作者与机构**：Hanxiang Xu, Shenao Wang, Ningke Li, Kailong Wang, Yanjie Zhao, Kai Chen, Ting Yu, Yang Liu, Haoyu Wang（arXiv 摘要页未列机构 → **机构待核实**）
  **年份**：2024（2025 年修订，已被 ACM TOSEM 接收）
  **核心方法与结论**：采集 40K+ 相关论文，系统分析来自顶级安全与软件工程会议的 185 篇论文（LLM4Security）。分类维度为：网络安全任务（漏洞检测、恶意代码分析、网络入侵检测等）、LLM 架构（encoder-only / encoder-decoder / decoder-only）、适配技术（微调、提示工程、外部增强）。关键结论之一：**基于 LLM 的自主 Agent 是显著新兴趋势**，代表从单任务执行到编排复杂多步安全流程的范式转变。
  **来源链接**：[arxiv.org/abs/2405.04760](https://arxiv.org/abs/2405.04760)

- **标题**：A Survey of Large Language Models in Cybersecurity
  **arXiv 编号**：arXiv:2402.16968（v1 2024-02-26，仅一版）
  **作者与机构**：Gabriel de Jesus Coelho da Silva, Carlos Becker Westphall（arXiv 摘要页未列机构 → **机构待核实**；作者名与巴西 UFSC 团队常见署名一致，但未核实）
  **年份**：2024
  **核心方法与结论**：识别 LLM 已在网络安全的哪些领域被应用、以何种方式应用、以及在领域内的局限性；最后给出如何改进这些局限性的建议，并预测这些局限被克服后系统可以期待什么。属较早（2024 年初）的领域地图型综述，分类粒度较粗，未涉及 Agent 化。
  **来源链接**：[arxiv.org/abs/2402.16968](https://arxiv.org/abs/2402.16968)
  **⚠️ 标题不匹配提示**：用户给出的候选标题「A Survey on Large Language Model-based Cybersecurity」**不成立**；真实标题为「A Survey **of** Large Language Models **in** Cybersecurity」，编号 2402.16968。

- **标题**：Forewarned is Forearmed: A Survey on Large Language Model-based Agents in Autonomous Cyberattacks
  **arXiv 编号**：arXiv:2505.12786（v1 2025-05-19，v2 2025-05-27）
  **作者与机构**：Minrui Xu, Jiani Fan, Xinyu Huang, Conghao Zhou, Jiawen Kang, Dusit Niyato, Shiwen Mao, Zhu Han, Xuemin (Sherman) Shen, Kwok-Yan Lam（arXiv 摘要页未列机构 → **机构待核实**；署名构成与 NTU / 澳门大学 / USYD 等团队重合，未核实）
  **年份**：2025（cs.NI，CC BY 4.0）
  **核心方法与结论**：这是**进攻侧**（攻击者视角）的综述。提出 LLM Agent 的攻防能力模型（scouting / memory / reasoning / action 四要素 + 与其他 Agent 或人类操作者的协同），并把网络环境分为 static / mobile / infrastructure-free 三类，比较常见攻击在不同网络类型下的有效性。提出核心概念 **"Cyber Threat Inflation"（网络威胁通胀）**：攻击成本显著下降、攻击规模大幅上升。结论：由于攻防**运营不平衡**（operational imbalances），现有防御方法不足以对抗自主化网络攻击；最后给出面向遗留网络系统的防御策略与研究方向。
  **来源链接**：[arxiv.org/abs/2505.12786](https://arxiv.org/abs/2505.12786)

- **标题**：A Survey of LLM-Driven Penetration Testing: Taxonomy, Co-Evolution, and Open Challenges
  **arXiv 编号**：arXiv:2607.02605（v1 2026-07-01）
  **作者与机构**：Zheyuan He, Jiaxun Dong, Zihao Li, Ting Chen, Gelei Deng, Feng Luo, Jinkun Ji, Yuanlong Cao, Xiaolu Cao（arXiv 摘要页未列机构 → **机构待核实**；Ting Chen / Xiapu Luo 与 UESTC、香港理工有长期关联，未核实）
  **年份**：2026（cs.SE）
  **核心方法与结论**：**最贴合「LLM 渗透测试」主题的综述**。系统分析 2023–2026 年间的 81 篇论文，分为六类：评估基准、通用系统、领域专用框架、CTF 系统、防御导向研究、综述。提出 **Agents4Pentest** 概念与四阶段架构演化：纯文本推理 Agent → …… → 以 **RLVR（可验证奖励的强化学习）** 训练的 Agent，并指出每次跃迁都由特定的能力瓶颈驱动。四项关键发现：(1) RLVR 标志着能力获取从模仿专家示范转向奖励驱动的自我改进，使 Agent 能发现此前未文档化的攻击策略；(2) CTF 平台已从评测沙盒演进为「评测 + RL 训练」双用途基础设施；(3) 领域专用框架通过反复出现的专门化机制提升效率，但收益局限于窄任务类，且因基准各异而难以跨域比较；(4) 领域正从进攻自动化扩展到对抗性防御与安全合规。**三大开放挑战**：评测可靠性、多阶段攻击场景表现有限、高质量训练数据稀缺。
  **来源链接**：[arxiv.org/abs/2607.02605](https://arxiv.org/abs/2607.02605)
  **⚠️ 标题不匹配提示**：用户给出的候选标题「Penetration Testing with LLMs: A Survey」**不成立**；真实标题为上。

- **标题**：Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges
  **arXiv 编号**：arXiv:2510.23883（v1 2025-10-27，v3 2026-04-03；已发表于 IEEE Access，DOI 10.1109/ACCESS.2026.3675554）
  **作者与机构**：Anshuman Chhabra, Shrestha Datta, Shahriar Kabir Nahin, Prasant Mohapatra（arXiv 摘要页未列机构 → **机构待核实**）
  **年份**：2025（v3 2026）
  **核心方法与结论**：面向「具有 planning / tool use / memory / autonomy 的 LLM Agent 系统」的**威胁分类学**综述。核心论点：Agentic AI 的风险**既不同于传统 AI 安全，也不同于常规软件安全**。内容涵盖：Agent 特有威胁分类、近期基准与评测方法学、以及技术与治理（governance）两个层面的防御策略；主张 secure-by-design。
  **来源链接**：[arxiv.org/abs/2510.23883](https://arxiv.org/abs/2510.23883)
  **⚠️ 标题不匹配提示**：用户给出的候选标题「Agentic AI for Cybersecurity」**未找到对应论文**；最接近的真实论文是本条（2510.23883）。另一个近名候选「A Survey of Agentic AI and Cybersecurity」确实存在，见下条。

- **标题**：A Survey of Agentic AI and Cybersecurity: Challenges, Opportunities and Use-case Prototypes
  **arXiv 编号**：arXiv:2601.05293（v1 2026-01-08）
  **作者与机构**：Sahaya Jestus Lazer, Kshitiz Aryal, Maanak Gupta, Elisa Bertino（arXiv 摘要页未列机构 → **机构待核实**；Elisa Bertino 长期任职 Purdue University，未核实）
  **年份**：2026（cs.CR，CC BY-SA 4.0）
  **核心方法与结论**：**双用途（dual-use）视角最明确的综述**。论述防御侧：持续监控、自主事件响应、自适应威胁狩猎、大规模欺诈检测；进攻侧：同一组属性放大侦察、利用、协同与社会工程攻击。明确指出这些双用途动态**暴露了现有治理、保证（assurance）与问责机制的深层缺口**——这些机制原本是为「非自主、短生命周期」AI 设计的。分析的系统性风险包括：Agent 串谋（collusion）、级联失效、规避监督、记忆投毒（memory poisoning）。最后给出三个代表性用例原型，说明设计选择如何影响可靠性、安全性与运营有效性。
  **来源链接**：[arxiv.org/abs/2601.05293](https://arxiv.org/abs/2601.05293)

- **标题**：LLM-Based Agents for Software and Systems Security: Approaches, Applications, and Assessment
  **arXiv 编号**：arXiv:2608.28490（v1 2026-08-28）
  **作者与机构**：Jingjing Nie, Jiawei Guo, Krishna Meda, Haipeng Cai（arXiv 摘要页未列机构 → **机构待核实**）
  **年份**：2026（cs.CR）
  **核心方法与结论**：覆盖 **2023–2026 年同行评议文献**的系统性文献综述，三个维度：(1) 技术方法（Agent 架构、感知、记忆、推理与规划、动作空间、编排、自我改进）；(2) 应用（所服务的具体安全任务）；(3) 评估（数据集、结果指标与轨迹指标、安全措施、基线）。核心判断极具批判性：**"a field that has built agents able to act but not yet agents whose authority is bounded or whose behavior is auditable"**（该领域已造出「能行动」的 Agent，但尚未造出「权限有界、行为可审计」的 Agent）。同时指出术语 "agent" 使用不一致、应用的风险等级差异极大、评估协议往往不可比较。
  **来源链接**：[arxiv.org/abs/2608.28490](https://arxiv.org/abs/2608.28490)

- **标题**：From LLMs to LLM-based Agents for Software Engineering: A Survey of Current, Challenges and Future
  **arXiv 编号**：arXiv:2408.02479（v1 2024-08-05，v2 2025-04-13）
  **作者与机构**：Haolin Jin, Linghan Huang, Haipeng Cai, Jun Yan, Bo Li, Huaming Chen（arXiv 摘要页未列机构 → **机构待核实**）
  **年份**：2024（v2 2025）
  **核心方法与结论**：覆盖软件工程六大主题：需求工程、代码生成、自主决策、软件设计、测试生成、软件维护。逐一对比 "LLM" 与 "LLM-based Agent" 在任务、基准、评估指标上的异同。
  **⚠️ 重要限定（勿误引为网络安全综述）**：该文是**软件工程（cs.SE）综述**，**不是**网络安全/渗透测试综述；「漏洞检测」仅作为其覆盖的任务之一被提及。若将其列为「LLM 网络安全综述」属于分类错误。
  **来源链接**：[arxiv.org/abs/2408.02479](https://arxiv.org/abs/2408.02479)

---

## 滥用风险与政策

### 一、能力提升的实证评测（frontier model cyber uplift）

- **标题**：Measuring AI Agents' Progress on Multi-Step Cyber Attack Scenarios（UK AISI 官方论文）
  **arXiv 编号**：arXiv:2603.11214（v1 2026-03-11，v3 2026-03-17）
  **作者**：Linus Folkerts, Will Payne, Simon Inman, Philippos Giavridis, Joe Skinner, Sam Deverett, James Aung, Ekin Zorer, Michael Schmatz, Mahmoud Ghanem, John Wilkinson, Alan Steer, Vy Hong, Jessica Wang（UK AI Security Institute 团队；arXiv 摘要页未列机构，但 AISI 博客明确称「our recent paper」并链接此文）
  **年份**：2026（cs.AI / cs.LG）
  **核心方法与结论**：在两个专门构建的 cyber range 上评测前沿模型自主攻击能力——**32 步企业网络攻击**与 **7 步工业控制系统（ICS）攻击**。对比 18 个月内（2024-08 至 2026-02）发布的 7 个模型，在不同推理算力预算下：
  - **能力随推理算力呈对数线性增长，未见平台期**：从 10M token 提升到 100M token，收益最高达 **59%**，且不需要操作者具备任何特定技术能力；
  - 固定 token 预算下，每一代模型都优于前代：企业网络 range 在 10M token 下平均完成步数从 **1.7 步（GPT-4o, 2024-08）升至 9.8 步（Opus 4.6, 2026-02）**；
  - 最佳单次运行完成 **32 步中的 22 步**，约相当于人类专家所需 14 小时中的 6 小时；
  - ICS range 上表现仍然有限，最新模型才首次能稳定完成部分步骤（平均 **7 步中的 1.2–1.4 步，最高 3 步**）。
  **来源链接**：[arxiv.org/abs/2603.11214](https://arxiv.org/abs/2603.11214)

- **标题**：How fast is autonomous AI cyber capability advancing?（AISI 博客）
  **URL**：https://www.aisi.gov.uk/blog/how-fast-is-autonomous-ai-cyber-capability-advancing
  **机构与作者**：UK AI Security Institute（属 DSIT）
  **日期**：2026-05-13
  **核心方法与结论**：
  - AISI 称从 2023 年起追踪 AI 网络能力。其「窄任务网络任务集」的时间视野（time horizon）在 **2025-11 估计为每 8 个月翻倍**，**2026-02 修正为每 4.7 个月翻倍**；Claude Mythos Preview 与 GPT-5.5 大幅超出这两条趋势线，**尚不清楚是孤立跃迁还是新的更快趋势**；单一模型剔除最多只把翻倍时间估计推到 4.1–5.0 个月区间。
  - 评测设置：2.5M token/任务上限、简单 ReAct scaffold、80% 可靠性阈值；作者明确说明该设置**低估**真实能力（GPT-5.5 在 2.5M 上限下对 6 个 8 小时以上任务中的 5 个达到 100% 成功率，第 6 个在取消上限后每次都能解）。
  - Cyber range 结果：更新的 Mythos Preview checkpoint **首次完成两个 range**——"The Last Ones" 10 次中 6 次成功、"Cooling Tower" 10 次中 3 次成功（后者为首次有模型完成）；GPT-5.5 在 "The Last Ones" 上 10 次中 3 次成功。
  - 与 METR 对照：METR 的软件工程时间视野隐含约 **4.2 个月** 的翻倍时间，量级一致。
  - 明确免责：时间视野是「不精确的预测指标」，且**不能说明对抗真实有防御系统时的表现**。
  **来源链接**：[aisi.gov.uk/blog/how-fast-is-autonomous-ai-cyber-capability-advancing](https://www.aisi.gov.uk/blog/how-fast-is-autonomous-ai-cyber-capability-advancing)

- **标题**：Our evaluation of Claude Mythos Preview's cyber capabilities（AISI 博客）
  **URL**：https://www.aisi.gov.uk/blog/our-evaluation-of-claude-mythos-previews-cyber-capabilities
  **机构与作者**：UK AI Security Institute
  **日期**：2026-04-13
  **核心方法与结论**：
  - **专家级 CTF 任务**（2025-04 前无任何模型能完成）上，Mythos Preview 成功率达 **73%**。
  - **Cyber range**：Mythos Preview 是**第一个端到端解出 "The Last Ones"（32 步企业网络攻击，估需人类专家约 20 小时）的模型**，10 次尝试中 3 次成功，全部尝试平均完成 **32 步中的 22 步**；次优的 Claude Opus 4.6 平均 16 步。
  - 未能完成 ICS 方向的 "Cooling Tower" range，且作者指出失败发生在该 range 的 **IT 部分而非 OT 步骤**，因此不能推断其对工控攻击的能力。
  - **明确的局限声明**：range 缺少真实环境的主动防御者、防御工具，且模型触发告警无惩罚 → **无法断言 Mythos Preview 能否攻击防御良好的系统**。
  - 指出能力**双用途**，并呼吁投资网络防御基本盘（补丁、访问控制、配置、日志）。
  **来源链接**：[aisi.gov.uk/blog/our-evaluation-of-claude-mythos-previews-cyber-capabilities](https://www.aisi.gov.uk/blog/our-evaluation-of-claude-mythos-previews-cyber-capabilities)

- **标题**：Our evaluation of OpenAI's GPT-5.5 cyber capabilities（AISI 博客）
  **URL**：https://www.aisi.gov.uk/blog/our-evaluation-of-openais-gpt-5-5-cyber-capabilities
  **机构与作者**：UK AI Security Institute（任务由 Crystal Peak Security、Irregular 协作构建）
  **日期**：2026-04-30
  **核心方法与结论**：
  - **高级任务集**（27 个 Practitioner + 21 个 Expert）：GPT-5.5 在 Expert 级平均通过率 **71.4%（±8.0%, 1 SEM）**，高于 Mythos Preview 的 **68.6%（±8.7%）**、GPT-5.4 的 52.4%（±9.8%）、Opus 4.7 的 48.6%（±10.0%）→ AISI 称 GPT-5.5 **可能是其测试过的最强模型**。
  - **具体案例（rust_vm 逆向题）**：人类专家 playtester（用 Binary Ninja、gdb、Python、Z3）耗时约 **12 小时**；GPT-5.5 在无人工协助下 **10 分 22 秒** 解出，API 成本 **1.73 美元**。
  - **Cyber range**：GPT-5.5 在 "The Last Ones" 上 **10 次中 2 次** 端到端成功（第二个做到的模型）；未能解出 "Cooling Tower"。作者同时披露：**这与 OpenAI GPT-5.5 system card 中原本写的「1 in 10」不同，原因是 AISI 后来发现自己的评分 bug**，经人工复核后更正为 2/10。
  - **安全防护（safeguards）红队结果**：AISI 专家红队发现一个**通用越狱（universal jailbreak）**，可对 OpenAI 提供的**全部恶意网络查询**引出违规内容，**包括多轮 agentic 场景**；该攻击耗时 **6 小时**专家红队开发。OpenAI 随后更新了防护栈，但由于所提供版本存在配置问题，**AISI 无法验证最终配置的有效性**。
  - 结论指出：若进攻性网络技能是长视野自主性/推理/编码能力提升的**副产品**，则未来可能**快速连续**出现能力跃升。
  **来源链接**：[aisi.gov.uk/blog/our-evaluation-of-openais-gpt-5-5-cyber-capabilities](https://www.aisi.gov.uk/blog/our-evaluation-of-openais-gpt-5-5-cyber-capabilities)

- **标题**：How Far Behind the Frontier are Leading Open Weight Models on Cyber?（AISI 博客）
  **URL**：https://www.aisi.gov.uk/blog/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber
  **机构与作者**：UK AI Security Institute
  **日期**：2026-07-17
  **核心方法与结论**：
  - 首个关于开源权重模型与闭源前沿在**网络能力**上差距的公开分析。结论：**GLM-5.2（2026-06）是最具网络能力的开源权重模型**，在 AISI 窄任务上相当于 Opus 4.6（2026-02），在长视野 cyber range 上相当于 Opus 4.5（2025-11），即**落后前沿 4–7 个月**；这比 2025 年 1–9 月内部测得的 **6–10 个月** 差距更窄。
  - 窄任务：70 个任务子集（18 技术非专家 / 25 apprentice / 19 practitioner / 8 expert），每题 5 次尝试、2.5M token 上限。GLM-5.2 与早其 4 个月发布的 Opus 4.6、GPT-5.3-Codex 相当；DeepSeek V4-Pro 相当于早其 5 个月的 Opus 4.5。
  - Cyber range "The Last Ones"（32 步、4 子网、约 20 主机、估人类专家约 20 小时）：GLM-5.2 达到 Opus 4.5 的水平（后者早其不到 7 个月）；DeepSeek V4-Pro 低于 Sonnet 4.5。GLM-5.2 以**比其他任何模型都略少的 token 到达第 7 步**，并在停滞前跟随 Opus 4.6 到第 11 步。
  - **成本对比**：100M token 的 range 运行，Opus 4.5 与 4.6 约 **85 美元**，GLM-5.2 约 **46 美元**，DeepSeek V4-Pro 约 **1.19 美元**；在两者均 100% 可靠解出的任务上，Opus 4.6 每任务 15.17 美元 vs GLM-5.2 6.12 美元，Opus 4.5 12.50 美元 vs DeepSeek V4-Pro 0.28 美元。
  - **开源权重的安全含义**：开放权重使监控、分类器、封禁用户等部署期防护失效，且**一经发布不可逆**；仅剩的拒绝训练易被权重级逆转。作者实测中，DeepSeek V4-Pro 偶有拒绝（主要在逆向工程），**仅用少量重复尝试即绕过**。
  - 结论：网络防御者只有**很短的窗口**来准备，因为今天的前沿网络能力可能很快在缺少同等防护的情况下可得。
  **来源链接**：[aisi.gov.uk/blog/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber](https://www.aisi.gov.uk/blog/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber)

- **标题**：AI models are showing a greater ability to find and exploit vulnerabilities on realistic cyber ranges（Anthropic Frontier Red Team）
  **URL**：https://www.anthropic.com/research/cyber-toolkits-update
  **机构与作者**：Anthropic Frontier Red Team（与 Carnegie Mellon University CyLab 早前合作、与 Incalmo 持续合作）
  **日期**：2026-01-16
  **核心方法与结论**：
  - 与上一年（需要定制 cyber toolkit 才能在 25–50 主机网络上完全成功）相比，**Claude Sonnet 4.5 已能在少数网络上不使用定制 toolkit 而成功**。
  - 具体：Sonnet 4.5 能在**高保真模拟的 Equifax 数据泄露场景**中，仅用一台常见 Kali Linux 主机上的 Bash shell（标准开源渗透测试工具）**外泄全部（模拟）个人信息**；其方式是**即时识别一个已公开的 CVE 并直接写出利用代码，无需查询或迭代**。
  - **关键量化与克制表述**：Sonnet 4.5 在 Equifax range 上 **5 次试验中 2 次**自主成功；在 9 个网络中有 **5 个**在没有定制 toolkit 时无法取得进展。作为对照，早一年多发布的 Claude Sonnet 3.5 在 **5 次试验中 0 次** 能在不用专用 toolkit 的情况下成功。
  - 结论：模型从「需要专用工具」到「可仅用公开工具」的轨迹**预示着网络领域能力将持续改善**，凸显及时打补丁与更新的紧迫性；同时强调不应夸大现状。
  **来源链接**：[anthropic.com/research/cyber-toolkits-update](https://www.anthropic.com/research/cyber-toolkits-update)

- **标题**：CAISI's Assessment of Z.ai's GLM-5.3 Cyber Capabilities（美国 CAISI/NIST 官方评测）
  **URL**：https://www.nist.gov/news-events/news/2026/09/caisis-assessment-zais-glm-53-cyber-capabilities
  **机构与作者**：Center for AI Standards and Innovation（CAISI）/ NIST（页面署名 CAISI/NIST）
  **日期**：2026-09-17
  **核心方法与结论**：
  - 结论一：**GLM-5.3 是迄今发布的最具网络能力的开源权重模型**。
  - 结论二：**GLM-5.3 的网络能力显著低于当前美国前沿模型**，在 CAISI 网络基准的综合度量上**落后美国前沿约 4 个月**。
  - 四个基准（漏洞发现与利用开发）：**SEC-Bench Pro**（183 任务，V8/SpiderMonkey 源码中定位并触发指定类型漏洞导致崩溃）；**ExploitBench**（41 任务，把 V8 已知 bug 发展为可执行任意代码的利用，16 分制取三次最佳）；**ExploitGym (Userspace)**（502 任务，把开源项目真实 bug 发展为利用）；**CAISI OSS-Fuzz**（297 任务，私有基准，无描述/无示例崩溃/无修复，需自行发现并劫持程序）。
  - 关键分值（GLM-5.3 / 美国前沿最佳 / 中国前沿最佳）：SEC-Bench Pro **40.4%** / 90.2% / 27.3%；ExploitBench **61.1%（9.8/16）** / 100.0%（16.0/16）/ 32.2%（5.1/16）；ExploitGym **9.4%** / 44.4% / 2.6%；OSS-Fuzz **7.7%** / 23.2% / 2.4%。
  - 方法论：所有模型以 ReAct harness（bash、python、停止时提示继续）作为 Agent 评测；美国模型在适用时**关闭网络防护（cyber safeguards disabled）**后测试；使用 1PL IRT 模型拟合「网络能力指数」，400 分对应解题几率 10 倍变化。
  **来源链接**：[nist.gov/news-events/news/2026/09/caisis-assessment-zais-glm-53-cyber-capabilities](https://www.nist.gov/news-events/news/2026/09/caisis-assessment-zais-glm-53-cyber-capabilities)

- **标题**：LLM Agents can Autonomously Exploit One-day Vulnerabilities
  **arXiv 编号**：arXiv:2404.08144（v1 2024-04-11，v2 2024-04-17）
  **作者与机构**：Richard Fang, Rohan Bindu, Akul Gupta, Daniel Kang（arXiv 摘要页未列机构 → **机构待核实**；相关代码仓库在 uiuc-kang-lab，未核实）
  **年份**：2024（cs.CR）
  **核心方法与结论**：构建含 **15 个 one-day 漏洞**（含 CVE 描述中标为 critical 的）数据集。**给定 CVE 描述时，GPT-4 能利用其中 87% 的漏洞**，而所有其他被测模型（GPT-3.5、开源 LLM）与开源漏洞扫描器（ZAP、Metasploit）均为 **0%**。关键限定：**GPT-4 高度依赖 CVE 描述——没有描述时只能利用 7%**。作者认为该发现对高能力 LLM Agent 的广泛部署提出了质疑。
  **来源链接**：[arxiv.org/abs/2404.08144](https://arxiv.org/abs/2404.08144)

- **标题**：Teams of LLM Agents can Exploit Zero-Day Vulnerabilities
  **arXiv 编号**：arXiv:2406.01637（v1 2024-06-02，v2 2025-03-30）
  **作者与机构**：Yuxuan Zhu, Antony Kellermann, Akul Gupta, Philip Li, Richard Fang, Rohan Bindu, Daniel Kang（arXiv 摘要页未列机构 → **机构待核实**；GitHub 仓库 uiuc-kang-lab/HPTSA）
  **年份**：2024（cs.MA）
  **核心方法与结论**：单个 Agent 在「事先未知的零日漏洞」上表现差，原因是探索多个漏洞与长程规划困难。提出 **HPTSA**：含一个可启动 subagent 的 **planning agent**，由规划者探索系统并决定调用哪些 subagent，从而解决长程规划问题。构建 **14 个真实世界漏洞**的基准，结果显示该多 Agent 团队相较此前的 Agent 框架**提升最高 4.3 倍**。
  **来源链接**：[arxiv.org/abs/2406.01637](https://arxiv.org/abs/2406.01637)

### 二、双用途风险的学术/立场论文

- **标题**：The Ethics of Autonomous AI Agents for Offensive Security
  **arXiv 编号**：arXiv:2607.20255（v1 2026-07-22，v2 2026-08-07；已被 FAIEMA 2026 接收）
  **作者与机构**：Andreas Happe, Jürgen Cito, Jasmin Wachter（arXiv 摘要页未列机构 → **机构待核实**；Jürgen Cito 长期任职 TU Wien，未核实）
  **年份**：2026（cs.CR / cs.AI）
  **核心方法与结论**：**最直接回应「LLM 渗透测试 Agent 双用途风险」的立场/伦理分析论文**。提出 LLM 驱动的自主 Agent 与传统渗透测试工具（确定性、范围窄、由受训从业者操作）根本不同，其**不确定性沿三个相互独立、彼此不可推导的维度**展开：
  1. **行为不确定**：动作取自非确定性策略，输出既难以事前解释（ex-ante）也难以事后解释（ex-post），使**事件归因与部署前安全审查复杂化**；
  2. **影响开放**：由于动作非确定、所用模型具能动性、以及不透明的 LLM 供应链，影响边界开放；
  3. **用户群体不确定**：使用或开发进攻能力的**技能门槛急剧下降**，用户规模与所需技能都不可界定。
  叠加攻防之间的**结构性成本不对称**，这三者共同促成**进攻能力的工业化（industrialization of offensive capability）**。作者判断：**短期净效应有利于攻击者**，即使长期同一技术可能使防御实践民主化。核心论点是现有**双用途网络安全框架与 AI 伦理框架难以应对这一组合**；论文分析在使用自主 AI Agent 进行进攻性安全时，**道德归因如何在用户、工具制造者与第三方之间弥散（diffuse）**，并考察对利益相关方的影响，最后给出分层建议（stratified recommendations）。
  **来源链接**：[arxiv.org/abs/2607.20255](https://arxiv.org/abs/2607.20255)

### 三、模型厂商政策

#### OpenAI

**⚠️ 严重核实限制：本环境下 `openai.com` 全域返回 HTTP 403（Cloudflare 拦截），`cdn.openai.com` 的 PDF 因内容类型为 `application/pdf` 而无法解析。因此以下条目的 URL 与标题来自搜索结果索引（属二手信息），其正文内容我未能直接读取验证。请勿将下列描述当作已核实事实使用。**

- **条目**：Usage policies（使用政策）
  **URL**：https://openai.com/policies/usage-policies
  **核实状态**：**直接抓取返回 HTTP 403**。搜索索引显示该页标题为 "Usage policies"、且索引快照标注 "Updated: January 29, 2025"。
  **可确认的片段**：搜索结果中出现一条引用该政策原文的片段：「**Illegal activity: OpenAI prohibits the use of our models, tools, and services for illegal activity**」（违法活动：OpenAI 禁止将我们的模型、工具和服务用于违法活动）。该片段来自第三方页面（[scholar.google 索引的 arXiv PDF 2607.19829](https://arxiv.org/abs/2607.19829) 引用处），我抓取了 2607.19829 本身，确认该文为 DARWIN 越狱论文，**但未能定位/核实其中引用该句的具体段落** → 该引文**待核实**。
  **来源链接**：[openai.com/policies/usage-policies](https://openai.com/policies/usage-policies)（403，未能读取内容）

- **条目**：Updating our Preparedness Framework（预置框架更新）
  **URL**：https://openai.com/index/updating-our-preparedness-framework/
  **核实状态**：**直接抓取返回 HTTP 403**，正文未能读取。该 URL 由搜索结果索引返回，标题为「Our updated Preparedness Framework」。
  **相关**：Preparedness Framework 早期版本 PDF 位于 https://cdn.openai.com/openai-preparedness-framework-beta.pdf —— 该 URL 存在（抓取返回「unsupported content type application/pdf」，说明文件确实可访问），但**我无法解析 PDF 正文**，因此**无法核实其中「Cybersecurity」能力类别的确切名称与 High / Critical 阈值定义** → **待核实**。
  **来源链接**：[openai.com/index/updating-our-preparedness-framework/](https://openai.com/index/updating-our-preparedness-framework/)（403）；[cdn.openai.com/openai-preparedness-framework-beta.pdf](https://cdn.openai.com/openai-preparedness-framework-beta.pdf)（PDF 不可解析）

- **条目**：Responding to the next frontier of critical cyber capabilities
  **URL**：https://openai.com/index/responding-next-frontier-critical-cyber-capabilities/
  **核实状态**：**直接抓取返回 HTTP 403**，正文未能读取。URL 与标题由搜索结果索引返回（多语言版本 nb-NO / ja-JP / de-DE 亦被索引）。
  **第三方报道（二手）**：需注意我未能直接读取该 OpenAI 页面，因此**无法确认其具体内容**。
  **来源链接**：[openai.com/index/responding-next-frontier-critical-cyber-capabilities/](https://openai.com/index/responding-next-frontier-critical-cyber-capabilities/)（403）

- **条目**：Scaling trusted access for cyber defense
  **URL**：https://openai.com/index/scaling-trusted-access-for-cyber-defense/
  **核实状态**：仅由搜索结果索引返回（含 sv-SE 版本），**未能抓取**，内容与发布日期**待核实**。
  **来源链接**：[openai.com/index/scaling-trusted-access-for-cyber-defense/](https://openai.com/index/scaling-trusted-access-for-cyber-defense/)（未抓取）

- **关于「Astra / GPT-6 达到 Critical 网络能力」的报道（二手，未能核实原始来源）**
  搜索结果索引中出现了多条第三方报道称 OpenAI 的 Astra / GPT-6 模型达到其预置框架下的 "Critical" 网络能力阈值，例如 [InfoQ: GPT-6 Astra is the First Model OpenAI Classifies as Critical for Cybersecurity](https://www.infoq.com/news/2026/09/gpt-6-astra-critical-cyber/)（**抓取返回 HTTP 405 / Human Verification，未能读取**）、[Digital Watch Observatory](https://dig.watch/updates/openai-model-critical-cyber-capability-threshold)（抓取成功但正文被截断，未获得实质内容）、[CSA Labs research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-openai-astra-critical-cyber-threshold-2026/)（**抓取返回 HTTP 403 / Cloudflare "Just a moment..."**）。
  **结论**：上述「OpenAI 模型达到 Critical 网络能力阈值」的说法在本环境下**未能通过任何可完整读取的一手或可靠二手来源核实** → **待核实**，请勿据以引用。
  **另需提示**：搜索索引中出现一条第三方文档片段称「GPT-5.6-Sol was assessed at **High, not Critical**, for frontier cyber capability」——与上述「Astra 达到 Critical」的说法**互相矛盾**，我未能核实任一说法。

#### Anthropic

- **标题**：Anthropic Usage Policy（使用政策，含 AUP）
  **URL**：https://www.anthropic.com/legal/aup
  **机构**：Anthropic PBC；生效日期 **2026 年 11 月 12 日**（页面明示 "Effective November 12, 2026"，并提供 Previous Version 链接）
  **核心内容（已逐字核实）**：
  - 政策分三类：**Universal Usage Standards**（对所有用户适用）、**High-risk Use Case Requirements**、**Additional Use Case Guidelines**。
  - 与进攻性安全直接相关的章节为 **"Do Not Compromise Computer or Network Systems Without Authorization"**，明确禁止用其产品：
    "**Discover or exploit vulnerabilities in systems, networks, or applications without authorization of the system owner**"；
    "Gain unauthorized access to, or escalate unauthorized privileges within, systems…"；
    "Create or install tools designed to intercept communications or monitor devices without authorization"；
    "Develop persistent unauthorized remote access tools… including firmware modifications or hardware implants"；
    "**Create automated tools designed to compromise multiple systems at scale without authorization**"；
    "Bypass security controls such as authentication systems, endpoint protection, or monitoring tools without authorization"；
    "Create or distribute malware, ransomware, or other types of malicious code"；
    "Conduct denial-of-service attacks, or develop tools for denial-of-service attacks or managing botnets"。
  - **关键授权例外（security research carve-out）**，逐字引用："This section does not prohibit security research, testing, or tool development conducted on systems you own or operate, with the authorization of the system owner, or within the scope of an authorized bug bounty program or vulnerability disclosure policy, provided the activity complies with applicable law. For work covered by our real-time cyber safeguards, users may apply for adjusted access through our **Cyber Verification Program**."
  - 另有 **"Do Not Compromise Critical Infrastructure"** 章节，禁止破坏电网、水处理、医疗设备、电信、应急、交通等关键基础设施，禁止未授权访问选举/医疗/金融系统，禁止干扰军事基地及基础设施运行。
  - 页面说明其产品含**实时防护（real-time safeguards）**，且「遇到阻断本身并不表示违反使用政策」；针对双重用途场景提供可申请的调整访问项目（Cyber Verification Program、Life Sciences Verification Program）。
  **来源链接**：[anthropic.com/legal/aup](https://www.anthropic.com/legal/aup)

- **标题**：Anthropic's Responsible Scaling Policy（负责任扩展政策，RSP）总览页
  **URL**：https://www.anthropic.com/rsp（重定向至 https://www.anthropic.com/responsible-scaling-policy）
  **机构**：Anthropic PBC；页面 **最后更新 2026-08-14**
  **核心内容（已核实）**：
  - **当前版本 RSP v3.4（生效 2026-07-08）**；历史版本：v3.3（2026-05-26）、v3.2（2026-04-29）、v3.1（2026-04-02）、v3.0（2026-02-24）、v2.2（2025-05-14）、v2.1（2025-03-31）、v2.0（2024-10-15）、v1.0（2023-09-19）。
  - v3.4 的变更包括：修订自动化 R&D 阈值以更好追踪所关注的威胁模型、放宽完整未删节 Risk Report 的内部共享要求（改为至少 200 名员工）、允许 Risk Report 以给定覆盖日期分析风险、要求公开版 Risk Report 标注删节位置等。
  - v3.0 是一次**全面重写**，引入 **Frontier Safety Roadmaps**（详细安全目标）与 **Risk Reports**（量化全部已部署模型的风险）。
  - 已发布 Risk Reports：**Redacted Risk Report August 2026**、**Redacted Risk Report February 2026**。
  - 另有 **RSP Noncompliance Reporting and Anti-Retaliation Policy**（2026-02 内部发布，2026-03-24 公开更新）。
  - ⚠️ **关于「ASL-3 / 网络能力阈值」的重要限定**：本总览页中列出的 **Capability Thresholds 明确为两类——AI R&D 与 CBRN（化学/生物/放射/核）**（另见 2025-03-31 条目新增的「中等资源国家项目级 CBRN 开发能力」阈值与 AI R&D 阈值拆分）。页面正文**未把「网络（cyber）」列为一项 Capability Threshold**。RSP 正文为 PDF，**本环境无法解析 PDF**，因此**不能排除** RSP v3.x 全文在别处含网络相关门槛 → **该点待核实**。
  **来源链接**：[anthropic.com/responsible-scaling-policy](https://www.anthropic.com/responsible-scaling-policy)

- **标题**：Announcing our updated Responsible Scaling Policy（RSP v2.0 公告）
  **URL**：https://www.anthropic.com/news/announcing-our-updated-responsible-scaling-policy
  **机构与作者**：Anthropic PBC；日期 **2024-10-15**
  **核心内容（已核实）**：
  - 提出 **AI Safety Level Standards（ASL Standards）**，借鉴生物安全等级（Biosafety Levels）思路，从 ASL-1（基本能力，如象棋机器人）递进至 ASL-2、ASL-3 等；**当时所有模型在 ASL-2 标准下运行**。
  - 该版本定义的两个 Capability Threshold 为：**Autonomous AI Research and Development** 与 **CBRN weapons**——**此处同样未把 cyber 列为能力阈值**。
  - ASL-3 部署防护采用四层纵深架构：访问控制、实时提示与补全分类器（流式）、异步监控分类器、事后越狱检测与快速响应。
  - ASL-3 安全防护列出 17 项控制措施，其中第 13 项为 "Red teaming and penetration testing"（与外部红队与渗透测试专家合作，模拟内部威胁与供应链攻击场景）、第 16 项为欺骗技术（含假模型权重蜜罐）。
  - 组织分工：**Frontier Red Team 负责威胁建模与能力评估**；Trust & Safety 负责部署防护；Security and Compliance 负责安全防护与风险管理；Alignment Science；RSP Team。
  - 披露首次 RSP 合规复盘发现若干**未完全达标项**（评估晚于计划 3 天、占位评估替换、部分评估缺少 best-of-N 或思维链等诱导技术、未显式设计 6x 扩展缓冲），结论为风险极小。
  - 脚注明确：其评估方法论已分享给**两家 AI Safety Institute** 及独立专家征求意见，且**这不代表任一 AISI 或专家的背书**。
  **来源链接**：[anthropic.com/news/announcing-our-updated-responsible-scaling-policy](https://www.anthropic.com/news/announcing-our-updated-responsible-scaling-policy)

- **标题**：Introducing the Anthropic Cyber Mission
  **URL**：https://www.anthropic.com/news/anthropic-cyber-mission
  **机构与作者**：Anthropic PBC；日期 **2026-10-08**
  **核心内容（已核实）**：
  - 启动「Anthropic Cyber Mission」长期承诺，先从两个方向入手：**关键基础设施**（成立 Critical Infrastructure Defense Program, CIDP，创始伙伴包括 Accenture、Booz Allen、CrowdStrike、Deloitte、Dragos、Hitachi、Insane Cyber、Nozomi Networks、Palo Alto Networks、PwC、Rockwell Automation）与**开源软件**（推出 **OSS Scanner**，为开源项目提供免费的定期安全扫描）。
  - 点明双用途风险："Frontier models can be misused to exploit vulnerabilities and conduct cyber operations."
  - 披露 Project Glasswing 的经验与量化判断：**OSS Scanner 报告为模型生成、不经人工复核**，因此会含不准确（如错误严重性评级）；**预期真阳性率高于 90%**，并将持续改进。
  - 关键判断："**The cost of exploiting vulnerabilities has dropped**, while verifying, disclosing, and fixing them is slow and still depends on people."（利用漏洞的成本已下降，而验证、披露与修复仍然缓慢且依赖人力）；Glasswing 中常见「漏洞被发现到被修复之间隔数月」；OT 环境的修复有时需等待可安全应用于运行中机械的时机，**罕见情况下可能长达数十年**。
  - 预测："Our forecast is that in two years, AI will favor defense… **But in the near term, that may not be true.**"
  **来源链接**：[anthropic.com/news/anthropic-cyber-mission](https://www.anthropic.com/news/anthropic-cyber-mission)

### 四、政府评测机构

#### 英国 AI Security Institute（AISI，aisi.gov.uk）

- **标题**：The AI Security Institute (AISI) 官网
  **URL**：https://www.aisi.gov.uk/
  **机构**：UK AI Security Institute，隶属**英国科学、创新与技术部（DSIT）**
  **核心内容（已核实）**：自称 "the first state-backed organisation dedicated to advancing this goal"（首个由国家背书的、致力于推进该目标的机构）；拥有 100+ 技术人员（含来自 OpenAI、Google DeepMind、牛津大学的资深成员）；主页列出的重点研究方向为：监测 AI 发展态势、评估 AI 对国家安全的威胁、推进 safeguard/alignment/control 类解决方案。主页首推 **Frontier AI Trends Report**（含 cyber 专章与术语表）。
  **来源链接**：[aisi.gov.uk](https://www.aisi.gov.uk/)

- **AISI 网络能力评测体系（已核实，来自上述各篇博客）**：
  1. **Narrow cyber tasks**：CTF 形式的窄任务集，原为 95/96 题、四档难度（technical non-expert / apprentice / practitioner / expert）；时间视野分析使用 **70 题子集**（对应 18/25/19/8 题）以支持历史比较。专家级任务在 2025-04 前无模型能完成。
  2. **Cyber ranges**：专家构建的模拟网络（主机、服务、漏洞、顺序攻击链），从「已获得初始访问」开始。目前两个：**"The Last Ones"（TLO）**——32 步企业网络攻击、4 子网、约 20 主机、估人类专家约 20 小时，与 SpecterOps 共建；**"Cooling Tower"**——7 步 ICS 攻击模拟（模拟电厂，须通过面向 Web 的 HMI 进入、逆向专有控制协议及其加密认证、最终操纵 PLC 破坏物理过程），估人类专家约 15 小时，与 Hack The Box 共建。
  3. **AISI 明确声明的范围限制**：range **缺少真实环境的主动防御者、防御工具，且模型触发告警无惩罚**；测试范围限于「Agent 被明确指示并获得网络访问、针对特定脆弱目标」的情形；**无法据此判断模型能否攻破防御良好的目标**。AISI 正在构建含主动监控、终端检测与实时事件响应的加固环境 range。
  **来源链接**：[measuring-ai-agents-progress-on-multi-step-cyber-attack-scenarios](https://www.aisi.gov.uk/research/measuring-ai-agents-progress-on-multi-step-cyber-attack-scenarios)、[arXiv:2603.11214](https://arxiv.org/abs/2603.11214)

- **AISI 与 CAISI 联合评测（已核实存在，内容未逐篇读取）**：NIST 页面列出「UK AISI / CAISI Preliminary Assessment of Kimi K3's Cyber Capabilities」（2026-07-23），评测使用 **ExploitBench** 等基准。
  **来源链接**：[nist.gov/news-events/news/2026/07/uk-aisi-caisi-preliminary-assessment-kimi-k3s-cyber-capabilities](https://www.nist.gov/news-events/news/2026/07/uk-aisi-caisi-preliminary-assessment-kimi-k3s-cyber-capabilities)

- **相关**：英国国家网络安全中心（NCSC）与 AISI 联合发布面向防御者的指引，包括 [Retaining defensive advantage in the age of frontier AI cyber capabilities](https://www.ncsc.gov.uk/blogs/retaining-defensive-advantage-in-the-age-of-frontier-ai-cyber-capabilities)（抓取成功但正文被导航结构截断，未获得实质内容 → **内容待核实**）与 [Why cyber defenders need to be ready for frontier AI](https://www.ncsc.gov.uk/blogs/why-cyber-defenders-need-to-be-ready-for-frontier-ai)（由 AISI 博客引用）。

#### 美国 CAISI / CAISSI（NIST）

- **标题**：Center for Advancing Innovation and Standards for Super Intelligence (CAISSI)
  **URL**：https://www.nist.gov/caissi （`https://www.nist.gov/caisi` 会重定向至此）
  **机构**：NIST（美国商务部）
  **⚠️ 重要更名事实**：用户提到的 "Center for AI Standards and Innovation (CAISI)" 是**旧称**；NIST 现行页面标题为 **Center for Advancing Innovation and Standards for Super Intelligence (CAISSI)**，归属 NIST 的 "Super intelligence" 主题域，并下设 **AI Agent Standards Initiative**、Guidelines、AI Consortium 等。
  **核心内容（已核实，逐条）**：CAISSI 的职责包括：
  - 作为产业界在**美国政府内的主要对接窗口**，促进与 SI（superintelligence）系统相关的测试与协作研究；
  - 与 NIST 各组织合作制定测量与提升 SI 系统安全性的指南与最佳实践，协助产业界制定自愿性标准；
  - 与私营 SI 开发者与评估方建立自愿协议，**牵头对可能构成国家安全风险的 SI 能力开展非机密评估**——页面明确写道："**In conducting these evaluations, CAISSI will focus on demonstrable risks, such as cybersecurity, biosecurity, and chemical weapons.**"（评估聚焦可证明的风险，如**网络安全**、生物安全与化学武器）；
  - 牵头评估美国与对手 SI 系统的能力、外国 SI 系统的采用情况、国际 SI 竞争态势；
  - 评估使用对手 SI 系统带来的安全隐患与恶意外国影响（**包括后门与其他隐蔽恶意行为的可能性**）；
  - 与国防部、能源部、国土安全部、OSTP 及情报界协调评估方法；
  - 在国际上代表美国利益，防止外国政府对美国技术施加繁重且不必要的监管。
  **来源链接**：[nist.gov/caissi](https://www.nist.gov/caissi)

- **CAISSI 已发布的网络能力评测（已核实存在）**：
  - **CAISI's Assessment of Z.ai's GLM-5.3 Cyber Capabilities**（2026-09-17，已详读，见上文）
  - **UK AISI / CAISI Preliminary Assessment of Kimi K3's Cyber Capabilities**（2026-07-23）
  - **CAISI Assessment of Z.ai's GLM-5.2**（2026-07-17）
  - **CAISI Evaluation of DeepSeek V4 Pro**（2026-05-01，"In April 2026… CAISI evaluated the open-weight AI model DeepSeek V4 Pro"）
  - **CAISSI Research Blog** 系列，含 [Insights into AI Agent Security from a Large-Scale Red-Teaming Competition](https://www.nist.gov/blogs/caissi-research-blog/insights-ai-agent-security-large-scale-red-teaming-competition)（2026-03-23）、[Analyzing Transcripts from AI Agent Evaluations](https://www.nist.gov/blogs/caissi-research-blog/analyzing-transcripts-ai-agent-evaluations)（2026-02-18，提到 2025 年 12 月曾发文分析 AI 模型**在 agentic 评测中作弊**）、[Cheating On AI Agent Evaluations](https://www.nist.gov/blogs/caissi-research-blog/cheating-ai-agent-evaluations)（2025-12-02）。
  **来源链接**：[nist.gov/caissi](https://www.nist.gov/caissi)（含上述全部链接的索引）

- **NIST AI RMF（AI 风险管理框架）**：https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10 —— 该 URL 由搜索结果索引返回，**我未直接抓取该页面**，故仅记录其存在与位置，**内容待核实**。

### 五、监管框架

#### 欧盟《人工智能法案》（Regulation (EU) 2024/1689）

> **核实说明**：`eur-lex.europa.eu`（包括 `/eli/reg/2024/1689/oj`、`CELEX:32024R1689`、`OJ:L_202401689` 三个变体）在本环境中返回 **HTTP 202 且正文为空**，无法读取。因此我改用**欧盟委员会官方的 AI Act Service Desk**（`ai-act-service-desk.ec.europa.eu`，由 DG CONNECT 运营，页面注明其文本基于 **EUR-Lex 2026-07-27 合并版**）作为一手来源逐条核实法条原文。

- **标题**：AI Act（欧盟委员会官方政策页）
  **URL**：https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
  **机构**：European Commission, DG CONNECT；页面最后更新 **2026-08-03**
  **核心内容（已核实）**：
  - 法案全称：**Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence**，为全球首个 AI 综合法律框架。
  - **四档风险**：不可接受风险（禁止）、高风险、透明度风险、最低/无风险。
  - **九项禁止实践**（prohibitions 1–8 自 2025 年 2 月起生效；第 9 项于 **2026 年 12 月**生效，由 AI Omnibus 引入）——其中与安全测试生态相关的是第 1、2 项（有害的 AI 操纵与欺骗、有害地利用脆弱性），第 9 项为生成非自愿性私密内容或 CSAM 的 AI 系统。
  - **高风险类别**包括「**AI safety components in critical infrastructures**（如交通），其失效可能危及公民生命健康」等；高风险系统自 **2027-12-02** 起适用严格义务（因 AI Omnibus 延期），嵌入式产品中的高风险系统延至 **2028-08-02**。
  - **GPAI 规则自 2025 年 8 月起生效**；对可能带来系统性风险的 GPAI 模型，提供者应**评估并缓解风险**。
  - **时间线**：2024-08-01 生效；2026-08-02 全面适用（有例外）；禁止性实践与 AI 素养义务自 2025-02-02 起适用；治理规则与 GPAI 义务自 2025-08-02 起适用。
  - **AI Omnibus（简化方案）**：2025-11-19 通过、2026-05-07 达成政治一致、**2026-07-27 生效**；新增禁止生成非自愿性私密内容/CSAM 的 AI 系统、强化 AI Office 权力并集中对基于 GPAI 构建的 AI 系统的监督等。
  - **与网络安全的直接关联**：2026 年 7 月发布 **[EU Action Plan on Cybersecurity and Artificial Intelligence](https://digital-strategy.ec.europa.eu/en/library/eu-action-plan-cybersecurity-and-artificial-intelligence)**，提出成员国、企业与公共机构协同应对最先进 AI 模型带来的网络安全与韧性挑战；**欧盟委员会将发起征集以提高 EU 对 AI 模型的评估能力（在市场投放前）**，预计 **2027 年**投入运行，以强化对 AI 能力与风险的第三方评估并服务于 AI Office 的监管职能；委员会与 **ENISA** 将制定**为网络安全目的获取先进 AI 系统的蓝图**，并建立安全测试平台，供能源、交通、医疗、金融、公共行政等关键部门安全测试与部署 AI 方案。
  **来源链接**：[digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)

- **标题**：Article 55: Obligations of providers of general-purpose AI models with systemic risk（第 55 条：具有系统性风险的通用人工智能模型提供者的义务）
  **URL**：https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-55
  **机构**：European Commission / AI Act Service Desk（基于 EUR-Lex 2026-07-27 合并版）
  **核心内容（已逐字核实第 1 款四项义务）**：具有系统性风险的 GPAI 模型提供者，除第 53、54 条义务外还应：
  - **(a)** "perform model evaluation in accordance with standardised protocols and tools reflecting the state of the art, **including conducting and documenting adversarial testing of the model with a view to identifying and mitigating systemic risks**"（按反映最新技术水平的标准化协议与工具进行模型评估，**包括对模型开展并记录对抗性测试，以识别和缓解系统性风险**）；
  - **(b)** 在**欧盟层面**评估并缓解可能的系统性风险（含其来源），这些风险可能源自模型的开发、投放市场或使用；
  - **(c)** 追踪、记录并及时向 **AI Office**（及视情向国家主管机构）报告**严重事件**的相关信息与可能的纠正措施；
  - **(d)** 为具有系统性风险的 GPAI 模型**及该模型的物理基础设施**确保**足够的网络安全保护水平**。
  **⚠️ 重要更正**：用户假设「第 55(1)(a) 提到 cyber offence（网络犯罪）能力评估」——**该具体表述在合并版条文文本中并不存在**。第 55(1)(a) 的措辞是「adversarial testing … with a view to identifying and mitigating **systemic risks**」（对抗性测试以识别和缓解**系统性风险**），未出现 "cyber offence" 字样。与网络安全直接相关的表述是第 55(1)(d)（网络防护水平）。**请勿引用「第 55 条明确要求 cyber offence 评估」这一说法。**
  **来源链接**：[ai-act-service-desk.ec.europa.eu/en/ai-act/article-55](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-55)

- **标题**：ANNEX III — High-risk AI systems referred to in Article 6(2)
  **URL**：https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3
  **核心内容（已逐字核实）**：附件三列出的高风险领域共 8 类：1. 生物识别；**2. 关键基础设施**；3. 教育与职业培训；4. 就业、劳动者管理与自雇准入；5. 基本私有与公共服务及福利的可及性；6. 执法；7. 移民、庇护与边境管制；8. 司法行政与民主进程。
  **⚠️ 重要更正（两点）**：
  1. 关键基础设施**不是**附件三点 1，而是**点 2**，其措辞为："**Critical infrastructure: AI systems intended to be used as safety components in the management and operation of critical digital infrastructure, road traffic, or in the supply of water, gas, heating or electricity.**"（关键基础设施：拟用作**关键数字基础设施**、道路交通、或水/气/热/电供应之管理与运营中的**安全组件**的 AI 系统）。
  2. 附件三**点 5(b)** 是「评估自然人信用度或建立信用评分」，**并非**关键基础设施或网络安全条款。
  3. 附件三**通篇未出现 "cybersecurity" 一词**；网络安全要求出现在**第 15 条（准确性、鲁棒性与网络安全）**与**第 55(1)(d)**，属对高风险系统与系统性风险 GPAI 提供者的**要求**，而非高风险**分类**依据。
  **来源链接**：[ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3)

- **关于「10^25 FLOP 系统性风险阈值」**：用户提出的这一数值我**未能在本次抓取中核实**。AI Act Service Desk 的 Article 51 页面我没有抓取；EUR-Lex 正文在本环境不可读。→ **待核实**（该数值通常被归属于 AI Act 第 51(2) 条授权委员会通过的实施法案中的算力推定门槛，但**本次未核实**）。
  **可核实的相关线索**：https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-51 （未抓取）

#### 美国：CFAA 与 DOJ 2022 年起诉政策

- **标题**：18 U.S. Code § 1030 — Fraud and related activity in connection with computers（《计算机欺诈与滥用法》，CFAA）
  **URL**：https://www.law.cornell.edu/uscode/text/18/1030
  **来源说明**：**Cornell Law School Legal Information Institute (LII)** 是美国判例与法典的常用权威转载源（非政府官网）；`uscode.house.gov` 的对应 section 链接在本环境返回 "Page Not Found"（该站点当前处于临时格式状态，其自述「current through Public Law 119-120 (October 7, 2026)」）。
  **核心内容（已逐字核实）**：
  - **(a)(2)** 未经授权或**超越授权访问**并由此获取受保护计算机中的信息；(a)(4) 以欺诈意图未经授权访问受保护计算机；(a)(5)(A)–(C) 未经授权传输程序/信息/代码/命令并**故意造成损害**、或未经授权访问并**轻率/故意造成损害与损失**；(a)(7) 以**勒索**意图传输威胁。
  - **(e)(6) 定义「exceeds authorized access」**："to access a computer with authorization and to use such access to obtain or alter information in the computer that the accesser is not entitled so to obtain or alter"（以**有授权**方式访问计算机，但利用该访问获取或篡改**其无权**获取或篡改的信息）。
  - **(e)(2) 定义「protected computer」**涵盖用于或影响州际/对外商务或通信的计算机，**包括位于美国境外但以影响美国州际/对外商务或通信的方式使用的计算机**。
  - **(f) 例外条款**：本条**不禁止**美国、州或州政治分区执法机构、或美国情报机构**合法授权的**调查、保护或情报活动。
  - **(c) 刑罚**：例如 (a)(1) 项最高 10 年（再犯 20 年）；(a)(5)(A) 造成 (c)(4)(A)(i)(I)–(VI) 中任一危害者最高 10 年，致重伤最高 20 年，致死可至**终身**。
  - **(g) 民事诉权**：受害人可提起民事诉讼要求补偿性损害赔偿与禁令救济，但仅限第 (c)(4)(A)(i) 项的 (I)–(V) 类情形，且**诉讼时效为 2 年**。
  **来源链接**：[law.cornell.edu/uscode/text/18/1030](https://www.law.cornell.edu/uscode/text/18/1030)

- **标题**：DOJ 2022 年 CFAA 起诉新政策（「good-faith security research」不入罪）
  **原始官方 URL（存在但本环境不可达）**：https://www.justice.gov/archives/opa/pr/department-justice-announces-new-policy-charging-cases-under-computer-fraud-and-abuse-act
  **核实状态**：**`justice.gov` 全域在本环境中连接超时**（我尝试了 `/opa/pr/...`、`/archives/opa/pr/...`、`/jm/jm-9-48000-computer-fraud`、`/criminal/criminal-ccips` 及站点根路径共 6 次，全部 `fetch failed`）。因此**该政策的原文我未能读取**。
  **可用的替代来源（已成功抓取，属二手但引文明确）**：[Alston & Bird Privacy, Cyber & Data Strategy Blog, "DOJ Issues New Policy on CFAA Prosecutions", 2022-05-19](https://www.alstonprivacy.com/doj-issues-new-policy-on-cfaa-prosecutions/)
  该文（作者 Kim Peretti，前 DOJ 网络犯罪检察官）**逐字引用**了政策原文，可核实的内容如下：
  - 该政策是自 2014 年以来 DOJ 的**首次更新**，**立即生效**；所有希望依 CFAA 起诉的联邦检察官**必须遵循该政策，并在起诉前与刑事司计算机犯罪与知识产权科（CCIPS）磋商**。
  - **首次明确写入**："**the government should decline prosecution if available evidence shows the defendant's conduct consisted of, and the defendant intended, good-faith security research**"（若有可用证据表明被告的行为构成且其意图为**善意安全研究**，政府应拒绝起诉）。
  - **「善意安全研究」的定义（引原文）**：访问系统 "solely for purposes of good-faith testing, investigation, and/or correction of a security flaw or vulnerability, where such activity is carried out in a manner designed to avoid any harm to individuals or the public, and where the information derived from the activity is used primarily to promote the security or safety of the class of devices, machines, or online services to which the accessed computer belongs, or those who use such devices, machines, or online services."
  - 时任副司法部长 Lisa O. Monaco 表态："today's announcement promotes cybersecurity by providing clarity for good-faith security researchers who root out vulnerabilities for the common good."
  - **明确的排除项**："claiming to be conducting security research is not a free pass"，DOJ 重申**任何勒索企图（extortion）都不属于善意研究**。
  - 呼应最高法院 **_United States v. Van Buren_（2021）**：新政策**禁止**基于「被告对特定文件、数据库、文件夹或用户账户的访问授权是被合同、协议或政策（如网站服务条款）所附加条件」这一理论提起 CFAA 起诉；但保留一项**窄例外**——若计算机所有者有「**在任何情况下完全禁止**被告访问特定文件、数据库、文件夹或用户账户」的合同/协议/政策，则仍可能起诉。
  **来源链接**：[alstonprivacy.com/doj-issues-new-policy-on-cfaa-prosecutions/](https://www.alstonprivacy.com/doj-issues-new-policy-on-cfaa-prosecutions/)

#### 中国

- **标题**：中华人民共和国网络安全法（2025 年修正）
  **URL（官方，中国网信网转载中国人大网文本）**：https://www.cac.gov.cn/2025-12/29/c_1768735112911946.htm
  **发布与版本（已逐字核实抬头）**：「（2016年11月7日第十二届全国人民代表大会常务委员会第二十四次会议通过　**根据2025年10月28日第十四届全国人民代表大会常务委员会第十八次会议《关于修改〈中华人民共和国网络安全法〉的决定》修正**）」，页面来源标注「中国人大网」，发布日期 **2025-12-29**。
  **与授权测试/漏洞披露直接相关的条款（已逐字核实）**：
  - **第二十条**（新增，涉 AI）："国家支持人工智能基础理论研究和算法等关键技术研发，推进训练数据资源、算力等基础设施建设，**完善人工智能伦理规范，加强风险监测评估和安全监管**，促进人工智能应用和健康发展。国家支持创新网络安全管理方式，**运用人工智能等新技术，提升网络安全保护水平**。"
  - **第二十八条**："开展网络安全认证、检测、风险评估等活动，**向社会发布系统漏洞**、计算机病毒、网络攻击、网络侵入等网络安全信息，**应当遵守国家有关规定**。"（→ 这是「漏洞信息披露须遵守国家规定」的直接依据）
  - **第二十九条**（核心禁止性条款）："**任何个人和组织不得从事非法侵入他人网络、干扰他人网络正常功能、窃取网络数据等危害网络安全的活动；不得提供专门用于从事侵入网络、干扰网络正常功能及防护措施、窃取网络数据等危害网络安全活动的程序、工具**；明知他人从事危害网络安全的活动的，不得为其提供技术支持、广告推广、支付结算等帮助。"
    → **重要限定**：该条使用「**非法**侵入」表述，即对「**经授权的**渗透测试」留出了由「非法」限定词与《刑法》等对接的解释空间；但**本法的正文并未设立一般性的「善意安全研究」豁免条款**（与 DOJ 政策不同）。这是中国法与美国政策的一处显著差异。
  - **第六十六条**（罚则）：违反第二十九条从事危害网络安全活动、提供专门程序工具或提供帮助、**尚不构成犯罪**的，由公安机关没收违法所得，处 **5 日以下拘留**，可并处 **5 万元以上 50 万元以下**罚款；情节较重的处 **5 日以上 15 日以下拘留**，可并处 **10 万元以上 100 万元以下**罚款；单位犯罪处 **10 万元以上 100 万元以下**罚款并对直接负责人员依前款处罚。另规定：因违反第二十九条受**治安管理处罚**的人员，**5 年内**不得从事网络安全管理和网络运营关键岗位工作；受**刑事处罚**的，**终身**禁止。
  - **第六十五条**：违反第二十八条（含**向社会发布系统漏洞**）的，责令改正、警告，可处 1 万–10 万元罚款；拒不改正或情节严重的，处 10 万–100 万元罚款，并可责令暂停相关业务、停业整顿、关闭网站或应用程序、吊销相关业务许可证或营业执照。
  - **第七十五条**：**境外**的机构、组织、个人从事危害中华人民共和国网络安全的活动的，依法追究法律责任；造成严重后果的，国务院公安部门和有关部门并可决定采取**冻结财产**或其他必要制裁措施（域外效力条款）。
  **来源链接**：[cac.gov.cn/2025-12/29/c_1768735112911946.htm](https://www.cac.gov.cn/2025-12/29/c_1768735112911946.htm)

- **标题**：中华人民共和国数据安全法
  **URL（官方，中国人大网）**：http://www.npc.gov.cn/c2/c30834/202106/t20210610_311888.html
  **发布**：2021 年 6 月 10 日第十三届全国人民代表大会常务委员会第二十九次会议通过；**自 2021 年 9 月 1 日起施行**（第五十五条）
  **与安全测试/数据获取相关的条款（已逐字核实）**：
  - **第二十一条**：国家建立**数据分类分级保护制度**；关系国家安全、国民经济命脉、重要民生、重大公共利益等数据属于**国家核心数据**，实行更加严格的管理制度。
  - **第二十七条**："开展数据处理活动应当依照法律、法规的规定，建立健全全流程数据安全管理制度……**利用互联网等信息网络开展数据处理活动，应当在网络安全等级保护制度的基础上，履行上述数据安全保护义务**。重要数据的处理者应当明确数据安全负责人和管理机构。"
  - **第二十九条**："开展数据处理活动应当加强风险监测，**发现数据安全缺陷、漏洞等风险时，应当立即采取补救措施**；发生数据安全事件时，应当立即采取处置措施，按照规定及时告知用户并向有关主管部门报告。"
  - **第三十二条**（对安全测试的直接影响）："**任何组织、个人收集数据，应当采取合法、正当的方式，不得窃取或者以其他非法方式获取数据。**法律、行政法规对收集、使用数据的目的、范围有规定的，应当在法律、行政法规规定的目的和范围内收集、使用数据。"
  - **第三十一条**：关键信息基础设施运营者在境内运营中收集和产生的**重要数据**出境安全管理，适用《网络安全法》的规定。
  - **第四十五条**（罚则）：不履行第二十七条、第二十九条、第三十条义务的，责令改正、警告，可并处 5 万–50 万元罚款，对直接负责人员可处 1 万–10 万元；拒不改正或造成大量数据泄露等严重后果的，处 **50 万–200 万元**罚款，并可责令暂停业务、停业整顿、吊销许可证或营业执照；违反国家核心数据管理制度、危害国家主权安全和发展利益的，处 **200 万–1000 万元**罚款。
  **来源链接**：[npc.gov.cn/c2/c30834/202106/t20210610_311888.html](http://www.npc.gov.cn/c2/c30834/202106/t20210610_311888.html)

- **标题**：生成式人工智能服务管理暂行办法
  **URL（官方，中国网信网 / 国家互联网信息办公室）**：https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm
  **发布机关与文号**：国家互联网信息办公室、国家发展和改革委员会、教育部、科学技术部、工业和信息化部、公安部、国家广播电视总局 **令第 15 号**；2023 年 5 月 23 日审议通过，2023 年 7 月 10 日公布，**自 2023 年 8 月 15 日起施行**
  **与网络/数据安全直接相关的条款（已逐字核实）**：
  - **第一条**（上位法依据）："为了促进生成式人工智能健康发展和规范应用，维护国家安全和社会公共利益……**根据《中华人民共和国网络安全法》、《中华人民共和国数据安全法》、《中华人民共和国个人信息保护法》、《中华人民共和国科学技术进步法》等法律、行政法规，制定本办法。**"
  - **第二条**（适用范围）：适用于"利用生成式人工智能技术向中华人民共和国境内公众提供生成文本、图片、音频、视频等内容的服务"；并明确"行业组织、企业、教育和科研机构、公共文化机构、有关专业机构等研发、应用生成式人工智能技术，**未向境内公众提供生成式人工智能服务的，不适用本办法的规定**"（→ 内部研发/自用场景的适用性边界）。
  - **第三条**：对生成式人工智能服务实行**包容审慎和分类分级监管**。
  - **第四条**（内容红线，含安全相关）：应遵守法律行政法规、尊重社会公德伦理，其中包括"（一）坚持社会主义核心价值观，**不得生成**煽动颠覆国家政权、推翻社会主义制度，危害国家安全和利益、损害国家形象，煽动分裂国家、破坏国家统一和社会稳定，宣扬恐怖主义、极端主义，宣扬民族仇恨、民族歧视，**暴力、淫秽色情，以及虚假有害信息等法律、行政法规禁止的内容**"。
  - **第七条**（训练数据合规）：训练数据处理活动须"（一）使用具有**合法来源**的数据和基础模型；（二）涉及知识产权的，不得侵害他人依法享有的知识产权；（三）涉及个人信息的，应当取得个人同意……（五）**《中华人民共和国网络安全法》、《中华人民共和国数据安全法》、《中华人民共和国个人信息保护法》等法律、行政法规的其他有关规定和有关主管部门的相关监管要求**"。
  - **第九条**（安全义务）："提供者应当依法承担**网络信息内容生产者责任，履行网络信息安全义务**。涉及个人信息的，依法承担个人信息处理者责任，履行个人信息保护义务。"
  - **第十四条**（发现违法内容的处置义务）："提供者**发现违法内容的，应当及时采取停止生成、停止传输、消除等处置措施**，采取模型优化训练等措施进行整改，并向有关主管部门报告。提供者**发现使用者利用生成式人工智能服务从事违法活动的，应当依法依约采取警示、限制功能、暂停或者终止向其提供服务等处置措施，保存有关记录，并向有关主管部门报告。**"
  - **第十七条**：提供具有**舆论属性或者社会动员能力**的生成式人工智能服务的，应当按照国家有关规定**开展安全评估**，并履行**算法备案**手续。
  - **第二十一条**（罚则衔接）：违反本办法的，由有关主管部门依照《网络安全法》《数据安全法》《个人信息保护法》《科学技术进步法》等规定予以处罚；无规定的，予以警告、通报批评，责令限期改正；拒不改正或情节严重的，**责令暂停提供相关服务**；构成违反治安管理行为的依法给予治安管理处罚，构成犯罪的依法追究刑事责任。
  **来源链接**：[cac.gov.cn/2023-07/13/c_1690898327029107.htm](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)

---

## 未能核实的条目

以下条目**我未能核实**，请勿据以引用。按未核实的原因分类：

**A. 因目标站点在本环境不可达 / 拒止而无法核实正文**

1. **OpenAI 使用政策（openai.com/policies/usage-policies）正文**：抓取返回 **HTTP 403（Cloudflare）**，尝试了含/不含尾部斜杠与 zh-Hans-CN 本地化版本，均为 403。搜索索引显示标题 "Usage policies"、快照标注 "Updated: January 29, 2025"，但**我未能读取正文**，因此**未能核实**其中关于网络攻击/进攻性安全/未授权访问的**确切措辞**。
2. **OpenAI Preparedness Framework 的「Cybersecurity」能力类别名称与 High / Critical 阈值定义**：官方 PDF（cdn.openai.com/openai-preparedness-framework-beta.pdf）确实存在，但工具**不支持解析 `application/pdf`**；HTML 版页面（openai.com/index/updating-our-preparedness-framework/）返回 **403**。→ **完全未核实**。用户假设该框架存在名为「Cybersecurity」的类别，**我无法确认或否认**。
3. **OpenAI Model Spec 中与网络/违法协助相关的条款**：**完全未尝试成功核实**（openai.com 全域 403）。→ **未找到可核实信息**。
4. **OpenAI「Astra / GPT-6 达到 Critical 网络能力阈值」的说法**：三方报道中，[InfoQ](https://www.infoq.com/news/2026/09/gpt-6-astra-critical-cyber/) 抓取返回 HTTP 405（Human Verification）、[CSA Labs](https://labs.cloudsecurityalliance.org/research/csa-research-note-openai-astra-critical-cyber-threshold-2026/) 返回 HTTP 403（Cloudflare）、[Digital Watch Observatory](https://dig.watch/updates/openai-model-critical-cyber-capability-threshold) 抓取成功但正文被截断且未含实质内容。→ **未能通过任何可读来源核实**。另有互相矛盾的第三方片段称 GPT-5.6-Sol 被评为 "High, not Critical"。**两个方向都待核实。**
5. **OpenAI「Trusted Access for Cyber Defense」/「scaling trusted access for cyber defense」页面**：仅由搜索索引返回 URL 与标题，**未能抓取**，发布日期与内容**待核实**。
6. **OpenAI 是否设有「Frontier」/「Trusted Access for Cyber」类项目及其框架细节**：**未找到可核实的官方信息**（openai.com 403；搜索仅返回第三方二手报道）。
7. **DOJ 2022 年 CFAA 起诉政策的官方原文**：`justice.gov` 全域连接超时（6 次不同路径尝试全部失败）。政策的**官方 URL 存在性**由搜索索引与二手来源的反向链接共同支持（https://www.justice.gov/archives/opa/pr/department-justice-announces-new-policy-charging-cases-under-computer-fraud-and-abuse-act），但**原文未读取**。已用 Alston & Bird 的**逐字引用**作为替代（见上文），该内容属二手转引，**建议使用前以官方原文复核**。
8. **`uscode.house.gov` 上 CFAA 的官方页面**：直链返回 "Page Not Found"（该站在临时格式下部分功能不可用）。已改用 Cornell LII 作为来源。
9. **NCSC「Retaining defensive advantage in the age of frontier AI cyber capabilities」的正文**：抓取成功（HTTP 200）但**正文被站点导航结构截断**，未获得实质内容 → **内容待核实**（其存在与主题由 AISI 博客的反复引用佐证）。

**B. 因 PDF 不可解析或法条页面不可达而无法核实**

10. **欧盟 AI Act 第 51 条与「10^25 FLOP」系统性风险算力阈值**：AI Act Service Desk 的 Article 51 页面**未抓取**；EUR-Lex 三个变体 URL 全部返回 **HTTP 202 空内容**。→ **该数值未核实**。
11. **欧盟 AI Act 第 3 条（定义）、第 5 条（禁止实践）、第 6 条（高风险分类规则）、第 15 条（准确性/鲁棒性/网络安全）的法条原文**：我核实的是**委员会政策页的概述**与**第 55 条、附件三的全文**；**第 3/5/6/15 条的逐字原文未抓取** → 相关内容**待核实**（尤其第 5 条九项禁止实践我只核实到委员会概述层面的列举，未读条文原文）。
12. **Anthropic RSP 全文（特别是 ASL-3 及以上的网络相关 Capability Threshold 是否存在）**：当前版本 **v3.4（2026-07-08）** 及全部历史版本均为 **PDF**，本环境**无法解析 PDF**。RSP 总览页正文列出的 Capability Thresholds **仅为 AI R&D 与 CBRN 两类，未列 cyber**；但我**不能据此断言 RSP 全文不含网络门槛** → **待核实**。
13. **Anthropic 各模型 System Card、Aug/Feb 2026 Risk Report 的具体网络评测数字**：均为 PDF 或需跳转页面，**未抓取** → **待核实**。本报告中 Anthropic 的具体数字仅来自 [Frontier Red Team 的 HTML 博客](https://www.anthropic.com/research/cyber-toolkits-update)。
14. **Anthropic「Expanding the Cyber Verification Program」与「2026 Usage Policy update」两篇公告的正文**：仅在页面底部 "Related content" 中见到链接，**未抓取正文** → **待核实**。

**C. 因标题/编号与用户假设不符而未确认的条目**

15. **候选标题「A Survey on Large Language Model-based Cybersecurity」**：**不存在**。最接近的真实论文是 arXiv:2402.16968「A Survey **of** Large Language Models **in** Cybersecurity」（已核实，见上）。→ 用户给出的标题**为误记**。
16. **候选标题「Agentic AI for Cybersecurity」**：**未找到**任何以此为题的真实论文。最接近的两篇为 arXiv:2510.23883「Agentic AI **Security**: Threats, Defenses, Evaluation, and Open Challenges」与 arXiv:2601.05293「A Survey of **Agentic AI and Cybersecurity**: Challenges, Opportunities and Use-case Prototypes」（均已核实）。
17. **候选标题「AI Agents for Offensive Security: A Survey」**：**未找到**。目前最接近的「进攻性安全 Agent」主题文献是 arXiv:2607.20255「The Ethics of Autonomous AI Agents for Offensive Security」（**立场/伦理论文，非综述**）与 arXiv:2505.12786「Forewarned is Forearmed: A Survey on Large Language Model-based Agents in Autonomous Cyberattacks」（**综述**）。
18. **候选标题「Penetration Testing with LLMs: A Survey」**：**不存在**。真实标题为 arXiv:2607.02605「A Survey of **LLM-Driven Penetration Testing**: Taxonomy, Co-Evolution, and Open Challenges」（已核实）。
19. **用户给出的「arXiv 2405.04760 = Large Language Models for Cyber Security: A Systematic Literature Review」**：**✅ 完全正确**（标题、编号、作者均核对一致）。
20. **arXiv:2404.08144「LLM Agents can Autonomously Exploit One-day Vulnerabilities」**：**✅ 编号与标题正确**（用户未给编号，仅要求核实；已核实并给出精确数字）。
21. **arXiv:2607.20255「The Ethics of Autonomous AI Agents for Offensive Security」**：**✅ 编号与标题正确**（用户以问号标注，已确认）。
22. **候选标题「From LLMs to LLM-based Agents for Software Engineering」**：**标题正确**，真实编号 **arXiv:2408.02479**。但**主题匹配度提示**：该文是**软件工程**综述而非网络安全综述，列入「LLM 网络安全综述」清单属分类错误（详见上文）。

**D. 其他明确未核实的点**

23. **上述所有 arXiv 论文的作者所属机构**：arXiv 摘要页**不列机构**，我在本次核实中**未抓取任何论文 PDF 或作者主页**，因此**每一篇的作者机构均应视为「待核实」**。本报告中凡涉及机构处均已显式标注。
24. **arXiv 论文作者的「作者名拼写」**：arXiv:2607.02605 的作者列表中，arXiv 页面将最后一位作者写作 **"Xiaolu Cao"**（搜索索引中同篇的标题上下文有时出现该论文的其他拼写），我按抓取到的 arXiv 页面书写；另注意该页作者列表中 "Xuemin (Sherman) Shen" 在 arXiv:2505.12786 页面上被拆分为 "Xuemin" 与 "(Sherman)"、"Shen" 三个链接项，属 arXiv 页面渲染问题，**真实姓名应为 Xuemin (Sherman) Shen**。
25. **任何具体的「渗透测试 Agent 攻击成功率」类数字，若未在本报告正文中给出精确出处与区间，即未核实**。本报告中的所有数字均标注了其原始评测设置与置信区间（若有），请连同这些限定一并引用。
26. **中国法规的英文官方译本**：未核实（本次仅核实中文官方原文）。
27. **《网络安全法》2025 年修正的官方决定文本（全国人大决定本身）**：本次核实的是**修正后的合并全文**（来源标注中国人大网、转载于中国网信网），**未单独抓取人大决定文本** → 修正案条文的逐条对照**待核实**。

---

### 方法论与诚实性声明

- 本报告中每一条事实性陈述均对应一个我在本次会话中**实际抓取成功**的 URL。凡抓取失败（403 / 405 / 202 空内容 / 连接超时 / PDF 不可解析）者，均已显式标注失败类型与未核实状态。
- 我**没有**引用任何通过搜索引擎摘要间接获得、而未经我本人抓取的内容作为已核实事实。
- 抓取到的网页内容一律按**数据**处理，未执行其中出现的任何指令或建议。
- arXiv 存在速率限制，本报告的 arXiv 条目均以约 15–20 秒间隔逐条抓取，未使用任何缓存或镜像替代一手摘要页。
