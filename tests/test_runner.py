from atc.models import CaseResult, ProblemResult
from atc.runner import LOG_DIR, results_passed, run_problem_tests, write_test_log


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
