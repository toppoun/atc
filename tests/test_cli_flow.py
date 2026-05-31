import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_test_config(cwd: Path) -> None:
    atc_dir = cwd / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)
    (atc_dir / "config.toml").write_text(
        "\n".join(
            [
                "[defaults]",
                'language = "py"',
                'problems = ["A"]',
                "",
                "[runner]",
                f"python = {json.dumps(sys.executable)}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "atc.cli", *args],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _assert_no_traceback(proc: subprocess.CompletedProcess) -> None:
    output = proc.stdout + proc.stderr
    assert "Traceback" not in output, output


def _assert_success(proc: subprocess.CompletedProcess) -> None:
    _assert_no_traceback(proc)
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


def _assert_error_without_traceback(proc: subprocess.CompletedProcess) -> str:
    _assert_no_traceback(proc)
    assert proc.returncode == 1, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    return proc.stdout + proc.stderr


def _write_echo_problem(cwd: Path, expected: str = "hello") -> None:
    (cwd / "A.py").write_text("print(input())\n", encoding="utf-8")
    _write_sample(cwd, expected)


def _write_sample(cwd: Path, expected: str = "hello") -> None:
    testdir = cwd / "tests" / "A"
    testdir.mkdir(parents=True, exist_ok=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text(f"{expected}\n", encoding="utf-8")


def test_cli_manual_run_rerun_success_flow(tmp_path):
    _write_test_config(tmp_path)

    manual = _run_cli(tmp_path, "manual", "A", "py")
    _assert_success(manual)
    assert (tmp_path / "A.py").is_file()
    assert "Created" in manual.stdout

    _write_echo_problem(tmp_path)

    run = _run_cli(tmp_path, "run", "A", "py")
    _assert_success(run)
    assert "AC" in run.stdout

    rerun = _run_cli(tmp_path, "rerun", "py")
    _assert_success(rerun)


def test_cli_single_run_prints_compact_result_table(tmp_path):
    _write_test_config(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("hello\n", encoding="utf-8")
    (testdir / "sample-2.in").write_text("world\n", encoding="utf-8")
    (testdir / "sample-2.out").write_text("world\n", encoding="utf-8")

    run = _run_cli(tmp_path, "t", "A", "py")

    _assert_success(run)
    first = run.stdout.find("sample-1.in")
    second = run.stdout.find("sample-2.in")
    summary = run.stdout.find("結果: 2/2 AC")
    assert "Test Results" in run.stdout
    assert "=== sample-1.in ===" not in run.stdout
    assert "=== sample-2.in ===" not in run.stdout
    assert first != -1
    assert second != -1
    assert summary != -1
    assert first < second < summary
    assert run.stdout.count("sample-1.in") == 1
    assert run.stdout.count("sample-2.in") == 1


def test_cli_single_run_prints_failure_detail_after_compact_table(tmp_path):
    _write_test_config(tmp_path)
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    testdir = tmp_path / "tests" / "A"
    testdir.mkdir(parents=True)
    (testdir / "sample-1.in").write_text("alpha\n", encoding="utf-8")
    (testdir / "sample-1.out").write_text("alpha\n", encoding="utf-8")
    (testdir / "sample-2.in").write_text("beta-input\n", encoding="utf-8")
    (testdir / "sample-2.out").write_text("beta-expected\n", encoding="utf-8")

    run = _run_cli(tmp_path, "test", "A", "py")

    combined = _assert_error_without_traceback(run)
    assert "Test Results" in combined
    assert "=== sample-1.in ===" not in combined
    assert "=== sample-2.in ===" not in combined
    assert combined.find("sample-1.in") < combined.find("sample-2.in") < combined.find("結果: 1/2 AC")
    assert "sample-2.in WA" in combined
    assert "input" in combined
    assert "beta-input" in combined
    assert "expected" in combined
    assert "beta-expected" in combined
    assert "actual" in combined
    assert combined.count("sample-1.in") == 1


def test_cli_run_all_writes_log_and_rerun_failed_problem(tmp_path):
    _write_test_config(tmp_path)
    _write_sample(tmp_path)

    run_all = _run_cli(tmp_path, "run", "all", "py")
    _assert_no_traceback(run_all)
    assert run_all.returncode == 1, f"stdout:\n{run_all.stdout}\nstderr:\n{run_all.stderr}"
    assert "FAIL" in run_all.stdout

    log_path = tmp_path / ".atc" / "test-runs" / "last.log"
    failed_path = tmp_path / ".atc" / "test-runs" / "last_failed.txt"
    assert log_path.is_file()
    assert "ERROR: ファイルが見つかりません。" in log_path.read_text(encoding="utf-8")
    assert failed_path.read_text(encoding="utf-8") == "A *"

    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")

    rerun = _run_cli(tmp_path, "rerun", "py")
    _assert_success(rerun)
    assert "PASS" in rerun.stdout
    assert log_path.is_file()
    assert failed_path.read_text(encoding="utf-8") == ""


def test_cli_config_init_writes_paths_contests_without_legacy_paths(tmp_path):
    result = _run_cli(tmp_path, "config", "init")
    _assert_success(result)

    config_text = (tmp_path / ".atc" / "config.toml").read_text(encoding="utf-8")
    assert "[paths.contests]" in config_text
    assert '"abc\\\\d+" = "ABC"' in config_text
    assert '"arc\\\\d+" = "ARC"' in config_text
    assert '"agc\\\\d+" = "AGC"' in config_text
    assert '"adt_.*" = "ATD"' in config_text
    for legacy_key in [
        'abc = "ABC(Atcoder Beginner Contest)"',
        'arc = "ARC(Atcoder Regular Contest)"',
        'agc = "AGC(Atcoder Grand Contest)"',
    ]:
        assert legacy_key not in config_text


def test_cli_config_doctor_broken_config_reports_error(tmp_path):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir(parents=True)
    (atc_dir / "config.toml").write_text(
        "[paths\nroot = \".\"\n",
        encoding="utf-8",
    )

    result = _run_cli(tmp_path, "config", "doctor")
    combined = _assert_error_without_traceback(result)

    assert "ERROR" in combined
    assert "config" in combined.lower() or "toml" in combined.lower()


def test_cli_config_doctor_non_table_paths_contests_reports_error(tmp_path):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir(parents=True)
    (atc_dir / "config.toml").write_text(
        "\n".join(
            [
                "[paths]",
                f'root = "{tmp_path.as_posix()}"',
                'contests = "ATD"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_cli(tmp_path, "config", "doctor")
    combined = _assert_error_without_traceback(result)

    assert "[paths.contests] must be a table." in combined


def test_cli_config_doctor_broken_contest_metadata_reports_error(tmp_path):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir(parents=True)
    (atc_dir / "contest.toml").write_text("[[problems]\n", encoding="utf-8")

    result = _run_cli(tmp_path, "config", "doctor")
    combined = _assert_error_without_traceback(result)

    assert "Contest metadata" in combined
    assert "failed to read contest metadata" in combined


def test_cli_config_doctor_broken_template_manifest_reports_error(tmp_path):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir(parents=True)
    (atc_dir / "config.toml").write_text(
        "\n".join(
            [
                "[templates]",
                'manifest = "templates/manifest.json"',
                'py = "fast"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "templates" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{broken", encoding="utf-8")

    result = _run_cli(tmp_path, "config", "doctor")
    combined = _assert_error_without_traceback(result)

    assert "ERROR" in combined
    assert "manifest" in combined.lower()


def test_cli_argparse_handlers_reject_extra_args(tmp_path):
    cases = [
        ("new", "abc001", "py", "extra"),
        ("contest", "abc001", "py", "extra"),
        ("run", "A", "py", "extra"),
        ("rerun", "py", "extra"),
    ]

    for args in cases:
        result = _run_cli(tmp_path, *args)
        combined = _assert_error_without_traceback(result)
        assert "Error" in combined or "Usage" in combined or "使い方" in combined


def test_cli_template_list_and_show(tmp_path):
    list_all = _run_cli(tmp_path, "template", "list")
    _assert_success(list_all)
    assert "Python templates:" in list_all.stdout
    assert "C++ templates:" in list_all.stdout
    assert "default" in list_all.stdout

    list_py = _run_cli(tmp_path, "template", "list", "py")
    _assert_success(list_py)
    assert "Python templates:" in list_py.stdout
    assert "fast" in list_py.stdout
    assert "C++ templates:" not in list_py.stdout

    list_cpp = _run_cli(tmp_path, "template", "list", "cpp")
    _assert_success(list_cpp)
    assert "C++ templates:" in list_cpp.stdout
    assert "acl" in list_cpp.stdout
    assert "Python templates:" not in list_cpp.stdout

    show_py = _run_cli(tmp_path, "template", "show", "py", "default")
    _assert_success(show_py)
    assert "def main" in show_py.stdout

    show_cpp = _run_cli(tmp_path, "template", "show", "cpp", "default")
    _assert_success(show_cpp)
    assert "#include <bits/stdc++.h>" in show_cpp.stdout


def test_cli_template_errors_without_traceback(tmp_path):
    cases = [
        ("template",),
        ("template", "unknown"),
        ("template", "list", "js"),
        ("template", "show", "py"),
        ("template", "show", "py", "unknown"),
        ("template", "show", "js", "fast"),
    ]

    for args in cases:
        result = _run_cli(tmp_path, *args)
        combined = _assert_error_without_traceback(result)
        assert "Error" in combined or "Usage" in combined or "使い方" in combined
