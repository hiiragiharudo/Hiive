"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { BenchInfo, BenchMetrics } from "@/lib/types";

/**
 * 预置配置——与 `backend/tools/run_bench.py` 的主干消融一致。
 *
 * 目的：让评委/使用者能**在界面上复现论文里的对照实验**，
 * 而不是只看到一个静态结果表。
 */
const PRESETS: {
  label: string;
  note: string;
  cfg: { channels?: string[]; expand_query?: boolean; min_coverage?: number };
}[] = [
  {
    label: "① 基线（无跨语言）",
    note: "关掉跨语言机制，观察中文查询的召回率塌陷",
    cfg: { channels: ["bm25"], expand_query: false },
  },
  {
    label: "② 仅查询侧扩展",
    note: "当前最优配置",
    cfg: { channels: ["bm25"], expand_query: true },
  },
  {
    label: "③ 加向量通道（等权 RRF）",
    note: "实测：融合反而拖累 BM25",
    cfg: { channels: ["bm25", "vector"], expand_query: true },
  },
  {
    label: "④ 仅向量单通道",
    note: "观察向量通道自身的质量",
    cfg: { channels: ["vector"], expand_query: true },
  },
  {
    label: "⑤ 启用弃权阈值 0.35",
    note: "观察弃权与召回的权衡",
    cfg: { channels: ["bm25"], expand_query: true, min_coverage: 0.35 },
  },
];

