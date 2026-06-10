from typing import List
from pathlib import Path

from atc.argparse_utils import AtcArgumentParser
from atc.commands.usage_error import USAGE_ERROR
from atc.commands.parsing import parse_handler_args
from atc.core.config import find_config_file, load_config, config_to_toml, CONFIG_FILE_NAME, default_config_template
from atc.core.doctor import cmd_config_doctor
from atc.ui.console import warn


# --- Config handlers ---
def handle_config(args: List[str]):
    parser = AtcArgumentParser(prog="atc config")
    subparsers = parser.add_subparsers(
        dest="subcommand",
        required=True,
        parser_class=AtcArgumentParser,
    )

    subparsers.add_parser("show", prog="atc config show")
    subparsers.add_parser("init", prog="atc config init")
    subparsers.add_parser("doctor", prog="atc config doctor")

    parsed = parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    
    if parsed.subcommand == "show":
        return _show_config()
    if parsed.subcommand == "init":
        return _init_config()
    if parsed.subcommand == "doctor":
        return _doctor_config()
    
    return USAGE_ERROR


def _show_config():
    config_file = find_config_file(Path.cwd())
    config = load_config(Path.cwd())
    print(f"config file: {config_file.resolve() if config_file else '(default)'}")
    print()
    print(config_to_toml(config), end="")
    return 0


def _init_config():
    atc_dir = Path(".atc")
    atc_dir.mkdir(parents=True, exist_ok=True)
    config_file = atc_dir / CONFIG_FILE_NAME
    if config_file.exists():
        warn(f"already exists: {config_file.resolve()}")
        return 0
    config_file.write_text(config_to_toml(default_config_template()), encoding="utf-8")
    print(f"created: {config_file.resolve()}")
    return 0

def _doctor_config():
    cmd_config_doctor()
    return 0