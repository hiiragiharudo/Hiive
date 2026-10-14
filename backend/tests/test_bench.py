"""SkillRoute-Bench 评测基础设施的测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval.bench import (
    BenchItem,
    BenchMetrics,
    breakdown_by,
    load_bench,
    run_bench,
    save_bench,
)
from app.skills.bm25 import BM25Index
from app.skills.registry import SkillRegistry
from app.skills.router import RouterConfig, SkillRouter
from app.skills.tokenize import tokenize

# --------------------------------------------------------------------- 数据结构


def test_bench_item_validates_enums():
    with pytest.raises(ValueError, match="lang"):
        BenchItem(id="x", query="q", lang="jp")
    with pytest.raises(ValueError, match="source"):
        BenchItem(id="x", query="q", source="guessed")
    with pytest.raises(ValueError, match="confidence"):
        BenchItem(id="x", query="q", confidence="sure")


def test_empty_expected_means_abstention_case():
    assert BenchItem(id="a", query="写个 PPT").is_abstention
    assert not BenchItem(id="b", query="测 SQL 注入", expected=["sqli"]).is_abstention


def test_bench_item_roundtrip():
    it = BenchItem(id="x", query="q", expected=["a"], acceptable=["b"],
                   lang="en", domains=["web"], source="hand",
                   confidence="medium", notes="n")
    assert BenchItem.from_dict(it.to_dict()) == it


# --------------------------------------------------------------------- 读写


def test_load_and_save_roundtrip(tmp_path: Path):
    items = [
        BenchItem(id="a", query="查 SQL 注入", expected=["sqli-sql-injection"]),
        BenchItem(id="b", query="写个 PPT"),
    ]
    p = tmp_path / "b.jsonl"
    save_bench(items, p)
    assert load_bench(p) == items


def test_load_bench_tolerates_blank_and_comment_lines(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    p.write_text(
        "# 这是注释\n\n"
        + json.dumps({"id": "a", "query": "q", "expected": ["x"]}, ensure_ascii=False)
        + "\n\n",
        encoding="utf-8",
    )
    items = load_bench(p)
    assert len(items) == 1
    assert items[0].id == "a"


def test_load_bench_rejects_duplicate_ids(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    line = json.dumps({"id": "a", "query": "q"})
    p.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="重复的 id"):
        load_bench(p)


def test_load_bench_reports_bad_json_with_line_number(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    p.write_text('{"id": "a", "query": "q"}\n{broken\n', encoding="utf-8")
    with pytest.raises(ValueError, match=":2"):
        load_bench(p)


def test_load_bench_ignores_unknown_fields(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    p.write_text(json.dumps({"id": "a", "query": "q", "future_field": 1}) + "\n",
                 encoding="utf-8")
    assert load_bench(p)[0].id == "a"


def test_shipped_bench_file_is_valid():
    """随仓库发布的基准文件必须可加载且字段合规。"""
    repo = Path(__file__).resolve().parent.parent.parent
    p = repo / "eval" / "bench" / "skillroute-bench-v0.jsonl"
    if not p.exists():
        pytest.skip("基准文件不存在")
    items = load_bench(p)
    assert len(items) >= 50, f"基准至少应有 50 条，实际 {len(items)}"
    assert any(it.is_abstention for it in items), "必须包含弃权用例"
    assert any(it.lang == "en" for it in items), "必须包含英文查询"
    ids = [it.id for it in items]
    assert len(ids) == len(set(ids))
    for it in items:
        assert it.query.strip(), f"{it.id} 查询为空"
        if it.is_abstention:
            assert it.notes, f"弃权用例 {it.id} 必须写明理由"


# --------------------------------------------------------------------- 覆盖率信号


def test_weighted_coverage_full_and_zero():
    idx = BM25Index()
    idx.add("d1", tokenize("水平越权 对象标识 替换"))
    idx.finalize()
    assert idx.weighted_coverage("d1", tokenize("水平越权")) == pytest.approx(1.0)
    assert idx.weighted_coverage("d1", tokenize("完全无关词汇")) == 0.0


def test_weighted_coverage_is_between_zero_and_one():
    idx = BM25Index()
    idx.add("d1", tokenize("水平越权 对象标识"))
    idx.add("d2", tokenize("SQL 注入 报错"))
    idx.finalize()
    c = idx.weighted_coverage("d1", tokenize("水平越权 SQL"))
    assert 0.0 < c < 1.0


def test_weighted_coverage_empty_query():
    idx = BM25Index()
    idx.add("d1", tokenize("abc"))
    idx.finalize()
    assert idx.weighted_coverage("d1", []) == 0.0


# --------------------------------------------------------------------- 评测运行


SKILLS = {
    "sqli": "---\nname: sqli-sql-injection\ndescription: SQL 注入测试\n---\n报错注入 布尔盲注\n",
    "idor": "---\nname: idor-broken-object-authorization\ndescription: 水平越权测试\n---\n替换对象标识\n",
    "race": "---\nname: race-condition\ndescription: 竞态条件测试\n---\n并发请求重复提交\n",
}


@pytest.fixture()
def router(tmp_path: Path) -> SkillRouter:
    root = tmp_path / "s"
    for sub, content in SKILLS.items():
        d = root / sub
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
    reg = SkillRegistry()
    reg.load_roots([("t", root)])
    reg.build_index(vector_kind="tfidf")
    return SkillRouter(reg, RouterConfig(top_k=2, recall_n=10))


def test_run_bench_computes_recall_and_mrr(router: SkillRouter):
    items = [
        BenchItem(id="a", query="SQL 注入 报错", expected=["sqli-sql-injection"]),
        BenchItem(id="b", query="水平越权 对象标识",
                  expected=["idor-broken-object-authorization"]),
    ]
    m = run_bench(router, items)
    assert m.scored == 2
    assert m.recall_at_1 == 2
    assert m.mrr == pytest.approx(1.0)


def test_run_bench_counts_abstention(router: SkillRouter):
    """纯 ASCII 无意义查询两通道均无命中 → 正确弃权。"""
    items = [
        BenchItem(id="a", query="SQL 注入", expected=["sqli-sql-injection"]),
        BenchItem(id="z", query="zzzqqq wwwvvv yyy"),
    ]
    m = run_bench(router, items)
    assert m.abstention_total == 1
    assert m.abstention_correct == 1
    assert m.abstention_accuracy == pytest.approx(1.0)


def test_run_bench_detects_false_route(router: SkillRouter):
    """含中文的无关查询会因 bigram 偶然重叠而被误路由 → 误路由被计入。"""
    items = [BenchItem(id="z", query="测试水平越权的内容")]
    m = run_bench(router, items)
    assert m.abstention_total == 1
    assert m.false_route_rate == pytest.approx(1.0)


def test_run_bench_abstains_when_coverage_below_threshold(tmp_path: Path):
    """阈值高于实际覆盖率时应弃权。

    注意：查询必须**不是全覆盖**——若查询词元全部出现在技能中，覆盖率为 1.0，
    任何 ≤1.0 的阈值都不会触发弃权。这里混入一个语料中不存在的词元，
    使覆盖率低于 1.0。
    """
    root = tmp_path / "s"
    for sub, content in SKILLS.items():
        d = root / sub
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
    reg = SkillRegistry()
    reg.load_roots([("t", root)])
    reg.build_index(vector_kind="tfidf")

    query = "SQL 完全不存在的词元组合"
    probe = SkillRouter(reg, RouterConfig(top_k=2, recall_n=10))
    cov = probe.route(query).top_coverage
    assert 0.0 < cov < 1.0, f"前置条件：覆盖率应介于 0 与 1 之间，实际 {cov}"

    router = SkillRouter(reg, RouterConfig(top_k=2, recall_n=10, min_coverage=cov + 0.01))
    res = router.route(query)
    assert res.abstained, "阈值高于覆盖率时应弃权"
    assert res.candidates == []

    # 阈值低于覆盖率时不应弃权
    router2 = SkillRouter(reg, RouterConfig(top_k=2, recall_n=10, min_coverage=cov - 0.01))
    assert not router2.route(query).abstained


def test_run_bench_separates_recall_and_ranking_failures(router: SkillRouter):
    """阶段一名次要被记录，以区分召回失败与排序失败。"""
    items = [BenchItem(id="a", query="SQL 注入 报错", expected=["sqli-sql-injection"])]
    m = run_bench(router, items)
    r = m.results[0]
    assert r.stage1_rank >= 1
    assert r.hit_rank >= 1


# --------------------------------------------------------------------- 分层与汇总


def test_metrics_to_dict_and_summary(router: SkillRouter):
    items = [BenchItem(id="a", query="SQL 注入", expected=["sqli-sql-injection"])]
    m = run_bench(router, items, name="t")
    d = m.to_dict()
    assert d["total"] == 1 and d["scored"] == 1
    assert "R@1" in m.summary()


def test_breakdown_by_language(router: SkillRouter):
    items = [
        BenchItem(id="a", query="SQL 注入", expected=["sqli-sql-injection"], lang="zh"),
        BenchItem(id="b", query="error based SQL injection",
                  expected=["sqli-sql-injection"], lang="en"),
    ]
    m = run_bench(router, items)
    groups = breakdown_by(m.results, "lang")
    assert set(groups) == {"zh", "en"}
    assert groups["en"].recall_at_1 == 1


def test_breakdown_by_source_isolates_circularity(router: SkillRouter):
    """按 source 分层是控制循环性风险的手段，必须可用。"""
    items = [
        BenchItem(id="a", query="SQL 注入", expected=["sqli-sql-injection"],
                  source="hand"),
        BenchItem(id="b", query="报错注入", expected=["sqli-sql-injection"],
                  source="body-derived"),
    ]
    m = run_bench(router, items)
    groups = breakdown_by(m.results, "source")
    assert set(groups) == {"hand", "body-derived"}


def test_metrics_mrr_uses_full_stage1_ranking(router: SkillRouter):
    """MRR 基于阶段一完整排序，因此 k 截断不影响它。"""
    items = [BenchItem(id="a", query="SQL 注入 报错", expected=["sqli-sql-injection"])]
    m_k1 = run_bench(router, items, top_k=1)
    m_k2 = run_bench(router, items, top_k=2)
    assert m_k1.mrr == pytest.approx(m_k2.mrr)
