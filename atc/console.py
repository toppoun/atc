from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple


PROBLEM_LIST_DISPLAY_LIMIT = 12

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


### 純粋テキスト出力 ###
def color_text(message: str, color: str) -> str:
    return f"{color}{message}{RESET}"


def _styled_text(message: str, style: str):
    return Text(str(message), style=style)


def print_text(message: str = "", *, style: Optional[str] = None, end: str = "\n", flush: bool = False) -> None:
    console.print(str(message), style=style, end=end)
    if flush:
        console.file.flush()



def ok(message: str) -> None:
    console.print(Text(f"[OK] {message}", style="green"))


def warn(message: str) -> None:
    console.print(Text(f"[WARN] {message}", style="yellow"))


def error(message: str) -> None:
    console.print(Text(f"[ERROR] {message}", style="red"))


def info(message: str) -> None:
    console.print(Text(f"[INFO] {message}", style="cyan"))


def rule(title: str) -> None:
    console.rule(str(title))


### Richのパネル(四角で囲ってるやつ)出力 ###
def panel(title: str, message: str, style: str = "cyan") -> None:
    console.print(Panel(str(message), title=str(title), border_style=style))


def _path_text(path) -> str:
    return str(path)


def compact_problem_list(
    problems: Sequence[str],
    *,
    limit: int = PROBLEM_LIST_DISPLAY_LIMIT,
    overflow_label: str = "count",
) -> str:
    if not problems:
        return "(none)"
    if len(problems) <= limit:
        return ",".join(problems)
    if overflow_label == "all":
        return "all"
    return f"{len(problems)} problems"


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
    if status in {"WA", "RE", "TLE", "CE", "ERROR"}:
        return "red"
    return "yellow"


def _case_values(case):
    if isinstance(case, tuple):
        return case
    return case.name, case.status, case.elapsed_ms


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
            _styled_text(status, _status_style(status)),
            f"{elapsed_ms:.2f} ms",
        )
    console.print(table)

    print_problem_summary(ok_count, total_count)

    for case_name, status, sections in failure_details:
        if status != "AC" and sections:
            print_failure_detail(f"{case_name} {status}", sections, style="red")


def print_problem_summary(ok_count: int, total_count: int) -> None:
    print_text(f"結果: {ok_count}/{total_count} AC", style="green" if ok_count == total_count and total_count else "red")


def print_failure_detail(title: str, sections: Iterable[Tuple[str, str]], style: str = "red") -> None:
    lines = []
    for label, text in sections:
        lines.append(str(label))
        lines.append(str(text))
        lines.append("")
    message = "\n".join(lines).rstrip()
    panel(title, message, style=style)


def print_auto_summary(
    problems: str,
    passed_cases: int,
    total_cases: int,
    duration: str,
    failed_items: Sequence[Tuple[str, str, str]],
    log_path: Path,
) -> None:
    if failed_items:
        print_text(f"FAIL {problems}: {passed_cases}/{total_cases} AC in {duration}", style="red")
        for problem, status, detail in failed_items[:8]:
            print_text(f"  {problem} - {status}: {detail}")
        if len(failed_items) > 8:
            print_text(f"  ... and {len(failed_items) - 8} more")
    else:
        print_text(f"PASS {problems}: {total_cases} tests in {duration}", style="green")
    print_text(f"Full log: {log_path}")


def print_watch_header(
    cwd: Path,
    poll_seconds: float,
    debounce_seconds: float,
    log_path: Path,
    problems: Sequence[str],
    *,
    mode: Optional[str] = None,
    initial: Optional[str] = None,
) -> None:
    rows = [
        ("cwd", cwd),
        ("problems", compact_problem_list(problems)),
    ]
    if mode:
        rows.append(("mode", mode))
    if initial:
        rows.append(("initial", initial))
    rows.extend(
        [
            ("poll", f"{poll_seconds:.2f}s"),
            ("debounce", f"{debounce_seconds:.2f}s"),
            ("log", log_path),
        ]
    )
    print_key_value_panel(
        "Watch",
        rows,
        style="cyan",
    )
    print_text("Ctrl+C で終了します。")


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

