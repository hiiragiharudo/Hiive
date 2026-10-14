"""Agent 执行引擎。

## 目标能力对应

开题报告要求技能引擎具备四项能力，前两项已由 `app.skills` 实现：

| 能力 | 实现位置 |
|---|---|
| **加载** | `skills.registry` —— 解析、校验、建索引 |
| **选择** | `skills.router` —— 两阶段检索路由 |
| **编排** | `skills.router.dependency_closure` + 本模块的**执行期依赖补齐** |
| **回溯** | 本模块的 `trace` —— 执行留痕 + 技能贡献度回填 |

## 安全约束（硬性）

1. **默认离线**：`target` 层默认使用 `SimulatedTarget`（进程内确定性模拟靶场），
   不发任何真实网络请求；
2. **作用域强制**：所有出站动作经 `Scope` 校验，越界**直接拒绝并记录**，
   不依赖提示词自觉；
3. **验证门控**：只有通过验证判据的候选才能升级为「发现」，无证据不产生发现。

这三点使得整套流程可在无网络、无 LLM、无 API 费用的条件下复现——
这是本课题"评测可离线"优势在系统层的落地。
"""

from .engine import AgentEngine, RunResult
from .scope import Scope, ScopeViolation
from .state import Asset, AttackGraph, Finding
from .target import HttpRequest, HttpResponse, Route, SimulatedTarget
from .tools import HttpTool
from .trace import StepRecord, Trace
from .verify import VerifyResult, evaluate_predicates

__all__ = [
    "AgentEngine",
    "Asset",
    "AttackGraph",
    "Finding",
    "HttpRequest",
    "HttpResponse",
    "HttpTool",
    "Route",
    "RunResult",
    "Scope",
    "ScopeViolation",
    "SimulatedTarget",
    "StepRecord",
    "Trace",
    "VerifyResult",
    "evaluate_predicates",
]
