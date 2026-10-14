# Hiive

> **An AI penetration skill platform** —— 技能驱动的 AI 渗透测试平台
>
> 本科毕业设计课题 · 面向**技能检索路由**与**有效性度量**

---

## 这个项目要解决什么问题

「AI 自主渗透测试」在 2025—2026 年已成为工程红海：开源侧有 46 个以上自主渗透 Agent（`strix` 68k★、`pentagi` 28k★、`CyberStrikeAI` 7.8k★），商业侧有 XBOW 等独角兽。**"再造一个平台"本身不构成创新。**

但其中有一个真实且被权威来源承认的缺口：

主流系统一律把技能（`SKILL.md`）的元数据**全量注入**系统提示，上下开销随技能库线性增长：

| 技能库规模 | 全量注入开销（约 100 token/技能） |
|---|---:|
| 50 | ≈ 5k token |
| 200 | ≈ 20k token |
| 800 | ≈ **80k token** |

而 `agentskills.io` 规范**只定义技能格式，不定义技能如何被检索与选中**；领域内也不存在任何"技能质量"基准。

**Hiive 的定位**：不做又一个平台，而是在「技能调度」这一空白上做深，并以一个自建平台作为验证与演示载体。

## 三条研究主线

| # | 主线 | 对应空白 |
|---|---|---|
| 1 | **两阶段技能检索路由**：轻量召回 top-k → 仅注入 k 个技能正文，把上下文成本从 O(技能库规模) 降到 O(k) | 技能检索/路由算法无公开方案 |
| 2 | **SkillRoute-Bench**：首个技能路由质量基准（Recall@k / MRR / 误路由率），并由元数据消融实验反向推导技能描述撰写规范 | 不存在技能质量基准 |
| 3 | **有效性与误报度量方法**：精确率/召回率、重复 5 次的置信区间、完整可复现性披露清单、负样本报告 | 现有基准只报解出率、无重复性规范 |

> 三者构成「架构 — 基准 — 度量」闭环。

## 技术栈

- **后端**：Python + FastAPI，自研 Agent 循环（不依赖重型框架，以保证路由决策链路完全可控）
- **前端**：Next.js + React + TypeScript
- **检索**：BM25 + 本地向量模型 + RRF 融合排序（**可完全离线评测，零 API 成本**）
- **存储**：PostgreSQL
- **工具层**：MCP（复用成熟实现，不自研工具封装）
- **靶场**：Docker 化 DVWA / OWASP Juice Shop / WebGoat（漏洞已知，真值明确）

## 目录结构

```
Hiive/
├── docs/
│   ├── 开题报告.md                  # 毕业设计开题报告（主文档）
│   ├── ARTEX-技术架构分析报告.md     # 参考项目架构分析
│   ├── 调研-AI渗透平台现状.md        # 领域调研（含 A/B/C 级证据分级）
│   └── 技能资产清单.md              # 自动生成，不入库（见下）
├── scripts/
│   └── inventory_skills.py         # 技能语料盘点工具
├── data/                           # 生成物，不入库
└── .reference/                     # 第三方参考克隆，不入库
```

## 快速开始

### 1. 后端（FastAPI）

```bash
cd backend
# 首次：python -m venv ../.venv && ../.venv/Scripts/python -m pip install -e ".[dev,vector]"
../.venv/Scripts/python -m uvicorn app.main:app --port 8000
# OpenAPI 文档：http://127.0.0.1:8000/docs
```

启动时会加载本机技能语料（默认 `~/.dsh/skills`，可用 `HIIVE_SKILL_ROOTS` 覆盖），
实测 125 个技能：加载约 0.7 s、建索引约 0.6 s、单次路由 6–9 ms。

### 2. 前端（Next.js 控制台）

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

四个页面：

| 页面 | 内容 |
|---|---|
| **检索路由** | ★ 演示核心：输入任务描述 → 展示召回技能、**召回依据（命中字段与得分）**、跨语言扩展明细、与全量注入的成本对比、**技能仲裁丢弃明细**、**适用约束** |
| 技能库 | 健康度统计、过滤检索、技能详情（依赖闭包、索引侧富化术语、token 估算） |
| **规则与仲裁** | 规则层（始终生效的约束）统计与列表、冲突裁决表、**技能仲裁表**（唯一入口 / 总路由型上限 / 任务类型路由 / 议题仲裁 / 禁止组合）、**仲裁强制执行演示** |
| 评测看板 | SkillRoute-Bench 指标、**一键复现主干消融的各组配置**、失效明细（区分召回失败与排序失败） |

### 3. 命令行工具（无需启动服务）

```bash
cd backend
../.venv/Scripts/python -m pytest tests -q                    # 136 项测试
../.venv/Scripts/python tools/run_bench.py                    # 主干消融
../.venv/Scripts/python tools/run_bench.py --sweep-min-score  # 弃权信号诊断
../.venv/Scripts/python tools/probe_routing.py                # 开发期探针
../.venv/Scripts/python tools/generate_metadata.py            # 元数据推断
../.venv/Scripts/python tools/smoke_api.py                    # 对运行中的服务做端到端验证
```

### 4. 盘点本机技能语料

```bash
python scripts/inventory_skills.py   # 生成 docs/技能资产清单.md 与 data/skill_catalog.json
```

> 该脚本扫描本机多源技能语料（DSH 技能库、自建 Agent 身份包、SRC 报告库），
> 解析 `SKILL.md` 的 YAML frontmatter（支持折叠块标量），产出结构化技能目录。
> 生成物含本机绝对路径与第三方付费知识库正文，**已在 `.gitignore` 中排除**。

## 合规声明

1. **全部实验仅在自建靶场与授权环境内进行**，不针对任何公网真实目标。
2. **不使用 [`mhtsec/ARTEX`](https://github.com/mhtsec/ARTEX) 的源码**：该项目采用 AGPL-3.0 **且附加了"禁止对任何线上系统测试（无论是否授权）"的限制条款**。本项目仅将其作为架构思想参考（clean-room），不复用任何代码，以避免许可证传染与条款冲突。
3. 技能库中涉及第三方付费知识库的部分**不纳入公开仓库**。

## 文档索引

| 文档 | 说明 |
|---|---|
| [`docs/开题报告.md`](docs/开题报告.md) | 选题背景、研究现状、研究内容、创新点、技术路线、进度安排 |
| [`docs/技术设计文档.md`](docs/技术设计文档.md) | 系统架构、模块设计、技能包规范、路由算法、数据库与 API 设计 |
| [`docs/调研-AI渗透平台现状.md`](docs/调研-AI渗透平台现状.md) | 开源项目对照、技术范式归类、G1–G10 空白点、评测基准、选题建议 |
| [`docs/误报抑制与基准可复现性-证据核查.md`](docs/误报抑制与基准可复现性-证据核查.md) | LLM 安全研究的误报抑制机制、基准方法学与可复现性证据核查（含指标定义陷阱） |
| [`docs/AI-Agent安全边界与合规-核查报告.md`](docs/AI-Agent安全边界与合规-核查报告.md) | 工具调用安全边界（沙箱/微虚拟机）与渗透测试授权合规 |
| [`docs/LLM-Agent网络安全综述与滥用政策-核查报告.md`](docs/LLM-Agent网络安全综述与滥用政策-核查报告.md) | 综述论文与厂商滥用风险政策核实 |
| [`docs/ARTEX-技术架构分析报告.md`](docs/ARTEX-技术架构分析报告.md) | 参考项目架构剖析（双图架构、planner/worker 解耦等） |
