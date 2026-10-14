"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { ArbitrationOutcome, ArbitrationTable, RuleItem, RulesList } from "@/lib/types";

/** 触发词冲突场景的演示输入——模拟"5 个总路由型技能同时被检索到"。 */
const DEMO_CANDIDATES = [
  ["src-6k-skill", "pent3st", "vibe-pentest", "hack-skills", "aboutsecurity"],
  ["pent3st", "vibe-pentest"],
  ["src-6k-skill", "hack-skills", "idor-broken-object-authorization"],
  ["cve-yu2", "secknowledge-skill"],
];

export default function RulesPage() {
  const [list, setList] = useState<RulesList | null>(null);
  const [ab, setAb] = useState<ArbitrationTable | null>(null);
  const [open, setOpen] = useState<RuleItem | null>(null);
  const [error, setError] = useState("");
  const [demo, setDemo] = useState<{ input: string[]; out: ArbitrationOutcome } | null>(
    null,
  );
  const [busy, setBusy] = useState("");

  const load = useCallback(() => {
    api
      .rules(true)
      .then(setList)
      .catch((e: Error) => setError(e instanceof ApiError ? e.message : String(e)));
    api
      .arbitration()
      .then(setAb)
      .catch(() => setAb(null));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runDemo = async (names: string[]) => {
    setBusy(names.join(","));
    setError("");
    try {
      const out = await api.arbitrationEnforce(names);
      setDemo({ input: names, out });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy("");
    }
  };

  return (
    <>
      {error && <div className="notice err">{error}</div>}

      {/* ---------------------------------------------------------- 仲裁表 */}
      {ab && (
        <div className="card">
          <h2>
            ★ 技能仲裁表
            <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
              人工撰写的路由仲裁规则，已解析为机器可强制的约束
            </span>
          </h2>

          <div className="notice warn">
            <b>为什么需要仲裁？</b>技能可以在自己的 <code>description</code> 里
            <b>自称</b>为"总路由/入口/必须触发"，而规范对此没有任何约束。
            笔者的实践语料记录了后果：
            <b>
              5 个技能抢同一触发词、4 个自称总路由，导致同一输入可能走 4 条不同路线 →
              行为不一致
            </b>
            。本页展示的仲裁表就是对该问题的形式化解答。
          </div>

          <div className="metrics">
            <div className="metric">
              <div className="k">唯一入口</div>
              <div className="v small mono">{ab.entry.join(", ") || "—"}</div>
            </div>
            <div className="metric">
              <div className="k">总路由型技能</div>
              <div className="v">{ab.umbrella_skills.length}</div>
            </div>
            <div className="metric">
              <div className="k">总路由型上限</div>
              <div className="v">{ab.max_umbrella_skills}</div>
            </div>
            <div className="metric">
              <div className="k">执行技能上限</div>
              <div className="v">{ab.max_execution_skills}</div>
            </div>
            <div className="metric">
              <div className="k">议题仲裁</div>
              <div className="v">{ab.topic_arbiters}</div>
            </div>
            <div className="metric">
              <div className="k">禁止组合</div>
              <div className="v">{ab.forbidden_combos}</div>
            </div>
          </div>

          {ab.parse_warnings.length > 0 && (
            <div className="notice err mt">
              解析告警：{ab.parse_warnings.join("；")}
            </div>
          )}

          <h3>总路由型技能（自称入口的）</h3>
          <div className="pill-list">
            {ab.umbrella_skills.map((s) => (
              <span key={s} className="badge high">
                {s}
              </span>
            ))}
          </div>

          <h3>禁止同时加载的组合</h3>
          <table>
            <thead>
              <tr>
                <th>组合</th>
                <th>原因（引自语料原文）</th>
              </tr>
            </thead>
            <tbody>
              {ab.forbidden.map((f, i) => (
                <tr key={i}>
                  <td className="mono">
                    {f.skills.length >= 2
                      ? f.skills.join("  +  ")
                      : `任何 ${f.max_count + 1} 个以上「总路由」型技能`}
                  </td>
                  <td className="small dim">{f.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>任务类型路由（一次最多 1 个执行技能）</h3>
          <table>
            <thead>
              <tr>
                <th>任务类型</th>
                <th>加载</th>
                <th>不加载</th>
              </tr>
            </thead>
            <tbody>
              {ab.task_routes.map((t, i) => (
                <tr key={i}>
                  <td className="small">{t.task_type}</td>
                  <td className="mono small" style={{ color: "var(--ok)" }}>
                    {t.load.join(", ") || "—"}
                  </td>
                  <td className="mono small dim">{t.not_load.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>议题仲裁（同一议题多技能有说法时以谁为准）</h3>
          <table>
            <thead>
              <tr>
                <th>议题</th>
                <th>仲裁</th>
                <th>理由</th>
              </tr>
            </thead>
            <tbody>
              {ab.topics.map((t, i) => (
                <tr key={i}>
                  <td className="small">{t.topic}</td>
                  <td className="mono small" style={{ color: "var(--accent)" }}>
                    {t.winners.join(" + ")}
                  </td>
                  <td className="small dim">{t.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {ab.motto && (
            <>
              <h3>一句话总则（语料原文）</h3>
              <div className="body mono" style={{ maxHeight: 200 }}>
                {ab.motto}
              </div>
            </>
          )}
        </div>
      )}

      {/* ---------------------------------------------------------- 仲裁演示 */}
      <div className="card">
        <h2>仲裁强制执行演示</h2>
        <div className="small dim">
          给定一组<b>按路由排序</b>的候选技能，观察仲裁丢弃哪些、以及丢弃原因。
          仲裁丢弃时<b>保留排名更高者</b>——不引入新的偏好。
        </div>
        <div className="pill-list mt">
          {DEMO_CANDIDATES.map((c, i) => (
            <button key={i} disabled={busy !== ""} onClick={() => void runDemo(c)}>
              {busy === c.join(",") ? "执行中…" : c.slice(0, 3).join(" + ") + (c.length > 3 ? " …" : "")}
            </button>
          ))}
        </div>

        {demo && (
          <div className="mt">
            <div className="small">
              <b>输入（按排名）</b>：
              <span className="mono">{demo.input.join("  >  ")}</span>
            </div>
            <div className="small mt">
              <b>保留</b>：
              <span className="mono" style={{ color: "var(--ok)" }}>
                {demo.out.kept.join(", ") || "（空）"}
              </span>
            </div>
            {demo.out.dropped.length > 0 && (
              <>
                <div className="small mt">
                  <b>丢弃 {demo.out.dropped.length} 项</b>：
                </div>
                {demo.out.dropped.map((d, i) => (
                  <div key={i} className="reason" style={{ marginTop: 6 }}>
                    <span className="mono" style={{ color: "var(--bad)" }}>
                      ✂ {d.name}
                    </span>{" "}
                    <span className="dim">— {d.reason}</span>
                  </div>
                ))}
              </>
            )}
            {demo.out.applied_constraints.length > 0 && (
              <div className="small mt dim">
                应用的约束：{demo.out.applied_constraints.join("；")}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ---------------------------------------------------------- 规则层 */}
      {list && (
        <div className="card">
          <h2>
            规则层
            <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
              始终生效的约束（与技能的"按需检索"正交）
            </span>
          </h2>
          <div className="metrics">
            <div className="metric">
              <div className="k">规则条数</div>
              <div className="v">{list.count}</div>
            </div>
            <div className="metric">
              <div className="k">恒适用</div>
              <div className="v">{list.always_on}</div>
            </div>
            <div className="metric">
              <div className="k">全文 token</div>
              <div className="v">
                {(list.total_estimated_tokens / 1000).toFixed(1)}
                <span className="dim small">k</span>
              </div>
            </div>
            <div className="metric">
              <div className="k">仅规则头 token</div>
              <div className="v ok">{list.header_tokens_if_all_headers_kept}</div>
            </div>
            <div className="metric">
              <div className="k">冲突裁决条目</div>
              <div className="v">{list.conflict_topics}</div>
            </div>
          </div>
          <div className="notice ok mt small">
            <b>约束层自身的上下文经济学</b>：{list.count} 条规则全文约{" "}
            {list.total_estimated_tokens.toLocaleString()} token，但规则头（名称+摘要）仅{" "}
            <b>{list.header_tokens_if_all_headers_kept} token</b>。因此本实现
            <b>只常驻规则头，正文按需加载</b>——与技能的渐进披露是同一策略。
            这说明"约束层也要做上下文经济学"，是本课题论点的一个佐证。
          </div>

          <h3>冲突裁决表</h3>
          <table>
            <thead>
              <tr>
                <th>议题</th>
                <th>以谁为准</th>
                <th>理由</th>
              </tr>
            </thead>
            <tbody>
              {list.conflict_resolution.map((c, i) => (
                <tr key={i}>
                  <td className="small">{c.topic}</td>
                  <td className="mono small" style={{ color: "var(--accent)" }}>
                    {c.winner === "__rules__" ? "（全部 rules）" : c.winner}
                  </td>
                  <td className="small dim">{c.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>规则列表</h3>
          <table>
            <thead>
              <tr>
                <th>规则</th>
                <th>恒适用</th>
                <th>主题</th>
                <th>摘要</th>
                <th className="num">token</th>
              </tr>
            </thead>
            <tbody>
              {list.rules.map((r) => (
                <tr key={r.name} onClick={() => setOpen(r)} style={{ cursor: "pointer" }}>
                  <td className="mono">{r.name}</td>
                  <td>{r.always && <span className="badge on">恒适用</span>}</td>
                  <td className="small dim">{r.topics.join(", ")}</td>
                  <td className="small dim">{r.summary.slice(0, 70)}</td>
                  <td className="num">{r.estimated_tokens.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <div className="card">
          <h2>
            <span className="mono">{open.name}</span>
            <button className="link" style={{ marginLeft: 12 }} onClick={() => setOpen(null)}>
              关闭
            </button>
          </h2>
          <div className="small dim">
            {open.title} ｜ {open.estimated_tokens.toLocaleString()} token ｜{" "}
            {open.always ? "恒适用" : "按需适用"}
          </div>
          <div className="body" style={{ maxHeight: 460 }}>
            {open.body}
          </div>
        </div>
      )}
    </>
  );
}
