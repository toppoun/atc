import re
from pathlib import Path
from typing import Optional

from .config import config_root, find_project_root


class ContestPathConfigError(ValueError):
    pass


def resolve_contest_group(contest: str, paths: dict) -> Optional[str]:
    contests = paths.get("contests")
    if "contests" in paths and not isinstance(contests, dict):
        raise ContestPathConfigError("[paths.contests] must be a table.")

    if isinstance(contests, dict) and contests:
        lowered = contest.lower()
        matched_group = None
        for pattern, group in contests.items():
            pattern = str(pattern)
            try:
                matched = re.fullmatch(pattern, lowered)
            except re.error:
                raise ContestPathConfigError(f"invalid contest path regex: {pattern}")
            if matched and matched_group is None:
                matched_group = str(group or "").strip()
        if matched_group is not None:
            return matched_group

    return None


def resolve_contest_dir(contest: str, config: dict) -> Path:
    contest_path = Path(contest)
    if contest_path.is_absolute():
        return contest_path

    paths = config.get("paths", {})
    root_path = config_root(config)
    category_dir = resolve_contest_group(contest, paths)

    if root_path:
        if category_dir:
            return root_path / category_dir / contest
        return root_path / contest

    return contest_path


def is_workspace_root(path: Path, config: dict) -> bool:
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
