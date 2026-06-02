import time
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from .console import Live, RICH_AVAILABLE, console, print_text
    from .config import SOURCE_EXTS, load_config, watch_settings
    from .metadata import contest_metadata_problems
    from .problems import resolve_available_problems
    from .runner import LOG_DIR, normalize_problem, run_problem_tests, write_test_log
    from .watch_render import WATCH_WAIT_MESSAGE, WatchState, build_plain_watch_view, build_watch_view
except ImportError:
    from console import Live, RICH_AVAILABLE, console, print_text
    from config import SOURCE_EXTS, load_config, watch_settings
    from metadata import contest_metadata_problems
    from problems import resolve_available_problems
    from runner import LOG_DIR, normalize_problem, run_problem_tests, write_test_log
    from watch_render import WATCH_WAIT_MESSAGE, WatchState, build_plain_watch_view, build_watch_view


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


def _problem_titles(cwd: Path):
    return {problem.index: problem.title for problem in contest_metadata_problems(cwd, warn_on_error=True) if problem.title}


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
    if problems is None:
        problems = resolve_available_problems(cwd, load_config(cwd))
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
    if problems is None:
        problems = resolve_available_problems(cwd, load_config(cwd))
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


def _select_problem_after_change(
    cwd: Path,
    paths: Set[Path],
    selected: List[str],
    problems: List[str],
    last_problem: str = "",
):
    selected_set = set(selected)
    changed = set()
    has_all_change = False

    for path in paths:
        problem = _problem_from_changed_path(cwd, path, problems)
        if problem == "ALL":
            has_all_change = True
        elif problem:
            changed.add(problem)

    if selected_set:
        changed &= selected_set
    if changed:
        return sorted(changed)[0]
    if has_all_change:
        return last_problem or None
    return None


def _run_watch_problem(problem: str, run_language: Optional[str], titles: Dict[str, str], state: WatchState):
    state.problem = problem
    state.title = titles.get(problem, "")
    state.message = f"Running {problem}..."
    result = run_problem_tests(problem, run_language, show_compile=False)
    updated_at = time.monotonic()
    state.problem = result.problem
    state.title = titles.get(result.problem, state.title)
    state.result = result
    state.updated_at = updated_at
    state.message = ""
    write_test_log([result])
    return result


def _print_plain_watch_result(state: WatchState):
    print_text(build_plain_watch_view(state))


def _run_watch_loop(
    cwd: Path,
    watch_problems: List[str],
    selected: List[str],
    poll_seconds: float,
    debounce_seconds: float,
    run_one,
    on_tick=None,
):
    snapshot = _watch_snapshot(cwd, watch_problems)
    pending = set()
    last_change_at = None
    last_problem = selected[0] if selected else ""

    try:
        while True:
            time.sleep(poll_seconds)
            now = time.monotonic()
            current = _watch_snapshot(cwd, watch_problems)
            changed = _changed_paths(snapshot, current)
            if changed:
                snapshot = current
                pending.update(changed)
                last_change_at = now
                if on_tick:
                    on_tick(now)
                continue

            if pending and last_change_at and now - last_change_at >= debounce_seconds:
                problem = _select_problem_after_change(cwd, pending, selected, watch_problems, last_problem)
                if problem:
                    last_problem = problem
                    run_one(problem)
                pending.clear()
                last_change_at = None

            if on_tick:
                on_tick(now)
    except KeyboardInterrupt:
        print_text()
        print_text("watch stopped.")


def cmd_watch(args):
    cwd = Path.cwd()
    config = load_config(cwd)
    resolved_problems = resolve_available_problems(cwd, config)
    poll_seconds, debounce_seconds, _watch_warnings = watch_settings(config)
    run_language = None
    selected = []

    for arg in args:
        low = arg.lower()
        if low in ["python", "py", "pypy", "cpp"]:
            run_language = low
        elif low in ["all", "--all"]:
            print_text("atc watch --all is deprecated.")
            print_text("Use `atc test all` for one-shot all tests.")
            return 0
        else:
            selected.append(normalize_problem(arg))

    if selected:
        watch_problems = selected
    else:
        watch_problems = resolved_problems

    titles = _problem_titles(cwd)
    state = WatchState(cwd=cwd, problems=watch_problems, log_path=LOG_DIR / "last.log")

    if RICH_AVAILABLE and Live:
        last_render_at = 0.0

        with Live(build_watch_view(state), console=console, refresh_per_second=4) as live:
            def run_one(problem: str):
                nonlocal last_render_at
                state.problem = problem
                state.title = titles.get(problem, "")
                state.message = f"Running {problem}..."
                live.update(build_watch_view(state))
                _run_watch_problem(problem, run_language, titles, state)
                last_render_at = state.updated_at or time.monotonic()
                live.update(build_watch_view(state, now=last_render_at))

            def tick(now: float):
                nonlocal last_render_at
                if state.updated_at is None or now - last_render_at < 1.0:
                    return
                live.update(build_watch_view(state, now=now))
                last_render_at = now

            if selected:
                run_one(selected[0])
            _run_watch_loop(cwd, watch_problems, selected, poll_seconds, debounce_seconds, run_one, on_tick=tick)
        return 0

    print_text(f"Watching {cwd}")
    print_text(WATCH_WAIT_MESSAGE)

    def run_one_plain(problem: str):
        _run_watch_problem(problem, run_language, titles, state)
        _print_plain_watch_result(state)

    if selected:
        run_one_plain(selected[0])
    _run_watch_loop(cwd, watch_problems, selected, poll_seconds, debounce_seconds, run_one_plain)
    return 0
