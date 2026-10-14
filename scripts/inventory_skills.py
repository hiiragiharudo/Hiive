#!/usr/bin/env python3
"""扫描本机渗透技能语料，产出结构化清单。

用途：
  1. 为毕业设计开题报告提供「研究基础 / 语料规模」的可验证证据；
  2. 作为 Hiive 技能引擎（skill engine）的语料导入前置步骤。

产出：docs/技能资产清单.md  与  data/skill_catalog.json

用法：
  python scripts/inventory_skills.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

# ---------------------------------------------------------------- 语料根目录

HOME = Path(os.path.expanduser("~"))

#: 语料来源：(标签, 根路径, 说明)
SOURCES: list[tuple[str, Path, str]] = [
    ("dsh", HOME / ".dsh" / "skills", "DSH 技能库（本机 Agent 运行时）"),
    ("clown", Path("H:/渗透skill/src-6k-skill/clown-src-6k-skill"), "自建 Agent 身份包"),
    ("src6k", Path("H:/渗透skill/src-6k-skill"), "SRC 6K 技能集"),
    ("reports", Path("H:/渗透skill/上千份SRC报告"), "真实 SRC 漏洞报告语料"),
]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class Skill:
    """一个技能条目。"""

    name: str = ""
    description: str = ""
    source: str = ""
    path: str = ""
    rel_dir: str = ""
    body_lines: int = 0
    bytes: int = 0
    assets: list[str] = field(default_factory=list)  # 附带脚本/参考文件

    @property
    def dir_name(self) -> str:
        return Path(self.path).parent.name


def parse_frontmatter(text: str) -> dict[str, str]:
    """极简 YAML frontmatter 解析：只取顶层 `key: value` 标量。

    不引入 PyYAML 依赖，因为技能 frontmatter 结构固定且简单。
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    lines = m.group(1).splitlines()
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0].isspace():  # 嵌套字段（如 metadata.xxx）暂不处理
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        key = k.strip()
        val = v.strip()

        # 块标量：`>`/`>-`（折叠，块内换行折叠为空格） 与 `|`/`|-`（字面，保留换行）
        if val in (">", ">-", ">+", "|", "|-", "|+"):
            folded = val.startswith(">")
            block: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and not nxt[0].isspace():
                    break  # 回到顶层键，块结束
                block.append(nxt.strip())
                i += 1
            joiner = " " if folded else "\n"
            out[key] = joiner.join(x for x in block if x).strip()
            continue

        out[key] = val.strip("'\"")
    return out


def collect_skill_file(p: Path, source: str, root: Path) -> Skill | None:
    """把一个 SKILL.md 解析为 Skill 对象。"""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    fm = parse_frontmatter(text)
    parent = p.parent

    # 收集 payload / 脚本 / 参考文件
    assets: list[str] = []
    for sub in sorted(parent.rglob("*")):
        if sub.is_file() and sub.name != "SKILL.md":
            try:
                assets.append(str(sub.relative_to(parent)))
            except ValueError:
                assets.append(sub.name)

    return Skill(
        name=fm.get("name", parent.name),
        description=fm.get("description", ""),
        source=source,
        path=str(p),
        rel_dir=str(parent.relative_to(root)) if _is_rel(parent, root) else parent.name,
        body_lines=len(text.splitlines()),
        bytes=len(text.encode("utf-8")),
        assets=assets[:50],
    )


def _is_rel(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def scan_source(label: str, root: Path) -> list[Skill]:
    if not root.exists():
        print(f"  [跳过] {label}: 路径不存在 {root}", file=sys.stderr)
        return []
    found: list[Skill] = []
    for p in sorted(root.rglob("SKILL.md")):
        s = collect_skill_file(p, label, root)
        if s:
            found.append(s)
    print(f"  [{label}] {root} -> {len(found)} 个技能", file=sys.stderr)
    return found


# ---------------------------------------------------------------- 统计辅助


def dir_stats(root: Path) -> tuple[int, float]:
    """返回 (文件数, MB)。"""
    if not root.exists():
        return 0, 0.0
    n = 0
    total = 0
    for p in root.rglob("*"):
        if p.is_file():
            n += 1
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return n, total / 1024 / 1024


def count_files(root: Path, pattern: str = "*") -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob(pattern) if p.is_file())


# ---------------------------------------------------------------- 报告渲染


def render_markdown(skills: list[Skill]) -> str:
    by_source: dict[str, list[Skill]] = {}
    for s in skills:
        by_source.setdefault(s.source, []).append(s)

    labels = {lbl: desc for lbl, _, desc in SOURCES}
    L: list[str] = []
    L.append("# 技能资产清单（自动生成）\n")
    L.append("> 由 `scripts/inventory_skills.py` 扫描本机语料生成，"
             "作为毕业设计「研究基础」与技能引擎语料导入的依据。\n")
    L.append(f"**技能条目总数：{len(skills)}**\n")

    # 总览表
    L.append("## 一、语料来源总览\n")
    L.append("| 来源标签 | 说明 | 技能条目 | 磁盘文件数 | 体积 |")
    L.append("|---|---|---:|---:|---:|")
    source_roots = {lbl: root for lbl, root, _ in SOURCES}
    for lbl, items in by_source.items():
        n, mb = dir_stats(source_roots[lbl])
        L.append(f"| `{lbl}` | {labels.get(lbl, '')} | {len(items)} | {n} | {mb:.1f} MB |")
    L.append("")

    # 真值补充：SRC 报告语料
    rpt = source_roots["reports"]
    if rpt.exists():
        L.append(f"另：真实 SRC 漏洞报告语料 `{rpt}` 共 "
                 f"**{count_files(rpt)}** 个文件。\n")

    # 明细
    for lbl, items in by_source.items():
        L.append(f"## 二、`{lbl}` 明细 —— {labels.get(lbl, '')}\n")
        L.append("| # | 技能名 | 描述 | 目录 | 正文行数 | 附带资产 |")
        L.append("|---:|---|---|---|---:|---:|")
        for i, s in enumerate(items, 1):
            desc = (s.description or "—").replace("|", "\\|")
            if len(desc) > 70:
                desc = desc[:70] + "…"
            L.append(
                f"| {i} | `{s.name}` | {desc} | `{s.rel_dir}` | "
                f"{s.body_lines} | {len(s.assets)} |"
            )
        L.append("")

    return "\n".join(L)


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    out_md = repo / "docs" / "技能资产清单.md"
    out_json = repo / "data" / "skill_catalog.json"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    print("正在扫描技能语料 …", file=sys.stderr)
    skills: list[Skill] = []
    for label, root, _desc in SOURCES:
        skills.extend(scan_source(label, root))

    out_md.write_text(render_markdown(skills), encoding="utf-8")
    out_json.write_text(
        json.dumps(
            {
                "total": len(skills),
                "sources": [
                    {
                        "label": lbl,
                        "root": str(root),
                        "description": desc,
                        "skill_count": sum(1 for s in skills if s.source == lbl),
                    }
                    for lbl, root, desc in SOURCES
                ],
                "skills": [asdict(s) | {"dir_name": s.dir_name} for s in skills],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n完成：{len(skills)} 个技能条目", file=sys.stderr)
    print(f"  -> {out_md}", file=sys.stderr)
    print(f"  -> {out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
