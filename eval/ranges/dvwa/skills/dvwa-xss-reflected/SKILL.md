---
name: dvwa-xss-reflected
description: >-
  DVWA 反射型 XSS 模块测试：向 name 参数投放带标签的唯一探针，
  若标签被**原样**写入响应（未经 HTML 实体编码），即证明存在反射型跨站脚本。
  当参数值被直接输出到页面时使用。
domains: [web]
phase: discovery
triggers:
  - 反射型 XSS
  - 跨站脚本
  - DVWA xss
  - 参数回显
targets: [dvwa, php]
requires: [dvwa-recon-modules]
risk: low
provides: [finding]
---

# DVWA 反射型 XSS

## 判据：编码与否是分界线

| 步骤 | 请求 | 期望 |
|---|---|---|
| 1 基线 | `name=hiive_probe_7f3a` | 探针原样回显（`Hello hiive_probe_7f3a`） |
| 2 注入 | `name=<b>hiive_probe_7f3a</b>` | 响应中出现**未编码的 `<b>hiive_probe_7f3a</b>`** |

第 2 步是关键：若页面把 `<` 转义为 `&lt;`，探针字符串依然"出现"，
但那**不是 XSS**。断言带标签的原文，才能区分「安全回显」与「可执行注入」。

> **对照价值**：把安全级别切到 `impossible` 再跑同一套判据，
> 第 2 步应当**失败**（标签被 `htmlspecialchars` 编码）。
> 这个正反对照本身就是"验证判据有效"的证据，可直接写进论文实验章节。

## 边界

- 探针只用无害标签（`<b>`），不投放 `alert`／窃取 cookie 类 payload；
- 只验证反射与编码情况，不构造实际攻击链。
