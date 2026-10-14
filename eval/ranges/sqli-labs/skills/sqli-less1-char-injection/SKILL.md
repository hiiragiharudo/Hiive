---
name: sqli-less1-char-injection
description: >-
  SQL 注入测试（GET 字符型）：向数字型/字符型参数投放引号与注释符，
  通过回显差分判定参数是否进入 SQL 语句，再用 UNION 验证可利用性。
  当 URL 参数被直接拼进查询且页面有回显时使用。
domains: [web]
phase: discovery
triggers:
  - SQL 注入
  - 字符型注入
  - UNION 注入
  - 报错注入
targets: [sqli-labs, mysql, php]
requires: [lab-recon-endpoints]
risk: low
provides: [finding]
---

# SQL 注入测试（GET 字符型）

## 判据（**差分法，不看报错**）

本靶场的 `sql-connect.php` 里有 `@error_reporting(0)`，**SQL 报错被有意屏蔽**。
因此"是否出现报错"不是可靠判据，会得出**假阴性**。改用四步差分：

| 步骤 | 请求 | 期望 |
|---|---|---|
| 1 基线 | `id=1` | 有回显（`Your Login name:Dumb`） |
| 2 破坏 | `id=1'` | 回显消失 —— 证明引号进入了 SQL |
| 3 修复 | `id=1'-- -` | 回显恢复 —— 证明破坏确由未转义引号引起 |
| 4 利用 | `id=-1' UNION SELECT 1,2,3-- -` | 回显出注入的值 —— **可利用的硬证据** |

第 2 步只证明「参数未转义」，第 4 步才证明「注入可利用」。**两者都做才算完成验证。**

## 为什么必须做第 3 步

只看"回显消失"是不够的：回显消失也可能是别的原因（参数校验、业务逻辑分支）。
用注释符修复后回显恢复，才能把因果锁定在"未转义的引号"上。

## 边界

- 只做**只读**验证（SELECT），不 INSERT/UPDATE/DELETE，不拖库；
- UNION 回显验证只看注入位，不导出其它表的数据。
