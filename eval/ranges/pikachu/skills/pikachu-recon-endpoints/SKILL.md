---
name: pikachu-recon-endpoints
description: >-
  Pikachu 靶场端点侦察：访问首页与关键漏洞模块入口，确认服务在线并记录可测端点，
  产出端点资产供后续测试技能使用。
domains: [web]
phase: recon
triggers:
  - 靶场侦察
  - 端点枚举
  - pikachu 侦察
targets: [pikachu, php]
risk: low
provides: [endpoint]
---

# Pikachu 端点侦察

对靶场首页与模块入口做受控 GET 探测，记录端点资产。

## 纪律

- 只读探测，不改数据；
- 遵守适配层节流（默认 0.2 s 间隔）；
- **未记入攻击图的端点不算已覆盖**。
