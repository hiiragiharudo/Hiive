"use client";

import type { RouteCost } from "@/lib/types";

/**
 * 成本对比可视化。
 *
 * **刻意展示两项**（元数据项 / 正文项），而不是只给一个"省了 X%"的数字——
 * 因为正文项在两种方案下**相同**（同为 k 个技能），真正的差异在元数据项。
 * 只报总节省会掩盖这一点（见技术设计文档 §5 的成本模型）。
 */
export default function CostComparison({ cost }: { cost: RouteCost }) {
  const base = cost.baseline_tokens || 1;
  const ours = cost.injected_tokens || 1;
  const max = Math.max(base, ours);

  const pct = (v: number) => `${(v / max) * 100}%`;

  return (
    <div className="costbar">
      <div className="small dim" style={{ marginBottom: 6 }}>
        基线 = 全库 {cost.baseline_meta_tokens.toLocaleString()} token 元数据 +
        top-k {cost.body_tokens.toLocaleString()} token 正文 ；本方案 = top-k{" "}
        {cost.injected_meta_tokens.toLocaleString()} token 元数据 + 同样正文
      </div>

      <div className="small dim">基线（agentskills.io 全量注入）</div>
      <div className="track" style={{ marginBottom: 8 }}>
        <div className="seg meta" style={{ width: pct(cost.baseline_meta_tokens) }}>
          {cost.baseline_meta_tokens.toLocaleString()}
        </div>
        <div className="seg body" style={{ width: pct(cost.body_tokens) }}>
          {cost.body_tokens.toLocaleString()}
        </div>
      </div>

      <div className="small dim">本方案（两阶段路由）</div>
      <div className="track">
        <div className="seg meta" style={{ width: pct(cost.injected_meta_tokens) }}>
          {cost.injected_meta_tokens.toLocaleString()}
        </div>
        <div className="seg body" style={{ width: pct(cost.body_tokens) }}>
          {cost.body_tokens.toLocaleString()}
        </div>
      </div>

      <div className="legend">
        <span>
          <i style={{ background: "var(--accent-soft)" }} />
          元数据（O(N) → O(k)）
        </span>
        <span>
          <i style={{ background: "#6e40c9" }} />
          正文（两方案相同）
        </span>
        <span>
          元数据项节省{" "}
          <b className="mono" style={{ color: "var(--ok)" }}>
            {(cost.meta_saving_ratio * 100).toFixed(1)}%
          </b>
        </span>
        <span>
          总开销节省{" "}
          <b className="mono">{(cost.token_saving_ratio * 100).toFixed(1)}%</b>
        </span>
      </div>
    </div>
  );
}
