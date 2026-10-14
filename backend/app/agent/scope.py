"""作用域（授权范围）强制。

**这是架构层面的越界防护，而非提示词约束。** 提示词约束可以被模型忽略或绕过，
代码级的统一出口校验不能。因此所有出站动作**必须**经过本模块。

设计参考了调研中反复出现的教训：
- 云鼎实验室公开的 5h48m 真实越界实验中，Agent 把靶机当作跳板出网——
  这类行为只有在"统一出口 + 目标白名单"下才可能被拦住；
- 既有工作（`ScopeJudge` / `ScopeBench`）已证明这是独立且未完全解决的问题，
  本课题只做**必要的最小实现**，**不声称**解决了越界检测。
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field


class ScopeViolation(Exception):
    """出站动作超出授权范围。"""


@dataclass
class Scope:
    """授权范围。

    - `hosts`：允许的主机（精确匹配或子域后缀匹配）
    - `cidrs`：允许的 IP 段
    - `ports`：允许的端口；空集表示不限制
    - `allow_schemes`：允许的协议
    """

    hosts: list[str] = field(default_factory=list)
    cidrs: list[str] = field(default_factory=list)
    ports: set[int] = field(default_factory=set)
    allow_schemes: set[str] = field(default_factory=lambda: {"http", "https"})

    def check(self, host: str, port: int | None = None, scheme: str = "http") -> None:
        """校验目标是否在范围内；不在则抛 `ScopeViolation`。"""
        if scheme not in self.allow_schemes:
            raise ScopeViolation(f"协议不在授权范围: {scheme}")

        if port is not None and self.ports and port not in self.ports:
            raise ScopeViolation(f"端口不在授权范围: {port}")

        if self._host_ok(host):
            return
        if port is not None and self._ip_ok(host):
            return
        if self._ip_ok(host):
            return
        raise ScopeViolation(f"主机不在授权范围: {host}")

    def _host_ok(self, host: str) -> bool:
        h = host.lower().strip(".")
        for allowed in self.hosts:
            a = allowed.lower().strip(".")
            if h == a or h.endswith("." + a):
                return True
        return False

    def _ip_ok(self, host: str) -> bool:
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return False
        for cidr in self.cidrs:
            try:
                if ip in ipaddress.ip_network(cidr, strict=False):
                    return True
            except ValueError:
                continue
        return False

    def is_allowed(self, host: str, port: int | None = None, scheme: str = "http") -> bool:
        try:
            self.check(host, port, scheme)
            return True
        except ScopeViolation:
            return False

    def to_dict(self) -> dict:
        return {
            "hosts": list(self.hosts),
            "cidrs": list(self.cidrs),
            "ports": sorted(self.ports),
            "allow_schemes": sorted(self.allow_schemes),
        }
