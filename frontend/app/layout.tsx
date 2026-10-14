import type { Metadata } from "next";

import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hiive 控制台",
  description:
    "技能驱动的 AI 渗透测试平台 —— 检索路由可视化、技能库管理与能力评测看板",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="shell">
          <Nav />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
