# 阶段测试与门禁协议（固定测试方法 v1）

> 落地总纲（每阶段实现什么、L1/L2/L3 三层测试、阶段×测试矩阵）见 `docs/guide/implementation-plan.md`；本文只负责"怎么判、为什么这样判"。

> 目的：回答一个问题——**每完成一个阶段，用完全相同的测试方法跑一次，判断"相对上一阶段到底提升了多少"，并自动产出一份能直接贴进报告的对比报告。**

## 0. 文档给了什么、缺什么

| 固定测试方法必需 | 清单文档 | 说明 |
|---|---|---|
| 冻结的测试数据集 | 🟡 半个 | 阶段一说"保留 10~20 条测试问题作为初始基线"（L29），阶段三说"对固定测试集输出…对比"（L48），阶段六说"构建 Golden Dataset（问题、标准答案、相关文档）"（L71）——但**没有**说明三者是什么关系、标注口径、以及由谁在什么时点冻结 |
| 固定的运行方式 | 🟡 半个 | 阶段六验收"每次修改配置后自动生成质量、延迟、成本对比报告"（L78）——要求了自动化，但没定义命令与产物格式 |
| 固定的比较基准 | ❌ | L105"每个阶段保留 Baseline，使用同一批测试问题验证改动效果"——保留的是**测试问题**，没说保留**指标数值**；不冻结数值就无法计算 Δ |
| 固定的判定规则 | ❌ | 全文 0 个阈值（已核对：无任何数值门禁、无提升幅度要求） |
| 固定的报告格式 | ❌ | 阶段七验收只要求"能复现部署与测试"（L88） |

**结论：文档要求了"用同一批问题重复验证"这件事，但没有给出使之可比的全部机制。** 只照文档做，阶段三/四/六只能得到"多个配置之间横向对比"，得不到"阶段 N 相对阶段 N-1 的提升"。本协议补齐这个缺口，且不改变文档的任何验收项。

## 1. "固定"的五个要素

1. **数据集固定**：套件是文件，运行时记录 `sha256`；一旦基线与当前 `sha256` 不一致，直接判 FAIL（防止"看结果改题目"）。
2. **指标实现固定**：口径写在 `rag_eval/metrics.py` 顶部注释里；改动口径必须 bump `EVAL_VERSION`，报告里会记录版本号。
3. **运行方式固定**：一条命令，无人工干预，参数跨阶段完全一致（只有 `--stage` 与 `--system` 变）。
4. **基准固定**：baseline 是**冻结的报告文件**，不是"重跑一遍"。重跑会把噪声当成 Δ。
5. **判定规则固定**：门禁写在 `rag_eval/gates.json`，是数据不是代码；同一阶段每次都按同一张表判。

## 2. 测试资产与变更纪律

| 路径 | 作用 | 变更纪律 |
|---|---|---|
| `data/eval_suites/smoke_v1.jsonl` | 阶段一冒烟套件（10 题，**无标注**） | 阶段二之后不得修改 |
| `data/eval_suites/retrieval_v1.jsonl` | 检索套件（20 题，含 `relevant_chunk_ids`、dev/holdout 划分） | 每阶段**冻结使用**；新增用例须标 `added_in_stage` 并在报告中单独统计 |
| `data/corpus/demo.jsonl` | 演示语料（21 个 chunk，含干扰项） | 仅用于协议自检，真实项目替换为你的语料 |
| `rag_eval/metrics.py` | 指标口径（固定资产） | 改动必须 bump `EVAL_VERSION` |
| `rag_eval/gates.json` | 判定规则（主指标 + 护栏） | 每阶段开始时定，阶段中途不得放宽 |
| `baselines/*.json` | 冻结的基线数值 | **只写不读改写**；新基线 = 新文件名 |
| `reports/*.json` / `*.md` | 每次运行的产物 | 追加式，不覆盖 |

## 3. 每阶段跑什么

### 方案 A：七阶段（与清单一一对应）

