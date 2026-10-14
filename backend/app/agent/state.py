"""攻击图状态与发现模型。

**设计动机（见技术设计文档）**：把 Agent 的决策空间从"任意工具调用的组合"
收敛为"在攻击图上选择技能"。因此状态必须显式建模，而不是藏在对话上下文里。

三层结构：
- `Asset`：攻击图节点（域/主机/端点/凭证）
- `Finding`：**经验证**的漏洞候选（未验证的不进 findings，只进 `candidates`）
- `AttackGraph`：整体状态 + 阶段推进

**「发现」与「候选」必须分离**——这是去误报的关键：调研中该领域公认的做法是
"创造性 AI 负责发现，确定性逻辑负责判定真实性"（XBOW 原话）。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

#: 资产类型
ASSET_KINDS = ("domain", "host", "endpoint", "credential")

#: 渗透阶段推进顺序（复用技能元数据的 phase 取值）
PHASE_ORDER = ("recon", "discovery", "exploitation", "post", "report")


@dataclass
class Asset:
    """攻击图节点。"""

    kind: str
    value: str
    tested: bool = False
    discovered_by: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.value}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Finding:
    """**经验证**的漏洞。未通过验证判据的只能进 `AttackGraph.candidates`。"""

    skill: str
    kind: str
    asset: str
    severity: str = "medium"
    verified: bool = False
    evidence: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    """未经（或未通过）验证的漏洞候选——即"疑似发现"。"""

    skill: str
    kind: str
    asset: str
    reason: str = ""
    rejected_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AttackGraph:
    """任务级的攻击图状态。"""

    target: str = ""
    assets: dict[str, Asset] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    executed_skills: list[str] = field(default_factory=list)
    phase: str = "recon"
    step: int = 0

    # ---------------------------------------------------------------- 变更

    def add_asset(self, kind: str, value: str, by: str = "", **meta) -> Asset:
        a = Asset(kind=kind, value=value, discovered_by=by, meta=meta)
        self.assets.setdefault(a.key, a)
        return self.assets[a.key]

    def mark_tested(self, kind: str, value: str) -> None:
        a = self.assets.get(f"{kind}:{value}")
        if a:
            a.tested = True

    def add_finding(self, f: Finding) -> None:
        self.findings.append(f)

    def add_candidate(self, c: Candidate) -> None:
        self.candidates.append(c)

    @property
    def verified_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.verified]

    def advance_phase(self, phase: str) -> None:
        if phase in PHASE_ORDER and phase != self.phase:
            # 只前进不后退，避免阶段震荡
            if PHASE_ORDER.index(phase) > PHASE_ORDER.index(self.phase):
                self.phase = phase

    # ---------------------------------------------------------------- 视图

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "phase": self.phase,
            "step": self.step,
            "assets": [a.to_dict() for a in self.assets.values()],
            "asset_count": len(self.assets),
            "findings": [f.to_dict() for f in self.findings],
            "candidates": [c.to_dict() for c in self.candidates],
            "executed_skills": list(self.executed_skills),
            "verified_count": len(self.verified_findings),
        }

    def summary(self) -> str:
        return (
            f"step={self.step} phase={self.phase} "
            f"资产 {len(self.assets)} 已执行技能 {len(self.executed_skills)} "
            f"发现 {len(self.verified_findings)} 候选 {len(self.candidates)}"
        )
