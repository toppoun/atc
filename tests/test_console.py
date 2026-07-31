from io import StringIO

import pytest
from rich.console import Console

import atc.ui.console as console_module
from atc.models import CaseResult, ProblemResult


def _capture_console(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(
        console_module,
        "console",
        Console(
            file=output,
            force_terminal=False,
            color_system=None,
            width=120,
        ),
    )
    return output


def test_single_result_hides_ac_stderr_without_debug_output(monkeypatch):
    output = _capture_console(monkeypatch)
    result = ProblemResult(
        problem="A",
        cases=[
            CaseResult(
                name="sample-1.in",
                status="AC",
                elapsed_ms=1.0,
                expected="expected",
                output="ac-stdout-must-stay-hidden",
                stderr="ac-stderr-must-stay-hidden",
            )
        ],
    )

    console_module.print_detailed_result(result)

    rendered = output.getvalue()
    assert "Test Results" in rendered
    assert "sample-1.in" in rendered
    assert "結果: 1/1 AC" in rendered
    assert "ac-stderr-must-stay-hidden" not in rendered
    assert "ac-stdout-must-stay-hidden" not in rendered


def test_single_debug_output_displays_each_nonempty_ac_stderr(monkeypatch):
    output = _capture_console(monkeypatch)
    result = ProblemResult(
        problem="A",
        cases=[
            CaseResult(
                name="sample-1.in",
                status="AC",
                elapsed_ms=1.0,
                output="ac-stdout-must-stay-hidden",
                stderr="[L18] n = 5\n[L24] values = {1, 2, 3, 4, 5}",
            ),
            CaseResult(
                name="sample-2.in",
                status="AC",
                elapsed_ms=2.0,
                stderr="[L18] n = 3",
            ),
            CaseResult(
                name="sample-empty.in",
                status="AC",
                elapsed_ms=3.0,
                stderr="",
            ),
            CaseResult(
                name="sample-whitespace.in",
                status="AC",
                elapsed_ms=4.0,
                stderr=" \r\n\t",
            ),
        ],
    )

    console_module.print_detailed_result(
        result,
        show_debug_output=True,
    )

    rendered = output.getvalue()
    first_title = rendered.find("=== sample-1.in debug ===")
    second_title = rendered.find("=== sample-2.in debug ===")
    assert "Test Results" in rendered
    assert "結果: 4/4 AC" in rendered
    assert "[L18] n = 5\n[L24] values = {1, 2, 3, 4, 5}" in rendered
    assert "[L18] n = 3" in rendered
    assert first_title > rendered.find("結果: 4/4 AC")
    assert second_title > first_title
    assert "sample-empty.in debug" not in rendered
    assert "sample-whitespace.in debug" not in rendered
    assert "ac-stdout-must-stay-hidden" not in rendered


@pytest.mark.parametrize("status", ["WA", "RE", "TLE"])
def test_single_debug_output_does_not_duplicate_failed_case_stderr(monkeypatch, status):
    output = _capture_console(monkeypatch)
    stderr = f"{status}-stderr-marker"
    result = ProblemResult(
        problem="A",
        cases=[
            CaseResult(
                name="sample-failed.in",
                status=status,
                elapsed_ms=1.0,
                expected="expected",
                output="actual",
                stderr=stderr,
            )
        ],
    )

    console_module.print_detailed_result(
        result,
        show_debug_output=True,
    )

    rendered = output.getvalue()
    assert f"=== sample-failed.in {status} ===" in rendered
    assert "=== sample-failed.in debug ===" not in rendered
    assert rendered.count(stderr) == 1
    assert "結果: 0/1 AC" in rendered


def test_all_summary_hides_stderr_without_debug_output(monkeypatch):
    output = _capture_console(monkeypatch)
    results = [
        ProblemResult(
            problem="A",
            cases=[
                CaseResult(
                    name="sample-1.in",
                    status="AC",
                    elapsed_ms=1.0,
                    stderr="all-stderr-must-stay-hidden",
                )
            ],
        )
    ]

    console_module.print_all_summary(results)

    rendered = output.getvalue()
    assert "A - AC" in rendered
    assert "all-stderr-must-stay-hidden" not in rendered
    assert " debug ===" not in rendered


def test_all_debug_output_displays_problem_case_and_failed_stderr_after_summary(monkeypatch):
    output = _capture_console(monkeypatch)
    results = [
        ProblemResult(
            problem="A",
            cases=[
                CaseResult(
                    name="sample-1.in",
                    status="AC",
                    elapsed_ms=1.0,
                    output="all-stdout-must-stay-hidden",
                    stderr="A-AC-stderr",
                ),
                CaseResult(
                    name="sample-2.in",
                    status="WA",
                    elapsed_ms=2.0,
                    stderr="A-WA-stderr",
                ),
                CaseResult(
                    name="sample-empty.in",
                    status="AC",
                    elapsed_ms=3.0,
                    stderr="\n",
                ),
            ],
        ),
        ProblemResult(
            problem="B",
            cases=[
                CaseResult(
                    name="sample-3.in",
                    status="AC",
                    elapsed_ms=4.0,
                    stderr="B-AC-stderr",
                )
            ],
        ),
    ]

    console_module.print_all_summary(
        results,
        show_debug_output=True,
    )

    rendered = output.getvalue()
    last_summary = rendered.find("B - AC")
    first_debug = rendered.find("=== A / sample-1.in debug ===")
    assert "A - WA" in rendered
    assert last_summary != -1
    assert first_debug > last_summary
    assert "=== A / sample-2.in debug ===" in rendered
    assert "=== B / sample-3.in debug ===" in rendered
    assert "A-AC-stderr" in rendered
    assert "A-WA-stderr" in rendered
    assert "B-AC-stderr" in rendered
    assert "A / sample-empty.in debug" not in rendered
    assert "all-stdout-must-stay-hidden" not in rendered
