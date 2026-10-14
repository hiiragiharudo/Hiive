---
name: lab-recon-endpoints
description: >-
  靶场端点侦察：枚举 sqli-labs 的关键关卡入口与参数，产出端点资产，
  为后续注入测试提供输入。当需要先摸清靶场有哪些可测入口时使用。
domains: [web]
phase: recon
triggers:
  - 靶场侦察
  - 端点枚举
  - 关卡入口
  - sqli-labs 侦察
targets: [sqli-labs, php]
risk: low
provides: [endpoint]
---

# 靶场端点侦察

对靶场入口做一次受控访问，确认服务在线并记录关卡入口，产出端点资产。

## 为什么单独做这一步

真实渗透中"先规划后执行"比"上来就喷 payload"有效得多。
本技能产出攻击图节点，后续技能据此选择测试目标；
这也是"技能驱动 + 攻击图状态"这套架构的最小体现。

## 纪律

- 只做 **GET 探测**，不改数据、不爆破；
- 请求间隔遵守适配层节流；
- 每个入口记入攻击图资产，**未记入的不算已覆盖**。
