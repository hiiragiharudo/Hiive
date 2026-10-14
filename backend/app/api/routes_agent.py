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
    #: 目标选择：留空 = 离线模拟靶场（默认）；填真实靶场名 = 打 XAMPP 上的真实靶场
    target: str = Field("", description="靶场名（sqli-labs / dvwa / pikachu）；留空用离线模拟靶场")
    max_steps: int = Field(8, ge=1, le=50)
    top_k: int = Field(3, ge=1, le=10)
    #: 授权主机；默认模拟靶场主机。仅对离线模拟靶场生效
    hosts: list[str] | None = Field(None, description="授权主机列表")
    max_blocked_calls: int = Field(3, ge=1, le=100, description="越界熔断阈值")


@agent_router.get("/ranges", summary="★ 可用真实靶场列表")
def ranges_list(svc: SkillService = Depends(get_service)) -> dict:
    """列出全部真实靶场及其就绪状态。

    真实靶场跑在本机 XAMPP 上（sqli-labs / DVWA / Pikachu），
    搭建与踩坑记录见 `docs/靶场环境搭建.md`。
    **全部请求指向 localhost，不涉及任何线上目标。**
    """
    items = svc.list_ranges()
    return {
        "ranges": items,
        "count": len(items),
        "note": (
            "真实的漏洞演练靶场，部署在本机 localhost。平台的技能包与验证判据"
            "针对每个靶场单独编写（判据标记来自实测，见 eval/ranges/probe_ranges.py）。"
        ),
    }


@agent_router.get("/ranges/{name}", summary="靶场详情（技能、计划、登录状态）")
def range_detail(
    name: str,
    refresh: bool = Query(False, description="是否重建运行时（重置登录会话）"),
    svc: SkillService = Depends(get_service),
) -> dict:
    try:
        rt = svc.range_runtime(name, refresh=refresh)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return rt.to_dict()


@agent_router.get("/lab", summary="离线模拟靶场信息")
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

    **两种目标**，由 `target` 参数选择：

    | `target` | 目标 | 说明 |
    |---|---|---|
    | 留空 | 离线模拟靶场 | 进程内、无网络 IO、确定性。用于单元测试与无靶场时演示 |
    | `sqli-labs` / `dvwa` / `pikachu` | **真实靶场** | XAMPP 上运行的漏洞演练环境，**请求全部指向 localhost** |

    返回内容含：
    - `graph`：攻击图（资产 / **经验证的发现** / 被拒绝的候选）；
    - `trace`：逐步留痕与**技能贡献度回溯统计**；
    - `routings`：每次路由的完整结果（含召回依据与成本）；
    - `tools`：全部工具调用留痕（含越界拦截）；
    - `summary`：步数、发现数、拒绝数、拦截数、终止原因；
    - `target_info`：本次使用的目标说明（真实靶场含登录状态与警告）。
    """
    target_info: dict = {}
    if body.target:
        try:
            rt = svc.range_runtime(body.target)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        engine = AgentEngine(
            rt.router, rt.plans, target=rt.target, scope=rt.target.scope,
            max_steps=body.max_steps, top_k=body.top_k,
            max_blocked_calls=body.max_blocked_calls,
        )
        target_info = {
            "kind": "range",
            "name": rt.profile.name,
            "label": rt.profile.label,
            "base_url": rt.target.base_url,
            "login_ok": rt.login_ok,
            "login_detail": rt.login_detail,
            "warnings": rt.warnings,
            "note": rt.profile.note,
        }
    else:
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
        target_info = {
            "kind": "simulated",
            "name": "lab",
            "label": "离线模拟靶场",
            "base_url": f"in-process ({SimulatedTarget.HOST})",
            "note": "进程内确定性模拟，不监听端口、无网络 IO、不含可用 exploit。",
        }

    try:
        result = engine.run(body.query, task_id="api-run")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    out = result.to_dict()
    out["target_info"] = target_info
    return out


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
