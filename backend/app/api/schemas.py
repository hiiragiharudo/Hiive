"""API 请求模型。

**响应统一使用领域对象自带的 `to_dict()`**，不再重复定义响应 schema——
领域层的序列化逻辑（含成本模型、路由依据、分层指标）已是唯一真值来源，
重复定义会产生两处不一致的风险。

**请求模型必须做严格校验**，尤其是：
- 查询时参数与建索引时参数的区分（改后者无效应明确报错，而非静默忽略）；
- `recall_n >= top_k`（否则路由器内部校验会抛错，应提前给出可读消息）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Channel = Literal["bm25", "vector"]


class RouteRequest(BaseModel):
    """`POST /api/route` 请求体——全部为**查询时**参数。

    **`extra="forbid"` 是刻意的**：本接口只接受查询时参数。若传入建索引时参数
    （如 `scoring`、`enrich_triggers`），必须**明确报错**而不是静默忽略——
    否则前端改了开关却"没反应"，会浪费大量排查时间。
    实测：初版未设置该项时，`scoring` 被静默丢弃并返回 200。
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000, description="任务描述")
    top_k: int | None = Field(None, ge=1, le=50, description="注入上下文的技能数")
    recall_n: int | None = Field(None, ge=1, le=200, description="阶段一召回池大小")
    state_phase: str = Field("", description="当前渗透阶段（阶段先验）")
    expand_query: bool | None = Field(None, description="查询侧跨语言扩展")
    channels: list[Channel] | None = Field(None, description="启用的检索通道")
    weights: dict[str, float] | None = Field(None, description="通道权重（RRF）")
    min_coverage: float | None = Field(
        None, ge=0.0, le=1.0, description="弃权阈值（IDF 加权覆盖率）"
    )
    min_score: float | None = Field(None, ge=0.0, description="RRF 得分阈值（已废弃，仅对照）")
    phase_bonus: float | None = Field(None, ge=0.0, description="阶段匹配奖励")
    include_body: bool = Field(False, description="响应是否包含技能正文")

    @field_validator("channels")
    @classmethod
    def _non_empty(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and not v:
            raise ValueError("channels 不得为空列表")
        return v

    def overrides(self) -> dict:
        """转成 `SkillService.make_router` 可接受的覆盖参数。"""
        return {
            k: getattr(self, k)
            for k in ("top_k", "recall_n", "expand_query", "channels",
                      "weights", "min_coverage", "min_score", "phase_bonus")
            if getattr(self, k) is not None
        }


class ReloadRequest(BaseModel):
    """`POST /api/skills/reload` 请求体。"""

    model_config = ConfigDict(extra="forbid")

    apply_metadata_overlay: bool = Field(
        True, description="是否用规则推断补齐缺失的路由元数据"
    )


class ExpandRequest(BaseModel):
    """`POST /api/lexicon/expand` 请求体。"""

    query: str = Field(..., min_length=1, max_length=2000)


class BenchRunRequest(BaseModel):
    """`POST /api/bench/run` 请求体——在基准上跑一组查询时配置。"""

    bench_path: str | None = Field(None, description="基准文件路径，缺省用默认")
    name: str = Field("api", max_length=80)
    top_k: int = Field(5, ge=1, le=50)
    channels: list[Channel] | None = None
    expand_query: bool | None = None
    min_coverage: float | None = Field(None, ge=0.0, le=1.0)
