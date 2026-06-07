import tomllib

from atc.models import AtCoderProblem
from atc.metadata import (
    contest_metadata_error,
    contest_metadata_problems,
    infer_source_name_for_metadata,
    write_contest_metadata,
)


def test_write_contest_metadata_preserves_schema_and_source_override(tmp_path):
    problems = [
        AtCoderProblem(
            index="A",
            title="Mod While Positive",
            task_id="abc460_a",
            url="https://atcoder.jp/contests/abc460/tasks/abc460_a",
        ),
        AtCoderProblem(
            index="B",
            title="Two Rings",
            task_id="abc460_b",
            url="https://atcoder.jp/contests/abc460/tasks/abc460_b",
        ),
    ]

    contest_file = write_contest_metadata(
        "abc460",
        tmp_path,
        "py",
        problems,
        source_by_index={"B": "B.cpp"},
    )

    with contest_file.open("rb") as f:
        metadata = tomllib.load(f)

    assert metadata["contest_id"] == "abc460"
    assert metadata["problems"] == [
        {
            "index": "A",
            "title": "Mod While Positive",
            "task_id": "abc460_a",
            "url": "https://atcoder.jp/contests/abc460/tasks/abc460_a",
            "source": "A.py",
            "tests": "tests/A",
        },
        {
            "index": "B",
            "title": "Two Rings",
            "task_id": "abc460_b",
            "url": "https://atcoder.jp/contests/abc460/tasks/abc460_b",
            "source": "B.cpp",
            "tests": "tests/B",
        },
    ]


def test_contest_metadata_problems_and_error_match_existing_behavior(tmp_path):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    (atc_dir / "contest.toml").write_text(
        "\n".join(
            [
                'contest_id = "abc460"',
                "",
                "[[problems]]",
                'index = "a"',
                'title = "Problem A"',
                'task_id = "abc460_a"',
                'url = "https://atcoder.jp/contests/abc460/tasks/abc460_a"',
                'source = "A.py"',
                'tests = "tests/A"',
                "",
                "[[problems]]",
                'index = "A"',
                'title = "Duplicate A"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    problems = contest_metadata_problems(tmp_path)

    assert contest_metadata_error(tmp_path) is None
    assert len(problems) == 1
    assert problems[0].index == "A"
    assert problems[0].title == "Problem A"
    assert problems[0].task_id == "abc460_a"


def test_infer_source_name_for_metadata_prefers_existing_sources(tmp_path):
    (tmp_path / "A.cpp").write_text("int main() {}\n", encoding="utf-8")
    (tmp_path / "B.py").write_text("print(input())\n", encoding="utf-8")

    assert infer_source_name_for_metadata(tmp_path, "A", "py") == "A.cpp"
    assert infer_source_name_for_metadata(tmp_path, "B", "cpp") == "B.py"
    assert infer_source_name_for_metadata(tmp_path, "C", "py") == "C.py"

