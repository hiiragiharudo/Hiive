"""对运行中的 Hiive 服务做端到端验证（真实 HTTP，非 TestClient）。

用法::

    .venv/Scripts/python backend/tools/smoke_api.py [base_url]
"""

from __future__ import annotations

import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"


def show(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0)

    show("1. 健康检查")
    d = c.get("/api/health").json()
    print(f"  status={d['status']} loaded={d['loaded']} skills={d['skill_count']}")
    print(f"  加载 {d['load_ms']} ms | 建索引 {d['index_ms']} ms")
    svc = d.get("load_report", {})
    print(f"  解析错误 {len(svc.get('parse_errors', []))} | "
          f"同名冲突 {len(svc.get('duplicates', []))} | "
          f"富化 {d.get('enrichment_stats')}")
    print(f"  元数据覆盖层: {d.get('overlay_stats')}")

    show("2. 配置区分（前端必须知道哪些参数需重建索引）")
    cfg = c.get("/api/config").json()
    print(f"  建索引时: {cfg['index_time_params']}")
    print(f"  查询时:   {cfg['query_time_params']}")

    show("3. ★ 核心接口：中文查询路由（验证中文在真实 HTTP 上无编码问题）")
    queries = [
        ("域环境里怎么做 Kerberoasting 拿票据", None),
        ("把订单接口的 id 换成别人的能读到他人数据，这是水平越权吗", None),
        ("上传头像的功能只在前端校验扩展名，怎么绕过拿到 webshell", None),
        ("先做信息收集，把子域名和资产都测绘出来", None),
        ("后台返回 403，想试试路径混淆和 header 绕过", None),
    ]
    for q, _ in queries:
        r = c.post("/api/route", json={"query": q, "top_k": 3}).json()
        names = [x["name"] for x in r["candidates"]]
        exp = r["cross_lingual"]
        print(f"\n  Q: {r['query']}")
        if exp["expanded"]:
            terms = "、".join(f"{e['zh']}→{e['en'].split()[0]}"
                             for e in exp["expansion"][:3])
            print(f"     跨语言扩展: {terms}")
        print(f"     命中: {names}")
        if r["candidates"]:
            print(f"     依据: {r['candidates'][0]['reason']}")
        print(f"     阶段一耗时 {r['timing_ms']['stage1']} ms | "
              f"元数据节省 {r['cost']['meta_saving_ratio']:.1%}")

    show("4. 阶段先验（分阶段动态路由）")
    r = c.post("/api/route", json={"query": "横向 提权", "state_phase": "post",
                                   "phase_bonus": 1.0, "top_k": 3}).json()
    for x in r["candidates"]:
        print(f"  {x['name']:<40} phase命中依据: {x['reason']}")

    show("5. 弃权（覆盖率阈值）")
    for thr in (0.0, 0.20, 0.35):
        r = c.post("/api/route", json={"query": "MySQL 慢查询怎么优化，加什么索引",
                                       "min_coverage": thr}).json()
        print(f"  阈值 {thr:.2f} → 弃权={r['abstained']} "
              f"覆盖率={r['top_coverage']} 候选={[x['name'] for x in r['candidates']][:2]}")

    show("6. 技能详情（依赖闭包 = 编排能力）")
    d = c.get("/api/skills/active-directory-kerberos-attacks").json()
    print(f"  {d['name']}")
    print(f"  phase={d['phase']} domains={d['domains']} risk={d['risk']}")
    print(f"  requires={d['requires']} 闭包={d['dependency_closure']}")
    print(f"  元数据 {d['estimated_meta_tokens']} tok | 正文 {d['estimated_body_tokens']} tok")

    show("7. 过滤与检索")
    for params in ({"domain": "ad"}, {"phase": "post"}, {"q": "kerberos"}):
        d = c.get("/api/skills", params=params).json()
        print(f"  {params} → {d['total']} 条")

    show("8. 基准接口")
    info = c.get("/api/bench/info").json()
    print(f"  {info['total']} 条（计分 {info['scored']} / 弃权 {info['abstention']}）"
          f" 来源 {info['by_source']} 语言 {info['by_lang']}")
    m = c.post("/api/bench/run", json={"name": "api-smoke", "top_k": 5}).json()
    print(f"  R@1 {m['recall@1']} R@3 {m['recall@3']} R@5 {m['recall@5']} "
          f"MRR {m['mrr_stage1']}")
    print(f"  弃权 {m['abstention_correct']}/{m['abstention_total']} "
          f"({m['abstention_accuracy']}) 元数据节省 {m['meta_saving']:.1%}")
    print(f"  未命中 {len(m['failures'])} 条 | 误路由 {len(m['false_routes'])} 条")

    show("9. 错误路径")
    for desc, resp in (
        ("未知查询参数 scoring（建索引时参数）",
         c.post("/api/route", json={"query": "x", "scoring": "flat"})),
        ("top_k > recall_n", c.post("/api/route", json={"query": "x", "top_k": 50,
                                                        "recall_n": 5})),
        ("空查询", c.post("/api/route", json={"query": ""})),
        ("不存在的技能", c.get("/api/skills/no-such-skill")),
    ):
        detail = ""
        try:
            detail = str(resp.json().get("detail", ""))[:70]
        except Exception:
            pass
        print(f"  {desc:<34} → HTTP {resp.status_code} {detail}")

    print("\n" + "=" * 78)
    print("端到端验证完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
