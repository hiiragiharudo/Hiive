/**
 * 后端 API 的响应类型。
 *
 * 与 `backend/app/skills/models.py` 的 `to_dict()` 一一对应。
 * **刻意不引入代码生成**：字段有限，手写可读性更好，
 * 且改动时 TS 编译会直接暴露不匹配。
 */

export interface RouteCandidate {
  name: string;
  description: string;
  phase: string;
  domains: string[];
  score: number;
  bm25_score: number;
  vector_score: number;
  bm25_rank: number | null;
  vector_rank: number | null;
  matched_fields: string[];
  reason: string;
  estimated_body_tokens: number;
  body?: string;
}

export interface RouteCost {
  baseline_meta_tokens: number;
  injected_meta_tokens: number;
  body_tokens: number;
  baseline_tokens: number;
  injected_tokens: number;
  token_saving_ratio: number;
  meta_saving_ratio: number;
}

export interface CrossLingual {
  expanded: boolean;
  expansion: { zh: string; en: string }[];
  retrieval_query: string;
}

export interface RouteResponse {
  query: string;
  top_k: number;
  stage1_recall: number;
  library_size: number;
  state_phase: string;
  retrieval_channels: string[];
  cost: RouteCost;
  cross_lingual: CrossLingual;
  timing_ms: { stage1?: number; stage2?: number };
  candidates: RouteCandidate[];
  applied_overrides: Record<string, unknown>;
  abstained: boolean;
  top_coverage: number;
}

export interface SkillSummary {
  name: string;
  description: string;
  domains: string[];
  phase: string;
  targets: string[];
  triggers: string[];
  requires: string[];
  provides: string[];
  tools: string[];
  risk: string;
  source: string;
  dir_path: string;
}

export interface SkillDetail extends SkillSummary {
  body: string;
  body_lines: number;
  body_chars: number;
  assets: string[];
  enriched_triggers: string[];
  dependency_closure: string[];
  dependency_cycles: string[];
  missing_dependencies: string[];
  estimated_meta_tokens: number;
  estimated_body_tokens: number;
}

export interface SkillStats {
  total: number;
  by_source: Record<string, number>;
  by_phase: Record<string, number>;
  by_domain: Record<string, number>;
  with_triggers: number;
  with_description: number;
  total_body_chars: number;
  baseline_meta_tokens: number;
  full_injection_tokens: number;
  index_build_ms: number;
  vector_channel: string;
  tokenizer: string;
  service: ServiceState;
  lexicon: Record<string, number | boolean>;
}

export interface ServiceState {
  loaded: boolean;
  skill_count: number;
  load_ms: number;
  index_ms: number;
  error: string;
  load_report: {
    loaded?: number;
    by_source?: Record<string, number>;
    duplicates?: { name: string; kept: string; skipped: string }[];
    parse_errors?: { path: string; error: string }[];
    validation_problems?: Record<string, string[]>;
    ok?: boolean;
  };
  enrichment_stats: { enriched?: number; terms_added?: number };
  overlay_stats: { skills_touched?: number; fields_filled?: number; fields_skipped?: number };
}

export interface BenchMetrics {
  name: string;
  total: number;
  scored: number;
  "recall@1": number;
  "recall@3": number;
  "recall@5": number;
  mrr_stage1: number;
  stage1_recall_rate: number;
  abstention_total: number;
  abstention_correct: number;
  abstention_accuracy: number;
  false_route_rate: number;
  meta_saving: number;
  config: Record<string, unknown>;
  failures: {
    id: string;
    query: string;
    expected: string[];
    candidates: string[];
    failure_kind: "recall" | "ranking";
  }[];
  false_routes: { id: string; query: string; candidates: string[] }[];
}

export interface BenchInfo {
  path: string;
  total: number;
  scored: number;
  abstention: number;
  by_source: Record<string, number>;
  by_lang: Record<string, number>;
  note: string;
}
