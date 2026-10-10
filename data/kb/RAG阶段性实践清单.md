RAG 与知识库｜阶段性实践清单  [Title]
AI工程技能学习 · 第二节专项实践路线  [Subtitle]
目标：从基础文档问答逐步构建 Project Knowledge Engine，支持多项目隔离、Code RAG、检索评测及外部 Agent 调用。建议以同一个工程持续迭代，而不是制作七个孤立 Demo。

# 一、阶段总览

--- TABLE ---
| 阶段 | 重点 | 验收成果 |
| 1 基础 RAG Pipeline | 解析、切块、Embedding、向量检索、问答 | 可运行的最小文档问答系统 |
| 2 文档与索引优化 | 清洗、Metadata、层级切块、增量索引 | 可维护的文档索引模块 |
| 3 检索质量优化 | BM25、Hybrid Search、Rerank、Query Rewrite | 可配置的检索流水线 |
| 4 Context Engineering | 去重、压缩、Token Budget、来源追踪 | Context Builder |
| 5 Code RAG 专项 | AST、Symbol、依赖关系、增量索引、多项目隔离 | Project Knowledge Engine |
| 6 Evaluation | Golden Dataset、召回、排序、成本与延迟 | 自动评测与对比报告 |
| 7 工程集成 | FastAPI、Docker、MCP、Harness 接入 | 可供 Agent 调用的 RAG 服务 |
--- END TABLE ---

注：阶段 6 的基础评测应从阶段 1 开始，随着系统完善逐步扩充。

# 二、分阶段实践清单

## 阶段一：基础 RAG Pipeline
☐ 解析 TXT、Markdown、PDF 文档
☐ 实现固定长度 Chunking 与 Overlap
☐ 调用 Embedding 模型生成向量
☐ 使用 FAISS / Chroma 建立向量索引
☐ 实现 Top-K 语义检索
☐ 接入 LLM 生成带来源引用的回答
验收：能够完成文档导入、索引构建、检索与问答；保留 10～20 条测试问题作为初始基线。

## 阶段二：文档处理与索引优化
☐ 实现文档清洗、去重与格式统一
☐ 对比固定长度、语义与层级切块
☐ 设计 Chunk Metadata（来源、章节、位置、更新时间）
☐ 实现 Metadata Filtering
☐ 实现 Parent-Child Retrieval
☐ 支持文档更新、删除与增量索引
验收：更新文档后仅重建受影响的索引，能够按来源过滤并回溯原文。

## 阶段三：检索质量优化
☐ 实现 BM25 关键词检索
☐ 实现 Dense + Sparse Hybrid Search
☐ 使用 RRF 等方法融合检索结果
☐ 接入 Cross-Encoder 或 API Reranker
☐ 实现 Query Rewrite
☐ 实现 Multi-query Retrieval
☐ 比较各方案的准确率与延迟
验收：对固定测试集输出 Dense、BM25、Hybrid、Rerank 的检索指标对比。

## 阶段四：Context Engineering
☐ 实现检索结果去重与相关性过滤
☐ 实现 Context Compression
☐ 为检索上下文设置 Token Budget
☐ 处理冲突、过期与低可信度内容
☐ 保留引用来源和文档定位
☐ 比较上下文长度、成本与回答质量
验收：在固定 Token 预算下输出可追溯上下文，记录成本与答案质量变化。

## 阶段五：Code RAG 专项
☐ 扫描 Python 等语言的项目代码
☐ 使用 AST / tree-sitter 解析代码结构
☐ 建立函数、类、方法等 Symbol 索引
☐ 实现函数/类级结构化切块
☐ 建立代码引用与依赖关系
☐ 融合符号检索、关键词检索与语义检索
☐ 支持 Git 变更检测与增量索引
☐ 实现多项目知识库隔离
验收：能够根据自然语言问题定位函数、相关调用点及跨文件依赖，并避免混入其他项目。

## 阶段六：Evaluation 与性能优化
☐ 构建 Golden Dataset（问题、标准答案、相关文档）
☐ 评估 Recall@K、Precision@K、MRR
☐ 评估 Rerank 前后排序质量
☐ 测试回答忠实度与引用正确性
☐ 统计检索延迟、Token 和 API 成本
☐ 对比 Embedding、Chunking、Rerank 配置
☐ 建立自动化回归测试
验收：每次修改配置后自动生成质量、延迟、成本对比报告。

## 阶段七：工程集成与扩展
☐ 使用 FastAPI 封装索引与检索服务
☐ 支持多个项目的知识库管理
☐ 实现索引持久化与后台更新
☐ 使用 Docker 部署
☐ 通过 MCP 暴露 search_project、get_symbol、read_context 等工具
☐ 接入 Cline / Codex 等 Harness
☐ 选做 Graph RAG 与跨文件关系检索
验收：外部客户端能够通过标准接口检索项目知识，并能复现部署与测试。

# 三、建议技术栈
• 语言与工程：Python、pytest、Pydantic
• 文档处理：PyMuPDF、Unstructured
• Embedding：sentence-transformers / Embedding API
• 向量索引：FAISS → Qdrant（或 Chroma）
• 关键词检索：BM25
• Rerank：Cross-Encoder / Rerank API
• 代码解析：Python AST、tree-sitter
• RAG 编排：原生 Python，后续可引入 LlamaIndex
• 服务化：FastAPI、Docker、MCP
• 评测：pytest、RAGAS、DeepEval

# 四、实践原则与最终交付
• 前三阶段尽量亲自实现核心检索链路，避免框架封装遮蔽错误来源。
• Code RAG 的重点是代码结构、符号关系、跨文件依赖，而不是机械按 Token 切块。
• 每个阶段保留 Baseline，使用同一批测试问题验证改动效果。
• 最终交付：代码仓库、部署说明、API/MCP 接口说明、示例项目索引、评测数据及优化报告。
参考资料：《AI工程师技能学习指南》“五、RAG 与知识库”；《AI工程师个人学习重点与进阶路线》“Code RAG 与 Context Engineering”。