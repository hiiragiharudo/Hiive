"""技能数据模型。

本模块定义 Hiive 技能引擎的核心数据结构。设计原则：

- **纯标准库**：不引入任何第三方依赖，保证研究核心（检索路由）可零依赖测试与复现。
- **路由元数据与正文分离**：`SkillMeta` 是常驻内存/上下文的轻量元数据，
  `Skill.body` 是渐进披露的正文（仅在第二阶段按需加载）。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

#: 允许的渗透阶段（与 Kill Chain / 渗透流程对齐）
VALID_PHASES: tuple[str, ...] = ("recon", "discovery", "exploitation", "post", "report")

#: 允许的风险等级（决定是否需要人在环路审批）
VALID_RISKS: tuple[str, ...] = ("low", "medium", "high")


@dataclass
class SkillMeta:
    """技能的机器可读元数据——即技能路由的唯一依据。

    `name` 与 `description` 来自 agentskills.io 规范；其余字段是本课题为
    「可检索性」补充的路由元数据（见开题报告研究内容一）。
    """

    name: str
    description: str = ""

    # ---- 路由元数据（本课题扩展） ----
    domains: list[str] = field(default_factory=list)
    phase: str = ""
    targets: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    risk: str = "low"

    # ---- 溯源 ----
    source: str = ""
    dir_path: str = ""

    def routing_text(self) -> str:
        """构造用于第一阶段检索的文本表示。

        字段加权策略：通过**字段重复**实现加权（无需 fielded BM25 的复杂度）。
        `name` 与 `triggers` 是最强的意图信号，故重复两次。

        该函数的字段顺序与重复次数是**消融实验的自变量之一**——见
        `eval/ablation.py` 中 `routing_text_variant`。
        """
        parts = [
            self.name,
            self.name,
            self.description,
            " ".join(self.triggers),
            " ".join(self.triggers),
            " ".join(self.targets),
            " ".join(self.domains),
            self.phase,
            " ".join(self.tools),
        ]
        return " ".join(p for p in parts if p)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Skill:
    """一个完整技能：元数据 + 正文 + 附带资产。"""

    meta: SkillMeta
    body: str = ""
    assets: list[str] = field(default_factory=list)
    body_lines: int = 0

    # ---- 便利属性 ----
    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def description(self) -> str:
        return self.meta.description

    @property
    def body_chars(self) -> int:
        return len(self.body)

    def estimated_body_tokens(self) -> int:
        """正文 token 的粗略估算。

        中英混合语料下经验系数约 1.6 字符/token（英文约 4 字符/token，
        中文约 1 字符/token，技能正文以中文为主）。
        该估算用于成本对比，**不作为精确计量**，论文中须标注为估算方法。
        """
        return int(self.body_chars / 1.6)

    def estimated_meta_tokens(self) -> int:
        """元数据 token 的粗略估算——即 agentskills.io 规范下常驻上下文的部分。

        只计 ``name`` 与 ``description``（规范注入的内容），外加固定的
        列表/换行开销 8 token。**不含**本课题扩展的路由元数据，因为那些字段
        只存在于检索索引中，不进入上下文。
        """
        text = f"{self.meta.name}: {self.meta.description}"
        return int(len(text) / 1.6) + 8

    def injected_tokens(self) -> int:
        """两阶段架构下该技能被注入上下文的成本 = 元数据 + 正文。"""
        return self.estimated_meta_tokens() + self.estimated_body_tokens()

    def to_dict(self, include_body: bool = False) -> dict:
        d = self.meta.to_dict()
        d["body_lines"] = self.body_lines
        d["body_chars"] = self.body_chars
        d["assets"] = self.assets
        if include_body:
            d["body"] = self.body
        return d


@dataclass
class RouteCandidate:
    """路由候选：技能 + 各通道得分 + 融合得分。"""

    skill: Skill
    score: float = 0.0
    bm25_score: float = 0.0
    vector_score: float = 0.0
    bm25_rank: int | None = None
    vector_rank: int | None = None
    matched_fields: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self, include_body: bool = False) -> dict:
        return {
            "name": self.skill.name,
            "description": self.skill.description,
            "phase": self.skill.meta.phase,
            "domains": self.skill.meta.domains,
            "score": round(self.score, 6),
            "bm25_score": round(self.bm25_score, 4),
            "vector_score": round(self.vector_score, 4),
            "bm25_rank": self.bm25_rank,
            "vector_rank": self.vector_rank,
            "matched_fields": self.matched_fields,
            "reason": self.reason,
            "estimated_body_tokens": self.skill.estimated_body_tokens(),
            **({"body": self.skill.body} if include_body else {}),
        }


@dataclass
class RouteResult:
    """一次技能路由的完整结果——供前端「检索路由可视化」直接消费。

    ## 成本模型（必须诚实）

    朴素地比较「全量注入 vs 只注入 top-k 正文」是**误导性**的：真实技能正文动辄
    数百行，k 个正文的开销远大于全库元数据。因此本模型把成本拆成两项：

    - **元数据项**：随技能库规模 N 线性增长，是真正的瓶颈；
    - **正文项**：两种方案都需要读，规模由 k 决定。

    对照必须在**同等 k** 下进行（即假设基线方案也恰好选中同样 k 个技能——这对
    基线是最有利的假设，因而是保守比较）：

    | 方案 | 元数据项 | 正文项 |
    |---|---|---|
    | 基线（agentskills.io 全量注入） | ``N × meta`` | ``k × body`` |
    | 本课题（两阶段路由） | ``k × meta`` | ``k × body`` |

    故节省量恰为 ``(N − k) × meta``，**随技能库规模线性增长**——这才是本课题的
    论点，而不是"总 token 一定更少"。
    """

    query: str
    candidates: list[RouteCandidate] = field(default_factory=list)
    top_k: int = 0
    stage1_recall: int = 0
    library_size: int = 0

    #: 基线元数据开销 = N × meta（随库规模线性增长）
    baseline_meta_tokens: int = 0
    #: 本方案元数据开销 = k × meta
    injected_meta_tokens: int = 0
    #: top-k 正文开销——两种方案相同，单列以保证透明
    body_tokens: int = 0
    #: 两方案总上下文开销
    baseline_tokens: int = 0
    injected_tokens: int = 0

    retrieval_channels: list[str] = field(default_factory=list)
    state_phase: str = ""
    timing_ms: dict[str, float] = field(default_factory=dict)

    #: 跨语言查询扩展的命中项：[(中文术语, 追加的英文等价词), ...]
    query_expansion: list[tuple[str, str]] = field(default_factory=list)
    #: 实际用于检索的查询文本（含扩展追加内容）；等于原查询表示未扩展
    retrieval_query: str = ""

    #: 阶段一的完整融合排序（技能名，最多 recall_n 个）。
    #:
    #: **关键诊断字段**：区分"召回失败"与"排序失败"——
    #: 若期望技能出现在此列表中却不在 top-k，说明问题在**排序/融合**，加元数据无用；
    #: 若根本不在此列表中，才是**召回**问题。二者需要完全不同的修复方向。
    stage1_ranking: list[str] = field(default_factory=list)

    @property
    def token_saving_ratio(self) -> float:
        """总上下文开销的节省比例（同等 k 假设下）。"""
        if not self.candidates or self.baseline_tokens <= 0:
            return 0.0
        return 1.0 - self.injected_tokens / self.baseline_tokens

    @property
    def meta_saving_ratio(self) -> float:
        """**元数据项**的节省比例——本课题的核心指标。

        该指标不随技能正文长度变化，只随技能库规模 N 变化，因此是在固定语料下
        真正刻画「两阶段路由价值」的量。
        """
        if not self.candidates or self.baseline_meta_tokens <= 0:
            return 0.0
        return 1.0 - self.injected_meta_tokens / self.baseline_meta_tokens

    def to_dict(self, include_body: bool = False) -> dict:
        return {
            "query": self.query,
            "top_k": self.top_k,
            "stage1_recall": self.stage1_recall,
            "library_size": self.library_size,
            "state_phase": self.state_phase,
            "retrieval_channels": self.retrieval_channels,
            "cross_lingual": {
                "expanded": bool(self.query_expansion),
                "expansion": [
                    {"zh": zh, "en": en} for zh, en in self.query_expansion
                ],
                "retrieval_query": self.retrieval_query or self.query,
            },
            "cost": {
                "baseline_meta_tokens": self.baseline_meta_tokens,
                "injected_meta_tokens": self.injected_meta_tokens,
                "body_tokens": self.body_tokens,
                "baseline_tokens": self.baseline_tokens,
                "injected_tokens": self.injected_tokens,
                "token_saving_ratio": round(self.token_saving_ratio, 4),
                "meta_saving_ratio": round(self.meta_saving_ratio, 4),
            },
            "timing_ms": {k: round(v, 2) for k, v in self.timing_ms.items()},
            "candidates": [c.to_dict(include_body=include_body) for c in self.candidates],
        }
