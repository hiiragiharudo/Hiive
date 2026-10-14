"""SkillRoute-Bench：技能路由质量基准的评测基础设施。

## 为什么需要它（实测理由，非"为了好看"）

开发期探针集（`probes.py`，14 条）在最优配置下已达 **14/14 全命中**，
**失去区分能力**——任何改进都无法在它上面体现，继续使用会产生"改进无效"的假象，
或诱导针对这 14 条查询的过拟合（见技术设计文档 §6.7）。

## 相对既有基准的差异

既有基准（AutoPenBench / Cybench / TSBbench 等）的评测单位是**任务**或 **Agent**
（"目标打进去了吗"）。本基准的评测单位是**技能调度**
（"该给 Agent 看哪些技能"）——二者正交，本基准填补的是这一粒度。

## 指标设计

| 指标 | 含义 |
|---|---|
| Recall@k | 命中率：期望技能是否出现在 top-k |
| MRR | 平均倒数名次（阶段一完整排序），对排序质量敏感 |
| **弃权准确率** | **对"库中无正确答案"的查询，是否正确地不返回候选** |
| 误路由率 | 1 − 弃权准确率 |
| 上下文成本 | 注入 token 与基线元数据 token 的对比 |

**弃权指标是本基准的特色**：真实使用中，用户会问大量与技能库无关的问题
（运维配置、性能优化、日常事务），一个总是"硬凑"一个技能的检索器是危险的
——它会误导 Agent 去执行不相关的攻击性技能。既有基准不测这一点。

## 标注来源与可信度

每条标注带 `source` 与 `confidence`，指标可**按来源分层报告**：

- ``hand``：人工编写，ground truth 由人工判定（**最可信**）
- ``body-derived``：从技能正文派生（**存在循环性风险**，须分层报告，见下）

**循环性风险声明**：若查询由某技能的 `description` 生成，则词面检索器必然命中它，
指标会被虚高。因此 ``body-derived`` 的生成**必须排除 `name` 与 `description` 的 token**，
且其指标**不得与 ``hand`` 混合统计**。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- 数据结构

VALID_SOURCES = ("hand", "body-derived", "report-derived")
VALID_CONFIDENCE = ("high", "medium", "low")
VALID_LANG = ("zh", "en")


@dataclass
class BenchItem:
    """一条基准查询。"""

    id: str
    query: str
    #: 期望被召回的技能名。**空列表表示"库中无正确答案"**，用于测弃权能力。
    expected: list[str] = field(default_factory=list)
    #: 可接受的替代答案。不计入主指标，但记录以便分析。
    acceptable: list[str] = field(default_factory=list)
    lang: str = "zh"
    #: 覆盖的安全域标签（便于分层报告）
    domains: list[str] = field(default_factory=list)
    source: str = "hand"
    confidence: str = "high"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.lang not in VALID_LANG:
            raise ValueError(f"非法 lang: {self.lang!r}")
        if self.source not in VALID_SOURCES:
            raise ValueError(f"非法 source: {self.source!r}")
        if self.confidence not in VALID_CONFIDENCE:
            raise ValueError(f"非法 confidence: {self.confidence!r}")

    @property
    def is_abstention(self) -> bool:
        """是否为"库中无正确答案"的弃权用例。"""
        return not self.expected

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BenchItem":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# --------------------------------------------------------------------------- 读写


def load_bench(path: Path) -> list[BenchItem]:
    """从 JSONL 加载基准。每行一条，容忍空行与注释行（``#`` 开头）。"""
    items: list[BenchItem] = []
    seen: set[str] = set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{lineno} JSON 解析失败: {e}") from e
        item = BenchItem.from_dict(d)
        if item.id in seen:
            raise ValueError(f"{path}:{lineno} 重复的 id: {item.id}")
        seen.add(item.id)
        items.append(item)
    return items


