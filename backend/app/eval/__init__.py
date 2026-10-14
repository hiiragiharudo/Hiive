"""评测模块。

- ``probes``：**探针集**——14 条查询的种子评测集，用于快速诊断与消融实验。
- 正式的 ``SkillRoute-Bench``（M4，200+ 条带标注真值）将置于 ``bench`` 模块。

**探针集不是正式基准**：规模小、由单人标注、未公开标注指南。
它只用于开发期快速定位失效模式，**不能作为论文的实验依据**。
"""

from .probes import PROBES, EvalStats, evaluate_routing

__all__ = ["PROBES", "EvalStats", "evaluate_routing"]
