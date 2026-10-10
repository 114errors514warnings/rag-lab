"""RAG 系统本体（Project Knowledge Engine）。

阶段一最小链路：解析 -> 切块 -> Embedding -> 向量索引 -> Top-K 检索 -> 带引用生成。

设计原则
- 与评测协议（``rag_eval``）完全解耦：唯一连接点是 ``eval_adapter.MyPipeline``。
- 默认零外部依赖（纯 numpy + 标准库），保证离线可复现；重型组件（OpenAI Embedding、
  PyMuPDF 等）通过可选导入接入，缺少时不影响主链路。
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
