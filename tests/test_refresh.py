import tomllib
import pytest

import atc.commands as commands_module
import atc.refresh as refresh_module
from atc.models import AtCoderProblem


def _problem(index, url=None, task_id=None):
    task_id = task_id or f"abc329_{index.lower()}"
    return AtCoderProblem(
        index=index,
        title=f"Problem {index}",
        url=url or f"https://atcoder.jp/contests/abc329/tasks/{task_id}",
        task_id=task_id,
    )


def _config(lang="py"):
    return {
        "paths": {},
        "defaults": {
            "language": lang,
            "problems": ["A"],
        },
    }


def _root_config(root, lang="py"):
    config = _config(lang)
    config["paths"] = {"root": str(root)}
    return config


def _metadata(contest_dir):
    with (contest_dir / ".atc" / "contest.toml").open("rb") as f:
        return tomllib.load(f)


def _patch_fetch(monkeypatch, problems):
    monkeypatch.setattr(refresh_module, "fetch_atcoder_tasks", lambda contest_id: problems)


def _patch_download(monkeypatch, calls=None):
    calls = calls if calls is not None else []

    def fake_download_samples(contest, problem, dst_dir, url=None):
        calls.append((contest, problem, dst_dir, url))
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "sample-1.in").write_text("1\n", encoding="utf-8")
        (dst_dir / "sample-1.out").write_text("1\n", encoding="utf-8")
        return True, ""

    monkeypatch.setattr(refresh_module, "download_samples", fake_download_samples)
    return calls


def _patch_current(monkeypatch, calls=None):
    calls = calls if calls is not None else []

    def fake_write_current_contest(contest_dir, config=None):
        calls.append((contest_dir, config))
        return contest_dir / ".atc" / "current-contest.json"

    monkeypatch.setattr(refresh_module, "write_current_contest", fake_write_current_contest, raising=False)
    return calls


