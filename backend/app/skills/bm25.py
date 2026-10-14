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
