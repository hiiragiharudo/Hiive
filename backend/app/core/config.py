"""应用配置。

**不使用 pydantic-settings**：仅需环境变量读取，引入额外依赖不值得。
配置项全部有可用默认值，使服务开箱可跑；生产/他人复现时用环境变量覆盖。

## index-time vs query-time 参数（重要）

| 类别 | 参数 | 说明 |
|---|---|---|
| **建索引时** | `skill_roots`、`lexicon_path`、`enrich_triggers`、`vector_kind`、`tokenizer` | 改动需**重建索引**（`POST /api/skills/reload`） |
| **查询时** | `top_k`、`recall_n`、`state_phase`、`expand_query`、`channels`、`min_coverage` | 可按请求覆盖，无需重建 |

API 层必须向前端明确这一区分，否则演示时会出现"改了开关却没反应"的困惑。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _flag(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    """运行配置。"""

    # ---- 语料（建索引时） ----
    #: 技能根目录，多个用 os.pathsep 分隔
    skill_roots: list[tuple[str, Path]] = field(default_factory=list)
    #: 自动挖掘的双语词典（可空）
    lexicon_path: Path | None = None
    #: 是否把词典反查得到的术语并入 `triggers`（索引侧富化）
    #:
    #: **默认 False——依据实测**：富化与查询侧扩展**都作用于 `triggers` 字段**，
    #: 是替代品而非互补品。SkillRoute-Bench 实测（`tools/run_bench.py`）：
    #: - 查询扩展 OFF 时，富化显著有益：R@5 .658 → .789
    #: - 查询扩展 ON  时，富化**略微有害**：R@5 .842 → .803
    #:
    #: 由于默认开启了查询扩展（更有效且查询期开销可忽略），故富化默认关闭。
    #: 若要对比两种机制，用 `HIIVE_ENRICH_TRIGGERS=1` 打开后 `POST /api/skills/reload`。
    enrich_triggers: bool = False
    #: 是否并入自动挖掘层（实测其边际贡献为负，默认关闭）
    lexicon_include_mined: bool = False

    # ---- 检索（建索引时） ----
    tokenizer: str = "hybrid"
    vector_kind: str = "lsa"
    n_components: int = 64
    #: `fielded`（默认，消除文档长度偏置）或 `flat`（消融基线）
    scoring: str = "fielded"

    # ---- 检索（查询时默认值） ----
    top_k: int = 5
    recall_n: int = 50
    expand_query: bool = True
    channels: tuple[str, ...] = ("bm25",)
    min_coverage: float = 0.0
    phase_bonus: float = 0.004

    # ---- 服务 ----
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])

    @classmethod
    def from_env(cls) -> "Settings":
        s = cls()

        raw_roots = os.environ.get("HIIVE_SKILL_ROOTS")
        if raw_roots:
            roots: list[tuple[str, Path]] = []
            for i, part in enumerate(raw_roots.split(os.pathsep)):
                part = part.strip()
                if part:
                    roots.append((f"root{i}", Path(part)))
            s.skill_roots = roots
        else:
            s.skill_roots = [("dsh", Path(os.path.expanduser("~")) / ".dsh" / "skills")]

        lex = os.environ.get("HIIVE_LEXICON")
        if lex:
            s.lexicon_path = Path(lex)
        else:
            cand = Path(__file__).resolve().parent.parent.parent.parent / "data" / "lexicon_mined.json"
            s.lexicon_path = cand if cand.exists() else None

        s.enrich_triggers = _flag("HIIVE_ENRICH_TRIGGERS", s.enrich_triggers)
        s.lexicon_include_mined = _flag("HIIVE_LEXICON_INCLUDE_MINED", s.lexicon_include_mined)
        s.expand_query = _flag("HIIVE_EXPAND_QUERY", s.expand_query)

        s.tokenizer = os.environ.get("HIIVE_TOKENIZER", s.tokenizer)
        s.vector_kind = os.environ.get("HIIVE_VECTOR_KIND", s.vector_kind)
        s.scoring = os.environ.get("HIIVE_SCORING", s.scoring)
        s.n_components = int(os.environ.get("HIIVE_N_COMPONENTS", s.n_components))
        s.top_k = int(os.environ.get("HIIVE_TOP_K", s.top_k))
        s.recall_n = int(os.environ.get("HIIVE_RECALL_N", s.recall_n))
        s.min_coverage = float(os.environ.get("HIIVE_MIN_COVERAGE", s.min_coverage))
        s.phase_bonus = float(os.environ.get("HIIVE_PHASE_BONUS", s.phase_bonus))

        chans = os.environ.get("HIIVE_CHANNELS")
        if chans:
            s.channels = tuple(c.strip() for c in chans.split(",") if c.strip())

        s.host = os.environ.get("HIIVE_HOST", s.host)
        s.port = int(os.environ.get("HIIVE_PORT", s.port))

        cors = os.environ.get("HIIVE_CORS_ORIGINS")
        if cors:
            s.cors_origins = [c.strip() for c in cors.split(",") if c.strip()]
        return s

    def index_signature(self) -> dict:
        """影响索引构建的参数快照——用于前端提示"这些参数改动需重建索引"。"""
        return {
            "skill_roots": [str(p) for _l, p in self.skill_roots],
            "tokenizer": self.tokenizer,
            "vector_kind": self.vector_kind,
            "n_components": self.n_components,
            "scoring": self.scoring,
            "enrich_triggers": self.enrich_triggers,
            "lexicon_include_mined": self.lexicon_include_mined,
            "lexicon_path": str(self.lexicon_path) if self.lexicon_path else None,
        }

    def query_defaults(self) -> dict:
        """查询时参数的默认值快照。"""
        return {
            "top_k": self.top_k,
            "recall_n": self.recall_n,
            "expand_query": self.expand_query,
            "channels": list(self.channels),
            "min_coverage": self.min_coverage,
            "phase_bonus": self.phase_bonus,
        }


#: 哪些查询参数可在请求中覆盖（API 层据此校验并告知前端）
QUERY_TIME_OVERRIDABLE = (
    "top_k", "recall_n", "state_phase", "expand_query",
    "channels", "weights", "min_coverage", "min_score", "phase_bonus",
)

#: 哪些参数属于建索引时（改动需 reload）
INDEX_TIME_PARAMS = (
    "skill_roots", "tokenizer", "vector_kind", "n_components",
    "scoring", "enrich_triggers", "lexicon_include_mined", "lexicon_path",
)
