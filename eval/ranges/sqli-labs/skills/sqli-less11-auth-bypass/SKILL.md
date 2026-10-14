---
name: sqli-less11-auth-bypass
description: >-
  登录框 SQL 注入与认证绕过：向用户名/口令字段投放引号与注释符，
  若在口令错误的情况下仍能登录，即证明存在认证绕过；再用 UNION 验证可利用性。
  当站点存在用户名口令表单且后端直接拼接 SQL 时使用。
domains: [web, api]
phase: discovery
triggers:
  - 登录框注入
  - 认证绕过
  - 万能密码
  - POST 注入
targets: [sqli-labs, mysql, php]
requires: [lab-recon-endpoints]
risk: low
provides: [finding]
---

# 登录框 SQL 注入与认证绕过

## 判据（先证伪，再证真）

| 步骤 | 请求 | 期望 |
|---|---|---|
| 1 基线成功 | `uname=admin & passwd=admin` | 登录成功（有回显） |
| 2 **基线失败** | `uname=admin & passwd=wrong` | **登录失败（无回显）** |
| 3 绕过 | `uname=admin' -- - & passwd=wrong` | **登录成功** |
| 4 利用 | `uname=-1' union select 1,2# & passwd=x` | 回显注入的 `1` 与 `2` |

**第 2 步是关键**：必须先证明"口令错误时确实登录失败"，
否则第 3 步的"登录成功"可能只是系统不校验口令——那就不是注入漏洞，而是另一个（更严重的）问题。
**先证伪再证真**是本技能的核心纪律。

## 注释符的选择

- `-- -`（MySQL 要求 `--` 后有空格）与 `#` 在本靶场都有效；
- 判据里两者都试，只要一个成功即可（真实环境中 `#` 常在 URL 里被截断，
  而 `-- -` 更通用）。

## 边界

- 只用**已知存在的账号名**（`admin`）做绕过，不猜测、不爆破其他账号；
- 不做数据导出，UNION 只回显常量位。
