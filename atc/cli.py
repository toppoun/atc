import sys
import subprocess
import shutil
import time
import platform
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

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

def load_template(ext: str):
    """templates/template.{ext} を読み込む。存在しない場合は空文字を返す"""
    template_file = TEMPLATE_DIR / f"template.{ext}"
    if template_file.exists():
        return template_file.read_text(encoding="utf-8")
    else:
        print(f"{YELLOW}Warning: {template_file} が見つかりません。空ファイルを作成します。{RESET}")
        return ""

def _download_samples(contest: str, problem_char: str, dst_dir: Path):
    tmp = dst_dir.parent / f".oj_tmp_{problem_char}"
    url = f"https://atcoder.jp/contests/{contest}/tasks/{contest}_{problem_char.lower()}"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        subprocess.run(["oj", "d", url, "-d", str(tmp)], check=True, capture_output=True, text=True)
        if not tmp.exists(): return False
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in tmp.iterdir(): shutil.move(str(f), dst_dir / f.name)
        shutil.rmtree(tmp, ignore_errors=True)
        return True
    except:
        shutil.rmtree(tmp, ignore_errors=True)
        return False

# ---------- usage ----------

def usage():
    print("使い方:")
    print("  atc new abc413 [py|cpp]  (デフォルトは cpp)")
    print("  atc run A [python|pypy]")
    print("  atc run all [python|pypy]")
    print("  atc rerun [python|pypy]")
    print("  atc watch [A] [python|pypy]")
    print("  atc manual A B C")
    print("  atc manual tests  (現在のフォルダ名を contest_id としてサンプル取得)")
    sys.exit(1)

# ---------- new ----------
def cmd_new(contest: str, lang: str = "cpp"):
    base = Path(contest)
    tests = base / "tests"
    base.mkdir(exist_ok=True)
    
    template_content = load_template(lang)
    
    for p in PROBLEMS:
        # ファイル作成 (A.py または A.cpp)
        source_file = base / f"{p}.{lang}"
        if not source_file.exists():
            source_file.write_text(template_content, encoding="utf-8")

        # サンプル取得
        print(f"fetching {p} ...", end=" ", flush=True)
        if _download_samples(contest, p, tests / p):
            print(f"{GREEN}done{RESET}")
        else:
            print(f"{RED}failed{RESET}")

    print(f"\n{contest} ({lang}) ready.")

# ---------- manual ----------
def cmd_manual(args):
    cwd = Path.cwd()
    # 簡易的に拡張子を判別（引数に .cpp 等が含まれていればそれを使う）
    lang = "cpp"
    targets = []
    for arg in args:
        if arg in ["py", "cpp"]:
            lang = arg
            continue
        targets.append(arg)

    template_content = load_template(lang)
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
    contest = cwd.name.lower()
    tests = cwd / "tests"

    if not contest:
        print(f"{RED}コンテストIDを現在のフォルダ名から取得できません。{RESET}")
        sys.exit(1)

    print(f"contest: {contest}")
    for p in PROBLEMS:
        print(f"fetching {p} ...", end=" ", flush=True)
        if _download_samples(contest, p, tests / p):
            print(f"{GREEN}done{RESET}")
        else:
            print(f"{RED}failed{RESET}")

def _normalize_problem(problem: str):
    return problem.upper()


def _available_problems(cwd: Path):
    found = []
    for problem in PROBLEMS:
        has_source = any((cwd / f"{problem}.{ext}").exists() for ext in SOURCE_EXTS)
        has_tests = (cwd / "tests" / problem).exists()
        if has_source or has_tests:
            found.append(problem)
    return found


