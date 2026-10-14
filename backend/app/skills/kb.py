"""知识库文档的接入。

## 为什么知识库文档可以当作技能处理

本机知识库（`知识库/*.md`，49 篇）是**按漏洞类组织的方法论文档**
（`idor-test.md`、`http-smuggling-test.md` …）。它与"技能"在用途上完全同构：

- 都是**按需加载**的方法论（不是始终生效的约束——那是 `app/rules` 的职责）；
- 都以 Markdown 组织，可渐进披露；
- 都只描述"怎么做"，不描述"不许怎么做"。

区别只在**格式**：技能有 `SKILL.md` 的 YAML frontmatter，知识库文档没有。
因此本模块把知识库文档**合成为 Skill 对象**，从而无需为它单独造一套检索/路由。

## 元数据来源

知识库文档无 frontmatter，故元数据全部**推断**：

| 字段 | 来源 |
|---|---|
| `name` | 文件名去扩展名（`idor-test`） |
| `title` | 正文首个 `# ` 标题 |
| `description` | 标题 + 首个实质段落 |
| `domains` / `phase` / `targets` / `triggers` | 复用 `app/skills/metadata.py` 的规则推断 |

这条路径同时构成对 M2 元数据推断的一次**跨语料检验**：
推断规则是在技能语料上调出来的，把它用到形态完全不同的知识库上，
可以观察泛化性（见 `tools/run_kb.py`）。

## 已知取舍

合成的 `description` 由标题与首段拼成，**质量低于人工撰写的技能描述**。
这会影响路由召回——须在跨语料评测中如实报告，而不是假设"能加载就等于能用"。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .metadata import infer_skill
from .models import Skill, SkillMeta

_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


@dataclass
class KbLoadReport:
    """知识库加载报告。"""

    loaded: int = 0
    skipped: int = 0
    errors: list[tuple[str, str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> dict:
        return {
            "loaded": self.loaded,
            "skipped": self.skipped,
            "errors": [{"path": p, "error": e} for p, e in self.errors],
        }


def _first_heading(text: str) -> str:
    m = _H1_RE.search(text)
    return m.group(1).strip() if m else ""


def _first_paragraph(text: str) -> str:
    """首个实质段落：跳过引用块（约束性提示）、标题、空行。"""
    body = _CODE_RE.sub("", text)
    for raw in body.splitlines():
        s = raw.strip()
        if not s or s.startswith(("#", ">", "-", "*", "|", "```")):
            continue
        return s
    return ""


def synthesize_description(name: str, text: str) -> str:
    """为无 frontmatter 的知识库文档合成 `description`。

    路由的质量**高度依赖 `description`**（见技术设计文档 §6.9），
    因此这里明确记录合成规则，便于在跨语料评测中定位召回失败的原因。
    """
    title = _first_heading(text)
    para = _first_paragraph(text)
    parts = [p for p in (title, para) if p]
    desc = "。".join(parts) if parts else name
    return desc[:600]


def doc_to_skill(path: Path, source: str = "kb") -> Skill:
    """把一篇知识库 Markdown 转成 `Skill`。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    name = path.stem
    meta = SkillMeta(
        name=name,
        description=synthesize_description(name, text),
        source=source,
        dir_path=str(path.parent),
    )
    skill = Skill(meta=meta, body=text.strip(), body_lines=len(text.splitlines()))

    # 复用技能语料上调出的规则推断（跨语料检验）
    inferred = infer_skill(skill)
    meta.domains = inferred.domains
    meta.phase = inferred.phase
    meta.targets = inferred.targets
    meta.triggers = inferred.triggers
    meta.risk = inferred.risk
    return skill


def load_kb_docs(root: Path, source: str = "kb") -> tuple[list[Skill], KbLoadReport]:
    """加载一个知识库根目录下的全部 `*.md`。"""
    report = KbLoadReport()
    skills: list[Skill] = []
    if not root.exists():
        report.errors.append((str(root), "路径不存在"))
        return skills, report

    for path in sorted(root.glob("*.md")):
        try:
            skill = doc_to_skill(path, source=source)
        except OSError as e:
            report.errors.append((str(path), str(e)))
            continue
        if not skill.body.strip() or skill.body_chars < 200:
            # 过短的文档承载不了方法论，加载进来只会稀释路由候选
            report.skipped += 1
            continue
        skills.append(skill)
        report.loaded += 1
    return skills, report
