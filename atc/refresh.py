from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from .atcoder import AtCoderProblem, fetch_atcoder_tasks
    from .config import SOURCE_EXTS, config_root, default_language, find_project_root, load_config
    from .console import RICH_AVAILABLE, Table, console, error, ok as print_ok
    from .contest import (
        ContestPathConfigError,
        resolve_contest_dir,
        write_contest_metadata,
    )
    from .samples import download_samples
except ImportError:
    from atcoder import AtCoderProblem, fetch_atcoder_tasks
    from config import SOURCE_EXTS, config_root, default_language, find_project_root, load_config
    from console import RICH_AVAILABLE, Table, console, error, ok as print_ok
    from contest import (
        ContestPathConfigError,
        resolve_contest_dir,
        write_contest_metadata,
    )
    from samples import download_samples


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


def _workspace_root_error_message() -> str:
    return (
        "`atc refresh` must be run inside a contest directory, not the workspace root.\n"
        "Move to a contest folder such as abc329, or run `atc refresh abc329`."
    )


def _is_workspace_root(path: Path, config: dict) -> bool:
    configured_root = config_root(config)
    try:
        resolved_path = path.resolve()
    except OSError:
        return False

    try:
        if configured_root and resolved_path == configured_root.resolve():
            return True
    except OSError:
        return False

    root = find_project_root(path, config)
    try:
        resolved_root = root.resolve()
    except OSError:
        return False

    if resolved_path != resolved_root:
        return False

    return (
        (resolved_path / ".atc" / "config.toml").exists()
        or (resolved_path / ".git").exists()
        or (resolved_path / "pyproject.toml").exists()
        or (resolved_path / ".vscode").exists()
    )


def infer_source_name_for_metadata(contest_dir: Path, problem_index: str, default_lang: str) -> str:
    for ext in SOURCE_EXTS:
        candidate = contest_dir / f"{problem_index}.{ext}"
        if candidate.is_file():
            return candidate.name
    return f"{problem_index}.{default_lang}"


def _tests_need_download(dst_dir: Path) -> bool:
    if not dst_dir.exists():
        return True
    if not dst_dir.is_dir():
        return False
    try:
        return not any(dst_dir.iterdir())
    except OSError:
        return False


def download_missing_samples(contest_id: str, contest_dir: Path, problems: List[AtCoderProblem]):
    downloaded: List[str] = []
    skipped: List[str] = []
    failed: List[Tuple[str, str]] = []
    tests_dir = contest_dir / "tests"

    for problem in problems:
        dst_dir = tests_dir / problem.index
        if not _tests_need_download(dst_dir):
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
    if _is_workspace_root(contest_dir, config):
        raise RefreshError(_workspace_root_error_message())

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
    if failed:
        raise RefreshError(f"Sample download failed for: {_problem_list([problem for problem, _reason in failed])}")

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

    print()
    if RICH_AVAILABLE:
        console.print(f"Refresh {result.contest_id}", style="bold")
        table = Table.grid(padding=(0, 4))
        table.add_column(style="bold")
        table.add_column()
        for key, value in rows:
            table.add_row(key, value)
        console.print(table)
        return

    print(f"Refresh {result.contest_id}")
    for key, value in rows:
        print(f"{key:<10} {value}")


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
    return 0


_fetch_contest_problems_strict = fetch_contest_problems_strict
_infer_source_name_for_metadata = infer_source_name_for_metadata
_download_missing_samples = download_missing_samples
_refresh_contest = refresh_contest
