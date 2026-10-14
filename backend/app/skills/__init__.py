"""Hiive 技能引擎。

模块划分：

- ``models``    技能数据模型（元数据 / 正文 / 路由结果）
- ``parser``    `SKILL.md` 解析与元数据校验
- ``tokenize``  中英混合语料的轻量分词（CJK bigram + ASCII 词）
- ``bm25``      BM25 Okapi 检索通道（纯标准库）
- ``vectors``   TF-IDF 稀疏向量 + LSA 潜在语义通道
- ``fusion``    RRF 多通道融合
- ``registry``  技能注册表：加载 / 校验 / 建索引
- ``router``    ★ 两阶段技能路由器（本课题核心）
"""

from .bm25 import BM25Index
from .fusion import FusedResult, rrf_fuse
from .lexicon import CURATED, BilingualLexicon, LexiconStats
from .models import RouteCandidate, RouteResult, Skill, SkillMeta
from .parser import SkillParseError, parse_skill_file, validate_meta
from .registry import LoadReport, SkillRegistry
from .router import RouterConfig, SkillRouter
from .tokenize import tokenize

__all__ = [
    "BM25Index",
    "BilingualLexicon",
    "CURATED",
    "FusedResult",
    "LexiconStats",
    "LoadReport",
    "RouteCandidate",
    "RouteResult",
    "RouterConfig",
    "Skill",
    "SkillMeta",
    "SkillParseError",
    "SkillRegistry",
    "SkillRouter",
    "parse_skill_file",
    "rrf_fuse",
    "tokenize",
    "validate_meta",
]
