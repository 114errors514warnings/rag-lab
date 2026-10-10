"""带来源引用的生成。

- :class:`ExtractiveGenerator`：离线默认。直接从检索到的片段组织回答并**逐条标注
  chunk_id 来源**，保证"来源可回溯"这一阶段一护栏；零成本、零依赖、确定。
- :class:`OpenAIGenerator`：可选。真正调用 LLM，提示词要求以 ``[chunk_id]`` 标注来源，
  回答后扫描其中的 chunk_id 得到 citations；用量与成本回填给评测。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, Sequence, runtime_checkable

from ..schema import Retrieved
from ..utils import estimate_tokens

_CITE = re.compile(r"[\[\（(]?\b([0-9a-zA-Z_\-:.]+:\d{4})\b[\]\）)]?")


@dataclass
class Generation:
    answer: str
    citations: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


@runtime_checkable
class Generator(Protocol):
    def generate(self, question: str, retrieved: Sequence[Retrieved]) -> Generation: ...


class ExtractiveGenerator:
    def __init__(self, max_chunks: int = 5) -> None:
        self.max_chunks = max_chunks

    def generate(self, question: str, retrieved: Sequence[Retrieved]) -> Generation:
        used = list(retrieved)[: self.max_chunks]
        if not used:
            return Generation(answer="", citations=[], prompt_tokens=estimate_tokens(question))
        parts = [f"{r.chunk.text}（来源：{r.chunk.chunk_id}）" for r in used]
        answer = " ".join(parts)
        citations = [r.chunk.chunk_id for r in used]
        prompt_tokens = estimate_tokens(question) + sum(estimate_tokens(r.chunk.text) for r in used)
        return Generation(
            answer=answer,
            citations=citations,
            prompt_tokens=prompt_tokens,
            completion_tokens=estimate_tokens(answer),
            cost_usd=0.0,
        )


class OpenAIGenerator:
    def __init__(self, model: str = "gpt-4o-mini", max_chunks: int = 5) -> None:
        self.model = model
        self.max_chunks = max_chunks
        self._client = None
        self._fallback = ExtractiveGenerator(max_chunks=max_chunks)

    def _client_or_create(self):
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore
            except ImportError as exc:  # pragma: no cover - 环境相关
                raise RuntimeError("未安装 openai，无法使用 OpenAIGenerator") from exc
            self._client = OpenAI()
        return self._client

    def generate(self, question: str, retrieved: Sequence[Retrieved]) -> Generation:
        used = list(retrieved)[: self.max_chunks]
        if not used:
            return Generation(answer="", citations=[], prompt_tokens=estimate_tokens(question))
        context = "\n\n".join(
            f"[{i + 1}] chunk_id={r.chunk.chunk_id}\n{r.chunk.text}"
            for i, r in enumerate(used)
        )
        prompt = (
            "仅依据以下资料回答问题，不要编造；并在引用处用 [chunk_id] 标注来源。\n\n"
            f"资料：\n{context}\n\n问题：{question}\n回答："
        )
        try:
            client = self._client_or_create()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
        except Exception:  # noqa: BLE001 - 网络/密钥问题回退到抽取式
            return self._fallback.generate(question, used)
        text = resp.choices[0].message.content or ""
        valid = {r.chunk.chunk_id for r in used}
        cited: list[str] = []
        for match in _CITE.findall(text):
            if match in valid and match not in cited:
                cited.append(match)
        usage = getattr(resp, "usage", None)
        return Generation(
            answer=text,
            citations=cited,
            prompt_tokens=getattr(usage, "prompt_tokens", estimate_tokens(prompt)),
            completion_tokens=getattr(usage, "completion_tokens", estimate_tokens(text)),
            cost_usd=0.0,
        )


def build_generator(kind: str, model: str, max_chunks: int) -> Generator:
    if kind == "openai":
        return OpenAIGenerator(model=model, max_chunks=max_chunks)
    return ExtractiveGenerator(max_chunks=max_chunks)
