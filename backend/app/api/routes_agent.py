"""Agent 执行引擎的 API。

**安全声明**：这些端点只在**进程内模拟靶场**（`app/agent/target.py`）上运行，
不产生任何真实网络 IO。作用域校验在工具层与靶场层各做一次（纵深防御）。

任务状态**不持久化**（无数据库），仅返回本次请求的执行结果。
持久化（`tasks` / `task_skills` 表）属后续工作——见技术设计文档 §9。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..agent.engine import AgentEngine
from ..agent.scope import Scope
from ..agent.target import SimulatedTarget
from ..core.service import SkillService
from .routes import get_service

agent_router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    """`POST /api/agent/run` 请求体。"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000, description="任务描述")
    max_steps: int = Field(8, ge=1, le=50)
    top_k: int = Field(3, ge=1, le=10)
    #: 授权主机；默认模拟靶场主机。用于演示作用域拦截（填错即全被拦）
    hosts: list[str] | None = Field(None, description="授权主机列表")
    max_blocked_calls: int = Field(3, ge=1, le=100, description="越界熔断阈值")


@agent_router.get("/lab", summary="实验靶场信息")
def lab_info(svc: SkillService = Depends(get_service)) -> dict:
    try:
        router = svc.lab_router()
        plans = svc.lab_plans()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    skills_dir, plans_path = svc.lab_paths()
    target = SimulatedTarget()
    return {
        "skills_dir": str(skills_dir),
        "plans_path": str(plans_path),
        "skills": sorted(router.registry.skills),
        "skill_count": len(router.registry),
        "plans": sorted(plans),
        "target_host": target.HOST,
        "routes": [
            {"name": r.name, "method": r.method, "path": r.path, "status": r.status}
            for r in target.routes
        ],
        "planted": {
            "GET /api/orders/{id}": "水平越权（不校验属主，不同 id 返回不同属主）",
            "GET /admin/users": "访问控制缺陷（403，但伪造头可绕过）",
            "GET /search?q=": "反射型 XSS（查询串原样写入 body）",
            "POST /upload": "不安全上传（.php/.phtml 被接受）",
            "GET /static?file=": "目录遍历（../ 未规范化）",
        },
        "note": (
            "靶场为进程内确定性模拟，不监听端口、无网络 IO、不含可用 exploit。"
            "验证由确定性判据完成，不调用 LLM。"
        ),
    }


@agent_router.post("/run", summary="★ 运行技能驱动的渗透 Agent")
def agent_run(
    body: AgentRunRequest, svc: SkillService = Depends(get_service)
) -> dict:
    """执行完整循环：路由 → 依赖编排 → 执行 → 验证 → 更新攻击图 → 留痕。

    返回内容含：
    - `graph`：攻击图（资产 / **经验证的发现** / 被拒绝的候选）；
    - `trace`：逐步留痕与**技能贡献度回溯统计**；
    - `routings`：每次路由的完整结果（含召回依据与成本）；
    - `tools`：全部工具调用留痕（含越界拦截）；
    - `summary`：步数、发现数、拒绝数、拦截数、终止原因。
    """
    try:
        router = svc.lab_router()
        plans = svc.lab_plans()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    scope = Scope(hosts=body.hosts or [SimulatedTarget.HOST])
    engine = AgentEngine(
        router, plans, scope=scope,
        max_steps=body.max_steps, top_k=body.top_k,
        max_blocked_calls=body.max_blocked_calls,
    )
    try:
        result = engine.run(body.query, task_id="api-run")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return result.to_dict()


@agent_router.get("/contribution", summary="技能贡献度（回溯统计）")
def agent_contribution(
    q: str = Query(..., min_length=1, description="任务描述"),
    svc: SkillService = Depends(get_service),
    top_k: int = Query(5, ge=1, le=10),
    max_steps: int = Query(10, ge=1, le=50),
) -> dict:
    """只返回贡献度表——回答"某技能实际产出了多少经验证的发现"。"""
    try:
        router = svc.lab_router()
        plans = svc.lab_plans()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    engine = AgentEngine(router, plans, max_steps=max_steps, top_k=top_k)
    result = engine.run(q, task_id="contribution")
    return {
        "query": q,
        "contribution": result.trace.contribution(),
        "verified_findings": [f.to_dict() for f in result.graph.verified_findings],
        "rejected_candidates": [c.to_dict() for c in result.graph.candidates],
        "terminated_reason": result.trace.terminated_reason,
        "summary": result.to_dict()["summary"],
    }
