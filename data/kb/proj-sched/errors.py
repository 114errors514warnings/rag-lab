"""错误码与重试策略（proj-sched）。"""

SCHED_TASK_TIMEOUT = "SCHED_2001"
SCHED_QUEUE_FULL = "SCHED_2002"
SCHED_DEPENDENCY_MISSING = "SCHED_2003"


class SchedError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """指数退避：base * 2**attempt，封顶 cap。"""
    return min(base * (2 ** attempt), cap)
