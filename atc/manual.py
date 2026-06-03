import sys
from pathlib import Path

from .config import default_language, load_config
from .console import GREEN, color_text, error, ok as print_ok, warn
from .problems import resolve_sample_download_problems
from .samples import download_samples
from .templates import load_template


def cmd_manual(args):
    cwd = Path.cwd()
    config = load_config(cwd)
    # 簡易的に拡張子を判別（引数に .cpp 等が含まれていればそれを使う）
    lang = default_language(config)
    targets = []
    for arg in args:
        if arg in ["py", "cpp"]:
            lang = arg
            continue
        targets.append(arg)

    template_content = load_template(lang, config, cwd)
    for p in targets:
        # 範囲指定 A~E などの展開
        if "~" in p or "-" in p:
            sep = "~" if "~" in p else "-"
            s, e = p.split(sep)
            for c in range(ord(s), ord(e) + 1):
                f = cwd / f"{chr(c)}.{lang}"
                if not f.exists():
                    f.write_text(template_content, encoding="utf-8")
                    print(f" {color_text('Created', GREEN)}: {f.name}")
            continue

        f = cwd / f"{p}.{lang}"
        if not f.exists():
            f.write_text(template_content, encoding="utf-8")
            print(f" {color_text('Created', GREEN)}: {f.name}")


def cmd_manual_tests():
    cwd = Path.cwd()
    config = load_config(cwd)
    problems = resolve_sample_download_problems(cwd, config)
    contest = cwd.name.lower()
    tests = cwd / "tests"

    if not contest:
        error("コンテストIDを現在のフォルダ名から取得できません。")
        sys.exit(1)

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
            print_ok("done")
        else:
            error("failed")
            if reason:
                print(f"  reason: {reason}")
