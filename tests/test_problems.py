from atc.core.problems import (
    contest_metadata_error,
    contest_metadata_problems,
    resolve_available_problems,
    resolve_sample_download_problems,
)


ADT_INDEXES = list("ABCDEFGHI")


def _write_contest_metadata(contest_dir, indexes=ADT_INDEXES):
    atc_dir = contest_dir / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        'contest_id = "adt_easy_20260525_1"',
        "",
    ]
    for index in indexes:
        task_id = "abc230_a" if index == "A" else f"adt_task_{index.lower()}"
        lines.extend(
            [
                "[[problems]]",
                f'index = "{index}"',
                f'title = "Problem {index}"',
                f'task_id = "{task_id}"',
                f'url = "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/{task_id}"',
                f'source = "{index}.py"',
                f'tests = "tests/{index}"',
                "",
            ]
        )
    (atc_dir / "contest.toml").write_text("\n".join(lines), encoding="utf-8")


def test_resolve_available_problems_uses_contest_metadata_for_adt(tmp_path):
    _write_contest_metadata(tmp_path)
    config = {"defaults": {"problems": ["A", "B", "C", "D", "E"]}}

    assert resolve_available_problems(tmp_path, config) == ADT_INDEXES


def test_resolve_available_problems_uses_source_files_without_metadata(tmp_path):
    config = {"defaults": {"problems": ["A", "B", "C", "D", "E"]}}
    for problem in ["I", "A", "B"]:
        (tmp_path / f"{problem}.py").write_text("print(input())\n", encoding="utf-8")
    for helper in ["A_gen.py", "A_brute.py", "template.py"]:
        (tmp_path / helper).write_text("print(input())\n", encoding="utf-8")

    assert resolve_available_problems(tmp_path, config) == ["A", "B", "I"]


def test_resolve_available_problems_falls_back_to_defaults_last(tmp_path, capsys):
    config = {"defaults": {"problems": ["A", "B", "I"]}}

    assert resolve_available_problems(tmp_path, config) == ["A", "B", "I"]
    assert "failed to read contest metadata" not in capsys.readouterr().out


def test_resolve_available_problems_warns_when_metadata_is_broken(tmp_path, capsys):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    (atc_dir / "contest.toml").write_text("[[problems]\n", encoding="utf-8")
    config = {"defaults": {"problems": ["A", "B"]}}

    assert resolve_available_problems(tmp_path, config) == ["A", "B"]

    output = capsys.readouterr().out
    assert "failed to read contest metadata" in output
    assert "contest.toml" in output.replace("\n", "")
    assert contest_metadata_error(tmp_path) is not None


def test_resolve_sample_download_problems_uses_metadata_urls(tmp_path):
    _write_contest_metadata(tmp_path, ["A"])

    problems = resolve_sample_download_problems(tmp_path, {"defaults": {"problems": ["A", "B"]}})

    assert [problem.index for problem in problems] == ["A"]
    assert problems[0].task_id == "abc230_a"
    assert problems[0].url == "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/abc230_a"


def test_contest_metadata_problems_ignores_duplicate_indexes(tmp_path):
    _write_contest_metadata(tmp_path, ["A", "B", "A", "I"])

    assert [problem.index for problem in contest_metadata_problems(tmp_path)] == ["A", "B", "I"]
