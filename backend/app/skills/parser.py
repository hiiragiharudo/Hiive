"""`SKILL.md` 解析器。

解析能力覆盖 agentskills.io 规范所需的最小子集，外加本课题扩展的路由元数据：

- 标量：``key: value``（自动去除包裹引号）
- 块标量：``key: >-``（折叠，换行转空格）与 ``key: |-``（字面，保留换行）
- 行内列表：``key: [a, b, c]``
- 破折号列表：``key:`` 后跟 ``- item``

**为什么不用 PyYAML？** 与 BM25 同理：schema 固定且简单，自己解析可避免
引入依赖、并能在解析阶段给出更精确的校验错误信息（例如指出第几行的字段非法）。
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import VALID_PHASES, VALID_RISKS, Skill, SkillMeta

_FRONTMATTER_RE = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)
_BLOCK_SCALARS = {">", ">-", ">+", "|", "|-", "|+"}


class SkillParseError(ValueError):
    """技能文件格式错误。"""


def split_frontmatter(text: str) -> tuple[str, str]:
    """返回 (frontmatter, body)。无 frontmatter 时返回 ("", text)。"""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end() :]


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def _parse_inline_list(v: str) -> list[str]:
    inner = v.strip()
    if not (inner.startswith("[") and inner.endswith("]")):
        return []
    inner = inner[1:-1].strip()
    if not inner:
        return []
    return [_strip_quotes(x) for x in inner.split(",") if x.strip()]


def parse_frontmatter(fm: str) -> dict[str, object]:
    """把 frontmatter 文本解析为字典。"""
    out: dict[str, object] = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0].isspace():  # 顶层之外的缩进行由上层键消费，此处忽略
            continue
        if ":" not in line:
            raise SkillParseError(f"frontmatter 行缺少冒号: {raw!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        value = rest.strip()

        # ---- 块标量 ----
        if value in _BLOCK_SCALARS:
            folded = value.startswith(">")
            block: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and not nxt[0].isspace():
                    break
                block.append(nxt.strip())
                i += 1
            joiner = " " if folded else "\n"
            out[key] = joiner.join(x for x in block if x).strip()
            continue

        # ---- 行内列表 ----
        if value.startswith("["):
            out[key] = _parse_inline_list(value)
            continue

        # ---- 破折号列表 ----
        if value == "":
            items: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                stripped = nxt.strip()
                if stripped.startswith("- "):
                    items.append(_strip_quotes(stripped[2:]))
                    i += 1
                elif not stripped:
                    i += 1
                else:
                    break
            out[key] = items if items else ""
            continue

        out[key] = _strip_quotes(value)

    return out


def parse_skill_file(path: Path, source: str = "") -> Skill:
    """解析单个 `SKILL.md`，返回 ``Skill``。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise SkillParseError(f"无法读取 {path}: {e}") from e

    fm_text, body = split_frontmatter(text)
    if not fm_text:
        raise SkillParseError(f"{path}: 缺少 YAML frontmatter")

    fm = parse_frontmatter(fm_text)

    name = fm.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SkillParseError(f"{path}: frontmatter 缺少必填字段 name")

    meta = SkillMeta(
        name=name.strip(),
        description=str(fm.get("description", "") or ""),
        domains=_as_list(fm.get("domains")),
        phase=str(fm.get("phase", "") or ""),
        targets=_as_list(fm.get("targets")),
        triggers=_as_list(fm.get("triggers")),
        requires=_as_list(fm.get("requires")),
        provides=_as_list(fm.get("provides")),
        tools=_as_list(fm.get("tools")),
        risk=str(fm.get("risk", "low") or "low").strip().lower(),
        source=source,
        dir_path=str(path.parent),
    )

    assets: list[str] = []
    for sub in sorted(path.parent.rglob("*")):
        if sub.is_file() and sub.name != "SKILL.md":
            try:
                assets.append(str(sub.relative_to(path.parent)))
            except ValueError:
                assets.append(sub.name)

    return Skill(
        meta=meta,
        body=body.strip(),
        assets=assets,
        body_lines=len(body.splitlines()),
    )


def _as_list(v: object) -> list[str]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()]


def validate_meta(meta: SkillMeta) -> list[str]:
    """校验技能元数据，返回问题列表（空列表表示通过）。"""
    problems: list[str] = []
    if not meta.name:
        problems.append("name 为空")
    if not meta.description:
        problems.append("description 为空——将无法被第一阶段检索命中")
    if len(meta.description) > 1024:
        problems.append(f"description 过长（{len(meta.description)} 字符，规范上限 1024）")
    if meta.phase and meta.phase not in VALID_PHASES:
        problems.append(f"phase 非法: {meta.phase!r}（允许 {VALID_PHASES}）")
    if meta.risk not in VALID_RISKS:
        problems.append(f"risk 非法: {meta.risk!r}（允许 {VALID_RISKS}）")
    return problems
