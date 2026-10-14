"use client";

import { useState } from "react";

import type { RouteCandidate } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  name: "技能名",
  triggers: "触发词",
  description: "描述",
  targets: "适用目标",
  domains: "领域",
  tools: "工具",
};

/**
 * 单个路由候选。
 *
 * 核心价值是**把不可见的检索决策变成可视证据**：
 * - `reason` 与 `matched_fields`：命中在哪个字段（字段得分已归一化）；
 * - 各通道名次与得分：BM25 / 向量分别排第几；
 * - 正文折叠：默认不展示，避免界面被长文淹没。
 */
export default function CandidateCard({
  cand,
  rank,
}: {
  cand: RouteCandidate;
  rank: number;
}) {
  const [showBody, setShowBody] = useState(false);
  const riskCls =
    cand.name && cand.reason ? "" : "";
  const domains = cand.domains ?? [];

  return (
    <div className="cand">
      <div className="head">
        <span className="rank">#{rank}</span>
        <span className="name">{cand.name}</span>
        {cand.phase && <span className="badge accent">{cand.phase}</span>}
        {domains.slice(0, 5).map((d) => (
          <span key={d} className="badge">
            {d}
          </span>
        ))}
        <span className="score">RRF {cand.score.toFixed(5)}</span>
      </div>

      <div className="reason">
        <b>召回依据：</b>
        {cand.reason}
        {cand.matched_fields.length > 0 && (
          <span className="dim">
            {" "}
            （字段：
            {cand.matched_fields
              .map((f) => FIELD_LABELS[f] ?? f)
              .join("、")}
            ）
          </span>
        )}
      </div>

      <div className="desc">{cand.description}</div>

      <div className="meta">
        <span className="badge">
          正文 ≈ {cand.estimated_body_tokens.toLocaleString()} token
        </span>
        {cand.source && <span className="badge">来源 {cand.source}</span>}
        {cand.applicable_rules?.length > 0 && (
          <span className="badge accent" title={cand.applicable_rules.join(", ")}>
            适用约束 {cand.applicable_rules.length}
          </span>
        )}
        <button className="link" onClick={() => setShowBody((v) => !v)}>
          {showBody ? "收起正文" : "查看正文"}
        </button>
      </div>

      <div className="chans">
        通道名次：
        {cand.bm25_rank !== null ? (
          <>
            BM25 #{cand.bm25_rank}（{cand.bm25_score.toFixed(3)}）
          </>
        ) : (
          "BM25 未命中"
        )}
        {" ｜ "}
        {cand.vector_rank !== null ? (
          <>
            向量 #{cand.vector_rank}（{cand.vector_score.toFixed(3)}）
          </>
        ) : (
          "向量未命中"
        )}
      </div>

      {showBody && cand.body && <div className="body">{cand.body}</div>}
      {showBody && !cand.body && (
        <div className="body dim">
          未返回正文。请在左侧勾选「包含技能正文」后重新路由。
        </div>
      )}
    </div>
  );
}
