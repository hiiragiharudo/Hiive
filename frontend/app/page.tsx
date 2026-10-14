"use client";

import { useCallback, useEffect, useState } from "react";

import CandidateCard from "@/components/CandidateCard";
import CostComparison from "@/components/CostComparison";
import { ApiError, api } from "@/lib/api";
import type { RouteResponse } from "@/lib/types";

/** 示例查询——覆盖中英、跨语言、以及"库中无答案"的弃权场景。 */
const EXAMPLES: { label: string; query: string; note?: string }[] = [
  { label: "水平越权", query: "把订单接口的 id 换成别人的能读到他人数据，这是水平越权吗" },
  { label: "域渗透票据", query: "域环境里怎么做 Kerberoasting 拿票据" },
  { label: "文件上传", query: "上传头像的功能只在前端校验扩展名，怎么绕过拿到 webshell" },
  { label: "子域名收集", query: "先做信息收集，把子域名和资产都测绘出来" },
  { label: "403 绕过", query: "后台返回 403，想试试路径混淆和 header 绕过" },
  { label: "提示注入", query: "这个客服大模型能不能用提示注入让它泄露系统提示词" },
  { label: "英文查询", query: "AS-REP roasting and golden ticket attacks against Active Directory" },
  {
    label: "弃权场景",
    query: "MySQL 慢查询怎么优化，加什么索引",
    note: "含 MySQL 但属性能优化，库中无正确答案",
  },
];

