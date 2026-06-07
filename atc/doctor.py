import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set
import tomllib

from atc.ui.console import Text, Table, Panel, box, console
from .config import (
    CONFIG_FILE_META_KEY,
    deep_merge_config,
    default_config,
    find_config_file,
    find_project_root,
    runner_command,
    runner_compile_timeout,
    runner_cpp_flags,
    runner_timeout,
    config_root,
    resolve_executable,
    watch_settings,
)
from .metadata import contest_metadata_error, contest_metadata_problems
from .templates import TemplateError, resolve_template_file as _resolve_template_file

try:
    from rich.columns import Columns
except ImportError:  # pragma: no cover - exercised when rich is not installed
    Columns = None


# --- Constants ---
STATUS_ORDER = ["OK", "WARN", "ERROR", "INFO"]
STATUS_STYLES = {
    "OK": "green",
    "WARN": "yellow",
    "ERROR": "bold red",
    "INFO": "cyan",
}
DASHBOARD_CARD_WIDTH = 24


@dataclass
class DoctorItem:
    section: str
    status: str
    message: str = ""
    details: List[str] = field(default_factory=list)
    key: str = ""
    label: str = ""
    value: str = ""

    @property
    def display_message(self) -> str:
        if self.label and self.value:
            return f"{self.label}: {self.value}"
        if self.label:
            return self.label
        return self.message


