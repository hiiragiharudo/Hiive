"""离线模拟靶场：植入已知漏洞的**确定性** HTTP 服务。

## 为什么需要它

毕设有"实验验证"章节，必须有可复现的评测环境。真实靶场（DVWA、Juice Shop）
需要 Docker 与网络；而本课题的评测要求是**离线、零成本、可复现**。

因此实现一个进程内的确定性靶场：给定输入必然产生相同输出，
漏洞是**刻意植入且已知**的，因而构成客观真值（ground truth）。

## 明确边界

- 本靶场**不监听任何端口**，不做真实网络 IO，仅作函数调用；
- 漏洞是**模拟**的（例如"两个订单返回不同 owner"），不包含可用 exploit；
- 它服务于"验证判据是否被正确执行"的测试，而非训练攻击能力。

## 植入的漏洞类别

| 端点 | 类别 | 说明 |
|---|---|---|
| `GET /api/orders/{id}` | 水平越权（IDOR/BOLA） | 不同 id 返回不同属主的订单，且不校验属主 |
| `GET /admin/users` | 访问控制缺陷 | 无凭证返回 403，带 `X-Original-URL` 头可绕过 |
| `GET /search?q=` | 反射型 XSS | 查询串被原样反射进 body |
| `POST /upload` | 不安全文件上传 | `filename` 以 `.php` 结尾即接受 |
| `GET /static/` | 目录遍历 | `file=../../etc/passwd` 被"读"出 |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from .scope import Scope, ScopeViolation


@dataclass
class HttpRequest:
    method: str
    host: str
    path: str
    query: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, str] = field(default_factory=dict)
    port: int | None = None
    scheme: str = "http"

    @classmethod
    def from_url(cls, method: str, url: str, **kw) -> "HttpRequest":
        u = urlparse(url)
        return cls(
            method=method.upper(),
            host=u.hostname or "",
            path=u.path or "/",
            query={k: v[0] for k, v in parse_qs(u.query).items()},
            port=u.port,
            scheme=u.scheme or "http",
            **kw,
        )

    @property
    def url(self) -> str:
        q = "&".join(f"{k}={v}" for k, v in self.query.items())
        base = f"{self.scheme}://{self.host}{self.path}"
        return f"{base}?{q}" if q else base

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "url": self.url,
            "headers": dict(self.headers),
            "body": dict(self.body),
        }


@dataclass
class HttpResponse:
    status: int
    body: str
    headers: dict[str, str] = field(default_factory=dict)
    #: 命中的路由名（便于测试与留痕）
    route: str = ""
    #: 是否发生了作用域拦截
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "body": self.body[:2000],
            "headers": dict(self.headers),
            "route": self.route,
            "blocked": self.blocked,
        }


@dataclass
class Route:
    """靶场路由。"""

    name: str
    method: str
    path: str
    status: int = 200
    body: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    #: 若为真，无凭证时返回 403（但伪造头可绕过——植入的访问控制缺陷）
    requires_auth: bool = False
    handler: str = ""


#: 订单数据——不同 id 属主不同，构成水平越权的**客观真值**
ORDERS = {
    "1001": {"owner": "alice", "item": "键盘", "amount": 399},
    "1002": {"owner": "bob", "item": "显示器", "amount": 1299},
}


def _default_routes() -> list[Route]:
    return [
        Route(name="home", method="GET", path="/", body="<h1>Hiive Lab</h1>"),
        Route(
            name="order",
            method="GET",
            path="/api/orders/{id}",
            handler="order",
        ),
        Route(
            name="admin_users",
            method="GET",
            path="/admin/users",
            status=403,
            body="forbidden",
            requires_auth=True,
            handler="admin_users",
        ),
        Route(
            name="search",
            method="GET",
            path="/search",
            handler="search",
        ),
        Route(name="upload", method="POST", path="/upload", handler="upload"),
        Route(name="static", method="GET", path="/static", handler="static"),
    ]


class SimulatedTarget:
    """进程内确定性靶场。"""

    HOST = "lab.local"

    def __init__(self, scope: Scope | None = None, routes: list[Route] | None = None) -> None:
        self.scope = scope or Scope(hosts=[self.HOST])
        self.routes = routes or _default_routes()
        #: 全部已处理的请求（留痕用）
        self.log: list[tuple[HttpRequest, HttpResponse]] = []

    # ---------------------------------------------------------------- 入口

    def handle(self, req: HttpRequest) -> HttpResponse:
        """处理请求。**作用域校验在任何路由匹配之前**——越界一律拒绝。"""
        try:
            self.scope.check(req.host, req.port, req.scheme)
        except ScopeViolation as e:
            resp = HttpResponse(
                status=0,
                body=str(e),
                blocked=True,
                route="__scope_violation__",
            )
            self.log.append((req, resp))
            return resp

        route, params = self._match(req)
        if route is None:
            resp = HttpResponse(status=404, body="not found", route="__no_match__")
        else:
            resp = self._dispatch(route, params, req)

        self.log.append((req, resp))
        return resp

    def _match(self, req: HttpRequest) -> tuple[Route | None, dict[str, str]]:
        req_parts = [p for p in req.path.split("/") if p]
        for r in self.routes:
            if r.method != req.method:
                continue
            rt_parts = [p for p in r.path.split("/") if p]
            if len(rt_parts) != len(req_parts):
                continue
            params: dict[str, str] = {}
            ok = True
            for rp, ap in zip(rt_parts, req_parts):
                if rp.startswith("{") and rp.endswith("}"):
                    params[rp[1:-1]] = ap
                elif rp != ap:
                    ok = False
                    break
            if ok:
                return r, params
        return None, {}

    def _dispatch(
        self, route: Route, params: dict[str, str], req: HttpRequest
    ) -> HttpResponse:
        handler = getattr(self, f"_h_{route.handler}", None) if route.handler else None
        if handler is not None:
            return handler(route, params, req)

        # 无 handler：按静态定义返回，但处理 requires_auth 的绕过逻辑
        if route.requires_auth and not self._bypass_headers(req):
            return HttpResponse(status=403, body="forbidden", route=route.name)
        return HttpResponse(status=route.status, body=route.body,
                            headers=dict(route.headers), route=route.name)

    @staticmethod
    def _bypass_headers(req: HttpRequest) -> bool:
        """植入的访问控制缺陷：这些头会被错误地当作已授权。"""
        h = {k.lower(): v for k, v in req.headers.items()}
        return any(
            k in h
            for k in ("x-original-url", "x-rewrite-url", "x-forwarded-for", "x-custom-ip-authorization")
        )

    # ---------------------------------------------------------------- handlers

    def _h_order(self, route: Route, params: dict[str, str], req: HttpRequest) -> HttpResponse:
        """水平越权植入点：**不校验属主**，任意 id 都返回。"""
        oid = params.get("id", "")
        order = ORDERS.get(oid)
        if order is None:
            return HttpResponse(status=404, body="order not found", route=route.name)
        return HttpResponse(
            status=200,
            body=f'{{"order_id":"{oid}","owner":"{order["owner"]}",'
                 f'"item":"{order["item"]}","amount":{order["amount"]}}}',
            headers={"content-type": "application/json"},
            route=route.name,
        )

    def _h_admin_users(self, route: Route, params: dict[str, str], req: HttpRequest) -> HttpResponse:
        if not self._bypass_headers(req):
            return HttpResponse(status=403, body="forbidden", route=route.name)
        return HttpResponse(
            status=200,
            body='[{"user":"admin","role":"admin"},{"user":"alice","role":"user"}]',
            headers={"content-type": "application/json"},
            route=route.name,
        )

    def _h_search(self, route: Route, params: dict[str, str], req: HttpRequest) -> HttpResponse:
        """反射型 XSS 植入点：查询串被原样写入 body。"""
        q = req.query.get("q", "")
        return HttpResponse(
            status=200,
            body=f'<html><body><h2>搜索结果：</h2><div id="q">{q}</div></body></html>',
            headers={"content-type": "text/html"},
            route=route.name,
        )

    def _h_upload(self, route: Route, params: dict[str, str], req: HttpRequest) -> HttpResponse:
        """不安全上传植入点：只按扩展名判断，`.php` 被接受。"""
        name = req.body.get("filename", "")
        if name.lower().endswith((".php", ".php5", ".phtml")):
            return HttpResponse(
                status=200,
                body=f'{{"uploaded":"{name}","path":"/uploads/{name}"}}',
                route=route.name,
            )
        return HttpResponse(status=200, body='{"uploaded":false,"reason":"extension"}',
                            route=route.name)

    def _h_static(self, route: Route, params: dict[str, str], req: HttpRequest) -> HttpResponse:
        """目录遍历植入点：`file` 参数未做规范化。"""
        f = req.query.get("file", "")
        if "../" in f:
            return HttpResponse(
                status=200,
                body="root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:...",
                route=route.name,
            )
        return HttpResponse(status=200, body=f"<file>{f}</file>", route=route.name)
