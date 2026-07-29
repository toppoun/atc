import json
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import atc.core.runner as runner_module
from atc.core.config import default_config
from atc.models import CaseResult, ProblemResult
from atc.core.runner import LOG_DIR, results_passed, run_problem_tests, write_test_log


ADT_INDEXES = list("ABCDEFGHI")


def _write_runner_config(cwd, timeout_seconds=None):
    atc_dir = cwd / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "[runner]",
        f"python = {json.dumps(sys.executable)}",
    ]
    if timeout_seconds is not None:
        lines.append(f"timeout_seconds = {timeout_seconds}")
    (atc_dir / "config.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_contest_metadata(contest_dir, indexes=ADT_INDEXES):
    atc_dir = contest_dir / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        'contest_id = "adt_easy_20260525_1"',
        "",
    ]
    for index in indexes:
        lines.extend(
            [
                "[[problems]]",
                f'index = "{index}"',
                f'url = "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/task_{index.lower()}"',
                f'source = "{index}.py"',
                f'tests = "tests/{index}"',
                "",
            ]
        )
    (atc_dir / "contest.toml").write_text("\n".join(lines), encoding="utf-8")


def _passed_result(problem="A"):
    return ProblemResult(
        problem=problem,
        mode="py",
        cases=[
            CaseResult(
                name="sample-1.in",
                status="AC",
                elapsed_ms=1.0,
                expected="hello",
                output="hello",
            )
        ],
    )


def test_results_passed_true_when_all_results_are_ac():
    assert results_passed([_passed_result("A"), _passed_result("B")]) is True


def test_results_passed_false_when_any_result_fails():
    failed = ProblemResult(
        problem="A",
        mode="py",
        cases=[
            CaseResult(
                name="sample-1.in",
                status="WA",
                elapsed_ms=1.0,
                expected="hello",
                output="bye",
            )
        ],
    )

    assert results_passed([_passed_result("B"), failed]) is False
    assert results_passed([]) is False


def test_run_problem_tests_returns_no_tests_without_samples(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")

    result = run_problem_tests("A", "python")

    assert result.problem == "A"
    assert result.mode == "py"
    assert result.error_status == "NO_TESTS"
    assert "テストケース" in result.error_message
    assert result.passed is False


def test_run_problem_tests_returns_no_source_without_source_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("hello\n", encoding="utf-8")

    result = run_problem_tests("A", "python")

    assert result.problem == "A"
    assert result.error_status == "NO_SOURCE"
    assert "ファイル" in result.error_message
    assert result.passed is False


def test_run_problem_tests_returns_error_for_invalid_language(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")

    result = run_problem_tests("A", "ruby")

    assert result.problem == "A"
    assert result.error_status == "INVALID_LANGUAGE"
    assert "Invalid language" in result.error_message
    assert result.passed is False


def test_cmd_run_all_uses_metadata_problem_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path)
    calls = []

    def fake_run_problem_tests(problem, run_language, show_compile=False, debug=False, cpp_extra_flags=()):
        calls.append((problem, run_language, show_compile, debug, tuple(cpp_extra_flags)))
        return _passed_result(problem)

    monkeypatch.setattr(runner_module, "run_problem_tests", fake_run_problem_tests)

    results = runner_module.run_all_problem_tests("py")

    assert [result.problem for result in results] == ADT_INDEXES
    assert calls == [(problem, "py", False, False, ()) for problem in ADT_INDEXES]


def test_run_all_problem_tests_passes_cpp_extra_flags_to_each_problem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, ["A", "B"])
    calls = []
    extra_flags = ("-DLOCAL", "-D_GLIBCXX_DEBUG")

    def fake_run_problem_tests(problem, run_language, show_compile=False, debug=False, cpp_extra_flags=()):
        calls.append((problem, run_language, show_compile, debug, tuple(cpp_extra_flags)))
        return _passed_result(problem)

    monkeypatch.setattr(runner_module, "run_problem_tests", fake_run_problem_tests)

    results = runner_module.run_all_problem_tests("cpp", cpp_extra_flags=extra_flags)

    assert [result.problem for result in results] == ["A", "B"]
    assert calls == [
        ("A", "cpp", False, False, extra_flags),
        ("B", "cpp", False, False, extra_flags),
    ]


def test_run_all_problem_tests_passes_debug_to_each_problem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, ["A", "B"])
    calls = []

    def fake_run_problem_tests(problem, run_language, show_compile=False, debug=False, cpp_extra_flags=()):
        calls.append((problem, run_language, show_compile, debug, tuple(cpp_extra_flags)))
        return _passed_result(problem)

    monkeypatch.setattr(runner_module, "run_problem_tests", fake_run_problem_tests)

    results = runner_module.run_all_problem_tests("cpp", debug=True)

    assert [result.problem for result in results] == ["A", "B"]
    assert calls == [
        ("A", "cpp", False, True, ()),
        ("B", "cpp", False, True, ()),
    ]


