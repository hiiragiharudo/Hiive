"""FastAPI 接口层测试。

使用 `create_app(settings)` 注入**临时语料**，使测试不依赖本机技能库。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

SKILLS = {
    "sqli": (
        "---\n"
        "name: sqli-sql-injection\n"
        "description: >-\n"
        "  SQL 注入测试剧本。当参数存在报错或布尔差异时使用。\n"
        "domains: [web]\n"
        "phase: discovery\n"
        "triggers:\n"
        "  - 注入\n"
        "  - 报错注入\n"
        "risk: medium\n"
        "---\n"
        "# SQL 注入\n\n用报错注入确认注入点。\n"
    ),
    "idor": (
        "---\n"
        "name: idor-broken-object-authorization\n"
        "description: 水平越权测试，替换对象标识比较响应归属。\n"
        "domains: [api]\n"
        "phase: discovery\n"
        "triggers: [越权, 对象标识]\n"
        "risk: low\n"
        "---\n"
        "# 水平越权\n\n替换 id 比较两个主体的响应。\n"
    ),
    "post": (
        "---\n"
        "name: post-exploitation-lateral\n"
        "description: 后渗透横向移动与提权准备。\n"
        "domains: [post]\n"
        "phase: post\n"
        "requires: [recon-subdomain]\n"
        "triggers: [横向, 提权]\n"
        "risk: high\n"
        "---\n"
        "# 横向移动\n\n注意高风险操作需审批。\n"
    ),
    "recon": (
        "---\n"
        "name: recon-subdomain\n"
        "description: 子域名收集与资产测绘。\n"
        "domains: [network]\n"
        "phase: recon\n"
        "triggers: [子域名, 资产]\n"
        "risk: low\n"
        "---\n"
        "# 子域名收集\n\n证书透明度日志与字典爆破。\n"
    ),
}


@pytest.fixture()
def corpus(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    for sub, content in SKILLS.items():
        d = root / sub
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
    return root


@pytest.fixture()
def client(corpus: Path) -> TestClient:
    settings = Settings(
        skill_roots=[("test", corpus)],
        lexicon_path=None,
        enrich_triggers=True,
        expand_query=True,
        channels=("bm25",),
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


# --------------------------------------------------------------------- meta


def test_health_reports_loaded(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert d["loaded"] is True
    assert d["skill_count"] == 4


def test_config_distinguishes_index_and_query_params(client: TestClient):
    """前端必须能区分哪些参数改动需要重建索引。"""
    d = client.get("/api/config").json()
    assert "scoring" in d["index_time_params"]
    assert "enrich_triggers" in d["index_time_params"]
    assert "top_k" in d["query_time_params"]
    assert "expand_query" in d["query_time_params"]
    # 建索引时参数不得出现在查询时参数里
    assert not set(d["index_time_params"]) & set(d["query_time_params"])


# --------------------------------------------------------------------- skills


def test_skills_stats(client: TestClient):
    d = client.get("/api/skills/stats").json()
    assert d["total"] == 4
    assert d["by_phase"]["discovery"] == 2
    assert d["baseline_meta_tokens"] > 0


def test_skills_names_sorted(client: TestClient):
    names = client.get("/api/skills/names").json()["names"]
    assert names == sorted(names)
    assert "sqli-sql-injection" in names


def test_skills_list_filters(client: TestClient):
    assert client.get("/api/skills").json()["total"] == 4
    assert client.get("/api/skills", params={"domain": "api"}).json()["total"] == 1
    assert client.get("/api/skills", params={"phase": "recon"}).json()["total"] == 1
    assert client.get("/api/skills", params={"risk": "high"}).json()["total"] == 1
    assert client.get("/api/skills", params={"q": "越权"}).json()["total"] == 1


def test_skills_list_pagination(client: TestClient):
    d = client.get("/api/skills", params={"limit": 2, "offset": 0}).json()
    assert d["total"] == 4 and len(d["items"]) == 2
    d2 = client.get("/api/skills", params={"limit": 2, "offset": 2}).json()
    assert len(d2["items"]) == 2
    assert d["items"][0]["name"] != d2["items"][0]["name"]


def test_skill_detail_includes_dependencies_and_tokens(client: TestClient):
    d = client.get("/api/skills/post-exploitation-lateral").json()
    assert d["name"] == "post-exploitation-lateral"
    assert "recon-subdomain" in d["dependency_closure"]
    assert d["missing_dependencies"] == []
    assert d["estimated_meta_tokens"] > 0
    assert d["estimated_body_tokens"] > 0
    assert d["body"]


def test_skill_detail_404(client: TestClient):
    r = client.get("/api/skills/does-not-exist")
    assert r.status_code == 404
    assert "不存在" in r.json()["detail"]


def test_skill_detail_reports_missing_dependency(corpus: Path, tmp_path: Path):
    """`requires` 指向不存在的技能时必须如实报告，而非静默忽略。"""
    extra = tmp_path / "extra"
    d = extra / "x"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: needs-ghost\ndescription: 依赖不存在的技能\n"
        "requires: [ghost-skill]\n---\n正文\n",
        encoding="utf-8",
    )
    app = create_app(Settings(skill_roots=[("a", corpus), ("b", extra)],
                              lexicon_path=None))
    with TestClient(app) as c:
        d = c.get("/api/skills/needs-ghost").json()
        assert d["missing_dependencies"] == ["ghost-skill"]


def test_skills_reload(client: TestClient):
    r = client.post("/api/skills/reload", json={"apply_metadata_overlay": True})
    assert r.status_code == 200
    assert r.json()["reloaded"] is True
    assert r.json()["skill_count"] == 4


def test_reload_without_overlay_keeps_declared_only(corpus: Path):
    """关闭元数据推断后，未声明 phase 的技能应保持为空。"""
    root = corpus
    d = root / "bare"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: bare-skill\ndescription: 只有 name 和 description\n---\n正文\n",
        encoding="utf-8",
    )
    app = create_app(Settings(skill_roots=[("t", root)], lexicon_path=None))
    with TestClient(app) as c:
        c.post("/api/skills/reload", json={"apply_metadata_overlay": False})
        d2 = c.get("/api/skills/bare-skill").json()
        assert d2["phase"] == "", "关闭推断后不应有 phase"


# --------------------------------------------------------------------- route


def test_route_returns_candidates_with_reasons_and_cost(client: TestClient):
    r = client.post("/api/route", json={"query": "测试水平越权，替换对象标识"})
    assert r.status_code == 200
    d = r.json()
    assert d["candidates"], "应召回技能"
    top = d["candidates"][0]
    assert top["name"] == "idor-broken-object-authorization"
    assert top["reason"]
    # 成本模型字段齐备
    cost = d["cost"]
    assert cost["baseline_meta_tokens"] > 0
    assert cost["injected_tokens"] > 0
    assert 0.0 <= cost["meta_saving_ratio"] <= 1.0
    assert d["timing_ms"]["stage1"] >= 0


def test_route_records_query_expansion(client: TestClient):
    d = client.post("/api/route", json={"query": "测试水平越权"}).json()
    assert d["cross_lingual"]["expanded"] is True
    assert any(e["zh"] == "水平越权" for e in d["cross_lingual"]["expansion"])


def test_route_top_k_override(client: TestClient):
    d = client.post("/api/route", json={"query": "注入 越权 子域名", "top_k": 2}).json()
    assert len(d["candidates"]) <= 2
    assert d["applied_overrides"]["top_k"] == 2


def test_route_include_body(client: TestClient):
    d = client.post("/api/route", json={"query": "水平越权", "include_body": True}).json()
    assert d["candidates"][0].get("body")


def test_route_rejects_empty_query(client: TestClient):
    assert client.post("/api/route", json={"query": ""}).status_code == 422


def test_route_rejects_unknown_param(client: TestClient):
    """建索引时参数不应能通过 /api/route 覆盖——必须明确报错而非静默忽略。"""
    r = client.post("/api/route", json={"query": "越权", "scoring": "flat"})
    assert r.status_code == 422


def test_route_rejects_top_k_above_recall_n(client: TestClient):
    r = client.post("/api/route",
                    json={"query": "越权", "top_k": 20, "recall_n": 5})
    assert r.status_code == 422
    assert "recall_n" in r.json()["detail"]


def test_route_abstains_when_coverage_threshold_high(client: TestClient):
    d = client.post("/api/route",
                    json={"query": "完全无关的运维问题内容", "min_coverage": 0.99}).json()
    assert d["abstained"] is True
    assert d["candidates"] == []
    assert d["top_coverage"] < 0.99


def test_route_phase_prior(client: TestClient):
    d = client.post("/api/route",
                    json={"query": "横向 提权", "state_phase": "post",
                          "phase_bonus": 1.0}).json()
    assert d["candidates"][0]["name"] == "post-exploitation-lateral"


# --------------------------------------------------------------------- expansion


def test_route_expansion_endpoint(client: TestClient):
    d = client.get("/api/route/expansion", params={"q": "帮我测水平越权"}).json()
    assert d["expanded"] is True
    assert "idor" in d["retrieval_query"]


def test_lexicon_stats_and_expand(client: TestClient):
    d = client.get("/api/lexicon/stats").json()
    assert d["total_zh_keys"] > 0
    d2 = client.post("/api/lexicon/expand", json={"query": "文件上传绕过"}).json()
    assert d2["expansion"]
    assert d2["retrieval_query"].startswith("文件上传绕过")


# --------------------------------------------------------------------- bench


def test_bench_info_404_when_missing(client: TestClient):
    """基准文件不在默认位置时应返回 404 而非 500。"""
    r = client.get("/api/bench/info")
    assert r.status_code in (200, 404)
    if r.status_code == 404:
        assert "不存在" in r.json()["detail"]


def test_bench_run_with_temp_bench(corpus: Path, tmp_path: Path):
    bench = tmp_path / "b.jsonl"
    rows = [
        {"id": "a", "query": "测试水平越权", "expected": ["idor-broken-object-authorization"],
         "lang": "zh", "source": "hand", "confidence": "high"},
        {"id": "z", "query": "zzzqqq vvv", "expected": [], "lang": "en",
         "source": "hand", "confidence": "high", "notes": "弃权用例"},
    ]
    bench.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                     encoding="utf-8")

    app = create_app(Settings(skill_roots=[("t", corpus)], lexicon_path=None))
    with TestClient(app) as c:
        r = c.post("/api/bench/run", json={"bench_path": str(bench), "top_k": 3})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] == 2
        assert d["scored"] == 1
        assert d["abstention_total"] == 1
        assert d["recall@3"] == 1.0
        assert "failures" in d and "false_routes" in d


def test_bench_run_rejects_missing_file(client: TestClient):
    r = client.post("/api/bench/run", json={"bench_path": "Z:/nope.jsonl"})
    assert r.status_code == 404


# --------------------------------------------------------------------- agent


def test_agent_lab_info(client: TestClient):
    r = client.get("/api/agent/lab")
    if r.status_code == 404:
        pytest.skip("实验靶场不存在")
    d = r.json()
    assert d["target_host"] == "lab.local"
    assert d["skill_count"] >= 5
    assert set(d["skills"]) == set(d["plans"]), "靶场技能与执行计划必须一一对应"
    assert "GET /api/orders/{id}" in d["planted"]


def test_agent_run_end_to_end(client: TestClient):
    if client.get("/api/agent/lab").status_code == 404:
        pytest.skip("实验靶场不存在")
    r = client.post("/api/agent/run",
                    json={"query": "端点枚举，然后测试水平越权和后台访问控制绕过",
                          "max_steps": 10, "top_k": 5})
    assert r.status_code == 200
    d = r.json()
    assert d["summary"]["steps"] >= 1
    kinds = {f["kind"] for f in d["graph"]["findings"]}
    assert "bola" in kinds, f"应验证出水平越权，实际 {kinds}"
    # 每个经验证的发现都要有证据链
    for f in d["graph"]["findings"]:
        assert f["verified"] is True
        assert f["evidence"], "经验证的发现必须带证据"
    # 每个执行步都要有验证结果留痕
    for s in d["trace"]["steps"]:
        if s["outcome"] == "executed":
            assert s["actions"] and s["verify"]
    assert "contribution" in d["trace"]


def test_agent_run_rejects_false_positive(client: TestClient):
    if client.get("/api/agent/lab").status_code == 404:
        pytest.skip("实验靶场不存在")
    d = client.post("/api/agent/run",
                    json={"query": "测试搜索框的 SQL 注入", "max_steps": 12,
                          "top_k": 6}).json()
    verified = {f["kind"] for f in d["graph"]["findings"]}
    assert "sql-injection" not in verified, "判据未通过不得成为发现"


def test_agent_run_scope_block_and_circuit_breaker(client: TestClient):
    """把授权主机填错 → 全部请求被拦截，且越界熔断会中止任务。"""
    if client.get("/api/agent/lab").status_code == 404:
        pytest.skip("实验靶场不存在")
    d = client.post("/api/agent/run",
                    json={"query": "端点枚举 水平越权 目录遍历 XSS 上传",
                          "max_steps": 20, "top_k": 6,
                          "hosts": ["wrong-host.local"], "max_blocked_calls": 2}).json()
    assert d["summary"]["blocked_calls"] > 0
    assert d["graph"]["findings"] == []
    assert "越界" in d["summary"]["terminated_reason"]
    assert d["summary"]["steps"] < 6, "不应把所有候选技能都试完"


def test_agent_run_rejects_unknown_field(client: TestClient):
    assert client.post("/api/agent/run",
                       json={"query": "x", "nonsense": 1}).status_code == 422


def test_agent_contribution_endpoint(client: TestClient):
    if client.get("/api/agent/lab").status_code == 404:
        pytest.skip("实验靶场不存在")
    d = client.get("/api/agent/contribution",
                   params={"q": "端点枚举 水平越权", "top_k": 5}).json()
    assert d["contribution"], "应产出贡献度统计"
    for name, a in d["contribution"].items():
        assert "hit_rate" in a and "executed" in a
    assert "terminated_reason" in d


# --------------------------------------------------------------------- 失败路径


def test_endpoints_return_503_when_corpus_missing(tmp_path: Path):
    """语料不存在时服务仍应启动，但相关接口返回 503 并说明原因。"""
    app = create_app(Settings(skill_roots=[("missing", tmp_path / "nope")],
                              lexicon_path=None))
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"] == "loading"
        assert c.get("/api/skills/stats").status_code == 503
        assert c.post("/api/route", json={"query": "x"}).status_code == 503
