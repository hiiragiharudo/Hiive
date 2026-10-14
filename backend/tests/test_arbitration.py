"""技能仲裁表解析与强制执行的测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.rules import CONFLICT_RESOLUTION, RULE_SCOPE, RuleSet
from app.rules.arbitration import (
    ArbitrationTable,
    ForbiddenCombo,
    TopicArbiter,
    _kebab_names,
    _names,
    _parse_table,
    _split_sections,
)

REAL_ARB = (
    Path.home() / ".dsh" / "skills" / "src-6k-skill" / "references"
    / "rules" / "skill-arbitration.md"
)

SAMPLE = """# 技能仲裁表（示例）

## 0. 为什么需要这张表

| 技能 | 自称 |
|---|---|
| `alpha-router` | 「必须触发」 |
| `beta-router` | 「总路由」 |
| `delta-router` | 「强制入口」 |
| `gamma-tool` | 普通能力 |

## 1. 唯一入口（不参与竞争）

```
任何安全任务 → 【必定】先加载 alpha-router
```

## 2. 执行技能路由（按任务类型选，一次最多 1 个）

| 任务类型 | 加载 | 不加载 |
|---|---|---|
| **黑盒测试** | `beta-router` | 其余全部 |
| **具体漏洞怎么打** | `gamma-tool` | — |

## 3. 冲突仲裁（同一议题多技能有说法时，以谁为准）

| 议题 | 仲裁 | 理由 |
|---|---|---|
| **范围判定** | **`alpha-router`** | 唯一权威 |
| **CVE 报告** | **`beta-router`**（`references/report_EN.md`） | 唯一权威 |

## 5. 禁止同时加载的组合（避免路由打架）

| 组合 | 为什么禁 |
|---|---|
| `beta-router` + `gamma-tool` | 双重路由 |
| **任何 3 个以上「总路由」型技能同时加载** | 必然摇摆 |

## 6. 一句话总则

