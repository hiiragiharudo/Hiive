import type { NextConfig } from "next";

/**
 * 前端通过 `NEXT_PUBLIC_API_BASE` 指向后端（默认 http://127.0.0.1:8000）。
 *
 * 这里**不做 rewrite 代理**：后端已配置 CORS 允许 localhost:3000，
 * 直接跨域调用更简单，也便于把前端部署到别处时只改环境变量。
 *
 * 注意：本文件必须是 `.ts`——`.mjs` 是纯 JS，不支持 `import type` 语法，
 * 写成 `.mjs` 会导致 `Failed to load next.config.mjs: SyntaxError`。
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
