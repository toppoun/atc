import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

try:
    from .config import (
        SOURCE_EXTS,
        _normalize_run_language,
        _runner_command,
        _runner_compile_timeout,
        _runner_cpp_flags,
        _runner_timeout,
        config_problems,
        load_config,
        resolve_executable,
    )
    from .console import GREEN, RED, RESET, color_text, error, ok, warn
    from .models import CaseResult, ProblemResult
except ImportError:
    from config import (
        SOURCE_EXTS,
        _normalize_run_language,
        _runner_command,
        _runner_compile_timeout,
        _runner_cpp_flags,
        _runner_timeout,
        config_problems,
        load_config,
        resolve_executable,
    )
    from console import GREEN, RED, RESET, color_text, error, ok, warn
    from models import CaseResult, ProblemResult


LOG_DIR = Path(".atc") / "test-runs"


def _normalize_problem(problem: str):
    return problem.upper()


def _available_problems(cwd: Path, problems: Optional[List[str]] = None):
    problems = problems or config_problems(load_config(cwd))
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
    compiler_path = resolve_executable(compiler)
    if not compiler_path:
        return "cpp", [], None, "ERROR", _missing_cpp_compiler_message(compiler)

    suffix = ".exe" if platform.system() == "Windows" else ".out"
    exe_path = cwd / f"_{problem}{suffix}"
    flags = _runner_cpp_flags(config)

    if show_compile:
        warn(f"Compiling {cpp_file.name}...")
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
    executable = resolve_executable(command)
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
        error(result.error_status)
        if result.error_message:
            print(result.error_message)
        return

    for case in result.cases:
        print(f"=== {case.name} ===")
        if case.status == "AC":
            print(f" {color_text('AC', GREEN)}")
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


def cmd_run(problem: str, run_language: Optional[str] = None):
    result = run_problem_tests(problem, run_language, show_compile=True)
    _print_detailed_result(result)
    if not result.passed:
        sys.exit(1)


def cmd_run_all(run_language: Optional[str] = None):
    cwd = Path.cwd()
    config = load_config(cwd)
    problems = _available_problems(cwd, config_problems(config))
    if not _run_auto_tests(problems, run_language, reason="manual"):
        sys.exit(1)


def cmd_rerun(run_language: Optional[str] = None):
    failed_path = LOG_DIR / "last_failed.txt"
    if not failed_path.exists():
        warn("直前の失敗記録がありません。")
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
        ok("直前に失敗したケースはありません。")
        return

    results = []
    for problem, case_names in sorted(groups.items()):
        results.append(run_problem_tests(problem, run_language, show_compile=False, case_names=case_names))

    log_path = _write_test_log(results)
    _print_auto_summary(results, log_path)
    if not _results_passed(results):
        sys.exit(1)


def _run_auto_tests(problems: List[str], run_language: Optional[str] = None, reason=""):
    if not problems:
        warn("テスト対象が見つかりません。")
        return False

    label = ",".join(problems)
    prefix = f"{reason}: " if reason else ""
    print(f"{prefix}running {label} ...")
    results = [run_problem_tests(problem, run_language, show_compile=False) for problem in problems]
    log_path = _write_test_log(results)
    _print_auto_summary(results, log_path)
    return _results_passed(results)


# Public aliases used by watch.py and lightweight tests.
normalize_problem = _normalize_problem
available_problems = _available_problems
write_test_log = _write_test_log
print_auto_summary = _print_auto_summary
results_passed = _results_passed
run_auto_tests = _run_auto_tests