def test_cmd_run_all_returns_empty_list_without_available_problems(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner_module, "resolve_available_problems", lambda cwd, config: [])

    results = runner_module.run_all_problem_tests("py")

    captured = capsys.readouterr()
    assert results == []
    assert captured.out == ""
    assert captured.err == ""


def test_write_test_log_records_failed_cases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    failed = ProblemResult(
        problem="A",
        mode="py",
        cases=[
            CaseResult(
                name="sample-1.in",
                status="WA",
                elapsed_ms=1.0,
                expected="hello",
                output="bye",
            )
        ],
    )
    error = ProblemResult(
        problem="B",
        mode="py",
        error_status="NO_TESTS",
        error_message="テストケースがありません。",
    )

    log_path = write_test_log([failed, error])

    assert log_path == LOG_DIR / "last.log"
    assert "status: WA" in log_path.read_text(encoding="utf-8")
    assert (tmp_path / ".atc" / "test-runs" / "last_failed.txt").read_text(encoding="utf-8") == "A sample-1.in\nB *"


def test_runner_does_not_expose_removed_batch_display_helpers():
    assert not hasattr(runner_module, "print_auto_summary")
    assert not hasattr(runner_module, "run_batch_tests")
    assert not hasattr(runner_module, "rerun")


def test_runner_does_not_import_console_display_functions():
    source = inspect.getsource(runner_module)

    assert "from .console import" not in source
    assert "from console import" not in source


