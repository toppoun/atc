import atc.watch as watch_module
from atc.console import print_watch_header
from atc.watch import _changed_problems, _problem_from_changed_path


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


def test_changed_problems_config_change_uses_all_available(tmp_path):
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    (tmp_path / "tests" / "B").mkdir(parents=True)

    changed = _changed_problems(
        tmp_path,
        {tmp_path / ".atc" / "config.toml"},
        [],
        ["A", "B", "C"],
    )

    assert changed == ["A", "B"]


def test_changed_problems_filters_selected_problem(tmp_path):
    changed = _changed_problems(
        tmp_path,
        {
            tmp_path / "A.py",
            tmp_path / "B.py",
        },
        ["A"],
        ["A", "B"],
    )

    assert changed == ["A"]


def test_cmd_watch_without_args_uses_metadata_problem_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path)
    calls = []

    def fake_run_auto_tests(problems, run_language, reason="", display_mode="normal"):
        calls.append((problems, run_language, reason, display_mode))
        return True

    def stop_watch(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(watch_module, "run_auto_tests", fake_run_auto_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", lambda cwd, problems=None: {})
    monkeypatch.setattr(watch_module.time, "sleep", stop_watch)

    watch_module.cmd_watch([])

    assert calls[0] == (ADT_INDEXES, None, "initial", "watch")


def test_cmd_watch_without_args_uses_lazy_mode_for_many_metadata_problems(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    calls = []

    def stop_watch(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(watch_module, "run_auto_tests", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(watch_module, "_watch_snapshot", lambda cwd, problems=None: {})
    monkeypatch.setattr(watch_module.time, "sleep", stop_watch)

    result = watch_module.cmd_watch([])
    output = capsys.readouterr().out

    assert result is None
    assert calls == []
    assert "50 problems" in output
    assert "lazy" in output
    assert "skipped" in output
    assert "Please specify a problem:" not in output


def test_cmd_watch_explicit_problem_uses_only_that_problem_with_many_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    calls = []

    def fake_run_auto_tests(problems, run_language, reason="", display_mode="normal"):
        calls.append((problems, run_language, reason, display_mode))
        return True

    def stop_watch(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(watch_module, "run_auto_tests", fake_run_auto_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", lambda cwd, problems=None: {})
    monkeypatch.setattr(watch_module.time, "sleep", stop_watch)

    watch_module.cmd_watch(["A01"])

    assert calls[0] == (["A01"], None, "initial", "watch")


def test_cmd_watch_all_uses_all_many_metadata_problems(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path, MANY_INDEXES)
    calls = []

    def fake_run_auto_tests(problems, run_language, reason="", display_mode="normal"):
        calls.append((problems, run_language, reason, display_mode))
        return True

    def stop_watch(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(watch_module, "run_auto_tests", fake_run_auto_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", lambda cwd, problems=None: {})
    monkeypatch.setattr(watch_module.time, "sleep", stop_watch)

    watch_module.cmd_watch(["--all"])

    assert calls[0] == (MANY_INDEXES, None, "initial", "watch")


def test_watch_header_summarizes_many_problems(tmp_path, capsys):
    print_watch_header(tmp_path, 0.25, 1.5, tmp_path / ".atc" / "test-runs" / "last.log", MANY_INDEXES)
    output = capsys.readouterr().out

    assert "50 problems" in output
    assert "A01,A02,A03" not in output


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

    def fake_run_auto_tests(problems, run_language, reason="", display_mode="normal"):
        calls.append((problems, run_language, reason, display_mode))
        return True

    def fake_snapshot(cwd, problems=None):
        return snapshots.pop(0)

    def fake_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(watch_module, "run_auto_tests", fake_run_auto_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", fake_snapshot)
    monkeypatch.setattr(watch_module, "watch_settings", lambda config: (0.01, 0.0, []))
    monkeypatch.setattr(watch_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(watch_module.time, "perf_counter", lambda: sleep_calls)

    watch_module.cmd_watch(["A01"])

    assert calls[0] == (["A01"], None, "initial", "watch")
    assert calls[1] == (["A01"], None, "changed", "watch")


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

    def fake_run_auto_tests(problems, run_language, reason="", display_mode="normal"):
        calls.append((problems, run_language, reason, display_mode))
        return True

    def fake_snapshot(cwd, problems=None):
        return snapshots.pop(0)

    def fake_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(watch_module, "run_auto_tests", fake_run_auto_tests)
    monkeypatch.setattr(watch_module, "_watch_snapshot", fake_snapshot)
    monkeypatch.setattr(watch_module, "watch_settings", lambda config: (0.01, 0.0, []))
    monkeypatch.setattr(watch_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(watch_module.time, "perf_counter", lambda: sleep_calls)

    watch_module.cmd_watch([])

    assert calls == [(["A01"], None, "changed", "watch")]