```
范围 → alpha-router
流程 → beta-router
```
"""


@pytest.fixture()
def table(tmp_path: Path) -> ArbitrationTable:
    p = tmp_path / "arb.md"
    p.write_text(SAMPLE, encoding="utf-8")
    return ArbitrationTable.parse(p)


# --------------------------------------------------------------------- 基础解析


def test_split_sections():
    secs = _split_sections(SAMPLE)
    assert any(k.startswith("0.") for k in secs)
    assert any(k.startswith("5.") for k in secs)
    assert "| 技能 | 自称 |" in secs["0. 为什么需要这张表"]


def test_parse_table_skips_header_and_separator():
    rows = _parse_table("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
    assert rows == [["1", "2"], ["3", "4"]]


def test_names_extracts_backticked_and_filters_paths():
    """实测：§3 单元格里混有文件路径，必须过滤掉。"""
    got = _names("**`cve-yu2`**（`references/workflow/reporting/report_generator_EN.md`）")
    assert got == ["cve-yu2"]


def test_kebab_names_prefers_known_list():
    text = "任何安全任务 → 先加载 alpha-router，再看 beta-router"
    assert _kebab_names(text, ["alpha-router"]) == ["alpha-router"]
    assert set(_kebab_names(text)) == {"alpha-router", "beta-router"}


# --------------------------------------------------------------------- 解析结果


def test_parse_entry_from_unbackticked_fence(table: ArbitrationTable):
    """★ 回归：§1 的代码块里技能名没有反引号，须按 kebab-case 提取。

    实测原实现只认反引号，导致唯一入口解析为空。
    """
    assert table.entry == ["alpha-router"]
    assert not table.parse_warnings, table.parse_warnings


def test_parse_umbrella_skills(table: ArbitrationTable):
    """只把"自称"列含标志词的算作总路由型——`gamma-tool` 是普通能力，须排除。

    这条对应真实语料的情形：§0 列了 5 个技能，但原文说只有 4 个自称总路由。
    """
    assert table.umbrella_skills == ["alpha-router", "beta-router", "delta-router"]
    assert "gamma-tool" not in table.umbrella_skills


def test_parse_task_routes(table: ArbitrationTable):
    routes = {r.task_type: r for r in table.task_routes}
    assert any("黑盒测试" in k for k in routes)
    r = next(v for k, v in routes.items() if "黑盒测试" in k)
    assert r.load == ["beta-router"]


def test_parse_topic_arbiters(table: ArbitrationTable):
    topics = {t.topic: t for t in table.topics}
    assert "范围判定" in topics
    assert topics["范围判定"].winners == ["alpha-router"]


def test_parse_forbidden_pairs_and_count_constraint(table: ArbitrationTable):
    pairs = [f for f in table.forbidden if not f.is_count_constraint()]
    counts = [f for f in table.forbidden if f.is_count_constraint()]
    assert len(pairs) == 1 and pairs[0].skills == ["beta-router", "gamma-tool"]
    assert len(counts) == 1
    # "任何 3 个以上" → 上限为 2
    assert counts[0].max_count == 2
    assert table.max_umbrella_skills == 2


def test_parse_motto(table: ArbitrationTable):
    assert "alpha-router" in table.motto


def test_parse_missing_file_is_reported(tmp_path: Path):
    t = ArbitrationTable.parse(tmp_path / "nope.md")
    assert t.parse_warnings and "不存在" in t.parse_warnings[0]
    assert t.entry == []


# --------------------------------------------------------------------- 强制执行


def test_enforce_drops_lower_ranked_of_forbidden_pair(table: ArbitrationTable):
    """禁止组合成对出现时，保留**排名更高**者——不引入新的偏好。"""
    out = table.enforce(["gamma-tool", "beta-router"])
    assert out.kept == ["gamma-tool"], "gamma-tool 排名更高，应保留"
    assert out.dropped and out.dropped[0][0] == "beta-router"
    assert "双重路由" in out.dropped[0][1]

    out2 = table.enforce(["beta-router", "gamma-tool"])
    assert out2.kept == ["beta-router"]
    assert out2.dropped[0][0] == "gamma-tool"


def test_enforce_caps_umbrella_skills(table: ArbitrationTable):
    """3 个总路由型同时出现时，按上限只保留前 2 个（排名优先）。"""
    out = table.enforce(
        ["alpha-router", "beta-router", "delta-router", "gamma-tool"]
    )
    umbrellas_kept = [n for n in out.kept if table.is_umbrella(n)]
    assert len(umbrellas_kept) == 2, f"总路由型应被压到 2 个，实际 {umbrellas_kept}"
    assert "delta-router" in [n for n, _r in out.dropped]
    # gamma-tool 被禁止组合丢弃（与 beta-router 冲突）
    assert "gamma-tool" in [n for n, _r in out.dropped]
    assert any("上限" in r for _n, r in out.dropped)


def test_enforce_forbidden_pair_applies_before_cap(table: ArbitrationTable):
    """执行顺序：先配对消解，再计数上限——两者都记录在 applied 中。"""
    out = table.enforce(["alpha-router", "beta-router", "delta-router", "gamma-tool"])
    assert len(out.applied) == 2, f"应记录两条约束，实际 {out.applied}"
    assert any("禁止组合" in a for a in out.applied)
    assert any("上限" in a for a in out.applied)


def test_enforce_noop_when_no_conflict(table: ArbitrationTable):
    names = ["gamma-tool", "delta-skill"]
    out = table.enforce(names)
    assert out.kept == names
    assert out.dropped == []
    assert out.applied == []


def test_enforce_empty_input(table: ArbitrationTable):
    out = table.enforce([])
    assert out.kept == [] and out.dropped == []


def test_enforce_is_deterministic(table: ArbitrationTable):
    names = ["alpha-router", "beta-router", "gamma-tool"]
    a = table.enforce(list(names))
    b = table.enforce(list(names))
    assert a.kept == b.kept and a.dropped == b.dropped


def test_is_umbrella_helper(table: ArbitrationTable):
    assert table.is_umbrella("alpha-router")
    assert not table.is_umbrella("gamma-tool")


def test_stats_and_to_dict(table: ArbitrationTable):
    s = table.stats()
    assert s["entry"] == ["alpha-router"] and s["forbidden_combos"] == 2
    d = table.to_dict()
    assert "task_routes" in d and "topics" in d and "motto" in d


# --------------------------------------------------------------------- 真实语料


@pytest.mark.skipif(not REAL_ARB.exists(), reason="本机仲裁表不存在")
def test_real_arbitration_table_parses_completely():
    """真实语料必须完整解析——这是本模块存在的理由。"""
    t = ArbitrationTable.parse(REAL_ARB)
    assert t.entry, "应解析出唯一入口"
    assert len(t.umbrella_skills) >= 4, "§0 应解析出 4+ 个自称入口的技能"
    assert len(t.task_routes) >= 8
    assert len(t.topics) >= 10
    assert len(t.forbidden) >= 4
    assert not t.parse_warnings, f"不应有解析告警: {t.parse_warnings}"
    # 入口必须是总路由型之一
    assert set(t.entry) <= set(t.umbrella_skills)


@pytest.mark.skipif(not REAL_ARB.exists(), reason="本机仲裁表不存在")
def test_real_arbitration_resolves_the_measured_problem():
    """★ 核心断言：真实语料上，仲裁必须消解"多个总路由型技能同时被选中"。

    这是本课题实测发现的问题（伞状技能霸榜，见技术设计文档 §6.6），
    而笔者的语料中已有人工撰写的答案；本模块把该答案变成机器可强制的约束。
    """
    t = ArbitrationTable.parse(REAL_ARB)
    # 模拟检索给出的"5 个总路由型技能霸榜"的极端情况
    candidates = ["src-6k-skill", "pent3st", "hack-skills", "aboutsecurity",
                  "vibe-pentest"]
    out = t.enforce(candidates)
    umbrellas_kept = [n for n in out.kept if t.is_umbrella(n)]
    assert len(umbrellas_kept) <= t.max_umbrella_skills
    assert len(out.dropped) >= 3, f"应丢弃至少 3 项，实际 {out.dropped}"
    assert out.applied, "应记录应用的约束"


# --------------------------------------------------------------------- 规则层


def test_rule_scope_has_no_placeholder_entries():
    """RULE_SCOPE 不应残留占位/空摘要条目（初版曾误留一个）。"""
    for name, spec in RULE_SCOPE.items():
        if name.endswith("-dup"):
            pytest.fail(f"RULE_SCOPE 残留占位条目: {name}")
        if name in ("skill-arbitration",):
            continue  # 仲裁表由 arbitration.py 单独处理
        assert spec.get("summary"), f"{name} 缺少 summary"


def test_conflict_resolution_targets_exist_in_scope():
    """冲突裁决的胜出方必须是已知规则（或特殊标记 __rules__）。"""
    for topic, spec in CONFLICT_RESOLUTION.items():
        w = spec["winner"]
        assert w == "__rules__" or w in RULE_SCOPE, f"{topic} 的胜出方 {w} 不在 RULE_SCOPE"


def test_ruleset_loads_and_applicable(tmp_path: Path):
    (tmp_path / "always-rule.md").write_text("# 全局规则\n\n正文\n", encoding="utf-8")
    (tmp_path / "web-rule.md").write_text("# Web 规则\n\n正文\n", encoding="utf-8")
    scope = {
        "always-rule": {"always": True, "summary": "恒适用", "domains": [], "phases": []},
        "web-rule": {"always": False, "summary": "仅 Web", "domains": ["web"], "phases": []},
    }
    rs = RuleSet.load(tmp_path, scope=scope)
    assert set(rs.rules) == {"always-rule", "web-rule"}
    got = {r.name for r in rs.applicable(domains=["web"], phase="recon")}
    assert got == {"always-rule", "web-rule"}
    got2 = {r.name for r in rs.applicable(domains=["ad"], phase="post")}
    assert got2 == {"always-rule"}


def test_ruleset_headers_are_compact(tmp_path: Path):
    """规则全文不可常驻上下文——headers 必须是短摘要。"""
    body = "正文" * 2000
    (tmp_path / "big.md").write_text(f"# 大规则\n\n{body}\n", encoding="utf-8")
    rs = RuleSet.load(tmp_path, scope={"big": {"always": True, "summary": "摘要"}})
    h = rs.headers()[0]
    assert len(h) < 120, "规则头必须远小于正文"
    assert rs.stats()["total_estimated_tokens"] > 1000
    assert rs.stats()["header_tokens_if_all_headers_kept"] < 60


def test_ruleset_conflicts_for():
    rs = RuleSet([])
    got = rs.conflicts_for(["vuln-report-format"])
    assert any("报告" in c["topic"] for c in got)
