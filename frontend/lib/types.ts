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
  source: string;
  score: number;
  bm25_score: number;
  vector_score: number;
  bm25_rank: number | null;
  vector_rank: number | null;
  matched_fields: string[];
  reason: string;
  applicable_rules: string[];
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
  attached_rules: AttachedRule[];
  rule_conflicts: { topic: string; winner: string; reason: string }[];
  arbitration: {
    kept?: string[];
    dropped?: { name: string; reason: string }[];
    applied_constraints?: string[];
  };
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

// ---------------------------------------------------------------- 规则层

export interface RuleItem {
  name: string;
  title: string;
  topics: string[];
  domains: string[];
  phases: string[];
  always: boolean;
  summary: string;
  chars: number;
  estimated_tokens: number;
  path: string;
  body?: string;
}

export interface RuleStats {
  count: number;
  total_chars: number;
  total_estimated_tokens: number;
  always_on: number;
  header_tokens_if_all_headers_kept: number;
  conflict_topics: number;
  parse_errors: number;
  note: string;
}

export interface RulesList extends RuleStats {
  rules: RuleItem[];
  conflict_resolution: { topic: string; winner: string; reason: string }[];
}

// ---------------------------------------------------------------- 技能仲裁表

export interface ArbitrationTaskRoute {
  task_type: string;
  load: string[];
  not_load: string[];
}

export interface ArbitrationTopic {
  topic: string;
  winners: string[];
  reason: string;
}

export interface ArbitrationForbidden {
  skills: string[];
  reason: string;
  max_count: number;
  applies_to: string;
}

export interface ArbitrationTable {
  raw_path: string;
  entry: string[];
  umbrella_skills: string[];
  max_execution_skills: number;
  max_umbrella_skills: number;
  /** 注意：后端 `to_dict()` 用列表覆盖了 stats() 里的计数，故此字段是明细列表 */
  task_routes: ArbitrationTaskRoute[];
  topic_arbiters: number;
  forbidden_combos: number;
  has_motto: boolean;
  parse_warnings: string[];
  topics: ArbitrationTopic[];
  forbidden: ArbitrationForbidden[];
  motto: string;
}

export interface ArbitrationOutcome {
  kept: string[];
  dropped: { name: string; reason: string }[];
  applied_constraints: string[];
}

export interface AttachedRule {
  name: string;
  title: string;
  topics: string[];
  always: boolean;
  summary: string;
  estimated_tokens: number;
}

// ---------------------------------------------------------------- Agent 执行

export interface LabRoute {
  name: string;
  method: string;
  path: string;
  status: number;
}

export interface AgentLabInfo {
  skills_dir: string;
  plans_path: string;
  skills: string[];
  skill_count: number;
  plans: string[];
  target_host: string;
  routes: LabRoute[];
  /** 植入的漏洞：端点 -> 说明 */
  planted: Record<string, string>;
  note: string;
}

export interface AgentFinding {
  skill: string;
  kind: string;
  asset: string;
  severity: string;
  verified: boolean;
  evidence: string[];
  detail: string;
}

export interface AgentCandidate {
  skill: string;
  kind: string;
  asset: string;
  reason: string;
  rejected_reason: string;
}

export interface AgentAsset {
  kind: string;
  value: string;
  tested: boolean;
  discovered_by: string;
  meta: Record<string, unknown>;
}

export interface VerifyOutcome {
  kind: string;
  passed: boolean;
  detail: string;
  evidence: string[];
}

export interface AgentStep {
  step: number;
  skill: string;
  phase: string;
  route_score: number;
  route_reason: string;
  /** executed / skipped_no_plan */
  outcome: string;
  skipped_reason: string;
  actions: { method?: string; path?: string; query?: Record<string, string>; body?: Record<string, string> }[];
  tool_calls: number;
  blocked_calls: number;
  verify: VerifyOutcome[];
  verified: boolean;
  finding_kind: string;
  rejected_reason: string;
  new_assets: number;
  cost_tokens: number;
}

export interface ContributionEntry {
  executed: number;
  skipped: number;
  verified: number;
  rejected: number;
  tool_calls: number;
  blocked_calls: number;
  cost_tokens: number;
  reject_reasons: string[];
  hit_rate: number;
}

export interface RangeProfileInfo {
  name: string;
  label: string;
  base_url: string;
  host: string;
  skills_dir: string;
  plans_path: string;
  note: string;
  requires_login: boolean;
  exists: boolean;
}

export interface RangeRuntimeInfo {
  profile: RangeProfileInfo;
  target: {
    kind: string;
    base_url: string;
    host: string;
    delay: number;
    timeout: number;
    calls: number;
    cookies: string[];
  };
  skills: string[];
  skill_count: number;
  plans: string[];
  login_ok: boolean;
  login_detail: string;
  warnings: string[];
}

export interface TargetInfo {
  kind: "simulated" | "range";
  name: string;
  label: string;
  base_url: string;
  login_ok?: boolean;
  login_detail?: string;
  warnings?: string[];
  note?: string;
}

export interface AgentRunResult {
  task_id: string;
  query: string;
  /** 本次使用的目标说明（真实靶场含登录状态与警告） */
  target_info: TargetInfo;
  graph: {
    target: string;
    phase: string;
    step: number;
    assets: AgentAsset[];
    asset_count: number;
    findings: AgentFinding[];
    candidates: AgentCandidate[];
    executed_skills: string[];
    verified_count: number;
  };
  trace: {
    task_id: string;
    query: string;
    terminated_reason: string;
    step_count: number;
    steps: AgentStep[];
    contribution: Record<string, ContributionEntry>;
  };
  routings: RouteResponse[];
  scope: Record<string, unknown>;
  tools: {
    calls: number;
    blocked: number;
    detail: { tool: string; args: Record<string, unknown>; status: number; blocked: boolean; error: string; evidence: string }[];
  };
  summary: {
    steps: number;
    verified_findings: number;
    candidates_rejected: number;
    assets: number;
    blocked_calls: number;
    terminated_reason: string;
  };
}
