from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple, List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models import ProblemResult, CaseResult


# --- Constants ---
PROBLEM_LIST_DISPLAY_LIMIT = 12

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


# --- Console instance ---
console = Console()


# --- Basic text output ---
def color_text(message: str, color: str) -> str:
    return f"{color}{message}{RESET}"

def ok(message: str) -> None:
    console.print(Text(f"[OK] {message}", style="green"))

def warn(message: str) -> None:
    console.print(Text(f"[WARN] {message}", style="yellow"))

def error(message: str) -> None:
    console.print(Text(f"[ERROR] {message}", style="red"))


def print_text(
    message="",
    *,
    style: Optional[str] = None,
    end: str = "\n",
    flush: bool = False,
) -> None:
    if isinstance(message, Text):
        console.print(message, end=end, highlight=False)
    else:
        console.print(
            message,
            style=style,
            end=end,
            highlight=False,
            markup=False,
        )

    if flush:
        console.file.flush()


# --- Rich helpers ---
def _make_styled_text(message: str, style: str):
    return Text(str(message), style=style)

def panel(title: str, message: str, style: str = "cyan") -> None:
    console.print(Panel(str(message), title=str(title), border_style=style))

def _path_text(path) -> str:
    return str(path)

def print_key_value_panel(title: str, rows: Sequence[Tuple[str, object]], style: str = "cyan") -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()
    for key, value in rows:
        table.add_row(str(key), _path_text(value))
    console.print(Panel(table, title=str(title), border_style=style))

def _status_style(status: str) -> str:
    if status == "AC":
        return "green"
    if status in {"WA", "RE", "TLE", "CE", "ERROR", "NO_SOURCE", "NO_TESTS", "INVALID_LANGUAGE"}:
        return "red"
    return "yellow"


def _case_values(case):
    if isinstance(case, tuple):
        return case
    return case.name, case.status, case.elapsed_ms


# --- run output ---
def _case_input_text(problem: str, case_name: str):
    case_path = Path.cwd() / "tests" / problem / case_name
    try:
        return case_path.read_text(encoding="utf-8")
    except OSError:
        return None
    

def _case_failure_sections(problem: str, case: CaseResult):
    sections = []
    input_text = _case_input_text(problem, case.name) if problem else None

    if input_text:
        sections.append(("input", input_text))
    if case.expected is not None:
        sections.append(("expected", case.expected))
    if case.output:
        sections.append(("output", case.output))
    if case.stderr:
        sections.append(("stderr", case.stderr))
    return sections



def print_detailed_result(result: ProblemResult):
    if result.error_status:
        error(result.error_status)
        if result.error_message:
            print_text(result.error_message)
        return
    
    failure_details = [
        (case.name, case.status, _case_failure_sections(result.problem, case))
        for case in result.failed_cases
    ]

    print_test_results(
        result.cases,
        ok_count=result.ok_count,
        total_count=result.total_count,
        failure_details=failure_details,
    )
def print_test_results(
    cases,
    *,
    title: str = "Test Results",
    ok_count: Optional[int] = None,
    total_count: Optional[int] = None,
    failure_details: Sequence[Tuple[str, str, Sequence[Tuple[str, str]]]] = (),
) -> None:
    rows = [_case_values(case) for case in cases]
    if ok_count is None:
        ok_count = sum(1 for _name, status, _elapsed in rows if status == "AC")
    if total_count is None:
        total_count = len(rows)

    print_text(title, style="bold")
    table = Table(box=box.SIMPLE)
    table.add_column("Case")
    table.add_column("Result")
    table.add_column("Time", justify="right")
    for case_name, status, elapsed_ms in rows:
        table.add_row(
            case_name,
            _make_styled_text(status, _status_style(status)),
            f"{elapsed_ms:.2f} ms",
        )
    console.print(table)

    print_text(f"結果: {ok_count}/{total_count} AC", style="green" if ok_count == total_count and total_count else "red")

    for case_name, status, sections in failure_details:
        if status != "AC" and sections:
            print_failure_detail(f"{case_name} {status}", sections, style="red")


def print_failure_detail(title: str, sections: Iterable[Tuple[str, str]], style: str = "red") -> None:
    print_text()
    print_text(f"=== {title} ===", style=style)

    for label, text in sections:
        print_text()
        print_text(f"{label}: ", style="bold")
        print_text(str(text))


def print_all_summary(results: List[ProblemResult]) -> None:
    for result in results:
        if result.error_status:
            status = result.error_status
            status_text = _make_styled_text(status, _status_style(status))

            print_text(
                Text.assemble(
                    f"{result.problem} - ",
                    status_text,
                    f" {result.ok_count}/{result.total_count}  {result.error_message}",
                )
            )
            continue

        status = "AC" if result.passed else "WA"
        status_text = _make_styled_text(status, _status_style(status))


        print_text(
            Text.assemble(
                f"{result.problem} - ",
                status_text,
                f" {result.ok_count}/{result.total_count}  "
                f"{result.duration_ms / 1000:.2f}s",
            )
        )



# --- stress output ---
def print_stress_header(
    problem: str,
    language: str,
    solution: str,
    generator: str,
    brute: str,
    count: int,
    seed: int,
    compare: str,
    timeout: float,
) -> None:
    print_key_value_panel(
        "Stress Test",
        [
            ("problem", problem),
            ("language", language),
            ("solution", solution),
            ("generator", generator),
            ("brute", brute),
            ("count", count),
            ("seed", seed),
            ("compare", compare),
            ("timeout", timeout),
        ],
        style="magenta",
    )


def print_stress_failure(
    case_number: int,
    seed: int,
    input_text: str,
    your_output: str,
    brute_output: str,
    saved_paths: Sequence[Path],
) -> None:
    print_key_value_panel(
        "WA found",
        [("case", case_number), ("seed", seed)],
        style="red",
    )
    print_failure_detail(
        "Stress Failure",
        [
            ("input", input_text),
            ("actual", your_output),
            ("expected", brute_output),
        ],
        style="red",
    )
    print_text("saved:")
    for path in saved_paths:
        print_text(f"  {path}")


def print_promote_result(problem: str, source_input: Path, source_expected: Path, target_input: Path, target_output: Path) -> None:
    print_text(f"promoted stress case for {problem}", style="green")
    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Item")
    table.add_column("Path")
    table.add_row("input", str(source_input))
    table.add_row("expected", str(source_expected))
    table.add_row("saved input", str(target_input))
    table.add_row("saved output", str(target_output))
    console.print(table)