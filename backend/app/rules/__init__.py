"""规则层（Rules）：**始终生效的约束**。

## 与技能层的本质区别（本模块的设计依据）

| | 技能（Skill） | 规则（Rule） |
|---|---|---|
| 性质 | **能力**——"该怎么做" | **约束**——"不许怎么做" |
| 加载 | **按需检索**（两阶段路由） | **始终生效** |
| 违反后果 | 做不成事 | 越界 / 误报 / 合规风险 |
| 可协商性 | 可组合、可替代 | **不可协商**（除非规则间冲突） |

把两者混在一起建模会同时失去两个性质：技能被"always-on"会让上下文爆炸，
约束被"按需加载"则会在需要它的时候恰好没被检索到。

## 冲突裁决

规则之间会冲突（实测语料中就有：`dig-scope-workflow` 要求"继续挖不问"，
而通用礼貌约定要求"等用户确认"）。因此规则层必须有**显式的裁决表**，
而不是让模型自行取舍。裁决表以**声明式数据**给出（见 `CONFLICT_RESOLUTION`），
不做 prose 解析——prose 解析不可靠，且裁决规则本身必须可审计。

## 规则体积与"始终生效"的可行性

本机 11 条规则合计约 127 KB。**显然不能全文常驻上下文**。
因此本模块采用与技能一致的分层策略：**标题 + 主题标签常驻**（约 30 token/条），
正文按需加载。这与 agentskills.io 的渐进披露是同一思路，
说明"约束层的上下文经济学"与技能层是同一个问题——这也是本课题论点的一个佐证。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{2,3}\s+(.+)$", re.MULTILINE)
_QUOTE_RE = re.compile(r"^\s*>.*$", re.MULTILINE)
_CODE_RE = re.compile(r"```.*?```", re.DOTALL)

#: 规则的主题标签与适用范围（**人工策划、可审计**）。
#:
#: 只有 11 条规则，人工映射比关键词猜测更可靠，也便于论文中直接展示与复核。
#: 字段含义：domains/phase 用于"该规则是否适用于当前路由到的技能"，
#: topics 用于展示与检索。
RULE_SCOPE: dict[str, dict] = {
    "security-research-context": {
        "domains": [], "phases": [],
        "topics": ["授权", "语境", "边界"],
        "always": True,
        "summary": "授权安全研究语境与默认边界：授权范围内、面向防御/披露/教育。",
    },
    "anti-over-moralization": {
        "domains": [], "phases": [],
        "topics": ["态度", "拒答"],
        "always": True,
        "summary": "反说教、反过度道德化、反误拒：授权研究请求按技术任务处理。",
    },
    "researcher-blackbox-whitebox": {
        "domains": [], "phases": [],
        "topics": ["主流程", "黑白盒"],
        "always": True,
        "summary": "黑盒 SRC 与白盒 0day 的主流程定义。",
    },
    "dig-scope-workflow": {
        "domains": ["network", "web"], "phases": ["recon"],
        "topics": ["范围", "种子", "测绘节奏", "持续挖"],
        "always": True,
        "summary": (
            "锁面/自由跳全流程：一种子闭环、种子队列、续挖回扫、深挖优先。"
            "要求本种子剩余活面挖完才换种，禁止用测绘冒充挖掘进度。"
        ),
    },
    "hunt-iter": {
        "domains": [], "phases": ["discovery", "exploitation"],
        "topics": ["迭代", "短表"],
        "summary": "短表迭代方式：能力迭代须落盘，但不压过范围规则。",
    },
    "src-value-hunting": {
        "domains": ["web", "api"], "phases": ["discovery"],
        "topics": ["挖什么", "漏洞类型", "优先级"],
        "summary": "SRC 挖什么、类型矩阵怎么测、力气先砸哪。",
    },
    "vuln-report-format": {
        "domains": [], "phases": ["report"],
        "topics": ["报告", "格式"],
        "always": False,
        "summary": "漏洞报告格式的**唯一**依据（两张表）。与其它规则冲突时以本规则为准。",
    },
    "cors-vuln-report-priority": {
        "domains": ["web"], "phases": ["discovery"],
        "topics": ["CORS", "不挖"],
        "summary": "CORS：**不挖**（明确排除项）。",
    },
    "skill-arbitration": {
        "domains": [], "phases": [],
        "topics": ["仲裁", "路由策略", "冲突消解"],
        "always": True,
        "summary": (
            "技能仲裁表：限定唯一入口 + 一次最多 1 个执行技能 + 禁止组合 + 议题仲裁。"
            "把 5 个抢同一触发词、4 个自称「总路由」的冲突显式消解。"
        ),
    },
    "playwright-browser-mcp": {
        "domains": ["web"], "phases": [],
        "topics": ["浏览器", "工具"],
        "summary": "浏览器操作统一走 Playwright MCP。",
    },
    "desktop-task-folder": {
        "domains": [], "phases": ["recon", "discovery", "exploitation"],
        "topics": ["任务目录", "落盘"],
        "summary": "任务目录规范：资产/JS/报告的分目录约定。",
    },
    "skill-as-boost": {
        "domains": [], "phases": [],
        "topics": ["技能定位"],
        "always": True,
        "summary": "技能与知识库只能**增强**能力，不能限制能力上限。",
    },
}

#: 显式冲突裁决表（来源：用户语料 `AGENTS.md` 的"冲突时"段落，人工转录为数据）。
#:
#: 键为**议题**，值为胜出规则名。`reason` 供审计与展示。
CONFLICT_RESOLUTION: dict[str, dict[str, str]] = {
    "挖什么（目标筛选与类型优先级）": {
        "winner": "src-value-hunting",
        "reason": "挖什么问题只认 src-value-hunting。",
    },
    "漏洞报告格式": {
        "winner": "vuln-report-format",
        "reason": "报告格式只跟 vuln-report-format（唯一依据）。",
    },
    "是否测试 CORS": {
        "winner": "cors-vuln-report-priority",
        "reason": "CORS 明确不挖，该规则压过通用类型矩阵。",
    },
    "白盒审计流程": {
        "winner": "researcher-blackbox-whitebox",
        "reason": "白盒流程认 researcher-blackbox-whitebox。",
    },
    "范围与是否继续挖": {
        "winner": "dig-scope-workflow",
        "reason": "范围/持续挖以 dig-scope-workflow 为准，**压过**默认的「等用户继续」礼貌约定。",
    },
    "能力迭代落盘": {
        "winner": "hunt-iter",
        "reason": "迭代落盘认 hunt-iter，但它**不压过**范围规则。",
    },
    "技能与规则冲突": {
        "winner": "__rules__",
        "reason": "技能/知识库与 rules 冲突时，**以 rules 为准**。",
    },
}


@dataclass
class Rule:
    """一条约束。"""

    name: str
    title: str = ""
    body: str = ""
    topics: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    always: bool = False
    summary: str = ""
    path: str = ""

    @property
    def chars(self) -> int:
        return len(self.body)

    def estimated_tokens(self) -> int:
        """正文 token 估算（与 `Skill` 同一经验系数，便于横向比较）。"""
        return int(self.chars / 1.6)

    def header(self) -> str:
        """常驻部分：标题 + 主题 + 摘要（约 30–50 token）。"""
        return f"[规则] {self.name}: {self.summary or self.title}"

    def to_dict(self, include_body: bool = False) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "topics": self.topics,
            "domains": self.domains,
            "phases": self.phases,
            "always": self.always,
            "summary": self.summary,
            "chars": self.chars,
            "estimated_tokens": self.estimated_tokens(),
            "path": self.path,
            **({"body": self.body} if include_body else {}),
        }


def _extract_title(text: str) -> str:
    m = _TITLE_RE.search(text)
    return m.group(1).strip() if m else ""


def _first_paragraph(text: str) -> str:
    """取正文首个非空、非引用、非标题段落——用作规则的自动摘要兜底。"""
    body = _CODE_RE.sub("", text)
    body = _QUOTE_RE.sub("", body)
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        return s[:200]
    return ""


class RuleSet:
    """规则集合。"""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules: dict[str, Rule] = {r.name: r for r in (rules or [])}
        self.parse_errors: list[tuple[str, str]] = []

    # ---------------------------------------------------------------- 加载

    @classmethod
    def load(cls, root: Path, scope: dict[str, dict] | None = None) -> "RuleSet":
        scope = scope or RULE_SCOPE
        rs = cls()
        if not root.exists():
            rs.parse_errors.append((str(root), "路径不存在"))
            return rs
        for path in sorted(root.glob("*.md")):
            name = path.stem
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                rs.parse_errors.append((str(path), str(e)))
                continue
            spec = scope.get(name, {})
            rs.rules[name] = Rule(
                name=name,
                title=_extract_title(text) or name,
                body=text,
                topics=list(spec.get("topics", [])),
                domains=list(spec.get("domains", [])),
                phases=list(spec.get("phases", [])),
                always=bool(spec.get("always", False)),
                summary=str(spec.get("summary") or _first_paragraph(text)),
                path=str(path),
            )
        return rs

    # ---------------------------------------------------------------- 适用性

    def applicable(
        self, domains: list[str] | None = None, phase: str = "", always_only: bool = False
    ) -> list[Rule]:
        """返回适用于给定技能（域 + 阶段）的规则。

        判定规则（**刻意收紧**）：

        1. `always=True` 的规则恒适用；
        2. 其余规则要求**域或阶段有交集**才适用；
        3. **未声明任何范围且非 `always` 的规则不适用**——它们只能按需检索。

        **第 3 条是实测修正**：初版把"无域无阶段"当作全局适用，结果 12 条规则
        全部被附加到每次路由上，"适用约束"完全失去区分能力（等于没做）。
        宁可少附加、由调用方按需取正文，也不要附加一堆无关约束。
        """
        domains = domains or []
        out: list[Rule] = []
        for r in self.rules.values():
            if always_only and not r.always:
                continue
            if r.always:
                out.append(r)
                continue
            if r.domains and set(r.domains) & set(domains):
                out.append(r)
                continue
            if r.phases and phase and phase in r.phases:
                out.append(r)
        return out

    def conflicts_for(self, rule_names: list[str]) -> list[dict]:
        """返回涉及给定规则的冲突裁决条目。"""
        out = []
        for topic, spec in CONFLICT_RESOLUTION.items():
            if spec["winner"] in rule_names or spec["winner"] == "__rules__":
                out.append({"topic": topic, **spec})
        return out

    # ---------------------------------------------------------------- 视图

    def headers(self) -> list[str]:
        """常驻上下文的规则头（标题 + 摘要），非全文。"""
        return [r.header() for r in self.rules.values()]

    def stats(self) -> dict:
        total_chars = sum(r.chars for r in self.rules.values())
        header_tokens = sum(int(len(r.header()) / 1.6) + 4 for r in self.rules.values())
        return {
            "count": len(self.rules),
            "total_chars": total_chars,
            "total_estimated_tokens": int(total_chars / 1.6),
            "always_on": sum(1 for r in self.rules.values() if r.always),
            "header_tokens_if_all_headers_kept": header_tokens,
            "conflict_topics": len(CONFLICT_RESOLUTION),
            "parse_errors": len(self.parse_errors),
            "note": (
                "规则为**始终生效的约束**，但全文不可常驻上下文（本机 11 条约 "
                f"{int(total_chars / 1.6)} token）。本实现只常驻规则头"
                f"（约 {header_tokens} token），正文按需加载——与技能的渐进披露同源。"
            ),
        }

    def to_dict(self, include_body: bool = False) -> dict:
        return {
            **self.stats(),
            "rules": [r.to_dict(include_body=include_body) for r in self.rules.values()],
            "conflict_resolution": [
                {"topic": k, **v} for k, v in CONFLICT_RESOLUTION.items()
            ],
        }
