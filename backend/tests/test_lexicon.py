"""双语词典与跨语言路由的单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.skills.lexicon import (
    CURATED,
    MINED_TRUSTED_EXTRA,
    BilingualLexicon,
    _mined_acceptable,
)
from app.skills.registry import SkillRegistry
from app.skills.router import RouterConfig, SkillRouter

# --------------------------------------------------------------------- 词典构建


def test_curated_lexicon_is_bidirectional():
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    assert "水平越权" in lex.zh_to_en
    assert "idor" in lex.zh_to_en["水平越权"]
    # 反向表
    assert "水平越权" in lex.en_to_zh["idor"]


def test_curated_lexicon_covers_core_vuln_classes():
    """核心漏洞类型必须有中文键，否则中文查询无从扩展。"""
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    for term in ("水平越权", "垂直越权", "注入", "跨站脚本", "服务端请求伪造",
                 "文件上传", "反序列化", "命令执行", "子域名", "容器"):
        assert term in lex.zh_to_en, f"核心词典缺少 {term}"
        assert lex.zh_to_en[term], f"{term} 的英文等价词为空"


# --------------------------------------------------------------------- 查询扩展


def test_expand_query_appends_english():
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    expanded, matched = lex.expand_query("帮我测试水平越权")
    assert matched
    assert "水平越权" in [zh for zh, _ in matched]
    assert "idor" in expanded
    assert expanded.startswith("帮我测试水平越权"), "原查询必须保留在前"


def test_expand_query_uses_longest_match_first():
    """`水平越权` 命中后不应再追加 `越权` 的英文，避免同一概念重复加权。"""
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    _expanded, matched = lex.expand_query("测试水平越权")
    zhs = [zh for zh, _ in matched]
    assert "水平越权" in zhs
    assert "越权" not in zhs


def test_expand_query_no_match_returns_original():
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    q = "zzzz qqqq 无术语内容"
    expanded, matched = lex.expand_query(q)
    assert expanded == q
    assert matched == []


def test_expand_query_keeps_original_before_expansion():
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    expanded, _ = lex.expand_query("文件上传绕过")
    assert expanded.startswith("文件上传绕过")


# --------------------------------------------------------------------- 索引侧富化


def test_zh_triggers_for_reverse_lookup():
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    zh = lex.zh_triggers_for("Playbook for BOLA and IDOR testing on APIs")
    assert "水平越权" in zh


def test_zh_triggers_for_empty_on_unrelated_text():
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    assert lex.zh_triggers_for("nothing relevant here zzzz") == []


def test_enrichment_uses_word_boundary_not_substring(tmp_path: Path):
    """回归测试：英文键 `id` 不得命中 `identifier` / `provide` 中的子串。

    实测踩坑：子串匹配会让「不限字段名」这类挖掘噪声被富化到大批技能上。
    """
    mined = tmp_path / "lex.json"
    mined.write_text(
        json.dumps(
            {"pairs": [{"zh": "字段标识", "en": "id", "count": 9}]}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    lex = BilingualLexicon.build(mined_path=mined, include_mined=True, mined_min_count=4)
    assert "字段标识" in lex.zh_to_en, "前置条件：该挖掘对应被接受"

    # 子串出现（identifier / provide）不应命中
    assert "字段标识" not in lex.zh_triggers_for("the identifier provide middleware")
    # 独立词出现应命中
    assert "字段标识" in lex.zh_triggers_for("pass the object id parameter")


def test_enrichment_handles_multiword_phrase(tmp_path: Path):
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    # curated: 水平越权 -> bola / idor / broken object level authorization
    zh = lex.zh_triggers_for("testing broken object level authorization")
    assert "水平越权" in zh
    # 部分词不应命中
    assert "水平越权" not in lex.zh_triggers_for("object level only")


# --------------------------------------------------------------------- 挖掘过滤


@pytest.mark.parametrize(
    "zh,en",
    [
        ("这个就不截图了", "xss"),          # 句子片段（含功能词「就」）
        ("已修复", "login"),                # 报告模板状态词
        ("待补", "ai-app-agent-cot-2.md"),  # 占位符 + 文件名
        ("多看临时目录", "tmp/temp"),        # 命令 + 路径
        ("某某系统", "xxxxx"),               # 占位符
    ],
)
def test_mined_filter_rejects_observed_noise(zh: str, en: str):
    """这些是真实挖掘结果中出现的噪声，必须被过滤器拒绝。"""
    assert not _mined_acceptable(zh, en), f"应拒绝噪声对 {zh} <-> {en}"


@pytest.mark.parametrize(
    "zh,en",
    [
        ("水平越权", "idor"),
        ("带外回连", "oob"),
        ("命令执行", "rce"),
        ("存储型", "xss"),
    ],
)
def test_mined_filter_accepts_real_terms(zh: str, en: str):
    assert _mined_acceptable(zh, en), f"应接受真实术语对 {zh} <-> {en}"


def test_mined_layer_respects_min_count(tmp_path: Path):
    mined = tmp_path / "lex.json"
    mined.write_text(
        json.dumps(
            {
                "pairs": [
                    {"zh": "凭证伪造", "en": "credential forgery", "count": 9},
                    {"zh": "低频噪声词", "en": "lowfreq", "count": 2},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    lex = BilingualLexicon.build(mined_path=mined, include_mined=True, mined_min_count=4)
    assert "凭证伪造" in lex.zh_to_en
    assert "低频噪声词" not in lex.zh_to_en
    assert lex.stats.mined_pairs == 1


def test_include_mined_false_skips_mining(tmp_path: Path):
    mined = tmp_path / "lex.json"
    mined.write_text(
        json.dumps({"pairs": [{"zh": "凭证伪造", "en": "credential forgery", "count": 9}]},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    lex = BilingualLexicon.build(mined_path=mined, include_mined=False)
    assert "凭证伪造" not in lex.zh_to_en
    assert lex.stats.mined_pairs == 0
    assert lex.stats.loaded_mined is False


def test_curated_and_trusted_extra_are_disjoint():
    """人工复核补充项不应与核心词典重复，避免统计口径重复计数。"""
    assert not (set(CURATED) & set(MINED_TRUSTED_EXTRA))


# --------------------------------------------------------------------- 与引擎集成

SKILL_EN = """---
name: bola-testing-en
description: >-
  API object level authorization testing playbook. Use when APIs expose object
  identifiers and you need to test broken object level authorization.
