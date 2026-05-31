from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple


RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()
    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when rich is not installed
    box = None
    Console = None
    Panel = None
    Table = None
    Text = None
    console = None
    RICH_AVAILABLE = False


def color_text(message: str, color: str) -> str:
    return f"{color}{message}{RESET}"


def _styled_text(message: str, style: str):
    if RICH_AVAILABLE:
        return Text(str(message), style=style)
    return str(message)


def print_text(message: str = "", *, style: Optional[str] = None, end: str = "\n", flush: bool = False) -> None:
    if RICH_AVAILABLE:
        console.print(str(message), style=style, end=end)
        if flush:
            console.file.flush()
        return
    print(str(message), end=end, flush=flush)


def ok(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(Text(f"[OK] {message}", style="green"))
    else:
        print(color_text(f"[OK] {message}", GREEN))


def warn(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(Text(f"[WARN] {message}", style="yellow"))
    else:
        print(color_text(f"[WARN] {message}", YELLOW))


def error(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(Text(f"[ERROR] {message}", style="red"))
    else:
        print(color_text(f"[ERROR] {message}", RED))


def info(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(Text(f"[INFO] {message}", style="cyan"))
    else:
        print(color_text(f"[INFO] {message}", CYAN))


def rule(title: str) -> None:
    if RICH_AVAILABLE:
        console.rule(str(title))
    else:
        print(f"--- {title} ---")


def panel(title: str, message: str, style: str = "cyan") -> None:
    if RICH_AVAILABLE:
        console.print(Panel(str(message), title=str(title), border_style=style))
    else:
        print(f"[{title}]")
        print(message)


def _path_text(path) -> str:
    return str(path)


def print_key_value_panel(title: str, rows: Sequence[Tuple[str, object]], style: str = "cyan") -> None:
    if RICH_AVAILABLE:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold")
        table.add_column()
        for key, value in rows:
            table.add_row(str(key), _path_text(value))
        console.print(Panel(table, title=str(title), border_style=style))
        return

    print(f"{title}:")
    for key, value in rows:
        print(f"  {key}: {_path_text(value)}")


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


def _failure_sections(
    *,
    input_text: Optional[str] = None,
    expected: Optional[str] = None,
    actual: str = "",
    stderr: str = "",
) -> Sequence[Tuple[str, str]]:
    sections = []
    if input_text:
        sections.append(("input: ", input_text))
    if expected is not None:
        sections.append(("expected: ", expected))
    if actual:
        sections.append(("actual: ", actual))
    if stderr:
        sections.append(("stderr: ", stderr))
    return sections


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
    if RICH_AVAILABLE:
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
    else:
        for case_name, status, elapsed_ms in rows:
            print(f"{status:<3} {case_name} {elapsed_ms:.2f} ms")

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


def print_watch_result(
    problems: str,
    passed_cases: int,
    total_cases: int,
    duration: str,
    failed_items: Sequence[Tuple[str, str, str]],
) -> None:
    if not failed_items:
        print_text(f"PASS {problems}: {passed_cases}/{total_cases} AC", style="green")
        return

    print_text(f"FAIL {problems}: {passed_cases}/{total_cases} AC", style="red")


def print_watch_header(cwd: Path, poll_seconds: float, debounce_seconds: float, log_path: Path, problems: Sequence[str]) -> None:
    print_key_value_panel(
        "Watch",
        [
            ("cwd", cwd),
            ("problems", ",".join(problems) if problems else "(none)"),
            ("poll", f"{poll_seconds:.2f}s"),
            ("debounce", f"{debounce_seconds:.2f}s"),
            ("log", log_path),
        ],
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
    if RICH_AVAILABLE:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Item")
        table.add_column("Path")
        table.add_row("input", str(source_input))
        table.add_row("expected", str(source_expected))
        table.add_row("saved input", str(target_input))
        table.add_row("saved output", str(target_output))
        console.print(table)
        return

    print()
    print("input:")
    print(f"  {source_input}")
    print("expected:")
    print(f"  {source_expected}")
    print()
    print("saved:")
    print(f"  {target_input}")
    print(f"  {target_output}")
