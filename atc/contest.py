import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .config import (
        config_root,
        _find_project_root,
        config_problems,
        default_language,
        load_config,
    )
    from .console import error, ok as print_ok, warn
    from .samples import download_samples, print_sample_download_summary
    from .templates import load_template
except ImportError:
    from config import (
        config_root,
        _find_project_root,
        config_problems,
        default_language,
        load_config,
    )
    from console import error, ok as print_ok, warn
    from samples import download_samples, print_sample_download_summary
    from templates import load_template


def cmd_new(contest: str, lang: Optional[str] = None):
    config = load_config(Path.cwd())
    lang = lang or default_language(config)
    create_contest_files(contest, Path(contest), lang, config)


def cmd_contest(contest: str, lang: Optional[str] = None):
    config = load_config(Path.cwd())
    lang = lang or default_language(config)
    contest_dir = resolve_contest_dir(contest, config)

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
    problems = config_problems(config)
    tests = base / "tests"
    base.mkdir(parents=True, exist_ok=True)

    template_content = load_template(lang, config, Path.cwd())

    failed_downloads = []
    for p in problems:
        source_file = base / f"{p}.{lang}"
        if not source_file.exists():
            source_file.write_text(template_content, encoding="utf-8")

        print(f"fetching {p} ...", end=" ", flush=True)
        sample_ok, reason = download_samples(contest_id, p, tests / p)
        if sample_ok:
            print_ok("done")
        else:
            error("failed")
            if reason:
                print(f"  reason: {reason}")
            failed_downloads.append((p, reason))

    print_sample_download_summary(problems, failed_downloads)

    if failed_downloads:
        print(f"\n{contest_id} ({lang}) files ready, but sample download incomplete.")
    else:
        print(f"\n{contest_id} ({lang}) ready.")


def contest_category_key(contest: str) -> Optional[str]:
    match = re.fullmatch(r"(abc|arc|agc)\d+", contest.lower())
    return match.group(1) if match else None


def resolve_contest_dir(contest: str, config: dict):
    contest_path = Path(contest)
    if contest_path.is_absolute():
        return contest_path

    paths = config.get("paths", {})
    root_path = config_root(config)
    category_key = contest_category_key(contest)
    category_dir = str(paths.get(category_key) or "").strip() if category_key else ""

    if root_path:
        if category_dir:
            return root_path / category_dir / contest
        return root_path / contest

    return contest_path


def write_current_contest(contest_dir: Path, config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    project_root = _find_project_root(Path.cwd(), config)
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


_create_contest_files = create_contest_files
_contest_category_key = contest_category_key
_resolve_contest_dir = resolve_contest_dir
_write_current_contest = write_current_contest