class DoctorReport:
    def __init__(self, immediate: bool = True):
        self.counts = {"OK": 0, "WARN": 0, "ERROR": 0, "INFO": 0}
        self.immediate = immediate
        self.current_section = ""
        self.section_order: List[str] = []
        self.items: List[DoctorItem] = []

    def section(self, title: str):
        self.current_section = title
        if title not in self.section_order:
            self.section_order.append(title)
        if self.immediate:
            print()
            print(title)

    def item(
        self,
        status: str,
        message: str = "",
        details: Optional[List[str]] = None,
        *,
        key: str = "",
        label: str = "",
        value: object = "",
    ):
        self.counts[status] = self.counts.get(status, 0) + 1
        item = DoctorItem(
            self.current_section,
            status,
            message,
            list(details or []),
            key,
            label,
            "" if value is None else str(value),
        )
        self.items.append(item)
        if self.immediate:
            self._print_plain_item(item)

    def summary(self):
        if not self.immediate:
            self._render_summary()
            return
        self._print_plain_summary()

    def render(self):
        self._render_rich()


    def _print_plain_item(self, item: DoctorItem):
        print(f"  [{item.status}] {item.display_message}")
        for detail in item.details:
            print(f"       {detail}")

    def _print_plain_summary(self):
        print()
        print("Summary")
        print(f"  OK: {self.counts.get('OK', 0)}")
        print(f"  WARN: {self.counts.get('WARN', 0)}")
        print(f"  ERROR: {self.counts.get('ERROR', 0)}")
        print(f"  INFO: {self.counts.get('INFO', 0)}")

    def _render_plain(self):
        print("AtC Doctor")
        for label, value in self._dashboard_rows():
            print(f"  {label:<8} {value}")
        print()
        print("Status")
        for status in STATUS_ORDER:
            print(f"  {status:<5} {self.counts.get(status, 0)}")
        print()
        print("Tools")
        for label, status in self._tool_rows():
            print(f"  {label:<8} {status}")
        print()
        print("Current")
        for label, value in self._current_rows():
            print(f"  {label:<8} {value}")
        self._render_details_plain()
        self._print_plain_summary()

    def _render_rich(self):
        border_style = "bold red" if self.has_error else "cyan"
        console.print(self._dashboard_panel(border_style))
        card_height = max(len(self._status_rows()), len(self._tool_rows()), len(self._current_rows()))
        panels = [
            self._status_panel(card_height),
            self._tools_panel(card_height),
            self._current_panel(card_height),
        ]
        if Columns:
            console.print(Columns(panels, equal=True))
        else:
            for panel in panels:
                console.print(panel)
        self._render_details_rich()
        self._render_summary()

    def _dashboard_panel(self, border_style: str):
        table = Table.grid(padding=(0, 2), expand=True)
        table.add_column(style="bold", no_wrap=True)
        table.add_column(style="dim", ratio=1)
        for label, value in self._dashboard_rows():
            table.add_row(label, value)
        return Panel(table, title="AtC Doctor", border_style=border_style, box=box.ROUNDED)

    def _pad_rows(self, rows, min_rows: int):
        padded = list(rows)
        while len(padded) < min_rows:
            padded.append(("", ""))
        return padded

    def _kv_table(self, rows, *, value_style: str = ""):
        table = Table.grid(padding=(0, 2), expand=True)
        table.add_column(style="bold", no_wrap=True)
        table.add_column(justify="right")
        for label, value in rows:
            if isinstance(value, str) and value in STATUS_STYLES:
                rendered_value = self._status_text(value)
            elif value_style:
                rendered_value = Text(str(value), style=value_style)
            else:
                rendered_value = str(value)
            table.add_row(label, rendered_value)
        return table

    def _status_panel(self, min_rows: int = 0):
        rows = self._pad_rows(self._status_rows(), min_rows)
        return Panel(
            self._kv_table(rows),
            title="Status",
            border_style="cyan",
            box=box.ROUNDED,
            width=DASHBOARD_CARD_WIDTH,
        )

    def _tools_panel(self, min_rows: int = 0):
        rows = self._pad_rows(self._tool_rows(), min_rows)
        return Panel(
            self._kv_table(rows),
            title="Tools",
            border_style="cyan",
            box=box.ROUNDED,
            width=DASHBOARD_CARD_WIDTH,
        )

    def _current_panel(self, min_rows: int = 0):
        rows = self._pad_rows(self._current_rows(), min_rows)
        return Panel(
            self._kv_table(rows, value_style="dim"),
            title="Current",
            border_style="cyan",
            box=box.ROUNDED,
            width=DASHBOARD_CARD_WIDTH,
        )

    def _render_details_plain(self):
        for section in self.section_order:
            print()
            print(section)
            for item in self._items_for_section(section):
                self._print_plain_item(item)

    def _render_details_rich(self):
        for section in self.section_order:
            console.print()
            console.print(section, style="bold cyan")
            for item in self._items_for_section(section):
                line = Text("  ")
                line.append(f"[{item.status}]", style=STATUS_STYLES.get(item.status, ""))
                line.append(" ")
                self._append_item_message(line, item)
                console.print(line)
                for detail in item.details:
                    console.print(Text(f"       {detail}", style="dim"))

    def _render_summary(self):
        console.print()
        console.print("Summary", style="bold cyan")
        for status in STATUS_ORDER:
            line = Text("  ")
            line.append(f"{status}: ", style=STATUS_STYLES.get(status, ""))
            line.append(str(self.counts.get(status, 0)))
            console.print(line)


    def _append_message(self, line, message: str):
        label, sep, value = message.partition(":")
        if sep and label and len(label) <= 48:
            line.append(label, style="bold")
            line.append(sep)
            line.append(value, style="dim")
            return
        line.append(message)

    def _append_item_message(self, line, item: DoctorItem):
        if item.label:
            line.append(item.label, style="bold")
            if item.value:
                line.append(":")
                line.append(f" {item.value}", style="dim")
            return
        self._append_message(line, item.message)

    def _items_for_section(self, section: str):
        return [item for item in self.items if item.section == section]

    def _find_item(self, *, section: Optional[str] = None, prefixes=(), contains=()):
        for item in self.items:
            if section and item.section != section:
                continue
            message = item.display_message
            if prefixes and not any(message.startswith(prefix) for prefix in prefixes):
                continue
            if contains and not any(part in message for part in contains):
                continue
            return item
        return None

    def _message_after(self, prefix: str, *, section: Optional[str] = None):
        item = self._find_item(section=section, prefixes=(prefix,))
        if not item:
            return None
        return item.display_message[len(prefix):].strip()

    def item_by_key(self, key: str) -> Optional[DoctorItem]:
        for item in self.items:
            if item.key == key:
                return item
        return None

    def value_for(self, key: str, default: str = "") -> str:
        item = self.item_by_key(key)
        if not item:
            return default
        return item.value or default

    def status_for_key(self, key: str, default: str = "INFO") -> str:
        item = self.item_by_key(key)
        return item.status if item else default

    def _dashboard_rows(self):
        root = self.value_for("resolved_root")
        if not root:
            root = self.value_for("resolved_root_missing")
        if not root:
            root = self._message_after("Resolved root: ", section="Config")
        if not root:
            root = self._message_after("Resolved root does not exist: ", section="Config")
        if not root and (self.item_by_key("paths_root_empty") or self._find_item(section="Config", prefixes=("paths.root is empty.",))):
            root = "current directory"

        config_file = self.value_for("config_file")
        if not config_file:
            config_file = self._message_after("Config file: ", section="Config")
        current = self.value_for("current_contest_dir")
        if not current:
            current = self._message_after("contestDir: ", section="Current contest")
        if not current and (self.item_by_key("current_contest_missing") or self._find_item(section="Current contest", prefixes=("current-contest.json not found yet.",))):
            current = "(none)"

        oj_login = "unknown"
        login_item = self.item_by_key("oj_login") or self._find_item(section="Tools", prefixes=("oj login:", "oj login check"))
        if login_item:
            if login_item.status == "OK":
                oj_login = "logged in"
            elif login_item.status == "WARN":
                oj_login = "not logged in or check failed"
            else:
                oj_login = login_item.status.lower()
        oj_item = self.item_by_key("oj")
        if (
            not login_item
            and (
                (oj_item and oj_item.display_message.startswith("oj was not found."))
                or self._find_item(section="Tools", prefixes=("oj was not found.",))
            )
        ):
            oj_login = "oj not found"

        return [
            ("Root", root or "(unknown)"),
            ("Config", config_file or "(default config)"),
            ("Current", current or "(unknown)"),
            ("oj", oj_login),
        ]

    def _tool_rows(self):
        return [
            ("Python", self.status_for_key("python", self._status_for(section="Environment", prefixes=("Python:",)))),
            ("PyPy", self.status_for_key("pypy", self._status_for(section="Runner", prefixes=("PyPy:",)))),
            (
                "g++",
                self.status_for_key(
                    "cpp_compiler",
                    self._status_for(section="Runner", prefixes=("C++ compiler:", "Configured C++ compiler", "C++ compiler not found.")),
                ),
            ),
            ("oj", self.status_for_key("oj", self._status_for(section="Tools", prefixes=("oj:", "oj command", "oj was not found.")))),
            ("oj login", self.status_for_key("oj_login", self._status_for(section="Tools", prefixes=("oj login:", "oj login check")))),
            ("VS Code", self.status_for_key("vscode_extension", self._status_for(section="VS Code", prefixes=("VS Code extension:",)))),
        ]

    def _status_rows(self):
        return [(self._status_text(status), str(self.counts.get(status, 0))) for status in STATUS_ORDER]

    def _current_rows(self):
        contest_dir = self.value_for("current_contest_dir")
        if not contest_dir:
            contest_dir = self._message_after("contestDir: ", section="Current contest")
        if contest_dir:
            contest = Path(contest_dir).name
        elif self.item_by_key("current_contest_missing") or self._find_item(section="Current contest", prefixes=("current-contest.json not found yet.",)):
            contest = "(none)"
        else:
            contest = "(unknown)"

        metadata = "unknown"
        metadata_item = self.item_by_key("contest_metadata") or self._find_item(section="Contest metadata", prefixes=("Contest metadata:",))
        if metadata_item:
            if metadata_item.status == "OK":
                metadata = "found"
            elif metadata_item.status == "INFO":
                metadata = "not found"
            else:
                metadata = metadata_item.status

        current_status = "INFO"
        for key in ("current_contest_dir", "current_contest_file", "current_contest_missing"):
            item = self.item_by_key(key)
            if item:
                current_status = item.status
                break
        if current_status == "INFO" and not self.item_by_key("current_contest_missing"):
            current_status = self._status_for(
                section="Current contest",
                prefixes=(
                    "current-contest.json",
                    "contestDir",
                    "Failed to read current-contest.json",
                ),
            )

        return [
            ("contest", contest),
            ("metadata", metadata),
            ("current", current_status),
            ("VS Code", self.status_for_key("vscode_extension", self._status_for(section="VS Code", prefixes=("VS Code extension:",)))),
        ]

    def _status_for(self, *, section: str, prefixes=()):
        item = self._find_item(section=section, prefixes=prefixes)
        return item.status if item else "INFO"

    def _status_text(self, status: str):
        return Text(status, style=STATUS_STYLES.get(status, ""))

    @property
    def has_error(self):
        return self.counts.get("ERROR", 0) > 0


