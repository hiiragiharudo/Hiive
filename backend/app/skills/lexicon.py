"""双语安全术语词典与跨语言查询扩展。

## 问题

路由实测发现**跨语言鸿沟**：技能库中 5 个伞状技能用中文长描述，103 个细粒度
子技能用英文描述（`active-directory-kerberos-attacks` …）。中文查询的字面 token
无法命中英文描述，实测中文查询命中期望技能仅 **2/6**，英文查询 **3/3**。

## 解法（双向，均离线、无 LLM 依赖）

1. **查询侧扩展 `expand_query`**：中文查询中出现词典术语时，追加其英文等价词
   （及缩写），使 BM25/向量通道得以命中英文描述的技能。
2. **索引侧富化 `zh_triggers_for`**：扫描英文描述的技能，反向查表得到中文术语，
   作为该技能的 `triggers` 写入。这使**中文查询的字面 token 直接命中触发词字段**，
   且富化只在建索引时做一次，**每次查询零额外开销**。

两种解法可独立开关，构成消融实验的一组自变量。

## 词典构成（双层）

- **Tier 1 `CURATED`**：人工编写的高精度核心词典。这是驱动路由的主力，
  基于安全领域专业判断编写，覆盖主要漏洞类型与安全域。
- **Tier 2 自动挖掘（`data/lexicon_mined.json`）**：由
  ``backend/tools/mine_lexicon.py`` 从真实 SRC 报告与技能语料中挖掘
  「中文（ENGLISH）」对照写法得到。用于**补充**候选术语，并作为论文中
  「双语领域词典自动构建方法」的方法学证据；其精度须诚实报告。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- Tier 1

#: 人工核心词典：中文术语 -> 英文等价词（含常见缩写）。
#: 键为中文（可为子串匹配），值为英文词/缩写列表。
CURATED: dict[str, list[str]] = {
    # ---- 授权 / 访问控制 ----
    "越权": ["authorization", "access control", "privilege escalation"],
    "水平越权": ["bola", "idor", "broken object level authorization"],
    "垂直越权": ["bfla", "privilege escalation", "function level authorization"],
    "未授权访问": ["unauthorized access", "missing authentication", "broken access control"],
    "权限绕过": ["authorization bypass", "access control bypass"],
    "身份认证": ["authentication", "auth"],
    "认证绕过": ["authentication bypass", "auth bypass"],
    "会话固定": ["session fixation"],
    "会话劫持": ["session hijacking", "session hijack"],
    "密码重置": ["password reset"],
    "弱口令": ["weak password", "weak credentials", "brute force", "default credentials"],
    "暴力破解": ["brute force", "password brute force"],
    "验证码绕过": ["captcha bypass"],
    "双因素": ["two factor", "2fa", "mfa"],
    "单点登录": ["sso", "single sign on"],
    "令牌": ["token", "jwt"],
    "对象标识": ["object id", "identifier", "id parameter"],
    # ---- 注入类 ----
    "注入": ["injection"],
    "SQL注入": ["sql injection", "sqli"],
    "报错注入": ["error based injection", "error based sql injection"],
    "盲注": ["blind injection", "blind sql injection"],
    "布尔盲注": ["boolean based blind injection"],
    "时间盲注": ["time based blind injection"],
    "堆叠注入": ["stacked queries", "stacked injection"],
    "命令注入": ["command injection", "os command injection", "rce"],
    "命令执行": ["command execution", "rce", "remote code execution"],
    "代码执行": ["code execution", "rce"],
    "任意文件读取": ["arbitrary file read", "file read"],
    "任意文件上传": ["arbitrary file upload", "unrestricted file upload"],
    "任意文件下载": ["arbitrary file download", "path traversal"],
    "文件包含": ["file inclusion", "lfi", "rfi", "local file inclusion"],
    "目录遍历": ["directory traversal", "path traversal"],
    "模板注入": ["ssti", "server side template injection", "template injection"],
    "表达式注入": ["expression injection", "el injection", "ognl injection"],
    "反序列化": ["deserialization", "insecure deserialization", "unserialize"],
    "XML外部实体": ["xxe", "xml external entity"],
    "请求走私": ["request smuggling", "http request smuggling"],
    "参数污染": ["http parameter pollution", "hpp"],
    "原型污染": ["prototype pollution"],
    "竞态": ["race condition", "race"],
    # ---- 客户端 ----
    "跨站脚本": ["xss", "cross site scripting"],
    "反射型": ["reflected", "reflected xss"],
    "存储型": ["stored", "persistent", "stored xss"],
    "文档对象模型": ["dom", "dom xss"],
    "跨站请求伪造": ["csrf", "cross site request forgery"],
    "点击劫持": ["clickjacking", "ui redressing"],
    "跨域": ["cors", "cross origin"],
    "内容安全策略": ["csp", "content security policy"],
    "开放重定向": ["open redirect"],
    "子资源完整性": ["sri", "subresource integrity"],
    # ---- 服务端请求类 ----
    "服务端请求伪造": ["ssrf", "server side request forgery"],
    "带外回连": ["oob", "out of band"],
    "DNS重绑定": ["dns rebinding"],
    "云元数据": ["cloud metadata", "imds", "instance metadata"],
    # ---- 业务逻辑 ----
    "业务逻辑": ["business logic"],
    "任意用户注册": ["arbitrary user registration"],
    "支付逻辑": ["payment logic"],
    "条件竞争": ["race condition"],
    "短信轰炸": ["sms bombing"],
    "遍历": ["enumeration"],
    "信息泄露": ["information disclosure", "info leak"],
    "敏感信息": ["sensitive information", "sensitive data"],
    "源码泄露": ["source code disclosure", "source leak", "git leak"],
    # ---- 上传 / 解析 ----
    "文件上传": ["file upload", "upload"],
    "解析漏洞": ["parsing vulnerability", "parser bypass"],
    "类型校验绕过": ["content type bypass", "mime bypass"],
    "黑名单绕过": ["blacklist bypass", "extension bypass"],
    # ---- 侦察 ----
    "信息收集": ["recon", "reconnaissance", "information gathering"],
    "子域名": ["subdomain", "subdomain enumeration"],
    "资产测绘": ["asset discovery", "attack surface mapping"],
    "端口扫描": ["port scan", "port scanning"],
    "目录扫描": ["directory scan", "dirscan", "content discovery"],
    "指纹识别": ["fingerprint", "technology fingerprint"],
    "接口": ["api", "endpoint", "interface"],
    "隐藏接口": ["hidden endpoint", "undocumented api"],
    "后台": ["admin panel", "admin", "backend", "management console"],
    "登录入口": ["login", "login page", "sign in"],
    "管理后台": ["admin panel", "admin console", "cms backend"],
    "编辑器": ["editor", "rich text editor"],
    # ---- 域渗透 ----
    "域": ["active directory", "ad", "domain"],
    "域控": ["domain controller", "dc"],
    "票据": ["ticket", "kerberos ticket"],
    "Kerberos": ["kerberos", "kerberoasting", "as-rep roasting"],
    "黄金票据": ["golden ticket"],
    "白银票据": ["silver ticket"],
    "哈希传递": ["pass the hash", "pth"],
    "票据传递": ["pass the ticket", "ptt"],
    "中继": ["relay", "ntlm relay"],
    "委派": ["delegation"],
    "证书服务": ["adcs", "certificate services"],
    "访问控制列表": ["acl", "access control list"],
    "横向移动": ["lateral movement"],
    "提权": ["privilege escalation", "privesc"],
    "凭据": ["credential", "credentials"],
    "内网": ["internal network", "intranet"],
    # ---- 云原生 / 容器 ----
    "容器": ["container", "docker"],
    "容器逃逸": ["container escape"],
    "集群": ["kubernetes", "k8s", "cluster"],
    "云": ["cloud", "aws", "azure", "aliyun"],
    "对象存储": ["object storage", "s3", "oss"],
    "服务器端模板": ["ssti"],
    # ---- 二进制 / 客户端 ----
    "缓冲区溢出": ["buffer overflow"],
    "格式化字符串": ["format string"],
    "堆溢出": ["heap overflow"],
    "栈溢出": ["stack overflow"],
    "整数溢出": ["integer overflow"],
    "释放后使用": ["use after free", "uaf"],
    "逆向": ["reverse engineering", "reversing"],
    "壳": ["packer", "unpacking"],
    "免杀": ["av evasion", "edr evasion", "bypass av"],
    # ---- 移动端 ----
    "安卓": ["android", "apk"],
    "苹果": ["ios", "iphone"],
    "移动端": ["mobile"],
    "加固": ["obfuscation", "hardening"],
    "抓包": ["traffic capture", "packet capture", "mitm"],
    # ---- AI / LLM ----
    "提示注入": ["prompt injection"],
    "越狱": ["jailbreak"],
    "模型": ["model", "llm"],
    "智能体": ["agent", "ai agent"],
    "工具调用": ["tool calling", "function calling"],
    # ---- 其它 ----
    "中间件": ["middleware"],
    "框架": ["framework"],
    "组件": ["component"],
    "第三方库": ["third party library", "dependency"],
    "供应链": ["supply chain"],
    "配置错误": ["misconfiguration"],
    "默认配置": ["default configuration", "default credentials"],
    "防火墙": ["firewall", "waf"],
    "绕过": ["bypass", "evasion"],
    "日志": ["log", "logging"],
    "审计": ["audit"],
    "应急响应": ["incident response"],
    "取证": ["forensics"],
    "威胁情报": ["threat intelligence"],
    "靶场": ["lab", "range", "ctf"],
    "报告": ["report", "reporting"],
}

#: 自动挖掘层的人工复核白名单：即便频次低也接受的高置信术语
MINED_TRUSTED_EXTRA: dict[str, list[str]] = {
    "反射型跨站脚本": ["reflected cross-site scripting", "reflected xss"],
    "持久型跨站脚本": ["persistent cross-site scripting", "stored xss"],
    "存储型跨站脚本": ["stored cross-site scripting", "stored xss"],
    "基于角色的访问控制": ["rbac", "role based access control"],
    "可信执行环境": ["tee", "trusted execution environment"],
    "安全多方计算": ["mpc", "secure multi party computation"],
    "生成对抗网络": ["gan", "generative adversarial network"],
    "聊天标记语言": ["chatml"],
}


# --------------------------------------------------------------------------- 结构


@dataclass
class LexiconStats:
    curated_terms: int = 0
    mined_pairs: int = 0
    trusted_extra: int = 0
    total_zh_keys: int = 0
    loaded_mined: bool = False

    def to_dict(self) -> dict:
        return {
            "curated_terms": self.curated_terms,
            "mined_pairs": self.mined_pairs,
            "trusted_extra": self.trusted_extra,
            "total_zh_keys": self.total_zh_keys,
            "loaded_mined": self.loaded_mined,
        }


@dataclass
class BilingualLexicon:
    """中英双向术语词典。

    - ``zh_to_en``：中文术语 -> 英文词列表（查询侧扩展用）
    - ``en_to_zh``：英文词（小写）-> 中文术语列表（索引侧富化用）
    """

    zh_to_en: dict[str, list[str]] = field(default_factory=dict)
    en_to_zh: dict[str, list[str]] = field(default_factory=dict)
    stats: LexiconStats = field(default_factory=LexiconStats)
    #: 是否把自动挖掘层并入（默认并入，可用开关做消融）
    include_mined: bool = True

    # ---------------------------------------------------------------- 构建

    @classmethod
    def build(
        cls,
        mined_path: Path | None = None,
        include_mined: bool = True,
        mined_min_count: int = 4,
    ) -> "BilingualLexicon":
        """构建词典。

        参数
        ----
        mined_path
            自动挖掘结果 JSON 路径（可空）。
        include_mined
            是否并入自动挖掘层。
        mined_min_count
            并入自动挖掘层的最低频次门槛。**默认 4**——挖掘实测表明该阈值以下
            噪声显著上升（如 `已修复 <-> login`、`待补 <-> *.md`）。
        """
        lex = cls(include_mined=include_mined)

        for zh, ens in CURATED.items():
            lex._add(zh, ens)
        lex.stats.curated_terms = len(CURATED)

        for zh, ens in MINED_TRUSTED_EXTRA.items():
            lex._add(zh, ens)
        lex.stats.trusted_extra = len(MINED_TRUSTED_EXTRA)

        if include_mined and mined_path and mined_path.exists():
            try:
                payload = json.loads(mined_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
            if payload:
                kept = 0
                for pair in payload.get("pairs", []):
                    if pair.get("count", 0) < mined_min_count:
                        continue
                    zh, en = pair.get("zh", ""), pair.get("en", "")
                    if not _mined_acceptable(zh, en):
                        continue
                    lex._add(zh, [en])
                    kept += 1
                lex.stats.mined_pairs = kept
                lex.stats.loaded_mined = True

        lex.stats.total_zh_keys = len(lex.zh_to_en)
        return lex

    def _add(self, zh: str, ens: list[str]) -> None:
        zh = zh.strip()
        if not zh:
            return
        bucket = self.zh_to_en.setdefault(zh, [])
        for en in ens:
            en = " ".join(str(en).split()).strip().lower()
            if not en:
                continue
            if en not in bucket:
                bucket.append(en)
            rev = self.en_to_zh.setdefault(en, [])
            if zh not in rev:
                rev.append(zh)

    # ---------------------------------------------------------------- 查询侧扩展

    def expand_query(self, query: str) -> tuple[str, list[tuple[str, str]]]:
        """中文查询 -> 追加英文等价词。

        返回 ``(扩展后查询文本, [(命中术语, 追加的英文), ...])``。

        匹配策略：**最长键优先**（`水平越权` 命中后不再重复匹配 `越权`），
        避免同一概念被追加多次而过度加权。
        """
        matched: list[tuple[str, str]] = []
        used_span: list[tuple[int, int]] = []
        q_lower = query.lower()

        for zh in sorted(self.zh_to_en, key=len, reverse=True):
            start = q_lower.find(zh)
            if start < 0:
                continue
            end = start + len(zh)
            if any(not (end <= s or start >= e) for s, e in used_span):
                continue  # 与已匹配的更长期术语重叠
            used_span.append((start, end))
            ens = self.zh_to_en[zh]
            matched.append((zh, " ".join(ens)))

        if not matched:
            return query, []

        addition = " ".join(en for _zh, en in matched)
        return f"{query} {addition}", matched

    # ---------------------------------------------------------------- 索引侧富化

    def zh_triggers_for(self, text: str) -> list[str]:
        """扫描英文文本，反向查表得到中文触发词。

        用于给**英文描述的技能**补充中文 `triggers`，使中文查询的字面 token
        能直接命中。只在建索引时执行一次，查询期零开销。

        **必须使用词边界匹配而非子串匹配。** 实测踩坑：英文键 `id` 用子串匹配会
        命中 `identifier` / `provide` 中的 `id`，导致「不限字段名」这类挖掘噪声被
        富化到大批技能上。改用 ``(?<![a-z0-9])key(?![a-z0-9])`` 后只有独立词才命中。
        """
        t = text.lower()
        out: list[str] = []
        for en, zhs in self.en_to_zh.items():
            if not _word_in(en, t):
                continue
            for zh in zhs:
                if zh not in out:
                    out.append(zh)
        return out


# --------------------------------------------------------------------------- 过滤


#: 英文侧词边界匹配缓存
_WORD_CACHE: dict[str, re.Pattern[str]] = {}


def _word_in(needle: str, haystack_lower: str) -> bool:
    """判断 needle 是否作为**独立词**出现在 haystack 中。

    多词短语（含空格）也支持：要求两侧不是字母数字。
    """
    pat = _WORD_CACHE.get(needle)
    if pat is None:
        pat = re.compile(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])")
        _WORD_CACHE[needle] = pat
    return pat.search(haystack_lower) is not None


#: 术语中不应出现的功能词（用于剔除挖到的句子片段）
_FUNC_WORDS = set("的了就会这那个是在有和与或要能可把被从而对为以及等如若则请我你他它")

#: 报告模板中的**状态词**黑名单。
#:
#: 挖掘噪声中有一类特殊来源：漏洞报告模板的状态字段（`已修复`、`待确认`…）会与
#: 相邻的英文词（如 `已修复（login）`）构成假的术语对。它们不是术语，必须剔除。
#:
#: **注意**：不能简单地禁止中文侧以「已/未/待」开头——`未授权访问`、
#: `待确认漏洞` 中前者是核心术语。因此这里采用**显式枚举**而非词缀规则。
_ZH_STATUS = {
    "已修复", "未修复", "已确认", "待确认", "无法复现", "已提交", "已忽略",
    "已公开", "已审核", "已通过", "未通过", "暂未修复", "忽略", "待补",
    "已验证", "未验证", "已上线", "未上线", "已驳回", "已归档", "待办",
    "暂无", "无", "其他", "其它", "合计", "小计", "总计",
}

#: 形如文件名的英文侧
_FILENAME_RE = re.compile(r"\.(md|txt|pdf|docx?|html?|php|jsp|aspx?|py|js|json|ya?ml)$", re.I)
#: 形如占位符
_PLACEHOLDER_RE = re.compile(r"^(x{3,}|y{3,}|z{3,}|待补|todo|xxx+)$", re.I)
#: 形如 URL/路径
_URLISH_RE = re.compile(r"[/\\]|^https?$|^\d+(\.\d+)*$")


def _mined_acceptable(zh: str, en: str) -> bool:
    """自动挖掘层的人工可复现过滤器。

    挖掘实测中出现的典型噪声（均被本函数拒绝）：
    ``这个就不截图了 <-> xss``（句子片段）、``已修复 <-> login``（报告状态词）、
    ``待补 <-> ai-app-agent-cot-2.md``（占位符+文件名）、
    ``多看临时目录 <-> tmp/temp``（命令+路径）、``某某系统 <-> xxxxx``（占位符）。
    """
    zh = zh.strip()
    en = en.strip()
    if not (2 <= len(zh) <= 8):
        return False
    if any(ch in _FUNC_WORDS for ch in zh):
        return False
    if zh in _ZH_STATUS:
        return False
    if _PLACEHOLDER_RE.match(zh) or _PLACEHOLDER_RE.match(en):
        return False
    if not en or len(en) > 32:
        return False
    if _FILENAME_RE.search(en) or _URLISH_RE.search(en):
        return False
    if len(en.split()) > 4:  # 英文侧过长通常是句子而非术语
        return False
    if not re.search(r"[a-z]{2,}", en):
        return False
    return True
