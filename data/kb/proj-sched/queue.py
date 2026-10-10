"""任务队列（proj-sched）。"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field


@dataclass(order=True)
class Task:
    priority: int
    seq: int
    name: str = field(compare=False)
    payload: dict = field(default_factory=dict, compare=False)


class PriorityQueue:
    """最小堆优先队列；同优先级按入队顺序（FIFO）。"""

    def __init__(self) -> None:
        self._heap: list[Task] = []
        self._counter = itertools.count()

    def push(self, name: str, priority: int = 0, payload: dict | None = None) -> Task:
        task = Task(priority=priority, seq=next(self._counter), name=name, payload=payload or {})
        heapq.heappush(self._heap, task)
        return task

    def pop(self) -> Task | None:
        return heapq.heappop(self._heap) if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)
