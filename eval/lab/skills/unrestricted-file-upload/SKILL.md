---
name: unrestricted-file-upload
description: >-
  不安全文件上传：上传接口仅按扩展名或 Content-Type 做校验时，
  提交可执行脚本后缀（.php/.phtml 等）验证是否能落地。
domains: [web]
phase: exploitation
triggers:
  - 文件上传
  - 上传绕过
  - webshell
targets: [upload, php]
risk: high
provides: [finding]
---

# 不安全文件上传

## 判据

提交一个可执行后缀的文件名，若服务端返回接受（且给出落地路径），
则判定存在不安全上传。

**注意**：本技能 `risk: high`，在真实场景中会造成文件写入，
因此默认需要人在环路审批（见引擎的作用域与审批机制）。
