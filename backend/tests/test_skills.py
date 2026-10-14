"""技能引擎单元测试。

运行：``.venv/Scripts/python -m pytest backend/tests -q``
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.skills.bm25 import BM25Index
from app.skills.fusion import rrf_fuse
from app.skills.parser import (
    SkillParseError,
    parse_frontmatter,
    parse_skill_file,
    validate_meta,
)
from app.skills.models import SkillMeta
from app.skills.registry import SkillRegistry
from app.skills.router import RouterConfig, SkillRouter
from app.skills.tokenize import tokenize

# --------------------------------------------------------------------- 分词


def test_tokenize_cjk_bigram_and_ascii():
    toks = tokenize("水平越权 IDOR 测试")
    assert "idor" in toks
    # CJK 单字
    assert "越" in toks and "权" in toks
    # CJK 二元组
    assert "越权" in toks
    assert "水平" in toks


def test_tokenize_lowercases_and_keeps_tech_symbols():
    toks = tokenize("C++ C# .NET node.js SQLi")
    assert "c++" in toks
    assert "c#" in toks
    assert "node.js" in toks
    assert "sqli" in toks
    # 前导点不是词首字符，故 ".NET" 的 token 是 "net"
    assert "net" in toks


def test_tokenize_empty():
    assert tokenize("") == []


# --------------------------------------------------------------------- BM25


def test_bm25_ranks_matching_doc_first():
    idx = BM25Index()
    idx.add("idor", tokenize("水平越权 对象标识 越权访问"))
    idx.add("sqli", tokenize("SQL 注入 报错注入"))
    idx.finalize()
    hits = idx.search(tokenize("越权"), top_n=5)
    assert hits, "应至少命中一个文档"
    assert hits[0][0] == "idor"


def test_bm25_returns_empty_for_unmatched_query():
    idx = BM25Index()
    idx.add("a", tokenize("越权"))
    idx.finalize()
    assert idx.search(tokenize("完全不相干的词汇组合")) == []


def test_bm25_duplicate_doc_id_rejected():
    idx = BM25Index()
    idx.add("a", ["x"])
    with pytest.raises(ValueError):
        idx.add("a", ["y"])


def test_bm25_term_hits_sorted_by_idf():
    idx = BM25Index()
    idx.add("a", tokenize("越权 越权 越权 常见词"))
    idx.add("b", tokenize("常见词 另一个"))
    idx.finalize()
    hits = idx.term_hits("a", tokenize("越权 常见词"))
    assert set(hits) == {"越", "权", "越权", "常", "见", "词", "常见", "见词"}
    # 「越/权/越权」只出现在 a 中（df=1），IDF 高于两文档共有的「常/见/词/常见/见词」
    # 故前三名必为 df=1 的那组（组内按字符序稳定平局）
    assert set(hits[:3]) == {"越", "权", "越权"}
    assert set(hits[3:]) == {"常", "见", "词", "常见", "见词"}


# --------------------------------------------------------------------- RRF


def test_rrf_fuses_ranks():
    fused = rrf_fuse(
        {
            "bm25": [("a", 9.0), ("b", 5.0)],
            "vector": [("b", 0.9), ("a", 0.8)],
        },
        k=60,
    )
    scores = {f.doc_id: f.rrf_score for f in fused}
    # 两通道都排第一的文档不该吃亏：a 与 b 名次互换，得分相同
    assert scores["a"] == pytest.approx(scores["b"])
    assert fused[0].channel_ranks  # 记录了通道名次


def test_rrf_weights_can_disable_channel():
    fused = rrf_fuse(
        {"bm25": [("a", 1.0)], "vector": [("b", 1.0)]},
        weights={"bm25": 1.0, "vector": 0.0},
    )
    assert [f.doc_id for f in fused] == ["a"]


# --------------------------------------------------------------------- 解析


def test_parse_frontmatter_block_scalar_folded():
    fm = parse_frontmatter("name: x\ndescription: >-\n  第一行\n  第二行\n")
    assert fm["description"] == "第一行 第二行"


def test_parse_frontmatter_block_scalar_literal():
    fm = parse_frontmatter("name: x\ndescription: |-\n  第一行\n  第二行\n")
    assert fm["description"] == "第一行\n第二行"


def test_parse_frontmatter_inline_list():
    fm = parse_frontmatter("domains: [web, api, ad]\n")
    assert fm["domains"] == ["web", "api", "ad"]


def test_parse_frontmatter_dash_list():
    fm = parse_frontmatter("triggers:\n  - 接口收集\n  - API 侦察\nphase: recon\n")
    assert fm["triggers"] == ["接口收集", "API 侦察"]
    assert fm["phase"] == "recon"


def test_parse_frontmatter_rejects_line_without_colon():
    with pytest.raises(SkillParseError):
        parse_frontmatter("this line has no colon\n")


def test_parse_skill_file_requires_name(tmp_path: Path):
    p = tmp_path / "SKILL.md"
    p.write_text("---\ndescription: 缺 name\n---\n正文\n", encoding="utf-8")
    with pytest.raises(SkillParseError, match="name"):
        parse_skill_file(p)


def test_parse_skill_file_requires_frontmatter(tmp_path: Path):
    p = tmp_path / "SKILL.md"
    p.write_text("没有 frontmatter 的正文\n", encoding="utf-8")
    with pytest.raises(SkillParseError, match="frontmatter"):
        parse_skill_file(p)


def test_validate_meta_flags_missing_description_and_bad_phase():
    problems = validate_meta(SkillMeta(name="x", phase="nope", risk="extreme"))
    assert any("description" in p for p in problems)
    assert any("phase" in p for p in problems)
    assert any("risk" in p for p in problems)


# --------------------------------------------------------------------- 语料夹具


SKILL_A = """---
name: idor-hunt
description: >-
  测试水平越权（IDOR）时调用该技能：替换对象标识，比较不同主体返回的数据归属。
