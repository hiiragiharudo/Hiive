---
name: dvwa-recon-modules
description: >-
  DVWA 模块侦察：登录后确认会话有效并访问 SQL 注入模块入口，产出端点资产。
  当需要先建立会话再测试 DVWA 各漏洞模块时使用。
domains: [web]
phase: recon
triggers:
  - 靶场侦察
  - DVWA 侦察
  - 模块入口
  - 会话确认
targets: [dvwa, php]
risk: low
provides: [endpoint]
---

# DVWA 模块侦察

## 前置：会话

DVWA **必须先登录**才能访问漏洞模块，未登录会被重定向到 `login.php`。
本平台的靶场配置（`eval/ranges/profiles.json`）已声明登录步骤，
适配器会保持会话 cookie，因此技能本身只需按路径访问。

> **注意 DVWA 的登录带 CSRF token**：`login.php` 调 `checkToken()`，
> 不带 `user_token` 直接 POST 会**返回 200 但未登录**（静默失败）。

## 安全级别

DVWA 默认级别是 `impossible`，**该级别下各模块给出的是安全的实现（无漏洞）**。
因此登录后必须把级别切到 `low`——这一步也由靶场配置声明。

## 判据

访问 index 确认已登录，再访问 SQLi 模块入口确认可达。
