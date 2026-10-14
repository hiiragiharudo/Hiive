"""在实验靶场上端到端运行 Agent 引擎。

**离线、确定性、零成本**：靶场是进程内模拟（无网络 IO），验证判据是确定性求值
（无 LLM 调用）。因此本脚本可在任何机器上重复得到相同结果。

用法::

    .venv/Scripts/python backend/tools/run_lab.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.engine import AgentEngine, load_plans  # noqa: E402
from app.agent.scope import Scope  # noqa: E402
from app.skills.registry import SkillRegistry  # noqa: E402
from app.skills.router import RouterConfig, SkillRouter  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
LAB_SKILLS = REPO / "eval" / "lab" / "skills"
LAB_PLANS = REPO / "eval" / "lab" / "plans.json"

SCENARIOS: list[tuple[str, str]] = [
    ("S1 常规任务", "对目标做端点枚举，然后测试接口的水平越权和后台访问控制绕过"),
    ("S2 假阳性抑制", "测试搜索框的 SQL 注入"),
    ("S3 多技能并发面", "端点枚举 水平越权 目录遍历 反射型 XSS 文件上传"),
    ("S4 越界拦截", "端点枚举并测试所有接口"),
]


def main() -> int:
    if not LAB_SKILLS.exists() or not LAB_PLANS.exists():
        print("实验靶场不存在", file=sys.stderr)
        return 1

    reg = SkillRegistry()
    reg.load_roots([("lab", LAB_SKILLS)])
    reg.build_index(vector_kind="tfidf")
    router = SkillRouter(reg, RouterConfig(top_k=3, recall_n=10))
    plans = load_plans(LAB_PLANS)

    print("=" * 88)
    print("Hiive Agent 引擎 · 实验靶场端到端运行")
    print("=" * 88)
    print(f"靶场技能 {len(reg)} 个 ｜ 执行计划 {len(plans)} 个 ｜ "
          f"靶场主机 {router.registry.skills and ''}lab.local（进程内模拟，无网络 IO）")
    print("验证方式：确定性判据求值（不调用 LLM）")

    total_verified = total_rejected = total_blocked = 0

    for label, query in SCENARIOS:
        # S4 故意把作用域设错，用于演示越界拦截
        scope = (
            Scope(hosts=["not-the-lab.local"])
            if "越界" in label
            else Scope(hosts=["lab.local"])
        )
        eng = AgentEngine(router, plans, scope=scope, max_steps=10, top_k=5)
        r = eng.run(query, task_id=label.split()[0])

        print("\n" + "-" * 88)
        print(f"【{label}】 {query}")
        print("-" * 88)
        print(f"  攻击图：{r.graph.summary()}")
        print(f"  终止原因：{r.trace.terminated_reason}")
        print(f"  路由：{len(r.routings)} 次")

        print("\n  执行留痕（回溯）：")
        for s in r.trace.steps:
            if s.outcome == "executed":
                mark = "✓ 已验证" if s.verified else "✗ 判据未过"
                print(f"    #{s.step} {s.skill:<32} {mark}")
                print(f"         路由依据：{s.route_reason}")
                print(f"         动作 {s.tool_calls} 次 | 注入成本 {s.cost_tokens} token")
                for v in s.verify_results:
                    print(f"           [{ '通过' if v.passed else '未过' }] {v.kind}: {v.detail}")
                if s.rejected_reason:
                    print(f"         拒绝原因：{s.rejected_reason}")
            else:
                print(f"    #{s.step} {s.skill:<32} 跳过（{s.outcome}）")
                print(f"         {s.skipped_reason}")

        if r.graph.verified_findings:
            print("\n  ★ 经验证的发现：")
            for f in r.graph.verified_findings:
                print(f"    [{f.severity}] {f.kind} @ {f.asset}  (by {f.skill})")
                for e in f.evidence[:2]:
                    print(f"        证据：{e}")

        if r.graph.candidates:
            print("\n  被拒绝的候选（未通过验证门控）：")
            for c in r.graph.candidates:
                print(f"    {c.kind} @ {c.asset} (by {c.skill})")
                print(f"        原因：{c.rejected_reason}")

        contrib = r.trace.contribution()
        if contrib:
            print("\n  技能贡献度（回溯统计）：")
            print(f"    {'技能':<34}{'执行':>5}{'验证':>5}{'命中率':>8}{'调用':>5}")
            for name, a in sorted(contrib.items(), key=lambda kv: -kv[1]["verified"]):
                print(f"    {name:<34}{a['executed']:>5}{a['verified']:>5}"
                      f"{a['hit_rate']:>8.2f}{a['tool_calls']:>5}")

        if r.tool.blocked_count:
            print(f"\n  ⚠️ 作用域拦截 {r.tool.blocked_count} 次（架构级防护，非提示词约束）")

        total_verified += len(r.graph.verified_findings)
        total_rejected += len(r.graph.candidates)
        total_blocked += r.tool.blocked_count

    print("\n" + "=" * 88)
    print("汇总")
    print("=" * 88)
    print(f"  经验证发现 {total_verified} 个 ｜ 被拒绝候选 {total_rejected} 个 ｜ "
          f"越界拦截 {total_blocked} 次")
    print("\n  说明：'经验证发现' 必须通过确定性判据；技能声称有问题但判据未过的一律")
    print("        计入 '被拒绝候选'，不计入发现——这是抑制误报的系统层机制。")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
