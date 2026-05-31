import atc.watch as watch_module
from atc.watch import _changed_problems, _problem_from_changed_path


ADT_INDEXES = list("ABCDEFGHI")


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
