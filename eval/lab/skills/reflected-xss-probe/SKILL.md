---
name: reflected-xss-probe
description: >-
  反射型 XSS 探测：向搜索、查询类参数投放唯一探针串，若探针被原样反射进
  响应体且未做转义，则判定存在反射型跨站脚本。
domains: [web]
phase: discovery
triggers:
  - 反射型 XSS
  - 跨站脚本
  - xss
  - 搜索框
targets: [search]
risk: low
provides: [finding]
---

# 反射型 XSS 探测

## 判据

投放一个**唯一探针串**（含不可能自然出现的标记），然后在响应体中检索该串：

- 若原样出现 → 判定存在反射（未转义）；
- 若被实体编码或消失 → 判定不存在。

使用唯一探针串是为了避免把页面里本来就有的内容误判为反射。
