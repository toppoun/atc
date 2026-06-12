from pathlib import Path
from typing import List
from dataclasses import dataclass, field

from atc.core.templates import load_template


@dataclass
class ManualSourceResult:
    created: List[Path] = field(default_factory=list)
    skipped: List[Path] = field(default_factory=list)


def _expand_problem_targets(targets: List[str]) -> List[str]:
    problems: List[str] = []

    for target in targets:
        if "~" in target or "-" in target:
            sep = "~" if "~" in target else "-"
            start, end = target.split(sep, 1)
            for code in range(ord(start.upper()), ord(end.upper()) + 1):
                problems.append(chr(code))
        else:
            problems.append(target.upper())

    return problems


def create_manual_sources(cwd: Path, targets: List[str], lang: str, config: dict) -> ManualSourceResult:
    template_content = load_template(lang, config, cwd)
    result = ManualSourceResult()

    for problem in _expand_problem_targets(targets):
        path = cwd / f"{problem}.{lang}"
        if path.exists():
            result.skipped.append(path)
        else:
            result.created.append(path)
            path.write_text(template_content, encoding="utf-8")
    
    return result