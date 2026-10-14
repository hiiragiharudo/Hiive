---
name: sqli-search-false-positive
description: >-
  SQL 注入探测：向查询参数投放单引号与布尔对，依据报错或响应差异判断是否存在注入。
  当接口存在数据库交互迹象时使用。
domains: [web]
phase: discovery
triggers:
  - SQL 注入
  - 注入
  - 报错注入
targets: [sql, search]
risk: low
provides: [finding]
---

# SQL 注入探测

## 说明

**本技能在实验靶场中用于演示"验证门控"**：靶场的搜索接口并不存在 SQL 注入，
因此该技能的执行会**产生候选但验证失败**，从而被拒绝、不计入发现。

它验证的是本平台最重要的一条设计原则：
> 只有通过验证判据的候选才能升级为「发现」。**技能声称有问题不等于真有问题。**

这是抑制误报的系统层机制，而不是靠提示模型"不要误报"。
