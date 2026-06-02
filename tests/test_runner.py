import json
import sys

import atc.runner as runner_module
from atc.models import CaseResult, ProblemResult
from atc.runner import LOG_DIR, print_auto_summary, results_passed, run_problem_tests, write_test_log


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


def test_run_problem_tests_returns_error_for_invalid_language(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")

    result = run_problem_tests("A", "ruby")

    assert result.problem == "A"
    assert result.error_status == "ERROR"
    assert "Invalid language" in result.error_message
    assert result.passed is False


def test_cmd_run_all_uses_metadata_problem_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path)
    calls = []

    def fake_run_batch_tests(problems, run_language, reason=""):
        calls.append((problems, run_language, reason))
        return True

    monkeypatch.setattr(runner_module, "_run_batch_tests", fake_run_batch_tests)

    runner_module.cmd_run_all("py")

    assert calls == [(ADT_INDEXES, "py", "manual")]


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


def test_auto_summary_prints_batch_success_summary(capsys):
    result = _passed_result("A")

    print_auto_summary([result], LOG_DIR / "last.log")

    output = capsys.readouterr().out
    assert "Test Results: A" in output
    assert "PASS A: 1 tests" in output
    assert "Full log" in output


def test_auto_summary_prints_batch_failure_summary(capsys):
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

    print_auto_summary([failed], LOG_DIR / "last.log")

    output = capsys.readouterr().out
    assert "FAIL A: 0/1 AC" in output
    assert "sample-1.in" in output
    assert "Test Results: A" in output
    assert "Full log" in output


def test_batch_tests_prints_full_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def fake_run_problem_tests(problem, run_language, show_compile=False):
        return ProblemResult(
            problem=problem,
            mode="py",
            cases=[
                CaseResult(name=f"sample-{i}.in", status="WA", elapsed_ms=1.0, expected="ok", output="ng")
                for i in range(1, 5)
            ],
        )

    monkeypatch.setattr(runner_module, "run_problem_tests", fake_run_problem_tests)

    passed = runner_module.run_batch_tests(["A"], "python", reason="manual")

    output = capsys.readouterr().out
    assert passed is False
    assert "manual: running A" in output
    assert "FAIL A: 0/4 AC" in output
    assert "sample-1.in" in output


def test_batch_tests_prints_all_problem_names(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    problems = [f"A{i:02d}" for i in range(1, 51)]

    def fake_run_problem_tests(problem, run_language, show_compile=False):
        return ProblemResult(
            problem=problem,
            mode="py",
            cases=[CaseResult(name="sample-1.in", status="AC", elapsed_ms=1.0, expected="", output="")],
        )

    monkeypatch.setattr(runner_module, "run_problem_tests", fake_run_problem_tests)

    passed = runner_module.run_batch_tests(problems, "python", reason="manual")
    output = capsys.readouterr().out
    compact_output = "".join(output.split())

    assert passed is True
    assert "manual:runningA01,A02,A03" in compact_output
    assert "PASSA01,A02,A03" in compact_output


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
