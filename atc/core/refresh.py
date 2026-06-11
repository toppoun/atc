from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from ..models import AtCoderProblem
from atc.core.atcoder import fetch_atcoder_tasks
from atc.core.config import default_language, load_config
from atc.ui.console import Table, console, error, ok as print_ok
from atc.core.paths import (
    ContestPathConfigError,
    is_workspace_root,
    resolve_contest_dir,
)
from atc.core.metadata import infer_source_name_for_metadata, write_contest_metadata
from atc.core.samples import download_samples


class RefreshError(RuntimeError):
    pass


@dataclass
class RefreshResult:
    contest_id: str
    contest_dir: Path
    metadata_updated: bool = False
    samples_downloaded: List[str] = field(default_factory=list)
    samples_skipped: List[str] = field(default_factory=list)
    samples_failed: List[Tuple[str, str]] = field(default_factory=list)
    current_updated: bool = False
    cancelled: bool = False
    metadata_file: Optional[Path] = None
    current_contest_file: Optional[Path] = None


def fetch_contest_problems_strict(contest_id: str) -> List[AtCoderProblem]:
    try:
        problems = fetch_atcoder_tasks(contest_id)
    except Exception as e:
        raise RefreshError(_tasks_fetch_error_message(contest_id, str(e))) from e

    if not problems:
        raise RefreshError(_tasks_fetch_error_message(contest_id, "problem table was not found or was empty"))
    return problems


def _tasks_fetch_error_message(contest_id: str, reason: str = "") -> str:
    lines = [
        f"Failed to fetch tasks page for {contest_id}.",
        "`atc refresh` does not fallback to defaults.problems.",
    ]
    if reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def _workspace_root_error_message(root: Path) -> str:
    config_file = root / ".atc" / "config.toml"
    return (
        "`atc refresh` must be run inside a contest directory, not the workspace root.\n"
        "\n"
        "This protects your workspace config:\n"
        f"  {config_file}\n"
        "\n"
        "Move to a contest folder such as abc329, or run `atc refresh abc329`."
    )


def _tests_need_download(dst_dir: Path) -> bool:
    if not dst_dir.exists():
        return True
    if not dst_dir.is_dir():
        raise RefreshError(f"{dst_dir} exists but is not a directory")
    try:
        return not any(dst_dir.iterdir())
    except OSError:
        raise RefreshError(f"failed to inspect {dst_dir}")


def download_missing_samples(contest_id: str, contest_dir: Path, problems: List[AtCoderProblem]):
    downloaded: List[str] = []
    skipped: List[str] = []
    failed: List[Tuple[str, str]] = []
    tests_dir = contest_dir / "tests"

    for problem in problems:
        dst_dir = tests_dir / problem.index
        try:
            needs_download = _tests_need_download(dst_dir)
        except RefreshError as e:
            failed.append((problem.index, str(e)))
            continue

        if not needs_download:
            skipped.append(problem.index)
            continue

        print(f"fetching {problem.index} ...", end=" ", flush=True)
        sample_ok, reason = download_samples(contest_id, problem.index, dst_dir, url=problem.url)
        if sample_ok:
            print_ok("done")
            downloaded.append(problem.index)
        else:
            error("failed")
            if reason:
                print(f"  reason: {reason}")
            failed.append((problem.index, reason))

    return downloaded, skipped, failed


def confirm_refresh(contest_id: str, contest_dir: Path) -> bool:
    print(f"Refresh contest workspace: {contest_id}")
    print(f"Directory: {contest_dir}")
    print()
    print("This will update .atc/contest.toml and download missing samples.")
    print("Existing source files will be kept.")
    print("Existing tests will be skipped by default.")
    try:
        answer = input("Continue? [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def refresh_contest(contest_id: str, contest_dir: Path, config: dict, *, yes: bool = False) -> RefreshResult:
    contest_id = str(contest_id).strip().lower()
    contest_dir = Path(contest_dir)

    if not contest_id:
        raise RefreshError("Contest ID is empty.")
    if not contest_dir.exists():
        raise RefreshError(f"Contest directory does not exist: {contest_dir}")
    if not contest_dir.is_dir():
        raise RefreshError(f"Contest path is not a directory: {contest_dir}")
    if is_workspace_root(contest_dir, config):
        raise RefreshError(_workspace_root_error_message(contest_dir))

    result = RefreshResult(contest_id=contest_id, contest_dir=contest_dir.resolve())
    if not yes and not confirm_refresh(contest_id, result.contest_dir):
        result.cancelled = True
        return result

    problems = fetch_contest_problems_strict(contest_id)
    lang = default_language(config)
    source_by_index = {
        problem.index: infer_source_name_for_metadata(contest_dir, problem.index, lang)
        for problem in problems
    }

    result.metadata_file = write_contest_metadata(contest_id, contest_dir, lang, problems, source_by_index=source_by_index)
    result.metadata_updated = True

    downloaded, skipped, failed = download_missing_samples(contest_id, contest_dir, problems)
    result.samples_downloaded = downloaded
    result.samples_skipped = skipped
    result.samples_failed = failed
    return result


def _problem_list(values: List[str]) -> str:
    return ",".join(values) if values else "(none)"


def print_refresh_summary(result: RefreshResult) -> None:
    if result.cancelled:
        print("Refresh cancelled.")
        return

    rows = [
        ("Directory", str(result.contest_dir)),
        ("Metadata", "updated" if result.metadata_updated else "not updated"),
        ("Samples", f"downloaded: {_problem_list(result.samples_downloaded)}"),
        ("Skipped", _problem_list(result.samples_skipped)),
        ("Sources", "kept"),
        ("Current", "unchanged"),
    ]
    if result.samples_failed:
        rows.append(("Failed", _problem_list([problem for problem, _reason in result.samples_failed])))
    rows.append(("Result", "partial failure" if result.samples_failed else "success"))

    print()
    console.print(f"Refresh {result.contest_id}", style="bold")
    table = Table.grid(padding=(0, 4))
    table.add_column(style="bold")
    table.add_column()
    for key, value in rows:
        table.add_row(key, value)
    console.print(table)
    if result.samples_failed:
        console.print()
        console.print("Failed samples:", style="bold")
        for problem, reason in result.samples_failed:
            console.print(f"  {problem}: {reason or 'unknown error'}")


def cmd_refresh(contest: Optional[str] = None, *, yes: bool = False) -> int:
    config = load_config(Path.cwd())
    if contest:
        contest_id = contest.strip().lower()
        try:
            contest_dir = resolve_contest_dir(contest_id, config)
        except ContestPathConfigError as e:
            error(f"Error: {e}")
            return 1
    else:
        contest_dir = Path.cwd()
        contest_id = contest_dir.name.lower()

    try:
        result = refresh_contest(contest_id, contest_dir, config, yes=yes)
    except RefreshError as e:
        error(str(e))
        return 1

    print_refresh_summary(result)
    return 1 if result.samples_failed else 0
