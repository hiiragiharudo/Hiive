---
name: path-traversal-static-file
description: >-
  目录遍历：静态资源或文件下载接口的路径参数未做规范化时，
  用 ../ 序列可读取预期目录之外的文件。
domains: [web]
phase: discovery
triggers:
  - 目录遍历
  - 路径穿越
  - 任意文件读取
targets: [static, lfi]
risk: medium
provides: [finding]
---

# 目录遍历

## 判据

- 正常请求：`file=normal.txt` → 响应体是文件内容本身；
- 遍历请求：`file=../../etc/passwd` → 响应体出现目标系统文件的特征内容。

必须与正常请求对照，否则无法区分"读到了"和"回显了参数"。