def _prepare_run_command(cwd: Path, problem: str, interpreter="python", show_compile=False):
    py_file = cwd / f"{problem}.py"
    cpp_file = cwd / f"{problem}.cpp"

    if cpp_file.exists():
        mode = "cpp"
        suffix = ".exe" if platform.system() == "Windows" else ".out"
        exe_path = cwd / f"_{problem}{suffix}"

        if show_compile:
            print(f"{YELLOW}Compiling {cpp_file.name}...{RESET}")
        c_proc = subprocess.run(
            ["g++", "-O2", str(cpp_file), "-o", str(exe_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if c_proc.returncode != 0:
            return mode, [], exe_path, "CE", c_proc.stderr.strip()
        return mode, [str(exe_path)], exe_path, None, ""

    if py_file.exists():
        mode = "py"
        exe = sys.executable if interpreter != "pypy" else detect_pypy()
        if not exe:
            return mode, [], None, "ERROR", "PyPy が見つかりません。"
        return mode, [exe, str(py_file)], None, None, ""

    return None, [], None, "ERROR", "ファイルが見つかりません。"


def run_problem_tests(problem: str, interpreter="python", show_compile=False, case_names: Optional[Set[str]] = None):
    cwd = Path.cwd()
    problem = _normalize_problem(problem)
    testdir = cwd / "tests" / problem
    started = time.perf_counter()
    result = ProblemResult(problem=problem)

    mode, run_cmd, cleanup_path, error_status, error_message = _prepare_run_command(
        cwd,
        problem,
        interpreter,
        show_compile=show_compile,
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
                proc = subprocess.run(run_cmd, stdin=fin, capture_output=True, text=True)
                elapsed = (time.perf_counter() - case_started) * 1000

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


# ---------- run ----------
def cmd_run(problem: str, interpreter="python"):
    result = run_problem_tests(problem, interpreter, show_compile=True)
    _print_detailed_result(result)
    if result.error_status:
        sys.exit(1)


def cmd_run_all(interpreter="python"):
    problems = _available_problems(Path.cwd())
    _run_auto_tests(problems, interpreter, reason="manual")


def cmd_rerun(interpreter="python"):
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
        results.append(run_problem_tests(problem, interpreter, show_compile=False, case_names=case_names))

    log_path = _write_test_log(results)
    _print_auto_summary(results, log_path)


def _watch_snapshot(cwd: Path):
    snapshot = {}
    for path in _watch_paths(cwd):
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot[path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _watch_paths(cwd: Path):
    for problem in PROBLEMS:
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


def _problem_from_changed_path(cwd: Path, path: Path):
    try:
        rel = path.relative_to(cwd)
    except ValueError:
        return None

    parts = rel.parts
    if len(parts) == 1:
        if rel.name in CONFIG_FILES:
            return "ALL"
        if rel.suffix in [".py", ".cpp"] and rel.stem.upper() in PROBLEMS:
            return rel.stem.upper()

    if len(parts) >= 2 and parts[0] == "tests" and parts[1].upper() in PROBLEMS:
        return parts[1].upper()

    return None


def _changed_problems(cwd: Path, paths: Set[Path], selected: List[str]):
    selected_set = set(selected)
    changed = set()

    for path in paths:
        problem = _problem_from_changed_path(cwd, path)
        if problem == "ALL":
            return selected or _available_problems(cwd)
        if problem:
            changed.add(problem)

    if selected_set:
        changed &= selected_set
    return sorted(changed)


def _run_auto_tests(problems: List[str], interpreter="python", reason=""):
    if not problems:
        print(f"{YELLOW}テスト対象が見つかりません。{RESET}")
        return

    label = ",".join(problems)
    prefix = f"{reason}: " if reason else ""
    print(f"{prefix}running {label} ...")
    results = [run_problem_tests(problem, interpreter, show_compile=False) for problem in problems]
    log_path = _write_test_log(results)
    _print_auto_summary(results, log_path)


def cmd_watch(args):
    cwd = Path.cwd()
    interpreter = "python"
    selected = []

    for arg in args:
        low = arg.lower()
        if low in ["python", "pypy"]:
            interpreter = low
        elif low in ["all", "--all"]:
            selected = []
        else:
            selected.append(_normalize_problem(arg))

    problems = selected or _available_problems(cwd)
    print(f"watching {cwd}")
    print(f"debounce: {WATCH_DEBOUNCE_SECONDS:.1f}s / log: {LOG_DIR / 'last.log'}")
    print("Ctrl+C で終了します。")
    _run_auto_tests(problems, interpreter, reason="initial")

    snapshot = _watch_snapshot(cwd)
    pending = set()
    last_change_at = None

    try:
        while True:
            time.sleep(WATCH_POLL_SECONDS)
            current = _watch_snapshot(cwd)
            changed = _changed_paths(snapshot, current)
            if changed:
                snapshot = current
                pending.update(changed)
                last_change_at = time.perf_counter()
                continue

            if pending and last_change_at and time.perf_counter() - last_change_at >= WATCH_DEBOUNCE_SECONDS:
                changed = _changed_problems(cwd, pending, selected)
                _run_auto_tests(changed, interpreter, reason="changed")
                pending.clear()
                last_change_at = None
    except KeyboardInterrupt:
        print("\nwatch stopped.")

# ---------- main ----------
def main():
    if len(sys.argv) < 2: usage()
    cmd = sys.argv[1]

    if cmd == "new" and len(sys.argv) >= 3:
        lang = sys.argv[3] if len(sys.argv) == 4 else "cpp"
        cmd_new(sys.argv[2], lang)
    elif cmd in ["run", "r", "test", "t"] and len(sys.argv) >= 3:
        interp = sys.argv[3] if len(sys.argv) == 4 else "python"
        if sys.argv[2].lower() == "all":
            cmd_run_all(interp)
        else:
            cmd_run(sys.argv[2], interp)
    elif cmd in ["rerun", "retry"]:
        interp = sys.argv[2] if len(sys.argv) == 3 else "python"
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
