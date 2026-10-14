"""路由质量探针——用一组代表性查询观察真实召回情况。

用途：在构建 SkillRoute-Bench 之前，先用少量探针查询定位路由失效模式。
**这不是正式评测**（无标注真值），而是诊断工具。

用法::

    .venv/Scripts/python backend/tools/probe_routing.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.skills.registry import SkillRegistry  # noqa: E402
from app.skills.router import RouterConfig, SkillRouter  # noqa: E402

#: 探针查询：(说明, 查询文本, 期望命中的技能名片段)
PROBES: list[tuple[str, str, list[str]]] = [
    ("中文·WordPress 后台", "目标是一个 WordPress 站点，我要找管理员登录入口", ["wordpress", "login", "401-403"]),
    ("中文·越权", "这个接口返回了别人的订单数据，帮我测试水平越权", ["bola", "authorization", "idor"]),
    ("中文·域渗透", "域环境里如何做 Kerberoasting 拿票据", ["kerberos", "active-directory"]),
    ("中文·SQL 注入", "登录框疑似存在 SQL 注入，怎么做报错注入", ["sqli", "sql-injection", "injection"]),
    ("中文·SSRF", "一个 URL 参数可能可以访问内网，测试 SSRF", ["ssrf"]),
    ("中文·文件上传", "上传头像的功能想绕过文件类型校验拿 shell", ["upload", "file-upload"]),
    ("英文·Kerberos", "Kerberoasting AD ticket attacks", ["kerberos", "active-directory"]),
    ("英文·BOLA", "API object level authorization testing", ["bola", "authorization"]),
    ("英文·upload", "bypass file upload restrictions to get RCE", ["upload"]),
]


def main() -> int:
    root = Path(os.path.expanduser("~")) / ".dsh" / "skills"
    if not root.exists():
        print(f"语料不存在: {root}", file=sys.stderr)
        return 1

    reg = SkillRegistry()
    reg.load_roots([("dsh", root)])
    reg.build_index(tokenizer="hybrid", vector_kind="lsa", n_components=64)
    router = SkillRouter(reg, RouterConfig(top_k=5, recall_n=30))

    st = reg.stats()
    print("=" * 78)
    print(f"技能库: {st['total']} 个 | 构建索引 {st['index_build_ms']:.0f} ms | "
          f"向量通道 {st['vector_channel']}")
    print(f"基线元数据开销: {st['baseline_meta_tokens']} token")
    print("=" * 78)

    hit_stats = {"total": 0, "hit": 0, "zh_total": 0, "zh_hit": 0}

    for label, query, expect in PROBES:
        res = router.route(query)
        names = [c.skill.name for c in res.candidates]
        matched_any = any(any(e in n for n in names) for e in expect)
        is_zh = label.startswith("中文")

        hit_stats["total"] += 1
        hit_stats["hit"] += int(matched_any)
        if is_zh:
            hit_stats["zh_total"] += 1
            hit_stats["zh_hit"] += int(matched_any)

        flag = "✓" if matched_any else "✗"
        print(f"\n[{flag}] {label}  <{query}>")
        print(f"    期望含: {expect}")
        for c in res.candidates:
            print(f"      {c.skill.name:38} {c.reason}")

    print("\n" + "=" * 78)
    print(f"命中期望技能片段的查询: {hit_stats['hit']}/{hit_stats['total']}")
    print(f"  其中中文查询: {hit_stats['zh_hit']}/{hit_stats['zh_total']}")
    print(f"  其中英文查询: {hit_stats['hit'] - hit_stats['zh_hit']}/"
          f"{hit_stats['total'] - hit_stats['zh_total']}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