| 阶段 | 套件 | k | 主指标（判据） | 护栏 | 该阶段额外动作 |
|---|---|---|---|---|---|
| S1 基础 Pipeline | `smoke_v1` | 3 | 引用缺失率 ≤0.2 | 错误率 = 0 | **本次运行即 baseline 数值**（文档只要求保留问题，这里补上"保留数值"） |
| S2 索引优化 | `smoke_v1` | 3 | 错误率 = 0 | 引用缺失率不退化 | 功能性断言（增量重建精确率）由 `tests/` 承担，不放在本协议里 |
| S3 检索优化 | `retrieval_v1` | 3 | MRR Δ≥+0.10；Recall@3 Δ≥+0.05 | p95 延迟 ≤500ms、单查询成本 ≤$0.005 | 输出 Dense / BM25 / Hybrid / Rerank 四种系统各跑一次（L48 要求） |
| S4 Context | `retrieval_v1` | 5 | 引用精度不下降 | 平均 prompt token ≤预算 | 对比压缩前后：质量不降 且 token 下降（L57 要求） |
| S5 Code RAG | 待建 `code_v1` | 10 | symbol Recall@10 不下降 | **跨项目混入率 = 0**（L68 要求） | 需先编写套件：问题 → `expected_symbols` + `project_id` |
| S6 回归 | `smoke_v1` + `retrieval_v1` | 3 | —（全部护栏） | 任一指标回退 ≤0.01 | 这是 CI 里的门禁（L78 要求"自动化回归"） |
| S7 服务化 | `smoke_v1`（走客户端） | 3 | 成功率不下降 | — | 通过 MCP/HTTP 真实调用，验证"可复现"（L88 要求） |

### 方案 B：三里程碑（压缩版，你提到的"只保留 3 个阶段"）

| 里程碑 | 套件 | 主指标 | 说明 |
|---|---|---|---|
| M1 = 阶段一+二 | `smoke_v1` | 引用缺失率 ≤0.2 | 跑通 + 可维护，产出第一个 baseline 数值 |
| M2 = 阶段三+四 | `retrieval_v1` | MRR Δ≥+0.10；Recall@3 Δ≥+0.05 | 检索与上下文联合调优，收益最集中 |
| M3 = 阶段五+六+七 | `code_v1` + 回归 | symbol Recall@10 不下降 | 多项目隔离 + 服务化 |

> 两种方案共用同一套资产、同一套命令、同一份报告格式；**方案 B 只是把 S1~S7 的门禁合并执行**，不需要另写一套评测。


## 4. 怎么跑

```powershell
# 阶段一：跑通即产出基线数值（--freeze 冻结为基线）
python -m rag_eval.runner --stage S1 --system my_pipeline --freeze

# 阶段三：换检索方案后，与阶段一的冻结基线对比
python -m rag_eval.runner --stage S3 --system my_pipeline --baseline S1__my_pipeline

# 只跑某个套件 / 临时改 k（用于排查，不作为正式结论）
python -m rag_eval.runner --stage S3 --system my_pipeline --suite retrieval_v1 --k 5
```

- `--baseline` 接受三种写法：报告 json 的路径、冻结名（`baselines/<名字>.json`）、`latest`。
- **退出码**：有任一 `FAIL` → `1`（可直接作为 CI 门禁）；否则 `0`。
- 报告同时落盘两份：`reports/<时间戳>_<阶段>_<系统>.json`（机器可读，含逐条 per_case）与 `.md`（可直接贴进阶段报告）。

### 演示（用仓库内的两个占位系统跑出来的真实结果）

```powershell
python -m rag_eval.runner --stage S3 --system stub_dense --freeze          # 基线：朴素重叠检索
python -m rag_eval.runner --stage S3 --system stub_hybrid --baseline S3__stub_dense
```

| 指标 | 基线(dense) | 本次(hybrid) | Δ | 判定 |
|---|---|---|---|---|
| mrr | 0.7083 | 0.9500 | **+0.2417** | PASS |
| recall@3 | 0.9000 | 1.0000 | **+0.1000** | PASS |
| p95_latency_ms | 0.447 | 600.402 | +599.955 | **FAIL**（越绝对上限 500） |
| cost_per_query_usd | 0.0 | 0.0002048 | +0.0002 | PASS |
| recall@3[dev] | 0.8824 | 1.0000 | +0.1176 | 观察项 |
| recall@3[holdout] | 1.0000 | 1.0000 | +0.0000 | 观察项 |

结论行自动生成：**FAIL：`retrieval_v1` / `p95_latency_ms` — 未满足：绝对上限 500.0**。

