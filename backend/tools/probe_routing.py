"""路由质量探针 + 跨语言消融实验。

用一组代表性查询，对比四种配置下的路由命中率：

======================  ============  ==============
配置                    索引侧富化     查询侧扩展
======================  ============  ==============
① 基线（无跨语言支持）      ✗             ✗
② 仅索引侧富化             ✓             ✗
③ 仅查询侧扩展             ✗             ✓
④ 两者都开                 ✓             ✓
======================  ============  ==============

**这不是正式的 SkillRoute-Bench**（真值集规模小、由单人标注），
而是先导实验，用于验证跨语言机制是否有效、并定位剩余失效模式。

用法::

    .venv/Scripts/python backend/tools/probe_routing.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.skills.lexicon import BilingualLexicon  # noqa: E402
from app.skills.registry import SkillRegistry  # noqa: E402
from app.skills.router import RouterConfig, SkillRouter  # noqa: E402

#: 探针查询：(说明, 查询文本, 期望命中的技能名片段)
PROBES: list[tuple[str, str, list[str]]] = [
    ("中文·WordPress 后台", "目标是一个 WordPress 站点，我要找管理员登录入口",
     ["wordpress", "login", "401-403", "admin"]),
    ("中文·水平越权", "这个接口返回了别人的订单数据，帮我测试水平越权",
     ["bola", "authorization", "idor"]),
    ("中文·域渗透票据", "域环境里如何做 Kerberoasting 拿票据",
     ["kerberos", "active-directory"]),
    ("中文·SQL 注入", "登录框疑似存在 SQL 注入，怎么做报错注入",
     ["sqli", "sql-injection", "injection"]),
    ("中文·SSRF", "一个 URL 参数可能可以访问内网，测试 SSRF", ["ssrf"]),
    ("中文·文件上传", "上传头像的功能想绕过文件类型校验拿 shell",
     ["upload", "file-upload"]),
    ("中文·反序列化", "Java 反序列化漏洞怎么利用", ["deserialization", "java"]),
    ("中文·子域名", "先做信息收集，把子域名和资产都测绘出来",
     ["subdomain", "recon", "asset"]),
    ("中文·提示注入", "测试这个大模型应用有没有提示注入和越狱问题",
     ["prompt", "ai-ml", "llm", "injection"]),
    ("中文·云原生", "容器逃逸和 K8s 集群的提权怎么打",
     ["container", "k8s", "kubernetes", "escape"]),
    ("英文·Kerberos", "Kerberoasting AD ticket attacks", ["kerberos", "active-directory"]),
    ("英文·BOLA", "API object level authorization testing", ["bola", "authorization"]),
    ("英文·upload", "bypass file upload restrictions to get RCE", ["upload"]),
    ("英文·SSRF", "server side request forgery to reach cloud metadata",
     ["ssrf", "cloud", "metadata"]),
]

CONFIGS: list[tuple[str, bool, bool]] = [
    ("① 基线（无跨语言）", False, False),
    ("② 仅索引侧富化", True, False),
    ("③ 仅查询侧扩展", False, True),
    ("④ 两者都开", True, True),
]


def build(corpus: Path, lexicon, enrich: bool) -> tuple[SkillRegistry, SkillRouter, bool]:
    reg = SkillRegistry()
    reg.load_roots([("dsh", corpus)])
    if lexicon is not None:
        reg.attach_lexicon(lexicon, enrich_triggers=enrich)
    reg.build_index(tokenizer="hybrid", vector_kind="lsa", n_components=64)
    router = SkillRouter(reg, RouterConfig(top_k=5, recall_n=30))
    return reg, router, enrich


def evaluate(router: SkillRouter, verbose: bool = False) -> dict:
    stats = {"total": 0, "hit": 0, "zh_total": 0, "zh_hit": 0, "en_total": 0, "en_hit": 0}
    details = []
    for label, query, expect in PROBES:
        is_zh = label.startswith("中文")
        res = router.route(query)
        names = [c.skill.name for c in res.candidates]
        hit = any(any(e in n for n in names) for e in expect)

        stats["total"] += 1
        stats["hit"] += int(hit)
        if is_zh:
            stats["zh_total"] += 1
            stats["zh_hit"] += int(hit)
        else:
            stats["en_total"] += 1
            stats["en_hit"] += int(hit)

        details.append((label, query, expect, names, hit, res))
        if verbose:
            flag = "✓" if hit else "✗"
            print(f"\n  [{flag}] {label}  <{query}>")
            if res.query_expansion:
                exp = "、".join(f"{zh}→{en.split()[0]}" for zh, en in res.query_expansion[:4])
                print(f"      扩展: {exp}")
            for c in res.candidates:
                print(f"        {c.skill.name:38} {c.reason}")

    stats["details"] = details
    return stats


def main() -> int:
    repo = Path(__file__).resolve().parent.parent.parent
    corpus = Path(os.path.expanduser("~")) / ".dsh" / "skills"
    if not corpus.exists():
        print(f"语料不存在: {corpus}", file=sys.stderr)
        return 1

    lex = BilingualLexicon.build(repo / "data" / "lexicon_mined.json")
    ls = lex.stats.to_dict()
    print("=" * 78)
    print("双语词典：人工核心 %d 条 | 人工复核补充 %d 条 | 自动挖掘并入 %d 条 | 中文键共 %d"
          % (ls["curated_terms"], ls["trusted_extra"], ls["mined_pairs"], ls["total_zh_keys"]))
    print("=" * 78)

    summary = []
    regs: dict[str, SkillRegistry] = {}
    for name, enrich, expand in CONFIGS:
        reg, router, _ = build(corpus, lex, enrich)
        regs[name] = reg
        router.config.expand_query = expand
        # 基线配置展示逐条明细，最优配置也展示，便于观察剩余失效模式
        verbose = name in ("① 基线（无跨语言）", "④ 两者都开")
        st = evaluate(router, verbose=verbose)
        summary.append((name, st))
        es = reg.enrichment_stats
        print(f"\n{name}: 命中 {st['hit']}/{st['total']}"
              f"  中文 {st['zh_hit']}/{st['zh_total']}"
              f"  英文 {st['en_hit']}/{st['en_total']}"
              f"  | 富化技能 {es.get('enriched', 0)} 个，补入术语 {es.get('terms_added', 0)} 个")

    print("\n" + "=" * 78)
    print("消融结果汇总")
    print("=" * 78)
    print(f"{'配置':<22}{'中文命中':>12}{'英文命中':>12}{'总命中':>12}")
    for name, st in summary:
        print(f"{name:<22}{st['zh_hit']:>7}/{st['zh_total']:<4}"
              f"{st['en_hit']:>7}/{st['en_total']:<4}"
              f"{st['hit']:>7}/{st['total']:<4}")
    print("=" * 78)

    # ---- 自动挖掘层的边际贡献对照 ----
    print("\n" + "=" * 78)
    print("自动挖掘层的边际贡献（两种机制均开启）")
    print("=" * 78)
    lex_curated = BilingualLexicon.build(mined_path=None, include_mined=False)
    mined_rows = []
    for tag, lx in (("人工词典（无自动挖掘）", lex_curated), ("人工词典 + 自动挖掘", lex)):
        reg, router, _ = build(corpus, lx, True)
        router.config.expand_query = True
        st = evaluate(router)
        mined_rows.append((tag, st, lx.stats.to_dict()))
        print(f"{tag:<24} 中文 {st['zh_hit']}/{st['zh_total']}"
              f"  英文 {st['en_hit']}/{st['en_total']}"
              f"  总 {st['hit']}/{st['total']}"
              f"  | 词典中文键 {lx.stats.total_zh_keys}，挖掘并入 {lx.stats.mined_pairs}")
    print("→ 若两者得分相同，说明当前挖掘层未带来增益，应提高频次门槛或加强过滤；"
          "论文中须如实报告。")

    # ---- 剩余失效模式 ----
    worst = dict(summary)["④ 两者都开"]
    failed = [(lbl, q, exp) for lbl, q, exp, names, hit, _r in worst["details"] if not hit]
    if failed:
        print("\n最优配置下仍未命中的查询（剩余失效模式）")
        for lbl, q, exp in failed:
            print(f"  ✗ {lbl}: <{q}>  期望 {exp}")
        print("  → 这些查询的共同特征是被中文长描述的伞状技能占据前列，"
              "说明仍需技能分层（伞状技能→子技能）的路由策略。")

    # ---- 索引侧富化示例（人工审阅用） ----
    enriched_reg = regs.get("② 仅索引侧富化")
    if enriched_reg is not None:
        print("\n索引侧富化示例（人工审阅用）")
        shown = 0
        for name in enriched_reg.skills:
            extra = enriched_reg.enriched_triggers(name)
            if extra and shown < 8:
                print(f"  {name:38} 补入: {'、'.join(extra[:10])}")
                shown += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
