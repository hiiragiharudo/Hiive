"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { API_BASE, api } from "@/lib/api";

const NAV = [
  { href: "/", label: "检索路由" },
  { href: "/skills", label: "技能库" },
  { href: "/bench", label: "评测看板" },
];

export default function Nav() {
  const pathname = usePathname();
  const [status, setStatus] = useState<string>("连接中…");
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .health()
      .then((h) => {
        if (!alive) return;
        const loaded = Boolean(h.loaded);
        const n = Number(h.skill_count ?? 0);
        setOk(loaded);
        setStatus(loaded ? `${n} 个技能` : (String(h.error) || "未加载"));
      })
      .catch((e: Error) => {
        if (!alive) return;
        setOk(false);
        setStatus(e.message.slice(0, 60));
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <header className="topbar">
      <div className="brand">
        Hiive<span>·</span>
        <span className="dim small" style={{ marginLeft: 8, fontWeight: 400 }}>
          技能驱动的 AI 渗透测试平台
        </span>
      </div>
      <nav>
        {NAV.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            className={pathname === n.href ? "active" : ""}
          >
            {n.label}
          </Link>
        ))}
      </nav>
      <div className="spacer" />
      <div className="status" title={API_BASE}>
        <span
          className="badge"
          style={{
            borderColor: ok === null ? undefined : ok ? "var(--ok)" : "var(--bad)",
            color: ok === null ? undefined : ok ? "var(--ok)" : "var(--bad)",
          }}
        >
          {ok === null ? "…" : ok ? "已连接" : "未连接"}
        </span>{" "}
        {status}
      </div>
    </header>
  );
}
