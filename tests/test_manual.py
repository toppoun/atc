import atc.commands.manual as manual_module


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
    contest_dir = tmp_path / "adt_easy_20260525_1"
    contest_dir.mkdir()
    monkeypatch.chdir(contest_dir)
    _write_contest_metadata(contest_dir)
    calls = []

    def fake_download_samples(contest, problem, dst_dir, url=None):
        calls.append((contest, problem, dst_dir, url))
        return True, ""

    monkeypatch.setattr(manual_module, "download_samples", fake_download_samples)

    manual_module.cmd_manual_tests()

    assert calls == [
        (
            "adt_easy_20260525_1",
            "A",
            contest_dir / "tests" / "A",
            "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/abc230_a",
        )
    ]


def test_manual_tests_with_metadata_url_does_not_warn_for_adt(tmp_path, monkeypatch, capsys):
    contest_dir = tmp_path / "adt_easy_20260525_1"
    contest_dir.mkdir()
    monkeypatch.chdir(contest_dir)
    _write_contest_metadata(contest_dir)

    monkeypatch.setattr(manual_module, "download_samples", lambda contest, problem, dst_dir, url=None: (True, ""))

    manual_module.cmd_manual_tests()

    assert "using guessed task URLs for ADT" not in capsys.readouterr().out


def test_manual_tests_warns_when_adt_uses_guessed_urls_without_metadata(tmp_path, monkeypatch, capsys):
    contest_dir = tmp_path / "adt_easy_20260525_1"
    contest_dir.mkdir()
    monkeypatch.chdir(contest_dir)
    calls = []

    def fake_download_samples(contest, problem, dst_dir, url=None):
        calls.append((contest, problem, dst_dir, url))
        return True, ""

    monkeypatch.setattr(manual_module, "download_samples", fake_download_samples)

    manual_module.cmd_manual_tests()

    output = capsys.readouterr().out.replace("\n", " ")
    assert "using guessed task URLs for ADT" in output
    assert "atc contest" in output
    assert "adt_easy_20260525_1" in output
    assert calls
    assert calls[0][3] is None
