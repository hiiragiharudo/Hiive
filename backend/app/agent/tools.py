"""工具层。

当前仅实现 `HttpTool`（面向模拟靶场）。**工具层是唯一允许产生"副作用"的地方**，
因此作用域校验在此再做一次（纵深防御：靶场内部也校验一次）。

真实渗透需要 nmap/nuclei/sqlmap 等工具，本课题按设计**复用 MCP 实现而不自研**
（见技术设计文档 §4.3）。本模块的接口形态即为将来接入 MCP 客户端的落点。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .scope import Scope, ScopeViolation
from .target import HttpRequest, HttpResponse, SimulatedTarget


@dataclass
class ToolCall:
    """一次工具调用的留痕。"""

    tool: str
    args: dict
    status: int = 0
    blocked: bool = False
    error: str = ""
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "args": self.args,
            "status": self.status,
            "blocked": self.blocked,
            "error": self.error,
            "evidence": self.evidence,
        }


@dataclass
class HttpTool:
    """HTTP 工具：经作用域校验后调用靶场。"""

    target: SimulatedTarget
    scope: Scope
    calls: list[ToolCall] = field(default_factory=list)

    def request(
        self,
        method: str,
        host: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        body: dict[str, str] | None = None,
        port: int | None = None,
        scheme: str = "http",
    ) -> HttpResponse:
        """发起请求。越界**不抛异常**，而是返回 `blocked=True` 的响应并留痕——
        这样调用方（技能执行器/验证器）可以继续处理，越界事实也不会丢失。"""
        req = HttpRequest(
            method=method.upper(), host=host, path=path,
            query=dict(query or {}), headers=dict(headers or {}),
            body=dict(body or {}), port=port, scheme=scheme,
        )
        call = ToolCall(tool="http", args=req.to_dict())

        try:
            self.scope.check(host, port, scheme)
        except ScopeViolation as e:
            call.blocked = True
            call.error = str(e)
            call.evidence = f"[作用域拦截] {e}"
            self.calls.append(call)
            return HttpResponse(status=0, body=str(e), blocked=True,
                                route="__scope_violation__")

        try:
            resp = self.target.handle(req)
        except Exception as e:  # 工具异常不得中断整个任务
            call.error = f"{type(e).__name__}: {e}"
            self.calls.append(call)
            return HttpResponse(status=0, body=call.error, route="__tool_error__")

        call.status = resp.status
        call.blocked = resp.blocked
        call.evidence = f"{req.method} {req.url} -> {resp.status}"
        self.calls.append(call)
        return resp

    @property
    def blocked_count(self) -> int:
        return sum(1 for c in self.calls if c.blocked)

    def to_dict(self) -> dict:
        return {
            "calls": len(self.calls),
            "blocked": self.blocked_count,
            "detail": [c.to_dict() for c in self.calls],
        }
