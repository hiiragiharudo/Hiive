"""真实靶场适配层与靶场定义的测试。

真实靶场（sqli-labs / DVWA / Pikachu）跑在本机 XAMPP 上，
**未启动时相关测试会自动跳过**，不影响离线测试。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.engine import AgentEngine, load_plans
from app.agent.http_target import HttpTarget
from app.agent.ranges import build_range, load_profiles, perform_login
from app.agent.scope import Scope
from app.agent.target import HttpRequest
from app.skills.registry import SkillRegistry
from app.skills.router import RouterConfig, SkillRouter

REPO = Path(__file__).resolve().parent.parent.parent
RANGES = REPO / "eval" / "ranges"


def _xampp_up() -> bool:
    try:
        import httpx

        httpx.get("http://localhost/", timeout=3)
        return True
    except Exception:
        return False


XAMPP_UP = _xampp_up()
needs_xampp = pytest.mark.skipif(not XAMPP_UP, reason="本机靶场未启动（见 docs/靶场环境搭建.md）")


# --------------------------------------------------------------------- 靶场定义


def test_profiles_load_and_have_required_fields():
    profiles = load_profiles()
    assert set(profiles) >= {"sqli-labs", "dvwa", "pikachu"}
    for name, p in profiles.items():
        assert p.label and p.base_url and p.host
        assert p.skills_dir.name == "skills"
        assert p.plans_path.name == "plans.json"
        assert p.name == name


def test_dvwa_profile_declares_login():
    """DVWA 必须先登录再打模块，配置里必须声明，否则技能会全部打在登录页上。"""
    dvwa = load_profiles()["dvwa"]
    assert dvwa.login is not None
    assert "token" in dvwa.login, "DVWA 登录带 CSRF token，必须声明 token 步骤"
    assert dvwa.login.get("then"), "登录后还需把安全级别切到 low"
    assert dvwa.login["then"]["body"]["security"] == "low"


def test_other_ranges_do_not_require_login():
    profiles = load_profiles()
    assert profiles["sqli-labs"].login is None
    assert profiles["pikachu"].login is None


@pytest.mark.parametrize("name", ["sqli-labs", "dvwa", "pikachu"])
def test_range_skills_and_plans_align(name: str):
    """每个靶场的技能与执行计划必须一一对应，否则是配置错误。"""
    p = load_profiles()[name]
    if not (p.skills_dir.exists() and p.plans_path.exists()):
        pytest.skip(f"{name} 技能包不存在")
    reg = SkillRegistry()
    reg.load_roots([(name, p.skills_dir)])
    plans = load_plans(p.plans_path)
    assert set(plans) == set(reg.skills), (
        f"{name}: 仅在计划中 {set(plans) - set(reg.skills)}，"
        f"仅在技能中 {set(reg.skills) - set(plans)}"
    )


@pytest.mark.parametrize("name", ["sqli-labs", "dvwa", "pikachu"])
def test_every_plan_has_verify_predicates(name: str):
    """★ 每个计划都必须有验证判据——没有判据就不能升级为「发现」。"""
    p = load_profiles()[name]
    if not p.plans_path.exists():
        pytest.skip(f"{name} 计划不存在")
    plans = load_plans(p.plans_path)
    for skill, plan in plans.items():
        assert plan.verify, f"{name}/{skill} 缺少验证判据"
        assert plan.finding_kind, f"{name}/{skill} 缺少 finding_kind"


@pytest.mark.parametrize("name", ["sqli-labs", "dvwa", "pikachu"])
def test_plan_paths_are_target_relative(name: str):
    """判据里的路径必须是相对路径——写死 host 会让判据无法跨靶场复用。"""
    p = load_profiles()[name]
    if not p.plans_path.exists():
        pytest.skip(f"{name} 计划不存在")
    plans = load_plans(p.plans_path)
    for skill, plan in plans.items():
        for pred in plan.verify:
            req = pred.get("request") or pred.get("a") or {}
            if req:
                assert "host" not in req, f"{name}/{skill} 判据写死了 host"
                assert str(req.get("path", "")).startswith("/"), (
                    f"{name}/{skill} 判据路径应为绝对路径（以 / 开头）"
                )


# --------------------------------------------------------------------- HttpTarget


def test_http_target_blocks_out_of_scope_without_network():
    """越界必须在**发出任何数据包之前**被拦下。"""
    t = HttpTarget(base_url="http://localhost", delay=0)
    r = t.handle(HttpRequest("GET", "evil.example.com", "/"))
    assert r.blocked is True
    assert "不在授权范围" in r.body
    assert t.log, "越界也必须留痕"


def test_http_target_default_scope_is_localhost_only():
    """默认只允许本机——避免误配置导致对非授权目标发包。"""
    t = HttpTarget(base_url="http://localhost", delay=0)
    assert t.scope is not None
    assert t.scope.is_allowed("localhost")
    assert t.scope.is_allowed("127.0.0.1")
    assert not t.scope.is_allowed("192.168.1.1")
    assert not t.scope.is_allowed("example.com")


def test_http_target_rejects_custom_widened_scope_host():
    t = HttpTarget(base_url="http://localhost", delay=0,
                   scope=Scope(hosts=["target.internal"]))
    r = t.handle(HttpRequest("GET", "localhost", "/"))
    assert r.blocked, "作用域被显式收窄后，localhost 也应被拦"


def test_http_target_throttle_waits():
    import time

    t = HttpTarget(base_url="http://127.0.0.1:1", delay=0.3, timeout=0.05)
    # 端口 1 必然连不上，但节流应在请求前生效
    t0 = time.monotonic()
    t.handle(HttpRequest("GET", "127.0.0.1", "/", port=1))
    t.handle(HttpRequest("GET", "127.0.0.1", "/", port=1))
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.3, f"第二次请求应被节流，实际间隔 {elapsed:.3f}s"


def test_http_target_records_connection_error_without_raising():
    """连接失败不得抛异常中断任务，应返回错误响应并留痕。"""
    t = HttpTarget(base_url="http://127.0.0.1:1", delay=0, timeout=0.5)
    r = t.handle(HttpRequest("GET", "127.0.0.1", "/", port=1))
    assert r.status == 0
    assert r.route in ("__timeout__", "__http_error__")
    assert t.log


def test_http_target_to_dict_has_session_info():
    t = HttpTarget(base_url="http://localhost", delay=0.1)
    d = t.to_dict()
    assert d["kind"] == "http"
    assert d["base_url"] == "http://localhost"
    assert d["delay"] == 0.1


# --------------------------------------------------------------------- 真实靶场端到端


@needs_xampp
@pytest.mark.parametrize(
    "range_name,query,expect_kinds",
    [
        ("sqli-labs", "先做端点侦察，然后测试 GET 参数的 SQL 注入",
         {"endpoint-discovery", "sql-injection"}),
        ("pikachu", "测试 SQL 注入", {"sql-injection"}),
        ("dvwa", "测试 SQL 注入模块", {"sql-injection"}),
    ],
)
def test_range_end_to_end_finds_real_vulnerability(range_name, query, expect_kinds):
    """★ 在**真实靶场**上跑通并验证出漏洞。

    这是本平台最核心的能力：不是"能连接到靶场"，而是
    "技能执行 → 确定性判据 → 升级为经验证的发现"整条链路成立。
    """
    rt = build_range(load_profiles()[range_name], delay=0.05)
    if rt.profile.login and not rt.login_ok:
        pytest.skip(f"{range_name} 登录失败: {rt.login_detail}")

    eng = AgentEngine(rt.router, rt.plans, target=rt.target, scope=rt.target.scope,
                      max_steps=6, top_k=5)
    result = eng.run(query, task_id=f"test-{range_name}")

    kinds = {f.kind for f in result.graph.verified_findings}
    missing = expect_kinds - kinds
    assert not missing, f"{range_name} 未验证出 {missing}，实际 {kinds}"
    # 每个发现都必须带证据链
    for f in result.graph.verified_findings:
        assert f.verified and f.evidence, f"{f.kind} 缺少证据"
    # 实际发出了真实请求
    assert len(result.tool.calls) > 0
    assert result.tool.blocked_count == 0, "本机靶场不应触发越界拦截"


@needs_xampp
def test_dvwa_login_establishes_session_and_low_level():
    """DVWA 登录必须建立会话**并**把安全级别切到 low，否则模块不可利用。"""
    rt = build_range(load_profiles()["dvwa"], delay=0.05)
    assert rt.login_ok, f"登录失败: {rt.login_detail}"
    cookies = rt.target.cookies
    assert "PHPSESSID" in cookies
    # security cookie 出现说明安全级别切换步骤真的生效了
    assert "security" in cookies, (
        f"未见到 security cookie，安全级别可能没切成 low（cookies={sorted(cookies)}）"
    )


@needs_xampp
def test_xss_predicate_rejects_encoded_output():
    """★ 验证判据本身必须能区分「安全回显」与「真 XSS」。

    断言的是**带标签的原文**：若页面把 `<` 转义成 `&lt;`，
    判据必须失败——否则就是把"有回显"误判为"有 XSS"。
    """
    p = load_profiles()["pikachu"]
    plans = load_plans(p.plans_path)
    plan = plans["pikachu-xss-reflected"]
    # 末尾两条判据：探针回显 + 带标签原文回显
    last = plan.verify[-1]
    assert "<b>" in last["assert"]["contains"][0], (
        "XSS 判据必须断言带标签的原文，否则无法区分编码与未编码"
    )
