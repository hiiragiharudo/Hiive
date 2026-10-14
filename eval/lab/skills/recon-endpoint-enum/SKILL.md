---
name: recon-endpoint-enum
description: >-
  端点枚举与攻击面测绘：从响应与页面中发现可访问的接口路径，产出端点资产。
  当需要先摸清目标有哪些端点、再决定测什么时使用。
domains: [network, web]
phase: recon
triggers:
  - 端点枚举
  - 攻击面
  - 接口发现
targets: [endpoint]
risk: low
provides: [endpoint]
---

# 端点枚举

枚举目标可访问的路径，把发现写入攻击图资产，为后续测试提供输入。

本技能是 `bola-order-id-swap` 的前置技能。
