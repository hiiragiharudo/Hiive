---
name: bola-order-id-swap
description: >-
  水平越权（BOLA/IDOR）测试：替换对象标识（订单号、用户 id 等）并比较响应归属，
  若不同标识返回不同属主的数据即判定存在越权。当接口以数字或短标识引用对象时使用。
domains: [api, web]
phase: discovery
triggers:
  - 水平越权
  - 越权
  - 对象标识
  - 换 id
targets: [rest, idor]
requires: [recon-endpoint-enum]
risk: low
provides: [finding]
---

# 水平越权测试

## 判据

对同一接口用两个不同的对象标识各发一次请求：

- 两次均返回 200；
- 两次响应体内容不同（说明返回的是不同属主的数据）。

同时满足即判定存在水平越权。**判据是确定性的**——不依赖模型主观判断。