export default function BenchPage() {
  const [info, setInfo] = useState<BenchInfo | null>(null);
  const [metrics, setMetrics] = useState<BenchMetrics | null>(null);
  const [topK, setTopK] = useState(5);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [history, setHistory] = useState<BenchMetrics[]>([]);

  useEffect(() => {
    api
      .benchInfo()
      .then(setInfo)
      .catch((e: Error) => setError(e instanceof ApiError ? e.message : String(e)));
  }, []);

  const run = useCallback(
    async (label: string, cfg: (typeof PRESETS)[number]["cfg"]) => {
      setBusy(label);
      setError("");
      try {
        const m = await api.benchRun({ name: label, top_k: topK, ...cfg });
        setMetrics(m);
        setHistory((h) => [...h.filter((x) => x.name !== label), m]);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setBusy("");
      }
    },
    [topK],
  );

  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <>
      {error && <div className="notice err">{error}</div>}

      {info && (
        <div className="card">
          <h2>SkillRoute-Bench</h2>
          <div className="metrics">
            <div className="metric">
              <div className="k">条目</div>
              <div className="v">{info.total}</div>
            </div>
            <div className="metric">
              <div className="k">计分条目</div>
              <div className="v">{info.scored}</div>
            </div>
            <div className="metric">
              <div className="k">弃权用例</div>
              <div className="v">{info.abstention}</div>
            </div>
          </div>
          <div className="small dim mt">
            来源 {JSON.stringify(info.by_source)} ｜ 语言 {JSON.stringify(info.by_lang)}
            <br />
            {info.note}
          </div>
          <div className="notice warn mt small">
            <b>评测对象是「技能调度」，不是「渗透能力」</b>
            ：既有基准（AutoPenBench / Cybench / TSecBench 等）的评测单位是任务或
            Agent，回答「目标打进去了吗」；本基准回答「该给 Agent 看哪些技能」。
            二者正交，本基准不声称替代既有基准。
            <br />
            <b>已知局限</b>：v0 共 {info.total} 条、单人标注，无标注者间一致性数据，
            不足以支撑精细统计推断。详见
            <span className="mono"> docs/SkillRoute-Bench-标注指南.md</span>。
          </div>
        </div>
      )}

      <div className="card">
        <h2>运行对照实验</h2>
        <label className="field" style={{ maxWidth: 200 }}>
          <span>top_k</span>
          <input
            type="number"
            min={1}
            max={20}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          />
        </label>
        <div className="pill-list">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              title={p.note}
              onClick={() => void run(p.label, p.cfg)}
              disabled={busy !== ""}
            >
              {busy === p.label ? "运行中…" : p.label}
            </button>
          ))}
        </div>
        <div className="small dim mt">
          这些预置对应主干消融的每一组配置，可在界面上复现论文中的对照实验。
        </div>
      </div>

      {metrics && (
        <div className="card">
          <h2>
            {metrics.name}
            <span className="dim small" style={{ fontWeight: 400, marginLeft: 10 }}>
              {JSON.stringify(metrics.config)}
            </span>
          </h2>
          <div className="metrics">
            <div className="metric">
              <div className="k">Recall@1</div>
              <div className="v">{pct(metrics["recall@1"])}</div>
            </div>
            <div className="metric">
              <div className="k">Recall@3</div>
              <div className="v">{pct(metrics["recall@3"])}</div>
            </div>
            <div className="metric">
              <div className="k">Recall@5</div>
              <div className="v ok">{pct(metrics["recall@5"])}</div>
            </div>
            <div className="metric">
              <div className="k">MRR（阶段一）</div>
              <div className="v">{metrics.mrr_stage1.toFixed(3)}</div>
            </div>
            <div className="metric">
              <div className="k">弃权准确率</div>
              <div className={`v ${metrics.abstention_accuracy > 0.5 ? "ok" : "bad"}`}>
                {metrics.abstention_correct}/{metrics.abstention_total}
              </div>
            </div>
            <div className="metric">
              <div className="k">元数据节省</div>
              <div className="v">{pct(metrics.meta_saving)}</div>
            </div>
          </div>

          {metrics.abstention_accuracy === 0 && metrics.abstention_total > 0 && (
            <div className="notice warn mt">
              <b>弃权准确率为 0</b>：全部弃权用例都被误路由。
              实测根因是本质性的——RRF 只用排名、丢弃分数大小，其得分与匹配强度无关，
              <b>原理上无法支持基于置信度的弃权</b>；改用 IDF 加权覆盖率后信号分离度仍差
              （两组区间重叠 0.318）。该问题列为独立课题，<b>不声称已解决</b>。
            </div>
          )}

          {metrics.failures.length > 0 && (
            <>
              <h3>未命中（{metrics.failures.length} 条）</h3>
              <table>
                <thead>
                  <tr>
                    <th>类型</th>
                    <th>查询</th>
                    <th>期望</th>
                    <th>实际 top-5</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.failures.map((f) => (
                    <tr key={f.id}>
                      <td>
                        <span
                          className={`badge ${f.failure_kind === "recall" ? "high" : "medium"}`}
                        >
                          {f.failure_kind === "recall" ? "召回失败" : "排序失败"}
                        </span>
                      </td>
                      <td className="small">{f.query}</td>
                      <td className="mono small">{f.expected.join(", ")}</td>
                      <td className="mono small dim">{f.candidates.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="small dim mt">
                「召回失败」= 期望技能未进入候选池；「排序失败」= 进了候选池但没进 top-k。
                二者需要完全不同的修复方向——这是本基准的诊断价值所在。
              </div>
            </>
          )}

          {metrics.false_routes.length > 0 && (
            <>
              <h3>误路由（弃权用例，{metrics.false_routes.length} 条）</h3>
              <table>
                <thead>
                  <tr>
                    <th>查询</th>
                    <th>被误路由到</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.false_routes.map((f) => (
                    <tr key={f.id}>
                      <td className="small">{f.query}</td>
                      <td className="mono small dim">{f.candidates.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}

      {history.length > 1 && (
        <div className="card">
          <h2>本次会话的配置对比</h2>
          <table>
            <thead>
              <tr>
                <th>配置</th>
                <th className="num">R@1</th>
                <th className="num">R@3</th>
                <th className="num">R@5</th>
                <th className="num">MRR</th>
                <th className="num">弃权</th>
              </tr>
            </thead>
            <tbody>
              {history.map((m) => (
                <tr key={m.name}>
                  <td>{m.name}</td>
                  <td className="num">{pct(m["recall@1"])}</td>
                  <td className="num">{pct(m["recall@3"])}</td>
                  <td className="num">{pct(m["recall@5"])}</td>
                  <td className="num">{m.mrr_stage1.toFixed(3)}</td>
                  <td className="num">
                    {m.abstention_correct}/{m.abstention_total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
