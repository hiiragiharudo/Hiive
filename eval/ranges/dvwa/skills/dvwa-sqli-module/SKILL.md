---
name: dvwa-sqli-module
description: >-
  DVWA SQL 注入模块测试：向 id 参数投放单引号触发数据库报错，
  再用 UNION 把可控值回显到页面，从而区分「参数未过滤」与「注入可利用」。
  当数字型参数被直接拼入 SQL 时使用。
domains: [web]
phase: discovery
triggers:
  - SQL 注入
  - DVWA sqli
  - UNION 注入
  - 报错注入
targets: [dvwa, mysql, php]
requires: [dvwa-recon-modules]
risk: low
provides: [finding]
---

# DVWA SQL 注入模块

## 判据（报错 + 利用，两步都要）

| 步骤 | 请求 | 期望 |
|---|---|---|
| 1 基线 | `id=1` | 正常回显（`First name: admin Surname: admin`） |
| 2 报错 | `id=1'` | 出现 `You have an error in your SQL syntax` |
| 3 利用 | `id=-1' union select 1,2#` | 回显 `First name: 1` 与 `Surname: 2` |

**第 2 步与第 3 步的意义不同，缺一不可**：
- 报错只证明「引号进入了 SQL 且未过滤」；
- UNION 回显才证明「注入**可利用**」——攻击者能控制返回内容。

只做第 2 步就下结论，在真实报告里会被质疑"只能触发报错，不能证明影响"。

## 前置

需要先用 `admin/password` 登录，且安全级别为 `low`。
级别为 `impossible` 时该模块使用参数化查询，**上述 payload 全部无效**——
这本身是个好的对照：同一模块在不同级别下的行为差异，正说明漏洞来自实现而非框架。
