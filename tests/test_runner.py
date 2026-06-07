import json
import inspect
import sys

import atc.runner as runner_module
from atc.models import CaseResult, ProblemResult
from atc.runner import LOG_DIR, results_passed, run_problem_tests, write_test_log


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

    def fake_run_problem_tests(problem, run_language, show_compile=False):
        calls.append((problem, run_language, show_compile))
        return _passed_result(problem)

    monkeypatch.setattr(runner_module, "run_problem_tests", fake_run_problem_tests)

    results = runner_module.run_all_problem_tests("py")

    assert [result.problem for result in results] == ADT_INDEXES
    assert calls == [(problem, "py", False) for problem in ADT_INDEXES]


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
