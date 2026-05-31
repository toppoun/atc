import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

try:
    from .config import SOURCE_EXTS, config_problems, load_config
    from .console import warn
except ImportError:
    from config import SOURCE_EXTS, config_problems, load_config
    from console import warn


CONTEST_METADATA_PATH = Path(".atc") / "contest.toml"


@dataclass(frozen=True)
class ContestProblem:
    index: str
    title: str = ""
    task_id: str = ""
    url: str = ""
    source: str = ""
    tests: str = ""


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


def _contest_metadata_error_message(metadata_file: Path, error: Exception) -> str:
    return f"failed to read contest metadata: {metadata_file} ({error})"


def contest_metadata_error(contest_dir: Path) -> Optional[str]:
    metadata_file = contest_dir / CONTEST_METADATA_PATH
    if not metadata_file.exists():
        return None

    try:
        with metadata_file.open("rb") as f:
            tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        return _contest_metadata_error_message(metadata_file, e)

    return None


def read_contest_metadata(contest_dir: Path, warn_on_error: bool = False) -> dict:
    metadata_file = contest_dir / CONTEST_METADATA_PATH
    if not metadata_file.exists():
        return {}

    try:
        with metadata_file.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        if warn_on_error:
            warn(_contest_metadata_error_message(metadata_file, e))
        return {}

    return data if isinstance(data, dict) else {}


def contest_metadata_problems(contest_dir: Path, warn_on_error: bool = False) -> List[ContestProblem]:
    raw_problems = read_contest_metadata(contest_dir, warn_on_error=warn_on_error).get("problems", [])
    if not isinstance(raw_problems, list):
        return []

    problems = []
    seen = set()
    for raw_problem in raw_problems:
        if not isinstance(raw_problem, dict):
            continue

        index = _normalize_problem_index(raw_problem.get("index"))
        if not index or index in seen:
            continue

        seen.add(index)
        problems.append(
            ContestProblem(
                index=index,
                title=str(raw_problem.get("title") or ""),
                task_id=str(raw_problem.get("task_id") or ""),
                url=str(raw_problem.get("url") or ""),
                source=str(raw_problem.get("source") or ""),
                tests=str(raw_problem.get("tests") or ""),
            )
        )
    return problems


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
