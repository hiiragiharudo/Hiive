"""多通道结果融合。

采用 Reciprocal Rank Fusion（RRF，Cormack et al., SIGIR 2009）：

    RRF(d) = Σ_c  1 / (k + rank_c(d))

**为什么用 RRF 而不是加权分数求和？**
BM25 得分与余弦相似度的量纲完全不同（前者无上界、后者在 [-1,1]），
直接加权需要归一化，而归一化方式本身又是一个需要调参的自由度。
RRF 只用**排名**，无需归一化、无需调参，且是该领域的标准做法
（被 Elasticsearch、Azure AI Search 等生产系统采用）。

`k` 取 60 是 RRF 原论文与现代系统的默认经验值。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FusedResult:
    """融合后的单个文档结果。"""

    doc_id: str
    rrf_score: float
    channel_ranks: dict[str, int] = field(default_factory=dict)
    channel_scores: dict[str, float] = field(default_factory=dict)


def rrf_fuse(
    channels: dict[str, list[tuple[str, float]]],
    k: int = 60,
    weights: dict[str, float] | None = None,
    top_n: int | None = None,
) -> list[FusedResult]:
    """融合多个通道的排序结果。

    参数
    ----
    channels
        ``{"bm25": [(doc_id, score), ...], "vector": [...]}``，每个通道内部须已按得分降序。
    k
        RRF 平滑常数，默认 60。
    weights
        可选的通道权重（消融实验的自变量）。缺省视为等权。
    top_n
        截断长度。

    返回
    ----
    按 RRF 得分降序的 ``FusedResult`` 列表。
    """
    if weights is None:
        weights = {name: 1.0 for name in channels}

    acc: dict[str, FusedResult] = {}

    for name, ranked in channels.items():
        w = weights.get(name, 1.0)
        if w == 0.0:
            continue
        for rank, (doc_id, score) in enumerate(ranked, start=1):
            fr = acc.get(doc_id)
            if fr is None:
                fr = FusedResult(doc_id=doc_id, rrf_score=0.0)
                acc[doc_id] = fr
            fr.rrf_score += w * (1.0 / (k + rank))
            fr.channel_ranks[name] = rank
            fr.channel_scores[name] = score

    out = sorted(acc.values(), key=lambda r: (-r.rrf_score, r.doc_id))
    if top_n is not None:
        out = out[:top_n]
    return out