domains: [web, api]
phase: discovery
targets: [rest, graphql]
triggers:
  - 越权
  - 对象标识
  - 换 id
requires: []
provides: [finding]
tools: [burp]
risk: low
---

# 水平越权测试

替换请求中的对象标识，比较两个不同主体账号的响应。
"""

SKILL_B = """---
name: sqli-probe
description: SQL 注入探测：在存在差分面的参数上投放探针，依据报错与布尔差异判定。
domains: [web]
phase: discovery
triggers: [注入, sql]
tools: [sqlmap]
risk: low
---

# SQL 注入探测

按栈选择探针，不要对每个 path 无差别投放。
"""

SKILL_C = """---
name: recon-subdomain
description: 子域名收集与资产测绘，铺开攻击面。
domains: [recon]
phase: recon
triggers: [子域名, 资产, 测绘]
risk: low
---

# 子域名收集

使用证书透明度日志与字典爆破。
"""

SKILL_D = """---
name: post-cred-dump
description: 获取凭据后的横向移动与提权准备。
domains: [ad]
phase: post
requires: [recon-subdomain]
triggers: [横向, 提权, 凭据]
risk: high
---

# 凭据利用

注意：高风险操作需人工审批。
"""


@pytest.fixture()
def corpus_dir(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    for fname, content in (
        ("idor-hunt", SKILL_A),
        ("sqli-probe", SKILL_B),
        ("recon-subdomain", SKILL_C),
        ("post-cred-dump", SKILL_D),
    ):
        d = root / fname
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
    return root


@pytest.fixture()
def registry(corpus_dir: Path) -> SkillRegistry:
    reg = SkillRegistry()
    reg.load_roots([("test", corpus_dir)])
    reg.build_index(tokenizer="hybrid", vector_kind="lsa", n_components=3)
    return reg


# --------------------------------------------------------------------- 注册表


def test_registry_loads_all_skills(registry: SkillRegistry):
    assert len(registry) == 4
    assert registry.report.ok, registry.report.to_dict()
    assert "idor-hunt" in registry
    assert registry.get("idor-hunt").meta.phase == "discovery"


def test_registry_stats(registry: SkillRegistry):
    st = registry.stats()
    assert st["total"] == 4
    assert st["by_phase"]["discovery"] == 2
    assert st["baseline_meta_tokens"] > 0
    assert st["full_injection_tokens"] > st["baseline_meta_tokens"]


def test_registry_records_duplicate_names(tmp_path: Path, corpus_dir: Path):
    dup = tmp_path / "dup" / "idor-hunt"
    dup.mkdir(parents=True)
    (dup / "SKILL.md").write_text(SKILL_A, encoding="utf-8")
    reg = SkillRegistry()
    rep = reg.load_roots([("test", corpus_dir), ("dup", tmp_path / "dup")])
    assert rep.duplicates, "同名技能应被记录而非静默覆盖"
    assert len(reg) == 4


def test_registry_dependency_validation(registry: SkillRegistry):
    router = SkillRouter(registry)
    assert router.validate_dependencies() == {}


# --------------------------------------------------------------------- 路由器


def test_router_returns_top_k_with_reasons(registry: SkillRegistry):
    router = SkillRouter(registry, RouterConfig(top_k=2, recall_n=10))
    res = router.route("我要测试这个接口的水平越权，换一下对象 id")
    assert len(res.candidates) <= 2
    assert res.candidates, "应召回技能"
    assert res.candidates[0].skill.name == "idor-hunt"
    assert res.candidates[0].reason
    assert res.candidates[0].matched_fields


def test_router_saves_context_tokens(registry: SkillRegistry):
    router = SkillRouter(registry, RouterConfig(top_k=1, recall_n=10))
    res = router.route("子域名收集")
    assert res.candidates
    # 元数据项：基线 N×meta vs 本方案 k×meta
    assert res.baseline_meta_tokens == registry.baseline_tokens()
    assert res.injected_meta_tokens < res.baseline_meta_tokens
    assert res.meta_saving_ratio > 0.0
    # 总开销：正文项两方案相同，故总开销必然更低
    assert res.injected_tokens < res.baseline_tokens
    assert res.baseline_tokens == res.baseline_meta_tokens + res.body_tokens
    assert res.injected_tokens == res.injected_meta_tokens + res.body_tokens


def test_cost_model_saving_equals_library_minus_k(registry: SkillRegistry):
    """节省量应恰为 (N − k) × meta（同等 k 假设）。"""
    router = SkillRouter(registry, RouterConfig(top_k=2, recall_n=10))
    res = router.route("越权 注入")
    n = res.library_size
    k = len(res.candidates)
    assert 0 < k <= 2
    saved = res.baseline_tokens - res.injected_tokens
    assert saved == res.baseline_meta_tokens - res.injected_meta_tokens
    # 平均 meta 一致时，节省量 ≈ (N-k)×meta
    avg_meta = res.injected_meta_tokens / k
    assert abs(saved - (n - k) * avg_meta) <= avg_meta * k


def test_router_phase_prior_promotes_matching_phase(registry: SkillRegistry):
    router = SkillRouter(
        registry,
        RouterConfig(top_k=3, recall_n=10, use_phase_prior=True, phase_bonus=1.0),
    )
    res = router.route("凭据 横向 提权", state_phase="post")
    assert res.candidates[0].skill.meta.phase == "post"


def test_router_empty_result_on_irrelevant_query(registry: SkillRegistry):
    """纯 ASCII 无意义查询：BM25 与向量通道均无命中，应返回空结果。

    注意：含中文的"无关"查询**不会**返回空——字符 bigram 会在词面上产生
    偶然重叠（如「内容」命中技能描述）。这是词面检索的固有特性，不是缺陷；
    真正的路由质量要靠 SkillRoute-Bench 的标注真值来度量。
    """
    router = SkillRouter(registry, RouterConfig(top_k=3, recall_n=10))
    res = router.route("zzzzqqqq wwwwvbbb")
    assert res.candidates == []
    assert res.token_saving_ratio == 0.0
    assert res.meta_saving_ratio == 0.0


def test_router_rejects_top_k_above_recall_n(registry: SkillRegistry):
    with pytest.raises(ValueError, match="recall_n"):
        SkillRouter(registry, RouterConfig(top_k=10, recall_n=3))


def test_router_rejects_unknown_channel(registry: SkillRegistry):
    with pytest.raises(ValueError, match="未知检索通道"):
        SkillRouter(registry, RouterConfig(channels=("bm25", "nonsense")))


def test_router_dependency_closure_orders_dependencies(registry: SkillRegistry):
    router = SkillRouter(registry)
    ordered, cycles = router.dependency_closure(["post-cred-dump"])
    assert cycles == []
    assert ordered.index("recon-subdomain") < ordered.index("post-cred-dump")


def test_router_detects_dependency_cycle(tmp_path: Path):
    root = tmp_path / "cyc"
    for a, b in (("x", "y"), ("y", "x")):
        d = root / a
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {a}\ndescription: {a}\nrequires: [{b}]\n---\n正文\n",
            encoding="utf-8",
        )
    reg = SkillRegistry()
    reg.load_roots([("cyc", root)])
    reg.build_index(vector_kind="tfidf")
    router = SkillRouter(reg)
    _, cycles = router.dependency_closure(["x"])
    assert cycles, "应检测到循环依赖"


# --------------------------------------------------------------------- 真实语料


REAL_CORPUS = Path(os.path.expanduser("~")) / ".dsh" / "skills"


@pytest.mark.skipif(not REAL_CORPUS.exists(), reason="本机技能语料不存在")
def test_real_corpus_loads_and_routes():
    """端到端：加载本机真实技能语料并路由。

    注意断言的是 **meta_saving_ratio**（元数据项节省）而非总开销节省——
    真实技能正文长达数百行，k 个正文的开销本身就远超全库元数据，
    因此"总 token 一定更少"是错误命题（见 RouteResult 成本模型文档）。
    """
    reg = SkillRegistry()
    rep = reg.load_roots([("dsh", REAL_CORPUS)])
    assert rep.loaded >= 100, f"真实语料应加载 100+ 技能，实际 {rep.loaded}"
    reg.build_index(tokenizer="hybrid", vector_kind="lsa", n_components=64)

    router = SkillRouter(reg, RouterConfig(top_k=5, recall_n=30))
    res = router.route("目标是一个 WordPress 站点，我要找管理员登录入口")
    assert res.candidates, "真实语料上应召回技能"

    # 核心指标：随技能库规模线性增长的元数据项被大幅压缩
    assert res.meta_saving_ratio > 0.9, f"元数据节省不足: {res.meta_saving_ratio}"
    assert res.meta_saving_ratio > res.token_saving_ratio

    print(
        f"\n[真实语料] 技能库 N={res.library_size}"
        f"\n  基线  元数据 {res.baseline_meta_tokens:>7} + 正文 {res.body_tokens:>7}"
        f" = {res.baseline_tokens:>7} token"
        f"\n  本方案 元数据 {res.injected_meta_tokens:>7} + 正文 {res.body_tokens:>7}"
        f" = {res.injected_tokens:>7} token"
        f"\n  元数据项节省 {res.meta_saving_ratio:.1%}"
        f" | 总开销节省 {res.token_saving_ratio:.1%}"
    )
    for c in res.candidates:
        print(f"  - {c.skill.name:34} rrf={c.score:.5f}  {c.reason}")
