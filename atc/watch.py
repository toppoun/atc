import time
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from .console import print_text, print_watch_header
    from .config import SOURCE_EXTS, config_problems, load_config, watch_settings
    from .runner import LOG_DIR, available_problems, normalize_problem, run_auto_tests
except ImportError:
    from console import print_text, print_watch_header
    from config import SOURCE_EXTS, config_problems, load_config, watch_settings
    from runner import LOG_DIR, available_problems, normalize_problem, run_auto_tests


CONFIG_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
    "Makefile",
    "CMakeLists.txt",
}
CONFIG_PATHS = {
    Path(".atc") / "config.toml",
}


def _watch_snapshot(cwd: Path, problems: Optional[List[str]] = None):
    snapshot = {}
    for path in _watch_paths(cwd, problems):
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot[path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _watch_paths(cwd: Path, problems: Optional[List[str]] = None):
    problems = problems or config_problems(load_config(cwd))
    for problem in problems:
        for ext in SOURCE_EXTS:
            source = cwd / f"{problem}.{ext}"
            if source.exists():
                yield source

        testdir = cwd / "tests" / problem
        if testdir.exists():
            for path in testdir.rglob("*"):
                if path.is_file():
                    yield path

    for name in CONFIG_FILES:
        config = cwd / name
        if config.exists():
            yield config
    for rel_path in CONFIG_PATHS:
        config = cwd / rel_path
        if config.exists():
            yield config


def _changed_paths(before: Dict[Path, tuple], after: Dict[Path, tuple]):
    changed = set()
    for path in before.keys() | after.keys():
        if before.get(path) != after.get(path):
            changed.add(path)
    return changed


def _problem_from_changed_path(cwd: Path, path: Path, problems: Optional[List[str]] = None):
    problems = problems or config_problems(load_config(cwd))
    problem_set = set(problems)

    try:
        rel = path.relative_to(cwd)
    except ValueError:
        return None

    parts = rel.parts
    if rel in CONFIG_PATHS:
        return "ALL"
    if len(parts) == 1:
        if rel.name in CONFIG_FILES:
            return "ALL"
        if rel.suffix in [".py", ".cpp"] and rel.stem.upper() in problem_set:
            return rel.stem.upper()

    if len(parts) >= 2 and parts[0] == "tests" and parts[1].upper() in problem_set:
        return parts[1].upper()

    return None


def _changed_problems(cwd: Path, paths: Set[Path], selected: List[str], problems: Optional[List[str]] = None):
    selected_set = set(selected)
    changed = set()
    problems = problems or config_problems(load_config(cwd))

    for path in paths:
        problem = _problem_from_changed_path(cwd, path, problems)
        if problem == "ALL":
            return selected or available_problems(cwd, problems)
        if problem:
            changed.add(problem)

    if selected_set:
        changed &= selected_set
    return sorted(changed)


def cmd_watch(args):
    cwd = Path.cwd()
    config = load_config(cwd)
    configured_problems = config_problems(config)
    poll_seconds, debounce_seconds, _watch_warnings = watch_settings(config)
    run_language = None
    selected = []

    for arg in args:
        low = arg.lower()
        if low in ["python", "py", "pypy", "cpp"]:
            run_language = low
        elif low in ["all", "--all"]:
            selected = []
        else:
            selected.append(normalize_problem(arg))

    watch_problems = selected or configured_problems
    problems = selected or available_problems(cwd, configured_problems)
    print_watch_header(cwd, poll_seconds, debounce_seconds, LOG_DIR / "last.log", problems)
    run_auto_tests(problems, run_language, reason="initial", display_mode="watch")

    snapshot = _watch_snapshot(cwd, watch_problems)
    pending = set()
    last_change_at = None

    try:
        while True:
            time.sleep(poll_seconds)
            current = _watch_snapshot(cwd, watch_problems)
            changed = _changed_paths(snapshot, current)
            if changed:
                snapshot = current
                pending.update(changed)
                last_change_at = time.perf_counter()
                continue

            if pending and last_change_at and time.perf_counter() - last_change_at >= debounce_seconds:
                changed = _changed_problems(cwd, pending, selected, watch_problems)
                run_auto_tests(changed, run_language, reason="changed", display_mode="watch")
                pending.clear()
                last_change_at = None
    except KeyboardInterrupt:
        print_text()
        print_text("watch stopped.")
