"""服务容器：持有技能注册表与路由器，供 API 层复用。

## 为什么单独抽一层

FastAPI 的依赖注入若直接在路由函数里加载语料，会**每个请求重建索引**
（实测本机 125 技能建索引约 100–300 ms），且无法共享状态。
本模块把「加载 → 建索引 → 暴露 router」收敛为一处，由 lifespan 在启动时执行一次。

## 并发与重建

`reload()` 会替换 `registry` 与 `router`。uvicorn 单 worker 下请求是协作式的，
但 `build_index` 是同步 CPU 工作，会短暂阻塞事件循环。
因此：① 用锁串行化重建；② 重建时**先生成新对象再原子替换**，
避免请求读到半构建状态。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..eval.bench import BenchItem, BenchMetrics, load_bench, run_bench
from ..skills.lexicon import BilingualLexicon
from ..skills.metadata import infer_all
from ..skills.registry import SkillRegistry
from ..skills.router import RouterConfig, SkillRouter
from .config import Settings


@dataclass
class ServiceState:
    """对外暴露的服务状态快照。"""

    loaded: bool = False
    skill_count: int = 0
    load_ms: float = 0.0
    index_ms: float = 0.0
    error: str = ""
    load_report: dict = field(default_factory=dict)
    enrichment_stats: dict = field(default_factory=dict)
    overlay_stats: dict = field(default_factory=dict)
    lexicon_stats: dict = field(default_factory=dict)
    apply_metadata_overlay: bool = True

    def to_dict(self) -> dict:
        return {
            "loaded": self.loaded,
            "skill_count": self.skill_count,
            "load_ms": round(self.load_ms, 1),
            "index_ms": round(self.index_ms, 1),
            "error": self.error,
            "load_report": self.load_report,
            "enrichment_stats": self.enrichment_stats,
            "overlay_stats": self.overlay_stats,
            "lexicon_stats": self.lexicon_stats,
            "apply_metadata_overlay": self.apply_metadata_overlay,
        }


class SkillService:
    """技能引擎的服务门面。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._lock = threading.Lock()
        self.registry: SkillRegistry | None = None
        self.router: SkillRouter | None = None
        self.lexicon: BilingualLexicon | None = None
        self.state = ServiceState()
        self._bench_cache: dict[Path, list[BenchItem]] = {}

    # ---------------------------------------------------------------- 加载

    def load(self, apply_metadata_overlay: bool = True) -> ServiceState:
        """加载语料、建索引、装配路由器。

        `apply_metadata_overlay=True` 时用规则推断补齐缺失的路由元数据
        （原始 `SKILL.md` 字节不变，见 `SkillRegistry.apply_overlay`）。
        """
        with self._lock:
            st = ServiceState(apply_metadata_overlay=apply_metadata_overlay)
            t0 = time.perf_counter()

            lex = BilingualLexicon.build(
                mined_path=self.settings.lexicon_path,
                include_mined=self.settings.lexicon_include_mined,
            )
            self.lexicon = lex
            st.lexicon_stats = lex.stats.to_dict()

            reg = SkillRegistry()
            report = reg.load_roots(self.settings.skill_roots)
            st.load_ms = (time.perf_counter() - t0) * 1000.0

            if apply_metadata_overlay:
                inferred = infer_all(reg.skills.values())
                overlay = {n: m.to_dict() for n, m in inferred.items()}
                reg.apply_overlay(overlay, only_missing=True)
                st.overlay_stats = dict(reg.overlay_stats)

            reg.attach_lexicon(lex, enrich_triggers=self.settings.enrich_triggers)

            t1 = time.perf_counter()
            reg.build_index(
                tokenizer=self.settings.tokenizer,
                vector_kind=self.settings.vector_kind,
                n_components=self.settings.n_components,
                scoring=self.settings.scoring,
            )
            st.index_ms = (time.perf_counter() - t1) * 1000.0

            router = SkillRouter(reg, self._make_router_config())

            # ---- 原子替换 ----
            self.registry = reg
            self.router = router
            self.state = st
            st.skill_count = len(reg)
            st.load_report = report.to_dict()
            st.enrichment_stats = dict(reg.enrichment_stats)

            # 一个技能都没加载到，等同于不可用——必须如实标记，而不是假装就绪。
            # （`load_roots` 对不存在的路径只记 parse_error 而不抛异常，故此处兜底。）
            if st.skill_count == 0:
                st.loaded = False
                st.error = (
                    "未加载到任何技能，请检查 skill_roots 配置："
                    f"{[str(p) for _l, p in self.settings.skill_roots]}"
                )
            else:
                st.loaded = True
            return st

    def _make_router_config(self) -> RouterConfig:
        s = self.settings
        return RouterConfig(
            top_k=s.top_k,
            recall_n=s.recall_n,
            channels=s.channels,
            expand_query=s.expand_query,
            enrich_triggers=s.enrich_triggers,
            min_coverage=s.min_coverage,
            phase_bonus=s.phase_bonus,
            tokenizer=s.tokenizer,
            vector_kind=s.vector_kind,
        )

    # ---------------------------------------------------------------- 访问

    def require_router(self) -> SkillRouter:
        if self.router is None or not self.state.loaded:
            raise RuntimeError("技能库尚未加载完成")
        return self.router

    def require_registry(self) -> SkillRegistry:
        if self.registry is None or not self.state.loaded:
            raise RuntimeError("技能库尚未加载完成")
        return self.registry

    def make_router(self, **overrides) -> SkillRouter:
        """按请求级覆盖参数构造路由器（不改变全局状态）。

        仅允许**查询时**参数覆盖；建索引时参数（如 `scoring`、`enrich_triggers`）
        不在 `RouterConfig` 中，故天然无法在此覆盖——这保证了"改了没反应"的
        参数不会静默出现。
        """
        cfg = self._make_router_config()
        for k, v in overrides.items():
            if v is None:
                continue
            if not hasattr(cfg, k):
                raise ValueError(f"未知的查询参数: {k}")
            if k == "channels" and isinstance(v, (list, tuple)):
                v = tuple(v)
            setattr(cfg, k, v)
        cfg.validate()
        return SkillRouter(self.require_registry(), cfg)

    # ---------------------------------------------------------------- 基准确

    def bench_items(self, path: Path) -> list[BenchItem]:
        if path not in self._bench_cache:
            self._bench_cache[path] = load_bench(path)
        return self._bench_cache[path]

    def run_bench(self, path: Path, **overrides) -> tuple[BenchMetrics, SkillRouter]:
        items = self.bench_items(path)
        router = self.make_router(**overrides)
        return run_bench(router, items, top_k=overrides.get("top_k")), router
