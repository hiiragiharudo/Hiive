/**
 * 后端 API 客户端。
 *
 * 统一处理错误：把 FastAPI 的 `detail` 提出来（含 422 的校验详情数组），
 * 避免界面只显示 "HTTP 422" 而看不到原因。
 */

import type {
  BenchInfo,
  BenchMetrics,
  RouteResponse,
  SkillDetail,
  SkillStats,
  SkillSummary,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function extractDetail(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const d = (payload as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    // FastAPI 422：detail 是 [{loc, msg, type}, ...]
    if (Array.isArray(d)) {
      return d
        .map((x) => {
          const loc = Array.isArray(x?.loc) ? x.loc.join(".") : "";
          return loc ? `${loc}: ${x?.msg ?? ""}` : String(x?.msg ?? x);
        })
        .join("；");
    }
  }
  return `HTTP ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch (e) {
    throw new ApiError(
      `无法连接后端 ${API_BASE}。请确认已启动：cd backend && python -m uvicorn app.main:app --port 8000`,
      0,
    );
  }
  if (!res.ok) {
    let payload: unknown = null;
    try {
      payload = await res.json();
    } catch {
      /* 忽略非 JSON 响应 */
    }
    throw new ApiError(extractDetail(payload, res.status), res.status);
  }
  return (await res.json()) as T;
}

// --------------------------------------------------------------------- 接口

export interface RouteParams {
  query: string;
  top_k?: number;
  recall_n?: number;
  state_phase?: string;
  expand_query?: boolean;
  channels?: string[];
  min_coverage?: number;
  phase_bonus?: number;
  include_body?: boolean;
}

export const api = {
  health: () => request<Record<string, unknown>>("/api/health"),
  config: () =>
    request<{
      index_time_params: string[];
      query_time_params: string[];
      index_signature: Record<string, unknown>;
      query_defaults: Record<string, unknown>;
      note: string;
    }>("/api/config"),

  skillsStats: () => request<SkillStats>("/api/skills/stats"),
  skillsNames: () => request<{ names: string[] }>("/api/skills/names"),
  skillsList: (p: { q?: string; domain?: string; phase?: string; risk?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(p).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== null) qs.set(k, String(v));
    });
    const s = qs.toString();
    return request<{ total: number; offset: number; limit: number; items: SkillSummary[] }>(
      `/api/skills${s ? `?${s}` : ""}`,
    );
  },
  skillDetail: (name: string) =>
    request<SkillDetail>(`/api/skills/${encodeURIComponent(name)}`),
  reload: (applyMetadataOverlay = true) =>
    request<Record<string, unknown>>("/api/skills/reload", {
      method: "POST",
      body: JSON.stringify({ apply_metadata_overlay: applyMetadataOverlay }),
    }),

  route: (params: RouteParams) =>
    request<RouteResponse>("/api/route", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  expansion: (q: string) =>
    request<{ query: string; expanded: boolean; expansion: { zh: string; en: string }[]; retrieval_query: string }>(
      `/api/route/expansion?q=${encodeURIComponent(q)}`,
    ),

  lexiconStats: () =>
    request<{ total_zh_keys: number; curated_terms: number; mined_pairs: number; sample: { zh: string; en: string[] }[] }>(
      "/api/lexicon/stats",
    ),

  benchInfo: () => request<BenchInfo>("/api/bench/info"),
  benchRun: (body: { name?: string; top_k?: number; channels?: string[]; expand_query?: boolean; min_coverage?: number }) =>
    request<BenchMetrics>("/api/bench/run", { method: "POST", body: JSON.stringify(body) }),
};
