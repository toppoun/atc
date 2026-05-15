import sys
from pathlib import Path

try:
    from .config import _config_problems, _default_language, load_config
    from .console import GREEN, color_text, error, ok as print_ok
    from .samples import download_samples
    from .templates import load_template
except ImportError:
    from config import _config_problems, _default_language, load_config
    from console import GREEN, color_text, error, ok as print_ok
    from samples import download_samples
    from templates import load_template


def cmd_manual(args):
    cwd = Path.cwd()
    config = load_config(cwd)
    # 簡易的に拡張子を判別（引数に .cpp 等が含まれていればそれを使う）
    lang = _default_language(config)
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
    problems = _config_problems(config)
    contest = cwd.name.lower()
    tests = cwd / "tests"

    if not contest:
        error("コンテストIDを現在のフォルダ名から取得できません。")
        sys.exit(1)

    print(f"contest: {contest}")
    for p in problems:
        print(f"fetching {p} ...", end=" ", flush=True)
        sample_ok, reason = download_samples(contest, p, tests / p)
        if sample_ok:
            print_ok("done")
        else:
            error("failed")
            if reason:
                print(f"  reason: {reason}")
