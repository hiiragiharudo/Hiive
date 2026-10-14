"""靶场配置：把 `eval/ranges/profiles.json` 装配成可直接运行的靶场。

## 装配了什么

一个"靶场"在本平台里是四件东西的组合：

| 组成 | 说明 |
|---|---|
| **目标适配器** | `HttpTarget`（真实 HTTP）或 `SimulatedTarget`（离线模拟） |
| **技能包** | 该靶场专属的 `SKILL.md`（含方法论文本） |
| **执行计划** | 动作序列 + **验证判据**（判据里的回显标记来自实测，见 `probe_ranges.py`） |
| **登录步骤** | 可选。DVWA 这类靶场必须先登录才能打模块 |

## 登录为什么做成声明式

DVWA 的 `login.php` 调 `checkToken()`——**必须先 GET 页面取 `user_token`
再带着它 POST**，否则返回 200 但什么都没发生（静默失败）。
把这个流程写成代码会让每个新靶场都要改代码；写成声明式配置
（`token` + `body` + `body_from_token` + `then`）则新靶场只需加一段 JSON。

## 安全边界

`HttpTarget` 默认只允许 `localhost` / `127.0.0.1` 与 `127.0.0.0/8`。
本模块**不提供**放宽作用域的入口——要打真实目标必须显式改代码，
以避免误配置导致对非授权目标发包。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..skills.registry import SkillRegistry
from ..skills.router import RouterConfig, SkillRouter
from .http_target import HttpTarget
from .scope import Scope

_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "eval" / "ranges"


@dataclass
class RangeProfile:
    """一个靶场的定义。"""

    name: str
    label: str
    base_url: str
    host: str
    skills_dir: Path
    plans_path: Path
    note: str = ""
    login: dict | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "base_url": self.base_url,
            "host": self.host,
            "skills_dir": str(self.skills_dir),
            "plans_path": str(self.plans_path),
            "note": self.note,
            "requires_login": bool(self.login),
            "exists": self.skills_dir.exists() and self.plans_path.exists(),
        }


def load_profiles(root: Path | None = None) -> dict[str, RangeProfile]:
    """加载全部靶场定义。"""
    root = root or _ROOT
    path = root / "profiles.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, RangeProfile] = {}
    for name, spec in raw.items():
        if name.startswith("_"):
            continue
        out[name] = RangeProfile(
            name=name,
            label=spec.get("label", name),
            base_url=spec.get("base_url", "http://localhost"),
            host=spec.get("host", "localhost"),
            skills_dir=(root / spec["skills_dir"]).resolve(),
            plans_path=(root / spec["plans_path"]).resolve(),
            note=spec.get("note", ""),
            login=spec.get("login"),
        )
    return out


# --------------------------------------------------------------------- 登录


def _fetch_token(target: HttpTarget, spec: dict) -> str:
    r = target.handle(_req(spec))
    m = re.search(spec["regex"], r.body)
    return m.group(1) if m else ""


def _req(spec: dict):
    from .target import HttpRequest

    return HttpRequest(
        method=str(spec.get("method", "GET")).upper(),
        host="",
        path=spec.get("path", "/"),
        query=dict(spec.get("query", {})),
        headers=dict(spec.get("headers", {})),
        body=dict(spec.get("body", {})),
    )


def perform_login(target: HttpTarget, login: dict) -> tuple[bool, str]:
    """执行声明式登录。返回 (是否成功, 说明)。

    `body_from_token` 表示"把前面取到的 token 放进这个字段名"——
    DVWA 的 CSRF 校验需要它。
    """
    detail: list[str] = []

    def step(spec: dict, label: str) -> tuple[bool, str]:
        token = ""
        tok_spec = spec.get("token")
        if tok_spec:
            token = _fetch_token(target, tok_spec)
            if not token:
                return False, f"{label}: 未取到 user_token（页面结构可能已变）"
            detail.append(f"{label} 取到 token")

        body = dict(spec.get("body", {}))
        field_name = spec.get("body_from_token")
        if field_name:
            if not token:
                return False, f"{label}: 声明了 body_from_token 但未取到 token"
            body[field_name] = token

        r = target.handle(_req({**spec, "body": body}))
        if r.blocked:
            return False, f"{label}: 被作用域拦截 {r.body}"

        # 成功判定支持三种形态（不同靶场行为不同）：
        #   1) success_status_in：显式声明成功状态码（如 DVWA 登录成功返回 302）
        #   2) success_contains：响应体包含特定标记（如 "logout.php"）
        # 实测教训：DVWA 登录成功返回 302 且适配器**默认不跟随重定向**，
        # 此时 body 为空，只按 success_contains 判定会**误报登录失败**
        # （而实际上登录成功、后续模块都能访问）。
        codes = spec.get("success_status_in")
        if codes and r.status in codes:
            detail.append(f"{label} HTTP {r.status}（声明的成功状态码）")
            return True, ""

        expect = spec.get("success_contains")
        if expect and expect not in r.body:
            return False, f"{label}: 期望响应含 {expect!r}，实际未出现（HTTP {r.status}）"
        if expect:
            detail.append(f"{label} HTTP {r.status}（含 {expect!r}）")
        else:
            detail.append(f"{label} HTTP {r.status}")
        return True, ""

    ok, msg = step(login, "登录")
    detail.append(msg) if msg else None
    if not ok:
        return False, "；".join(x for x in detail if x)

    then = login.get("then")
    if then:
        ok2, msg2 = step(then, "后续步骤")
        if msg2:
            detail.append(msg2)
        if not ok2:
            return False, "；".join(detail)

    return True, "；".join(detail) + f"（会话 cookie: {sorted(target.cookies.keys())}）"


# --------------------------------------------------------------------- 装配


@dataclass
class RangeRuntime:
    """装配好的靶场运行时。"""

    profile: RangeProfile
    target: HttpTarget
    router: SkillRouter
    plans: dict
    login_ok: bool = False
    login_detail: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile.to_dict(),
            "target": self.target.to_dict(),
            "skills": sorted(self.router.registry.skills),
            "skill_count": len(self.router.registry),
            "plans": sorted(self.plans),
            "login_ok": self.login_ok,
            "login_detail": self.login_detail,
            "warnings": self.warnings,
        }


def build_range(profile: RangeProfile, delay: float = 0.2) -> RangeRuntime:
    """按靶场定义装配出可运行的 `RangeRuntime`。"""
    from .engine import load_plans

    warnings: list[str] = []
    if not profile.skills_dir.exists():
        raise FileNotFoundError(f"技能目录不存在: {profile.skills_dir}")
    if not profile.plans_path.exists():
        raise FileNotFoundError(f"执行计划不存在: {profile.plans_path}")

    target = HttpTarget(
        base_url=profile.base_url,
        HOST=profile.host,
        scope=Scope(hosts=["localhost", "127.0.0.1"], cidrs=["127.0.0.0/8"]),
        delay=delay,
    )

    login_ok = False
    login_detail = ""
    if profile.login:
        login_ok, login_detail = perform_login(target, profile.login)
        if not login_ok:
            warnings.append(f"登录未成功：{login_detail}（依赖登录的模块将无法测试）")

    reg = SkillRegistry()
    reg.load_roots([(profile.name, profile.skills_dir)])
    reg.build_index(vector_kind="tfidf")

    plans = load_plans(profile.plans_path)

    # 计划与技能必须一一对应，否则是配置错误
    only_plan = set(plans) - set(reg.skills)
    only_skill = set(reg.skills) - set(plans)
    if only_plan:
        warnings.append(f"计划里有但技能里没有: {sorted(only_plan)}")
    if only_skill:
        warnings.append(f"技能里有但计划里没有: {sorted(only_skill)}")

    router = SkillRouter(reg, RouterConfig(top_k=5, recall_n=20, channels=("bm25",)))
    return RangeRuntime(
        profile=profile, target=target, router=router, plans=plans,
        login_ok=login_ok, login_detail=login_detail, warnings=warnings,
    )
