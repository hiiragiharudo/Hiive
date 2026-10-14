"""执行留痕与**回溯**。

## 「回溯」在本课题中的含义

这是技能引擎四项能力（加载/选择/编排/回溯）的最后一项，指：

1. **过程留痕**：每一步路由到哪个技能、发起了哪些动作、判据是否通过、
   为什么被拒——全部结构化记录，可事后审计；
2. **贡献度回填**：把执行结果（成功/失败）按技能聚合，
   得到「某个技能实际产出了多少经验证的发现」——**这是评测闭环的数据来源**，
   也是论文「技能贡献度」指标的系统层落地。

## 为什么必须落盘而非留在上下文

长任务中上下文会爆炸（`PentAGI` README 直言典型 agent 工作流消耗约 64K token）。
把过程性信息**外置到结构化存储**（本模块 + `task_skills` 表）是主流做法。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .verify import VerifyResult


@dataclass
class StepRecord:
    """单步（= 单个技能的一次执行）的完整留痕。"""

    step: int
    skill: str
    phase: str = ""
    #: 路由得分与召回依据（来自 RouteCandidate）
    route_score: float = 0.0
    route_reason: str = ""
    #: 执行状态：executed / skipped_no_plan / skipped_dependency / blocked
    outcome: str = "executed"
    skipped_reason: str = ""
    actions: list[dict] = field(default_factory=list)
    tool_calls: int = 0
    blocked_calls: int = 0
    verify_results: list[VerifyResult] = field(default_factory=list)
    verified: bool = False
    finding_kind: str = ""
    rejected_reason: str = ""
    new_assets: int = 0
    cost_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "skill": self.skill,
            "phase": self.phase,
            "route_score": round(self.route_score, 6),
            "route_reason": self.route_reason,
            "outcome": self.outcome,
            "skipped_reason": self.skipped_reason,
            "actions": self.actions,
            "tool_calls": self.tool_calls,
            "blocked_calls": self.blocked_calls,
            "verify": [v.to_dict() for v in self.verify_results],
            "verified": self.verified,
            "finding_kind": self.finding_kind,
            "rejected_reason": self.rejected_reason,
            "new_assets": self.new_assets,
            "cost_tokens": self.cost_tokens,
        }


@dataclass
class Trace:
    """一次任务的全部留痕。"""

    task_id: str = ""
    query: str = ""
    steps: list[StepRecord] = field(default_factory=list)
    terminated_reason: str = ""

    def add(self, rec: StepRecord) -> StepRecord:
        self.steps.append(rec)
        return rec

    # ---------------------------------------------------------------- 回溯

    def contribution(self) -> dict[str, dict]:
        """**技能贡献度回溯**：按技能聚合执行结果。

        这是论文「技能贡献度」指标的数据来源，用于回答
        "某技能是否值得保留在技能库中"。
        """
        agg: dict[str, dict] = {}
        for s in self.steps:
            a = agg.setdefault(
                s.skill,
                {
                    "executed": 0, "skipped": 0, "verified": 0,
                    "rejected": 0, "tool_calls": 0, "blocked_calls": 0,
                    "cost_tokens": 0, "reject_reasons": [],
                },
            )
            if s.outcome == "executed":
                a["executed"] += 1
            else:
                a["skipped"] += 1
            if s.verified:
                a["verified"] += 1
            elif s.outcome == "executed":
                a["rejected"] += 1
                if s.rejected_reason:
                    a["reject_reasons"].append(s.rejected_reason[:120])
            a["tool_calls"] += s.tool_calls
            a["blocked_calls"] += s.blocked_calls
            a["cost_tokens"] += s.cost_tokens

        for name, a in agg.items():
            a["hit_rate"] = round(a["verified"] / a["executed"], 4) if a["executed"] else 0.0
        return agg

    # ---------------------------------------------------------------- 视图

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "query": self.query,
            "terminated_reason": self.terminated_reason,
            "step_count": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "contribution": self.contribution(),
        }

    def summary(self) -> str:
        executed = sum(1 for s in self.steps if s.outcome == "executed")
        verified = sum(1 for s in self.steps if s.verified)
        blocked = sum(s.blocked_calls for s in self.steps)
        return (
            f"步数 {len(self.steps)}（执行 {executed}）"
            f" 经验证发现 {verified} 越界拦截 {blocked}"
            f" 终止原因：{self.terminated_reason or '—'}"
        )