def test_run_problem_tests_python_minimal_ac_case(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("hello\n", encoding="utf-8")

    result = run_problem_tests("A", "python")

    assert result.passed is True
    assert result.error_status is None
    assert result.ok_count == 1
    assert result.total_count == 1
    assert result.cases[0].status == "AC"
    assert result.cases[0].output == "hello"


def test_cpp_debug_flags_are_appended_without_mutating_config_or_leaking(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cpp_file = tmp_path / "A.cpp"
    cpp_file.write_text("int main() { return 0; }\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("hello\n", encoding="utf-8")

    config = default_config()
    base_flags = ["-std=gnu++23", "-O2", "-Wall", "-Wextra"]
    debug_flags = ["-DPROJECT_DEBUG", "-fsanitize=undefined"]
    config["runner"]["cpp_flags"] = base_flags[:]
    config["runner"]["cpp_debug_flags"] = debug_flags[:]
    compile_commands = []

    monkeypatch.setattr(runner_module, "load_config", lambda cwd: config)
    monkeypatch.setattr(runner_module, "resolve_executable", lambda command: command)

    def fake_subprocess_run(command, **kwargs):
        if command[0] == "g++":
            compile_commands.append(command[:])
            output_path = Path(command[command.index("-o") + 1])
            output_path.write_text("", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="hello\n", stderr="")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_subprocess_run)
    extra_flags = ("-fno-omit-frame-pointer",)
    executable_suffix = ".exe" if runner_module.platform.system() == "Windows" else ".out"
    executable_path = tmp_path / f"_A{executable_suffix}"

    first_debug = run_problem_tests("A", "cpp", debug=True, cpp_extra_flags=extra_flags)
    second_debug = run_problem_tests("A", "cpp", debug=True, cpp_extra_flags=extra_flags)
    normal = run_problem_tests("A", "cpp")

    assert first_debug.passed is True
    assert second_debug.passed is True
    assert normal.passed is True
    assert config["runner"]["cpp_flags"] == base_flags
    assert config["runner"]["cpp_debug_flags"] == debug_flags
    assert compile_commands[0] == [
        "g++",
        *base_flags,
        *debug_flags,
        *extra_flags,
        str(cpp_file),
        "-o",
        str(executable_path),
    ]
    assert compile_commands[1] == compile_commands[0]
    assert compile_commands[2] == [
        "g++",
        *base_flags,
        str(cpp_file),
        "-o",
        str(executable_path),
    ]
    assert not executable_path.exists()


def test_empty_cpp_debug_flags_adds_no_debug_flags(tmp_path, monkeypatch):
    cpp_file = tmp_path / "A.cpp"
    cpp_file.write_text("int main() { return 0; }\n", encoding="utf-8")
    config = default_config()
    config["runner"]["cpp_flags"] = ["-std=c++20"]
    config["runner"]["cpp_debug_flags"] = []
    compile_commands = []

    monkeypatch.setattr(runner_module, "resolve_executable", lambda command: command)

    def fake_compile(command, **kwargs):
        compile_commands.append(command[:])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_compile)

    mode, _run_cmd, _cleanup_path, error_status, _error_message = runner_module._prepare_cpp_run_command(
        tmp_path,
        "A",
        cpp_file,
        config,
        debug=True,
    )

    assert mode == "cpp"
    assert error_status is None
    assert compile_commands[0] == [
        "g++",
        "-std=c++20",
        str(cpp_file),
        "-o",
        str(tmp_path / ("_A.exe" if runner_module.platform.system() == "Windows" else "_A.out")),
    ]


def test_cpp_extra_flags_disable_python_fallback_when_cpp_source_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    extra_flags = ("-DLOCAL", "-D_GLIBCXX_DEBUG")

    result = run_problem_tests("A", "cpp", cpp_extra_flags=extra_flags)

    assert result.mode == "cpp"
    assert result.error_status == "NO_SOURCE"
    assert result.error_message == "C++ source not found: A.cpp"


def test_debug_disables_python_fallback_when_cpp_source_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")

    result = run_problem_tests("A", "cpp", debug=True)

    assert result.mode == "cpp"
    assert result.error_status == "NO_SOURCE"
    assert result.error_message == "C++ source not found: A.cpp"


def test_cpp_extra_flags_are_rejected_for_python_runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")

    result = run_problem_tests(
        "A",
        "python",
        cpp_extra_flags=("-DLOCAL", "-D_GLIBCXX_DEBUG"),
    )

    assert result.error_status == "INVALID_LANGUAGE"
    assert "only available for C++" in result.error_message


@pytest.mark.parametrize("run_language", ["python", "pypy"])
def test_debug_is_rejected_for_python_runners(tmp_path, monkeypatch, run_language):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")

    result = run_problem_tests("A", run_language, debug=True)

    assert result.error_status == "INVALID_LANGUAGE"
    assert result.error_message == "--debug is only available for C++."


def test_cpp_debug_compile_error_preserves_ce_result(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cpp_file = tmp_path / "A.cpp"
    cpp_file.write_text("broken C++\n", encoding="utf-8")
    config = default_config()
    config["runner"]["cpp_flags"] = ["-std=gnu++23", "-O2"]
    compile_commands = []

    monkeypatch.setattr(runner_module, "load_config", lambda cwd: config)
    monkeypatch.setattr(runner_module, "resolve_executable", lambda command: command)

    def fake_compile(command, **kwargs):
        compile_commands.append(command[:])
        return SimpleNamespace(returncode=1, stdout="", stderr="compile failed")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_compile)
    result = run_problem_tests("A", "cpp", debug=True)

    assert result.error_status == "CE"
    assert result.error_message == "compile failed"
    assert compile_commands[0][1:5] == [
        "-std=gnu++23",
        "-O2",
        "-DLOCAL",
        "-D_GLIBCXX_DEBUG",
    ]


def test_run_problem_tests_calls_callback_in_sample_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_runner_config(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-2.in").write_text("world\n", encoding="utf-8")
    (testdir / "sample-2.out").write_text("world\n", encoding="utf-8")
    callback_results = []

    result = run_problem_tests(
        "A",
        "python",
        on_case_result=lambda case: callback_results.append((case.name, case.status)),
    )

    assert callback_results == [("sample-1.in", "AC"), ("sample-2.in", "AC")]
    assert [case.name for case in result.cases] == ["sample-1.in", "sample-2.in"]
    assert result.passed is True
    assert result.ok_count == 2
    assert result.total_count == 2


def test_run_problem_tests_calls_callback_for_wa_case(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_runner_config(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("expected\n", encoding="utf-8")
    callback_statuses = []

    result = run_problem_tests("A", "python", on_case_result=lambda case: callback_statuses.append(case.status))

    assert callback_statuses == ["WA"]
    assert result.cases[0].status == "WA"
    assert result.passed is False


def test_run_problem_tests_calls_callback_for_re_case(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_runner_config(tmp_path)
    (tmp_path / "A.py").write_text("import sys\nprint('before exit')\nsys.exit(3)\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("before exit\n", encoding="utf-8")
    callback_statuses = []

    result = run_problem_tests("A", "python", on_case_result=lambda case: callback_statuses.append(case.status))

    assert callback_statuses == ["RE"]
    assert result.cases[0].status == "RE"
    assert result.passed is False


def test_run_problem_tests_calls_callback_for_tle_case(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_runner_config(tmp_path, timeout_seconds=0.1)
    (tmp_path / "A.py").write_text("import time\ntime.sleep(1)\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("hello\n", encoding="utf-8")
    callback_statuses = []

    result = run_problem_tests("A", "python", on_case_result=lambda case: callback_statuses.append(case.status))

    assert callback_statuses == ["TLE"]
    assert result.cases[0].status == "TLE"
    assert result.passed is False
