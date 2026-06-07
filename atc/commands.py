from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from .argparse_utils import ArgumentParseError, AtcArgumentParser
from atc.core.config import (
    CONFIG_FILE_NAME,
    config_to_toml,
    default_config_template,
    find_config_file,
    load_config,
)
from atc.ui.console import error, warn, print_detailed_result, print_all_summary
from atc.core.contest import cmd_contest, cmd_new
from atc.core.doctor import cmd_config_doctor
from atc.core.manual import cmd_manual, cmd_manual_tests
from atc.core.refresh import cmd_refresh
from atc.core.runner import run_all_problem_tests, run_problem_tests, write_test_log
from atc.core.stress import cmd_stress, cmd_stress_init, cmd_stress_promote
from .template_commands import cmd_template_list, cmd_template_show
from .watch import cmd_watch


# --- Constants ---
class _UsageError:
    pass

USAGE_ERROR = _UsageError()


# --- Command model ---
@dataclass(frozen=True)
class CommandSpec:
    name: str
    aliases: Tuple[str, ...]
    usage: Tuple[str, ...]
    description: str
    handler: Callable[[List[str]], Any]


# --- Argument parsing helpes ---
def _parse_handler_args(parser: AtcArgumentParser, args: List[str]):
    try:
        return parser.parse_args(args)
    except ArgumentParseError as e:
        if str(e):
            error(f"Error: {e}")
        return None


# --- Contest hadlers ---
def handle_new(args: List[str]):
    parser = AtcArgumentParser(prog="atc new")
    parser.add_argument("contest")
    parser.add_argument("lang", nargs="?")
    parsed = _parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    cmd_new(parsed.contest, parsed.lang)
    return 0


def handle_contest(args: List[str]):
    parser = AtcArgumentParser(prog="atc contest")
    parser.add_argument("contest")
    parser.add_argument("lang", nargs="?")
    parsed = _parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    cmd_contest(parsed.contest, parsed.lang)
    return 0


def handle_refresh(args: List[str]):
    parser = AtcArgumentParser(prog="atc refresh")
    parser.add_argument("-y", "--yes", action="store_true")
    parser.add_argument("contest", nargs="?")
    parsed = _parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    return cmd_refresh(parsed.contest, yes=parsed.yes)


# --- Config handlers ---
def handle_config(args: List[str]):
    if not args:
        return USAGE_ERROR

    subcmd = args[0]
    if subcmd == "show":
        config_file = find_config_file(Path.cwd())
        config = load_config(Path.cwd())
        print(f"config file: {config_file.resolve() if config_file else '(default)'}")
        print()
        print(config_to_toml(config), end="")
    elif subcmd == "init":
        atc_dir = Path(".atc")
        atc_dir.mkdir(parents=True, exist_ok=True)
        config_file = atc_dir / CONFIG_FILE_NAME
        if config_file.exists():
            warn(f"already exists: {config_file.resolve()}")
            return 0
        config_file.write_text(config_to_toml(default_config_template()), encoding="utf-8")
        print(f"created: {config_file.resolve()}")
    elif subcmd == "doctor":
        cmd_config_doctor()
    else:
        return USAGE_ERROR
    return 0


# --- Run hundlers ---
def handle_run(args: List[str]):
    parser = AtcArgumentParser(prog="atc run")
    parser.add_argument("problem")
    parser.add_argument("lang", nargs="?")
    parsed = _parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    if parsed.problem.lower() == "all":
        results = run_all_problem_tests(parsed.lang)
        print_all_summary(results)
        write_test_log(results)
        return 0 if bool(results) and all(result.passed for result in results) else 1
    else:
        result = run_problem_tests(parsed.problem, parsed.lang, show_compile=True)
        print_detailed_result(result)
        write_test_log([result])
        return 0 if result.passed else 1


def handle_watch(args: List[str]):
    result = cmd_watch(args)
    return result if result is not None else 0


# --- Template handlers ---
def handle_template(args: List[str]):
    parser = AtcArgumentParser(prog="atc template")
    subparsers = parser.add_subparsers(dest="subcommand", required=True, parser_class=AtcArgumentParser)

    list_parser = subparsers.add_parser("list", prog="atc template list")
    list_parser.add_argument("lang", nargs="?")

    show_parser = subparsers.add_parser("show", prog="atc template show")
    show_parser.add_argument("lang")
    show_parser.add_argument("name")

    parsed = _parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR

    if parsed.subcommand == "list":
        return cmd_template_list(parsed.lang)
    if parsed.subcommand == "show":
        return cmd_template_show(parsed.lang, parsed.name)
    return USAGE_ERROR


