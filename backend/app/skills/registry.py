"""技能注册表：加载、校验、建立检索索引。

这是两阶段路由的「离线侧」——索引在启动时一次性构建，查询时只做检索。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .bm25 import BM25Index
from .models import Skill
from .parser import SkillParseError, parse_skill_file, validate_meta
from .vectors import build_vector_channel


#: 分字段检索的字段权重。
#:
#: 设计动机：把技能的所有字段拼成一段文本再做 BM25，会产生**文档长度偏置**——
#: 拥有长 `description` 的"伞状技能"（desc 长达数百字）会因为词频累积而压过
#: 细粒度子技能，即使查询明明只与后者的 `triggers`/`name` 精确匹配。
#:
#: 实测证据（本机 133 个技能语料，查询「目标是一个 WordPress 站点，我要找管理员
#: 登录入口」）：拼接式 BM25 的 top-5 全部是 `src-6k-skill`/`pent3st`/`cve-yu2`
#: 等伞状技能，无一细粒度技能命中。改为分字段加权后，`name` 与 `triggers` 的
#: 精确匹配不再被长描述淹没。
#:
#: **这组权重是消融实验的自变量之一**（见 ``eval/ablation.py``）。
FIELD_WEIGHTS: dict[str, float] = {
    "name": 3.0,
    "triggers": 3.0,
    "targets": 2.0,
    "description": 1.0,
    "domains": 1.0,
    "tools": 1.0,
}


@dataclass
class LoadReport:
    """加载报告——用于「技能库健康度」展示与论文中的语料统计。"""

    loaded: int = 0
    duplicates: list[tuple[str, str, str]] = field(default_factory=list)
    parse_errors: list[tuple[str, str]] = field(default_factory=list)
    validation_problems: dict[str, list[str]] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.parse_errors and not self.validation_problems

    def to_dict(self) -> dict:
        return {
            "loaded": self.loaded,
            "by_source": self.by_source,
            "duplicates": [
                {"name": n, "kept": k, "skipped": s} for n, k, s in self.duplicates
            ],
            "parse_errors": [{"path": p, "error": e} for p, e in self.parse_errors],
            "validation_problems": self.validation_problems,
            "ok": self.ok,
        }


class SkillRegistry:
    """技能注册表 + 检索索引。"""

    def __init__(self) -> None:
        self.skills: dict[str, Skill] = {}
        self.report = LoadReport()
        self.bm25: BM25Index | None = None
        self.field_indexes: dict[str, BM25Index] = {}
        self.field_weights: dict[str, float] = dict(FIELD_WEIGHTS)
        self.scoring: str = "fielded"
        self.vector = None
        self.vector_kind: str = ""
        self.tokenizer_name: str = "hybrid"
        self.index_build_ms: float = 0.0

        # ---- 跨语言支持（见 lexicon.py） ----
        self.lexicon = None
        #: 是否用双语词典给技能补充中文触发词（索引侧富化）
        self.enrich_triggers: bool = False
        self._enriched_triggers: dict[str, list[str]] = {}
        self.enrichment_stats: dict[str, int] = {}
        self.overlay_stats: dict[str, int] = {}

    def attach_lexicon(self, lexicon, enrich_triggers: bool = True) -> None:
        """挂载双语词典。

        ``enrich_triggers=True`` 时，建索引阶段会把词典反查得到的中文术语
        并入每个技能的 `triggers` 字段——使**中文查询的字面 token 能直接命中
        英文描述的技能**，而查询期零额外开销。
        """
        self.lexicon = lexicon
        self.enrich_triggers = enrich_triggers

    # ------------------------------------------------------------ 加载

    def load_roots(self, roots: list[tuple[str, Path]]) -> LoadReport:
        """从多个根目录加载全部 `SKILL.md`。

        参数
        ----
        roots
            ``[(来源标签, 根路径), ...]``。同名声明的技能只保留**先出现的**，
            并在报告中记录冲突，避免静默覆盖。
        """
        self.skills.clear()
        self.report = LoadReport()

        for label, root in roots:
            root = Path(root)
            if not root.exists():
                self.report.parse_errors.append((str(root), "路径不存在"))
                continue
            count = 0
            for path in sorted(root.rglob("SKILL.md")):
                try:
                    skill = parse_skill_file(path, source=label)
                except SkillParseError as e:
                    self.report.parse_errors.append((str(path), str(e)))
                    continue

                existing = self.skills.get(skill.name)
                if existing is not None:
                    self.report.duplicates.append(
                        (skill.name, existing.meta.dir_path, str(path))
                    )
                    continue

                problems = validate_meta(skill.meta)
                if problems:
                    self.report.validation_problems[skill.name] = problems

                self.skills[skill.name] = skill
                count += 1
            self.report.by_source[label] = count

        self.report.loaded = len(self.skills)
        return self.report

    # ------------------------------------------------------------ 索引

    def build_index(
        self,
        tokenizer: str = "hybrid",
        vector_kind: str = "lsa",
        n_components: int = 64,
        min_df: int = 1,
        scoring: str = "fielded",
        field_weights: dict[str, float] | None = None,
    ) -> None:
        """构建 BM25（分字段）与向量双通道索引。

        参数
        ----
        scoring
            ``"fielded"``（默认）按字段分别建索引再加权求和，可消除文档长度偏置；
            ``"flat"`` 把全部字段拼成一段文本再建索引——保留它是为了**消融实验**
            能够量化分字段设计的贡献。
        """
        import time as _time

        t0 = _time.perf_counter()
        self.tokenizer_name = tokenizer
        self.vector_kind = vector_kind
        self.scoring = scoring
        if field_weights:
            self.field_weights = dict(field_weights)

        names = list(self.skills)
        texts = [self.skills[n].meta.routing_text() for n in names]

        # 必须从子模块直接导入：包 __init__ 中 `from .tokenize import tokenize`
        # 会把子模块名 tokenize 遮蔽为函数，`from . import tokenize` 会拿到函数。
        from .tokenize import TOKENIZERS

        tokfn = TOKENIZERS[tokenizer]

        # ---- 拼接式索引（flat，作为消融基线保留） ----
        flat = BM25Index()
        for name, text in zip(names, texts):
            flat.add(name, tokfn(text))
        flat.finalize()
        self.bm25 = flat

        # ---- 分字段索引（fielded，默认） ----
        self._build_enrichment()
        self.field_indexes = {}
        for field_name in FIELD_WEIGHTS:
            idx = BM25Index()
            for name in names:
                idx.add(name, tokfn(self._field_text(name, field_name)))
            idx.finalize()
            self.field_indexes[field_name] = idx

        # ---- 向量通道 ----
        try:
            vec = build_vector_channel(
                vector_kind, n_components=n_components, min_df=min_df, tokenizer=tokenizer
            )
            vec.fit(names, texts)
            self.vector = vec
        except RuntimeError:
            # numpy 缺失时（LSA 需要）优雅降级到纯标准库 TF-IDF
            vec = build_vector_channel("tfidf", min_df=min_df, tokenizer=tokenizer)
            vec.fit(names, texts)
            self.vector = vec
            self.vector_kind = "tfidf(降级)"

        self.index_build_ms = (_time.perf_counter() - t0) * 1000.0

    def _build_enrichment(self) -> None:
        """索引侧富化：用双语词典为技能反查中文触发词。

        **设计动机**：语料是双语异质的——103 个细粒度子技能用英文描述，
        中文查询的字面 token 无法命中。与其在每次查询时做扩展（有查询期开销），
        不如在建索引时把中文术语写进技能的 `triggers` 字段：一次付费、终身受益，
        且富化结果**可人工审阅**（能直接看到某技能被补了哪些中文词）。
        """
        self._enriched_triggers = {}
        self.enrichment_stats = {"enriched": 0, "terms_added": 0}
        if not (self.enrich_triggers and self.lexicon is not None):
            return
        for name, skill in self.skills.items():
            m = skill.meta
            text = f"{m.name} {m.description} {' '.join(m.targets)}"
            extra = self.lexicon.zh_triggers_for(text)
            if extra:
                self._enriched_triggers[name] = extra
                self.enrichment_stats["enriched"] += 1
                self.enrichment_stats["terms_added"] += len(extra)

    def _field_text(self, name: str, field: str) -> str:
        """取某技能的单个字段文本（`triggers` 字段含索引侧富化结果）。"""
        m = self.skills[name].meta
        if field == "name":
            return m.name
        if field == "description":
            return m.description
        if field == "triggers":
            base = " ".join(m.triggers)
            extra = self._enriched_triggers.get(name)
            if extra:
                base = f"{base} {' '.join(extra)}".strip()
            return base
        if field == "targets":
            return " ".join(m.targets)
        if field == "domains":
            return " ".join(m.domains)
        if field == "tools":
            return " ".join(m.tools)
        return ""

    def enriched_triggers(self, name: str) -> list[str]:
        """返回某技能被索引侧富化补入的中文触发词（供前端展示与人工审阅）。"""
        return list(self._enriched_triggers.get(name, []))

    # ------------------------------------------------------------ 元数据覆盖层

    def apply_overlay(self, overlay: dict[str, dict], only_missing: bool = True) -> dict:
        """把规则推断的元数据覆盖层合并进**内存中的**技能模型。

        **原始 `SKILL.md` 文件保持字节不变**——本方法只改内存对象。这样：
        ① 不污染第三方技能库；② 原始语料与课题加工可分离，便于消融；
        ③ 覆盖层可作为独立产物版本化与人工复核。

        参数
        ----
        overlay
            ``{技能名: {"phase":..., "domains":[...], "targets":[...],
            "triggers":[...], "risk":...}}``
        only_missing
            **默认 True（保守策略）**：只填补语料中为空的字段，绝不覆盖语料
            已显式声明的值。语料作者声明的元数据可信度高于规则推断；
            若允许覆盖，规则误判会静默劣化路由，且无法从结果中察觉。

        返回统计字典。
        """
        stats = {"skills_touched": 0, "fields_filled": 0, "fields_skipped": 0}
        self.overlay_stats = stats

        for name, patch in overlay.items():
            skill = self.skills.get(name)
            if skill is None:
                continue
            m = skill.meta
            touched = False
            for field_name in ("phase", "domains", "targets", "triggers"):
                value = patch.get(field_name)
                if not value:
                    continue
                current = getattr(m, field_name)
                if current and only_missing:
                    stats["fields_skipped"] += 1
                    continue
                setattr(m, field_name, value)
                stats["fields_filled"] += 1
                touched = True
            risk = patch.get("risk")
            if risk and risk != "low":
                # risk 默认 low，只有非 low 的推断才值得写入
                if m.risk == "low" or not only_missing:
                    if m.risk != risk:
                        m.risk = risk
                        stats["fields_filled"] += 1
                        touched = True
            if touched:
                stats["skills_touched"] += 1
        return stats

    # ------------------------------------------------------------ 访问

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def __len__(self) -> int:
        return len(self.skills)

    def __contains__(self, name: object) -> bool:
        return name in self.skills

    def search_bm25_detail(
        self, query: str, top_n: int | None = None
    ) -> tuple[list[tuple[str, float]], dict[str, dict[str, float]]]:
        """返回 ``(排序结果, 每文档的分字段得分)``。

        分字段得分经**逐字段最大值归一化**后再按 ``field_weights`` 加权——
        归一化是必要的，否则不同字段的 IDF 量级不可比（``name`` 字段的 IDF
        天然远高于 ``description``）。
        """
        if self.bm25 is None:
            raise RuntimeError("索引未构建，请先调用 build_index()")
        from .tokenize import TOKENIZERS

        q_tokens = TOKENIZERS[self.tokenizer_name](query)

        if self.scoring == "flat":
            hits = self.bm25.search(q_tokens, top_n=top_n)
            detail = {d: {"flat": s} for d, s in hits}
            return hits, detail

        field_scores: dict[str, dict[str, float]] = {}
        totals: dict[str, float] = {}
        for fname, idx in self.field_indexes.items():
            hits = idx.search(q_tokens, top_n=None)
            if not hits:
                continue
            mx = hits[0][1]
            if mx <= 0:
                continue
            w = self.field_weights.get(fname, 1.0)
            for doc, raw in hits:
                norm = raw / mx
                field_scores.setdefault(doc, {})[fname] = norm
                totals[doc] = totals.get(doc, 0.0) + w * norm

        ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
        if top_n is not None:
            ranked = ranked[:top_n]
        return ranked, field_scores

    def search_bm25(self, query: str, top_n: int | None = None) -> list[tuple[str, float]]:
        return self.search_bm25_detail(query, top_n=top_n)[0]


    def search_vector(self, query: str, top_n: int | None = None) -> list[tuple[str, float]]:
        if self.vector is None:
            raise RuntimeError("索引未构建，请先调用 build_index()")
        return self.vector.search(query, top_n=top_n)

    # ------------------------------------------------------------ 统计

    def baseline_tokens(self) -> int:
        """全量注入的技能元数据 token 总量——两阶段方案的对照基线。"""
        return sum(s.estimated_meta_tokens() for s in self.skills.values())

    def full_injection_tokens(self) -> int:
        """把所有技能的元数据**加**正文全部注入的成本（上界参考）。"""
        return sum(s.injected_tokens() for s in self.skills.values())

    def stats(self) -> dict:
        skills = list(self.skills.values())
        by_phase: dict[str, int] = {}
        by_domain: dict[str, int] = {}
        for s in skills:
            by_phase[s.meta.phase or "(未标注)"] = by_phase.get(s.meta.phase or "(未标注)", 0) + 1
            for d in s.meta.domains or ["(未标注)"]:
                by_domain[d] = by_domain.get(d, 0) + 1
        return {
            "total": len(skills),
            "by_source": dict(self.report.by_source),
            "by_phase": dict(sorted(by_phase.items(), key=lambda kv: -kv[1])),
            "by_domain": dict(sorted(by_domain.items(), key=lambda kv: -kv[1])),
            "with_triggers": sum(1 for s in skills if s.meta.triggers),
            "with_description": sum(1 for s in skills if s.meta.description),
            "total_body_chars": sum(s.body_chars for s in skills),
            "baseline_meta_tokens": self.baseline_tokens(),
            "full_injection_tokens": self.full_injection_tokens(),
            "index_build_ms": round(self.index_build_ms, 2),
            "vector_channel": self.vector_kind,
            "tokenizer": self.tokenizer_name,
        }
