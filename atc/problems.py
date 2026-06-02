import re
from pathlib import Path
from typing import List, Optional

try:
    from .config import SOURCE_EXTS, config_problems, load_config
    from .metadata import (
        ContestProblem,
        contest_metadata_error,
        contest_metadata_problems,
        read_contest_metadata,
    )
except ImportError:
    from config import SOURCE_EXTS, config_problems, load_config
    from metadata import (
        ContestProblem,
        contest_metadata_error,
        contest_metadata_problems,
        read_contest_metadata,
    )


def _normalize_problem_index(problem: object) -> str:
    return str(problem or "").strip().upper()


def _dedupe_problem_indexes(indexes: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for index in indexes:
        normalized = _normalize_problem_index(index)
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def _problem_sort_key(index: str):
    normalized = _normalize_problem_index(index)
    if len(normalized) == 1 and "A" <= normalized <= "Z":
        return (0, ord(normalized))

    parts = []
    for part in re.split(r"(\d+)", normalized):
        if not part:
            continue
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return (1, parts)


def _is_problem_source_index(index: str) -> bool:
    normalized = _normalize_problem_index(index)
    return bool(re.fullmatch(r"(?:[A-Z]|EX|[0-9]+|[A-Z][0-9]+)", normalized))


def source_file_problems(contest_dir: Path) -> List[str]:
    indexes = []
    for ext in SOURCE_EXTS:
        for source in contest_dir.glob(f"*.{ext}"):
            if source.is_file() and _is_problem_source_index(source.stem):
                indexes.append(source.stem)

    return sorted(_dedupe_problem_indexes(indexes), key=_problem_sort_key)


def resolve_available_problems(contest_dir: Path, config: Optional[dict] = None) -> List[str]:
    metadata_indexes = [problem.index for problem in contest_metadata_problems(contest_dir, warn_on_error=True)]
    if metadata_indexes:
        return metadata_indexes

    source_indexes = source_file_problems(contest_dir)
    if source_indexes:
        return source_indexes

    config = config or load_config(contest_dir)
    return config_problems(config)


def resolve_sample_download_problems(contest_dir: Path, config: Optional[dict] = None) -> List[ContestProblem]:
    metadata_problems = contest_metadata_problems(contest_dir, warn_on_error=True)
    if metadata_problems:
        return metadata_problems

    indexes = source_file_problems(contest_dir)
    if not indexes:
        config = config or load_config(contest_dir)
        indexes = config_problems(config)

    return [ContestProblem(index=index) for index in indexes]
