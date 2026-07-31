import inspect
from io import StringIO

import pytest
from rich.console import Console

import atc.commands.run as commands_module
import atc.ui.console as console_module
from atc.commands.registry import resolve_command, usage_sections, usage_sections
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

    monkeypatch.setattr(
        commands_module,
        "run_all_problem_tests",
        lambda lang=None, debug=False: results,
    )
    monkeypatch.setattr(
        commands_module,
        "print_all_summary",
        lambda value, show_debug_output=False: printed.append((value, show_debug_output)),
    )

    assert commands_module.handle_run(["all", "py"]) == 0
    assert printed == [(results, False)]


def test_handle_run_all_returns_failure_when_any_result_fails(monkeypatch):
    failed = ProblemResult(
        problem="A",
        mode="py",
        cases=[CaseResult(name="sample-1.in", status="WA", elapsed_ms=1.0, expected="ok", output="ng")],
    )
    results = [_passed_result("B"), failed]
    printed = []

    monkeypatch.setattr(
        commands_module,
        "run_all_problem_tests",
        lambda lang=None, debug=False: results,
    )
    monkeypatch.setattr(
        commands_module,
        "print_all_summary",
        lambda value, show_debug_output=False: printed.append((value, show_debug_output)),
    )

    assert commands_module.handle_run(["all"]) == 1
    assert printed == [(results, False)]


def test_handle_run_single_prints_detailed_result(monkeypatch):
    result = _passed_result("A")
    printed = []
    calls = []

    def fake_run_problem_tests(problem, lang=None, show_compile=False, debug=False):
        calls.append((problem, lang, show_compile, debug))
        return result

    monkeypatch.setattr(commands_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(
        commands_module,
        "print_detailed_result",
        lambda value, show_debug_output=False: printed.append((value, show_debug_output)),
    )

    assert commands_module.handle_run(["A", "py"]) == 0
    assert calls == [("A", "py", True, False)]
    assert printed == [(result, False)]


@pytest.mark.parametrize(
    "args",
    [
        ["A", "--debug"],
        ["--debug", "A"],
        ["A", "-d"],
        ["-d", "A"],
        ["A", "cpp", "--debug"],
    ],
)
def test_handle_run_accepts_debug_flag_before_or_after_problem(monkeypatch, args):
    result = _passed_result("A")
    calls = []
    printed = []

    def fake_run_problem_tests(problem, lang=None, show_compile=False, debug=False):
        calls.append((problem, lang, show_compile, debug))
        return result

    monkeypatch.setattr(commands_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(
        commands_module,
        "print_detailed_result",
        lambda value, show_debug_output=False: printed.append((value, show_debug_output)),
    )
    monkeypatch.setattr(commands_module, "write_test_log", lambda results: None)

    assert commands_module.handle_run(args) == 0
    assert calls == [("A", "cpp", True, True)]
    assert printed == [(result, True)]


def test_handle_run_all_passes_debug_to_all_runner(monkeypatch):
    results = [_passed_result("A"), _passed_result("B")]
    calls = []
    printed = []

    def fake_run_all_problem_tests(lang=None, debug=False):
        calls.append((lang, debug))
        return results

    monkeypatch.setattr(commands_module, "run_all_problem_tests", fake_run_all_problem_tests)
    monkeypatch.setattr(
        commands_module,
        "print_all_summary",
        lambda value, show_debug_output=False: printed.append((value, show_debug_output)),
    )
    monkeypatch.setattr(commands_module, "write_test_log", lambda values: None)

    assert commands_module.handle_run(["all", "--debug"]) == 0
    assert calls == [("cpp", True)]
    assert printed == [(results, True)]


@pytest.mark.parametrize("lang", ["py", "python", "pypy"])
def test_handle_run_rejects_debug_for_non_cpp_language(monkeypatch, capsys, lang):
    calls = []
    monkeypatch.setattr(commands_module, "run_problem_tests", lambda *args, **kwargs: calls.append((args, kwargs)))

    assert commands_module.handle_run(["A", lang, "--debug"]) == 1
    assert calls == []
    assert "--debug is only available for C++" in capsys.readouterr().out


def test_run_command_does_not_define_concrete_cpp_debug_flags():
    source = inspect.getsource(commands_module)

    assert "CPP_DEBUG_EXTRA_FLAGS" not in source
    assert "-DLOCAL" not in source
    assert "-D_GLIBCXX_DEBUG" not in source


def test_handle_run_debug_displays_ac_stderr_but_normal_run_hides_it(monkeypatch):
    result = ProblemResult(
        problem="A",
        mode="cpp",
        cases=[
            CaseResult(
                name="sample-1.in",
                status="AC",
                elapsed_ms=1.0,
                stderr="command-debug-stderr",
            )
        ],
    )
    calls = []

    def fake_run_problem_tests(problem, lang=None, show_compile=False, debug=False):
        calls.append((problem, lang, show_compile, debug))
        return result

    monkeypatch.setattr(commands_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(commands_module, "write_test_log", lambda results: None)

    debug_output = StringIO()
    monkeypatch.setattr(
        console_module,
        "console",
        Console(file=debug_output, force_terminal=False, color_system=None, width=120),
    )

    assert commands_module.handle_run(["A", "--debug"]) == 0
    assert "Test Results" in debug_output.getvalue()
    assert "command-debug-stderr" in debug_output.getvalue()
    assert "=== sample-1.in debug ===" in debug_output.getvalue()

    normal_output = StringIO()
    monkeypatch.setattr(
        console_module,
        "console",
        Console(file=normal_output, force_terminal=False, color_system=None, width=120),
    )

    assert commands_module.handle_run(["A", "cpp"]) == 0
    assert "Test Results" in normal_output.getvalue()
    assert "command-debug-stderr" not in normal_output.getvalue()
    assert calls == [
        ("A", "cpp", True, True),
        ("A", "cpp", True, False),
    ]


def test_usage_lines_include_main_commands():
    parts = []
    for _title, rows in usage_sections():
        parts.extend(command for command, _description in rows)

    usage = "\n".join(parts)

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


def test_watch_usage_does_not_include_debug_option():
    watch_commands = [
        command
        for _title, rows in usage_sections()
        for command, _description in rows
        if command.startswith("atc watch")
    ]

    assert watch_commands
    assert all("--debug" not in command and "-d" not in command for command in watch_commands)


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
