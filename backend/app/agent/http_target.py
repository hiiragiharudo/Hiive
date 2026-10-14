"""真实 HTTP 靶场适配器。

## 与 `SimulatedTarget` 的关系

两者实现**同一接口**（`Target.handle`），因此技能执行计划与验证判据 DSL
对"打模拟靶场"和"打真靶场"**完全通用**——不需要两套代码。

## 安全纪律（对真实靶场更严格）

1. **作用域强制**：每次请求前校验主机/端口/协议，越界返回 `blocked=True`；
2. **请求节流**：两次请求之间强制间隔（默认 0.2 s），避免打崩靶场；
3. **超时**：默认 15 s，超时不抛异常而是返回错误响应，任务不中断；
4. **默认只允许本机**：`localhost` / `127.0.0.1` 之外的目标需要显式放宽作用域。

## 会话支持

DVWA 这类靶场需要**先登录再打模块**，因此本适配器持有一个 `httpx.Client`，
**Cookie 在请求之间保持**。登录本身是一次普通请求，由技能的执行计划声明。

## 刻意不做的事

- **不跟随重定向**（默认）：渗透测试中重定向本身是信息（如登录态失效跳转），
  自动跟随会掩盖它。需要时可由技能显式声明。
- **不做 TLS 校验豁免的默认放宽**：靶场是 http，暂不涉及。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx

from .scope import Scope, ScopeViolation
from .target import HttpRequest, HttpResponse


@dataclass
class HttpTarget:
    """真实 HTTP 靶场。"""

    #: 靶场根地址，如 `http://localhost`
    base_url: str
    HOST: str = "localhost"
    scope: Scope | None = None
    timeout: float = 15.0
    #: 请求之间的最小间隔（秒）——节流纪律
    delay: float = 0.2
    follow_redirects: bool = False
    #: 默认请求头（如 DVWA 需要的 Referer / Cookie）
    default_headers: dict[str, str] = field(default_factory=dict)

    _client: httpx.Client | None = field(default=None, init=False, repr=False)
    _last_at: float = field(default=0.0, init=False, repr=False)
    log: list[tuple[HttpRequest, HttpResponse]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.scope is None:
            # 默认只允许本机 —— 真实靶场必须显式放宽
            self.scope = Scope(hosts=["localhost", "127.0.0.1"],
                               cidrs=["127.0.0.0/8"])
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=self.follow_redirects,
                headers={"User-Agent": "Hiive/0.1 (authorized lab testing)",
                         **self.default_headers},
            )

    # ---------------------------------------------------------------- 接口

    @property
    def client(self) -> httpx.Client:
        assert self._client is not None
        return self._client

    @property
    def cookies(self) -> dict[str, str]:
        return dict(self.client.cookies)

    def set_cookies(self, cookies: dict[str, str]) -> None:
        for k, v in cookies.items():
            self.client.cookies.set(k, v)

    def handle(self, req: HttpRequest) -> HttpResponse:
        """发送真实 HTTP 请求。

        **作用域校验在任何网络动作之前**——越界不发出任何数据包。
        """
        host = req.host or self.HOST
        port = req.port if req.port is not None else (443 if req.scheme == "https" else 80)
        try:
            assert self.scope is not None
            self.scope.check(host, req.port, req.scheme)
        except ScopeViolation as e:
            resp = HttpResponse(status=0, body=str(e), blocked=True,
                                route="__scope_violation__")
            self.log.append((req, resp))
            return resp

        self._throttle()

        url = req.path or "/"
        if req.query:
            url = f"{url}?{urlencode(req.query)}"

        try:
            if req.method.upper() in ("POST", "PUT", "PATCH"):
                r = self.client.request(
                    req.method.upper(), url,
                    data=req.body or None, headers=req.headers or None,
                )
            else:
                r = self.client.request(
                    req.method.upper(), url,
                    headers=req.headers or None,
                )
        except httpx.TimeoutException:
            resp = HttpResponse(status=0, body=f"请求超时（{self.timeout}s）",
                                route="__timeout__")
            self.log.append((req, resp))
            return resp
        except httpx.HTTPError as e:
            resp = HttpResponse(status=0, body=f"{type(e).__name__}: {e}",
                                route="__http_error__")
            self.log.append((req, resp))
            return resp

        resp = HttpResponse(
            status=r.status_code,
            body=r.text,
            headers={k.lower(): v for k, v in r.headers.items()},
            route=f"{req.method.upper()} {req.path}",
        )
        self.log.append((req, resp))
        return resp

    # ---------------------------------------------------------------- 辅助

    def _throttle(self) -> None:
        if self.delay <= 0:
            return
        gap = time.monotonic() - self._last_at
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last_at = time.monotonic()

    def get(self, path: str, **kw) -> HttpResponse:
        return self.handle(HttpRequest("GET", self.HOST, path, **kw))

    def post(self, path: str, body: dict | None = None, **kw) -> HttpResponse:
        return self.handle(HttpRequest("POST", self.HOST, path, body=body or {}, **kw))

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def to_dict(self) -> dict:
        return {
            "kind": "http",
            "base_url": self.base_url,
            "host": self.HOST,
            "delay": self.delay,
            "timeout": self.timeout,
            "follow_redirects": self.follow_redirects,
            "calls": len(self.log),
            "cookies": sorted(self.cookies.keys()),
        }
