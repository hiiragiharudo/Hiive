---
name: pikachu-xss-reflected
description: >-
  反射型 XSS：向回显型参数投放带标签的唯一探针，若标签被**原样**写入响应
  （未经 HTML 实体编码），即证明存在反射型跨站脚本。当参数值被直接输出到页面时使用。
domains: [web]
phase: discovery
triggers:
  - 反射型 XSS
  - 跨站脚本
  - xss
  - 参数回显
targets: [pikachu, php]
requires: [pikachu-recon-endpoints]
risk: low
provides: [finding]
---

# 反射型 XSS

## 判据：必须断言「标签未被编码」

| 步骤 | 请求 | 期望 |
|---|---|---|
| 1 基线 | `message=hiive_probe_7f3a` | 探针原样回显（证明参数会被输出到页面） |
| 2 注入 | `message=<b>hiive_probe_7f3a</b>` | 响应体中出现**未编码的 `<b>hiive_probe_7f3a</b>`** |

**只看「探针出现」是不够的。** 若页面把 `<` 转义成 `&lt;`，探针字符串仍然"出现"，
但那**不是 XSS**，只是安全的信息回显。因此第 2 步断言的是**带标签的原文**，
这是"回显"与"可执行 XSS"的分界。

## 为什么用唯一探针

探针串 `hiive_probe_7f3a` 不可能自然出现在页面里，因此"出现"必然是反射所致，
排除把页面固有内容误判为反射。

## 边界

- 探针只用无害标签（`<b>`），**不投放脚本执行 payload**（如 `alert`／窃取 cookie）；
- 只验证反射与编码情况，不构造实际攻击链。
