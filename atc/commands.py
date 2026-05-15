from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

try:
    from .config import (
        CONFIG_FILE_NAME,
        _config_to_toml,
        _default_config,
        _find_config_file,
        load_config,
    )
    from .console import error, warn
    from .contest import cmd_contest, cmd_new
    from .doctor import cmd_config_doctor
    from .manual import cmd_manual, cmd_manual_tests
    from .runner import cmd_rerun, cmd_run, cmd_run_all
    from .visual import cmd_visual, parse_visual_args
    from .watch import cmd_watch
except ImportError:
    from config import (
        CONFIG_FILE_NAME,
        _config_to_toml,
        _default_config,
        _find_config_file,
        load_config,
    )
    from console import error, warn
    from contest import cmd_contest, cmd_new
    from doctor import cmd_config_doctor
    from manual import cmd_manual, cmd_manual_tests
    from runner import cmd_rerun, cmd_run, cmd_run_all
    from visual import cmd_visual, parse_visual_args
    from watch import cmd_watch


class _UsageError:
    pass


USAGE_ERROR = _UsageError()


@dataclass(frozen=True)
class CommandSpec:
    name: str
    aliases: Tuple[str, ...]
    usage: Tuple[str, ...]
    description: str
    handler: Callable[[List[str]], Any]


def handle_new(args: List[str]):
    if len(args) < 1:
        return USAGE_ERROR
    lang = args[1] if len(args) == 2 else None
    cmd_new(args[0], lang)
    return 0


def handle_contest(args: List[str]):
    if len(args) < 1:
        return USAGE_ERROR
    lang = args[1] if len(args) == 2 else None
    cmd_contest(args[0], lang)
    return 0


def handle_config(args: List[str]):
    if not args:
        return USAGE_ERROR

    subcmd = args[0]
    if subcmd == "show":
        config_file = _find_config_file(Path.cwd())
        config = load_config(Path.cwd())
        print(f"config file: {config_file.resolve() if config_file else '(default)'}")
        print()
        print(_config_to_toml(config), end="")
    elif subcmd == "init":
        atc_dir = Path(".atc")
        atc_dir.mkdir(parents=True, exist_ok=True)
        config_file = atc_dir / CONFIG_FILE_NAME
        if config_file.exists():
            warn(f"already exists: {config_file.resolve()}")
            return 0
        config_file.write_text(_config_to_toml(_default_config()), encoding="utf-8")
        print(f"created: {config_file.resolve()}")
    elif subcmd == "doctor":
        cmd_config_doctor()
    else:
        return USAGE_ERROR
    return 0


def handle_run(args: List[str]):
    if len(args) < 1:
        return USAGE_ERROR
    interp = args[1] if len(args) == 2 else None
    if args[0].lower() == "all":
        cmd_run_all(interp)
    else:
        cmd_run(args[0], interp)
    return 0


def handle_rerun(args: List[str]):
    interp = args[0] if len(args) == 1 else None
    cmd_rerun(interp)
    return 0


def handle_watch(args: List[str]):
    cmd_watch(args)
    return 0


def handle_visual(args: List[str]):
    try:
        port, open_browser = parse_visual_args(args)
    except ValueError as e:
        error(f"Error: {e}")
        print("Usage: atc visual [--port 8765] [--no-open]")
        return 1
    return cmd_visual(port=port, open_browser=open_browser)


def handle_manual(args: List[str]):
    if len(args) >= 1 and args[0] == "tests":
        cmd_manual_tests()
    else:
        cmd_manual(args)
    return 0


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
        aliases=("contests",),
        usage=("atc contest abc413 [py|cpp]",),
        description="Create or select a contest directory.",
        handler=handle_contest,
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
        name="rerun",
        aliases=("retry",),
        usage=("atc rerun [python|pypy|cpp]",),
        description="Run the failed cases from the previous test run.",
        handler=handle_rerun,
    ),
    CommandSpec(
        name="watch",
        aliases=("w", "auto"),
        usage=("atc watch [A] [python|pypy|cpp]",),
        description="Watch files and rerun tests automatically.",
        handler=handle_watch,
    ),
    CommandSpec(
        name="visual",
        aliases=("vis", "vizui"),
        usage=("atc visual [--port 8765] [--no-open]",),
        description="Start the local visualizer server.",
        handler=handle_visual,
    ),
    CommandSpec(
        name="manual",
        aliases=(),
        usage=("atc manual A B C", "atc manual tests  (現在のフォルダ名を contest_id としてサンプル取得)"),
        description="Create problem files or download samples for the current folder.",
        handler=handle_manual,
    ),
)


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


def usage_lines() -> List[str]:
    lines: List[str] = []
    for spec in COMMANDS:
        lines.extend(spec.usage)
    return lines
