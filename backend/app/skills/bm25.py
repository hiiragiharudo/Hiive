"""BM25 Okapi 检索通道——纯标准库实现。

采用 Robertson & Zaragoza (2009) 的经典形式：

    IDF(q) = ln( (N - df + 0.5) / (df + 0.5) + 1 )
    score(D, Q) = Σ IDF(q) · [ f(q,D)·(k1+1) ] / [ f(q,D) + k1·(1 - b + b·|D|/avgdl) ]

其中 IDF 使用 `+1` 平滑（Lucene/BM25+ 风格），避免高频词产生负 IDF。

**为什么不直接用 `rank_bm25`？** 三个理由：
1. 该库不支持自定义分词器与字段加权，而本课题需要；
2. 需要统计每个查询词对各字段的命中情况，用于「路由依据」可视化；
3. 研究核心不应依赖不透明的第三方实现——公式与参数必须是可控变量（消融实验需要改 k1/b）。
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class BM25Index:
    """BM25 倒排索引。

    用法::

        idx = BM25Index()
        idx.add("s1", ["越权", "越权", "id"])
        idx.add("s2", ["注入", "sql"])
        idx.finalize()
        idx.search(["越权"], top_n=1)
    """

    k1: float = 1.5
    b: float = 0.75

    _doc_tf: dict[str, Counter] = field(default_factory=dict, repr=False)
    _doc_len: dict[str, int] = field(default_factory=dict, repr=False)
    _df: Counter = field(default_factory=Counter, repr=False)
    _avgdl: float = 0.0
    _finalized: bool = False

    # ---------------------------------------------------------------- 构建

    def add(self, doc_id: str, tokens: list[str]) -> None:
        if doc_id in self._doc_tf:
            raise ValueError(f"duplicate doc_id: {doc_id}")
        tf = Counter(tokens)
        self._doc_tf[doc_id] = tf
        self._doc_len[doc_id] = len(tokens)
        for term in tf:
            self._df[term] += 1
        self._finalized = False

    def finalize(self) -> None:
        n = len(self._doc_tf)
        total = sum(self._doc_len.values())
        self._avgdl = (total / n) if n else 0.0
        self._finalized = True

    # ---------------------------------------------------------------- 查询

    @property
    def size(self) -> int:
        return len(self._doc_tf)

    def _idf(self, term: str) -> float:
        n = self.size
        df = self._df.get(term, 0)
        if df == 0:
            return 0.0
        return math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, doc_id: str, query_tokens: list[str]) -> float:
        """单个文档对查询的 BM25 得分。"""
        if not self._finalized:
            self.finalize()
        tf = self._doc_tf.get(doc_id)
        if not tf:
            return 0.0
        dl = self._doc_len[doc_id]
        denom_norm = self.k1 * (1.0 - self.b + self.b * (dl / self._avgdl if self._avgdl else 0.0))
        s = 0.0
        for term in set(query_tokens):
            f = tf.get(term, 0)
            if not f:
                continue
            s += self._idf(term) * (f * (self.k1 + 1.0)) / (f + denom_norm)
        return s

    def search(
        self, query_tokens: list[str], top_n: int | None = None
    ) -> list[tuple[str, float]]:
        """返回 [(doc_id, score)]，按得分降序；得分为 0 的文档不返回。"""
        if not self._finalized:
            self.finalize()
        scored: list[tuple[str, float]] = []
        for doc_id in self._doc_tf:
            s = self.score(doc_id, query_tokens)
            if s > 0.0:
                scored.append((doc_id, s))
        scored.sort(key=lambda x: (-x[1], x[0]))  # 平局按 id 稳定排序
        if top_n is not None:
            scored = scored[:top_n]
        return scored

    def term_hits(self, doc_id: str, query_tokens: list[str]) -> list[str]:
        """返回查询词中命中该文档的词（按 IDF 降序），用于「路由依据」可视化。"""
        tf = self._doc_tf.get(doc_id, Counter())
        hits = [t for t in set(query_tokens) if tf.get(t)]
        hits.sort(key=lambda t: (-self._idf(t), t))
        return hits

    # ---------------------------------------------------------------- 覆盖率

    def _max_idf(self) -> float:
        """语料中的最大 IDF，用于给**未登录词**赋权。"""
        if not self._df:
            return 1.0
        n = self.size
        return math.log((n - 1 + 0.5) / (1 + 0.5) + 1.0) if n > 1 else 1.0

    def weighted_coverage(self, doc_id: str, query_tokens: list[str]) -> float:
        """IDF 加权的查询词覆盖率 ∈ [0, 1]。

        **为什么需要它？** RRF 融合只用**排名**、丢弃分数大小，因此融合得分恒等于
        ``1/(k+rank)``——**与匹配强度无关**。实测：无论把弃权阈值设在 0.004 还是
        0.016，弃权准确率始终为 0。故基于 RRF 得分的弃权**在原理上不可行**。

        本方法改用一个**尺度无关**的信号：查询中有多少"信息量"被该文档解释。

            coverage(d, q) = Σ_{t ∈ q} idf(t)·[t ∈ d]  /  Σ_{t ∈ q} idf(t)

        - 未登录词（语料中不存在）赋予**最大 IDF 权重**——所以查不到内容的
          离题查询覆盖率会很低，正是期望行为；
        - 覆盖率与查询无关地落在 [0,1]，可跨查询比较，适合做阈值。
        """
        tf = self._doc_tf.get(doc_id)
        terms = set(query_tokens)
        if not terms:
            return 0.0
        max_idf = self._max_idf()
        total = 0.0
        hit = 0.0
        for term in terms:
            w = self._idf(term) or max_idf
            total += w
            if tf and tf.get(term):
                hit += w
        return hit / total if total > 0 else 0.0
