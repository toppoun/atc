import atc.manual as manual_module


def _write_contest_metadata(contest_dir):
    atc_dir = contest_dir / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)
    (atc_dir / "contest.toml").write_text(
        "\n".join(
            [
                'contest_id = "adt_easy_20260525_1"',
                "",
                "[[problems]]",
                'index = "A"',
                'title = "AtCoder Quiz 3"',
                'task_id = "abc230_a"',
                'url = "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/abc230_a"',
                'source = "A.py"',
                'tests = "tests/A"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_manual_tests_uses_metadata_problem_url(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_contest_metadata(tmp_path)
    calls = []

    def fake_download_samples(contest, problem, dst_dir, url=None):
        calls.append((contest, problem, dst_dir, url))
        return True, ""

    monkeypatch.setattr(manual_module, "download_samples", fake_download_samples)

    manual_module.cmd_manual_tests()

    assert calls == [
        (
            tmp_path.name.lower(),
            "A",
            tmp_path / "tests" / "A",
            "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/abc230_a",
        )
    ]
