"""中英安全术语对照挖掘器。

## 动机

路由实测发现**跨语言鸿沟**：本机技能库中 103 个细粒度子技能用英文描述，
而 5 个伞状技能用中文描述。中文查询的字面 token 无法命中英文描述，
实测中文查询命中率仅 2/6，英文查询 3/3。

## 方法

真实中文漏洞报告中大量存在「中文（ENGLISH）」或「ENGLISH（中文）」的对照写法
（如 `水平越权（IDOR）`、`服务端请求伪造（SSRF）`、`Kerberoasting（Kerberoasting 攻击）`）。
这为**自动、有据可查**地构建双语领域词典提供了天然矿脉——比纯人工编写更可复现，
且带频次证据。

## 语料

- 真实 SRC 漏洞报告库（DOCX 用标准库 zipfile+XML 抽取，无需第三方依赖）
- 本机技能库正文（Markdown）
- 中文安全文章汇编

## 输出

``data/lexicon_mined.json``——术语对及其频次与来源计数。
人工只需复核高频对，低频对可直接丢弃。

用法::

    .venv/Scripts/python backend/tools/mine_lexicon.py
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

# ------------------------------------------------------------------ 抽取文本

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\u00a0]+")


def docx_text(path: Path) -> str:
    """从 .docx 抽取纯文本（zipfile + XML，标准库实现）。"""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError, OSError):
        return ""
    xml = xml.replace("</w:p>", "\n")
    return _TAG_RE.sub("", xml)


def read_text(path: Path) -> str:
    """按扩展名抽取文本；不支持的类型返回空串。"""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return docx_text(path)
    if suffix in (".md", ".txt", ".html", ".htm"):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return _TAG_RE.sub("", raw) if suffix in (".html", ".htm") else raw
    return ""


# ------------------------------------------------------------------ 术语挖掘

#: 中文（ENGLISH）
ZH_EN = re.compile(
    r"([\u4e00-\u9fff]{2,14})\s*[（(]\s*([A-Za-z][A-Za-z0-9 ._/+#-]{1,40}?)\s*[）)]"
)
#: ENGLISH（中文）
EN_ZH = re.compile(
    r"([A-Za-z][A-Za-z0-9 ._/+#-]{1,40}?)\s*[（(]\s*([\u4e00-\u9fff]{2,14})\s*[）)]"
)

#: 英文侧必须含至少 2 个连续字母，且不得是纯数字/版本号
_EN_OK = re.compile(r"[A-Za-z]{2,}")

#: 中文侧停用词（避免把普通措辞当术语）
_ZH_STOP = {
    "详见", "参考", "注意", "说明", "以下", "如下", "如上", "详情", "版本",
    "第一步", "第二步", "第三步", "部分", "内容", "方式", "方法", "情况",
    "例如", "示例", "备注", "补充", "总结", "附录", "目录", "链接", "地址",
    "用户名", "密码", "时间", "日期", "作者", "标题", "类型",
}

#: 英文侧停用词
_EN_STOP = {
    "http", "https", "www", "com", "cn", "net", "org", "html", "php", "asp",
    "jsp", "aspx", "get", "post", "the", "and", "for", "with", "you", "your",
    "this", "that", "not", "are", "was", "were", "from", "have", "has",
}


def _clean_en(s: str) -> str:
    return " ".join(s.split()).strip(" .,;:-")


def _clean_zh(s: str) -> str:
    return " ".join(s.split()).strip()


def _accept_en(s: str) -> bool:
    s = s.strip()
    if len(s) < 2 or len(s) > 40:
        return False
    if not _EN_OK.search(s):
        return False
    if s.lower() in _EN_STOP:
        return False
    # 排除纯版本号/编号
    if re.fullmatch(r"[\d.\s]+", s):
        return False
    return True


def _accept_zh(s: str) -> bool:
    s = s.strip()
    if len(s) < 2 or len(s) > 14:
        return False
    if s in _ZH_STOP:
        return False
    return True


def mine_text(text: str, zh_en: Counter, en_zh: Counter) -> None:
    """从一段文本中挖掘术语对。"""
    for m in ZH_EN.finditer(text):
        zh, en = _clean_zh(m.group(1)), _clean_en(m.group(2))
        if _accept_zh(zh) and _accept_en(en):
            zh_en[(zh, en.lower())] += 1
    for m in EN_ZH.finditer(text):
        en, zh = _clean_en(m.group(1)), _clean_zh(m.group(2))
        if _accept_zh(zh) and _accept_en(en):
            en_zh[(en.lower(), zh)] += 1


# ------------------------------------------------------------------ 主流程

DEFAULT_CORPORA: list[tuple[str, Path]] = [
    ("src_reports", Path("H:/渗透skill/上千份SRC报告")),
    ("skills", Path.home() / ".dsh" / "skills"),
    ("hack_report", Path("H:/HackReport")),
    ("articles", Path("H:/Tools/1.7GB的SRC报告绝对是精品 不是烂大街的货色")),
]

SUPPORTED = {".md", ".txt", ".html", ".htm", ".docx"}


def main() -> int:
    repo = Path(__file__).resolve().parent.parent.parent
    out = repo / "data" / "lexicon_mined.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    zh_en: Counter = Counter()
    en_zh: Counter = Counter()
    src_counts: dict[str, int] = defaultdict(int)
    files_read = 0

    for label, root in DEFAULT_CORPORA:
        if not root.exists():
            print(f"[跳过] {label}: {root} 不存在", file=sys.stderr)
            continue
        n = 0
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in SUPPORTED:
                continue
            text = read_text(p)
            if not text:
                continue
            files_read += 1
            n += 1
            before = len(zh_en) + len(en_zh)
            mine_text(text, zh_en, en_zh)
            src_counts[label] += (len(zh_en) + len(en_zh)) - before
        print(f"[{label}] 读取 {n} 个文件", file=sys.stderr)

    # 合并两种模式（同一术语对可能两种写法都出现）
    merged: Counter = Counter()
    for (zh, en), c in zh_en.items():
        merged[(zh, en)] += c
    for (en, zh), c in en_zh.items():
        merged[(zh, en)] += c

    # 只保留出现 >= 2 次的（可要求更高，由调用方过滤）
    pairs = [
        {"zh": zh, "en": en, "count": c}
        for (zh, en), c in merged.most_common()
        if c >= 2
    ]

    payload = {
        "generated_from": [
            {"label": lbl, "root": str(root), "exists": root.exists()}
            for lbl, root in DEFAULT_CORPORA
        ],
        "files_read": files_read,
        "raw_pairs": len(merged),
        "kept_pairs": len(pairs),
        "min_count": 2,
        "pairs": pairs,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n读取文件 {files_read} 个，原始术语对 {len(merged)} 个，"
          f"保留(≥2次) {len(pairs)} 个")
    print(f"-> {out}")
    print("\n高频术语对 Top 40：")
    for p in pairs[:40]:
        print(f"  {p['count']:>5}  {p['zh']:<16} <-> {p['en']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
