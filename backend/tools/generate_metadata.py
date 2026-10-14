"""M2：路由元数据生成与效果评估。

## 流程

1. 加载本机技能语料；
2. 用 ``app/skills/metadata.py`` 的规则**推断** `phase` / `domains` / `targets` /
   `triggers` / `risk`（可解释：记录命中的关键词）；
3. 产出 **overlay**（`data/skill_metadata.json`）——原始 `SKILL.md` 字节不变；
4. **测量**：对比应用 overlay 前后的路由命中率（探针集）；
5. 输出人工复核报告（`docs/技能元数据生成报告.md`）。

## 为什么必须测量而不是"补上就算完成"

元数据推断是启发式的，规则可能误判（例如把"信息收集阶段的漏洞探测"判成
`exploitation`）。因此**必须用路由指标验证推断是否真的有用**，
而不是假定"字段补齐了就应该更好"。

用法::

    .venv/Scripts/python backend/tools/generate_metadata.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.eval import PROBES, evaluate_routing  # noqa: E402
from app.skills.lexicon import BilingualLexicon  # noqa: E402
from app.skills.metadata import infer_all  # noqa: E402
from app.skills.registry import SkillRegistry  # noqa: E402
from app.skills.router import RouterConfig, SkillRouter  # noqa: E402

CORPUS = Path(os.path.expanduser("~")) / ".dsh" / "skills"
REPO = Path(__file__).resolve().parent.parent.parent


def build_registry(lexicon, overlay: dict | None) -> SkillRegistry:
    reg = SkillRegistry()
    reg.load_roots([("dsh", CORPUS)])
    if lexicon is not None:
        reg.attach_lexicon(lexicon, enrich_triggers=True)
    if overlay:
        reg.apply_overlay(overlay, only_missing=True)
    reg.build_index(tokenizer="hybrid", vector_kind="lsa", n_components=64)
    return reg


def make_router(reg: SkillRegistry) -> SkillRouter:
    return SkillRouter(reg, RouterConfig(top_k=5, recall_n=30,
                                        expand_query=True, enrich_triggers=True))


def coverage(reg: SkillRegistry) -> dict[str, int]:
    """统计元数据字段的覆盖情况。"""
    n = len(reg)
    return {
        "total": n,
        "phase": sum(1 for s in reg.skills.values() if s.meta.phase),
        "domains": sum(1 for s in reg.skills.values() if s.meta.domains),
        "targets": sum(1 for s in reg.skills.values() if s.meta.targets),
        "triggers": sum(1 for s in reg.skills.values() if s.meta.triggers),
        "risk_high": sum(1 for s in reg.skills.values() if s.meta.risk == "high"),
        "risk_medium": sum(1 for s in reg.skills.values() if s.meta.risk == "medium"),
    }


def render_report(
    before: dict, after: dict, grid: dict, overlay: dict, inferred, stats_overlay: dict,
) -> str:
    """`grid` 为 2×2 消融结果：{(词典名, 元数据名): EvalStats}。"""
    L: list[str] = []
    L.append("# 技能路由元数据生成报告（自动生成）\n")
    L.append("> 由 `backend/tools/generate_metadata.py` 生成。"
             "规则定义见 `backend/app/skills/metadata.py`。\n")
    L.append("## 1. 动机\n")
    L.append("实测发现本机语料的 **125/125 个技能完全缺失路由元数据**"
             "（无 `triggers`/`phase`/`domains`）——它们只有 agentskills.io 规范要求的"
             "`name` + `description`。缺这些字段时，路由只能依赖描述文本的模糊字面匹配，"
             "这是长描述伞状技能霸榜的原因之一。\n")
    L.append("## 2. 覆盖情况（推断前 → 推断后）\n")
    L.append("| 字段 | 推断前 | 推断后 |")
    L.append("|---|---:|---:|")
    for key, label in (("total", "技能总数"), ("phase", "有 phase"),
                       ("domains", "有 domains"), ("targets", "有 targets"),
                       ("triggers", "有 triggers")):
        L.append(f"| {label} | {before[key]} | {after[key]} |")
    L.append(f"| risk=high | {before['risk_high']} | {after['risk_high']} |")
    L.append(f"| risk=medium | {before['risk_medium']} | {after['risk_medium']} |")
    L.append("")
    L.append(f"覆盖层写入统计：触及 {stats_overlay.get('skills_touched', 0)} 个技能，"
             f"填充 {stats_overlay.get('fields_filled', 0)} 个字段，"
             f"跳过（语料已声明）{stats_overlay.get('fields_skipped', 0)} 个字段。\n")

    # 分布
    ph = Counter(s.phase or "(未推断)" for s in inferred.values())
    dm: Counter = Counter()
    for s in inferred.values():
        for d in s.domains or ["(未推断)"]:
            dm[d] += 1
    L.append("## 3. 推断结果分布\n")
    L.append("| phase | 技能数 |")
    L.append("|---|---:|")
    for k, v in ph.most_common():
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("| domain | 技能数 |")
    L.append("|---|---:|")
    for k, v in dm.most_common(18):
        L.append(f"| {k} | {v} |")
    L.append("")

    # ---- 2×2 消融 ----
    lex_names = []
    meta_names = []
    for lname, mname in grid:
        if lname not in lex_names:
            lex_names.append(lname)
        if mname not in meta_names:
            meta_names.append(mname)

    L.append("## 4. 2×2 消融：词典层 × 元数据层\n")
    L.append("> ⚠️ 探针集仅 14 条、单人标注，**仅用于开发期诊断，不构成论文实验依据**。"
             "正式结论须由 SkillRoute-Bench（200+ 条带标注真值）给出。\n")
    L.append("两个自变量的效果可能重叠（都作用于「把中文查询与英文/隐式描述对上」"
             "这件事），因此必须做正交对照而非只测单因素。\n")
    L.append("| 词典层 \\ 元数据层 | " + " | ".join(meta_names) + " |")
    L.append("|---" * (len(meta_names) + 1) + "|")
    for lname in lex_names:
        cells = []
        for mname in meta_names:
            st = grid.get((lname, mname))
            cells.append(st.summary() if st else "—")
        L.append(f"| **{lname}** | " + " | ".join(cells) + " |")
    L.append("")
    L.append("中文命中明细：\n")
    L.append("| 词典层 \\ 元数据层 | " + " | ".join(meta_names) + " |")
    L.append("|---" * (len(meta_names) + 1) + "|")
    for lname in lex_names:
        cells = []
        for mname in meta_names:
            st = grid.get((lname, mname))
            cells.append(f"{st.zh_hit}/{st.zh_total}" if st else "—")
        L.append(f"| **{lname}** | " + " | ".join(cells) + " |")
    L.append("")

    # 结论
    best = max(grid.items(), key=lambda kv: (kv[1].hit, kv[1].zh_hit))
    L.append(f"**最优配置：`{best[0][0]}` + `{best[0][1]}`，{best[1].summary()}。**\n")
    # 元数据层的边际贡献（在同一词典层内比较）
    for lname in lex_names:
        a = grid.get((lname, meta_names[0]))
        b = grid.get((lname, meta_names[-1]))
        if a and b:
            L.append(f"- 词典层 `{lname}`：元数据层带来 "
                     f"{b.hit - a.hit:+d} 总命中 / {b.zh_hit - a.zh_hit:+d} 中文命中")
    L.append("")
    L.append("> **负面结果须如实报告**：若某因素贡献为 0 或为负，"
             "论文中不得省略——它恰恰说明该机制的作用被其他机制覆盖，是有价值的发现。\n")

    st_best = best[1]
    if st_best.failed:
        L.append("### 最优配置下仍未命中的查询（剩余失效模式）\n")
        for o in st_best.failed:
            L.append(f"- `{o.label}`：<{o.query}> 期望 {o.expected}")
        L.append("")

    L.append("## 5. 人工复核样本\n")
    L.append("推断是可解释的——每条都记录了命中的关键词，复核时只需检查"
             "「为什么给出这个标签」而非通读技能全文。\n")
    L.append("| 技能 | phase | domains | targets | risk | 依据 |")
    L.append("|---|---|---|---|---|---|")
    for name in list(overlay)[:24]:
        meta = overlay[name]
        ev = meta.get("evidence", {})
        ev_short = "; ".join(f"{k}={','.join(v[:2])}" for k, v in list(ev.items())[:3])
        if len(ev_short) > 90:
            ev_short = ev_short[:90] + "…"
        L.append(
            f"| `{name}` | {meta.get('phase') or '—'} "
            f"| {', '.join(meta.get('domains') or []) or '—'} "
            f"| {', '.join(meta.get('targets') or []) or '—'} "
            f"| {meta.get('risk')} | {ev_short} |"
        )
    L.append("")
    L.append("## 6. 方法与局限\n")
    L.append("- **产出覆盖层而非改写原文件**：原始 `SKILL.md` 字节不变，"
             "课题加工与原始语料可分离，便于消融与回滚。\n")
    L.append("- **只填补空字段**（`only_missing=True`）：绝不覆盖语料已声明的值——"
             "语料作者的声明优先级高于规则推断。\n")
    L.append("- **匹配范围限于正文前 60 行**：技能正文常在开头声明适用场景，"
             "后续数百行为操作细节；取全文会引入大量与技术栈无关的噪声词。\n")
    L.append("- **局限**：规则为关键词匹配，无上下文理解能力，"
             "对同义改写与技术栈隐含描述无能为力。后续可评估用 LLM 辅助推断，"
             "但须权衡可复现性与成本。\n")
    return "\n".join(L)


def main() -> int:
    if not CORPUS.exists():
        print(f"语料不存在: {CORPUS}", file=sys.stderr)
        return 1

    mined = REPO / "data" / "lexicon_mined.json"
    lexicons = [
        ("人工词典", BilingualLexicon.build(mined_path=None, include_mined=False)),
        ("人工词典+挖掘", BilingualLexicon.build(mined_path=mined, include_mined=True)),
    ]

    # ---- 推断（不挂词典，保持推断与词典解耦） ----
    reg_plain = SkillRegistry()
    reg_plain.load_roots([("dsh", CORPUS)])
    inferred = infer_all(reg_plain.skills.values())
    overlay = {name: im.to_dict() for name, im in inferred.items()}
    before = coverage(reg_plain)

    reg_ref = build_registry(lexicons[0][1], overlay=overlay)
    after = coverage(reg_ref)

    # ---- 2×2 消融 ----
    meta_variants = [("无元数据", None), ("有元数据", overlay)]
    grid: dict[tuple[str, str], object] = {}
    for lname, lx in lexicons:
        for mname, ov in meta_variants:
            reg = build_registry(lx, ov)
            grid[(lname, mname)] = evaluate_routing(make_router(reg), PROBES)

    # ---- 写出覆盖层 ----
    out = REPO / "data" / "skill_metadata.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "source_corpus": str(CORPUS),
                "generator": "backend/app/skills/metadata.py",
                "only_missing_on_apply": True,
                "skills_inferred": len(overlay),
                "overlay": overlay,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ---- 报告 ----
    report = render_report(before, after, grid, overlay, inferred, reg_ref.overlay_stats)
    rpath = REPO / "docs" / "技能元数据生成报告.md"
    rpath.write_text(report, encoding="utf-8")

    print("=" * 78)
    print(f"技能总数 {before['total']}")
    print(f"覆盖  phase {before['phase']} -> {after['phase']}"
          f" | domains {before['domains']} -> {after['domains']}"
          f" | targets {before['targets']} -> {after['targets']}"
          f" | triggers {before['triggers']} -> {after['triggers']}")
    print(f"覆盖层：触及 {reg_ref.overlay_stats.get('skills_touched', 0)} 技能，"
          f"填充 {reg_ref.overlay_stats.get('fields_filled', 0)} 字段，"
          f"跳过 {reg_ref.overlay_stats.get('fields_skipped', 0)} 字段")
    print("-" * 78)
    print("2×2 消融（探针集 14 条）：")
    for lname, _lx in lexicons:
        for mname, _ov in meta_variants:
            st = grid[(lname, mname)]
            print(f"  {lname:<14} × {mname:<8}  {st.summary()}")
    print("-" * 78)
    best = max(grid.items(), key=lambda kv: (kv[1].hit, kv[1].zh_hit))
    print(f"最优：{best[0][0]} × {best[0][1]}  {best[1].summary()}")
    for lname, _lx in lexicons:
        a = grid[(lname, "无元数据")]
        b = grid[(lname, "有元数据")]
        print(f"  元数据层边际（{lname}）：{b.hit - a.hit:+d} 总 / "
              f"{b.zh_hit - a.zh_hit:+d} 中文")
    if best[1].failed:
        print("\n最优配置下仍未命中：")
        for o in best[1].failed:
            print(f"  ✗ {o.label}: <{o.query}>")
    print("=" * 78)
    print(f"-> {out}")
    print(f"-> {rpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
