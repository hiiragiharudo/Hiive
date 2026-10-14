"""探针集与路由评测辅助。

14 条查询（10 中文 + 4 英文），每条标注**期望被召回的技能名片段**。
用于开发期诊断与消融实验。

## 标注纪律

- 真值是"**可接受的答案集合**"，而非"唯一正确"。因此判定采用**片段包含**：
  候选集中任一技能名包含任一期望片段即算命中。这比精确匹配宽松，
  可避免因技能命名差异造成假阴性。
- 中英各半是**刻意设计**：用于量化跨语言鸿沟（见技术设计文档 §6.2）。

## ⚠️ 标注修订记录（必须保留，不得静默改写）

首次运行后诊断发现**两条探针的标注本身有误**，已修订并在此留痕：

| 探针 | 原标注 | 修订后 | 修订理由 |
|---|---|---|---|
| 中文·文件上传 | `["upload","file-upload"]` | 增加 `file-agent` | 语料中 `file-agent` 的描述是「负责文件类漏洞检测：…**任意文件上传**…」，是**中文描述的正确答案**。原标注只列英文名片段，属标注疏漏——这是"只按技能名标注"这一做法的系统性风险。 |
| 中文·WordPress 后台 | `["wordpress","login","401-403","admin"]` | **替换**为「后台返回 403，怎么绕过访问控制」→ `["401-403","bypass"]` | 诊断确认**语料中不存在任何 WordPress 相关技能**，原查询在当前技能库下**不可满足**——不存在正确答案，故其"失败"无意义。原查询属于应被识别为"库中无匹配"的场景，不宜计入命中率分母。 |

> **这两处修订本身就是研究发现**：探针集由单人标注，出现了"不可满足的查询"与
> "只按技能名标注而漏掉中文描述的正确答案"两类错误。**这直接证明了正式基准
> 必须建立公开的标注指南与复核机制**（SkillRoute-Bench 的设计要求），
> 否则任何基于它的结论都不可信。

## 局限（论文中须声明）

规模仅 14 条，且由单人标注（已发现上述 2 处标注错误），**不足以支撑统计结论**。
正式实验必须使用 SkillRoute-Bench（200+ 条，公开标注指南，含置信度与复核）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: (说明, 查询文本, 期望命中的技能名片段)
PROBES: list[tuple[str, str, list[str]]] = [
    ("中文·后台访问控制", "后台页面返回 403，怎么绕过访问控制",
     ["401-403", "bypass"]),
    ("中文·水平越权", "这个接口返回了别人的订单数据，帮我测试水平越权",
     ["bola", "authorization", "idor"]),
    ("中文·域渗透票据", "域环境里如何做 Kerberoasting 拿票据",
     ["kerberos", "active-directory"]),
    ("中文·SQL 注入", "登录框疑似存在 SQL 注入，怎么做报错注入",
     ["sqli", "sql-injection", "injection"]),
    ("中文·SSRF", "一个 URL 参数可能可以访问内网，测试 SSRF", ["ssrf"]),
    ("中文·文件上传", "上传头像的功能想绕过文件类型校验拿 shell",
     ["upload", "file-upload", "file-agent"]),
    ("中文·反序列化", "Java 反序列化漏洞怎么利用", ["deserialization", "java"]),
    ("中文·子域名", "先做信息收集，把子域名和资产都测绘出来",
     ["subdomain", "recon", "asset"]),
    ("中文·提示注入", "测试这个大模型应用有没有提示注入和越狱问题",
     ["prompt", "ai-ml", "llm", "injection"]),
    ("中文·云原生", "容器逃逸和 K8s 集群的提权怎么打",
     ["container", "k8s", "kubernetes", "escape"]),
    ("英文·Kerberos", "Kerberoasting AD ticket attacks", ["kerberos", "active-directory"]),
    ("英文·BOLA", "API object level authorization testing", ["bola", "authorization"]),
    ("英文·upload", "bypass file upload restrictions to get RCE", ["upload"]),
    ("英文·SSRF", "server side request forgery to reach cloud metadata",
     ["ssrf", "cloud", "metadata"]),
]


@dataclass
class ProbeOutcome:
    """单条探针的结果。"""

    label: str
    query: str
    expected: list[str]
    candidates: list[str]
    hit: bool
    is_zh: bool
    result: object = None  # RouteResult
    #: 命中的期望片段
    matched: str = ""
    #: 期望技能在**阶段一完整排序**中的名次（1 起）；0 表示未被召回
    stage1_rank: int = 0

    @property
    def recall_failure(self) -> bool:
        """召回失败：期望技能根本没进入阶段一候选池。"""
        return self.stage1_rank == 0

    @property
    def ranking_failure(self) -> bool:
        """排序失败：被召回了但没进 top-k。"""
        return self.stage1_rank > 0 and not self.hit


@dataclass
class EvalStats:
    """汇总统计。"""

    total: int = 0
    hit: int = 0
    zh_total: int = 0
    zh_hit: int = 0
    en_total: int = 0
    en_hit: int = 0
    outcomes: list[ProbeOutcome] = field(default_factory=list)

    @property
    def failed(self) -> list[ProbeOutcome]:
        return [o for o in self.outcomes if not o.hit]

    @property
    def recall_failures(self) -> list[ProbeOutcome]:
        return [o for o in self.outcomes if o.recall_failure]

    @property
    def ranking_failures(self) -> list[ProbeOutcome]:
        return [o for o in self.outcomes if o.ranking_failure]

    @property
    def mrr(self) -> float:
        """平均倒数名次（仅阶段一排序，衡量纯召回质量）。"""
        if not self.outcomes:
            return 0.0
        s = 0.0
        for o in self.outcomes:
            if o.stage1_rank > 0:
                s += 1.0 / o.stage1_rank
        return s / len(self.outcomes)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "hit": self.hit,
            "zh_hit": self.zh_hit,
            "zh_total": self.zh_total,
            "en_hit": self.en_hit,
            "en_total": self.en_total,
            "hit_rate": round(self.hit / self.total, 4) if self.total else 0.0,
            "zh_hit_rate": round(self.zh_hit / self.zh_total, 4) if self.zh_total else 0.0,
            "en_hit_rate": round(self.en_hit / self.en_total, 4) if self.en_total else 0.0,
            "recall_failures": len(self.recall_failures),
            "ranking_failures": len(self.ranking_failures),
            "mrr_stage1": round(self.mrr, 4),
        }

    def summary(self) -> str:
        d = self.to_dict()
        return (f"总 {d['hit']}/{d['total']}"
                f"  中文 {d['zh_hit']}/{d['zh_total']}"
                f"  英文 {d['en_hit']}/{d['en_total']}"
                f"  | 召回失败 {d['recall_failures']}"
                f" 排序失败 {d['ranking_failures']}"
                f" MRR {d['mrr_stage1']:.3f}")


def evaluate_routing(router, probes: list[tuple[str, str, list[str]]] | None = None) -> EvalStats:
    """对一组探针执行路由并统计命中率。

    除命中率外，还区分**召回失败**与**排序失败**：
    前者需改检索通道/查询扩展，后者需改融合权重或重排——修复方向完全不同。
    """
    probes = probes if probes is not None else PROBES
    stats = EvalStats()
    for label, query, expect in probes:
        is_zh = label.startswith("中文")
        res = router.route(query)
        names = [c.skill.name for c in res.candidates]
        matched = next(
            (n for n in names for e in expect if e in n), ""
        )
        hit = bool(matched)

        # 期望技能在阶段一完整排序中的最好名次
        ranking = getattr(res, "stage1_ranking", []) or []
        stage1_rank = 0
        for i, cand in enumerate(ranking, start=1):
            if any(e in cand for e in expect):
                stage1_rank = i
                break

        stats.total += 1
        stats.hit += int(hit)
        if is_zh:
            stats.zh_total += 1
            stats.zh_hit += int(hit)
        else:
            stats.en_total += 1
            stats.en_hit += int(hit)

        stats.outcomes.append(
            ProbeOutcome(
                label=label, query=query, expected=expect,
                candidates=names, hit=hit, is_zh=is_zh, result=res,
                matched=matched, stage1_rank=stage1_rank,
            )
        )
    return stats
