"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { SkillDetail, SkillStats, SkillSummary } from "@/lib/types";

export default function SkillsPage() {
  const [stats, setStats] = useState<SkillStats | null>(null);
  const [items, setItems] = useState<SkillSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [domain, setDomain] = useState("");
  const [phase, setPhase] = useState("");
  const [risk, setRisk] = useState("");
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadStats = useCallback(() => {
    api
      .skillsStats()
      .then(setStats)
      .catch((e: Error) => setError(e instanceof ApiError ? e.message : String(e)));
  }, []);

  const loadList = useCallback(() => {
    api
      .skillsList({ q, domain, phase, risk, limit: 200 })
      .then((d) => {
        setItems(d.items);
        setTotal(d.total);
      })
      .catch((e: Error) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [q, domain, phase, risk]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);
  useEffect(() => {
    loadList();
  }, [loadList]);

  const reload = async () => {
    setBusy(true);
    setError("");
    try {
      await api.reload(true);
      loadStats();
      loadList();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {error && <div className="notice err">{error}</div>}

      {stats && (
        <div className="card">
          <h2>
            技能库健康度
            <button
              className="link"
              style={{ marginLeft: 12 }}
              onClick={() => void reload()}
              disabled={busy}
            >
              {busy ? "重建中…" : "重新加载语料并重建索引"}
            </button>
          </h2>
          <div className="metrics">
            <div className="metric">
              <div className="k">技能总数</div>
              <div className="v">{stats.total}</div>
            </div>
            <div className="metric">
              <div className="k">加载耗时</div>
              <div className="v">
                {stats.service.load_ms.toFixed(0)}
                <span className="dim small"> ms</span>
              </div>
            </div>
            <div className="metric">
              <div className="k">建索引</div>
              <div className="v">
                {stats.service.index_ms.toFixed(0)}
                <span className="dim small"> ms</span>
              </div>
            </div>
            <div className="metric">
              <div className="k">基线元数据</div>
              <div className="v">
                {(stats.baseline_meta_tokens / 1000).toFixed(1)}
                <span className="dim small">k tok</span>
              </div>
            </div>
            <div className="metric">
              <div className="k">向量通道</div>
              <div className="v small">{stats.vector_channel}</div>
            </div>
          </div>

          <div className="small dim mt">
            元数据覆盖层：触及{" "}
            {stats.service.overlay_stats?.skills_touched ?? 0} 个技能，填充{" "}
            {stats.service.overlay_stats?.fields_filled ?? 0} 个字段，跳过（语料已声明）{" "}
            {stats.service.overlay_stats?.fields_skipped ?? 0} 个字段。
            <br />
            索引侧触发词富化：{stats.service.enrichment_stats?.enriched ?? 0} 个技能，补入{" "}
            {stats.service.enrichment_stats?.terms_added ?? 0} 个术语。
          </div>

          {!!stats.service.load_report?.duplicates?.length && (
            <div className="notice warn mt">
              <b>同名冲突 {stats.service.load_report.duplicates.length} 组</b>
              （按 name 去重并保留先出现的文件，未静默覆盖）：
              <div className="small mono" style={{ marginTop: 6 }}>
                {stats.service.load_report.duplicates
                  .slice(0, 6)
                  .map((d) => d.name)
                  .join("、")}
              </div>
            </div>
          )}
          {!!stats.service.load_report?.parse_errors?.length && (
            <div className="notice err mt">
              <b>解析错误 {stats.service.load_report.parse_errors.length} 个</b>
            </div>
          )}

          <h3>按阶段分布</h3>
          <div className="pill-list">
            {Object.entries(stats.by_phase).map(([k, v]) => (
              <span key={k} className="badge">
                {k} {v}
              </span>
            ))}
          </div>

          <h3>按安全域分布</h3>
          <div className="pill-list">
            {Object.entries(stats.by_domain)
              .slice(0, 18)
              .map(([k, v]) => (
                <span key={k} className="badge">
                  {k} {v}
                </span>
              ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2>
          技能列表
          <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
            {total} 条
          </span>
        </h2>
        <div className="row">
          <label className="field">
            <span>关键词（名称 / 描述）</span>
            <input type="text" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          <label className="field">
            <span>安全域</span>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="ad / api / web …"
            />
          </label>
          <label className="field">
            <span>阶段</span>
            <select value={phase} onChange={(e) => setPhase(e.target.value)}>
              <option value="">全部</option>
              <option value="recon">recon</option>
              <option value="discovery">discovery</option>
              <option value="exploitation">exploitation</option>
              <option value="post">post</option>
              <option value="report">report</option>
            </select>
          </label>
          <label className="field">
            <span>风险</span>
            <select value={risk} onChange={(e) => setRisk(e.target.value)}>
              <option value="">全部</option>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
          </label>
        </div>

        <table>
          <thead>
            <tr>
              <th>技能名</th>
              <th>阶段</th>
              <th>安全域</th>
              <th>风险</th>
              <th>描述</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr
                key={s.name}
                onClick={() => api.skillDetail(s.name).then(setDetail)}
                style={{ cursor: "pointer" }}
              >
                <td className="mono">{s.name}</td>
                <td>
                  {s.phase && <span className="badge accent">{s.phase}</span>}
                </td>
                <td>
                  <span className="dim small">{(s.domains ?? []).join(", ")}</span>
                </td>
                <td>
                  <span className={`badge ${s.risk}`}>{s.risk}</span>
                </td>
                <td className="dim small">{s.description.slice(0, 90)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="card">
          <h2>
            <span className="mono">{detail.name}</span>
            <button
              className="link"
              style={{ marginLeft: 12 }}
              onClick={() => setDetail(null)}
            >
              关闭
            </button>
          </h2>
          <div className="metrics">
            <div className="metric">
              <div className="k">元数据</div>
              <div className="v">
                {detail.estimated_meta_tokens}
                <span className="dim small"> tok</span>
              </div>
            </div>
            <div className="metric">
              <div className="k">正文</div>
              <div className="v">
                {detail.estimated_body_tokens.toLocaleString()}
                <span className="dim small"> tok</span>
              </div>
            </div>
            <div className="metric">
              <div className="k">正文行数</div>
              <div className="v">{detail.body_lines}</div>
            </div>
          </div>

          <h3>依赖与编排</h3>
          <div className="small">
            requires：<span className="mono">{detail.requires.join(", ") || "—"}</span>
            <br />
            依赖闭包（拓扑序）：
            <span className="mono">{detail.dependency_closure.join(" → ")}</span>
            <br />
            {detail.missing_dependencies.length > 0 && (
              <span style={{ color: "var(--bad)" }}>
                缺失依赖：{detail.missing_dependencies.join(", ")}
              </span>
            )}
            {detail.dependency_cycles.length > 0 && (
              <span style={{ color: "var(--bad)" }}>
                检测到循环依赖：{detail.dependency_cycles.join(", ")}
              </span>
            )}
          </div>

          {detail.enriched_triggers.length > 0 && (
            <>
              <h3>索引侧富化补入的中文触发词</h3>
              <div className="pill-list">
                {detail.enriched_triggers.map((t) => (
                  <span key={t} className="badge on">
                    {t}
                  </span>
                ))}
              </div>
            </>
          )}

          <h3>正文</h3>
          <div className="body" style={{ maxHeight: 420 }}>
            {detail.body}
          </div>
        </div>
      )}
    </>
  );
}
