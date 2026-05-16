import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

try:
    from .console import RED, RESET
except ImportError:
    from console import RED, RESET


PROBLEMS = ["A", "B", "C", "D", "E"]
SOURCE_EXTS = ["py", "cpp"]

WATCH_DEBOUNCE_SECONDS = 1.5
WATCH_POLL_SECONDS = 0.25
WATCH_POLL_SECONDS_MIN = 0.1
WATCH_POLL_SECONDS_MAX = 5.0
WATCH_DEBOUNCE_SECONDS_MIN = 0.0
WATCH_DEBOUNCE_SECONDS_MAX = 10.0

CONFIG_FILE_NAME = "config.toml"
CONFIG_FILE_META_KEY = "__config_file__"
INTERNAL_CONFIG_KEYS = {CONFIG_FILE_META_KEY}
LEGACY_ATCODER_CATEGORY_DIRS = {
    "ABC(Atcoder Beginner Contest)",
    "ARC(Atcoder Regular Contest)",
    "AGC(Atcoder Grand Contest)",
    "ABS(Atcoder Beginner Selection)",
    "ALPC(AtCoder Library Practice Contest)",
    "EDPC",
    "typical90",
    "tessoku-book",
}


def _default_config() -> dict:
    return {
        "paths": {
            "root": "",
            "abc": "ABC(Atcoder Beginner Contest)",
            "arc": "ARC(Atcoder Regular Contest)",
            "agc": "AGC(Atcoder Grand Contest)",
            "abs": "ABS(Atcoder Beginner Selection)",
            "alpc": "ALPC(AtCoder Library Practice Contest)",
            "edpc": "EDPC",
            "tessoku": "tessoku-book",
            "typical90": "typical90",
        },
        "templates": {
            "py": "templates/template.py",
            "cpp": "templates/template.cpp",
        },
        "defaults": {
            "language": "cpp",
            "problems": PROBLEMS[:],
        },
        "runner": {
            "python": "python",
            "pypy": "pypy",
            "cpp_compiler": "g++",
            "cpp_flags": ["-std=c++20", "-O2", "-Wall", "-Wextra"],
            "timeout_seconds": 2.0,
            "compile_timeout_seconds": 10.0,
        },
        "watch": {
            "poll_seconds": WATCH_POLL_SECONDS,
            "debounce_seconds": WATCH_DEBOUNCE_SECONDS,
        },
    }


def _find_config_file(start: Path) -> Optional[Path]:
    current = start.resolve()
    for path in [current, *current.parents]:
        config_file = path / ".atc" / CONFIG_FILE_NAME
        if config_file.exists():
            return config_file

    home_config = Path.home() / ".atc" / CONFIG_FILE_NAME
    if home_config.exists():
        return home_config

    return None


