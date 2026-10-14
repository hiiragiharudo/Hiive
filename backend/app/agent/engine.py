"""Agent 执行引擎：技能驱动的渗透循环。

## 循环结构

```
观测攻击图状态
  → 技能路由（两阶段，带阶段先验）
  → 依赖编排（补齐 requires 中尚未执行且有计划的前置技能）
  → 执行技能动作（经作用域校验的工具层）
  → 验证判据求值（确定性，不调用 LLM）
  → 更新攻击图（资产 / 经验证的发现 / 未通过的候选）
  → 留痕（供回溯与贡献度统计）
  → 终止判定
```

## 终止判据（三者任一）

1. 达到 `max_steps`；
2. 无新的可执行技能（路由结果中所有候选都已执行过）；
3. **连续 `no_progress_patience` 步无状态变化**（无新资产、无新发现）——
   这是针对"空转"的显式防护。调研中"用测绘行为冒充挖掘进度"是该领域的典型失效模式。

## 无执行计划的技能如何处理

语料中的第三方技能**不声明执行计划**（它们是方法论文本，本就不该被自动执行）。
引擎对这类技能记为 `skipped_no_plan` 并**如实留痕**，而不是假装执行过。
这既保证结果诚实，也说明本课题的"执行"目前只覆盖带计划的可验证技能——
**这一局限须写入论文**。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..skills.router import SkillRouter
from .scope import Scope
from .state import AttackGraph, Candidate, Finding
from .target import SimulatedTarget
from .tools import HttpTool
from .trace import StepRecord, Trace
from .verify import evaluate_predicates


@dataclass
class SkillPlan:
    """技能的执行计划：动作序列 + 验证判据 + 发现元信息。

    **为什么放在独立 JSON 而不是 `SKILL.md` 的 frontmatter**：
    本项目的 frontmatter 解析器只支持简单 YAML 子集（标量 / 标量列表 /
    块标量），不支持"列表里嵌字典"的嵌套结构。把嵌套结构塞进去会让解析器
    复杂度陡增。**这是一个已知取舍**：若日后接入完整 YAML 库，可迁回 frontmatter，
    届时技能包才是完全自包含的。
    """

    skill: str
    actions: list[dict] = field(default_factory=list)
    verify: list[dict] = field(default_factory=list)
    finding_kind: str = ""
    severity: str = "medium"
    asset: str = ""
    discover_assets: list[dict] = field(default_factory=list)

    @property
    def executable(self) -> bool:
        return bool(self.actions) or bool(self.verify)


def load_plans(path: Path) -> dict[str, SkillPlan]:
    """从 JSON 加载执行计划。"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, SkillPlan] = {}
    for name, spec in raw.items():
        if name.startswith("_"):  # 允许以 _ 开头的注释键
            continue
        out[name] = SkillPlan(
            skill=name,
            actions=list(spec.get("actions", [])),
            verify=list(spec.get("verify", [])),
            finding_kind=spec.get("finding_kind", ""),
            severity=spec.get("severity", "medium"),
            asset=spec.get("asset", ""),
            discover_assets=list(spec.get("discover_assets", [])),
        )
    return out


@dataclass
class RunResult:
    """一次任务的执行结果。"""

    task_id: str
    query: str
    graph: AttackGraph
    trace: Trace
    tool: HttpTool
    routings: list[dict] = field(default_factory=list)
    scope: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "query": self.query,
            "graph": self.graph.to_dict(),
            "trace": self.trace.to_dict(),
            "routings": self.routings,
            "scope": self.scope,
            "tools": self.tool.to_dict(),
            "summary": {
                "steps": len(self.trace.steps),
                "verified_findings": len(self.graph.verified_findings),
                "candidates_rejected": len(self.graph.candidates),
                "assets": len(self.graph.assets),
                "blocked_calls": self.tool.blocked_count,
                "terminated_reason": self.trace.terminated_reason,
            },
        }


