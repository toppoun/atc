from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from ..argparse_utils import ArgumentParseError, AtcArgumentParser
from atc.core.config import (
    CONFIG_FILE_NAME,
    config_to_toml,
    default_config_template,
    find_config_file,
    load_config,
)
from atc.ui.console import print_usage
from atc.core.contest import cmd_contest, cmd_new
from atc.core.manual import cmd_manual, cmd_manual_tests
from atc.core.refresh import cmd_refresh
from atc.core.stress import cmd_stress, cmd_stress_init, cmd_stress_promote
from atc.commands.template_commands import cmd_template_list, cmd_template_show
from atc.core.watch import cmd_watch

# リファクタ後
from atc.commands.parsing import parse_handler_args
from atc.commands.run import handle_run
from atc.commands.config import handle_config
from atc.commands.usage_error import USAGE_ERROR

# --- Constants ---



# --- Command model ---
@dataclass(frozen=True)
class CommandSpec:
    name: str
    aliases: Tuple[str, ...]
    usage: Tuple[Tuple[str, str], ...]
    category: str
    handler: Callable[[List[str]], Any]




# --- help handler ---
def handle_help(args: List[str]):
    if args:
        return USAGE_ERROR
    print_usage(usage_sections())
    return 0


# --- Contest hadlers ---
def handle_new(args: List[str]):
    parser = AtcArgumentParser(prog="atc new")
    parser.add_argument("contest")
    parser.add_argument("lang", nargs="?")
    parsed = parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    cmd_new(parsed.contest, parsed.lang)
    return 0


def handle_contest(args: List[str]):
    parser = AtcArgumentParser(prog="atc contest")
    parser.add_argument("contest")
    parser.add_argument("lang", nargs="?")
    parsed = parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    cmd_contest(parsed.contest, parsed.lang)
    return 0


def handle_refresh(args: List[str]):
    parser = AtcArgumentParser(prog="atc refresh")
    parser.add_argument("-y", "--yes", action="store_true")
    parser.add_argument("contest", nargs="?")
    parsed = parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    return cmd_refresh(parsed.contest, yes=parsed.yes)


# --- Watch hundler ---
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

    parsed = parse_handler_args(parser, args)
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
        parsed = parse_handler_args(parser, args)
        if parsed is None:
            return USAGE_ERROR
        return cmd_stress_init(parsed.problem)
    if args and args[0] == "promote":
        parser = AtcArgumentParser(prog="atc stress promote")
        parser.add_argument("subcommand")
        parser.add_argument("problem")
        parser.add_argument("--name")
        parser.add_argument("--force", action="store_true")
        parsed = parse_handler_args(parser, args)
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
    parsed = parse_handler_args(parser, args)
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
        usage=(("atc new abc413 [py|cpp]", "Create files for a contest in the current directory."),),
        category="Contest",
        handler=handle_new,
    ),
    CommandSpec(
        name="contest",
        aliases=("contests", "c"),
        usage=(("atc contest abc413 [py|cpp]", "Create or select a contest directory."),),
        category="Contest",
        handler=handle_contest,
    ),
    CommandSpec(
        name="refresh",
        aliases=(),
        usage=(("atc refresh [contest] [--yes]", "Refresh contest metadata and missing samples without touching sources."),),
        category="Contest",
        handler=handle_refresh,
    ),
    CommandSpec(
        name="config",
        aliases=(),
        usage=(
            ("atc config show", "Show configurations."), 
            ("atc config init", "Initialize configuration in the root directry."), 
            ("atc config doctor", "Diagnose configurations."),
            ),
        category="Config",
        handler=handle_config,
    ),
    CommandSpec(
        name="run",
        aliases=("r", "test", "t"),
        usage=(
            ("atc run A [python|pypy|cpp]", "Run tests for one problem."), 
            ("atc run all [python|pypy|cpp]", "Run tests for all available problems."), 
            ),
        category="Run",
        handler=handle_run,
    ),
    CommandSpec(
        name="watch",
        aliases=("w", "auto"),
        usage=(("atc watch [A] [python|pypy|cpp]", "Watch files and rerun tests automatically."),),
        category="Run",
        handler=handle_watch,
    ),
    CommandSpec(
        name="template",
        aliases=(),
        usage=(
            ("atc template list [py|cpp|stress]", "List templates."), 
            ("atc template show <py|cpp|stress> <name>", "Print a template body."),
            ),
        category="Template",
        handler=handle_template,
    ),
    CommandSpec(
        name="stress",
        aliases=(),
        usage=(
            ("atc stress A [py|cpp] [--count N] [--seed S]", "Run randomized stress tests against a brute force solution."), 
            ("atc stress init A", "Create a blute and generate file."), 
            ("atc stress promote A [--name NAME] [--force]", "Promote to test/"),
            ),
        category="Stress",
        handler=handle_stress,
    ),
    CommandSpec(
        name="manual",
        aliases=(),
        usage=(
            ("atc manual A B C", "Create problem files"),
            ("atc manual tests", "Download samples for the current folder."),
            ),
        category="Manual",
        handler=handle_manual,
    ),
    CommandSpec(
        name="help",
        aliases=("usage", "-h", "--help"),
        usage=(
            ("atc help", "Show usage."), 
            ),
        category="Help",
        handler=handle_help,
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
def usage_sections() -> list[Tuple[str, list[Tuple[str, str]]]]:
    sections: Dict[str, list[Tuple[str, str]]] = {}

    for spec in COMMANDS:
        rows = sections.setdefault(spec.category, [])
        rows.extend(spec.usage)
    return [(category, rows) for category, rows in sections.items()]
