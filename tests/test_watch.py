from atc.watch import _changed_problems, _problem_from_changed_path


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
