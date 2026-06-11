import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..models import AtCoderProblem

from atc.core.atcoder import (
    build_fallback_task_url,
    fetch_atcoder_tasks,
)
from atc.core.config import (
    find_project_root,
    config_problems,
    default_language,
    load_config,
)
from atc.ui.console import error, ok as print_ok, warn
from .metadata import write_contest_metadata
from .paths import ContestPathConfigError, resolve_contest_dir, resolve_contest_group
from atc.core.samples import download_samples, print_sample_download_summary
from .templates import load_template


def cmd_new(contest: str, lang: Optional[str] = None):
    config = load_config(Path.cwd())
    lang = lang or default_language(config)
    create_contest_files(contest, Path(contest), lang, config)


def cmd_contest(contest: str, lang: Optional[str] = None):
    config = load_config(Path.cwd())
    lang = lang or default_language(config)
    try:
        contest_dir = resolve_contest_dir(contest, config)
    except ContestPathConfigError as e:
        error(f"Error: {e}")
        sys.exit(1)

    if contest_dir.exists():
        if not contest_dir.is_dir():
            error(f"Error: {contest_dir} exists but is not a directory.")
            sys.exit(1)
        warn(f"{contest_dir} already exists. Skip creation and sample download.")
    else:
        create_contest_files(contest, contest_dir, lang, config)

    current_contest_file = write_current_contest(contest_dir.resolve(), config)
    print(f"current contest saved: {current_contest_file}")


def create_contest_files(contest_id: str, base: Path, lang: str, config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    problems = load_contest_problems(contest_id, config)
    tests = base / "tests"
    base.mkdir(parents=True, exist_ok=True)

    template_content = load_template(lang, config, Path.cwd())

    failed_downloads = []
    for problem in problems:
        source_file = base / f"{problem.index}.{lang}"
        if not source_file.exists():
            source_file.write_text(template_content, encoding="utf-8")

        print(f"fetching {problem.index} ...", end=" ", flush=True)
        sample_ok, reason = download_samples(contest_id, problem.index, tests / problem.index, url=problem.url)
        if sample_ok:
            print_ok("done")
        else:
            error("failed")
            if reason:
                print(f"  reason: {reason}")
            failed_downloads.append((problem.index, reason))

    write_contest_metadata(contest_id, base, lang, problems)
    print_sample_download_summary([problem.index for problem in problems], failed_downloads)

    if failed_downloads:
        print(f"\n{contest_id} ({lang}) files ready, but sample download incomplete.")
    else:
        print(f"\n{contest_id} ({lang}) ready.")


def guessed_problem_url(contest_id: str, problem_index: str) -> str:
    return build_fallback_task_url(contest_id, problem_index)


def fallback_contest_problems(contest_id: str, problem_indexes: List[str]) -> List[AtCoderProblem]:
    return [
        AtCoderProblem(
            index=problem_index,
            title="",
            url=guessed_problem_url(contest_id, problem_index),
            task_id=f"{contest_id}_{problem_index.lower()}",
        )
        for problem_index in problem_indexes
    ]


def load_contest_problems(contest_id: str, config: dict) -> List[AtCoderProblem]:
    fetch_failed = False
    try:
        problems = fetch_atcoder_tasks(contest_id)
    except Exception as e:
        warn(f"Failed to fetch AtCoder tasks page: {e}")
        fetch_failed = True
        problems = []

    if problems:
        return problems

    if not fetch_failed:
        warn("Failed to parse the problem list table from the AtCoder tasks page.")
    warn("Falling back to configured problem letters and guessed URLs. ADT contests may fail with this fallback.")
    return fallback_contest_problems(contest_id, config_problems(config))


def write_current_contest(contest_dir: Path, config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    project_root = find_project_root(Path.cwd(), config)
    atc_dir = project_root / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().isoformat(timespec="milliseconds")
    current_contest_file = atc_dir / "current-contest.json"
    current_contest_file.write_text(
        json.dumps(
            {
                "contestDir": str(contest_dir.resolve()),
                "requestId": now,
                "createdAt": now,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return current_contest_file.resolve()