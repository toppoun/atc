import atc.watch as watch_module
from atc.models import CaseResult, ProblemResult
from atc.watch import (
    _problem_from_changed_path,
    _run_watch_loop,
    _select_problem_after_change,
)
from atc.watch_render import WatchState, build_watch_view


ADT_INDEXES = list("ABCDEFGHI")
MANY_INDEXES = [f"A{i:02d}" for i in range(1, 51)]


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
                f'title = "Problem {index}"',
                f'url = "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/task_{index.lower()}"',
                f'source = "{index}.py"',
                f'tests = "tests/{index}"',
                "",
            ]
        )
    (atc_dir / "contest.toml").write_text("\n".join(lines), encoding="utf-8")


def test_problem_from_changed_source_files(tmp_path):
    problems = ["A", "B"]

    assert _problem_from_changed_path(tmp_path, tmp_path / "A.py", problems) == "A"
    assert _problem_from_changed_path(tmp_path, tmp_path / "A.cpp", problems) == "A"


def test_problem_from_changed_test_files(tmp_path):
    problems = ["A", "B"]

    assert _problem_from_changed_path(tmp_path, tmp_path / "tests" / "A" / "sample-1.in", problems) == "A"
    assert _problem_from_changed_path(tmp_path, tmp_path / "tests" / "A" / "sample-1.out", problems) == "A"


def test_problem_from_changed_config_is_all(tmp_path):
    assert _problem_from_changed_path(tmp_path, tmp_path / ".atc" / "config.toml", ["A", "B"]) == "ALL"


def test_problem_from_changed_unrelated_file(tmp_path):
    assert _problem_from_changed_path(tmp_path, tmp_path / "README.md", ["A", "B"]) is None


def test_select_problem_after_change_filters_selected_problem(tmp_path):
    problem = _select_problem_after_change(
        tmp_path,
        {
            tmp_path / "A.py",
            tmp_path / "B.py",
        },
        ["A"],
        ["A", "B"],
    )

    assert problem == "A"


def test_select_problem_after_config_change_without_last_problem_returns_none(tmp_path):
    problem = _select_problem_after_change(
        tmp_path,
        {tmp_path / ".atc" / "config.toml"},
        [],
        ["A", "B"],
    )

    assert problem is None


def _disable_live(monkeypatch):
    monkeypatch.setattr(watch_module, "Live", None)
    monkeypatch.setattr(watch_module, "RICH_AVAILABLE", False)


def _passed_result(problem):
    return ProblemResult(
        problem=problem,
        mode="py",
        cases=[CaseResult(name="sample-1.in", status="AC", elapsed_ms=1.0, expected="", output="")],
        duration_ms=1.0,
    )


def _render_text(renderable):
    if isinstance(renderable, str):
        return renderable
    from rich.console import Console

    test_console = Console(record=True, width=120)
    test_console.print(renderable)
    return test_console.export_text()


