import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .console import Panel, Table, Text, box
from .models import ProblemResult


WATCH_WAIT_MESSAGE = "Save a source file to run its samples."
WATCH_LOG_PATH = Path(".atc") / "test-runs" / "last.log"


@dataclass
class WatchState:
    cwd: Path
    problems: List[str]
    log_path: Path = WATCH_LOG_PATH
    problem: str = ""
    title: str = ""
    result: Optional[ProblemResult] = None
    updated_at: Optional[float] = None
    message: str = WATCH_WAIT_MESSAGE


def _status_style(status: str):
    if status == "AC":
        return "green"
    if status in {"WA", "RE", "TLE", "CE", "ERROR", "NO_TESTS"}:
        return "red"
    return "yellow"


def _format_case_time(elapsed_ms: Optional[float]):
    if elapsed_ms is None:
        return "-"
    return f"{elapsed_ms:.2f} ms"


def _format_problem_elapsed(state: WatchState, now: float):
    if state.updated_at is None:
        return ""
    elapsed_seconds = max(0, int(now - state.updated_at))
    return f" ({elapsed_seconds}s)"


def _problem_heading(state: WatchState, now: float):
    if not state.problem:
        return "Waiting for changes"
    heading = state.problem
    if state.title:
        heading = f"{heading} - {state.title}"
    return f"{heading}{_format_problem_elapsed(state, now)}"


def build_watch_result_table(result: Optional[ProblemResult]):
    table = Table(box=box.SIMPLE)
    table.add_column("Case")
    table.add_column("Result")
    table.add_column("Time", justify="right")

    if not result:
        table.add_row("waiting", Text("-", style="dim"), "-")
        return table

    if result.error_status:
        table.add_row(
            "problem",
            Text(result.error_status, style=_status_style(result.error_status)),
            "-",
        )
        return table

    for case in result.cases:
        table.add_row(
            case.name,
            Text(case.status, style=_status_style(case.status)),
            _format_case_time(case.elapsed_ms),
        )
    return table


def build_watch_header(state: WatchState, *, now: Optional[float] = None):
    now = time.monotonic() if now is None else now
    header = Table.grid(padding=(0, 1), expand=True)
    header.add_column(style="bold", no_wrap=True)
    header.add_column(ratio=1)
    header.add_row("status", _problem_heading(state, now))
    header.add_row("cwd", str(state.cwd))
    header.add_row("log", str(state.log_path))
    if state.message:
        header.add_row("message", state.message)
    elif state.result and state.result.error_message:
        header.add_row("message", state.result.error_message)
    return header


def build_watch_view(state: WatchState, *, now: Optional[float] = None):
    now = time.monotonic() if now is None else now
    view = Table.grid(expand=True)
    view.add_row(Panel(build_watch_header(state, now=now), title="Watch", border_style="cyan", box=box.ROUNDED))
    view.add_row(build_watch_result_table(state.result))
    return view

