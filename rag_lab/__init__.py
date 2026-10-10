"""RAG 实验平台（与 rag_engine 正交）：快照 / Golden / Trace / 实验运行器。

分工：
- ``rag_engine``  = 被测系统（Indexing / Retrieval / Answering）
- ``rag_eval``    = 固定评测内核（指标口径、证据映射）
- ``rag_lab``     = 实验编排（配置驱动、配对对照、归因、报告）
"""

__version__ = "0.1.0"
