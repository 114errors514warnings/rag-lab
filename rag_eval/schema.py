"""评测协议的数据契约（固定资产，改动需 bump EVAL_VERSION）。

v2 要点：以**证据**（文件 + 行区间 + symbol）为判定单位，而非 chunk_id。
v1 字段保留，桩系统与旧套件仍可用。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Finding = Literal["PASS", "WARN", "FAIL", "BASELINE", "NO_GATE"]

QueryType = Literal["symbol", "semantic", "dependency", "literal", "no_answer", "update"]
SplitName = Literal["dev", "validation", "holdout", "blind"]


class Evidence(BaseModel):
    """一条证据定位：文件 + 行区间 + 可选 symbol。

    行区间为 1-based 闭区间；symbol 用于代码符号定位题。
    """

    file: str
    start: int | None = None
    end: int | None = None
    symbol: str | None = None
    commit: str | None = None


class EvalCase(BaseModel):
    """一条固定的测试用例。"""

    id: str
    question: str
    #: 期望答案（阶段 4/6 评估忠实度用；阶段 1/3 可为空）
    expected_answer: str | None = None
    #: 标准相关 chunk（v1；v2 以 gold_evidence 为准）
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    #: Code RAG（阶段 5）使用的期望符号
    expected_symbols: list[str] = Field(default_factory=list)
    #: 该用例归属的项目，用于多项目隔离/泄漏检测（阶段 5）
    project_id: str | None = None
    #: 用例来源：dev 用于调参，validation 用于选型，blind 只在冻结后跑（防过拟合）
    split: SplitName = "dev"
    tags: list[str] = Field(default_factory=list)
    #: 若用例是某阶段新增的，记录来源阶段，报告中单独统计，避免"移动球门"
    added_in_stage: str | None = None

    # --- v2 字段 ---
    #: 题型：symbol/semantic/dependency/literal/no_answer/update
    query_type: QueryType | None = None
    #: 最小充分证据集。列表中的每一项要么是单条证据（则整体视为一个充分集），
    #: 要么是一个证据列表（每个内层列表是一个等价充分集）。
    gold_evidence: list = Field(default_factory=list)
    #: 可验证的答案要点（rubric）
    answer_rubric: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    #: 标注人 / 复核状态
    adjudication: dict = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """一条检索单元。v2 用 source/start_line/end_line/symbol 做证据映射。"""

    chunk_id: str
    score: float = 0.0
    source: str | None = None
    project_id: str | None = None
    # --- v2 证据定位 ---
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None


class SystemAnswer(BaseModel):
    """被测系统对一条用例的产出。"""

    answer: str = ""
    retrieved: list[RetrievedChunk] = Field(default_factory=list)
    #: 回答中引用的 chunk_id
    citations: list[str] = Field(default_factory=list)
    #: 最终送进 LLM 的上下文中的 chunk（v2：Context Evidence Coverage 用）
    context_chunk_ids: list[str] = Field(default_factory=list)
    #: 上下文单元（含扩展；用于把上下文映射回证据）
    context: list[RetrievedChunk] = Field(default_factory=list)
    #: 拒答标记（no_answer 题正确拒答用）
    refused: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    error: str | None = None


class SuiteResult(BaseModel):
    """一个 suite 的评测结果（同一 suite 在不同阶段可比）。"""

    suite: str
    sha256: str
    n_cases: int
    n_cases_with_labels: int
    k: int
    metrics: dict[str, float] = Field(default_factory=dict)
    per_case: list[dict] = Field(default_factory=list)


class Report(BaseModel):
    """固定格式的评测报告：一次运行 = 一个阶段的产物。"""

    stage: str
    system: str
    system_config_hash: str
    eval_version: str
    generated_at: str
    git_commit: str | None = None
    suites: dict[str, SuiteResult] = Field(default_factory=dict)
    findings: list[dict] = Field(default_factory=dict)
