import sys
import json
import subprocess
import shutil
import time
import platform
import copy
import re
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

# ===== 設定 =====
PROBLEMS = ["A", "B", "C", "D", "E"]
TEMPLATE_DIR = Path(__file__).parent / "templates"
LOG_DIR = Path(".atc") / "test-runs"
WATCH_DEBOUNCE_SECONDS = 1.5
WATCH_POLL_SECONDS = 0.25
SOURCE_EXTS = ["py", "cpp"]
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
CONFIG_FILE_NAME = "config.toml"
CONFIG_FILE_META_KEY = "__config_file__"
INTERNAL_CONFIG_KEYS = {CONFIG_FILE_META_KEY}

# =================
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

# ---------- 共通・補助関数 ----------

@dataclass
class CaseResult:
    name: str
    status: str
    elapsed_ms: float
    expected: Optional[str] = None
    output: str = ""
    stderr: str = ""


@dataclass
class ProblemResult:
    problem: str
    mode: Optional[str] = None
    cases: List[CaseResult] = field(default_factory=list)
    error_status: Optional[str] = None
    error_message: str = ""
    duration_ms: float = 0.0

    @property
    def ok_count(self):
        return sum(1 for case in self.cases if case.status == "AC")

    @property
    def total_count(self):
        return len(self.cases)

    @property
    def failed_cases(self):
        return [case for case in self.cases if case.status != "AC"]

    @property
    def passed(self):
        return not self.error_status and self.total_count > 0 and not self.failed_cases

def detect_pypy():
    for name in ["pypy3", "pypy"]:
        path = shutil.which(name)
        if path:
            return path
    return None

def load_template(ext: str, config: Optional[dict] = None, start: Optional[Path] = None):
    """Read a template file. If config exists, resolve [templates] from it."""
    template_file = _resolve_template_file(ext, config, start)
    if template_file.exists():
        return template_file.read_text(encoding="utf-8")
    else:
        print(f"{YELLOW}Warning: {template_file} が見つかりません。空ファイルを作成します。{RESET}")
        return ""

