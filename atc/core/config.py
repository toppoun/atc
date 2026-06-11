import copy
import json
import shutil
from pathlib import Path
from typing import Optional
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


# --- Constants ---
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
DEFAULT_CONTEST_PATH_RULES = {
    "abc\\d+": "ABC",
    "arc\\d+": "ARC",
    "agc\\d+": "AGC",
    "adt_.*": "ATD",
}

class ConfigError(RuntimeError):
    pass


# --- default config ---
def default_config() -> dict:
    return {
        "paths": {
            "root": "",
            "contests": copy.deepcopy(DEFAULT_CONTEST_PATH_RULES),
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


# --- default config template ---
def default_config_template() -> dict:
    config = default_config()
    config["paths"]["root"] = "."
    return config


def find_config_file(start: Path) -> Optional[Path]:
    current = start.resolve()
    for path in [current, *current.parents]:
        config_file = path / ".atc" / CONFIG_FILE_NAME
        if config_file.exists():
            return config_file

    home_config = Path.home() / ".atc" / CONFIG_FILE_NAME
    if home_config.exists():
        return home_config

    return None


def deep_merge_config(defaults: dict, overrides: dict) -> dict:
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_config(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(start: Optional[Path] = None) -> dict:
    if start is None:
        start = Path.cwd()
    config = default_config()
    config_file = find_config_file(start)
    if not config_file:
        return config

    try:
        with config_file.open("rb") as f:
            loaded = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Error: failed to parse config file: {config_file.resolve()}: {e}") from e
    except OSError as e:
        raise ConfigError(f"Error: failed to read config file: {config_file.resolve()}: {e}") from e

    if isinstance(loaded.get("paths"), dict) and "contests" in loaded["paths"]:
        config["paths"]["contests"] = {}

    merged = deep_merge_config(config, loaded)
    merged[CONFIG_FILE_META_KEY] = str(config_file.resolve())
    return merged


def config_file_path(config: dict) -> Optional[Path]:
    config_file = config.get(CONFIG_FILE_META_KEY)
    return Path(config_file) if config_file else None


def config_project_root(config_file: Path):
    if config_file.parent.name == ".atc":
        return config_file.parent.parent
    return config_file.parent


def config_root(config: dict) -> Optional[Path]:
    root = str(config.get("paths", {}).get("root") or "").strip()
    if not root:
        return None

    root_path = Path(root).expanduser()
    if root_path.is_absolute():
        return root_path

    config_file = config_file_path(config)
    if config_file:
        return (config_project_root(config_file) / root_path).resolve()

    return (Path.cwd() / root_path).resolve()


def find_project_root(start: Path, config: Optional[dict] = None):
    """Find a project root without requiring a specific AtCoder folder layout."""
    config = config or load_config(start)
    config_root_path = config_root(config)
    if config_root_path:
        return config_root_path

    marker_candidate = None
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

    if marker_candidate:
        return marker_candidate
    return start


def config_problems(config: Optional[dict] = None):
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


def default_language(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    lang = str(config.get("defaults", {}).get("language") or "cpp").strip().lower()
    return lang if lang in SOURCE_EXTS else "cpp"


def resolve_executable(command: str):
    path = Path(command).expanduser()
    if path.exists():
        return str(path)
    return shutil.which(command)


def normalize_run_language(language: Optional[str], config: dict):
    requested = str(language or default_language(config)).strip().lower()
    if requested == "py":
        return "python"
    if requested in ["python", "pypy", "cpp"]:
        return requested
    return None


def runner_settings(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    runner = config.get("runner", {})
    return runner if isinstance(runner, dict) else {}


def runner_command(config: dict, key: str, default: str):
    command = str(runner_settings(config).get(key) or default).strip()
    return command or default


def runner_cpp_flags(config: dict):
    flags = runner_settings(config).get("cpp_flags", ["-std=c++20", "-O2", "-Wall", "-Wextra"])
    if isinstance(flags, list):
        return [str(flag) for flag in flags]
    if isinstance(flags, str):
        return flags.split()
    return ["-std=c++20", "-O2", "-Wall", "-Wextra"]


def runner_timeout(config: dict):
    raw_timeout = runner_settings(config).get("timeout_seconds", 2.0)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        return 2.0
    return timeout if timeout > 0 else None


def runner_compile_timeout(config: dict):
    raw_timeout = runner_settings(config).get("compile_timeout_seconds", 10.0)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        return 10.0
    return timeout if timeout > 0 else None


def watch_settings(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    raw_watch = config.get("watch", {})
    defaults = default_config()["watch"]
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


def _toml_key(key):
    key = str(key)
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
    if key and all(char in allowed for char in key):
        return key
    return json.dumps(key, ensure_ascii=False)


def config_to_toml(config: dict) -> str:
    lines = []
    for section, values in config.items():
        if section in INTERNAL_CONFIG_KEYS:
            continue
        if isinstance(values, dict):
            scalar_values = [(key, value) for key, value in values.items() if not isinstance(value, dict)]
            nested_values = [(key, value) for key, value in values.items() if isinstance(value, dict)]

            if scalar_values or not nested_values:
                if lines:
                    lines.append("")
                lines.append(f"[{section}]")
                for key, value in scalar_values:
                    lines.append(f"{_toml_key(key)} = {_toml_value(value)}")

            for nested_key, nested in nested_values:
                if not nested:
                    continue
                if lines:
                    lines.append("")
                lines.append(f"[{section}.{nested_key}]")
                for key, value in nested.items():
                    lines.append(f"{_toml_key(key)} = {_toml_value(value)}")
        else:
            if lines:
                lines.append("")
            lines.append(f"[{section}]")
            lines.append(f"value = {_toml_value(values)}")
    return "\n".join(lines) + "\n"
