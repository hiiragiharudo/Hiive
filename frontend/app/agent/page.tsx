"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { AgentLabInfo, AgentRunResult } from "@/lib/types";

/** 预置场景——覆盖正常流程、假阳性抑制、越界拦截三种情况。 */
const PRESETS: { label: string; note: string; query: string; wrongScope?: boolean }[] = [
  {
    label: "正常流程",
    note: "端点枚举 + 水平越权 + 后台访问控制绕过",
    query: "端点枚举，然后测试接口的水平越权和后台访问控制绕过",
  },
  {
    label: "假阳性抑制",
    note: "靶场搜索框并无 SQL 注入，该技能应被判为假阳性",
    query: "测试搜索框的 SQL 注入",
  },
  {
    label: "全部技能",
    note: "让引擎跑满所有带执行计划的技能",
    query: "端点枚举 水平越权 目录遍历 反射型 XSS 文件上传 访问控制绕过",
  },
  {
    label: "越界拦截",
    note: "故意把授权主机填错，观察作用域强制与越界熔断",
    query: "端点枚举 水平越权 目录遍历 XSS 上传",
    wrongScope: true,
  },
];

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

export default function AgentPage() {
  const [lab, setLab] = useState<AgentLabInfo | null>(null);
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [query, setQuery] = useState(PRESETS[0].query);
  const [hosts, setHosts] = useState("");
  const [maxSteps, setMaxSteps] = useState(10);
  const [topK, setTopK] = useState(5);
  const [maxBlocked, setMaxBlocked] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .agentLab()
      .then((d) => {
        setLab(d);
        setHosts(d.target_host);
      })
      .catch((e: Error) => setError(e instanceof ApiError ? e.message : String(e)));
  }, []);

  const run = useCallback(
    async (q: string, overrideHosts?: string[]) => {
      if (!q.trim()) {
        setError("请输入任务描述");
        return;
      }
      setBusy(true);
      setError("");
      try {
        const hostList = (overrideHosts ?? hosts.split(",").map((h) => h.trim()))
          .filter(Boolean);
        const r = await api.agentRun({
          query: q,
          max_steps: maxSteps,
          top_k: topK,
          hosts: hostList.length ? hostList : undefined,
          max_blocked_calls: maxBlocked,
        });
        setResult(r);
      } catch (e) {
        setResult(null);
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [hosts, maxSteps, topK, maxBlocked],
  );

  const sortedFindings = result
    ? [...result.graph.findings].sort(
        (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
      )
    : [];
  const contrib = result ? Object.entries(result.trace.contribution) : [];

  return (
    <>
      {error && <div className="notice err">{error}</div>}

      {/* ---------------------------------------------------------- 说明 */}
      <div className="card">
        <h2>
          Agent 执行 —— 挖洞结果
          <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
            技能驱动：路由 → 编排 → 执行 → 验证 → 留痕
          </span>
        </h2>
        <div className="notice warn">
          <b>先说清楚"挖洞结果"从哪来。</b>
          本项目<b>不对任何真实目标发起请求</b>（学术与法律红线）。
          全部结果来自 <code>backend/app/agent/target.py</code> 里的
          <b>进程内模拟靶场</b>：不监听端口、无网络 IO、不含可用 exploit，
          漏洞是<b>刻意植入且已知</b>的，因而构成客观真值（ground truth）。
          <br />
          <br />
          <b>判定流程</b>：技能执行动作 → <b>确定性验证判据</b>求值（不调用 LLM）→
          通过的才升级为「发现」，未通过的一律进「被拒绝的候选」。
          <b>技能声称有问题 ≠ 真有问题</b>——这是抑制误报的系统层机制。
        </div>

        {lab && (
          <>
            <h3>靶场植入的漏洞（客观真值）</h3>
            <table>
              <thead>
                <tr>
                  <th>端点</th>
                  <th>漏洞类别</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(lab.planted).map(([ep, desc]) => (
                  <tr key={ep}>
                    <td className="mono small">{ep}</td>
                    <td className="small dim">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="small dim mt">
              靶场主机 <span className="mono">{lab.target_host}</span> ｜
              技能 {lab.skill_count} 个 ｜ 执行计划 {lab.plans.length} 个
            </div>
          </>
        )}
      </div>

      {/* ---------------------------------------------------------- 控制 */}
      <div className="card">
        <h2>运行任务</h2>
        <label className="field">
          <span>任务描述</span>
          <textarea value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>

        <div className="row">
          <label className="field">
            <span>授权主机（逗号分隔；填错即全被拦截）</span>
            <input type="text" value={hosts} onChange={(e) => setHosts(e.target.value)} />
          </label>
          <label className="field">
            <span>最大步数</span>
            <input
              type="number"
              min={1}
              max={50}
              value={maxSteps}
              onChange={(e) => setMaxSteps(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span>top_k</span>
            <input
              type="number"
              min={1}
              max={10}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span>越界熔断阈值</span>
            <input
              type="number"
              min={1}
              max={100}
              value={maxBlocked}
              onChange={(e) => setMaxBlocked(Number(e.target.value))}
            />
          </label>
        </div>

        <div className="pill-list">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              title={p.note}
              disabled={busy}
              onClick={() => {
                setQuery(p.query);
                void run(p.query, p.wrongScope ? ["wrong-host.local"] : [lab?.target_host ?? "lab.local"]);
              }}
            >
              {busy ? "…" : p.label}
            </button>
          ))}
          <button className="primary" disabled={busy} onClick={() => void run(query)}>
            {busy ? "执行中…" : "运行"}
          </button>
        </div>
        <div className="small dim mt">
          预置场景分别演示：① 正常发现流程 ② <b>假阳性被验证门控拒绝</b>
          ③ 跑满所有技能 ④ <b>越界拦截与熔断</b>。
        </div>
      </div>

      {/* ---------------------------------------------------------- 结果 */}
      {result && (
        <>
          <div className="card">
            <h2>执行摘要</h2>
            <div className="metrics">
              <div className="metric">
                <div className="k">执行步数</div>
                <div className="v">{result.summary.steps}</div>
              </div>
              <div className="metric">
                <div className="k">★ 经验证发现</div>
                <div className="v ok">{result.summary.verified_findings}</div>
              </div>
              <div className="metric">
                <div className="k">被拒绝候选</div>
                <div className="v warn">{result.summary.candidates_rejected}</div>
              </div>
              <div className="metric">
                <div className="k">攻击图资产</div>
                <div className="v">{result.summary.assets}</div>
              </div>
              <div className="metric">
                <div className="k">越界拦截</div>
                <div className={`v ${result.summary.blocked_calls ? "bad" : ""}`}>
                  {result.summary.blocked_calls}
                </div>
              </div>
              <div className="metric">
                <div className="k">当前阶段</div>
                <div className="v small">{result.graph.phase}</div>
              </div>
            </div>
            <div className="small dim mt">
              <b>终止原因</b>：{result.summary.terminated_reason}
            </div>
          </div>

          {/* ---- 经验证的发现 ---- */}
          <div className="card">
            <h2>
              ★ 经验证的发现
              <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                {sortedFindings.length} 个 · 每个都通过确定性判据并带证据链
              </span>
            </h2>
            {sortedFindings.length === 0 ? (
              <div className="dim">
                本次没有经验证的发现。
                {result.summary.blocked_calls > 0 &&
                  "（全部请求被作用域拦截 —— 检查上面的授权主机是否填对）"}
              </div>
            ) : (
              sortedFindings.map((f, i) => (
                <div key={i} className="cand">
                  <div className="head">
                    <span className={`badge ${f.severity}`}>{f.severity}</span>
                    <span className="name">{f.kind}</span>
                    <span className="badge">{f.asset}</span>
                    <span className="score">by {f.skill}</span>
                  </div>
                  <div className="reason">
                    <b>判定依据</b>：{f.detail}
                  </div>
                  <div className="chans">
                    <b>证据链</b>：
                    {f.evidence.map((e, j) => (
                      <div key={j} className="mono" style={{ marginTop: 4 }}>
                        {e}
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* ---- 被拒绝的候选 ---- */}
          {result.graph.candidates.length > 0 && (
            <div className="card">
              <h2>
                被拒绝的候选
                <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                  {result.graph.candidates.length} 个 · 技能声称有问题但判据未通过
                </span>
              </h2>
              <div className="notice warn small">
                这一栏是<b>抑制误报的系统层证据</b>：这些技能都执行了、也都"认为"发现了问题，
                但因为<b>确定性验证判据未通过</b>，一律不计入「发现」。
                注意靶场里刻意放了一个必然失败的技能
                <span className="mono"> sqli-search-false-positive</span>
                （搜索接口根本没有 SQL 注入）。
              </div>
              <table>
                <thead>
                  <tr>
                    <th>类别</th>
                    <th>资产</th>
                    <th>来自技能</th>
                    <th>拒绝原因</th>
                  </tr>
                </thead>
                <tbody>
                  {result.graph.candidates.map((c, i) => (
                    <tr key={i}>
                      <td className="mono small">{c.kind}</td>
                      <td className="mono small dim">{c.asset}</td>
                      <td className="mono small">{c.skill}</td>
                      <td className="small" style={{ color: "var(--warn)" }}>
                        {c.rejected_reason}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ---- 执行留痕（回溯） ---- */}
          <div className="card">
            <h2>
              执行留痕
              <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                {result.trace.step_count} 步 · 每步都可审计
              </span>
            </h2>
            {result.trace.steps.map((s) => (
              <div key={s.step} className="cand">
                <div className="head">
                  <span className="rank">#{s.step}</span>
                  <span className="name">{s.skill}</span>
                  {s.phase && <span className="badge accent">{s.phase}</span>}
                  {s.outcome === "executed" ? (
                    s.verified ? (
                      <span className="badge on">已验证</span>
                    ) : (
                      <span className="badge high">判据未过</span>
                    )
                  ) : (
                    <span className="badge">跳过</span>
                  )}
                  <span className="score">
                    {s.tool_calls} 次动作 · {s.cost_tokens} token
                  </span>
                </div>

                {s.outcome === "executed" ? (
                  <>
                    <div className="reason">
                      <b>路由依据</b>：{s.route_reason || "（依赖补齐，非本次路由候选）"}
                    </div>
                    {s.actions.length > 0 && (
                      <div className="chans">
                        <b>动作</b>：
                        {s.actions.map((a, j) => (
                          <div key={j} className="mono" style={{ marginTop: 2 }}>
                            {a.method} {a.path}
                            {a.query ? `?${JSON.stringify(a.query)}` : ""}
                            {a.body ? ` body=${JSON.stringify(a.body)}` : ""}
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="chans">
                      <b>验证判据</b>：
                      {s.verify.map((v, j) => (
                        <div
                          key={j}
                          className="mono"
                          style={{ marginTop: 2, color: v.passed ? "var(--ok)" : "var(--bad)" }}
                        >
                          [{v.passed ? "通过" : "未过"}] {v.kind}: {v.detail}
                        </div>
                      ))}
                    </div>
                    {s.rejected_reason && (
                      <div className="chans" style={{ color: "var(--warn)" }}>
                        <b>拒绝原因</b>：{s.rejected_reason}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="reason">
                    <b>跳过原因</b>：{s.skipped_reason}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* ---- 技能贡献度（回溯） ---- */}
          {contrib.length > 0 && (
            <div className="card">
              <h2>
                技能贡献度
                <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                  回溯统计：某技能实际产出了多少经验证的发现
                </span>
              </h2>
              <table>
                <thead>
                  <tr>
                    <th>技能</th>
                    <th className="num">执行</th>
                    <th className="num">验证</th>
                    <th className="num">命中率</th>
                    <th className="num">动作</th>
                    <th className="num">成本 token</th>
                  </tr>
                </thead>
                <tbody>
                  {contrib
                    .sort((a, b) => b[1].verified - a[1].verified)
                    .map(([name, c]) => (
                      <tr key={name}>
                        <td className="mono">{name}</td>
                        <td className="num">{c.executed}</td>
                        <td className="num">{c.verified}</td>
                        <td
                          className="num"
                          style={{ color: c.hit_rate > 0 ? "var(--ok)" : "var(--bad)" }}
                        >
                          {c.hit_rate.toFixed(2)}
                        </td>
                        <td className="num">{c.tool_calls}</td>
                        <td className="num">{c.cost_tokens.toLocaleString()}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
              <div className="small dim mt">
                命中率 0 的技能<b>不是失败</b>——它可能正确地判定"这里没有漏洞"
                （例如靶场里的假阳性技能）。这张表是论文「技能贡献度」指标的落地。
              </div>
            </div>
          )}

          {/* ---- 攻击图 ---- */}
          <div className="card">
            <h2>攻击图</h2>
            <table>
              <thead>
                <tr>
                  <th>类型</th>
                  <th>资产</th>
                  <th>已测</th>
                  <th>发现者</th>
                </tr>
              </thead>
              <tbody>
                {result.graph.assets.map((a, i) => (
                  <tr key={i}>
                    <td>
                      <span className="badge">{a.kind}</span>
                    </td>
                    <td className="mono small">{a.value}</td>
                    <td>{a.tested ? <span className="badge on">已测</span> : "—"}</td>
                    <td className="mono small dim">{a.discovered_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ---- 工具调用 ---- */}
          {result.tools.blocked > 0 && (
            <div className="card">
              <h2>
                越界拦截
                <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
                  {result.tools.blocked} 次 · 架构级防护，不依赖提示词自觉
                </span>
              </h2>
              <div className="notice err small">
                作用域校验在<b>工具层与靶场层各做一次</b>（纵深防御），且发生在
                <b>路由匹配之前</b>——越界请求不可能触达任何 handler。
                累计拦截达阈值即<b>熔断</b>，不持续冲击被拦目标。
              </div>
              <table>
                <thead>
                  <tr>
                    <th>调用</th>
                    <th>结果</th>
                  </tr>
                </thead>
                <tbody>
                  {result.tools.detail.map((c, i) => (
                    <tr key={i}>
                      <td className="mono small">
                        {String(c.args.url ?? "")}
                      </td>
                      <td className="small" style={{ color: c.blocked ? "var(--bad)" : undefined }}>
                        {c.blocked ? `拦截：${c.error}` : `HTTP ${c.status}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {!result && !error && (
        <div className="card dim">
          点上面任意一个预置场景即可运行。结果会展示：
          <b>经验证的发现（带证据链）</b>、<b>被拒绝的候选</b>、
          逐步执行留痕、技能贡献度回溯、攻击图与越界拦截。
        </div>
      )}
    </>
  );
}