def _download_samples(contest: str, problem_char: str, dst_dir: Path):
    tmp = dst_dir.parent / f".oj_tmp_{problem_char}"
    url = f"https://atcoder.jp/contests/{contest}/tasks/{contest}_{problem_char.lower()}"
    shutil.rmtree(tmp, ignore_errors=True)

    oj = shutil.which("oj")
    if not oj:
        return False, "oj command not found. Install online-judge-tools: python -m pip install online-judge-tools"

    try:
        subprocess.run(
            [oj, "d", url, "-d", str(tmp)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if not tmp.exists():
            return False, "oj finished but did not create a download directory"
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in tmp.iterdir(): shutil.move(str(f), dst_dir / f.name)
        shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        reason = (e.stderr or e.stdout or "").strip()
        if not reason:
            reason = f"oj exited with status {e.returncode}"
        return False, reason
    except OSError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return False, str(e)

# ---------- usage ----------

def usage():
    print("使い方:")
    print("  atc new abc413 [py|cpp]  (デフォルトは config の defaults.language、未設定なら cpp)")
    print("  atc contest abc413 [py|cpp]")
    print("  atc config show")
    print("  atc config init")
    print("  atc config doctor")
    print("  atc run A [python|pypy|cpp]")
    print("  atc run all [python|pypy|cpp]")
    print("  atc rerun [python|pypy|cpp]")
    print("  atc watch [A] [python|pypy|cpp]")
    print("  atc manual A B C")
    print("  atc manual tests  (現在のフォルダ名を contest_id としてサンプル取得)")
    sys.exit(1)

# ---------- new ----------
def cmd_new(contest: str, lang: Optional[str] = None):
    config = load_config(Path.cwd())
    lang = lang or _default_language(config)
    _create_contest_files(contest, Path(contest), lang, config)

def _create_contest_files(contest_id: str, base: Path, lang: str, config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    problems = _config_problems(config)
    tests = base / "tests"
    base.mkdir(parents=True, exist_ok=True)
    
    template_content = load_template(lang, config, Path.cwd())
    
    failed_downloads = []
    for p in problems:
        # ファイル作成 (A.py または A.cpp)
        source_file = base / f"{p}.{lang}"
        if not source_file.exists():
            source_file.write_text(template_content, encoding="utf-8")

        # サンプル取得
        print(f"fetching {p} ...", end=" ", flush=True)
        ok, reason = _download_samples(contest_id, p, tests / p)
        if ok:
            print(f"{GREEN}done{RESET}")
        else:
            print(f"{RED}failed{RESET}")
            if reason:
                print(f"  reason: {reason}")
            failed_downloads.append((p, reason))

    _print_sample_download_summary(problems, failed_downloads)

    if failed_downloads:
        print(f"\n{contest_id} ({lang}) files ready, but sample download incomplete.")
    else:
        print(f"\n{contest_id} ({lang}) ready.")

def _print_sample_download_summary(problems: List[str], failed_downloads: List[tuple]):
    if not failed_downloads:
        return

    total = len(problems)
    failed = len(failed_downloads)
    succeeded = total - failed
    failed_problems = ", ".join(problem for problem, _ in failed_downloads)

    print()
    print(f"{YELLOW}Sample download summary: {succeeded}/{total} succeeded, {failed} failed.{RESET}")
    if succeeded == 0:
        print(f"{YELLOW}Files were created, but sample download failed for all problems.{RESET}")
    else:
        print(f"{YELLOW}Files were created, but sample download failed for: {failed_problems}{RESET}")
    print("Check oj installation, AtCoder login, contest ID, and network connection.")
    print("Try: oj login https://atcoder.jp/")

# ---------- contest ----------
def cmd_contest(contest: str, lang: Optional[str] = None):
    config = load_config(Path.cwd())
    lang = lang or _default_language(config)
    contest_dir = _resolve_contest_dir(contest, config)

    if contest_dir.exists():
        if not contest_dir.is_dir():
            print(f"{RED}Error: {contest_dir} exists but is not a directory.{RESET}")
            sys.exit(1)
        print(f"{YELLOW}{contest_dir} already exists. Skip creation and sample download.{RESET}")
    else:
        _create_contest_files(contest, contest_dir, lang, config)

    current_contest_file = _write_current_contest(contest_dir.resolve(), config)
    print(f"current contest saved: {current_contest_file}")

def _contest_category_key(contest: str) -> Optional[str]:
    match = re.fullmatch(r"(abc|arc|agc)\d+", contest.lower())
    return match.group(1) if match else None

def _resolve_contest_dir(contest: str, config: dict):
    contest_path = Path(contest)
    if contest_path.is_absolute():
        return contest_path

    paths = config.get("paths", {})
    root_path = _config_root(config)
    category_key = _contest_category_key(contest)
    category_dir = str(paths.get(category_key) or "").strip() if category_key else ""

    if root_path:
        if category_dir:
            return root_path / category_dir / contest
        return root_path / contest

    return contest_path

def _config_file_path(config: dict) -> Optional[Path]:
    config_file = config.get(CONFIG_FILE_META_KEY)
    return Path(config_file) if config_file else None

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

def _write_current_contest(contest_dir: Path, config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    project_root = _find_project_root(Path.cwd(), config)
    atc_dir = project_root / ".atc"
    atc_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().isoformat(timespec="milliseconds")
    current_contest_file = atc_dir / "current-contest.json"
    current_contest_file.write_text(
        json.dumps(
            {
                "contestDir": str(contest_dir.resolve()),
                "requestId": now,
                "createdAt": now,
            },
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )
    return current_contest_file.resolve()

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

# ---------- config ----------
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
            "problems": ["A", "B", "C", "D", "E"],
        },
        "runner": {
            "python": "python",
            "pypy": "pypy",
            "cpp_compiler": "g++",
            "cpp_flags": ["-std=c++20", "-O2", "-Wall", "-Wextra"],
            "timeout_seconds": 2.0,
            "compile_timeout_seconds": 10.0,
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

def _default_language(config: Optional[dict] = None):
    config = config or load_config(Path.cwd())
    lang = str(config.get("defaults", {}).get("language") or "cpp").strip().lower()
    return lang if lang in SOURCE_EXTS else "cpp"

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

def _config_project_root(config_file: Path):
    if config_file.parent.name == ".atc":
        return config_file.parent.parent
    return config_file.parent

def _resolve_template_file(ext: str, config: Optional[dict] = None, start: Optional[Path] = None):
    start = start or Path.cwd()
    config_file = _find_config_file(start)
    if not config_file:
        return TEMPLATE_DIR / f"template.{ext}"

    config = config or load_config(start)
    template_value = str(config.get("templates", {}).get(ext) or f"templates/template.{ext}").strip()
    template_path = Path(template_value).expanduser()
    if template_path.is_absolute():
        return template_path

    candidates = [
        config_file.parent / template_path,
        _config_project_root(config_file) / template_path,
    ]

    config_root = _config_root(config)
    if config_root:
        candidates.append(config_root / template_path)

    candidates.append(_find_project_root(start, config) / template_path)

    if template_value == f"templates/template.{ext}":
        candidates.append(TEMPLATE_DIR / f"template.{ext}")

    unique_candidates = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            unique_candidates.append(candidate)
            seen.add(resolved)

    for candidate in unique_candidates:
        if candidate.exists():
            return candidate

    return unique_candidates[-1]

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

class DoctorReport:
    def __init__(self):
        self.counts = {"OK": 0, "WARN": 0, "ERROR": 0, "INFO": 0}

    def section(self, title: str):
        print()
        print(title)

    def item(self, status: str, message: str, details: Optional[List[str]] = None):
        self.counts[status] = self.counts.get(status, 0) + 1
        print(f"  [{status}] {message}")
        for detail in details or []:
            print(f"       {detail}")

    def summary(self):
        print()
        print("Summary")
        print(f"  OK: {self.counts.get('OK', 0)}")
        print(f"  WARN: {self.counts.get('WARN', 0)}")
        print(f"  ERROR: {self.counts.get('ERROR', 0)}")
        print(f"  INFO: {self.counts.get('INFO', 0)}")

    @property
    def has_error(self):
        return self.counts.get("ERROR", 0) > 0

def _load_config_for_doctor(start: Path):
    config = _default_config()
    config_file = _find_config_file(start)
    if not config_file:
        return config, None, None

    try:
        with config_file.open("rb") as f:
            loaded = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        return config, config_file, f"failed to parse config file: {e}"
    except OSError as e:
        return config, config_file, f"failed to read config file: {e}"

    merged = _deep_merge_config(config, loaded)
    merged[CONFIG_FILE_META_KEY] = str(config_file.resolve())
    return merged, config_file, None

def _run_doctor_command(args: List[str], timeout: float = 5.0):
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "", str(e)

def _first_line(text: str):
    return text.splitlines()[0] if text else ""

def _display_path(path: Optional[Path]):
    return str(path.resolve()) if path else "(none)"

def _doctor_check_python(report: DoctorReport):
    report.section("Environment")
    report.item("OK", f"Python: {sys.executable} ({platform.python_version()})")

    atc = shutil.which("atc")
    if atc:
        report.item("OK", f"atc command: {atc}")
    else:
        report.item(
            "WARN",
            "atc command was not found in PATH.",
            ["Try reopening your terminal, or check your pip scripts path."],
        )

def _doctor_check_config(report: DoctorReport, config: dict, config_file: Optional[Path], config_error: Optional[str]):
    report.section("Config")
    if config_error:
        report.item("ERROR", f"Config file: {_display_path(config_file)}", [config_error])
    elif config_file:
        report.item("OK", f"Config file: {config_file.resolve()}")
    else:
        report.item("INFO", "Config file: (default config)")

    paths = config.get("paths", {})
    root_value = str(paths.get("root") or "").strip()
    root = _config_root(config)
    if root_value:
        if root and root.exists():
            report.item("OK", f"Resolved root: {root}")
        elif root:
            report.item("WARN", f"Resolved root does not exist: {root}")
    else:
        report.item("INFO", "paths.root is empty. atc contest will use the current directory.")

    for key, label in [("abc", "ABC"), ("arc", "ARC"), ("agc", "AGC")]:
        value = str(paths.get(key) or "")
        if value:
            report.item("OK", f"paths.{key}: {value}")
        else:
            report.item("INFO", f"paths.{key} is empty. {label} contests will be created directly under root.")

def _doctor_check_templates(report: DoctorReport, config: dict, cwd: Path):
    report.section("Templates")
    for ext, label in [("py", "Python"), ("cpp", "C++")]:
        template = _resolve_template_file(ext, config, cwd)
        if template.exists():
            report.item("OK", f"{label} template: {template.resolve()}")
        else:
            report.item(
                "WARN",
                f"{label} template not found: {template}",
                [f"Empty files will be created for {label}."],
            )

def _doctor_check_runner(report: DoctorReport, config: dict):
    report.section("Runner")
    python_cmd = _runner_command(config, "python", "python")
    python_runner = _resolve_command(python_cmd)
    if python_runner:
        report.item("OK", f"Python runner: {python_runner}")
    else:
        report.item("OK", f"Python runner: {sys.executable}", [f"Configured runner.python was not found: {python_cmd}", "Using current Python as fallback."])

    pypy_cmd = _runner_command(config, "pypy", "pypy")
    pypy_runner = _resolve_command(pypy_cmd)
    if not pypy_runner and pypy_cmd == "pypy":
        pypy_runner = shutil.which("pypy3")
    if pypy_runner:
        report.item("OK", f"PyPy: {pypy_runner}")
    else:
        report.item("WARN", "PyPy: not found. Python mode still works.")

    compiler_cmd = _runner_command(config, "cpp_compiler", "g++")
    compiler = _resolve_command(compiler_cmd)
    if compiler:
        report.item("OK", f"C++ compiler: {compiler}")
    else:
        fallback_compiler = shutil.which("clang++") or shutil.which("g++")
        if fallback_compiler:
            report.item(
                "WARN",
                f"Configured C++ compiler not found: {compiler_cmd}",
                [f"Available compiler: {fallback_compiler}", "Update runner.cpp_compiler in config.toml if you use C++."],
            )
        else:
            report.item(
                "WARN",
                "C++ compiler not found.",
                ["If you use C++, install Xcode Command Line Tools:", "xcode-select --install"],
            )

    report.item("OK", f"C++ flags: {' '.join(_runner_cpp_flags(config))}")
    run_timeout = _runner_timeout(config)
    compile_timeout = _runner_compile_timeout(config)
    report.item("OK", f"Run timeout: {run_timeout}s" if run_timeout else "Run timeout: disabled")
    report.item("OK", f"Compile timeout: {compile_timeout}s" if compile_timeout else "Compile timeout: disabled")

def _doctor_check_tools(report: DoctorReport):
    report.section("Tools")
    oj = shutil.which("oj")
    if oj:
        code, stdout, stderr = _run_doctor_command([oj, "--version"])
        version = _first_line(stdout or stderr)
        if code == 0:
            report.item("OK", f"oj: {oj}" + (f" ({version})" if version else ""))
        else:
            report.item("WARN", f"oj command exists but failed: {oj}", [stderr or stdout or "oj --version failed"])
    else:
        report.item(
            "WARN",
            "oj was not found.",
            ["Sample download will not work.", "Install: python3 -m pip install online-judge-tools", "Login: oj login https://atcoder.jp/"],
        )

def _vscode_extension_id():
    package_json = Path(__file__).resolve().parent.parent / "vscode" / "atc-helper" / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            publisher = data.get("publisher") or "kouki"
            name = data.get("name") or "atc-helper"
            return f"{publisher}.{name}"
        except (OSError, json.JSONDecodeError):
            pass
    return "kouki.atc-helper"

def _resolve_vscode_cli():
    candidates: List[Path] = []

    for command in ["code", "code.cmd"]:
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd")

    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(Path(program_files) / "Microsoft VS Code" / "bin" / "code.cmd")

    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if program_files_x86:
        candidates.append(Path(program_files_x86) / "Microsoft VS Code" / "bin" / "code.cmd")

    seen: Set[str] = set()
    for candidate in candidates:
        try:
            resolved = str(candidate.expanduser())
            key = resolved.lower()
            if key in seen:
                continue
            seen.add(key)
            if candidate.exists():
                return resolved
        except OSError:
            continue
    return None

def _normalize_vscode_extension_id(raw: str):
    extension_id = raw.strip()
    if not extension_id:
        return ""
    if "@" in extension_id:
        extension_id = extension_id.split("@", 1)[0]
    return extension_id.strip().lower()

def _related_vscode_extensions(lines: List[str]):
    related: List[str] = []
    seen: Set[str] = set()
    for line in lines:
        extension_id = _normalize_vscode_extension_id(line)
        if not extension_id:
            continue
        if "atc" not in extension_id:
            continue
        if extension_id in seen:
            continue
        seen.add(extension_id)
        related.append(extension_id)
    return related

def _doctor_check_vscode(report: DoctorReport):
    report.section("VS Code")
    code_cmd = _resolve_vscode_cli()
    extension_id = _vscode_extension_id()
    if not code_cmd:
        report.item(
            "WARN",
            "VS Code CLI was not found.",
            [
                "Could not verify whether the VS Code extension is installed.",
                "If VS Code is installed, add the `code` command to PATH.",
                "In VS Code, run: Shell Command: Install 'code' command in PATH",
            ],
        )
        return

    code, stdout, stderr = _run_doctor_command([code_cmd, "--version"])
    version = _first_line(stdout or stderr)
    if code == 0:
        report.item("OK", f"VS Code CLI: {code_cmd}" + (f" ({version})" if version else ""))
    else:
        report.item("WARN", f"VS Code CLI exists but failed: {code_cmd}", [stderr or stdout or "code --version failed"])

    code, stdout, stderr = _run_doctor_command([code_cmd, "--list-extensions"])
    if code != 0:
        report.item(
            "WARN",
            "Could not verify whether the VS Code extension is installed.",
            [stderr or stdout or "code --list-extensions failed"],
        )
        return

    lines = stdout.splitlines()
    installed = {_normalize_vscode_extension_id(line) for line in lines}
    expected = extension_id.lower()
    if expected in installed:
        report.item("OK", f"VS Code extension: {extension_id}")
    else:
        details = [f"Expected: {extension_id}"]
        related = _related_vscode_extensions(lines)
        if related:
            details.append("Found related extensions:")
            details.extend([f"  - {item}" for item in related])
        details.append("Run ./install.sh or ./update.sh")
        report.item("WARN", "VS Code extension is not installed.", details)

def _doctor_current_contest_root(config: dict, cwd: Path):
    root = _config_root(config)
    return root if root else _find_project_root(cwd, config)

def _doctor_check_current_contest(report: DoctorReport, config: dict, cwd: Path):
    report.section("Current contest")
    root = _doctor_current_contest_root(config, cwd)
    current_file = root / ".atc" / "current-contest.json"
    if not current_file.exists():
        report.item("INFO", "current-contest.json not found yet.", ["Run: atc contest abc335 cpp", f"Expected path: {current_file}"])
        return

    try:
        data = json.loads(current_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.item("WARN", f"current-contest.json is invalid JSON: {current_file}", [str(e)])
        return
    except OSError as e:
        report.item("WARN", f"Failed to read current-contest.json: {current_file}", [str(e)])
        return

    contest_dir_value = data.get("contestDir")
    if not isinstance(contest_dir_value, str) or not contest_dir_value.strip():
        report.item("WARN", f"current-contest.json does not contain contestDir: {current_file}")
        return

    contest_dir = Path(contest_dir_value)
    if contest_dir.exists():
        report.item("OK", f"current-contest.json: {current_file}")
        report.item("OK", f"contestDir: {contest_dir}")
    else:
        report.item("WARN", f"contestDir does not exist: {contest_dir}", [f"Source: {current_file}"])

def cmd_config_doctor():
    cwd = Path.cwd()
    report = DoctorReport()
    config, config_file, config_error = _load_config_for_doctor(cwd)

    print("AtC Doctor")
    _doctor_check_python(report)
    _doctor_check_config(report, config, config_file, config_error)
    _doctor_check_templates(report, config, cwd)
    _doctor_check_runner(report, config)
    _doctor_check_tools(report)
    _doctor_check_vscode(report)
    _doctor_check_current_contest(report, config, cwd)
    report.summary()

    if report.has_error:
        sys.exit(1)

def cmd_config(args):
    if not args:
        usage()

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
            print(f"{YELLOW}already exists: {config_file.resolve()}{RESET}")
            return
        config_file.write_text(_config_to_toml(_default_config()), encoding="utf-8")
        print(f"created: {config_file.resolve()}")
    elif subcmd == "doctor":
        cmd_config_doctor()
    else:
        usage()

# ---------- manual ----------
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
                    print(f" {GREEN}Created{RESET}: {f.name}")
            continue
            
        f = cwd / f"{p}.{lang}"
        if not f.exists():
            f.write_text(template_content, encoding="utf-8")
            print(f" {GREEN}Created{RESET}: {f.name}")

# ---------- manual tests ----------
def cmd_manual_tests():
    cwd = Path.cwd()
    config = load_config(cwd)
    problems = _config_problems(config)
    contest = cwd.name.lower()
    tests = cwd / "tests"

    if not contest:
        print(f"{RED}コンテストIDを現在のフォルダ名から取得できません。{RESET}")
        sys.exit(1)

    print(f"contest: {contest}")
    for p in problems:
        print(f"fetching {p} ...", end=" ", flush=True)
        ok, reason = _download_samples(contest, p, tests / p)
        if ok:
            print(f"{GREEN}done{RESET}")
        else:
            print(f"{RED}failed{RESET}")
            if reason:
                print(f"  reason: {reason}")

def _normalize_problem(problem: str):
    return problem.upper()


def _available_problems(cwd: Path, problems: Optional[List[str]] = None):
    problems = problems or _config_problems(load_config(cwd))
    found = []
    for problem in problems:
        has_source = any((cwd / f"{problem}.{ext}").exists() for ext in SOURCE_EXTS)
        has_tests = (cwd / "tests" / problem).exists()
        if has_source or has_tests:
            found.append(problem)
    return found


def _missing_cpp_compiler_message(compiler: str):
    return (
        f"C++ compiler not found: {compiler}\n"
        "Install g++ and make sure it is on PATH.\n"
        "Windows recommendation: install MSYS2 UCRT64 and add C:\\msys64\\ucrt64\\bin to PATH."
    )

def _prepare_cpp_run_command(cwd: Path, problem: str, cpp_file: Path, config: dict, show_compile=False):
    compiler = _runner_command(config, "cpp_compiler", "g++")
    compiler_path = _resolve_command(compiler)
    if not compiler_path:
        return "cpp", [], None, "ERROR", _missing_cpp_compiler_message(compiler)

    suffix = ".exe" if platform.system() == "Windows" else ".out"
    exe_path = cwd / f"_{problem}{suffix}"
    flags = _runner_cpp_flags(config)

    if show_compile:
        print(f"{YELLOW}Compiling {cpp_file.name}...{RESET}")
    try:
        c_proc = subprocess.run(
            [compiler_path, *flags, str(cpp_file), "-o", str(exe_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_runner_compile_timeout(config),
        )
    except subprocess.TimeoutExpired:
        return "cpp", [], exe_path, "TLE", f"Compile timed out after {_runner_compile_timeout(config)} seconds."
    except OSError as e:
        return "cpp", [], exe_path, "ERROR", str(e)

    if c_proc.returncode != 0:
        return "cpp", [], exe_path, "CE", c_proc.stderr.strip()
    return "cpp", [str(exe_path)], exe_path, None, ""

def _prepare_python_run_command(py_file: Path, run_language: str, config: dict):
    key = "pypy" if run_language == "pypy" else "python"
    default = "pypy" if run_language == "pypy" else "python"
    command = _runner_command(config, key, default)
    executable = _resolve_command(command)
    if run_language == "pypy" and not executable and command == "pypy":
        executable = shutil.which("pypy3")
    if run_language != "pypy" and not executable:
        executable = sys.executable
    if not executable:
        if run_language == "pypy":
            return "py", [], None, "ERROR", f"PyPy command not found: {command}. Install PyPy or update runner.pypy in config.toml."
        return "py", [], None, "ERROR", f"Python command not found: {command}. Update runner.python in config.toml or check PATH."
    return "py", [executable, str(py_file)], None, None, ""

def _prepare_run_command(cwd: Path, problem: str, run_language: Optional[str] = None, show_compile=False, config: Optional[dict] = None):
    config = config or load_config(cwd)
    run_language = _normalize_run_language(run_language, config)
    if not run_language:
        return None, [], None, "ERROR", "Invalid language. Use python, pypy, cpp, or set defaults.language to py/cpp."

    py_file = cwd / f"{problem}.py"
    cpp_file = cwd / f"{problem}.cpp"

    if run_language == "cpp":
        if cpp_file.exists():
            return _prepare_cpp_run_command(cwd, problem, cpp_file, config, show_compile)
        if py_file.exists():
            return _prepare_python_run_command(py_file, "python", config)
        return None, [], None, "ERROR", "ファイルが見つかりません。"

    if py_file.exists():
        return _prepare_python_run_command(py_file, run_language, config)
    if cpp_file.exists():
        return _prepare_cpp_run_command(cwd, problem, cpp_file, config, show_compile)

    return None, [], None, "ERROR", "ファイルが見つかりません。"


def run_problem_tests(problem: str, run_language: Optional[str] = None, show_compile=False, case_names: Optional[Set[str]] = None):
    cwd = Path.cwd()
    config = load_config(cwd)
    problem = _normalize_problem(problem)
    testdir = cwd / "tests" / problem
    started = time.perf_counter()
    result = ProblemResult(problem=problem)

    mode, run_cmd, cleanup_path, error_status, error_message = _prepare_run_command(
        cwd,
        problem,
        run_language,
        show_compile=show_compile,
        config=config,
    )
    result.mode = mode
    if error_status:
        result.error_status = error_status
        result.error_message = error_message
        result.duration_ms = (time.perf_counter() - started) * 1000
        return result

    ins = sorted(testdir.glob("*.in")) if testdir.exists() else []
    if case_names:
        ins = [infile for infile in ins if infile.name in case_names]
    if not ins:
        result.error_status = "NO_TESTS"
        result.error_message = "テストケースがありません。"
        result.duration_ms = (time.perf_counter() - started) * 1000
        return result

    try:
        for infile in ins:
            outfile = infile.with_suffix(".out")
            with open(infile, "r", encoding="utf-8") as fin:
                case_started = time.perf_counter()
                try:
                    proc = subprocess.run(
                        run_cmd,
                        stdin=fin,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=_runner_timeout(config),
                    )
                    elapsed = (time.perf_counter() - case_started) * 1000
                except subprocess.TimeoutExpired as e:
                    elapsed = (time.perf_counter() - case_started) * 1000
                    result.cases.append(
                        CaseResult(
                            name=infile.name,
                            status="TLE",
                            elapsed_ms=elapsed,
                            output=(e.stdout or "").strip() if isinstance(e.stdout, str) else "",
                            stderr=f"Timed out after {_runner_timeout(config)} seconds.",
                        )
                    )
                    continue
                except OSError as e:
                    result.error_status = "ERROR"
                    result.error_message = str(e)
                    result.duration_ms = (time.perf_counter() - started) * 1000
                    return result

            output = proc.stdout.strip()
            stderr = proc.stderr.strip()
            expected = outfile.read_text(encoding="utf-8").strip() if outfile.exists() else None

            if proc.returncode != 0:
                status = "RE"
            elif expected is not None and output == expected:
                status = "AC"
            else:
                status = "WA"

            result.cases.append(
                CaseResult(
                    name=infile.name,
                    status=status,
                    elapsed_ms=elapsed,
                    expected=expected,
                    output=output,
                    stderr=stderr,
                )
            )
    finally:
        if mode == "cpp" and cleanup_path and cleanup_path.exists():
            cleanup_path.unlink()

    result.duration_ms = (time.perf_counter() - started) * 1000
    return result


def _print_detailed_result(result: ProblemResult):
    if result.error_status:
        print(f"{RED}{result.error_status}{RESET}")
        if result.error_message:
            print(result.error_message)
        return

    for case in result.cases:
        print(f"=== {case.name} ===")
        if case.status == "AC":
            print(f" {GREEN}AC{RESET}")
        elif case.status == "RE":
            print(f" {RED}RE{RESET}\n{case.stderr}")
        elif case.status == "TLE":
            print(f" {RED}TLE{RESET}")
            if case.stderr:
                print(case.stderr)
            if case.output:
                print(f" output:\n{case.output}")
        else:
            print(f" {RED}WA{RESET}\n expected:\n{case.expected}\n output:\n{case.output}")
        print(f" time: {case.elapsed_ms:.2f} ms")

    print(f"\n結果: {result.ok_count}/{result.total_count} AC")


def _format_seconds(ms: float):
    return f"{ms / 1000:.2f}s"


def _write_test_log(results: List[ProblemResult]):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "last.log"
    failed_path = LOG_DIR / "last_failed.txt"
    failed_lines = []
    lines = [
        f"atc test run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for result in results:
        lines.append(f"[{result.problem}]")
        if result.error_status:
            lines.append(f"{result.error_status}: {result.error_message}")
            failed_lines.append(f"{result.problem} *")
            lines.append("")
            continue

        for case in result.cases:
            lines.append(f"=== {case.name} ===")
            lines.append(f"status: {case.status}")
            lines.append(f"time: {case.elapsed_ms:.2f} ms")
            if case.status != "AC":
                failed_lines.append(f"{result.problem} {case.name}")
                if case.expected is not None:
                    lines.append("expected:")
                    lines.append(case.expected)
                lines.append("output:")
                lines.append(case.output)
                if case.stderr:
                    lines.append("stderr:")
                    lines.append(case.stderr)
            lines.append("")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    failed_path.write_text("\n".join(failed_lines), encoding="utf-8")
    return log_path


def _print_auto_summary(results: List[ProblemResult], log_path: Path):
    total_cases = sum(result.total_count for result in results)
    passed_cases = sum(result.ok_count for result in results)
    failed_items = []
    total_ms = sum(result.duration_ms for result in results)

    for result in results:
        if result.error_status:
            failed_items.append((result.problem, result.error_status, result.error_message))
        for case in result.failed_cases:
            failed_items.append((result.problem, case.status, case.name))

    problems = ",".join(result.problem for result in results)
    if failed_items:
        print(f"{RED}FAIL{RESET} {problems}: {passed_cases}/{total_cases} AC in {_format_seconds(total_ms)}")
        for problem, status, detail in failed_items[:8]:
            print(f"  {problem} - {status}: {detail}")
        if len(failed_items) > 8:
            print(f"  ... and {len(failed_items) - 8} more")
        print(f"Full log: {log_path}")
    else:
        print(f"{GREEN}PASS{RESET} {problems}: {total_cases} tests in {_format_seconds(total_ms)}")
        print(f"Full log: {log_path}")

def _results_passed(results: List[ProblemResult]):
    return bool(results) and all(result.passed for result in results)


# ---------- run ----------
def cmd_run(problem: str, run_language: Optional[str] = None):
    result = run_problem_tests(problem, run_language, show_compile=True)
    _print_detailed_result(result)
    if not result.passed:
        sys.exit(1)


def cmd_run_all(run_language: Optional[str] = None):
    cwd = Path.cwd()
    config = load_config(cwd)
    problems = _available_problems(cwd, _config_problems(config))
    if not _run_auto_tests(problems, run_language, reason="manual"):
        sys.exit(1)


def cmd_rerun(run_language: Optional[str] = None):
    failed_path = LOG_DIR / "last_failed.txt"
    if not failed_path.exists():
        print(f"{YELLOW}直前の失敗記録がありません。{RESET}")
        return

    groups = {}
    for line in failed_path.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        problem, case_name = parts
        if case_name == "*":
            groups[problem] = None
        elif groups.get(problem) is not None:
            groups.setdefault(problem, set()).add(case_name)

    if not groups:
        print(f"{GREEN}直前に失敗したケースはありません。{RESET}")
        return

    results = []
    for problem, case_names in sorted(groups.items()):
        results.append(run_problem_tests(problem, run_language, show_compile=False, case_names=case_names))

    log_path = _write_test_log(results)
    _print_auto_summary(results, log_path)
    if not _results_passed(results):
        sys.exit(1)


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
    problems = problems or _config_problems(load_config(cwd))
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


def _changed_paths(before: Dict[Path, tuple], after: Dict[Path, tuple]):
    changed = set()
    for path in before.keys() | after.keys():
        if before.get(path) != after.get(path):
            changed.add(path)
    return changed


def _problem_from_changed_path(cwd: Path, path: Path, problems: Optional[List[str]] = None):
    problems = problems or _config_problems(load_config(cwd))
    problem_set = set(problems)

    try:
        rel = path.relative_to(cwd)
    except ValueError:
        return None

    parts = rel.parts
    if len(parts) == 1:
        if rel.name in CONFIG_FILES:
            return "ALL"
        if rel.suffix in [".py", ".cpp"] and rel.stem.upper() in problem_set:
            return rel.stem.upper()

    if len(parts) >= 2 and parts[0] == "tests" and parts[1].upper() in problem_set:
        return parts[1].upper()

    return None


def _changed_problems(cwd: Path, paths: Set[Path], selected: List[str], problems: Optional[List[str]] = None):
    selected_set = set(selected)
    changed = set()
    problems = problems or _config_problems(load_config(cwd))

    for path in paths:
        problem = _problem_from_changed_path(cwd, path, problems)
        if problem == "ALL":
            return selected or _available_problems(cwd, problems)
        if problem:
            changed.add(problem)

    if selected_set:
        changed &= selected_set
    return sorted(changed)


def _run_auto_tests(problems: List[str], run_language: Optional[str] = None, reason=""):
    if not problems:
        print(f"{YELLOW}テスト対象が見つかりません。{RESET}")
        return False

    label = ",".join(problems)
    prefix = f"{reason}: " if reason else ""
    print(f"{prefix}running {label} ...")
    results = [run_problem_tests(problem, run_language, show_compile=False) for problem in problems]
    log_path = _write_test_log(results)
    _print_auto_summary(results, log_path)
    return _results_passed(results)


def cmd_watch(args):
    cwd = Path.cwd()
    config = load_config(cwd)
    configured_problems = _config_problems(config)
    run_language = None
    selected = []

    for arg in args:
        low = arg.lower()
        if low in ["python", "py", "pypy", "cpp"]:
            run_language = low
        elif low in ["all", "--all"]:
            selected = []
        else:
            selected.append(_normalize_problem(arg))

    watch_problems = selected or configured_problems
    problems = selected or _available_problems(cwd, configured_problems)
    print(f"watching {cwd}")
    print(f"debounce: {WATCH_DEBOUNCE_SECONDS:.1f}s / log: {LOG_DIR / 'last.log'}")
    print("Ctrl+C で終了します。")
    _run_auto_tests(problems, run_language, reason="initial")

    snapshot = _watch_snapshot(cwd, watch_problems)
    pending = set()
    last_change_at = None

    try:
        while True:
            time.sleep(WATCH_POLL_SECONDS)
            current = _watch_snapshot(cwd, watch_problems)
            changed = _changed_paths(snapshot, current)
            if changed:
                snapshot = current
                pending.update(changed)
                last_change_at = time.perf_counter()
                continue

            if pending and last_change_at and time.perf_counter() - last_change_at >= WATCH_DEBOUNCE_SECONDS:
                changed = _changed_problems(cwd, pending, selected, watch_problems)
                _run_auto_tests(changed, run_language, reason="changed")
                pending.clear()
                last_change_at = None
    except KeyboardInterrupt:
        print("\nwatch stopped.")

# ---------- main ----------
def main():
    if len(sys.argv) < 2: usage()
    cmd = sys.argv[1]

    if cmd == "new" and len(sys.argv) >= 3:
        lang = sys.argv[3] if len(sys.argv) == 4 else None
        cmd_new(sys.argv[2], lang)
    elif cmd in ["contest", "contests"] and len(sys.argv) >= 3:
        lang = sys.argv[3] if len(sys.argv) == 4 else None
        cmd_contest(sys.argv[2], lang)
    elif cmd == "config":
        cmd_config(sys.argv[2:])
    elif cmd in ["run", "r", "test", "t"] and len(sys.argv) >= 3:
        interp = sys.argv[3] if len(sys.argv) == 4 else None
        if sys.argv[2].lower() == "all":
            cmd_run_all(interp)
        else:
            cmd_run(sys.argv[2], interp)
    elif cmd in ["rerun", "retry"]:
        interp = sys.argv[2] if len(sys.argv) == 3 else None
        cmd_rerun(interp)
    elif cmd in ["watch", "w", "auto"]:
        cmd_watch(sys.argv[2:])
    elif cmd == "manual":
        if len(sys.argv) >= 3 and sys.argv[2] == "tests":
            cmd_manual_tests()
        else:
            cmd_manual(sys.argv[2:])
    else:
        usage()

if __name__ == "__main__":
    main()
