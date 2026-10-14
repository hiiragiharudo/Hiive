"""FastAPI 应用入口。

启动::

    cd backend
    ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

文档：http://127.0.0.1:8000/docs

## 启动时加载语料

语料加载与索引构建通过 lifespan 在**启动时执行一次**（实测本机 125 技能约 0.1–0.3 s）。
若语料路径不存在，服务**仍会启动**但状态标记为 `loaded=False`，相关接口返回 503
并附带原因——这样便于在浏览器里看到明确的错误，而不是让进程启动失败。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import (
    bench_router,
    lexicon_router,
    meta_router,
    route_router,
    skills_router,
)
from .api.routes_agent import agent_router
from .core.config import Settings
from .core.service import SkillService

logger = logging.getLogger("hiive")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 允许 create_app(settings) 注入配置（测试用临时语料时必须走这条路径）
    settings = getattr(app.state, "settings", None) or Settings.from_env()
    svc = SkillService(settings)
    app.state.service = svc
    try:
        st = svc.load(apply_metadata_overlay=True)
        logger.info(
            "技能库已加载: %d 个技能（加载 %.0f ms，建索引 %.0f ms）",
            st.skill_count, st.load_ms, st.index_ms,
        )
        if st.load_report.get("parse_errors"):
            logger.warning("存在 %d 个解析错误", len(st.load_report["parse_errors"]))
    except Exception as e:  # 语料缺失不应导致进程起不来
        svc.state.error = f"{type(e).__name__}: {e}"
        logger.error("技能库加载失败: %s", svc.state.error)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """构造应用（测试可直接调用并注入自定义 Settings）。"""
    app = FastAPI(
        title="Hiive API",
        description=(
            "技能驱动的 AI 渗透测试平台 —— 后端接口。\n\n"
            "核心能力是**两阶段技能路由**：以任务描述检索技能库，"
            "仅把 top-k 技能的元数据与正文注入 Agent 上下文，"
            "从而把元数据开销从 O(技能库规模) 降到 O(k)。"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    cfg = settings or Settings.from_env()
    app.state.settings = cfg
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(meta_router)
    app.include_router(skills_router)
    app.include_router(route_router)
    app.include_router(lexicon_router)
    app.include_router(bench_router)
    app.include_router(agent_router)
    return app


app = create_app()
