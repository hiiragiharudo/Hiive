"""路由元数据规则推断的单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.skills.metadata import (
    DOMAIN_RULES,
    PHASE_RULES,
    RISK_HIGH,
    TARGET_RULES,
    infer_all,
    infer_phase,
    infer_risk,
    infer_skill,
    infer_triggers,
)
from app.skills.models import Skill, SkillMeta
from app.skills.registry import SkillRegistry


def _skill(name: str, description: str = "", body: str = "", **kw) -> Skill:
    meta = SkillMeta(name=name, description=description, **kw)
    return Skill(meta=meta, body=body, body_lines=len(body.splitlines()))


# --------------------------------------------------------------------- 阶段


@pytest.mark.parametrize(
    "text,expected",
    [
        ("执行 Kerberoasting 拿到票据后横向移动到域控", "post"),
        ("后渗透阶段的持久化与权限维持", "post"),
        ("利用反序列化漏洞 getshell", "exploitation"),
        ("bypass file upload restrictions to get RCE", "exploitation"),
        ("子域名收集与资产测绘，铺开攻击面", "recon"),
        ("reconnaissance and port scan", "recon"),
        ("生成漏洞报告并提交到 SRC", "report"),
        ("SQL 注入探测与验证", "discovery"),
    ],
)
def test_infer_phase(text: str, expected: str):
    phase, evidence = infer_phase(text.lower())
    assert phase == expected, f"{text!r} 应判为 {expected}，实际 {phase}"
    assert evidence, "应记录命中的关键词作为依据"


def test_phase_rules_are_ordered_specific_first():
    """更具体的阶段（post/report）必须排在笼统阶段（discovery）之前。"""
    order = [p for p, _ in PHASE_RULES]
    assert order.index("post") < order.index("discovery")
    assert order.index("report") < order.index("discovery")


def test_infer_phase_returns_empty_when_no_match():
    phase, evidence = infer_phase("zzzz qqqq")
    assert phase == ""
    assert evidence == []


# --------------------------------------------------------------------- 风险


def test_infer_risk_high_for_destructive_capabilities():
    risk, ev = infer_risk("任意文件上传 getshell 后提权")
    assert risk == "high"
    assert ev


def test_infer_risk_medium_for_probing():
    risk, _ = infer_risk("对参数做 fuzz 与爆破")
    assert risk == "medium"


def test_infer_risk_low_by_default():
    risk, ev = infer_risk("阅读文档并整理结论")
    assert risk == "low"
    assert ev == []


def test_risk_high_keywords_cover_rce_and_lateral():
    joined = " ".join(RISK_HIGH)
    for kw in ("rce", "提权", "横向", "域控"):
        assert kw in joined


# --------------------------------------------------------------------- 触发词


def test_infer_triggers_from_hyphenated_name():
    s = _skill("active-directory-kerberos-attacks",
               "Kerberos attack playbook for Active Directory.")
    trig = infer_triggers(s, ["ad"], [])
    joined = " ".join(trig)
    assert "active directory" in joined, "连字符技能名应产生词组触发词"
    assert "kerberos" in joined


def test_infer_triggers_strips_generic_suffix():
    s = _skill("sql-injection-techniques", "SQL injection playbook.")
    trig = infer_triggers(s, ["web"], [])
    assert "sql injection" in trig


def test_infer_triggers_includes_declared_and_labels():
    s = _skill("x-skill", "desc", triggers=["已声明触发词"])
    trig = infer_triggers(s, ["web"], ["nginx"])
    assert "已声明触发词" in trig
    assert "nginx" in trig


def test_infer_triggers_dedupes_and_caps():
    s = _skill("a-b-c", "token " * 100)
    trig = infer_triggers(s, [], [])
    assert len(trig) == len(set(trig)), "触发词必须去重"
    assert len(trig) <= 24


def test_infer_triggers_excludes_stopwords():
    s = _skill("use-skill-when", "playbook guide")
    trig = infer_triggers(s, [], [])
    for stop in ("use", "skill", "when", "playbook", "guide"):
        assert stop not in trig


# --------------------------------------------------------------------- 域与目标


def test_domain_rules_cover_required_domains():
    for d in ("web", "api", "ad", "cloud", "container", "mobile", "ai"):
        assert d in DOMAIN_RULES, f"缺少安全域规则: {d}"
        assert DOMAIN_RULES[d]


def test_target_rules_cover_common_stacks():
    for t in ("wordpress", "spring", "nginx", "graphql", "jwt", "kubernetes"):
        assert t in TARGET_RULES, f"缺少目标规则: {t}"


def test_infer_skill_returns_evidence_for_audit():
    s = _skill("api-authorization-and-bola",
               "API authorization and BOLA testing. Use when APIs expose object identifiers.",
               "## 1. CORE TEST LOOP\nreplace object id and compare responses")
    im = infer_skill(s)
    assert im.name == "api-authorization-and-bola"
    assert "api" in im.domains
    assert im.phase, "应推断出阶段"
    assert im.evidence, "必须给出可审计的依据"


def test_infer_skill_body_limited_to_head():
    """正文只取前 60 行——避免操作细节里的噪声词污染推断。"""
    body = "\n".join(f"line {i}" for i in range(60)) + "\nwordpress kubernetes"
    s = _skill("generic-skill", "generic description", body)
    im = infer_skill(s)
    # 第 61 行的 wordpress / kubernetes 不应被算入
    assert "wordpress" not in im.targets
    assert "kubernetes" not in im.targets


# --------------------------------------------------------------------- 覆盖层


CORPUS = {
    "a/idor": "---\nname: idor-hunt\ndescription: 水平越权测试\n---\n换对象标识比较响应\n",
    "b/en": "---\nname: kerberos-attacks\ndescription: Kerberos attack playbook\n---\nAS-REP roasting\n",
}


@pytest.fixture()
def reg(tmp_path: Path) -> SkillRegistry:
    root = tmp_path / "s"
    for sub, content in CORPUS.items():
        d = root / sub
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
    r = SkillRegistry()
    r.load_roots([("t", root)])
    return r


def test_overlay_fills_missing_fields(reg: SkillRegistry):
    before = sum(1 for s in reg.skills.values() if s.meta.phase)
    overlay = {n: m.to_dict() for n, m in infer_all(reg.skills.values()).items()}
    reg.apply_overlay(overlay, only_missing=True)
    after = sum(1 for s in reg.skills.values() if s.meta.phase)
    assert before == 0 and after == len(reg), "空字段应被填满"


def test_overlay_does_not_override_declared_values(reg: SkillRegistry):
    """保守策略：语料已声明的值优先级高于规则推断，不得被覆盖。"""
    skill = reg.get("idor-hunt")
    skill.meta.phase = "exploitation"  # 模拟语料显式声明
    overlay = {"idor-hunt": {"phase": "post", "domains": ["web"]}}
    stats = reg.apply_overlay(overlay, only_missing=True)
    assert skill.meta.phase == "exploitation", "已声明字段不得被覆盖"
    assert skill.meta.domains == ["web"], "空字段仍应被填充"
    assert stats["fields_skipped"] >= 1


def test_overlay_can_force_override_when_asked(reg: SkillRegistry):
    skill = reg.get("idor-hunt")
    skill.meta.phase = "exploitation"
    reg.apply_overlay({"idor-hunt": {"phase": "post"}}, only_missing=False)
    assert skill.meta.phase == "post"


def test_overlay_ignores_unknown_skill_names(reg: SkillRegistry):
    stats = reg.apply_overlay({"不存在的技能": {"phase": "recon"}}, only_missing=True)
    assert stats["skills_touched"] == 0


def test_overlay_does_not_modify_source_files(reg: SkillRegistry, tmp_path: Path):
    """核心保证：覆盖层只改内存模型，原始 SKILL.md 字节不变。"""
    src = tmp_path / "s" / "a" / "idor" / "SKILL.md"
    original = src.read_bytes()
    overlay = {n: m.to_dict() for n, m in infer_all(reg.skills.values()).items()}
    reg.apply_overlay(overlay, only_missing=True)
    assert src.read_bytes() == original, "原始技能文件被改动了"


def test_overlay_risk_only_promotes_not_demotes(reg: SkillRegistry):
    """risk 默认 low；覆盖层不应把已声明的 high 降级为 low。"""
    skill = reg.get("idor-hunt")
    skill.meta.risk = "high"
    reg.apply_overlay({"idor-hunt": {"risk": "low"}}, only_missing=True)
    assert skill.meta.risk == "high"