# --- Stress handlers ---
def handle_stress(args: List[str]):
    if args and args[0] == "init":
        parser = AtcArgumentParser(prog="atc stress init")
        parser.add_argument("subcommand")
        parser.add_argument("problem")
        parsed = _parse_handler_args(parser, args)
        if parsed is None:
            return USAGE_ERROR
        return cmd_stress_init(parsed.problem)
    if args and args[0] == "promote":
        parser = AtcArgumentParser(prog="atc stress promote")
        parser.add_argument("subcommand")
        parser.add_argument("problem")
        parser.add_argument("--name")
        parser.add_argument("--force", action="store_true")
        parsed = _parse_handler_args(parser, args)
        if parsed is None:
            return USAGE_ERROR
        return cmd_stress_promote(parsed.problem, name=parsed.name, force=parsed.force)

    parser = AtcArgumentParser(prog="atc stress")
    parser.add_argument("problem")
    parser.add_argument("lang", nargs="?")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--gen")
    parser.add_argument("--brute")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--compare", default="strip")
    parsed = _parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    return cmd_stress(
        parsed.problem,
        parsed.lang,
        count=parsed.count,
        seed=parsed.seed,
        gen=parsed.gen,
        brute=parsed.brute,
        timeout=parsed.timeout,
        compare=parsed.compare,
    )


# --- Manual handlers ---
def handle_manual(args: List[str]):
    if len(args) >= 1 and args[0] == "tests":
        cmd_manual_tests()
    else:
        cmd_manual(args)
    return 0


# --- Command registry ---
COMMANDS: Tuple[CommandSpec, ...] = (
    CommandSpec(
        name="new",
        aliases=(),
        usage=("atc new abc413 [py|cpp]  (デフォルトは config の defaults.language、未設定なら cpp)",),
        description="Create files for a contest in the current directory.",
        handler=handle_new,
    ),
    CommandSpec(
        name="contest",
        aliases=("contests", "c"),
        usage=("atc contest abc413 [py|cpp]",),
        description="Create or select a contest directory.",
        handler=handle_contest,
    ),
    CommandSpec(
        name="refresh",
        aliases=(),
        usage=("atc refresh [contest] [--yes]",),
        description="Refresh contest metadata and missing samples without touching sources.",
        handler=handle_refresh,
    ),
    CommandSpec(
        name="config",
        aliases=(),
        usage=("atc config show", "atc config init", "atc config doctor"),
        description="Show, initialize, or diagnose configuration.",
        handler=handle_config,
    ),
    CommandSpec(
        name="run",
        aliases=("r", "test", "t"),
        usage=("atc run A [python|pypy|cpp]", "atc run all [python|pypy|cpp]"),
        description="Run tests for one problem or all available problems.",
        handler=handle_run,
    ),
    CommandSpec(
        name="watch",
        aliases=("w", "auto"),
        usage=("atc watch [A] [python|pypy|cpp]",),
        description="Watch files and rerun tests automatically.",
        handler=handle_watch,
    ),
    CommandSpec(
        name="template",
        aliases=(),
        usage=("atc template list [py|cpp|stress]", "atc template show <py|cpp|stress> <name>"),
        description="List templates or print a template body.",
        handler=handle_template,
    ),
    CommandSpec(
        name="stress",
        aliases=(),
        usage=("atc stress A [py|cpp] [--count N] [--seed S]", "atc stress init A", "atc stress promote A [--name NAME] [--force]"),
        description="Run randomized stress tests against a brute force solution.",
        handler=handle_stress,
    ),
    CommandSpec(
        name="manual",
        aliases=(),
        usage=("atc manual A B C", "atc manual tests  (現在のフォルダ名を contest_id としてサンプル取得)"),
        description="Create problem files or download samples for the current folder.",
        handler=handle_manual,
    ),
)


# --- Command lookup ---
def _command_map() -> Dict[str, CommandSpec]:
    mapping: Dict[str, CommandSpec] = {}
    for spec in COMMANDS:
        mapping[spec.name] = spec
        for alias in spec.aliases:
            mapping[alias] = spec
    return mapping


COMMAND_BY_NAME = _command_map()


def resolve_command(name: str):
    return COMMAND_BY_NAME.get(name)


# --- Usage data ---
def usage_lines() -> List[str]:
    lines: List[str] = []
    for spec in COMMANDS:
        lines.extend(spec.usage)
    return lines


USAGE_SECTIONS: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    (
        "Contest",
        (
            ("atc contest <contest> [py|cpp]", "Create/open contest"),
            ("atc new <contest> [py|cpp]", "Create contest files"),
            ("atc refresh [contest] [--yes]", "Refresh metadata/samples"),
        ),
    ),
    (
        "Run",
        (
            ("atc run <A|all> [python|pypy|cpp]", "Run tests"),
            ("atc watch [A] [python|pypy|cpp]", "Watch and run on save"),
        ),
    ),
    (
        "Config",
        (
            ("atc config show", "Show resolved config"),
            ("atc config init", "Create config file"),
            ("atc config doctor", "Diagnose environment"),
        ),
    ),
    (
        "Template",
        (
            ("atc template list [py|cpp|stress]", "List templates"),
            ("atc template show <kind> <name>", "Show template content"),
        ),
    ),
    (
        "Stress",
        (
            ("atc stress A [py|cpp] [--count N] [--seed S]", "Run stress test"),
            ("atc stress init A", "Create stress files"),
            ("atc stress promote A [--name NAME] [--force]", "Promote failed case"),
        ),
    ),
    (
        "Manual",
        (
            ("atc manual A B C", "Create manual problems"),
            ("atc manual tests", "Download samples for current folder contest"),
        ),
    ),
)


def usage_sections() -> List[Tuple[str, List[Tuple[str, str]]]]:
    return [(title, list(rows)) for title, rows in USAGE_SECTIONS]
