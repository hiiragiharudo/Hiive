"""技能仲裁表：把人工撰写的路由仲裁规则解析为**机器可强制的约束**。

## 为什么这个模块很重要

本课题用实测数据发现了一个问题：**伞状技能（umbrella skills）霸榜**——
它们的中文长描述覆盖所有主题，因文档长度偏置而垄断检索结果
（见技术设计文档 §6.6）。

而笔者的语料中**已经存在一份人工撰写的答案**：
`rules/skill-arbitration.md`（18.7 KB），它开门见山地描述了同一个问题：

> 已装 9 个技能，**其中 5 个在 description 里互相抢同一个触发词**
> （"渗透测试"被 5 个技能同时声明），**4 个自称"总路由/第一步/强制入口"**。
> **若不做仲裁，同一句「挖 XX 公司」我可能选 4 条不同路线 → 行为不一致。
> 这就是"冲突"的实质。**

这段话是对本课题核心问题的**独立实战印证**，而且给出了业界实践中真正有效的解法：
**限定入口 + 限制执行技能数 + 禁止组合 + 议题仲裁**。

因此本模块把这四类约束**解析为结构化数据并在路由器中强制**，
而不是让模型"读了之后自己注意"。

## 与 `app/rules` 的关系

`app/rules` 处理的是**约束文本的加载与适用性**（哪些规则对该技能生效）；
本模块处理的是**仲裁表这一类特殊规则的结构化解析与执行**。
仲裁表不是普通约束——它是**可执行的路由策略**。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_TICK_RE = re.compile(r"`([^`]+)`")
_HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
#: "任何 3 个以上「总路由」型技能同时加载" 这类计数约束
_COUNT_RE = re.compile(r"(\d+)\s*个以上")
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_SEP_ROW_RE = re.compile(r"^\|[\s:\-|]+\|\s*$")

#: §0 表格中"自称"列的**总路由型标志词**。
#:
#: **为什么不能把 §0 表格的所有行都当作总路由型**：实测该表列了 5 个技能，
#: 但原文明确说只有 "**4 个**自称总路由/第一步/强制入口"——第 5 个
#: （`cve-yu2`「独立的 CVE/白盒审计能力」）是被列出来做对比的，不是总路由型。
#: 把它算进去会让上限约束过严，误丢正常技能。
UMBRELLA_MARKERS = (
    "总路由", "入口", "必须触发", "primary router", "强制", "建议阅读",
    "第一步", "entry p0", "质量门", "也要触发",
)


def _split_sections(text: str) -> dict[str, str]:
    """按 `## ` 标题切分。键为标题（保持原文），值为该节正文。"""
    out: dict[str, str] = {}
    parts = _HEADING_RE.split(text)
    # parts = [前言, 标题1, 正文1, 标题2, 正文2, ...]
    for i in range(1, len(parts) - 1, 2):
        out[parts[i].strip()] = parts[i + 1]
    return out


def _parse_table(section: str) -> list[list[str]]:
    """解析节内的第一个 Markdown 表格为二维列表（不含表头分隔行）。"""
    rows: list[list[str]] = []
    for raw in section.splitlines():
        if _SEP_ROW_RE.match(raw):
            continue
        m = _TABLE_ROW_RE.match(raw.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        rows.append(cells)
    # 首行为表头，去掉
    return rows[1:] if rows else []


def _names(cell: str) -> list[str]:
    """取单元格中的反引号名（去重保序），**过滤掉文件路径**。

    实测：§3 的单元格里混有 `vuln-report-format.md`、
    `references/workflow/reporting/report_generator_EN.md` 这类**文件路径**，
    它们不是技能名，混入会污染仲裁结果。
    """
    out: list[str] = []
    for n in _TICK_RE.findall(cell):
        n = n.strip()
        if not n or "/" in n or n.endswith((".md", ".py", ".json", ".yaml", ".yml")):
            continue
        if n not in out:
            out.append(n)
    return out


#: kebab-case 技能名（§1 的代码块里技能名没有反引号，需按形态提取）
_KEBAB_RE = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b")


def _kebab_names(text: str, prefer: list[str] | None = None) -> list[str]:
    """从自由文本提取 kebab-case 标识符；`prefer` 非空时优先只保留其中的。"""
    found = _KEBAB_RE.findall(text)
    if prefer:
        hit = [n for n in found if n in prefer]
        if hit:
            return hit
    return found


def _first_name(cell: str) -> str:
    ns = _names(cell)
    return ns[0] if ns else ""


# --------------------------------------------------------------------------- 结构


@dataclass
class TaskRoute:
    """§2 任务类型 → 加载哪个执行技能、不加载什么。"""

    task_type: str
    load: list[str] = field(default_factory=list)
    not_load: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"task_type": self.task_type, "load": self.load, "not_load": self.not_load}


@dataclass
class TopicArbiter:
    """§3 议题 → 权威技能。"""

    topic: str
    winners: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {"topic": self.topic, "winners": self.winners, "reason": self.reason}


@dataclass
class ForbiddenCombo:
    """§5 禁止同时加载的组合。

    `skills` 为空且 `max_count>0` 时表示**计数约束**（"任何 3 个以上 X 型技能"）。
    """

    skills: list[str] = field(default_factory=list)
    reason: str = ""
    max_count: int = 0
    applies_to: str = ""

    def is_count_constraint(self) -> bool:
        return not self.skills and self.max_count > 0

    def to_dict(self) -> dict:
        return {
            "skills": self.skills,
            "reason": self.reason,
            "max_count": self.max_count,
            "applies_to": self.applies_to,
        }


@dataclass
class ArbitrationOutcome:
    """一次仲裁执行的结果。"""

    kept: list[str] = field(default_factory=list)
    #: (技能名, 丢弃原因)
    dropped: list[tuple[str, str]] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kept": self.kept,
            "dropped": [{"name": n, "reason": r} for n, r in self.dropped],
            "applied_constraints": self.applied,
        }

    def summary(self) -> str:
        if not self.dropped:
            return f"仲裁通过（{len(self.kept)} 项，未触发约束）"
        return (f"仲裁丢弃 {len(self.dropped)} 项："
                + "；".join(f"{n}（{r}）" for n, r in self.dropped))


@dataclass
class ArbitrationTable:
    """技能仲裁表。"""

    raw_path: str = ""
    #: §1 唯一入口（恒定加载，不参与竞争）
    entry: list[str] = field(default_factory=list)
    #: §0 自称"总路由/入口"的技能
    umbrella_skills: list[str] = field(default_factory=list)
    #: §2 "然后在下面按任务类型最多再加载 1 个执行技能"
    max_execution_skills: int = 1
    #: §5 计数约束推出的"总路由型"技能同时加载上限
    max_umbrella_skills: int = 2
    task_routes: list[TaskRoute] = field(default_factory=list)
    topics: list[TopicArbiter] = field(default_factory=list)
    forbidden: list[ForbiddenCombo] = field(default_factory=list)
    #: §6 一句话总则
    motto: str = ""
    parse_warnings: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------- 解析

    @classmethod
    def parse(cls, path: Path) -> "ArbitrationTable":
        t = cls(raw_path=str(path))
        if not path.exists():
            t.parse_warnings.append(f"仲裁表不存在: {path}")
            return t

        text = path.read_text(encoding="utf-8", errors="replace")
        sections = _split_sections(text)

        # ---- §0 自称入口的技能（按"自称"列的标志词判定，而非收录全表） ----
        for title, body in sections.items():
            if title.startswith("0."):
                for row in _parse_table(body):
                    n = _first_name(row[0]) if row else ""
                    if not n:
                        continue
                    claim = row[1].lower() if len(row) > 1 else ""
                    if any(m.lower() in claim for m in UMBRELLA_MARKERS):
                        t.umbrella_skills.append(n)

        # ---- §1 唯一入口 ----
        # 实测：§1 的代码块里技能名**没有反引号**（"任何安全任务 → 【必定】先加载 src-6k-skill"），
        # 因此先用反引号提取，失败则按 kebab-case 形态提取，并与 §0 的总路由名单求交。
        for title, body in sections.items():
            if title.startswith("1."):
                fence = re.search(r"```(.*?)```", body, re.DOTALL)
                if fence:
                    names = _names(fence.group(1))
                    if not names:
                        names = _kebab_names(fence.group(1), t.umbrella_skills)
                    if not names:
                        names = _kebab_names(body, t.umbrella_skills)
                    t.entry.extend(n for n in names if n not in t.entry)
                if not t.entry:
                    t.parse_warnings.append("§1 未解析出唯一入口")

        # ---- §2 任务类型路由 ----
        for title, body in sections.items():
            if title.startswith("2."):
                if "最多再加载 1 个" in body or "最多 1 个" in body:
                    t.max_execution_skills = 1
                for row in _parse_table(body):
                    if len(row) < 2:
                        continue
                    task = re.sub(r"\*\*", "", row[0])
                    load = _names(row[1]) if len(row) > 1 else []
                    not_load = _names(row[2]) if len(row) > 2 else []
                    if task:
                        t.task_routes.append(TaskRoute(task, load, not_load))

        # ---- §3 议题仲裁 ----
        for title, body in sections.items():
            if title.startswith("3."):
                for row in _parse_table(body):
                    if len(row) < 2:
                        continue
                    topic = re.sub(r"\*\*", "", row[0])
                    winners = _names(row[1])
                    reason = re.sub(r"\*\*", "", row[2]) if len(row) > 2 else ""
                    if topic and winners:
                        t.topics.append(TopicArbiter(topic, winners, reason[:200]))

        # ---- §5 禁止组合 ----
        for title, body in sections.items():
            if title.startswith("5."):
                for row in _parse_table(body):
                    if len(row) < 2:
                        continue
                    reason = re.sub(r"\*\*", "", row[1])
                    names = _names(row[0])
                    if len(names) >= 2:
                        t.forbidden.append(ForbiddenCombo(names[:2], reason[:200]))
                        continue
                    m = _COUNT_RE.search(row[0])
                    if m:
                        # "任何 N 个以上『总路由』型技能同时加载" → 上限为 N-1
                        t.forbidden.append(
                            ForbiddenCombo(
                                [], reason[:200], max_count=int(m.group(1)) - 1,
                                applies_to="umbrella",
                            )
                        )
                        if t.max_execution_skills >= 1:
                            t.max_umbrella_skills = int(m.group(1)) - 1
                    else:
                        t.parse_warnings.append(f"§5 未能解析的行：{row[0][:60]}")

        # ---- §6 总则 ----
        for title, body in sections.items():
            if title.startswith("6."):
                fence = re.search(r"```(.*?)```", body, re.DOTALL)
                if fence:
                    t.motto = fence.group(1).strip()

        if not t.umbrella_skills:
            t.parse_warnings.append("§0 未解析出自称入口的技能")
        if not t.forbidden:
            t.parse_warnings.append("§5 未解析出禁止组合")
        return t

    # ---------------------------------------------------------------- 执行

    def enforce(self, candidate_names: list[str]) -> ArbitrationOutcome:
        """对**已排序**的候选技能执行仲裁约束。

        参数 `candidate_names` 必须按路由排序（优者在前）——仲裁丢弃时
        **保留排名更高者**，从而在不引入新偏好的前提下消解冲突。

        执行顺序：① 禁止组合配对 → ② "总路由"型计数上限。
        """
        out = ArbitrationOutcome(kept=list(candidate_names))
        if not candidate_names:
            return out

        # ---- ① 禁止组合：成对存在时保留排名更高者 ----
        for combo in self.forbidden:
            if combo.is_count_constraint() or len(combo.skills) < 2:
                continue
            a, b = combo.skills[0], combo.skills[1]
            if a in out.kept and b in out.kept:
                i, j = out.kept.index(a), out.kept.index(b)
                loser = b if i < j else a
                out.kept.remove(loser)
                out.dropped.append(
                    (loser, f"禁止与 {a if loser == b else b} 同时加载：{combo.reason}")
                )
                out.applied.append(f"禁止组合 {a} + {b}")

        # ---- ② "总路由"型技能计数上限 ----
        count_rules = [c for c in self.forbidden if c.is_count_constraint()]
        limit = count_rules[0].max_count if count_rules else 0
        if limit <= 0 and self.max_umbrella_skills:
            limit = self.max_umbrella_skills
        if limit > 0:
            umbrellas = [n for n in out.kept if n in self.umbrella_skills]
            if len(umbrellas) > limit:
                for n in umbrellas[limit:]:
                    out.kept.remove(n)
                    out.dropped.append(
                        (n, f"「总路由」型技能同时加载上限为 {limit} 个"
                            f"（§5：会产生「先读哪个」的摇摆）")
                    )
                out.applied.append(f"总路由型上限 {limit}")

        return out

    # ---------------------------------------------------------------- 视图

    def is_umbrella(self, name: str) -> bool:
        return name in self.umbrella_skills

    def stats(self) -> dict:
        return {
            "raw_path": self.raw_path,
            "entry": self.entry,
            "umbrella_skills": self.umbrella_skills,
            "max_execution_skills": self.max_execution_skills,
            "max_umbrella_skills": self.max_umbrella_skills,
            "task_routes": len(self.task_routes),
            "topic_arbiters": len(self.topics),
            "forbidden_combos": len(self.forbidden),
            "has_motto": bool(self.motto),
            "parse_warnings": self.parse_warnings,
        }

    def to_dict(self) -> dict:
        return {
            **self.stats(),
            "task_routes": [t.to_dict() for t in self.task_routes],
            "topics": [t.to_dict() for t in self.topics],
            "forbidden": [f.to_dict() for f in self.forbidden],
            "motto": self.motto,
        }