export default function RoutePage() {
  const [query, setQuery] = useState(EXAMPLES[0].query);
  const [topK, setTopK] = useState(5);

  const [phase, setPhase] = useState("");
  const [expandQuery, setExpandQuery] = useState(true);
  const [useBm25, setUseBm25] = useState(true);
  const [useVector, setUseVector] = useState(false);
  const [minCoverage, setMinCoverage] = useState(0);
  const [includeBody, setIncludeBody] = useState(false);

  const [result, setResult] = useState<RouteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [defaults, setDefaults] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api
      .config()
      .then((c) => setDefaults(c.query_defaults))
      .catch(() => setDefaults(null));
  }, []);

  const run = useCallback(async () => {
    const q = query.trim();
    if (!q) {
      setError("请输入任务描述");
      return;
    }
    const channels = [useBm25 && "bm25", useVector && "vector"].filter(
      Boolean,
    ) as string[];
    if (channels.length === 0) {
      setError("至少启用一个检索通道");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const r = await api.route({
        query: q,
        top_k: topK,
        state_phase: phase,
        expand_query: expandQuery,
        channels,
        min_coverage: minCoverage,
        include_body: includeBody,
      });
      setResult(r);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [query, topK, phase, expandQuery, useBm25, useVector, minCoverage, includeBody]);

  // Ctrl/Cmd + Enter 提交
  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      void run();
    }
  };

  return (
    <>
      <div className="card">
        <h2>
          两阶段技能路由
          <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
            输入任务描述 → 检索技能库 → 仅注入 top-k 技能的正文
          </span>
        </h2>

        <label className="field">
          <span>任务描述（Ctrl/Cmd + Enter 执行）</span>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="例如：这个接口返回了别人的订单数据，帮我测试水平越权"
          />
        </label>

        <div className="examples">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              title={ex.note ? `${ex.query}\n（${ex.note}）` : ex.query}
              onClick={() => setQuery(ex.query)}
            >
              {ex.label}
            </button>
          ))}
        </div>

        <h3>查询参数（可按请求覆盖，无需重建索引）</h3>
        <div className="row">
          <label className="field">
            <span>top_k（注入技能数）</span>
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span>渗透阶段先验</span>
            <select value={phase} onChange={(e) => setPhase(e.target.value)}>
              <option value="">（不启用）</option>
              <option value="recon">recon 侦察</option>
              <option value="discovery">discovery 探测</option>
              <option value="exploitation">exploitation 利用</option>
              <option value="post">post 后渗透</option>
              <option value="report">report 报告</option>
            </select>
          </label>
          <label className="field">
            <span>弃权阈值（IDF 加权覆盖率）</span>
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={minCoverage}
              onChange={(e) => setMinCoverage(Number(e.target.value))}
            />
          </label>
        </div>

        <div className="row tight" style={{ marginTop: 4 }}>
          <label className="check">
            <input
              type="checkbox"
              checked={expandQuery}
              onChange={(e) => setExpandQuery(e.target.checked)}
            />
            跨语言查询扩展
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={useBm25}
              onChange={(e) => setUseBm25(e.target.checked)}
            />
            BM25 通道
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={useVector}
              onChange={(e) => setUseVector(e.target.checked)}
            />
            向量通道
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={includeBody}
              onChange={(e) => setIncludeBody(e.target.checked)}
            />
            返回正文
          </label>
          <button className="primary" onClick={() => void run()} disabled={loading}>
            {loading ? <span className="spin">◐</span> : "执行路由"}
          </button>
        </div>

        {defaults && (
          <div className="small dim mt">
            后端默认：top_k={String(defaults.top_k)} ｜ 通道{" "}
            {String((defaults.channels as string[])?.join("+"))} ｜ 查询扩展=
            {String(defaults.expand_query)} ｜ 注意：<b>scoring</b>、
            <b>enrich_triggers</b> 等属<b>建索引时</b>参数，改动需在技能库页重建索引。
          </div>
        )}
      </div>

      {error && <div className="notice err">{error}</div>}

      {result && (
        <>
          <div className="card">
            <h2>路由结果</h2>
            <div className="metrics">
              <div className="metric">
                <div className="k">技能库规模</div>
                <div className="v">{result.library_size}</div>
              </div>
              <div className="metric">
                <div className="k">阶段一召回</div>
                <div className="v">{result.stage1_recall}</div>
              </div>
              <div className="metric">
                <div className="k">阶段一耗时</div>
                <div className="v">
                  {(result.timing_ms.stage1 ?? 0).toFixed(1)}
                  <span className="dim small"> ms</span>
                </div>
              </div>
              <div className="metric">
                <div className="k">元数据项节省</div>
                <div className="v ok">
                  {(result.cost.meta_saving_ratio * 100).toFixed(1)}
                  <span className="dim small">%</span>
                </div>
              </div>
              <div className="metric">
                <div className="k">最高覆盖率</div>
                <div
                  className={`v ${result.top_coverage < 0.2 ? "bad" : "warn"}`}
                >
                  {result.top_coverage.toFixed(3)}
                </div>
              </div>
            </div>

            {result.cross_lingual.expanded && (
              <div className="notice ok mt">
                <b>跨语言查询扩展命中：</b>
                {result.cross_lingual.expansion.map((e, i) => (
                  <span key={i} className="badge on" style={{ marginLeft: 6 }}>
                    {e.zh} → {e.en.split(" ")[0]}
                  </span>
                ))}
                <div className="small dim mono" style={{ marginTop: 6 }}>
                  实际检索文本：{result.cross_lingual.retrieval_query}
                </div>
              </div>
            )}

            {result.abstained && (
              <div className="notice warn mt">
                <b>已弃权</b>：覆盖率 {result.top_coverage.toFixed(3)} 低于阈值，
                或两通道均无命中，故不返回任何技能。
                <div className="small dim" style={{ marginTop: 4 }}>
                  弃权是本平台的特色指标。真实使用中用户会问大量与技能库无关的问题，
                  一个总是「硬凑」出 top-k 的检索器会误导 Agent 执行不相关的攻击性技能。
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <h2>上下文成本对比</h2>
            <CostComparison cost={result.cost} />
          </div>

          {result.arbitration?.dropped && result.arbitration.dropped.length > 0 && (
            <div className="card">
              <h2>
                技能仲裁
                <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                  检索返回 {result.candidates.length + result.arbitration.dropped.length} 个，
                  仲裁后保留 {result.candidates.length} 个
                </span>
              </h2>
              <div className="notice warn small">
                <b>为什么需要仲裁？</b>技能可以在自己的 <code>description</code> 里
                <b>自称</b>为"总路由/入口"，规范对此没有约束。语料实测：
                5 个技能抢同一触发词、4 个自称总路由 →
                同一输入可能走 4 条不同路线，<b>行为不一致</b>。
              </div>
              {result.arbitration.dropped.map((d, i) => (
                <div key={i} className="reason" style={{ marginTop: 8 }}>
                  <span className="mono" style={{ color: "var(--bad)" }}>
                    ✂ {d.name}
                  </span>{" "}
                  <span className="dim small">— {d.reason}</span>
                </div>
              ))}
              {!!result.arbitration.applied_constraints?.length && (
                <div className="small dim mt">
                  应用的约束：{result.arbitration.applied_constraints.join("；")}
                </div>
              )}
            </div>
          )}

          {result.attached_rules?.length > 0 && (
            <div className="card">
              <h2>
                适用约束
                <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                  {result.attached_rules.length} 条 · 约束在决策处显式带回，不依赖模型记忆
                </span>
              </h2>
              <table>
                <thead>
                  <tr>
                    <th>规则</th>
                    <th>恒适用</th>
                    <th>主题</th>
                    <th>摘要</th>
                  </tr>
                </thead>
                <tbody>
                  {result.attached_rules.map((r) => (
                    <tr key={r.name}>
                      <td className="mono">{r.name}</td>
                      <td>{r.always && <span className="badge on">恒适用</span>}</td>
                      <td className="small dim">{r.topics.join(", ") || "—"}</td>
                      <td className="small dim">{r.summary.slice(0, 76)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {result.rule_conflicts?.length > 0 && (
                <div className="small dim mt">
                  <b>相关冲突裁决</b>：
                  {result.rule_conflicts
                    .slice(0, 4)
                    .map((c) => `${c.topic} → ${c.winner === "__rules__" ? "以 rules 为准" : c.winner}`)
                    .join("；")}
                </div>
              )}
            </div>
          )}

          <div className="card">
            <h2>
              召回候选
              <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                {result.candidates.length} 个（注入上下文）
              </span>
            </h2>
            {result.candidates.length === 0 ? (
              <div className="dim">无候选（已弃权）</div>
            ) : (
              result.candidates.map((c, i) => (
                <CandidateCard key={c.name} cand={c} rank={i + 1} />
              ))
            )}
          </div>
        </>
      )}

      {!result && !error && (
        <div className="card dim">
          后端接口就绪后，点击「执行路由」即可看到：召回了哪些技能、**为什么召回**
          （命中的字段与各通道名次）、以及相比全量注入节省了多少上下文。
        </div>
      )}
    </>
  );
}