def _load_config_for_doctor(start: Path):
    config = default_config()
    config_file = find_config_file(start)
    if not config_file:
        return config, None, None

    try:
        with config_file.open("rb") as f:
            loaded = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        return config, config_file, f"failed to parse config file: {e}"
    except OSError as e:
        return config, config_file, f"failed to read config file: {e}"

    merged = deep_merge_config(config, loaded)
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


def _doctor_check_oj_login(report: DoctorReport, oj: str):
    try:
        code, stdout, stderr = _run_doctor_command(
            [oj, "login", "--check", "https://atcoder.jp/"],
            timeout=8.0,
        )
    except Exception as e:
        report.item(
            "WARN",
            "oj login check failed.",
            [str(e), "check manually: oj login --check https://atcoder.jp/"],
            key="oj_login",
            label="oj login check failed.",
        )
        return

    output = "\n".join(part for part in [stdout, stderr] if part)
    if code == 0:
        report.item("OK", key="oj_login", label="oj login", value="logged in to atcoder.jp")
        return

    if "timed out" in output.lower() or "timeout" in output.lower():
        report.item(
            "WARN",
            "oj login check failed or timed out.",
            ["check manually: oj login --check https://atcoder.jp/"],
            key="oj_login",
            label="oj login check failed or timed out.",
        )
        return

    report.item(
        "WARN",
        "oj login: not logged in to atcoder.jp or login check failed.",
        [
            "sample download may fail for live contests.",
            "run: oj login https://atcoder.jp/",
            "check manually: oj login --check https://atcoder.jp/",
        ],
        key="oj_login",
        label="oj login",
        value="not logged in to atcoder.jp or login check failed.",
    )


