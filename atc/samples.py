import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from .atcoder import build_fallback_task_url
from .console import warn


def download_samples(contest: str, problem_char: str, dst_dir: Path, url: Optional[str] = None):
    tmp = dst_dir.parent / f".oj_tmp_{problem_char}"
    url = url or build_fallback_task_url(contest, problem_char)
    shutil.rmtree(tmp, ignore_errors=True)

    oj = shutil.which("oj")
    if not oj:
        return False, "oj command not found. Install online-judge-tools: python -m pip install online-judge-tools"

    try:
        subprocess.run(
            [oj, "d", url, "-d", str(tmp)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if not tmp.exists():
            return False, "oj finished but did not create a download directory"
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in tmp.iterdir():
            shutil.move(str(f), dst_dir / f.name)
        shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        reason = (e.stderr or e.stdout or "").strip()
        if not reason:
            reason = f"oj exited with status {e.returncode}"
        return False, reason
    except OSError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return False, str(e)


def print_sample_download_summary(problems: List[str], failed_downloads: List[tuple]):
    if not failed_downloads:
        return

    total = len(problems)
    failed = len(failed_downloads)
    succeeded = total - failed
    failed_problems = ", ".join(problem for problem, _ in failed_downloads)

    print()
    warn(f"Sample download summary: {succeeded}/{total} succeeded, {failed} failed.")
    if succeeded == 0:
        warn("Files were created, but sample download failed for all problems.")
    else:
        warn(f"Files were created, but sample download failed for: {failed_problems}")
    print("Check oj installation, AtCoder login, contest ID, and network connection.")
    print("Try: oj login https://atcoder.jp/")


_download_samples = download_samples
_print_sample_download_summary = print_sample_download_summary
