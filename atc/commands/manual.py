from typing import List
from pathlib import Path

from atc.core.config import default_language, load_config
from atc.core.manual import create_manual_sources
from atc.ui.console import GREEN, color_text, error, warn, ok
from atc.core.problems import resolve_sample_download_problems
from atc.core.samples import download_samples
from atc.commands.usage_error import USAGE_ERROR


# --- Manual handlers ---
def handle_manual(args: List[str]):
    if len(args) >= 1 and args[0] == "tests":
        if len(args) != 1:
            return USAGE_ERROR
        return cmd_manual_tests()
    return cmd_manual(args)


def cmd_manual(args):
    cwd = Path.cwd()
    config = load_config(cwd)
    lang = default_language(config)
    targets = []

    for arg in args:
        if arg in ["py", "cpp"]:
            lang = arg
            continue
        targets.append(arg)
    
    result = create_manual_sources(cwd, targets, lang, config)

    for path in result.created:
        print(f"{color_text('Created', GREEN)}: {path.name}")
    
    return 0


def cmd_manual_tests():
    cwd = Path.cwd()
    config = load_config(cwd)
    problems = resolve_sample_download_problems(cwd, config)
    contest = cwd.name.lower()
    tests = cwd / "tests"

    if not contest:
        error("コンテストIDを現在のフォルダ名から取得できません。")
        return 1

    if contest.startswith("adt_") and any(not problem.url for problem in problems):
        warn(
            f"using guessed task URLs for ADT. This may fail. "
            f"Run `atc contest {contest}` first to fetch task metadata."
        )

    print(f"contest: {contest}")
    for problem in problems:
        print(f"fetching {problem.index} ...", end=" ", flush=True)
        sample_ok, reason = download_samples(contest, problem.index, tests / problem.index, url=problem.url or None)
        if sample_ok:
            ok("done")
        else:
            error("failed")
            if reason:
                print(f"  reason: {reason}")
    return 0