"""中英混合语料的轻量分词器。

**为什么不用 jieba？**
本课题的技能语料是中英混合、且包含大量安全术语（`SQLi`、`SSRF`、`越权`、
`Kerberoasting`）。引入 jieba 会带来三个问题：
1. 额外依赖，削弱研究核心的可复现性；
2. jieba 的通用词典对安全术语切分不佳（`反序列化`、`越权` 等）；
3. 领域词典维护成本高。

**替代方案**：ASCII 词 + CJK 字符二元组（bigram）。这是中文信息检索中
不依赖分词器的经典做法——字符 bigram 在中文检索上的效果接近分词，
且天然覆盖未登录词与领域术语（`越权` → `越权`，`反序列化` → `反序/序列/列化`）。

同时输出 CJK unigram 以提升短查询的召回（单个汉字查询仍可命中）。
"""

from __future__ import annotations

import re

#: ASCII 词：字母数字及安全领域常见符号（C++、C#、.NET、node.js、xss-filter）
_ASCII_RE = re.compile(r"[a-z0-9][a-z0-9_+#.\-]*")

#: CJK 统一表意文字（含扩展 A）与常用全角标点边界
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x3400 <= o <= 0x4DBF
        or 0x4E00 <= o <= 0x9FFF
        or 0xF900 <= o <= 0xFAFF
    )


def tokenize(text: str) -> list[str]:
    """把文本切成检索 token 列表。

    规则：
    - 统一小写；
    - ASCII 字母数字串整体作为一个 token；
    - CJK 连续串输出「单字 + 相邻二元组」；
    - 其余字符（空白、标点）作为分隔符丢弃。
    """
    if not text:
        return []

    text = text.lower()
    tokens: list[str] = []

    # 先摘出 ASCII 词，并把 CJK 替换为占位以便分段处理
    for m in _ASCII_RE.finditer(text):
        tokens.append(m.group(0))

    for m in _CJK_RE.finditer(text):
        run = m.group(0)
        if len(run) == 1:
            tokens.append(run)
            continue
        # 单字
        tokens.extend(run)
        # 相邻二元组
        for i in range(len(run) - 1):
            tokens.append(run[i : i + 2])

    return tokens


def tokenize_cjk_free(text: str) -> list[str]:
    """消融实验用：仅 ASCII 分词（**故意丢弃中文**）。

    用于量化「中文字符 bigram 策略」的贡献：若去掉中文后路由召回率大幅下降，
    即证明该切分策略是必要的（技能语料为中文为主）。
    """
    if not text:
        return []
    return [m.group(0) for m in _ASCII_RE.finditer(text.lower())]


def tokenize_bigram_only(text: str) -> list[str]:
    """消融实验用：CJK 仅 bigram、不输出 unigram。"""
    if not text:
        return []
    tokens = [m.group(0) for m in _ASCII_RE.finditer(text.lower())]
    for m in _CJK_RE.finditer(text.lower()):
        run = m.group(0)
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


#: 可切换的分词策略（供消融实验使用）
TOKENIZERS = {
    "hybrid": tokenize,
    "ascii_only": tokenize_cjk_free,
    "bigram_only": tokenize_bigram_only,
}
