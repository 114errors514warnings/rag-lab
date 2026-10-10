"""与 RAG 系统解耦的固定评测协议（Fixed Evaluation Protocol）。

设计要点：
- 本包只依赖 pydantic，不导入任何 RAG 实现，被测系统通过 Sut 协议接入。
- 数据集、指标实现、判定规则、报告格式全部"固定"，只有被测系统随阶段变化。

版本历史：
- v1：chunk_id 制检索评测（recall/precision/MRR/citation）。
- v2：证据制评测（gold_evidence 行区间/symbol 覆盖），新增 nDCG、Context Evidence
  Coverage、Citation Support、No-answer Accuracy、宏/微平均。见 `rag_eval/metrics.py`。
  v1 报告与新报告不可直接比，需在报告中注明版本。
"""

EVAL_VERSION = "v2"

__all__ = ["EVAL_VERSION"]