> 这两个系统是**占位件**（关键词重叠 + 同义扩展 + 人为注入的 600ms 模拟重排延迟），数值不代表任何真实 RAG 的性能。它们存在的意义是：证明"跑一次 → 出报告 → 对比基线 → 给判定 → 退出码"这条链是通的，包括**主指标达标但护栏越线**这种真实项目里最常见的结果。

## 5. 判定规则语义（`gates.json`）

| 字段 | 含义 | 例 |
|---|---|---|
| `primary` | 主指标，决定"这个阶段有没有达成目标" | `{"mrr": {"min_delta": 0.1}}` |
| `guardrails` | 护栏指标，决定"提升是不是用别的东西换来的" | `{"p95_latency_ms": {"max": 500}}` |
| `min_delta` | 相对 baseline 至少要提升多少 | 与 `max_delta` 互斥 |
| `max_delta` | 允许的最大回退（写负数，如 `-0.01`；`0` 表示不允许退步） | 用于回归门禁 |
| `max` | 绝对上限，不依赖 baseline，可单独判定 | 延迟、成本、token 预算 |

判定取值：`PASS` / `FAIL` / `BASELINE`（缺 baseline，无法算 Δ，需先补基线）/ `NO_GATE`（该阶段未给此指标设门禁，仅作观察项）。

## 6. 三条不可破的纪律

1. **数据集冻结**：运行时会比对 `sha256`。一旦发现基线报告里的套件哈希与当前文件不一致，直接输出 `FAIL (suite_sha256)` 并把所有 Δ 作废——因为此时"提升"可能只是换了题目。
2. **baseline 只读**：绝不"重跑一遍基线再比"。要换基线，就是显式冻结一份新的（`--freeze`，文件名带阶段与系统标识）。
3. **口径变更留痕**：动 `metrics.py` 的公式（比如 `recall` 的分母定义）必须改版本号，否则历史报告与新报告不可比。

## 7. 阈值从哪来（文档没给，必须自己定）

文档没有任何数值，所以阈值只能按下面的顺序"先测后定"，并且**必须在阶段开始时定死**：

1. S1 跑出 baseline 数值（本协议已把这一步做成 `--freeze`）。
2. 目标提升幅度按"业务上值得做一次改造"来定，经验区间：排序质量 Δ≥0.10、召回 Δ≥0.05、成本 ≤+20%、p95 延迟 ≤+30% 或绝对值上限。
3. 护栏用"绝对不能破线"的值：跨项目混入率 = 0、错误率 = 0、token 预算上限。
4. 阈值写进 `gates.json` 后不再改；若必须改，要在报告里注明原因（否则等于事后放宽标准）。

## 8. 接入真实系统（不动评测代码）

只要实现一个方法：

```python
from rag_eval.schema import EvalCase, RetrievedChunk, SystemAnswer

class MyPipeline:
    name = "chroma+bm25+cross-encoder"
    config_hash = "..."          # 配置摘要，配置一改就变

    def answer(self, case: EvalCase, k: int) -> SystemAnswer:
        chunks = self.retrieve(case.question, k)      # 你的检索
        answer, citations = self.generate(case.question, chunks)
        return SystemAnswer(
            answer=answer,
            retrieved=[RetrievedChunk(chunk_id=c.id, score=c.score) for c in chunks],
            citations=citations,                       # 回答里引用的 chunk_id
            prompt_tokens=..., completion_tokens=..., cost_usd=...,
        )
```

然后在 `rag_eval/sut/__init__.py` 的 `REGISTRY` 里登记：`"my_pipeline": MyPipeline`，之后所有阶段的命令写法完全不变。

## 9. 已知边界

- **忠实度/答案正确性**：当前指标集偏"检索 + 引用 + 成本/延迟"，因为检索指标可离线、可复现、零成本。答案忠实度需要 LLM 裁判，建议在 S4/S6 追加 `ragas` 或自建 LLM-as-judge 套件，并把它作为**观察项**而非门禁（LLM 裁判本身有方差，做门禁会引入不稳定，需要固定裁判模型 + 多次采样）。
- **延迟**：`latency_ms` 用被测系统自报值优先，缺失时回落到墙钟计时。真实系统应自报各阶段耗时，否则 p95 里混着评测框架的开销。
- **单机噪声**：p95 在 CI 机器上有抖动，建议延迟门禁用"多个样本的 p95"或给 10%~20% 容忍带。
