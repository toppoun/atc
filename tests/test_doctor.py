import subprocess

from atc import doctor


def _run_tools_check(monkeypatch, capsys, which_result="C:/bin/oj", run_impl=None):
    calls = []

    monkeypatch.setattr(doctor.shutil, "which", lambda command: which_result if command == "oj" else None)

    def fake_run(args, **kwargs):
        calls.append(args)
        if run_impl:
            return run_impl(args, **kwargs)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="oj 11.5.1\n", stderr="")

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    report = doctor.DoctorReport()
    doctor._doctor_check_tools(report)
    output = capsys.readouterr().out
    return report, output, calls


def test_doctor_oj_login_check_ok(monkeypatch, capsys):
    def run_impl(args, **kwargs):
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="oj 11.5.1\n", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="[SUCCESS] You have already signed in.\n", stderr="")

    report, output, calls = _run_tools_check(monkeypatch, capsys, run_impl=run_impl)

    assert report.counts["ERROR"] == 0
    assert "[OK] oj:" in output
    assert "[OK] oj login: logged in to atcoder.jp" in output
    assert any(call[1:] == ["login", "--check", "https://atcoder.jp/"] for call in calls)


def test_doctor_oj_login_check_nonzero_warns(monkeypatch, capsys):
    def run_impl(args, **kwargs):
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="oj 11.5.1\n", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="not logged in")

    report, output, _calls = _run_tools_check(monkeypatch, capsys, run_impl=run_impl)

    assert report.counts["ERROR"] == 0
    assert "[WARN] oj login:" in output
    assert "not logged in" in output or "login check failed" in output
    assert "run: oj login https://atcoder.jp/" in output


def test_doctor_oj_missing_warns_and_skips_login_check(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(doctor.shutil, "which", lambda command: None)
    monkeypatch.setattr(doctor.subprocess, "run", lambda args, **kwargs: calls.append(args))

    report = doctor.DoctorReport()
    doctor._doctor_check_tools(report)
    output = capsys.readouterr().out

    assert report.counts["ERROR"] == 0
    assert "[WARN] oj was not found." in output
    assert "online-judge-tools" in output
    assert calls == []


def test_doctor_oj_login_timeout_warns(monkeypatch, capsys):
    def run_impl(args, **kwargs):
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="oj 11.5.1\n", stderr="")
        raise subprocess.TimeoutExpired(args, timeout=8.0)

    report, output, _calls = _run_tools_check(monkeypatch, capsys, run_impl=run_impl)

    assert report.counts["ERROR"] == 0
    assert "[WARN] oj login check failed or timed out." in output
    assert "check manually: oj login --check https://atcoder.jp/" in output


def test_doctor_oj_login_unexpected_exception_warns(monkeypatch, capsys):
    def run_impl(args, **kwargs):
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="oj 11.5.1\n", stderr="")
        raise RuntimeError("boom")

    report, output, _calls = _run_tools_check(monkeypatch, capsys, run_impl=run_impl)

    assert report.counts["ERROR"] == 0
    assert "[WARN] oj login check failed." in output
    assert "boom" in output
    assert "Traceback" not in output


def test_doctor_broken_contest_metadata_reports_error(tmp_path, capsys):
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    (atc_dir / "contest.toml").write_text("[[problems]\n", encoding="utf-8")

    report = doctor.DoctorReport()
    doctor._doctor_check_contest_metadata(report, tmp_path)
    output = capsys.readouterr().out

    assert report.counts["ERROR"] == 1
    assert "[ERROR] Contest metadata:" in output
    assert "failed to read contest metadata" in output


def test_doctor_report_render_prints_dashboard(capsys):
    report = doctor.DoctorReport(immediate=False)
    report.section("Environment")
    report.item("OK", "Python: C:/Python/python.exe (3.14.4)")
    report.section("Config")
    report.item("OK", "Config file: D:/atcoder/.atc/config.toml")
    report.item("OK", "Resolved root: D:/atcoder")
    report.section("Runner")
    report.item("OK", "PyPy: C:/pypy/pypy.exe")
    report.item("OK", "C++ compiler: C:/msys64/ucrt64/bin/g++.exe")
    report.section("Tools")
    report.item("OK", "oj: C:/Python/Scripts/oj.exe (oj 11.5.1)")
    report.item("OK", "oj login: logged in to atcoder.jp")
    report.section("VS Code")
    report.item("WARN", "VS Code extension: could not verify")
    report.section("Current contest")
    report.item("OK", "contestDir: D:/atcoder/ABC/abc460")

    report.render()
    output = capsys.readouterr().out

    assert "AtC Doctor" in output
    assert "Status" in output
    assert "Tools" in output
    assert "metadata" in output
    assert "Environment" in output
    assert "[OK] Python:" in output
    assert "Summary" in output


def test_doctor_report_item_keeps_message_backward_compatibility(capsys):
    report = doctor.DoctorReport()

    report.section("Environment")
    report.item("OK", "Python: xxx")
    output = capsys.readouterr().out

    assert "[OK] Python: xxx" in output
    assert report.items[0].display_message == "Python: xxx"
    assert report.counts["OK"] == 1


def test_doctor_report_item_supports_key_label_value():
    report = doctor.DoctorReport(immediate=False)

    report.item("OK", key="resolved_root", label="Resolved root", value="D:/atcoder")

    assert report.value_for("resolved_root") == "D:/atcoder"
    assert report.status_for_key("resolved_root") == "OK"
    assert report.items[0].display_message == "Resolved root: D:/atcoder"
    assert report.counts["OK"] == 1


def test_doctor_dashboard_uses_key_not_label_prefix():
    report = doctor.DoctorReport(immediate=False)
    report.section("Config")
    report.item("OK", key="resolved_root", label="Workspace root", value="D:/atcoder")
    report.item("OK", key="config_file", label="Config path", value="D:/atcoder/.atc/config.toml")
    report.section("Current contest")
    report.item("OK", key="current_contest_dir", label="Current directory", value="D:/atcoder/ABC/abc460")

    rows = dict(report._dashboard_rows())

    assert rows["Root"] == "D:/atcoder"
    assert rows["Config"] == "D:/atcoder/.atc/config.toml"
    assert rows["Current"] == "D:/atcoder/ABC/abc460"


def test_doctor_report_render_details_supports_label_value_and_message_fallback(capsys):
    report = doctor.DoctorReport(immediate=False)
    report.section("Environment")
    report.item("OK", key="python", label="Python", value="xxx")
    report.item("INFO", "message-only item")

    report.render()
    output = capsys.readouterr().out

    assert "[OK] Python: xxx" in output
    assert "[INFO] message-only item" in output
