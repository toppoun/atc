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
