"""路由元数据的规则化推断（M2）。

## 问题

实测：本机 125 个技能**全部缺失** `phase` / `domains` / `targets` / `triggers`
（§技术设计文档 6.1）。它们只有 agentskills.io 规范要求的 `name` + `description`。
而缺了这些字段，路由就只能靠描述文本的模糊字面匹配——这正是长描述伞状技能霸榜的原因之一。

## 解法：可解释的规则推断，产出「覆盖层」而非改写原文件

**为什么不直接修改 `SKILL.md`？**
1. 那些文件属于第三方技能库（`hack-skills` / `aboutskill` 等），改动会污染上游；
2. 改写第三方文件不可复现、不可回滚；
3. 论文需要区分「原始语料」与「本课题的加工」，混在一起无法做消融。

因此本模块产出 **overlay（覆盖层）**：`技能名 -> 推断元数据` 的映射，
由注册表在加载时合并。原始语料保持字节不变。

## 可解释性

每条推断都记录**命中的规则与关键词**（`explain()`），使人工复核可以只审查
"为什么给它标了 exploitation" 而不是从头读 125 个技能。这是元数据质量可审计的前提。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Skill

# --------------------------------------------------------------------------- 规则表

#: 渗透阶段推断规则。顺序即优先级（先匹配者胜）。
#: 设计依据：按"信息 → 探测 → 利用 → 后渗透 → 报告"的流程推进度排序，
#: 越靠后的阶段越具体，故优先级越高（避免"域渗透"被误判为笼统的 discovery）。
PHASE_RULES: list[tuple[str, list[str]]] = [
    ("report", [
        "报告", "写作", "汇报", "总结", "文档", "模板", "report", "writeup",
        "vuln-report", "finding", "提交",
    ]),
    ("post", [
        "后渗透", "横向", "提权", "持久化", "权限维持", "隧道", "代理", "凭据",
        "票据", "域控", "域内", "内网", "内存", "免杀", "绕过 edr", "c2", "后门",
        "lateral", "privilege escalation", "privesc", "persistence", "credential",
        "kerberos", "kerberoasting", "pass the", "golden ticket", "silver ticket",
        "domain controller", "active directory", "post-exploitation", "exfiltration",
        "tunneling", "pivoting",
    ]),
    ("exploitation", [
        "利用", "exploit", "rce", "getshell", "get shell", "拿 shell", "反弹",
        "payload", "反序列化", "deserialization", "命令执行", "代码执行",
        "command injection", "weaponiz", "bypass", "绕过", "逃逸", "escape",
        "upload", "上传", "shell", "webshell", "攻击链", "chain",
    ]),
    ("recon", [
        "信息收集", "侦察", "资产", "测绘", "子域名", "端口", "目录扫描", "指纹",
        "爬虫", "接口收集", "枚举", "资讯", "情报", "osint", "recon", "reconnaissance",
        "subdomain", "port scan", "fingerprint", "enumeration", "discovery of",
        "attack surface", "footprint", "spider", "crawl", "asset",
    ]),
    ("discovery", [
        "探测", "检测", "测试", "验证", "审计", "扫描", "检查", "排查",
        "detect", "scan", "test", "audit", "assess", "probe", "identify",
        "check", "review", "分析",
    ]),
]

#: 安全域推断规则
DOMAIN_RULES: dict[str, list[str]] = {
    "ad": [
        "active directory", "域控", "域内", "kerberos", "kerberoasting", "ntlm",
        "ldap", "adcs", "certificate services", "gpo", "group policy", "bloodhound",
        "delegation", "acl abuse", "ad 域", "域环境", "域渗透", "票据",
    ],
    "cloud": [
        "cloud", "aws", "azure", "gcp", "aliyun", "阿里云", "腾讯云", "云原生",
        "s3", "oss", "对象存储", "iam", "元数据", "imds", "serverless",
        "lambda", "terraform", "云安全",
    ],
    "container": [
        "docker", "kubernetes", "k8s", "容器", "集群", "pod", "helm",
        "container escape", "容器逃逸", "cgroup", "namespace",
    ],
    "api": [
        "api", "rest", "graphql", "grpc", "swagger", "openapi", "jwt", "oauth",
        "bola", "bfla", "idor", "越权", "接口", "端点", "endpoint",
    ],
    "web": [
        "web", "http", "浏览器", "前端", "后端", "xss", "csrf", "sqli", "sql 注入",
        "ssrf", "xxe", "ssti", "文件上传", "目录遍历", "跨站", "注入", "cookie",
        "session", "web 应用", "网站", "页面", "表单", "参数",
    ],
    "mobile": [
        "android", "ios", "apk", "安卓", "苹果", "移动端", "app", "frida",
        "objection", "mobsf", "逆向 app",
    ],
    "binary": [
        "二进制", "缓冲区", "buffer overflow", "栈溢出", "堆溢出", "格式化字符串",
        "format string", "use after free", "uaf", "rop", "shellcode", "汇编",
        "反汇编", "reverse engineering", "逆向", "pwn", "elf", "pe 文件",
    ],
    "ai": [
        "llm", "大模型", "提示注入", "prompt injection", "越狱", "jailbreak",
        "智能体", "agent", "mcp", "rag", "模型安全", "ai 安全", "对抗样本",
        "chatml", "生成对抗网络",
    ],
    "crypto": [
        "加密", "解密", "密码学", "crypto", "哈希", "hash", "rsa", "aes",
        "des", "base64", "jwt 签名", "签名伪造", "填充预言", "padding oracle",
        "prng", "随机数",
    ],
    "forensics": [
        "取证", "应急响应", "日志分析", "内存取证", "流量分析", "fornsics",
        "forensic", "incident response", "内存镜像", "磁盘镜像", "时间线",
        "痕迹", "att&ck",
    ],
    "network": [
        "网络", "协议", "dns", "tcp", "udp", "arp", "中间人", "mitm", "嗅探",
        "sniff", "vpn", "防火墙", "代理", "内网穿透", "ddos", "流量",
    ],
    "blockchain": [
        "区块链", "智能合约", "solidity", "defi", "以太坊", "ethereum",
        "web3", "重入", "reentrancy", "闪电贷", "flash loan",
    ],
    "iot": [
        "iot", "物联网", "工控", "ics", "scada", "固件", "firmware", "硬件",
        "串口", "modbus", "嵌入式", "路由器",
    ],
    "social": [
        "钓鱼", "社工", "phishing", "social engineering", "水坑", "诱饵",
        "鱼叉", "spear",
    ],
}

#: 适用目标（技术栈/产品）关键词 -> 归一化标签
TARGET_RULES: dict[str, list[str]] = {
    "wordpress": ["wordpress", "wp-", "woocommerce"],
    "spring": ["spring", "springboot", "spring boot", "spring cloud"],
    "struts2": ["struts", "struts2", "ognl"],
    "nginx": ["nginx", "ngx"],
    "apache": ["apache", "httpd"],
    "tomcat": ["tomcat", "jboss", "weblogic", "websphere"],
    "iis": ["iis", "asp.net", "aspx"],
    "php": ["php", "thinkphp", "laravel", "yii", "dedecms", "discuz"],
    "java": ["java", "jdk", "jvm", "shiro", "fastjson", "log4j", "jackson"],
    "python": ["python", "django", "flask", "fastapi", "tornado"],
    "nodejs": ["node.js", "nodejs", "express", "npm"],
    "graphql": ["graphql", "introspection"],
    "jwt": ["jwt", "json web token"],
    "redis": ["redis"],
    "mysql": ["mysql", "mariadb"],
    "mssql": ["mssql", "sql server"],
    "oracle": ["oracle", "plsql"],
    "postgres": ["postgres", "postgresql"],
    "mongodb": ["mongo"],
    "elasticsearch": ["elasticsearch", "elastic"],
    "git": ["git ", ".git", "gitea", "gitlab"],
    "jenkins": ["jenkins", "ci/cd", "流水线"],
    "drupal": ["drupal"],
    "joomla": ["joomla"],
    "confluence": ["confluence", "jira", "atlassian"],
    "wechat": ["微信", "小程序", "公众号", "wechat"],
    "windows": ["windows", "win32", "ntlm"],
    "linux": ["linux", "unix", "bash", "shell 脚本"],
    "kubernetes": ["kubernetes", "k8s"],
    "android": ["android", "apk"],
    "ios": ["ios", "iphone", "ipa"],
    "browser": ["chrome", "firefox", "浏览器", "v8"],
    "metasploit": ["metasploit", "msf"],
    "burp": ["burp"],
    "nmap": ["nmap"],
    "sqlmap": ["sqlmap"],
    "playwright": ["playwright", "puppeteer", "selenium"],
}

#: 风险等级推断（决定是否需要人在环路审批）
RISK_HIGH = [
    "rce", "命令执行", "代码执行", "getshell", "get shell", "拿 shell", "反弹",
    "提权", "privilege escalation", "privesc", "持久化", "删库", "破坏", "拒绝服务",
    "dos", "ddos", "勒索", "加密文件", "横向", "lateral", "域控", "domain controller",
    "写文件", "任意写", "arbitrary write", "反序列化", "deserialization",
    "上传", "upload", "逃逸", "escape", "凭证窃取", "dump", "hashdump",
]
RISK_MEDIUM = [
    "爆破", "brute", "fuzz", "暴破", "密码喷洒", "spray", "枚举", "enumeration",
    "扫描", "scan", "探测", "注入", "injection", "篡改", "绕过", "bypass",
    "越权", "idor", "bola", "竞态", "race",
]

#: 触发词生成的通用停用词（避免把泛化词当作触发词）
_TRIGGER_STOP = {
    "skill", "skills", "use", "when", "this", "that", "the", "and", "for",
    "with", "playbook", "guide", "expert", "测试", "技能", "使用", "调用",
    "方法", "指南", "手册", "说明", "场景",
}

_ASCII_TOKEN = re.compile(r"[a-z][a-z0-9+#._-]{2,}")


# --------------------------------------------------------------------------- 结果

@dataclass
class InferredMetadata:
    """一个技能的推断结果 + 可审计的依据。"""

    name: str
    phase: str = ""
    domains: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    risk: str = "low"
    #: 规则命中的依据：字段 -> 命中的关键词
    evidence: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "domains": self.domains,
            "targets": self.targets,
            "triggers": self.triggers,
            "risk": self.risk,
            "evidence": self.evidence,
        }


# --------------------------------------------------------------------------- 推断


def _search_text(skill: Skill, body_lines: int = 60) -> str:
    """构造用于规则匹配的文本。

    只取正文**开头 N 行**——技能正文常在开头用 `> **AI LOAD INSTRUCTION**`
    声明适用场景，而后续数百行是操作细节。取全文会引入大量与技术栈无关的
    噪声词（例如示例里的 URL、命令），降低推断精度。
    """
    m = skill.meta
    head = "\n".join(skill.body.splitlines()[:body_lines])
    parts = [m.name, m.description, " ".join(m.triggers), head]
    return "\n".join(p for p in parts if p).lower()


def _hits(text: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if k in text]


def infer_phase(text: str) -> tuple[str, list[str]]:
    for phase, keywords in PHASE_RULES:
        hit = _hits(text, keywords)
        if hit:
            return phase, hit[:6]
    return "", []


def infer_domains(text: str) -> tuple[list[str], dict[str, list[str]]]:
    out: list[str] = []
    ev: dict[str, list[str]] = {}
    for domain, keywords in DOMAIN_RULES.items():
        hit = _hits(text, keywords)
        if hit:
            out.append(domain)
            ev[domain] = hit[:5]
    return out, ev


def infer_targets(text: str) -> tuple[list[str], dict[str, list[str]]]:
    out: list[str] = []
    ev: dict[str, list[str]] = {}
    for target, keywords in TARGET_RULES.items():
        hit = _hits(text, keywords)
        if hit:
            out.append(target)
            ev[target] = hit[:3]
    return out, ev


def infer_risk(text: str) -> tuple[str, list[str]]:
    high = _hits(text, RISK_HIGH)
    if high:
        return "high", high[:5]
    med = _hits(text, RISK_MEDIUM)
    if med:
        return "medium", med[:5]
    return "low", []


def infer_triggers(skill: Skill, domains: list[str], targets: list[str]) -> list[str]:
    """生成触发词。

    来源（按可信度降序）：
    1. **技能名分词** —— 名字本身高度浓缩意图（`active-directory-kerberos-attacks`
       → `active directory` / `kerberos` / `attacks`）；
    2. **描述中的英文技术名词** —— 如 `AS-REP roasting`、`BOLA`；
    3. 已声明的 `triggers` 与推断出的 `domains` / `targets`（作为兜底）。
    """
    m = skill.meta
    out: list[str] = []

    # 1) 技能名：连字符/下划线切分为词组与单词
    name_parts = [p for p in re.split(r"[-_/]+", m.name.lower()) if p]
    if len(name_parts) >= 2:
        # 完整词组（去除尾部泛化词）
        joined = " ".join(name_parts).strip()
        for suffix in (" techniques", " attacks", " attack", " testing", " test",
                       " playbook", " guide", " tricks", " vulnerabilities",
                       " vulnerability", " bypass", " abuse"):
            if joined.endswith(suffix):
                joined = joined[: -len(suffix)].strip()
        if joined and joined not in _TRIGGER_STOP and len(joined) > 3:
            out.append(joined)
    out.extend(p for p in name_parts if p not in _TRIGGER_STOP and len(p) > 2)

    # 2) 描述中的英文技术名词（前 12 个不重复项）
    seen = {t.lower() for t in out}
    for tok in _ASCII_TOKEN.findall(m.description.lower()):
        if tok in _TRIGGER_STOP or tok in seen or len(tok) < 4:
            continue
        seen.add(tok)
        out.append(tok)
        if len(out) >= 24:
            break

    # 3) 兜底：已声明触发词 + 域名/目标标签
    for extra in list(m.triggers) + domains + targets:
        if extra and extra.lower() not in seen:
            seen.add(extra.lower())
            out.append(extra)

    # 去重保序
    final: list[str] = []
    for t in out:
        t = t.strip()
        if t and t not in final:
            final.append(t)
    return final[:24]


def infer_skill(skill: Skill) -> InferredMetadata:
    """对单个技能推断路由元数据。"""
    text = _search_text(skill)
    phase, phase_ev = infer_phase(text)
    domains, domain_ev = infer_domains(text)
    targets, target_ev = infer_targets(text)
    risk, risk_ev = infer_risk(text)
    triggers = infer_triggers(skill, domains, targets)

    evidence: dict[str, list[str]] = {}
    if phase_ev:
        evidence["phase"] = phase_ev
    for d, h in domain_ev.items():
        evidence[f"domain:{d}"] = h
    for t, h in target_ev.items():
        evidence[f"target:{t}"] = h
    if risk_ev:
        evidence["risk"] = risk_ev

    return InferredMetadata(
        name=skill.name,
        phase=phase,
        domains=domains,
        targets=targets,
        triggers=triggers,
        risk=risk,
        evidence=evidence,
    )


def infer_all(skills) -> dict[str, InferredMetadata]:
    return {s.name: infer_skill(s) for s in skills}