def _first_line(text: str):
    return text.splitlines()[0] if text else ""


def _display_path(path: Optional[Path]):
    return str(path.resolve()) if path else "(none)"


def _doctor_check_python(report: DoctorReport):
    report.section("Environment")
    report.item("OK", key="python", label="Python", value=f"{sys.executable} ({platform.python_version()})")

    atc = shutil.which("atc")
    if atc:
        report.item("OK", key="atc_command", label="atc command", value=atc)
    else:
        report.item(
            "WARN",
            "atc command was not found in PATH.",
            ["Try reopening your terminal, or check your pip scripts path."],
            key="atc_command",
            label="atc command was not found in PATH.",
        )


def _doctor_check_config(report: DoctorReport, config: dict, config_file: Optional[Path], config_error: Optional[str]):
    report.section("Config")
    if config_error:
        report.item("ERROR", details=[config_error], key="config_file", label="Config file", value=_display_path(config_file))
    elif config_file:
        report.item("OK", key="config_file", label="Config file", value=config_file.resolve())
    else:
        report.item("INFO", key="config_file", label="Config file", value="(default config)")

    paths = config.get("paths", {})
    root_value = str(paths.get("root") or "").strip()
    root = config_root(config)
    if root_value:
        if root and root.exists():
            report.item("OK", key="resolved_root", label="Resolved root", value=root)
        elif root:
            report.item("WARN", key="resolved_root_missing", label="Resolved root does not exist", value=root)
    else:
        report.item(
            "INFO",
            "paths.root is empty. atc contest will use the current directory.",
            key="paths_root_empty",
            label="paths.root is empty. atc contest will use the current directory.",
        )

    contests = paths.get("contests", {})
    if "contests" in paths and not isinstance(contests, dict):
        report.item("ERROR", "[paths.contests] must be a table.")
    elif isinstance(contests, dict) and contests:
        for pattern, directory in contests.items():
            report.item("OK", f"paths.contests[{pattern!r}]: {directory}")
    else:
        report.item("INFO", "paths.contests is empty. Contests will be created directly under root.")


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
    python_cmd = runner_command(config, "python", "python")
    python_runner = resolve_executable(python_cmd)
    if python_runner:
        report.item("OK", key="python_runner", label="Python runner", value=python_runner)
    else:
        report.item(
            "OK",
            details=[f"Configured runner.python was not found: {python_cmd}", "Using current Python as fallback."],
            key="python_runner",
            label="Python runner",
            value=sys.executable,
        )

    pypy_cmd = runner_command(config, "pypy", "pypy")
    pypy_runner = resolve_executable(pypy_cmd)
    if not pypy_runner and pypy_cmd == "pypy":
        pypy_runner = shutil.which("pypy3")
    if pypy_runner:
        report.item("OK", key="pypy", label="PyPy", value=pypy_runner)
    else:
        report.item("WARN", key="pypy", label="PyPy", value="not found. Python mode still works.")

    compiler_cmd = runner_command(config, "cpp_compiler", "g++")
    compiler = resolve_executable(compiler_cmd)
    if compiler:
        report.item("OK", key="cpp_compiler", label="C++ compiler", value=compiler)
    else:
        fallback_compiler = shutil.which("clang++") or shutil.which("g++")
        if fallback_compiler:
            report.item(
                "WARN",
                details=[f"Available compiler: {fallback_compiler}", "Update runner.cpp_compiler in config.toml if you use C++."],
                key="cpp_compiler",
                label="Configured C++ compiler not found",
                value=compiler_cmd,
            )
        else:
            report.item(
                "WARN",
                details=["If you use C++, install Xcode Command Line Tools:", "xcode-select --install"],
                key="cpp_compiler",
                label="C++ compiler not found.",
            )

    report.item("OK", f"C++ flags: {' '.join(runner_cpp_flags(config))}")
    run_timeout = runner_timeout(config)
    compile_timeout = runner_compile_timeout(config)
    report.item("OK", f"Run timeout: {run_timeout}s" if run_timeout else "Run timeout: disabled")
    report.item("OK", f"Compile timeout: {compile_timeout}s" if compile_timeout else "Compile timeout: disabled")