def save_bench(items: list[BenchItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(it.to_dict(), ensure_ascii=False) for it in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- 结果


@dataclass
class BenchItemResult:
    """单条基准的执行结果。"""

    item: BenchItem
    candidates: list[str]
    hit_rank: int = 0          # 期望技能在 top-k 中的最好名次；0 表示未命中
    stage1_rank: int = 0       # 阶段一完整排序中的名次；0 表示未召回
    abstained: bool = False    # 是否返回了空候选
    injected_tokens: int = 0
    baseline_tokens: int = 0

    @property
    def hit(self) -> bool:
        return self.hit_rank > 0

    @property
    def correct_abstention(self) -> bool:
        """弃权用例被正确弃权。"""
        return self.item.is_abstention and self.abstained

    @property
    def false_route(self) -> bool:
        """弃权用例却被路由到了某个技能（误路由）。"""
        return self.item.is_abstention and not self.abstained


@dataclass
class BenchMetrics:
    """分层指标汇总。"""

    name: str = ""
    total: int = 0
    scored: int = 0            # 参与 Recall 统计的条目（有正确答案的）
    abstention_total: int = 0
    abstention_correct: int = 0

    recall_at_1: int = 0
    recall_at_3: int = 0
    recall_at_5: int = 0
    mrr_sum: float = 0.0
    stage1_recall: int = 0     # 期望技能进入阶段一候选池的条目数
    rank_sum: int = 0

    injected_tokens: int = 0
    baseline_tokens: int = 0
    results: list[BenchItemResult] = field(default_factory=list)

    # ---- 派生指标 ----
    @property
    def recall1(self) -> float:
        return self.recall_at_1 / self.scored if self.scored else 0.0

    @property
    def recall3(self) -> float:
        return self.recall_at_3 / self.scored if self.scored else 0.0

    @property
    def recall5(self) -> float:
        return self.recall_at_5 / self.scored if self.scored else 0.0

    @property
    def mrr(self) -> float:
        """MRR 用**阶段一完整排序**的名次计算，因此不受 k 截断影响。"""
        return self.mrr_sum / self.scored if self.scored else 0.0

    @property
    def stage1_recall_rate(self) -> float:
        return self.stage1_recall / self.scored if self.scored else 0.0

    @property
    def abstention_accuracy(self) -> float:
        return (
            self.abstention_correct / self.abstention_total
            if self.abstention_total else 0.0
        )

    @property
    def false_route_rate(self) -> float:
        """弃权用例被误路由的比例。"""
        if not self.abstention_total:
            return 0.0
        return 1.0 - self.abstention_accuracy

    @property
    def meta_saving(self) -> float:
        if self.baseline_tokens <= 0:
            return 0.0
        return 1.0 - self.injected_tokens / self.baseline_tokens

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total": self.total,
            "scored": self.scored,
            "recall@1": round(self.recall1, 4),
            "recall@3": round(self.recall3, 4),
            "recall@5": round(self.recall5, 4),
            "mrr_stage1": round(self.mrr, 4),
            "stage1_recall_rate": round(self.stage1_recall_rate, 4),
            "abstention_total": self.abstention_total,
            "abstention_correct": self.abstention_correct,
            "abstention_accuracy": round(self.abstention_accuracy, 4),
            "false_route_rate": round(1.0 - self.abstention_accuracy, 4)
            if self.abstention_total else 0.0,
            "meta_saving": round(self.meta_saving, 4),
        }

    def summary(self) -> str:
        d = self.to_dict()
        return (f"R@1 {d['recall@1']:.3f} R@3 {d['recall@3']:.3f} "
                f"R@5 {d['recall@5']:.3f} MRR {d['mrr_stage1']:.3f} "
                f"| 弃权 {self.abstention_correct}/{self.abstention_total} "
                f"| 元数据节省 {d['meta_saving']:.1%}")


# --------------------------------------------------------------------------- 评测


def _match_rank(candidates: list[str], expected: list[str]) -> int:
    """返回期望技能在候选列表中的最好名次（1 起）；0 表示未出现。"""
    for i, cand in enumerate(candidates, start=1):
        if any(e in cand for e in expected):
            return i
    return 0


def run_bench(
    router,
    items: list[BenchItem],
    name: str = "bench",
    top_k: int | None = None,
) -> BenchMetrics:
    """在基准上运行路由器并汇总指标。"""
    m = BenchMetrics(name=name, total=len(items))

    for item in items:
        res = router.route(item.query, top_k=top_k)
        cands = [c.skill.name for c in res.candidates]
        abstained = not cands

        r = BenchItemResult(
            item=item,
            candidates=cands,
            abstained=abstained,
            injected_tokens=res.injected_tokens,
            baseline_tokens=res.baseline_tokens,
        )

        if item.is_abstention:
            m.abstention_total += 1
            m.abstention_correct += int(abstained)
        else:
            m.scored += 1
            hr = _match_rank(cands, item.expected)
            r.hit_rank = hr
            if hr == 1:
                m.recall_at_1 += 1
            if 0 < hr <= 3:
                m.recall_at_3 += 1
            if 0 < hr <= 5:
                m.recall_at_5 += 1

            stage1 = getattr(res, "stage1_ranking", []) or []
            # 阶段一名次要排除掉 top-k 已统计的部分也无妨——直接找最好名次
            r.stage1_rank = _match_rank(stage1, item.expected)
            if r.stage1_rank:
                m.stage1_recall += 1
                m.mrr_sum += 1.0 / r.stage1_rank
                m.rank_sum += r.stage1_rank

        m.injected_tokens += res.injected_tokens
        m.baseline_tokens += res.baseline_tokens
        m.results.append(r)

    return m


def breakdown_by(results: list[BenchItemResult], key: str) -> dict[str, BenchMetrics]:
    """按某字段分层汇总（``source`` / ``lang`` / ``confidence``）。

    分层报告是**控制循环性风险**的手段：``body-derived`` 的指标必须与 ``hand`` 分开看。
    """
    groups: dict[str, list[BenchItem]] = {}
    for r in results:
        k = str(getattr(r.item, key, "?"))
        groups.setdefault(k, []).append(r.item)

    out: dict[str, BenchMetrics] = {}
    for k, items in groups.items():
        sub = BenchMetrics(name=k, total=len(items))
        # 直接复用已有结果重算，避免重新路由
        for r in results:
            if str(getattr(r.item, key, "?")) != k:
                continue
            if r.item.is_abstention:
                sub.abstention_total += 1
                sub.abstention_correct += int(r.abstained)
            else:
                sub.scored += 1
                hr = _match_rank(r.candidates, r.item.expected)
                if hr == 1:
                    sub.recall_at_1 += 1
                if 0 < hr <= 3:
                    sub.recall_at_3 += 1
                if 0 < hr <= 5:
                    sub.recall_at_5 += 1
                if r.stage1_rank:
                    sub.stage1_recall += 1
                    sub.mrr_sum += 1.0 / r.stage1_rank
            sub.injected_tokens += r.injected_tokens
            sub.baseline_tokens += r.baseline_tokens
            sub.results.append(r)
        out[k] = sub
    return out