---

# BOLA

Replace the object identifier and compare responses.
"""

SKILL_ZH = """---
name: 中文技能
description: 一个中文描述的技能，用于对照。
---

# 中文技能
"""


@pytest.fixture()
def reg_with_lexicon(tmp_path: Path, request) -> SkillRegistry:
    root = tmp_path / "skills"
    for fname, content in (("a", SKILL_EN), ("b", SKILL_ZH)):
        d = root / fname
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")

    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    reg = SkillRegistry()
    reg.load_roots([("t", root)])
    reg.attach_lexicon(lex, enrich_triggers=True)
    reg.build_index(vector_kind="lsa", n_components=2)
    return reg


def test_registry_enrichment_adds_zh_triggers(reg_with_lexicon: SkillRegistry):
    extra = reg_with_lexicon.enriched_triggers("bola-testing-en")
    assert extra, "英文描述技能应被补入中文触发词"
    assert "水平越权" in extra
    assert reg_with_lexicon.enrichment_stats["enriched"] >= 1


def test_registry_enrichment_can_be_disabled(tmp_path: Path):
    root = tmp_path / "skills"
    d = root / "a"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(SKILL_EN, encoding="utf-8")
    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    reg = SkillRegistry()
    reg.load_roots([("t", root)])
    reg.attach_lexicon(lex, enrich_triggers=False)
    reg.build_index(vector_kind="tfidf")
    assert reg.enriched_triggers("bola-testing-en") == []
    assert reg.enrichment_stats["enriched"] == 0


def test_chinese_query_reaches_english_skill(reg_with_lexicon: SkillRegistry):
    """核心断言：中文查询应能召回到**英文描述**的技能。"""
    router = SkillRouter(
        reg_with_lexicon,
        RouterConfig(top_k=2, recall_n=5, expand_query=True, enrich_triggers=True),
    )
    res = router.route("帮我测一下水平越权")
    names = [c.skill.name for c in res.candidates]
    assert "bola-testing-en" in names, f"中文查询未能召回英文技能，实际: {names}"


def test_router_records_query_expansion(reg_with_lexicon: SkillRegistry):
    router = SkillRouter(
        reg_with_lexicon, RouterConfig(top_k=2, recall_n=5, expand_query=True)
    )
    res = router.route("测试水平越权")
    assert res.query_expansion, "应记录查询扩展命中项"
    assert any(zh == "水平越权" for zh, _en in res.query_expansion)
    assert res.retrieval_query and res.retrieval_query != res.query
    d = res.to_dict()
    assert d["cross_lingual"]["expanded"] is True


def test_router_without_expansion_has_no_expansion_record(reg_with_lexicon: SkillRegistry):
    router = SkillRouter(
        reg_with_lexicon, RouterConfig(top_k=2, recall_n=5, expand_query=False)
    )
    res = router.route("测试水平越权")
    assert res.query_expansion == []
    assert res.to_dict()["cross_lingual"]["expanded"] is False
