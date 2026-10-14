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

from app.eval import PROBES, EvalStats, evaluate_routing  # noqa: E402
from app.skills.lexicon import BilingualLexicon  # noqa: E402
from app.skills.registry import SkillRegistry  # noqa: E402
from app.skills.router import RouterConfig, SkillRouter  # noqa: E402

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


def evaluate(router: SkillRouter, verbose: bool = False) -> EvalStats:
    st = evaluate_routing(router, PROBES)
    if verbose:
        for o in st.outcomes:
            flag = "✓" if o.hit else ("RANK" if o.ranking_failure else "✗")
            print(f"\n  [{flag}] {o.label}  <{o.query}>")
            res = o.result
            if getattr(res, "query_expansion", None):
                exp = "、".join(f"{zh}→{en.split()[0]}"
                                for zh, en in res.query_expansion[:4])
                print(f"      扩展: {exp}")
            print(f"      阶段一期望技能名次: {o.stage1_rank or '未召回'}")
            for c in res.candidates:
                print(f"        {c.skill.name:38} {c.reason}")
    return st


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
        verbose = name in ("① 基线（无跨语言）", "④ 两者都开")
        st = evaluate(router, verbose=verbose)
        summary.append((name, st))
        es = reg.enrichment_stats
        print(f"\n{name}: {st.summary()}"
              f"  | 富化技能 {es.get('enriched', 0)} 个，补入术语 {es.get('terms_added', 0)} 个")

    print("\n" + "=" * 78)
    print("消融结果汇总")
    print("=" * 78)
    print(f"{'配置':<22}{'中文命中':>12}{'英文命中':>12}{'总命中':>12}")
    for name, st in summary:
        print(f"{name:<22}{st.zh_hit:>7}/{st.zh_total:<4}"
              f"{st.en_hit:>7}/{st.en_total:<4}"
              f"{st.hit:>7}/{st.total:<4}")
    print("=" * 78)

    # ---- 自动挖掘层的边际贡献对照 ----
    print("\n" + "=" * 78)
    print("自动挖掘层的边际贡献（两种机制均开启）")
    print("=" * 78)
    lex_curated = BilingualLexicon.build(mined_path=None, include_mined=False)
    for tag, lx in (("人工词典（无自动挖掘）", lex_curated), ("人工词典 + 自动挖掘", lex)):
        reg, router, _ = build(corpus, lx, True)
        router.config.expand_query = True
        st = evaluate(router)
        print(f"{tag:<24} {st.summary()}"
              f"  | 词典中文键 {lx.stats.total_zh_keys}，挖掘并入 {lx.stats.mined_pairs}")
    print("→ 若两者得分相同或更低，说明当前挖掘层未带来增益，须如实报告。")

    # ---- 召回失败 vs 排序失败（关键诊断） ----
    print("\n" + "=" * 78)
    print("失效类型诊断（区分「召回失败」与「排序失败」）")
    print("=" * 78)
    for name, st in summary:
        rf, kf = st.recall_failures, st.ranking_failures
        print(f"{name:<22} 召回失败 {len(rf)}  排序失败 {len(kf)}"
              f"  阶段一 MRR {st.mrr:.3f}")
    best_name, best_st = max(summary, key=lambda kv: (kv[1].hit, kv[1].zh_hit))
    print(f"\n最优配置 `{best_name}` 的逐条明细：")
    for o in best_st.outcomes:
        mark = "HIT " if o.hit else ("排序失败" if o.ranking_failure else "召回失败")
        print(f"  [{mark}] {o.label:<18} 阶段一名次={o.stage1_rank or '未召回'}")
    if not best_st.recall_failures:
        print("\n  → **本探针集上无一例召回失败**：期望技能均进入阶段一候选池，"
              "故瓶颈不在检索通道，而在**排序/融合**；"
              "继续增加检索通道或元数据字段不会改善结果。")

    # ---- 索引侧富化示例（人工审阅用） ----
    enriched_reg = regs.get("② 仅索引侧富化")
    if enriched_reg is not None:
        print("\n索引侧富化示例（人工审阅用）")
        shown = 0
        for name in enriched_reg.skills:
            extra = enriched_reg.enriched_triggers(name)
            if extra and shown < 6:
                print(f"  {name:38} 补入: {'、'.join(extra[:10])}")
                shown += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