class AgentEngine:
    """技能驱动的渗透 Agent 引擎。"""

    def __init__(
        self,
        router: SkillRouter,
        plans: dict[str, SkillPlan] | None = None,
        target: SimulatedTarget | None = None,
        scope: Scope | None = None,
        *,
        max_steps: int = 8,
        top_k: int = 3,
        no_progress_patience: int = 2,
        max_blocked_calls: int = 3,
        state_phase: str = "",
    ) -> None:
        self.router = router
        self.plans = plans or {}
        self.scope = scope or Scope(hosts=[SimulatedTarget.HOST])
        self.target = target or SimulatedTarget(self.scope)
        self.max_steps = max_steps
        self.top_k = top_k
        self.no_progress_patience = no_progress_patience
        #: **越界熔断**：累计被作用域拦截达到此数即终止任务。
        #:
        #: 动机（实测发现）：靶场主机不在授权范围时，引擎会把所有候选技能逐个执行完
        #: 才停——即使每一次请求都被拦截。**一个持续冲击被拦目标的 Agent 本身就是风险**
        #: （云鼎实验室公开的真实越界实验中，Agent 在受阻后仍继续尝试其他出网手法）。
        #: 因此把"累计拦截次数"作为独立终止条件，而非依赖步数上限兜底。
        self.max_blocked_calls = max_blocked_calls
        self.state_phase = state_phase

    # ---------------------------------------------------------------- 主循环

    def run(self, query: str, task_id: str = "task-1") -> RunResult:
        graph = AttackGraph(target=self.target.HOST)
        trace = Trace(task_id=task_id, query=query)
        tool = HttpTool(self.target, self.scope)
        routings: list[dict] = []
        executed: set[str] = set()
        no_progress = 0

        while len(trace.steps) < self.max_steps:
            res = self.router.route(query, state_phase=self.state_phase or graph.phase,
                                    top_k=self.top_k)
            routings.append(res.to_dict())
            if res.abstained or not res.candidates:
                trace.terminated_reason = "路由弃权：无相关技能"
                break

            # ---- 选取下一个待执行技能（含依赖补齐） ----
            order = self._execution_order(res.candidates, executed)
            pending = [n for n in order if n not in executed]
            if not pending:
                trace.terminated_reason = "无新的可执行技能（候选均已执行）"
                break

            name = pending[0]
            cand = next((c for c in res.candidates if c.skill.name == name), None)
            skill = self.router.registry.get(name)
            if skill is None:
                executed.add(name)
                continue

            rec = StepRecord(
                step=len(trace.steps) + 1,
                skill=name,
                phase=skill.meta.phase,
                route_score=cand.score if cand else 0.0,
                route_reason=cand.reason if cand else "",
                cost_tokens=skill.injected_tokens(),
            )
            executed.add(name)

            plan = self.plans.get(name)
            if plan is None or not plan.executable:
                rec.outcome = "skipped_no_plan"
                rec.skipped_reason = (
                    "该技能未声明执行计划（第三方方法论技能），引擎只做路由不做执行"
                )
                trace.add(rec)
                no_progress += 1
                if no_progress >= self.no_progress_patience:
                    trace.terminated_reason = (
                        f"连续 {no_progress} 步无状态变化（候选技能均无可执行计划）"
                    )
                    break
                continue

            # ---- 执行 ----
            before_assets = len(graph.assets)
            before_findings = len(graph.verified_findings)

            for a in plan.actions:
                tool.request(
                    a.get("method", "GET"),
                    a.get("host", self.target.HOST),
                    a.get("path", "/"),
                    query=a.get("query"), headers=a.get("headers"), body=a.get("body"),
                )
            rec.actions = [a for a in plan.actions]
            rec.tool_calls = len(plan.actions)

            # ---- 验证判据（确定性） ----
            if plan.verify:
                passed, results = evaluate_predicates(plan.verify, self.target)
                rec.verify_results = results
                rec.verified = passed
                if passed:
                    graph.add_finding(
                        Finding(
                            skill=name,
                            kind=plan.finding_kind or "unknown",
                            asset=plan.asset or self.target.HOST,
                            severity=plan.severity,
                            verified=True,
                            evidence=[e for r in results for e in r.evidence],
                            detail="；".join(r.detail for r in results),
                        )
                    )
                else:
                    reasons = [r.detail for r in results if not r.passed]
                    rec.rejected_reason = "；".join(reasons)[:300] or "判据未全部通过"
                    graph.add_candidate(
                        Candidate(
                            skill=name,
                            kind=plan.finding_kind or "unknown",
                            asset=plan.asset or self.target.HOST,
                            reason="技能判定为存在，但验证判据未通过",
                            rejected_reason=rec.rejected_reason,
                        )
                    )
            else:
                rec.rejected_reason = "该技能未声明验证判据，无法升级为发现"
                graph.add_candidate(
                    Candidate(
                        skill=name,
                        kind=plan.finding_kind or "unknown",
                        asset=plan.asset or self.target.HOST,
                        reason="技能执行完成但无验证判据",
                        rejected_reason=rec.rejected_reason,
                    )
                )

            # ---- 更新攻击图 ----
            for da in plan.discover_assets:
                graph.add_asset(da.get("kind", "endpoint"),
                                da.get("value", ""), by=name)
            graph.add_asset("endpoint", plan.asset or self.target.HOST, by=name)
            graph.mark_tested("endpoint", plan.asset or self.target.HOST)
            graph.advance_phase(skill.meta.phase)
            graph.executed_skills.append(name)
            graph.step = rec.step

            rec.tool_calls = len(plan.actions)
            rec.blocked_calls = tool.blocked_count
            rec.new_assets = len(graph.assets) - before_assets
            trace.add(rec)

            # ---- 无进展检测 ----
            if (len(graph.assets) == before_assets
                    and len(graph.verified_findings) == before_findings):
                no_progress += 1
            else:
                no_progress = 0

            # ---- 越界熔断（优先于无进展检测） ----
            if tool.blocked_count >= self.max_blocked_calls:
                trace.terminated_reason = (
                    f"越界拦截达到上限 {self.max_blocked_calls} 次，任务中止"
                    "（架构级防护：不持续冲击被拦目标）"
                )
                break

            if no_progress >= self.no_progress_patience:
                trace.terminated_reason = f"连续 {no_progress} 步无状态变化（无新资产/新发现）"
                break
        else:
            trace.terminated_reason = f"达到步数上限 {self.max_steps}"

        if not trace.terminated_reason:
            trace.terminated_reason = "正常结束"

        return RunResult(
            task_id=task_id,
            query=query,
            graph=graph,
            trace=trace,
            tool=tool,
            routings=routings,
            scope=self.scope.to_dict(),
        )

    # ---------------------------------------------------------------- 编排

    def _execution_order(self, candidates, executed: set[str]) -> list[str]:
        """按依赖闭包展开执行顺序（编排）。

        路由只保证"选对了技能"，不保证"前置条件已满足"。
        因此这里按 `requires` 补齐尚未执行的前置技能，并把它们排到前面。
        仅限于**本模块有计划**的技能才值得补齐——方法论类前置技能无法自动执行。
        """
        names = [c.skill.name for c in candidates]
        ordered: list[str] = []
        seen: set[str] = set()

        def visit(n: str) -> None:
            if n in seen:
                return
            seen.add(n)
            skill = self.router.registry.get(n)
            if skill is not None:
                for dep in skill.meta.requires:
                    if dep not in executed:
                        visit(dep)
            ordered.append(n)

        for n in names:
            visit(n)
        # 依赖优先，且只保留"待执行"的
        return [n for n in ordered if n not in executed or n in names]
