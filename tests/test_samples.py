import subprocess

import atc.core.samples as samples_module
from atc.core.samples import download_samples


def test_download_samples_prefers_explicit_url(tmp_path, monkeypatch):
    explicit_url = "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/abc230_a"
    calls = []

    monkeypatch.setattr(samples_module.shutil, "which", lambda command: "oj" if command == "oj" else None)

    def fake_run(args, **kwargs):
        calls.append(args)
        output_dir = tmp_path / "tests" / ".oj_tmp_A"
        output_dir.mkdir(parents=True)
        (output_dir / "sample-1.in").write_text("1\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(samples_module.subprocess, "run", fake_run)

    ok, reason = download_samples("adt_easy_20260525_1", "A", tmp_path / "tests" / "A", url=explicit_url)

    assert ok is True
    assert reason == ""
    assert calls[0][2] == explicit_url
