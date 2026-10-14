"""两阶段技能路由器 —— 本课题的核心模块。

**阶段一（召回）**：以用户任务描述（可选叠加当前渗透阶段）为查询，
在 BM25 与向量两个通道上分别检索，用 RRF 融合，得到 top-``recall_n`` 候选。
此阶段**不向上下文注入任何技能内容**——索引常驻内存，不进 prompt。

**阶段二（按需加载）**：截取 top-``top_k``，仅把这些技能的元数据与**正文**
注入上下文。

对照基线是 agentskills.io 的现行做法：**全部技能的元数据常驻上下文**。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .fusion import rrf_fuse
from .models import RouteCandidate, RouteResult, Skill
from .registry import SkillRegistry

#: 可在阶段一启用的检索通道
ALL_CHANNELS = ("bm25", "vector")


@dataclass
class RouterConfig:
    """路由器配置。

    这些字段同时也是**消融实验的自变量**（见 ``eval/ablation.py``）：
    改变 ``channels``、``top_k``、``phase_bonus``、``tokenizer``、``vector_kind``
    即可得到对照实验的各组配置。
    """

    recall_n: int = 30
    top_k: int = 5
    channels: tuple[str, ...] = ALL_CHANNELS
    rrf_k: int = 60
    weights: dict[str, float] | None = None

    #: 是否利用当前渗透阶段作为先验（分阶段动态路由）
    use_phase_prior: bool = True
    #: 阶段匹配时叠加到 RRF 得分上的奖励（0 表示关闭）
    phase_bonus: float = 0.004

    #: 是否启用跨语言查询扩展（中文查询 -> 追加英文等价词）。
    #: 需 registry 已 attach_lexicon；见 lexicon.py。
    expand_query: bool = True
    #: 是否启用索引侧触发词富化（须在 build_index 前 attach_lexicon）
    enrich_triggers: bool = True

    tokenizer: str = "hybrid"
    vector_kind: str = "lsa"

    def validate(self) -> None:
        bad = [c for c in self.channels if c not in ALL_CHANNELS]
        if bad:
            raise ValueError(f"未知检索通道: {bad}；允许 {ALL_CHANNELS}")
        if self.top_k <= 0:
            raise ValueError("top_k 必须为正数")
        if self.recall_n < self.top_k:
            raise ValueError(f"recall_n({self.recall_n}) 不得小于 top_k({self.top_k})")


class SkillRouter:
    """两阶段技能路由器。"""

    def __init__(self, registry: SkillRegistry, config: RouterConfig | None = None) -> None:
        self.registry = registry
        self.config = config or RouterConfig()
        self.config.validate()
        self._field_tokens: dict[str, dict[str, set[str]]] = {}
        self._build_field_tokens()

    # ------------------------------------------------------------ 解释性

    def _build_field_tokens(self) -> None:
        """为每个技能建立「字段 -> token 集合」，用于生成路由依据说明。"""
        from .tokenize import TOKENIZERS

        tokfn = TOKENIZERS[self.config.tokenizer]
        self._field_tokens = {}
        for name, skill in self.registry.skills.items():
            m = skill.meta
            self._field_tokens[name] = {
                "name": set(tokfn(m.name)),
                "description": set(tokfn(m.description)),
                "triggers": set(tokfn(" ".join(m.triggers))),
                "targets": set(tokfn(" ".join(m.targets))),
                "domains": set(tokfn(" ".join(m.domains))),
                "tools": set(tokfn(" ".join(m.tools))),
            }

    _FIELD_LABELS = {
        "name": "技能名",
        "triggers": "触发词",
        "description": "描述",
        "targets": "适用目标",
        "domains": "领域",
        "tools": "工具",
        "flat": "全文",
    }
    _FIELD_ORDER = ("name", "triggers", "targets", "description", "domains", "tools")

    def _explain(
        self,
        skill: Skill,
        query_tokens: list[str],
        field_scores: dict[str, float] | None = None,
    ) -> tuple[list[str], str]:
        """生成可读的路由依据。

        优先使用检索时记录的**分字段得分**（可显示每个字段的归一化贡献），
        在 BM25 通道被关闭时退化为 token 交集判断。
        """
        field_scores = field_scores or {}
        matched = [f for f in self._FIELD_ORDER if field_scores.get(f)]

        if not matched:
            ft = self._field_tokens.get(skill.name, {})
            qset = set(query_tokens)
            matched = [f for f in self._FIELD_ORDER if qset & ft.get(f, set())]

        if matched:
            parts = []
            for f in matched:
                label = self._FIELD_LABELS[f]
                parts.append(f"{label}({field_scores[f]:.2f})" if f in field_scores else label)
            reason = "命中 " + "、".join(parts)
        elif skill.meta.domains:
            reason = "语义相近（潜在语义空间召回）"
        else:
            reason = "弱相关"
        return matched, reason

    # ------------------------------------------------------------ 路由

    def route(
        self,
        query: str,
        state_phase: str = "",
        top_k: int | None = None,
    ) -> RouteResult:
        """执行两阶段路由。

        参数
        ----
        query
            用户任务描述，例如「目标是一个 WordPress 站点，我要找管理员入口」。
        state_phase
            当前渗透阶段（``recon``/``discovery``/``exploitation``/``post``），
            用于阶段先验。空字符串表示不启用。
        top_k
            覆盖配置中的 top_k。
        """
        if self.registry.bm25 is None or self.registry.vector is None:
            raise RuntimeError("索引未构建，请先调用 registry.build_index()")

        cfg = self.config
        k = top_k if top_k is not None else cfg.top_k
        if k > cfg.recall_n:
            raise ValueError(f"top_k({k}) 超过 recall_n({cfg.recall_n})，请提高 recall_n")

        result = RouteResult(
            query=query,
            top_k=k,
            library_size=len(self.registry),
            retrieval_channels=list(cfg.channels),
            state_phase=state_phase,
        )

        # ---------------- 跨语言查询扩展（查询侧） ----------------
        retrieval_query = query
        if cfg.expand_query and self.registry.lexicon is not None:
            retrieval_query, expansion = self.registry.lexicon.expand_query(query)
            result.query_expansion = expansion
            result.retrieval_query = retrieval_query

        # ---------------- 阶段一：多通道召回 + RRF 融合 ----------------
        t0 = time.perf_counter()

        channel_results: dict[str, list[tuple[str, float]]] = {}
        bm25_field_scores: dict[str, dict[str, float]] = {}
        if "bm25" in cfg.channels:
            hits, bm25_field_scores = self.registry.search_bm25_detail(
                retrieval_query, top_n=cfg.recall_n
            )
            channel_results["bm25"] = hits
        if "vector" in cfg.channels:
            channel_results["vector"] = self.registry.search_vector(
                retrieval_query, top_n=cfg.recall_n
            )

        fused = rrf_fuse(channel_results, k=cfg.rrf_k, weights=cfg.weights)
        if not fused:
            result.timing_ms["stage1"] = (time.perf_counter() - t0) * 1000.0
            return result

        # 阶段先验：当前渗透阶段与技能声明阶段一致时给予奖励
        if cfg.use_phase_prior and state_phase and cfg.phase_bonus:
            for fr in fused:
                sk = self.registry.get(fr.doc_id)
                if sk is not None and sk.meta.phase == state_phase:
                    fr.rrf_score += cfg.phase_bonus
            fused.sort(key=lambda r: (-r.rrf_score, r.doc_id))

        result.stage1_recall = len(fused)
        result.stage1_ranking = [fr.doc_id for fr in fused]
        result.timing_ms["stage1"] = (time.perf_counter() - t0) * 1000.0

        # ---------------- 阶段二：按需加载 top-k 正文 ----------------
        t1 = time.perf_counter()

        from .tokenize import TOKENIZERS

        query_tokens = TOKENIZERS[cfg.tokenizer](retrieval_query)

        injected_meta = 0
        body_tokens = 0
        for fr in fused[:k]:
            skill = self.registry.get(fr.doc_id)
            if skill is None:
                continue
            matched, reason = self._explain(
                skill, query_tokens, bm25_field_scores.get(skill.name)
            )
            injected_meta += skill.estimated_meta_tokens()
            body_tokens += skill.estimated_body_tokens()
            result.candidates.append(
                RouteCandidate(
                    skill=skill,
                    score=fr.rrf_score,
                    bm25_score=fr.channel_scores.get("bm25", 0.0),
                    vector_score=fr.channel_scores.get("vector", 0.0),
                    bm25_rank=fr.channel_ranks.get("bm25"),
                    vector_rank=fr.channel_ranks.get("vector"),
                    matched_fields=matched,
                    reason=reason,
                )
            )

        # ---- 成本模型（同等 k 的保守对照，详见 RouteResult 文档） ----
        result.baseline_meta_tokens = self.registry.baseline_tokens()
        result.injected_meta_tokens = injected_meta
        result.body_tokens = body_tokens
        result.baseline_tokens = result.baseline_meta_tokens + body_tokens
        result.injected_tokens = injected_meta + body_tokens

        result.timing_ms["stage2"] = (time.perf_counter() - t1) * 1000.0
        return result

    # ------------------------------------------------------------ 辅助

    def dependency_closure(self, names: list[str]) -> tuple[list[str], list[str]]:
        """按 ``requires`` 展开技能依赖闭包（拓扑序）。

        这是「编排」能力的核心：技能声明 ``requires`` 后，路由器可自动补齐
        前置技能。返回 ``(有序技能名, 检测到的循环依赖)``。
        """
        ordered: list[str] = []
        visiting: set[str] = set()
        done: set[str] = set()
        cycles: list[str] = []

        def visit(name: str) -> None:
            if name in done:
                return
            if name in visiting:
                cycles.append(name)
                return
            skill = self.registry.get(name)
            if skill is None:
                done.add(name)
                return
            visiting.add(name)
            for dep in skill.meta.requires:
                visit(dep)
            visiting.discard(name)
            done.add(name)
            ordered.append(name)

        for n in names:
            visit(n)
        return ordered, cycles

    def validate_dependencies(self) -> dict[str, list[str]]:
        """检查全部技能的 ``requires`` 是否都存在于技能库中。"""
        missing: dict[str, list[str]] = {}
        for name, skill in self.registry.skills.items():
            absent = [d for d in skill.meta.requires if d not in self.registry]
            if absent:
                missing[name] = absent
        return missing
