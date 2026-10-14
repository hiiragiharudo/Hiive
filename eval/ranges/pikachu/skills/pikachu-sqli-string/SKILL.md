---
name: pikachu-sqli-string
description: >-
  字符型 SQL 注入（报错型）：向查询参数投放单引号，若页面抛出数据库语法错误
  且泄露脚本路径，即证明参数被直接拼接进 SQL。当查询接口由用户输入直接构造 SQL 时使用。
domains: [web]
phase: discovery
triggers:
  - SQL 注入
  - 报错注入
  - 字符型注入
  - pikachu sqli
targets: [pikachu, mysql, php]
requires: [pikachu-recon-endpoints]
risk: low
provides: [finding]
---

# 字符型 SQL 注入（报错型）

## 判据

| 步骤 | 请求 | 期望 |
|---|---|---|
| 1 基线 | `name=vince` | 正常回显（含 `vince@pikachu.com`） |
| 2 注入 | `name=vince'` | 抛出 **`SQL syntax` 数据库错误** |

**为什么本靶场可以看报错，而 sqli-labs 不能？**
判据要**因靶场而异**：Pikachu 直接输出数据库报错（甚至泄露脚本绝对路径），
报错即是可靠证据；而 sqli-labs 的 `sql-connect.php` 有 `@error_reporting(0)`
把报错屏蔽了，那里必须用差分法。**没有通用判据，只有针对目标的判据。**

## 为什么先做基线

"出现报错"可能是页面本来就有的内容（Pikachu 页面引用大量 JS，其中就有含
`error` 字样的资源）。因此：
① 基线先确认正常查询能成功；② 断言精确到 `SQL syntax` 这类**数据库报错特征**，
而不是宽泛的 `error` —— 否则会**假阳性**。这是实测踩到的坑。

## 边界

- 只做只读探测（SELECT / 报错），不导出数据、不写入；
- 报错里泄露的路径信息**只记录不利用**。
