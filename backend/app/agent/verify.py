"""验证判据（受限可执行 DSL）。

## 设计动机

**「发现」与「验证」必须分离。** 调研中这是该领域公认的去误报做法
（XBOW 原话：*"Creative AI discovers. Deterministic logic decides what's real."*）。
因此本模块实现一个**确定性**的判据求值器：它不调用 LLM，
只按声明发出额外请求并断言结果。

## 为什么是"受限"DSL

判据必须是**可在沙箱中自动执行、且判定客观**的。因此只允许：

| kind | 语义 |
|---|---|
| `http_status` | 单个请求的状态码断言 |
| `http_diff` | 两个请求的响应差异断言（水平越权的客观判据） |
| `body_contains` | 响应体包含/不包含指定串（反射型 XSS 的客观判据） |
| `header_present` | 响应头存在性 |

**明确不支持的**：任意代码执行、正则回溯风险高的模式、跨请求状态机。
这些能力会引入不可控风险，且难以保证判据本身的正确性。

## 已知的判据可靠性风险（须写入论文）

`arXiv:2608.09567` 的独立复现研究发现：**30 个补丁反事实审计中有 20 个 oracle
在"已打补丁"的构建上仍然报警**——即基于内嵌 oracle 的"复现成功"含系统性假阳性。

因此本课题的立场是：**验证判据只能提高发现的可信度，不能保证零误报**。
这一点将明确写入论文的局限章节，不声称"零误报"。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .scope import ScopeViolation
from .target import HttpRequest, HttpResponse, SimulatedTarget

ALLOWED_KINDS = ("http_status", "http_diff", "body_contains", "header_present")


@dataclass
class VerifyResult:
    """单条判据的求值结果。"""

    kind: str
    passed: bool
    detail: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "passed": self.passed,
            "detail": self.detail,
            "evidence": self.evidence,
        }


def _req(spec: dict, default_host: str) -> HttpRequest:
    if "url" in spec:
        return HttpRequest.from_url(spec.get("method", "GET"), spec["url"],
                                    headers=spec.get("headers", {}),
                                    body=spec.get("body", {}))
    return HttpRequest(
        method=str(spec.get("method", "GET")).upper(),
        host=spec.get("host", default_host),
        path=spec.get("path", "/"),
        query=dict(spec.get("query", {})),
        headers=dict(spec.get("headers", {})),
        body=dict(spec.get("body", {})),
        port=spec.get("port"),
        scheme=spec.get("scheme", "http"),
    )


def _ev(req: HttpRequest, resp: HttpResponse) -> str:
    head = f"{req.method} {req.url} -> {resp.status}"
    if resp.blocked:
        head += " [作用域拦截]"
    return f"{head} | body[:120]={resp.body[:120]!r}"


def evaluate_predicate(
    pred: dict, target: SimulatedTarget, default_host: str = SimulatedTarget.HOST
) -> VerifyResult:
    """求值单条判据。**任何异常都转为"未通过"**，绝不向上抛。"""
    kind = str(pred.get("kind", ""))
    if kind not in ALLOWED_KINDS:
        return VerifyResult(
            kind=kind or "?",
            passed=False,
            detail=f"不支持的判据类型: {kind!r}（允许 {ALLOWED_KINDS}）",
        )

    try:
        if kind == "http_status":
            return _p_http_status(pred, target, default_host)
        if kind == "http_diff":
            return _p_http_diff(pred, target, default_host)
        if kind == "body_contains":
            return _p_body_contains(pred, target, default_host)
        return _p_header_present(pred, target, default_host)
    except ScopeViolation as e:
        return VerifyResult(kind=kind, passed=False, detail=f"作用域拒绝: {e}")
    except (KeyError, TypeError, ValueError) as e:
        return VerifyResult(kind=kind, passed=False, detail=f"判据格式错误: {e!r}")


def _p_http_status(pred: dict, t: SimulatedTarget, host: str) -> VerifyResult:
    req = _req(pred.get("request", {}), host)
    resp = t.handle(req)
    a = pred.get("assert", {})
    ev = [_ev(req, resp)]

    if resp.blocked:
        return VerifyResult("http_status", False, "请求被作用域拦截", ev)
    if "status" in a and resp.status != a["status"]:
        return VerifyResult("http_status", False,
                            f"期望 status={a['status']}，实际 {resp.status}", ev)
    if "status_in" in a and resp.status not in a["status_in"]:
        return VerifyResult("http_status", False,
                            f"期望 status ∈ {a['status_in']}，实际 {resp.status}", ev)
    if "status_not_in" in a and resp.status in a["status_not_in"]:
        return VerifyResult("http_status", False,
                            f"期望 status ∉ {a['status_not_in']}，实际 {resp.status}", ev)
    return VerifyResult("http_status", True, f"status={resp.status} 满足断言", ev)


def _p_http_diff(pred: dict, t: SimulatedTarget, host: str) -> VerifyResult:
    req_a = _req(pred.get("a", {}), host)
    req_b = _req(pred.get("b", {}), host)
    resp_a, resp_b = t.handle(req_a), t.handle(req_b)
    a = pred.get("assert", {})
    ev = [_ev(req_a, resp_a), _ev(req_b, resp_b)]

    if resp_a.blocked or resp_b.blocked:
        return VerifyResult("http_diff", False, "请求被作用域拦截", ev)

    if a.get("both_status") and not (resp_a.status == resp_b.status == a["both_status"]):
        return VerifyResult("http_diff", False,
                            f"期望两者 status 均为 {a['both_status']}，"
                            f"实际 {resp_a.status}/{resp_b.status}", ev)

    if a.get("body_differs") and resp_a.body == resp_b.body:
        return VerifyResult("http_diff", False,
                            "期望两个响应体不同（不同属主的数据），但实际相同", ev)

    if a.get("body_same") and resp_a.body != resp_b.body:
        return VerifyResult("http_diff", False, "期望两个响应体相同，但实际不同", ev)

    return VerifyResult("http_diff", True, "响应差异满足断言", ev)


def _p_body_contains(pred: dict, t: SimulatedTarget, host: str) -> VerifyResult:
    req = _req(pred.get("request", {}), host)
    resp = t.handle(req)
    a = pred.get("assert", {})
    ev = [_ev(req, resp)]

    if resp.blocked:
        return VerifyResult("body_contains", False, "请求被作用域拦截", ev)

    for needle in a.get("contains", []) or []:
        if needle not in resp.body:
            return VerifyResult("body_contains", False,
                                f"响应体未包含 {needle!r}", ev)
    for needle in a.get("not_contains", []) or []:
        if needle in resp.body:
            return VerifyResult("body_contains", False,
                                f"响应体意外包含 {needle!r}", ev)
    return VerifyResult("body_contains", True, "响应体内容满足断言", ev)


def _p_header_present(pred: dict, t: SimulatedTarget, host: str) -> VerifyResult:
    req = _req(pred.get("request", {}), host)
    resp = t.handle(req)
    a = pred.get("assert", {})
    ev = [_ev(req, resp)]
    lower = {k.lower() for k in resp.headers}

    for h in a.get("present", []) or []:
        if h.lower() not in lower:
            return VerifyResult("header_present", False, f"缺少响应头 {h!r}", ev)
    for h in a.get("absent", []) or []:
        if h.lower() in lower:
            return VerifyResult("header_present", False, f"意外存在响应头 {h!r}", ev)
    return VerifyResult("header_present", True, "响应头满足断言", ev)


def evaluate_predicates(
    preds: list[dict], target: SimulatedTarget, require_all: bool = True
) -> tuple[bool, list[VerifyResult]]:
    """求值一组判据。

    `require_all=True`（默认）时**全部通过才算通过**——保守策略：
    宁可漏报也不要误报，因为"发现"的代价（执行不相关攻击性技能、稀释报告可信度）
    高于"漏报"。
    """
    results = [evaluate_predicate(p, target) for p in preds]
    if not results:
        return False, results
    passed = all(r.passed for r in results) if require_all else any(r.passed for r in results)
    return passed, results
