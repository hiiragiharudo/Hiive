"""向量检索通道：TF-IDF 稀疏向量 + LSA 潜在语义投影。

设计取舍：**不使用 sentence-transformers / torch**（Python 3.14 下无稳定轮子，
且会让研究核心失去可复现性）。改用两级方案：

1. ``TfidfVectorizer``：纯标准库的稀疏 TF-IDF（sublinear tf + L2 归一化），
   作为「词面语义」通道——与 BM25 的区别在于它做了 L2 长度归一化并使用
   sublinear tf，对短技能描述更公平。
2. ``LsaVectorizer``：在 TF-IDF 矩阵上做截断 SVD（LSA），得到**潜在语义**向量。
   这能捕捉「词不同但语义相近」的情况（例如查询「后台入口」与技能描述
   「管理员登录页面识别」在词面上不重合，但在潜在语义空间中接近）。
   仅需 numpy，语料规模（百级文档）下 SVD 秒级完成。

真正的神经嵌入模型（BGE / text-embedding-3）可通过实现 ``Embedder`` 协议接入，
作为消融实验的一个通道，但**不是必需依赖**。
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

from .tokenize import tokenize


class Embedder(Protocol):
    """向量通道协议。"""

    name: str
    dim: int

    def fit(self, doc_ids: list[str], doc_texts: list[str]) -> None: ...

    def embed_query(self, text: str) -> list[float] | dict[int, float]: ...

    def similarity(self, doc_id: str, query_vec) -> float: ...


# --------------------------------------------------------------------------- TF-IDF


@dataclass
class TfidfVectorizer:
    """稀疏 TF-IDF 向量化器（纯标准库）。

    - ``sublinear_tf``：tf 取 ``1 + log(tf)``，抑制高频词主导；
    - L2 归一化：使长技能描述与短技能描述可比；
    - ``min_df``：丢弃只出现一次的稀有词，降低噪声与维度。
    """

    min_df: int = 1
    sublinear_tf: bool = True
    tokenizer: str = "hybrid"

    vocab: dict[str, int] = field(default_factory=dict, repr=False)
    idf: dict[str, float] = field(default_factory=dict, repr=False)
    _doc_vecs: dict[str, dict[int, float]] = field(default_factory=dict, repr=False)

    @property
    def name(self) -> str:
        return "tfidf"

    @property
    def dim(self) -> int:
        return len(self.vocab)

    def _tok(self, text: str) -> list[str]:
        from .tokenize import TOKENIZERS

        return TOKENIZERS[self.tokenizer](text)

    def fit(self, doc_ids: list[str], doc_texts: list[str]) -> None:
        from .tokenize import TOKENIZERS

        tokfn = TOKENIZERS[self.tokenizer]
        tokenized = [tokfn(t) for t in doc_texts]

        df: Counter = Counter()
        for toks in tokenized:
            for term in set(toks):
                df[term] += 1

        n = len(doc_ids)
        kept = [term for term, d in df.items() if d >= self.min_df]
        kept.sort()
        self.vocab = {term: i for i, term in enumerate(kept)}
        # 平滑 IDF，避免除零
        self.idf = {
            term: math.log((n + 1) / (df[term] + 1)) + 1.0 for term in kept
        }

        self._doc_vecs.clear()
        for doc_id, toks in zip(doc_ids, tokenized):
            self._doc_vecs[doc_id] = self._vectorize(toks)

    def _vectorize(self, toks: list[str]) -> dict[int, float]:
        tf = Counter(t for t in toks if t in self.vocab)
        vec: dict[int, float] = {}
        for term, f in tf.items():
            w = (1.0 + math.log(f)) if (self.sublinear_tf and f > 0) else float(f)
            vec[self.vocab[term]] = w * self.idf[term]
        return _l2_normalize_sparse(vec)

    def embed_query(self, text: str) -> dict[int, float]:
        return self._vectorize(self._tok(text))

    def similarity(self, doc_id: str, query_vec) -> float:
        dv = self._doc_vecs.get(doc_id)
        if not dv or not query_vec:
            return 0.0
        # 两者均已 L2 归一化，点积即余弦
        if len(dv) > len(query_vec):
            dv, query_vec = query_vec, dv
        return sum(w * query_vec.get(i, 0.0) for i, w in dv.items())

    def search(self, text: str, top_n: int | None = None) -> list[tuple[str, float]]:
        qv = self.embed_query(text)
        scored = [(d, self.similarity(d, qv)) for d in self._doc_vecs]
        scored = [(d, s) for d, s in scored if s > 0.0]
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored[:top_n] if top_n is not None else scored

    def doc_matrix(self) -> tuple[list[str], list[list[float]]]:
        """导出稠密文档-词矩阵，供 LSA 使用。"""
        ids = list(self._doc_vecs)
        mat = [[0.0] * len(self.vocab) for _ in ids]
        for r, d in enumerate(ids):
            for c, w in self._doc_vecs[d].items():
                mat[r][c] = w
        return ids, mat


def _l2_normalize_sparse(vec: dict[int, float]) -> dict[int, float]:
    norm = math.sqrt(sum(w * w for w in vec.values()))
    if norm <= 0.0:
        return vec
    return {i: w / norm for i, w in vec.items()}


# --------------------------------------------------------------------------- LSA


class LsaVectorizer:
    """潜在语义分析（Latent Semantic Analysis）向量通道。

    在 TF-IDF 文档-词矩阵上做截断 SVD：

        X ≈ U · Σ · Vᵀ

    文档向量取 ``U·Σ``，查询向量投影为 ``qᵀ·V·Σ⁻¹``（再 L2 归一化）。
    这样查询与文档落在同一潜在语义空间中，可捕捉词面不重合的语义相近。
    """

    name = "lsa"

    def __init__(self, base: TfidfVectorizer, n_components: int = 64) -> None:
        self.base = base
        self.n_components = n_components
        self._svd: tuple | None = None
        self._doc_ids: list[str] = []
        self._doc_vecs: dict[str, "object"] = {}
        self._vt = None
        self._sigma_inv = None

    @property
    def dim(self) -> int:
        return self.n_components

    def fit(self, doc_ids: list[str], doc_texts: list[str]) -> None:
        try:
            import numpy as np
        except ImportError as e:  # pragma: no cover - 环境相关
            raise RuntimeError(
                "LsaVectorizer 需要 numpy；请改用 tfidf 通道或安装 numpy"
            ) from e

        self.base.fit(doc_ids, doc_texts)
        ids, mat = self.base.doc_matrix()
        self._doc_ids = ids
        x = np.asarray(mat, dtype=np.float64)
        if x.size == 0:
            return
        k = min(self.n_components, min(x.shape) - 1) if min(x.shape) > 1 else 1
        k = max(k, 1)
        u, s, vt = np.linalg.svd(x, full_matrices=False)
        u, s, vt = u[:, :k], s[:k], vt[:k, :]
        self._svd = (u, s, vt)
        self._vt = vt
        with np.errstate(divide="ignore"):
            self._sigma_inv = np.where(s > 1e-12, 1.0 / s, 0.0)
        doc_latent = u * s
        for i, doc_id in enumerate(ids):
            v = doc_latent[i]
            nrm = float(np.linalg.norm(v))
            self._doc_vecs[doc_id] = v / nrm if nrm > 0 else v

    def embed_query(self, text: str):
        import numpy as np

        if self._vt is None:
            return None
        q = self.base.embed_query(text)
        if not q:
            return None
        idx = np.fromiter(q.keys(), dtype=np.int64, count=len(q))
        val = np.fromiter(q.values(), dtype=np.float64, count=len(q))
        dense = np.zeros(self.base.dim, dtype=np.float64)
        dense[idx] = val
        v = (dense @ self._vt.T) * self._sigma_inv
        nrm = float(np.linalg.norm(v))
        return v / nrm if nrm > 0 else v

    def similarity(self, doc_id: str, query_vec) -> float:
        dv = self._doc_vecs.get(doc_id)
        if dv is None or query_vec is None:
            return 0.0
        return float(dv @ query_vec)

    def search(self, text: str, top_n: int | None = None) -> list[tuple[str, float]]:
        qv = self.embed_query(text)
        if qv is None:
            return []
        scored = [(d, self.similarity(d, qv)) for d in self._doc_ids]
        scored = [(d, s) for d, s in scored if s > 0.0]
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored[:top_n] if top_n is not None else scored


def build_vector_channel(kind: str, **kwargs):
    """按名称构造向量通道。

    会按各通道的构造签名过滤无关关键字（例如给 ``tfidf`` 传了 ``n_components``
    时自动忽略），避免调用方需要区分参数。
    """
    if kind == "tfidf":
        allowed = {"min_df", "sublinear_tf", "tokenizer"}
        return TfidfVectorizer(**{k: v for k, v in kwargs.items() if k in allowed})
    if kind == "lsa":
        allowed = {"min_df", "sublinear_tf", "tokenizer"}
        base = TfidfVectorizer(**{k: v for k, v in kwargs.items() if k in allowed})
        return LsaVectorizer(base, n_components=kwargs.get("n_components", 64))
    raise ValueError(f"unknown vector channel: {kind}")
