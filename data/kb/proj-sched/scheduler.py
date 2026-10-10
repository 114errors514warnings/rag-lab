"""调度器主逻辑（proj-sched）。"""

from __future__ import annotations

from datetime import datetime

from errors import SCHED_DEPENDENCY_MISSING, SCHED_TASK_TIMEOUT, SchedError, backoff_delay
from queue import PriorityQueue, Task


class Scheduler:
    """按优先级调度任务，支持依赖检查与超时控制。"""

    def __init__(self) -> None:
        self.queue = PriorityQueue()
        self.completed: set[str] = set()
        self.dependencies: dict[str, set[str]] = {}

    def submit(self, name: str, priority: int = 0, depends_on: set[str] | None = None) -> Task:
        self.dependencies[name] = set(depends_on or set())
        return self.queue.push(name, priority)

    def _dependencies_ready(self, name: str) -> bool:
        return self.dependencies.get(name, set()).issubset(self.completed)

    def run_next(self, deadline: datetime | None = None) -> Task | None:
        """取出下一个可运行任务；依赖未满足则跳过并记录。"""
        pending = self.queue.pop()
        while pending is not None and not self._dependencies_ready(pending.name):
            pending = self.queue.pop()
        if pending is None:
            return None
        if deadline is not None and datetime.utcnow() >= deadline:
            self.queue.push(pending.name, pending.priority, pending.payload)
            raise SchedError(SCHED_TASK_TIMEOUT, f"任务超时：{pending.name}")
        self.completed.add(pending.name)
        return pending

    def retry(self, task: Task, attempt: int) -> float:
        delay = backoff_delay(attempt)
        self.queue.push(task.name, task.priority, task.payload)
        return delay


def validate_dependencies(scheduler: Scheduler) -> None:
    """确保所有依赖任务都已登记，否则抛错。"""
    known = set(scheduler.dependencies)
    for name, deps in scheduler.dependencies.items():
        missing = deps - known
        if missing:
            raise SchedError(SCHED_DEPENDENCY_MISSING, f"{name} 依赖缺失：{sorted(missing)}")
