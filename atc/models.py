from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CaseResult:
    name: str
    status: str
    elapsed_ms: float
    expected: Optional[str] = None
    output: str = ""
    stderr: str = ""


@dataclass
class ProblemResult:
    problem: str
    mode: Optional[str] = None
    cases: List[CaseResult] = field(default_factory=list)
    error_status: Optional[str] = None
    error_message: str = ""
    duration_ms: float = 0.0

    @property
    def ok_count(self):
        return sum(1 for case in self.cases if case.status == "AC")

    @property
    def total_count(self):
        return len(self.cases)

    @property
    def failed_cases(self):
        return [case for case in self.cases if case.status != "AC"]

    @property
    def passed(self):
        return not self.error_status and self.total_count > 0 and not self.failed_cases


@dataclass
class AtCoderProblem:
    index: str
    title: str
    url: str
    task_id: str
    time_limit: Optional[str] = None
    memory_limit: Optional[str] = None