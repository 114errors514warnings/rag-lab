"""S4 L1：Token Budget 裁剪后来源/定位不丢。"""

from __future__ import annotations

from rag_engine.context.builder import ContextBuilder
from rag_engine.generate.context_generator import ContextExtractiveGenerator
from rag_engine.schema import Chunk, Retrieved
from rag_engine.utils import estimate_tokens


def _hit(cid: str, text: str, score: float = 1.0, source: str = "s.md") -> Retrieved:
    return Retrieved(chunk=Chunk(chunk_id=cid, doc_id=cid.split(":")[0], text=text,
                                 meta={"source": source, "trust": 1.0}), score=score)


def test_budget_and_per_doc_minimum() -> None:
    hits = [
        _hit("a:0000", "甲" * 40, score=0.9, source="a.md"),
        _hit("a:0001", "乙" * 40, score=0.5, source="a.md"),
        _hit("b:0000", "丙" * 40, score=0.8, source="b.md"),
    ]
    ctx = ContextBuilder(max_tokens=60, per_doc_min=1).build(hits)
    assert ctx.tokens <= 60
    sources = {seg.source for seg in ctx.segments}
    assert {"a.md", "b.md"} <= sources          # 每个文档至少 1 块
    assert all(seg.chunk_id and seg.source for seg in ctx.segments)


def test_over_budget_is_truncated_but_traceable() -> None:
    long_text = "上下文预算" * 200
    ctx = ContextBuilder(max_tokens=30).build([_hit("x:0000", long_text, source="x.md")])
    assert ctx.tokens <= 30
    assert len(ctx.segments) == 1
    seg = ctx.segments[0]
    assert seg.chunk_id == "x:0000" and seg.source == "x.md"
    assert "truncated" in seg.notes
    assert estimate_tokens(seg.text) <= 30


def test_dropped_recorded_when_budget_exhausted() -> None:
    ctx = ContextBuilder(max_tokens=5).build([_hit("y:0000", "很长很长的一段文本" * 20, source="y.md")])
    assert ctx.segments == []
    assert ctx.dropped == ["y:0000"]


def test_dedupe_removes_same_id_and_same_text() -> None:
    hits = [_hit("c:0000", "重复内容", source="c.md"),
            _hit("c:0000", "重复内容", source="c.md"),
            _hit("c:0001", "重复内容", score=0.5, source="c.md")]
    ctx = ContextBuilder(max_tokens=1000).build(hits)
    ids = [seg.chunk_id for seg in ctx.segments]
    assert ids == ["c:0000"]            # id 去重 + 文本近似去重


def test_context_generator_keeps_citations() -> None:
    long_text = "预算超长文本" * 100
    generator = ContextExtractiveGenerator(max_tokens=40, max_chunks=5)
    hits = [_hit("z:0000", long_text, source="z.md")]
    gen = generator.generate("问题", hits)
    assert gen.citations == ["z:0000"]                 # 来源不丢
    assert "来源：z:0000" in gen.answer
    assert gen.prompt_tokens <= estimate_tokens("问题") + 40
