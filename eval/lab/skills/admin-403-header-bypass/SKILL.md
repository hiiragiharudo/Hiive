---
name: admin-403-header-bypass
description: >-
  访问控制绕过：管理后台或受限路径返回 403 时，尝试用路径混淆与伪造请求头
  （X-Original-URL、X-Rewrite-URL、X-Forwarded-For 等）绕过前置鉴权。
domains: [web]
phase: discovery
triggers:
  - 403 绕过
  - 访问控制绕过
  - 后台
  - 越权访问
targets: [admin, nginx]
risk: medium
provides: [finding]
---

# 403 绕过

## 判据

- 基线请求：不带伪造头访问受保护路径 → 期望 403；
- 绕过请求：带上伪造头再访问 → 期望状态码**不再是 403**。

两者同时成立才判定绕过成功。只发一次请求就宣称"绕过成功"是不可靠的——
必须与基线对照。
