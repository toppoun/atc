import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import tomllib

from .models import AtCoderProblem
from .config import SOURCE_EXTS
from .console import warn


# --- Constants ---
CONTEST_METADATA_PATH = Path(".atc") / "contest.toml"


@dataclass(frozen=True)
class ContestProblem:
    index: str
    title: str = ""
    task_id: str = ""
    url: str = ""
    source: str = ""
    tests: str = ""


def _normalize_metadata_problem_index(problem: object) -> str:
    return str(problem or "").strip().upper()


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

        index = _normalize_metadata_problem_index(raw_problem.get("index"))
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


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_contest_metadata(
    contest_id: str,
    base: Path,
    lang: str,
    problems: List[AtCoderProblem],
    source_by_index: Optional[Dict[str, str]] = None,
):
    atc_dir = base / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)
    contest_file = atc_dir / "contest.toml"

    lines = [
        f"contest_id = {_toml_string(contest_id)}",
        "",
    ]
    for problem in problems:
        source = source_by_index.get(problem.index, f"{problem.index}.{lang}") if source_by_index else f"{problem.index}.{lang}"
        lines.extend(
            [
                "[[problems]]",
                f"index = {_toml_string(problem.index)}",
                f"title = {_toml_string(problem.title)}",
                f"task_id = {_toml_string(problem.task_id)}",
                f"url = {_toml_string(problem.url)}",
                f"source = {_toml_string(source)}",
                f"tests = {_toml_string(f'tests/{problem.index}')}",
                "",
            ]
        )

    contest_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return contest_file


def infer_source_name_for_metadata(contest_dir: Path, problem_index: str, default_lang: str) -> str:
    for ext in SOURCE_EXTS:
        candidate = contest_dir / f"{problem_index}.{ext}"
        if candidate.is_file():
            return candidate.name
    return f"{problem_index}.{default_lang}"