def test_cmd_watch_without_args_does_not_initial_run_all(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path)
    calls = []

    def stop_watch(_seconds):
        raise KeyboardInterrupt

    _disable_live(monkeypatch)
    monkeypatch.setattr(watch_module, "run_problem_tests", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(watch_module, "_watch_snapshot", lambda cwd, problems=None: {})
    monkeypatch.setattr(watch_module.time, "sleep", stop_watch)

    watch_module.cmd_watch([])

    assert calls == []


def test_cmd_watch_runs_changed_problem_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path)
    source = tmp_path / "D.py"
    calls = []
    snapshots = [
        {},
        {source: (1, 1)},
        {source: (1, 1)},
    ]
    sleep_calls = 0

    def fake_run_problem_tests(problem, run_language, show_compile=False):
        calls.append((problem, run_language, show_compile))
        return _passed_result(problem)

    def fake_snapshot(cwd, problems=None):
        return snapshots.pop(0)

    def fake_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise KeyboardInterrupt

    _disable_live(monkeypatch)
    monkeypatch.setattr(watch_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", fake_snapshot)
    monkeypatch.setattr(watch_module, "watch_settings", lambda config: (0.01, 0.0, []))
    monkeypatch.setattr(watch_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(watch_module.time, "perf_counter", lambda: sleep_calls)

    watch_module.cmd_watch([])

    assert calls == [("D", None, False)]


def test_cmd_watch_explicit_problem_runs_initial_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    calls = []

    def fake_run_problem_tests(problem, run_language, show_compile=False):
        calls.append((problem, run_language, show_compile))
        return _passed_result(problem)

    def stop_watch(_seconds):
        raise KeyboardInterrupt

    _disable_live(monkeypatch)
    monkeypatch.setattr(watch_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", lambda cwd, problems=None: {})
    monkeypatch.setattr(watch_module.time, "sleep", stop_watch)

    watch_module.cmd_watch(["A01"])

    assert calls == [("A01", None, False)]


def test_cmd_watch_all_is_deprecated(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    calls = []

    monkeypatch.setattr(watch_module, "run_problem_tests", lambda *args, **kwargs: calls.append(args))

    watch_module.cmd_watch(["--all"])
    output = capsys.readouterr().out

    assert calls == []
    assert "deprecated" in output
    assert "atc test all" in output


def test_cmd_watch_all_word_is_deprecated(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    calls = []

    monkeypatch.setattr(watch_module, "run_problem_tests", lambda *args, **kwargs: calls.append(args))

    watch_module.cmd_watch(["all"])
    output = capsys.readouterr().out

    assert calls == []
    assert "deprecated" in output
    assert "atc test all" in output


def test_cmd_watch_explicit_problem_runs_after_changed_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    source = tmp_path / "A01.py"
    calls = []
    snapshots = [
        {},
        {source: (1, 1)},
        {source: (1, 1)},
    ]
    sleep_calls = 0

    def fake_run_problem_tests(problem, run_language, show_compile=False):
        calls.append((problem, run_language, show_compile))
        return _passed_result(problem)

    def fake_snapshot(cwd, problems=None):
        return snapshots.pop(0)

    def fake_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise KeyboardInterrupt

    _disable_live(monkeypatch)
    monkeypatch.setattr(watch_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", fake_snapshot)
    monkeypatch.setattr(watch_module, "watch_settings", lambda config: (0.01, 0.0, []))
    monkeypatch.setattr(watch_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(watch_module.time, "perf_counter", lambda: sleep_calls)

    watch_module.cmd_watch(["A01"])

    assert calls[0] == ("A01", None, False)
    assert calls[1] == ("A01", None, False)


def test_cmd_watch_many_without_args_runs_changed_problem_after_skipped_initial(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    source = tmp_path / "A01.py"
    calls = []
    snapshots = [
        {},
        {source: (1, 1)},
        {source: (1, 1)},
    ]
    sleep_calls = 0

    def fake_run_problem_tests(problem, run_language, show_compile=False):
        calls.append((problem, run_language, show_compile))
        return _passed_result(problem)

    def fake_snapshot(cwd, problems=None):
        return snapshots.pop(0)

    def fake_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise KeyboardInterrupt

    _disable_live(monkeypatch)
    monkeypatch.setattr(watch_module, "run_problem_tests", fake_run_problem_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", fake_snapshot)
    monkeypatch.setattr(watch_module, "watch_settings", lambda config: (0.01, 0.0, []))
    monkeypatch.setattr(watch_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(watch_module.time, "perf_counter", lambda: sleep_calls)

    watch_module.cmd_watch([])

    assert calls == [("A01", None, False)]


def test_select_problem_after_config_change_uses_last_problem(tmp_path):
    problem = _select_problem_after_change(
        tmp_path,
        {tmp_path / ".atc" / "config.toml"},
        [],
        ["A", "B"],
        "B",
    )

    assert problem == "B"


def test_watch_renderer_shows_sample_table_and_title(tmp_path):
    result = ProblemResult(
        problem="E",
        mode="py",
        cases=[CaseResult(name="sample-1.in", status="AC", elapsed_ms=58.79, expected="", output="")],
        duration_ms=20000,
    )
    state = WatchState(
        cwd=tmp_path,
        problems=["E"],
        problem="E",
        title="hello",
        result=result,
        message="",
    )

    output = _render_text(build_watch_view(state))

    assert "E - hello" in output
    assert "Case" in output
    assert "Result" in output
    assert "Time" in output
    assert "sample-1.in" in output
    assert "AC" in output


def test_watch_renderer_shows_zero_elapsed_after_update(tmp_path):
    result = _passed_result("E")
    state = WatchState(
        cwd=tmp_path,
        problems=["E"],
        problem="E",
        title="hello",
        result=result,
        updated_at=100.0,
        message="",
    )

    output = _render_text(build_watch_view(state, now=100.0))

    assert "E - hello (0s)" in output


def test_watch_renderer_elapsed_increases_from_updated_at(tmp_path):
    result = _passed_result("E")
    state = WatchState(
        cwd=tmp_path,
        problems=["E"],
        problem="E",
        title="hello",
        result=result,
        updated_at=100.0,
        message="",
    )

    output = _render_text(build_watch_view(state, now=120.0))

    assert "E - hello (20s)" in output


def test_watch_renderer_handles_missing_metadata_title(tmp_path):
    result = _passed_result("E")
    state = WatchState(cwd=tmp_path, problems=["E"], problem="E", result=result, message="")

    output = _render_text(build_watch_view(state))

    assert "E" in output
    assert "Problem E" not in output


def test_watch_renderer_handles_problem_error_status(tmp_path):
    result = ProblemResult(problem="A", mode="cpp", error_status="CE", error_message="compile failed")
    state = WatchState(cwd=tmp_path, problems=["A"], problem="A", result=result, message="")

    output = _render_text(build_watch_view(state))

    assert "CE" in output
    assert "compile failed" in output


def test_watch_loop_tick_does_not_run_problem_without_changes(tmp_path, monkeypatch):
    run_calls = []
    tick_calls = []
    sleep_calls = 0

    monkeypatch.setattr(watch_module, "_watch_snapshot", lambda cwd, problems=None: {})

    def fake_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(watch_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(watch_module.time, "monotonic", lambda: float(sleep_calls))

    _run_watch_loop(
        tmp_path,
        ["A"],
        [],
        0.01,
        0.0,
        lambda problem: run_calls.append(problem),
        on_tick=lambda now: tick_calls.append(now),
    )

    assert run_calls == []
    assert tick_calls == [1.0, 2.0]
