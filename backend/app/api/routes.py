"""API 路由定义。

**路由顺序很重要**：`/api/skills/stats` 必须声明在 `/api/skills/{name}` 之前，
否则 `stats` 会被当作技能名匹配。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..core.config import INDEX_TIME_PARAMS, QUERY_TIME_OVERRIDABLE
from ..core.service import SkillService
from .schemas import BenchRunRequest, ExpandRequest, ReloadRequest, RouteRequest

skills_router = APIRouter(prefix="/api/skills", tags=["skills"])
route_router = APIRouter(prefix="/api", tags=["route"])
lexicon_router = APIRouter(prefix="/api/lexicon", tags=["lexicon"])
bench_router = APIRouter(prefix="/api/bench", tags=["bench"])
meta_router = APIRouter(prefix="/api", tags=["meta"])


def get_service(request: Request) -> SkillService:
    """从 app.state 取出服务实例（由 lifespan 注入）。"""
    svc = getattr(request.app.state, "service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="服务未就绪")
    return svc


def _require_loaded(svc: SkillService) -> None:
    if not svc.state.loaded:
        raise HTTPException(
            status_code=503,
            detail=f"技能库未加载: {svc.state.error or '未知原因'}",
        )


# --------------------------------------------------------------------- meta


@meta_router.get("/health", summary="健康检查")
def health(svc: SkillService = Depends(get_service)) -> dict:
    return {"status": "ok" if svc.state.loaded else "loading", **svc.state.to_dict()}


@meta_router.get("/config", summary="配置说明（区分建索引时与查询时参数）")
def config(svc: SkillService = Depends(get_service)) -> dict:
    return {
        "index_time_params": list(INDEX_TIME_PARAMS),
        "query_time_params": list(QUERY_TIME_OVERRIDABLE),
        "index_signature": svc.settings.index_signature(),
        "query_defaults": svc.settings.query_defaults(),
        "note": (
            "index_time_params 的改动需要 POST /api/skills/reload 才生效；"
            "query_time_params 可在 POST /api/route 中按请求覆盖。"
        ),
    }


# --------------------------------------------------------------------- skills


@skills_router.get("/stats", summary="技能库健康度与统计")
def skills_stats(svc: SkillService = Depends(get_service)) -> dict:
    _require_loaded(svc)
    reg = svc.require_registry()
    return {
        **reg.stats(),
        "service": svc.state.to_dict(),
        "lexicon": svc.lexicon.stats.to_dict() if svc.lexicon else {},
    }


@skills_router.get("/names", summary="全部技能名（供前端下拉选择）")
def skills_names(svc: SkillService = Depends(get_service)) -> dict:
    _require_loaded(svc)
    reg = svc.require_registry()
    return {"names": sorted(reg.skills)}


@skills_router.get("", summary="技能列表（支持过滤与分页）")
def skills_list(
    svc: SkillService = Depends(get_service),
    q: str = Query("", description="按名称/描述子串过滤"),
    domain: str = Query("", description="按安全域过滤"),
    phase: str = Query("", description="按渗透阶段过滤"),
    risk: str = Query("", description="按风险等级过滤"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    _require_loaded(svc)
    reg = svc.require_registry()
    ql = q.strip().lower()
    items = []
    for name, skill in reg.skills.items():
        m = skill.meta
        if ql and ql not in name.lower() and ql not in m.description.lower():
            continue
        if domain and domain not in m.domains:
            continue
        if phase and m.phase != phase:
            continue
        if risk and m.risk != risk:
            continue
        items.append(skill.to_dict())
    items.sort(key=lambda d: d["name"])
    total = len(items)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items[offset : offset + limit],
    }


@skills_router.get("/{name}", summary="技能详情")
def skill_detail(
    name: str,
    svc: SkillService = Depends(get_service),
    include_body: bool = Query(True),
) -> dict:
    _require_loaded(svc)
    reg = svc.require_registry()
    skill = reg.get(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"技能不存在: {name}")

    # 依赖闭包与缺失依赖（编排能力的展示）
    router = svc.require_router()
    closure, cycles = router.dependency_closure([name])
    missing = [d for d in skill.meta.requires if d not in reg]

    return {
        **skill.to_dict(include_body=include_body),
        "enriched_triggers": reg.enriched_triggers(name),
        "dependency_closure": closure,
        "dependency_cycles": cycles,
        "missing_dependencies": missing,
        "estimated_meta_tokens": skill.estimated_meta_tokens(),
        "estimated_body_tokens": skill.estimated_body_tokens(),
    }


@skills_router.post("/reload", summary="重新加载语料并重建索引")
def skills_reload(
    body: ReloadRequest, svc: SkillService = Depends(get_service)
) -> dict:
    st = svc.load(apply_metadata_overlay=body.apply_metadata_overlay)
    return {"reloaded": True, **st.to_dict()}


# --------------------------------------------------------------------- route


@route_router.post("/route", summary="★ 两阶段技能路由（核心接口）")
def do_route(body: RouteRequest, svc: SkillService = Depends(get_service)) -> dict:
    """执行两阶段路由。

    响应直接对应 `RouteResult.to_dict()`，含：
    - `candidates`：每个技能的**召回依据**（`reason`、`matched_fields`、各通道名次与得分）；
    - `cost`：基线元数据 token、注入 token、元数据项节省比例、总开销节省比例；
    - `cross_lingual`：跨语言查询扩展的命中项与实际检索用的查询文本；
    - `timing_ms`：阶段一/阶段二耗时。

    前端「检索路由可视化」直接消费该结构。
    """
    _require_loaded(svc)
    ov = body.overrides()
    try:
        router = svc.make_router(**ov)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    top_k = ov.get("top_k")
    try:
        res = router.route(body.query, state_phase=body.state_phase, top_k=top_k)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    out = res.to_dict(include_body=body.include_body)
    out["applied_overrides"] = ov
    out["abstained"] = res.abstained
    out["top_coverage"] = round(res.top_coverage, 4)
    return out


@route_router.get("/route/expansion", summary="查询扩展诊断")
def route_expansion(
    q: str = Query(..., min_length=1),
    svc: SkillService = Depends(get_service),
) -> dict:
    """只看跨语言扩展命中了哪些术语（不执行检索）。"""
    _require_loaded(svc)
    if svc.lexicon is None:
        return {"query": q, "expanded": False, "expansion": [], "retrieval_query": q}
    expanded, matched = svc.lexicon.expand_query(q)
    return {
        "query": q,
        "expanded": bool(matched),
        "expansion": [{"zh": zh, "en": en} for zh, en in matched],
        "retrieval_query": expanded,
    }


# --------------------------------------------------------------------- lexicon


@lexicon_router.get("/stats", summary="双语词典统计")
def lexicon_stats(svc: SkillService = Depends(get_service)) -> dict:
    if svc.lexicon is None:
        raise HTTPException(status_code=503, detail="词典未加载")
    return {
        **svc.lexicon.stats.to_dict(),
        "sample": [
            {"zh": zh, "en": ens[:3]}
            for zh, ens in list(svc.lexicon.zh_to_en.items())[:20]
        ],
    }


@lexicon_router.post("/expand", summary="查询扩展（请求体形式）")
def lexicon_expand(
    body: ExpandRequest, svc: SkillService = Depends(get_service)
) -> dict:
    _require_loaded(svc)
    if svc.lexicon is None:
        raise HTTPException(status_code=503, detail="词典未加载")
    expanded, matched = svc.lexicon.expand_query(body.query)
    return {
        "query": body.query,
        "retrieval_query": expanded,
        "expansion": [{"zh": zh, "en": en} for zh, en in matched],
    }


# --------------------------------------------------------------------- bench


def _default_bench_path(svc: SkillService) -> Path:
    repo = Path(__file__).resolve().parent.parent.parent.parent
    return repo / "eval" / "bench" / "skillroute-bench-v0.jsonl"


@bench_router.get("/info", summary="基准信息")
def bench_info(svc: SkillService = Depends(get_service)) -> dict:
    path = _default_bench_path(svc)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"基准文件不存在: {path}")
    items = svc.bench_items(path)
    by_src: dict[str, int] = {}
    by_lang: dict[str, int] = {}
    for it in items:
        by_src[it.source] = by_src.get(it.source, 0) + 1
        by_lang[it.lang] = by_lang.get(it.lang, 0) + 1
    return {
        "path": str(path),
        "total": len(items),
        "scored": sum(1 for it in items if not it.is_abstention),
        "abstention": sum(1 for it in items if it.is_abstention),
        "by_source": by_src,
        "by_lang": by_lang,
        "note": "弃权用例为「库中无正确答案」的查询，用于测量路由器是否硬凑答案。",
    }


@bench_router.get("/items", summary="基准条目")
def bench_items(
    svc: SkillService = Depends(get_service),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    path = _default_bench_path(svc)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"基准文件不存在: {path}")
    items = svc.bench_items(path)
    return {
        "total": len(items),
        "items": [it.to_dict() for it in items[offset : offset + limit]],
    }


@bench_router.post("/run", summary="在基准上运行一组配置并返回指标")
def bench_run(
    body: BenchRunRequest, svc: SkillService = Depends(get_service)
) -> dict:
    _require_loaded(svc)
    path = Path(body.bench_path) if body.bench_path else _default_bench_path(svc)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"基准文件不存在: {path}")

    overrides: dict = {"top_k": body.top_k}
    if body.channels is not None:
        overrides["channels"] = body.channels
    if body.expand_query is not None:
        overrides["expand_query"] = body.expand_query
    if body.min_coverage is not None:
        overrides["min_coverage"] = body.min_coverage

    metrics, _router = svc.run_bench(path, **overrides)
    metrics.name = body.name
    out = metrics.to_dict()
    out["config"] = overrides
    out["failures"] = [
        {
            "id": r.item.id,
            "query": r.item.query,
            "expected": r.item.expected,
            "candidates": r.candidates,
            "failure_kind": "recall" if r.stage1_rank == 0 else "ranking",
        }
        for r in metrics.results
        if not r.item.is_abstention and not r.hit
    ]
    out["false_routes"] = [
        {"id": r.item.id, "query": r.item.query, "candidates": r.candidates[:5]}
        for r in metrics.results
        if r.false_route
    ]
    return out