def test_refresh_keeps_sources_and_regenerates_metadata_for_all_tasks(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    (contest_dir / "A.py").write_text("print('custom')\n", encoding="utf-8")
    (contest_dir / "B.cpp").write_text("int main() {}\n", encoding="utf-8")
    problems = [_problem("A"), _problem("B"), _problem("D")]
    _patch_fetch(monkeypatch, problems)
    _patch_download(monkeypatch)
    _patch_current(monkeypatch)

    result = refresh_module.refresh_contest("abc329", contest_dir, _config("py"), yes=True)

    assert (contest_dir / "A.py").read_text(encoding="utf-8") == "print('custom')\n"
    assert (contest_dir / "B.cpp").read_text(encoding="utf-8") == "int main() {}\n"
    assert not (contest_dir / "D.py").exists()

    metadata = _metadata(contest_dir)
    assert metadata["contest_id"] == "abc329"
    assert [problem["index"] for problem in metadata["problems"]] == ["A", "B", "D"]
    assert {problem["index"]: problem["source"] for problem in metadata["problems"]} == {
        "A": "A.py",
        "B": "B.cpp",
        "D": "D.py",
    }
    assert result.metadata_updated is True


def test_refresh_downloads_missing_or_empty_samples_and_skips_existing(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    existing = contest_dir / "tests" / "A"
    existing.mkdir(parents=True)
    (existing / "sample-1.in").write_text("manual\n", encoding="utf-8")
    (contest_dir / "tests" / "B").mkdir()
    _patch_fetch(monkeypatch, [_problem("A"), _problem("B"), _problem("C")])
    download_calls = _patch_download(monkeypatch)
    _patch_current(monkeypatch)

    result = refresh_module.refresh_contest("abc329", contest_dir, _config("py"), yes=True)

    assert [call[1] for call in download_calls] == ["B", "C"]
    assert result.samples_downloaded == ["B", "C"]
    assert result.samples_skipped == ["A"]
    assert (existing / "sample-1.in").read_text(encoding="utf-8") == "manual\n"


def test_refresh_adt_uses_parsed_task_url_for_metadata_and_download(tmp_path, monkeypatch):
    contest_id = "adt_easy_20260525_1"
    contest_dir = tmp_path / contest_id
    contest_dir.mkdir()
    actual_url = "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/abc230_a"
    _patch_fetch(monkeypatch, [_problem("A", url=actual_url, task_id="abc230_a")])
    download_calls = _patch_download(monkeypatch)
    _patch_current(monkeypatch)

    refresh_module.refresh_contest(contest_id, contest_dir, _config("py"), yes=True)

    metadata_problem = _metadata(contest_dir)["problems"][0]
    assert metadata_problem["url"] == actual_url
    assert metadata_problem["task_id"] == "abc230_a"
    assert download_calls == [(contest_id, "A", contest_dir / "tests" / "A", actual_url)]
    assert "adt_easy_20260525_1_a" not in metadata_problem["url"]


def test_refresh_fetch_failure_does_not_fallback_to_default_problems(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    monkeypatch.setattr(refresh_module, "fetch_atcoder_tasks", lambda contest_id: [])
    _patch_download(monkeypatch)
    _patch_current(monkeypatch)

    with pytest.raises(refresh_module.RefreshError, match="does not fallback"):
        refresh_module.refresh_contest("abc329", contest_dir, _config("py"), yes=True)

    assert not (contest_dir / ".atc" / "contest.toml").exists()
    assert not (contest_dir / "tests").exists()


def test_refresh_yes_skips_confirmation(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    _patch_fetch(monkeypatch, [_problem("A")])
    _patch_download(monkeypatch)
    _patch_current(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("confirmation should not be shown"))

    result = refresh_module.refresh_contest("abc329", contest_dir, _config("py"), yes=True)

    assert result.cancelled is False
    assert result.metadata_updated is True


def test_refresh_confirmation_reject_does_not_change_workspace(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    monkeypatch.setattr(refresh_module, "fetch_atcoder_tasks", lambda contest_id: pytest.fail("fetch should not run"))
    current_calls = _patch_current(monkeypatch)

    result = refresh_module.refresh_contest("abc329", contest_dir, _config("py"), yes=False)

    assert result.cancelled is True
    assert current_calls == []
    assert not (contest_dir / ".atc" / "contest.toml").exists()
    assert not (contest_dir / "tests").exists()


def test_refresh_does_not_update_current_contest_after_success(tmp_path, monkeypatch):
    contest_dir = tmp_path / "ABC" / "abc329"
    contest_dir.mkdir(parents=True)
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    current_file = atc_dir / "current-contest.json"
    before = '{"contestDir":"before"}\n'
    current_file.write_text(before, encoding="utf-8")
    config = _root_config(tmp_path, "py")
    _patch_fetch(monkeypatch, [_problem("A")])
    _patch_download(monkeypatch)
    current_calls = _patch_current(monkeypatch)

    result = refresh_module.refresh_contest("abc329", contest_dir, config, yes=True)

    assert current_calls == []
    assert current_file.read_text(encoding="utf-8") == before
    assert result.current_updated is False
    assert result.current_contest_file is None


def test_refresh_can_run_inside_contest_folder_with_workspace_root_config(tmp_path, monkeypatch):
    contest_dir = tmp_path / "ABC" / "abc329"
    contest_dir.mkdir(parents=True)
    config = _root_config(tmp_path, "py")
    _patch_fetch(monkeypatch, [_problem("A")])
    _patch_download(monkeypatch)

    result = refresh_module.refresh_contest("abc329", contest_dir, config, yes=True)

    assert result.metadata_updated is True
    assert (contest_dir / ".atc" / "contest.toml").is_file()
    assert (contest_dir / "tests" / "A" / "sample-1.in").is_file()


def test_refresh_rejects_workspace_root_before_confirmation_or_writes(tmp_path, monkeypatch):
    contest_dir = tmp_path
    config = _root_config(tmp_path, "py")
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    config_file = atc_dir / "config.toml"
    config_before = "[paths]\nroot = \".\"\n"
    config_file.write_text(config_before, encoding="utf-8")
    download_calls = _patch_download(monkeypatch)
    current_calls = _patch_current(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("confirmation should not be shown"))
    monkeypatch.setattr(refresh_module, "fetch_atcoder_tasks", lambda contest_id: pytest.fail("fetch should not run"))
    monkeypatch.setattr(refresh_module, "write_contest_metadata", lambda *args, **kwargs: pytest.fail("metadata should not be written"))

    with pytest.raises(refresh_module.RefreshError, match="workspace root") as excinfo:
        refresh_module.refresh_contest("atcoder", contest_dir, config, yes=False)

    assert ".atc" in str(excinfo.value)
    assert "config.toml" in str(excinfo.value)
    assert download_calls == []
    assert current_calls == []
    assert config_file.read_text(encoding="utf-8") == config_before
    assert not (tmp_path / ".atc" / "contest.toml").exists()
    assert not (tmp_path / "tests").exists()


def test_refresh_command_rejects_workspace_root_without_prompt(tmp_path, monkeypatch):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    (atc_dir / "config.toml").write_text(
        "\n".join(
            [
                "[paths]",
                'root = "."',
                "",
                "[defaults]",
                'language = "py"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("confirmation should not be shown"))
    monkeypatch.setattr(refresh_module, "fetch_atcoder_tasks", lambda contest_id: pytest.fail("fetch should not run"))

    assert refresh_module.cmd_refresh(yes=False) == 1
    assert (atc_dir / "config.toml").read_text(encoding="utf-8").startswith("[paths]")
    assert not (tmp_path / ".atc" / "contest.toml").exists()
    assert not (tmp_path / "tests").exists()


def test_refresh_partial_sample_failure_keeps_metadata_and_continues(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    _patch_fetch(monkeypatch, [_problem("A"), _problem("B"), _problem("C")])
    calls = []

    def fake_download_samples(contest, problem, dst_dir, url=None):
        calls.append(problem)
        if problem == "A":
            return False, "download failed"
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "sample-1.in").write_text("1\n", encoding="utf-8")
        return True, ""

    monkeypatch.setattr(refresh_module, "download_samples", fake_download_samples)
    current_calls = _patch_current(monkeypatch)

    result = refresh_module.refresh_contest("abc329", contest_dir, _config("py"), yes=True)

    assert calls == ["A", "B", "C"]
    assert (contest_dir / ".atc" / "contest.toml").is_file()
    assert result.samples_downloaded == ["B", "C"]
    assert result.samples_failed == [("A", "download failed")]
    assert current_calls == []


def test_refresh_cmd_reports_partial_failure_summary_and_nonzero_exit(tmp_path, monkeypatch, capsys):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    monkeypatch.chdir(contest_dir)
    _patch_fetch(monkeypatch, [_problem("A"), _problem("B")])

    def fake_download_samples(contest, problem, dst_dir, url=None):
        if problem == "A":
            return False, "oj download failed"
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "sample-1.in").write_text("1\n", encoding="utf-8")
        return True, ""

    monkeypatch.setattr(refresh_module, "download_samples", fake_download_samples)

    assert refresh_module.cmd_refresh(yes=True) == 1

    output = capsys.readouterr().out
    assert "Metadata" in output
    assert "updated" in output
    assert "Failed" in output
    assert "A" in output
    assert "partial failure" in output
    assert "oj download failed" in output
    assert (contest_dir / ".atc" / "contest.toml").is_file()


def test_refresh_tests_path_file_conflict_is_failed_and_others_continue(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    tests_dir = contest_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "A").write_text("not a directory\n", encoding="utf-8")
    _patch_fetch(monkeypatch, [_problem("A"), _problem("B")])
    download_calls = _patch_download(monkeypatch)

    result = refresh_module.refresh_contest("abc329", contest_dir, _config("py"), yes=True)

    assert download_calls == [("abc329", "B", contest_dir / "tests" / "B", "https://atcoder.jp/contests/abc329/tasks/abc329_b")]
    assert result.samples_downloaded == ["B"]
    assert result.samples_failed
    assert result.samples_failed[0][0] == "A"
    assert "not a directory" in result.samples_failed[0][1]


def test_refresh_cmd_success_remains_zero_exit(tmp_path, monkeypatch):
    contest_dir = tmp_path / "abc329"
    contest_dir.mkdir()
    monkeypatch.chdir(contest_dir)
    _patch_fetch(monkeypatch, [_problem("A")])
    _patch_download(monkeypatch)

    assert refresh_module.cmd_refresh(yes=True) == 0


def test_refresh_command_parses_yes_flags(monkeypatch):
    calls = []

    def fake_cmd_refresh(contest=None, *, yes=False):
        calls.append((contest, yes))
        return 0

    monkeypatch.setattr(commands_module, "cmd_refresh", fake_cmd_refresh)

    assert commands_module.handle_refresh(["--yes"]) == 0
    assert commands_module.handle_refresh(["-y", "abc329"]) == 0

    assert calls == [(None, True), ("abc329", True)]