def _deep_merge_config(defaults: dict, overrides: dict) -> dict:
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_config(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(start: Path = Path.cwd()) -> dict:
    config = _default_config()
    config_file = _find_config_file(start)
    if not config_file:
        return config

    try:
        with config_file.open("rb") as f:
            loaded = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        print(f"{RED}Error: failed to parse config file: {config_file.resolve()}{RESET}")
        print(f"  {e}")
        sys.exit(1)
    except OSError as e:
        print(f"{RED}Error: failed to read config file: {config_file.resolve()}{RESET}")
        print(f"  {e}")
        sys.exit(1)

    merged = _deep_merge_config(config, loaded)
    merged[CONFIG_FILE_META_KEY] = str(config_file.resolve())
    return merged


def _config_file_path(config: dict) -> Optional[Path]:
    config_file = config.get(CONFIG_FILE_META_KEY)
    return Path(config_file) if config_file else None


def _config_project_root(config_file: Path):
    if config_file.parent.name == ".atc":
        return config_file.parent.parent
    return config_file.parent


def _config_root(config: dict) -> Optional[Path]:
    root = str(config.get("paths", {}).get("root") or "").strip()
    if not root:
        return None

    root_path = Path(root).expanduser()
    if root_path.is_absolute():
        return root_path

    config_file = _config_file_path(config)
    if config_file:
        return (_config_project_root(config_file) / root_path).resolve()

    return (Path.cwd() / root_path).resolve()


def _find_project_root(start: Path, config: Optional[dict] = None):
    """Find a project root without requiring a specific AtCoder folder layout."""
    config = config or load_config(start)
    config_root = _config_root(config)
    if config_root:
        return config_root

    marker_candidate = None
    category_parent_candidate = None

    start = start.resolve()
    home = Path.home().resolve()
    for path in [start, *start.parents]:
        if (path / ".git").exists():
            return path

        if marker_candidate is None and (
            (path / "pyproject.toml").exists()
            or ((path / ".vscode").exists() and path != home)
        ):
            marker_candidate = path

        if path.name in LEGACY_ATCODER_CATEGORY_DIRS and category_parent_candidate is None:
            category_parent_candidate = path.parent

    if marker_candidate:
        return marker_candidate
    if category_parent_candidate:
        return category_parent_candidate
    return start


def _config_problems(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    raw_problems = config.get("defaults", {}).get("problems", PROBLEMS)
    if not isinstance(raw_problems, list):
        return PROBLEMS[:]

    problems = []
    for raw_problem in raw_problems:
        problem = str(raw_problem).strip().upper()
        if problem and problem not in problems:
            problems.append(problem)
    return problems or PROBLEMS[:]


def _default_language(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    lang = str(config.get("defaults", {}).get("language") or "cpp").strip().lower()
    return lang if lang in SOURCE_EXTS else "cpp"


def _resolve_command(command: str):
    path = Path(command).expanduser()
    if path.exists():
        return str(path)
    return shutil.which(command)


def _normalize_run_language(language: Optional[str], config: dict):
    requested = str(language or _default_language(config)).strip().lower()
    if requested == "py":
        return "python"
    if requested in ["python", "pypy", "cpp"]:
        return requested
    return None


def _runner_settings(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    runner = config.get("runner", {})
    return runner if isinstance(runner, dict) else {}


def _runner_command(config: dict, key: str, default: str):
    command = str(_runner_settings(config).get(key) or default).strip()
    return command or default


def _runner_cpp_flags(config: dict):
    flags = _runner_settings(config).get("cpp_flags", ["-std=c++20", "-O2", "-Wall", "-Wextra"])
    if isinstance(flags, list):
        return [str(flag) for flag in flags]
    if isinstance(flags, str):
        return flags.split()
    return ["-std=c++20", "-O2", "-Wall", "-Wextra"]


def _runner_timeout(config: dict):
    raw_timeout = _runner_settings(config).get("timeout_seconds", 2.0)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        return 2.0
    return timeout if timeout > 0 else None


def _runner_compile_timeout(config: dict):
    raw_timeout = _runner_settings(config).get("compile_timeout_seconds", 10.0)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        return 10.0
    return timeout if timeout > 0 else None


def _watch_settings(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    raw_watch = config.get("watch", {})
    defaults = _default_config()["watch"]
    warnings = []

    if not isinstance(raw_watch, dict):
        return defaults["poll_seconds"], defaults["debounce_seconds"], ["[watch] must be a table. Using default watch settings."]

    def read_seconds(key: str, default: float, min_value: float, max_value: float):
        if key not in raw_watch:
            return default

        raw_value = raw_watch.get(key)
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            warnings.append(f"watch.{key} must be a number. Using default: {default}")
            return default

        value = float(raw_value)
        if not (min_value <= value <= max_value):
            warnings.append(f"watch.{key} must be between {min_value} and {max_value}. Using default: {default}")
            return default

        return value

    poll_seconds = read_seconds(
        "poll_seconds",
        defaults["poll_seconds"],
        WATCH_POLL_SECONDS_MIN,
        WATCH_POLL_SECONDS_MAX,
    )
    debounce_seconds = read_seconds(
        "debounce_seconds",
        defaults["debounce_seconds"],
        WATCH_DEBOUNCE_SECONDS_MIN,
        WATCH_DEBOUNCE_SECONDS_MAX,
    )
    return poll_seconds, debounce_seconds, warnings


def _toml_value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def _config_to_toml(config: dict) -> str:
    lines = []
    for section, values in config.items():
        if section in INTERNAL_CONFIG_KEYS:
            continue
        if lines:
            lines.append("")
        lines.append(f"[{section}]")
        if isinstance(values, dict):
            for key, value in values.items():
                lines.append(f"{key} = {_toml_value(value)}")
        else:
            lines.append(f"value = {_toml_value(values)}")
    return "\n".join(lines) + "\n"


config_file_path = _config_file_path

# Public aliases used by feature modules.
config_root = _config_root
config_project_root = _config_project_root
find_project_root = _find_project_root
config_problems = _config_problems
default_language = _default_language
resolve_executable = _resolve_command
resolve_command = _resolve_command
normalize_run_language = _normalize_run_language
runner_settings = _runner_settings
runner_command = _runner_command
runner_cpp_flags = _runner_cpp_flags
runner_timeout = _runner_timeout
runner_compile_timeout = _runner_compile_timeout
watch_settings = _watch_settings
config_to_toml = _config_to_toml
toml_value = _toml_value
