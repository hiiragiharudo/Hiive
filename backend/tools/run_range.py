"""在真实靶场上端到端运行 Agent 引擎。

与 `run_lab.py` 的区别：`run_lab.py` 打的是**进程内模拟靶场**（离线、无网络），
本脚本打的是**XAMPP 上真实运行的 sqli-labs / DVWA / Pikachu**。

靶场需先就绪::

    .venv/Scripts/python eval/ranges/setup_ranges.py     # 初始化
    .venv/Scripts/python eval/ranges/probe_ranges.py     # 验证漏洞真实性

用法::

    .venv/Scripts/python backend/tools/run_range.py                      # 列出靶场
    .venv/Scripts/python backend/tools/run_range.py --range sqli-labs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.engine import AgentEngine  # noqa: E402
from app.agent.ranges import build_range, load_profiles  # noqa: E402

#: 每个靶场的推荐任务描述
QUERIES = {
    "sqli-labs": [
        "先做端点侦察，然后测试 GET 参数的 SQL 注入",
        "测试登录框的 SQL 注入与认证绕过",
        "SQL 注入 认证绕过 联合查询",
    ],
    "pikachu": [
        "先做端点侦察，然后测试 SQL 注入",
        "测试反射型 XSS",
    ],
    "dvwa": [
        "登录后测试 SQL 注入模块",
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", default="", help="靶场名；留空则列出全部")
    ap.add_argument("--query", default="", help="自定义任务描述")
    ap.add_argument("--max-steps", type=int, default=8)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--delay", type=float, default=0.2, help="请求间隔（秒），节流用")
    args = ap.parse_args()

    profiles = load_profiles()
    if not profiles:
        print("未找到靶场定义 eval/ranges/profiles.json", file=sys.stderr)
        return 2

    print("=" * 84)
    print("Hiive · 真实靶场挖洞验证")
    print("=" * 84)
    print(f"可用靶场 {len(profiles)} 个：")
    for name, p in profiles.items():
        ready = "✓ 就绪" if (p.skills_dir.exists() and p.plans_path.exists()) else "✗ 缺技能包"
        print(f"  {name:<12} {ready}  {p.label}")
        print(f"               {p.base_url}{'' if not p.login else '  （需登录）'}")

    if not args.range:
        print("\n用法: --range <名称>  [--query '自定义任务']")
        return 0

    if args.range not in profiles:
        print(f"\n未知靶场: {args.range}。可选: {', '.join(profiles)}", file=sys.stderr)
        return 2

    rt = build_range(profiles[args.range], delay=args.delay)
    print("\n" + "=" * 84)
    print(f"靶场: {rt.profile.label}")
    print("=" * 84)
    print(f"  技能 {len(rt.router.registry)} 个：{sorted(rt.router.registry.skills)}")
    print(f"  计划 {len(rt.plans)} 个")
    print(f"  目标 {rt.target.base_url}  节流 {rt.target.delay}s  超时 {rt.target.timeout}s")
    if rt.profile.login:
        print(f"  登录: {'✓ ' if rt.login_ok else '✗ '}{rt.login_detail}")
    for w in rt.warnings:
        print(f"  ⚠ {w}")

    queries = [args.query] if args.query else QUERIES.get(args.range, ["SQL 注入"])[:1]

    for q in queries:
        print("\n" + "-" * 84)
        print(f"【任务】{q}")
        print("-" * 84)
        eng = AgentEngine(rt.router, rt.plans, target=rt.target,
                          scope=rt.target.scope, max_steps=args.max_steps,
                          top_k=args.top_k)
        result = eng.run(q, task_id=f"{args.range}-run")

        print(f"  {result.graph.summary()}")
        print(f"  终止原因: {result.trace.terminated_reason}")

        print("\n  执行留痕：")
        for s in result.trace.steps:
            if s.outcome == "executed":
                mark = "✓ 已验证" if s.verified else "✗ 判据未过"
                print(f"    #{s.step} {s.skill:<32} {mark}")
                print(f"         路由依据: {s.route_reason}")
                print(f"         动作 {s.tool_calls} 次")
                for v in s.verify_results:
                    print(f"           [{'通过' if v.passed else '未过'}] {v.kind}: {v.detail}")
                if s.rejected_reason:
                    print(f"         拒绝原因: {s.rejected_reason}")
            else:
                print(f"    #{s.step} {s.skill:<32} 跳过 — {s.skipped_reason}")

        if result.graph.verified_findings:
            print("\n  ★ 经验证的发现：")
            for f in result.graph.verified_findings:
                print(f"    [{f.severity}] {f.kind} @ {f.asset}   (by {f.skill})")
                for e in f.evidence[:2]:
                    print(f"        证据: {e[:150]}")

        if result.graph.candidates:
            print("\n  被拒绝的候选：")
            for c in result.graph.candidates:
                print(f"    {c.kind} @ {c.asset} — {c.rejected_reason[:120]}")

        contrib = result.trace.contribution()
        if contrib:
            print("\n  技能贡献度：")
            for name, a in sorted(contrib.items(), key=lambda kv: -kv[1]["verified"]):
                print(f"    {name:<34} 执行 {a['executed']} 验证 {a['verified']} "
                      f"命中率 {a['hit_rate']:.2f}")

        print(f"\n  实际发出的请求 {len(result.tool.calls)} 次"
              f"（越界拦截 {result.tool.blocked_count} 次）")

    print("\n" + "=" * 84)
    print("说明：全部请求指向 localhost 本机靶场，不涉及任何线上目标。")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
