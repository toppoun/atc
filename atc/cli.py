import sys
import json
import subprocess
import shutil
import platform
import os
from pathlib import Path
from typing import List, Optional, Set

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

try:
    from .config import (
        CONFIG_FILE_META_KEY,
        CONFIG_FILE_NAME,
        _config_root,
        _config_to_toml,
        _deep_merge_config,
        _default_config,
        _find_config_file,
        _find_project_root,
        _resolve_command,
        _runner_command,
        _runner_compile_timeout,
        _runner_cpp_flags,
        _runner_timeout,
        _watch_settings,
        load_config,
    )
    from .console import error, warn
    from .contest import cmd_contest, cmd_new
    from .manual import cmd_manual, cmd_manual_tests
    from .runner import cmd_rerun, cmd_run, cmd_run_all
    from .templates import TemplateError, resolve_template_file as _resolve_template_file
    from .watch import cmd_watch
except ImportError:
    from config import (
        CONFIG_FILE_META_KEY,
        CONFIG_FILE_NAME,
        _config_root,
        _config_to_toml,
        _deep_merge_config,
        _default_config,
        _find_config_file,
        _find_project_root,
        _resolve_command,
        _runner_command,
        _runner_compile_timeout,
        _runner_cpp_flags,
        _runner_timeout,
        _watch_settings,
        load_config,
    )
    from console import error, warn
    from contest import cmd_contest, cmd_new
    from manual import cmd_manual, cmd_manual_tests
    from runner import cmd_rerun, cmd_run, cmd_run_all
    from templates import TemplateError, resolve_template_file as _resolve_template_file
    from watch import cmd_watch

# ===== 設定 =====
# ---------- 共通・補助関数 ----------

def detect_pypy():
    for name in ["pypy3", "pypy"]:
        path = shutil.which(name)
        if path:
            return path
    return None

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
    print("  atc visual [--port 8765] [--no-open]")
    print("  atc manual A B C")
    print("  atc manual tests  (現在のフォルダ名を contest_id としてサンプル取得)")
    sys.exit(1)

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

def _run_doctor_command(args: List[str], timeout: float = 3.0):
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            stdin=subprocess.DEVNULL,
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
        try:
            template = _resolve_template_file(ext, config, cwd)
        except TemplateError as e:
            report.item("ERROR", f"{label} template could not be resolved.", [str(e)])
            continue
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

def _doctor_check_watch(report: DoctorReport, config: dict):
    report.section("Watch")
    poll_seconds, debounce_seconds, warnings = _watch_settings(config)
    if warnings:
        report.item("WARN", "Watch settings: invalid values were ignored.", warnings)
    report.item("OK", f"poll_seconds: {poll_seconds}")
    report.item("OK", f"debounce_seconds: {debounce_seconds}")

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

    for command in ["code.cmd", "code"]:
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

def _vscode_extension_dirs():
    dirs = [
        Path.home() / ".vscode" / "extensions",
        Path.home() / ".vscode-insiders" / "extensions",
    ]
    portable_root = os.environ.get("VSCODE_PORTABLE")
    if portable_root:
        dirs.append(Path(portable_root) / "data" / "extensions")
    return dirs

def _extension_id_from_package_json(extension_dir: Path):
    package_json = extension_dir / "package.json"
    if not package_json.exists():
        return None
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    publisher = str(data.get("publisher") or "").strip()
    name = str(data.get("name") or "").strip()
    if not publisher or not name:
        return None
    return f"{publisher}.{name}".lower()

def _extension_dir_matches(extension_dir: Path, expected: str):
    package_id = _extension_id_from_package_json(extension_dir)
    if package_id:
        return package_id == expected

    name = extension_dir.name.lower()
    return name == expected or name.startswith(expected + "-") or name.startswith(expected + "@")

def _find_vscode_extension_on_disk(extension_id: str):
    expected = extension_id.lower()
    related: List[str] = []
    seen_related: Set[str] = set()
    searched: List[Path] = []

    for extensions_dir in _vscode_extension_dirs():
        searched.append(extensions_dir)
        if not extensions_dir.exists():
            continue
        try:
            children = [path for path in extensions_dir.iterdir() if path.is_dir()]
        except OSError:
            continue
        for child in children:
            if _extension_dir_matches(child, expected):
                return child, related, searched

            package_id = _extension_id_from_package_json(child)
            related_id = package_id or child.name.lower()
            if "atc" in related_id and related_id not in seen_related:
                seen_related.add(related_id)
                related.append(related_id)

    return None, related, searched

def _doctor_check_vscode(report: DoctorReport):
    report.section("VS Code")
    code_cmd = _resolve_vscode_cli()
    extension_id = _vscode_extension_id()
    if not code_cmd:
        report.item(
            "WARN",
            "VS Code CLI was not found.",
            [
                "Could not verify the VS Code extension from the CLI.",
                "This does not mean the extension is not installed.",
                "If VS Code is installed, add the `code` command to PATH.",
                "In VS Code, run: Shell Command: Install 'code' command in PATH",
            ],
        )
    else:
        report.item(
            "INFO",
            f"VS Code CLI candidate: {code_cmd}",
            ["Not executed by doctor to avoid opening VS Code."],
        )

    installed_path, related, searched = _find_vscode_extension_on_disk(extension_id)
    if installed_path:
        report.item("OK", f"VS Code extension: {extension_id}", [f"Found: {installed_path}"])
    else:
        details = [
            "Could not verify the VS Code extension without running VS Code CLI.",
            "This does not mean the extension is not installed.",
            f"Expected: {extension_id}",
        ]
        if related:
            details.append("Found related extensions:")
            details.extend([f"  - {item}" for item in related])
        if searched:
            details.append("Searched extension directories:")
            details.extend([f"  - {path}" for path in searched])
        details.append("You can verify manually from VS Code Extensions.")
        report.item("WARN", "VS Code extension: could not verify", details)

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
    _doctor_check_watch(report, config)
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
            warn(f"already exists: {config_file.resolve()}")
            return
        config_file.write_text(_config_to_toml(_default_config()), encoding="utf-8")
        print(f"created: {config_file.resolve()}")
    elif subcmd == "doctor":
        cmd_config_doctor()
    else:
        usage()

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
    elif cmd in ["visual", "vis", "vizui"]:
        from .visual import cmd_visual, parse_visual_args

        try:
            port, open_browser = parse_visual_args(sys.argv[2:])
        except ValueError as e:
            error(f"Error: {e}")
            print("Usage: atc visual [--port 8765] [--no-open]")
            sys.exit(1)
        sys.exit(cmd_visual(port=port, open_browser=open_browser))
    elif cmd == "manual":
        if len(sys.argv) >= 3 and sys.argv[2] == "tests":
            cmd_manual_tests()
        else:
            cmd_manual(sys.argv[2:])
    else:
        usage()

if __name__ == "__main__":
    main()
