import atc.commands as commands_module
from atc.commands import resolve_command, usage_lines, usage_sections
from atc.models import CaseResult, ProblemResult


def _passed_result(problem="A"):
    return ProblemResult(
        problem=problem,
        mode="py",
        cases=[CaseResult(name="sample-1.in", status="AC", elapsed_ms=1.0, expected="", output="")],
    )


def test_resolve_command_aliases():
    assert resolve_command("run").name == "run"
    assert resolve_command("r").name == "run"
    assert resolve_command("test").name == "run"
    assert resolve_command("t").name == "run"

    assert resolve_command("contest").name == "contest"
    assert resolve_command("contests").name == "contest"
    assert resolve_command("c").name == "contest"
    assert resolve_command("refresh").name == "refresh"

    assert resolve_command("template").name == "template"
    assert resolve_command("stress").name == "stress"

    assert resolve_command("unknown") is None


def test_handle_run_all_prints_all_summary_and_returns_success(monkeypatch):
    results = [_passed_result("A"), _passed_result("B")]
    printed = []

    monkeypatch.setattr(commands_module, "run_all_problem_tests", lambda lang=None: results)
    monkeypatch.setattr(commands_module, "print_all_summary", lambda value: printed.append(value))

    assert commands_module.handle_run(["all", "py"]) == 0
    assert printed == [results]


def test_handle_run_all_returns_failure_when_any_result_fails(monkeypatch):
    failed = ProblemResult(
        problem="A",
        mode="py",
        cases=[CaseResult(name="sample-1.in", status="WA", elapsed_ms=1.0, expected="ok", output="ng")],
    )
    results = [_passed_result("B"), failed]
    printed = []

    monkeypatch.setattr(commands_module, "run_all_problem_tests", lambda lang=None: results)
    monkeypatch.setattr(commands_module, "print_all_summary", lambda value: printed.append(value))

    assert commands_module.handle_run(["all"]) == 1
    assert printed == [results]


def test_handle_run_single_prints_detailed_result(monkeypatch):
    result = _passed_result("A")
    printed = []
    calls = []

    def fake_run_problem_tests(problem, lang=None, show_compile=False):
        calls.append((problem, lang, show_compile))
        return result

    monkeypatch.setattr(commands_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(commands_module, "print_detailed_result", lambda value: printed.append(value))

    assert commands_module.handle_run(["A", "py"]) == 0
    assert calls == [("A", "py", True)]
    assert printed == [result]


def test_usage_lines_include_main_commands():
    usage = "\n".join(usage_lines())

    assert "atc new" in usage
    assert "atc contest" in usage
    assert "atc refresh" in usage
    assert "atc config doctor" in usage
    assert "atc run A" in usage
    assert "atc run all" in usage
    assert "atc watch" in usage
    assert "atc template list" in usage
    assert "atc template show" in usage
    assert "atc stress A" in usage
    assert "atc stress init A" in usage
    assert "atc stress promote A" in usage
    assert "atc manual" in usage


def test_usage_sections_group_main_commands():
    parts = []
    for title, rows in usage_sections():
        parts.append(title)
        parts.extend(command for command, _description in rows)
    usage = "\n".join(parts)

    assert "AtC" not in usage
    assert "Contest" in usage
    assert "Run" in usage
    assert "Config" in usage
    assert "Stress" in usage
    assert "Manual" in usage
    assert "atc contest" in usage
    assert "atc refresh" in usage
    assert "atc run" in usage
    assert "atc config doctor" in usage