def _doctor_check_watch(report: DoctorReport, config: dict):
    report.section("Watch")
    poll_seconds, debounce_seconds, warnings = watch_settings(config)
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
            report.item("OK", key="oj", label="oj", value=f"{oj}" + (f" ({version})" if version else ""))
        else:
            report.item(
                "WARN",
                details=[stderr or stdout or "oj --version failed"],
                key="oj",
                label="oj command exists but failed",
                value=oj,
            )
        _doctor_check_oj_login(report, oj)
    else:
        report.item(
            "WARN",
            details=[
                "Sample download will not work.",
                "Install: python3 -m pip install online-judge-tools",
                "Login: oj login https://atcoder.jp/",
            ],
            key="oj",
            label="oj was not found.",
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
            details=["Not executed by doctor to avoid opening VS Code."],
            key="vscode_cli",
            label="VS Code CLI candidate",
            value=code_cmd,
        )

    installed_path, related, searched = _find_vscode_extension_on_disk(extension_id)
    if installed_path:
        report.item(
            "OK",
            details=[f"Found: {installed_path}"],
            key="vscode_extension",
            label="VS Code extension",
            value=extension_id,
        )
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
        report.item("WARN", details=details, key="vscode_extension", label="VS Code extension", value="could not verify")


def _doctor_current_contest_root(config: dict, cwd: Path):
    root = config_root(config)
    return root if root else find_project_root(cwd, config)


def _doctor_check_current_contest(report: DoctorReport, config: dict, cwd: Path):
    report.section("Current contest")
    root = _doctor_current_contest_root(config, cwd)
    current_file = root / ".atc" / "current-contest.json"
    if not current_file.exists():
        report.item(
            "INFO",
            "current-contest.json not found yet.",
            ["Run: atc contest abc335 cpp", f"Expected path: {current_file}"],
            key="current_contest_missing",
            label="current-contest.json not found yet.",
        )
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
        report.item("OK", key="current_contest_file", label="current-contest.json", value=current_file)
        report.item("OK", key="current_contest_dir", label="contestDir", value=contest_dir)
    else:
        report.item("WARN", details=[f"Source: {current_file}"], key="current_contest_dir", label="contestDir does not exist", value=contest_dir)


def _doctor_check_contest_metadata(report: DoctorReport, cwd: Path):
    report.section("Contest metadata")
    error_message = contest_metadata_error(cwd)
    metadata_file = cwd / ".atc" / "contest.toml"
    if error_message:
        report.item("ERROR", details=[error_message], key="contest_metadata", label="Contest metadata", value=metadata_file)
        return

    if metadata_file.exists():
        problems = contest_metadata_problems(cwd)
        report.item("OK", details=[f"problems: {len(problems)}"], key="contest_metadata", label="Contest metadata", value=metadata_file)
    else:
        report.item("INFO", details=[f"Expected path: {metadata_file}"], key="contest_metadata", label="Contest metadata", value="not found.")


def cmd_config_doctor():
    cwd = Path.cwd()
    report = DoctorReport(immediate=False)
    config, config_file, config_error = _load_config_for_doctor(cwd)

    _doctor_check_python(report)
    _doctor_check_config(report, config, config_file, config_error)
    _doctor_check_templates(report, config, cwd)
    _doctor_check_runner(report, config)
    _doctor_check_watch(report, config)
    _doctor_check_tools(report)
    _doctor_check_vscode(report)
    _doctor_check_contest_metadata(report, cwd)
    _doctor_check_current_contest(report, config, cwd)
    report.render()

    if report.has_error:
        sys.exit(1)
