"""SkillRoute-Bench 运行器。

对同一基准跑多组配置，输出分层指标对比。

用法::

    .venv/Scripts/python backend/tools/run_bench.py
    .venv/Scripts/python backend/tools/run_bench.py --bench eval/bench/skillroute-bench-v0.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.eval import breakdown_by, load_bench, run_bench, save_bench  # noqa: E402
from app.skills.lexicon import BilingualLexicon  # noqa: E402
from app.skills.metadata import infer_all  # noqa: E402
from app.skills.registry import SkillRegistry  # noqa: E402
from app.skills.router import RouterConfig, SkillRouter  # noqa: E402

CORPUS = Path(os.path.expanduser("~")) / ".dsh" / "skills"
REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_BENCH = REPO / "eval" / "bench" / "skillroute-bench-v0.jsonl"


def build(
    lexicon,
    overlay: dict | None,
    *,
    scoring: str = "fielded",
    channels: tuple[str, ...] = ("bm25",),
    weights: dict[str, float] | None = None,
    expand_query: bool = True,
    enrich_triggers: bool = True,
    top_k: int = 5,
    min_score: float = 0.0,
    min_coverage: float = 0.0,
) -> tuple[SkillRegistry, SkillRouter]:
    reg = SkillRegistry()
    reg.load_roots([("dsh", CORPUS)])
    if lexicon is not None:
        reg.attach_lexicon(lexicon, enrich_triggers=enrich_triggers)
    if overlay:
        reg.apply_overlay(overlay, only_missing=True)
    reg.build_index(tokenizer="hybrid", vector_kind="lsa", n_components=64, scoring=scoring)
    router = SkillRouter(
        reg,
        RouterConfig(top_k=top_k, recall_n=50, channels=channels, weights=weights,
                     expand_query=expand_query, enrich_triggers=enrich_triggers,
                     min_score=min_score, min_coverage=min_coverage),
    )
    return reg, router


#: 对照配置：(名称, 参数字典)
#:
#: **配置设计纪律**：每组配置只改变**一个**自变量，否则无法归因。
#: （初版曾把 `scoring="flat"` 与默认双通道配在一起，与"仅 BM25 单通道"对比时
#: 混淆了"分字段"与"通道数"两个因素，已修正。）
CONFIGS: list[tuple[str, dict]] = [
    ("① 基线（无跨语言）", dict(expand_query=False, enrich_triggers=False,
                                channels=("bm25",))),
    ("② 仅索引侧富化", dict(expand_query=False, enrich_triggers=True,
                            channels=("bm25",))),
    ("③ 仅查询侧扩展", dict(expand_query=True, enrich_triggers=False,
                            channels=("bm25",))),
    ("④ 跨语言双机制(bm25)", dict(expand_query=True, enrich_triggers=True,
                                  channels=("bm25",))),
    ("⑤ 加向量通道+等权RRF", dict(channels=("bm25", "vector"))),
    ("⑥ 加向量通道(权重0.3)", dict(channels=("bm25", "vector"),
                                    weights={"bm25": 1.0, "vector": 0.3})),
    ("⑦ 仅向量单通道", dict(channels=("vector",))),
    ("⑧ 拼接式BM25(消融分字段)", dict(channels=("bm25",), scoring="flat")),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--save-results", action="store_true",
                    help="把逐条结果写入 eval/runs/ 便于事后分析")
    ap.add_argument("--sweep-min-score", action="store_true",
                    help="扫描弃权阈值，输出「弃权准确率 vs 召回」权衡")
    args = ap.parse_args()

    if not args.bench.exists():
        print(f"基准文件不存在: {args.bench}", file=sys.stderr)
        return 1
    if not CORPUS.exists():
        print(f"语料不存在: {CORPUS}", file=sys.stderr)
        return 1

    items = load_bench(args.bench)
    n_abstain = sum(1 for it in items if it.is_abstention)
    print("=" * 92)
    print(f"SkillRoute-Bench: {args.bench.name}")
    print(f"  条目 {len(items)}（其中弃权用例 {n_abstain}，计分条目 {len(items) - n_abstain}）")
    by_src: dict[str, int] = {}
    by_lang: dict[str, int] = {}
    for it in items:
        by_src[it.source] = by_src.get(it.source, 0) + 1
        by_lang[it.lang] = by_lang.get(it.lang, 0) + 1
    print(f"  来源 {by_src} | 语言 {by_lang}")
    print("=" * 92)

    lex = BilingualLexicon.build(mined_path=None, include_mined=False)
    reg_plain = SkillRegistry()
    reg_plain.load_roots([("dsh", CORPUS)])
    overlay = {n: m.to_dict() for n, m in infer_all(reg_plain.skills.values()).items()}

    header = (f"{'配置':<26}{'R@1':>7}{'R@3':>7}{'R@5':>7}{'MRR':>7}"
              f"{'弃权准确':>10}{'误路由':>8}{'元数据省':>10}")
    print(header)
    print("-" * 92)

    all_metrics = []
    for name, kw in CONFIGS:
        reg, router = build(lex, overlay, top_k=args.top_k, **kw)
        m = run_bench(router, items, name=name, top_k=args.top_k)
        all_metrics.append((name, m))
        d = m.to_dict()
        print(f"{name:<26}{d['recall@1']:>7.3f}{d['recall@3']:>7.3f}"
              f"{d['recall@5']:>7.3f}{d['mrr_stage1']:>7.3f}"
              f"{d['abstention_accuracy']:>10.3f}{d['false_route_rate']:>8.3f}"
              f"{d['meta_saving']:>9.1%}")

    print("-" * 92)

    # ---- 分层报告（控制来源偏差） ----
    best_name, best = max(all_metrics, key=lambda kv: (kv[1].recall5, kv[1].mrr))
    print(f"\n最优配置 `{best_name}` 的分层报告：")
    for key, label in (("lang", "语言"), ("confidence", "标注置信度")):
        print(f"\n  按{label}分层：")
        for k, sub in sorted(breakdown_by(best.results, key).items()):
            print(f"    {k:<10} {sub.summary()}")

    # ---- 失效明细 ----
    miss = [r for r in best.results if not r.item.is_abstention and not r.hit]
    if miss:
        print(f"\n未命中（{len(miss)} 条）：")
        for r in miss[:15]:
            kind = "排序失败" if r.stage1_rank else "召回失败"
            print(f"  [{kind}] {r.item.id}: <{r.item.query[:44]}>")
            print(f"          期望 {r.item.expected}")
            print(f"          实际 {r.candidates}")
    fr = [r for r in best.results if r.false_route]
    if fr:
        print(f"\n弃权失败（{len(fr)} 条，近义陷阱为主）：")
        for r in fr[:12]:
            print(f"  ✗ {r.item.id}: <{r.item.query[:44]}>")
            print(f"          误路由到 {r.candidates[:3]}")
            print(f"          说明：{r.item.notes}")

    if args.save_results:
        out = REPO / "eval" / "runs" / "bench_v0_results.jsonl"
        save_bench([r.item for r in best.results], out)
        print(f"\n-> 结果已写入 {out}")

    # ---- 弃权阈值扫描（基于 IDF 加权覆盖率） ----
    if args.sweep_min_score:
        print("\n" + "=" * 92)
        print("弃权信号诊断与阈值扫描（配置③ 仅查询侧扩展 / 仅 BM25 单通道）")
        print("=" * 92)
        print("弃权信号 = 最高 IDF 加权查询词覆盖率 ∈ [0,1]（见 BM25Index.weighted_coverage）。")
        print("RRF 得分不能做弃权：它只用排名，得分恒为 1/(k+rank)，与匹配强度无关。\n")

        # 先跑一次不弃权，收集覆盖率分布（区分弃权用例与计分用例）
        _reg, router0 = build(lex, overlay, channels=("bm25",), min_coverage=0.0,
                              top_k=args.top_k)
        cov_abstain: list[float] = []
        cov_scored: list[float] = []
        for it in items:
            res = router0.route(it.query, top_k=args.top_k)
            (cov_abstain if it.is_abstention else cov_scored).append(res.top_coverage)

        def _stat(xs: list[float]) -> str:
            if not xs:
                return "—"
            s = sorted(xs)
            n = len(s)
            return (f"n={n} 均 {sum(s)/n:.3f} 中位 {s[n//2]:.3f} "
                    f"min {s[0]:.3f} max {s[-1]:.3f}")

        print(f"弃权用例覆盖率   {_stat(cov_abstain)}")
        print(f"计分用例覆盖率   {_stat(cov_scored)}")
        overlap = (max(cov_abstain) if cov_abstain else 0) - \
                  (min(cov_scored) if cov_scored else 0)
        print(f"→ 两组区间的重叠宽度: {overlap:.3f}"
              f"（>0 表示存在不可分区域，阈值需权衡）\n")

        print(f"{'覆盖率阈值':>12}{'R@5':>8}{'MRR':>8}{'弃权准确':>10}{'误路由':>8}"
              f"{'真答案被误弃权':>16}")
        print("-" * 92)
        best_row = None
        for thr in (0.00, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60):
            _r, router = build(lex, overlay, channels=("bm25",), min_coverage=thr,
                               top_k=args.top_k)
            m = run_bench(router, items, top_k=args.top_k)
            over = sum(1 for r in m.results
                       if not r.item.is_abstention and r.abstained)
            d = m.to_dict()
            print(f"{thr:>12.2f}{d['recall@5']:>8.3f}{d['mrr_stage1']:>8.3f}"
                  f"{d['abstention_accuracy']:>10.3f}{d['false_route_rate']:>8.3f}"
                  f"{over:>16}")
            if best_row is None or (
                d["abstention_accuracy"] - 0.5 * over / max(len(items), 1)
                > best_row[0]
            ):
                best_row = (d["abstention_accuracy"] - 0.5 * over / max(len(items), 1),
                            thr, d, over)
        print("-" * 92)
        if best_row:
            print(f"权衡最优点（启发式评分）：阈值 {best_row[1]:.2f} → "
                  f"弃权准确 {best_row[2]['abstention_accuracy']:.3f}，"
                  f"R@5 {best_row[2]['recall@5']:.3f}，误弃权 {best_row[3]} 条")
        print("⚠️ 阈值必须在**留出集**上标定；同一集上扫描仅用于展示权衡曲线，"
              "不可据此直接选定阈值。")

    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
