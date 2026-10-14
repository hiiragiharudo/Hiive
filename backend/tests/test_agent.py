"""Agent 执行引擎的测试：作用域、靶场、验证判据、回溯、端到端循环。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.engine import AgentEngine, load_plans
from app.agent.scope import Scope, ScopeViolation
from app.agent.state import AttackGraph, Finding, PHASE_ORDER
from app.agent.target import HttpRequest, SimulatedTarget
from app.agent.tools import HttpTool
from app.agent.trace import StepRecord, Trace
from app.agent.verify import evaluate_predicate, evaluate_predicates
from app.skills.registry import SkillRegistry
from app.skills.router import RouterConfig, SkillRouter

REPO = Path(__file__).resolve().parent.parent.parent
LAB_SKILLS = REPO / "eval" / "lab" / "skills"
LAB_PLANS = REPO / "eval" / "lab" / "plans.json"


# --------------------------------------------------------------------- 作用域


def test_scope_allows_exact_host_and_subdomain():
    s = Scope(hosts=["example.com"])
    s.check("example.com")
    s.check("api.example.com")
    with pytest.raises(ScopeViolation):
        s.check("example.com.evil.net")


def test_scope_rejects_unlisted_host():
    s = Scope(hosts=["lab.local"])
    with pytest.raises(ScopeViolation, match="主机不在授权范围"):
        s.check("8.8.8.8")


def test_scope_enforces_port_and_scheme():
    s = Scope(hosts=["lab.local"], ports={80, 443})
    s.check("lab.local", 80)
    with pytest.raises(ScopeViolation, match="端口"):
        s.check("lab.local", 8080)
    with pytest.raises(ScopeViolation, match="协议"):
        s.check("lab.local", 80, scheme="ftp")


def test_scope_allows_cidr():
    s = Scope(cidrs=["10.0.0.0/24"])
    s.check("10.0.0.5")
    with pytest.raises(ScopeViolation):
        s.check("10.0.1.5")


def test_scope_is_allowed_helper():
    s = Scope(hosts=["lab.local"])
    assert s.is_allowed("lab.local")
    assert not s.is_allowed("elsewhere.local")


# --------------------------------------------------------------------- 靶场


def test_target_planted_idor_returns_different_owners():
    t = SimulatedTarget()
    a = t.handle(HttpRequest("GET", t.HOST, "/api/orders/1001"))
    b = t.handle(HttpRequest("GET", t.HOST, "/api/orders/1002"))
    assert a.status == b.status == 200
    assert a.body != b.body
    assert "alice" in a.body and "bob" in b.body


def test_target_admin_requires_auth_but_header_bypass_works():
    t = SimulatedTarget()
    blocked = t.handle(HttpRequest("GET", t.HOST, "/admin/users"))
    assert blocked.status == 403
    bypassed = t.handle(
        HttpRequest("GET", t.HOST, "/admin/users", headers={"X-Original-URL": "/admin/users"})
    )
    assert bypassed.status == 200


def test_target_search_reflects_query():
    t = SimulatedTarget()
    r = t.handle(HttpRequest("GET", t.HOST, "/search", query={"q": "hiive_probe"}))
    assert "hiive_probe" in r.body


def test_target_upload_accepts_php_extension_only():
    t = SimulatedTarget()
    bad = t.handle(HttpRequest("POST", t.HOST, "/upload", body={"filename": "a.jpg"}))
    good = t.handle(HttpRequest("POST", t.HOST, "/upload", body={"filename": "a.phtml"}))
    assert '"uploaded":false' in bad.body
    assert "a.phtml" in good.body


def test_target_static_traversal_leaks_passwd():
    t = SimulatedTarget()
    r = t.handle(HttpRequest("GET", t.HOST, "/static", query={"file": "../../etc/passwd"}))
    assert "root:x:0:0" in r.body


def test_target_blocks_out_of_scope_before_routing():
    """作用域校验必须发生在路由匹配之前——越界请求不应触达任何 handler。"""
    t = SimulatedTarget()
    r = t.handle(HttpRequest("GET", "evil.example.com", "/admin/users"))
    assert r.blocked is True
    assert r.route == "__scope_violation__"
    assert r.status == 0


def test_target_404_for_unknown_path():
    t = SimulatedTarget()
    r = t.handle(HttpRequest("GET", t.HOST, "/nope"))
    assert r.status == 404


# --------------------------------------------------------------------- 工具层


def test_http_tool_records_calls_and_blocks_out_of_scope():
    scope = Scope(hosts=["lab.local"])
    tool = HttpTool(SimulatedTarget(scope), scope)
    tool.request("GET", "lab.local", "/")
    bad = tool.request("GET", "evil.local", "/")
    assert bad.blocked is True
    assert tool.blocked_count == 1
    assert len(tool.calls) == 2
    assert tool.calls[1].error


# --------------------------------------------------------------------- 验证判据


@pytest.fixture()
def target() -> SimulatedTarget:
    return SimulatedTarget()


def test_verify_http_status_pass_and_fail(target: SimulatedTarget):
    ok = evaluate_predicate(
        {"kind": "http_status", "request": {"method": "GET", "path": "/"},
         "assert": {"status": 200}},
        target,
    )
    assert ok.passed
    bad = evaluate_predicate(
        {"kind": "http_status", "request": {"method": "GET", "path": "/"},
         "assert": {"status_not_in": [200]}},
        target,
    )
    assert not bad.passed


def test_verify_http_diff_detects_bola(target: SimulatedTarget):
    r = evaluate_predicate(
        {"kind": "http_diff",
         "a": {"method": "GET", "path": "/api/orders/1001"},
         "b": {"method": "GET", "path": "/api/orders/1002"},
         "assert": {"both_status": 200, "body_differs": True}},
        target,
    )
    assert r.passed, r.detail
    assert len(r.evidence) == 2


def test_verify_http_diff_rejects_same_body(target: SimulatedTarget):
    r = evaluate_predicate(
        {"kind": "http_diff",
         "a": {"method": "GET", "path": "/"},
         "b": {"method": "GET", "path": "/"},
         "assert": {"body_differs": True}},
        target,
    )
    assert not r.passed


def test_verify_body_contains(target: SimulatedTarget):
    ok = evaluate_predicate(
        {"kind": "body_contains",
         "request": {"method": "GET", "path": "/search", "query": {"q": "probe_zz"}},
         "assert": {"contains": ["probe_zz"]}},
        target,
    )
    assert ok.passed
    bad = evaluate_predicate(
        {"kind": "body_contains",
         "request": {"method": "GET", "path": "/search", "query": {"q": "x"}},
         "assert": {"contains": ["SQL syntax"]}},
        target,
    )
    assert not bad.passed, "靶场无 SQL 报错，该判据必须失败"


def test_verify_rejects_unsupported_kind(target: SimulatedTarget):
    r = evaluate_predicate({"kind": "execute_shell", "cmd": "id"}, target)
    assert not r.passed
    assert "不支持" in r.detail


def test_verify_scope_violation_is_not_passing(target: SimulatedTarget):
    r = evaluate_predicate(
        {"kind": "http_status",
         "request": {"method": "GET", "host": "evil.local", "path": "/"},
         "assert": {"status": 200}},
        target,
    )
    assert not r.passed
    assert "作用域" in r.detail


def test_verify_predicates_require_all_by_default(target: SimulatedTarget):
    preds = [
        {"kind": "http_status", "request": {"method": "GET", "path": "/"},
         "assert": {"status": 200}},
        {"kind": "http_status", "request": {"method": "GET", "path": "/"},
         "assert": {"status": 500}},
    ]
    passed, results = evaluate_predicates(preds, target)
    assert not passed and len(results) == 2
    passed_any, _ = evaluate_predicates(preds, target, require_all=False)
    assert passed_any


def test_verify_empty_predicates_is_not_passing(target: SimulatedTarget):
    passed, results = evaluate_predicates([], target)
    assert not passed and results == []


# --------------------------------------------------------------------- 状态


def test_graph_phase_only_advances():
    g = AttackGraph()
    g.advance_phase("discovery")
    assert g.phase == "discovery"
    g.advance_phase("recon")  # 不得后退
    assert g.phase == "discovery"
    g.advance_phase("post")
    assert g.phase == "post"
    assert PHASE_ORDER.index("post") > PHASE_ORDER.index("discovery")


def test_graph_separates_findings_from_candidates():
    from app.agent.state import Candidate

    g = AttackGraph()
    g.add_finding(Finding(skill="a", kind="bola", asset="/x", verified=True))
    g.add_finding(Finding(skill="b", kind="xss", asset="/y", verified=False))
    g.add_candidate(Candidate(skill="b", kind="xss", asset="/y"))
    assert len(g.verified_findings) == 1
    assert g.to_dict()["verified_count"] == 1


# --------------------------------------------------------------------- 回溯


def test_trace_contribution_aggregates_per_skill():
    t = Trace(task_id="t")
    t.add(StepRecord(step=1, skill="a", outcome="executed", verified=True, tool_calls=2))
    t.add(StepRecord(step=2, skill="a", outcome="executed", verified=False,
                     rejected_reason="判据未通过", tool_calls=1))
    t.add(StepRecord(step=3, skill="b", outcome="skipped_no_plan"))
    c = t.contribution()
    assert c["a"]["executed"] == 2 and c["a"]["verified"] == 1
    assert c["a"]["hit_rate"] == 0.5
    assert c["a"]["reject_reasons"] == ["判据未通过"]
    assert c["b"]["skipped"] == 1 and c["b"]["hit_rate"] == 0.0


def test_trace_to_dict_has_steps_and_contribution():
    t = Trace(task_id="t", query="q")
    t.add(StepRecord(step=1, skill="a", outcome="executed"))
    d = t.to_dict()
    assert d["step_count"] == 1 and "contribution" in d and "a" in d["contribution"]


# --------------------------------------------------------------------- 端到端


@pytest.fixture()
def lab_router(tmp_path: Path) -> SkillRouter:
    if not LAB_SKILLS.exists():
        pytest.skip("实验靶场技能不存在")
    reg = SkillRegistry()
    reg.load_roots([("lab", LAB_SKILLS)])
    reg.build_index(vector_kind="tfidf")
    return SkillRouter(reg, RouterConfig(top_k=3, recall_n=10))


@pytest.fixture()
def plans():
    if not LAB_PLANS.exists():
        pytest.skip("实验靶场计划不存在")
    return load_plans(LAB_PLANS)


def test_lab_skills_and_plans_align(lab_router: SkillRouter, plans):
    """每个执行计划都必须对应一个真实存在的技能，反之亦然。"""
    skill_names = set(lab_router.registry.skills)
    assert set(plans) == skill_names, (
        f"计划与技能不匹配：仅在计划中 {set(plans) - skill_names}，"
        f"仅在技能中 {skill_names - set(plans)}"
    )


def test_engine_end_to_end_produces_verified_findings(lab_router: SkillRouter, plans):
    eng = AgentEngine(lab_router, plans, max_steps=10, top_k=3)
    result = eng.run("对目标做端点枚举，然后测试水平越权和访问控制绕过", task_id="t1")
    kinds = {f.kind for f in result.graph.verified_findings}
    assert "bola" in kinds, f"应验证出水平越权，实际 {kinds}"
    assert result.graph.phase in PHASE_ORDER
    assert result.trace.terminated_reason


def test_engine_rejects_false_positive_via_verification(lab_router: SkillRouter, plans):
    """核心断言：技能"声称"有问题但判据未通过时，不得升级为发现。"""
    eng = AgentEngine(lab_router, plans, max_steps=12, top_k=6)
    result = eng.run("测试搜索框的 SQL 注入", task_id="t2")

    verified_kinds = {f.kind for f in result.graph.verified_findings}
    assert "sql-injection" not in verified_kinds, "靶场无 SQL 报错，不得成为经验证的发现"

    rejected = {c.kind for c in result.graph.candidates}
    assert "sql-injection" in rejected or not any(
        s.skill == "sqli-search-false-positive" and s.outcome == "executed"
        for s in result.trace.steps
    ), "SQL 注入候选应被记录为拒绝而非发现"


def test_engine_records_skipped_skills_honestly(lab_router: SkillRouter, plans):
    """语料中未声明执行计划的技能必须如实记为 skipped，而非假装执行。"""
    eng = AgentEngine(lab_router, plans, max_steps=6, top_k=3)
    result = eng.run("测试水平越权", task_id="t3")
    for s in result.trace.steps:
        if s.outcome != "executed":
            assert s.skipped_reason, f"{s.skill} 跳过必须给出原因"


def test_engine_all_executed_steps_have_evidence(lab_router: SkillRouter, plans):
    """每个执行步都必须有动作与验证结果留痕——无证据不得算作执行。"""
    eng = AgentEngine(lab_router, plans, max_steps=10, top_k=5)
    result = eng.run("端点枚举 水平越权 目录遍历", task_id="t4")
    executed = [s for s in result.trace.steps if s.outcome == "executed"]
    assert executed, "应至少执行一个技能"
    for s in executed:
        assert s.actions, f"{s.skill} 执行步缺少动作留痕"
        assert s.verify_results, f"{s.skill} 执行步缺少验证结果留痕"


def test_engine_terminates_on_step_limit(lab_router: SkillRouter, plans):
    eng = AgentEngine(lab_router, plans, max_steps=2, top_k=3)
    result = eng.run("端点枚举 水平越权 目录遍历 XSS", task_id="t5")
    assert len(result.trace.steps) <= 2


def test_engine_pulls_in_dependency_first(lab_router: SkillRouter, plans):
    """编排：`bola-order-id-swap` 声明 requires `recon-endpoint-enum`，后者须先执行。"""
    eng = AgentEngine(lab_router, plans, max_steps=6, top_k=2)
    result = eng.run("测试接口的水平越权", task_id="t6")
    names = [s.skill for s in result.trace.steps]
    if "recon-endpoint-enum" in names and "bola-order-id-swap" in names:
        assert names.index("recon-endpoint-enum") < names.index("bola-order-id-swap")


def test_engine_blocks_out_of_scope_and_records_it(lab_router: SkillRouter, plans):
    """越界请求必须被拦截并留痕，而不是静默失败。"""
    scope = Scope(hosts=["only-this.local"])
    eng = AgentEngine(lab_router, plans, scope=scope, max_steps=4, top_k=3)
    result = eng.run("端点枚举", task_id="t7")
    assert result.tool.blocked_count > 0, "靶场主机不在范围内，应产生拦截"
    assert all(c.blocked for c in result.tool.calls if c.blocked)


def test_engine_circuit_breaks_on_repeated_scope_blocks(lab_router: SkillRouter, plans):
    """★ 越界熔断：累计拦截达上限须立即中止，而不是把候选技能逐个试完。

    实测发现的问题：靶场主机不在授权范围时，引擎原本会把所有候选技能执行完才停，
    即使每次请求都被拦截。一个持续冲击被拦目标的 Agent 本身就是风险。
    """
    scope = Scope(hosts=["not-the-lab.local"])
    eng = AgentEngine(lab_router, plans, scope=scope, max_steps=20, top_k=6,
                      max_blocked_calls=2)
    result = eng.run("端点枚举 水平越权 目录遍历 XSS 上传", task_id="t7b")
    assert result.tool.blocked_count <= 4, "应在拦截达上限后尽快中止"
    assert "越界" in result.trace.terminated_reason
    assert len(result.trace.steps) < 6, "不应把所有候选技能都试完"
    assert not result.graph.verified_findings


def test_engine_scope_block_termination_is_configurable(lab_router: SkillRouter, plans):
    """把上限设为很大时，引擎仍受步数上限约束（两种终止条件独立生效）。"""
    scope = Scope(hosts=["not-the-lab.local"])
    eng = AgentEngine(lab_router, plans, scope=scope, max_steps=3, top_k=6,
                      max_blocked_calls=999)
    result = eng.run("端点枚举 水平越权", task_id="t7c")
    assert len(result.trace.steps) <= 3


def test_engine_result_serializes(lab_router: SkillRouter, plans):
    eng = AgentEngine(lab_router, plans, max_steps=5, top_k=3)
    d = eng.run("水平越权", task_id="t8").to_dict()
    for key in ("task_id", "graph", "trace", "routings", "scope", "tools", "summary"):
        assert key in d
    assert d["summary"]["steps"] >= 1


def test_engine_respects_abstention(lab_router: SkillRouter, plans):
    """路由弃权时引擎应立即终止，而不是硬凑技能执行。"""
    eng = AgentEngine(lab_router, plans, max_steps=5, top_k=3)
    eng.router.config.min_coverage = 1.0  # 强制弃权
    result = eng.run("zzzqqq wwweee", task_id="t9")
    assert result.trace.steps == []
    assert "弃权" in result.trace.terminated_reason
