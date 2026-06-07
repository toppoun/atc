import json
import platform
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .config import (
    load_config,
    normalize_run_language,
    resolve_executable,
    runner_command,
    runner_compile_timeout,
    runner_cpp_flags,
    runner_timeout,
)
from .console import (
    error,
    ok,
    print_promote_result,
    print_stress_failure,
    print_stress_header,
    print_text,
    warn,
)
from .templates import (
    TemplateError,
    load_template_manifest,
    resolve_template_manifest,
    resolve_template_name,
)


# --- Constants ---
COMPARE_MODES = {"exact", "strip", "tokens"}
DEFAULT_STRESS_COUNT = 100
DEFAULT_STRESS_TIMEOUT = 2.0
STRESS_DIR = Path(".atc") / "stress"


class StressError(Exception):
    pass


@dataclass
class StressProgram:
    command: list
    path: Path
    cleanup_path: Optional[Path] = None


@dataclass
class StressRunOutput:
    stdout: str
    stderr: str
    returncode: int


def normalize_problem(problem: str) -> str:
    return str(problem).strip().upper()


def normalize_compare_mode(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized not in COMPARE_MODES:
        raise StressError("Invalid compare mode. Use exact, strip, or tokens.")
    return normalized


def compare_outputs(actual: str, expected: str, mode: str = "strip") -> bool:
    mode = normalize_compare_mode(mode)
    if mode == "exact":
        return actual == expected
    if mode == "tokens":
        return actual.split() == expected.split()
    return actual.strip() == expected.strip()


def seed_for_case(base_seed: int, case_number: int) -> int:
    return int(base_seed) + int(case_number) - 1


def validate_count(count: int) -> int:
    if count <= 0:
        raise StressError("count must be greater than 0.")
    return count


def resolve_stress_timeout(timeout: Optional[float], config: dict) -> float:
    value = (runner_timeout(config) or DEFAULT_STRESS_TIMEOUT) if timeout is None else timeout
    if value <= 0:
        raise StressError("timeout must be greater than 0.")
    return float(value)


def _display_path(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def _python_command(config: dict, key: str = "python") -> str:
    default = "pypy" if key == "pypy" else "python"
    command = runner_command(config, key, default)
    executable = resolve_executable(command)
    if key == "pypy" and not executable and command == "pypy":
        executable = resolve_executable("pypy3")
    if key != "pypy" and not executable:
        executable = sys.executable
    if not executable:
        label = "PyPy" if key == "pypy" else "Python"
        raise StressError(f"{label} command not found: {command}.")
    return executable


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise StressError(f"{label} file not found: {path}")


def _prepare_generator(cwd: Path, problem: str, gen: Optional[str], config: dict) -> StressProgram:
    path = (cwd / (gen or f"{problem}_gen.py")).resolve()
    _ensure_file(path, "generator")
    return StressProgram(command=[_python_command(config, "python"), str(path)], path=path)


def _prepare_brute(cwd: Path, problem: str, brute: Optional[str], config: dict) -> StressProgram:
    path = (cwd / (brute or f"{problem}_brute.py")).resolve()
    _ensure_file(path, "brute")
    return StressProgram(command=[_python_command(config, "python"), str(path)], path=path)


def _stress_template_path(cwd: Path, config: dict, name: str) -> Path:
    manifest_path = resolve_template_manifest(config, cwd, required=True)
    manifest = load_template_manifest(manifest_path)
    return resolve_template_name("stress", name, manifest, manifest_path)


def _write_stress_template(target: Path, template_path: Path) -> bool:
    if target.exists():
        warn(f"Warning: already exists: {target}")
        return False
    target.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
    ok(f"created: {target}")
    return True


def cmd_stress_init(problem: str) -> int:
    cwd = Path.cwd()
    config = load_config(cwd)
    problem = normalize_problem(problem)

    try:
        gen_template = _stress_template_path(cwd, config, "gen")
        brute_template = _stress_template_path(cwd, config, "brute")
        _write_stress_template(cwd / f"{problem}_gen.py", gen_template)
        _write_stress_template(cwd / f"{problem}_brute.py", brute_template)
    except TemplateError as e:
        error(f"Error: {e}")
        return 1
    except OSError as e:
        error(f"Error: failed to write stress template: {e}")
        return 1

    return 0


def _validate_promote_name(name: str) -> str:
    normalized = str(name or "").strip()
    if not normalized:
        raise StressError("case name must not be empty.")
    if Path(normalized).name != normalized or Path(normalized).suffix:
        raise StressError("case name must be a simple name without path separators or extension.")
    return normalized


def _next_promote_name(testdir: Path) -> str:
    index = 1
    while True:
        candidate = f"stress-{index}"
        if not (testdir / f"{candidate}.in").exists() and not (testdir / f"{candidate}.out").exists():
            return candidate
        index += 1


def _first_existing(paths: List[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def promote_failed_case(problem: str, *, name: Optional[str] = None, force: bool = False) -> int:
    cwd = Path.cwd()
    problem = normalize_problem(problem)
    stress_dir = cwd / STRESS_DIR / problem
    failed_input = stress_dir / "failed.in"
    brute_output = stress_dir / "brute.out"

    if not failed_input.exists():
        error(f"Error: no failed stress input found for {problem}")
        print_text("Run first:")
        print_text(f"  atc stress {problem}")
        return 1
    if not brute_output.exists():
        error(f"Error: no brute output found for {problem}")
        print_text("Run first:")
        print_text(f"  atc stress {problem}")
        return 1

    testdir = cwd / "tests" / problem
    try:
        case_name = _validate_promote_name(name) if name is not None else _next_promote_name(testdir)
    except StressError as e:
        error(f"Error: {e}")
        return 1

    target_input = testdir / f"{case_name}.in"
    target_output = testdir / f"{case_name}.out"
    existing = _first_existing([target_input, target_output])
    if existing and not force:
        error(f"Error: {_display_path(existing, cwd)} already exists")
        print_text("Use --force to overwrite.")
        return 1

    try:
        input_text = failed_input.read_text(encoding="utf-8")
        expected_text = brute_output.read_text(encoding="utf-8")
        testdir.mkdir(parents=True, exist_ok=True)
        target_input.write_text(input_text, encoding="utf-8")
        target_output.write_text(expected_text, encoding="utf-8")
    except OSError as e:
        error(f"Error: failed to promote stress case: {e}")
        return 1

    print_promote_result(
        problem,
        Path(_display_path(failed_input, cwd)),
        Path(_display_path(brute_output, cwd)),
        Path(_display_path(target_input, cwd)),
        Path(_display_path(target_output, cwd)),
    )
    return 0


def cmd_stress_promote(problem: str, name: Optional[str] = None, force: bool = False) -> int:
    return promote_failed_case(problem, name=name, force=force)


def _compile_cpp_solution(cwd: Path, problem: str, cpp_file: Path, config: dict) -> StressProgram:
    compiler = runner_command(config, "cpp_compiler", "g++")
    compiler_path = resolve_executable(compiler)
    if not compiler_path:
        raise StressError(f"C++ compiler not found: {compiler}")

    stress_dir = cwd / STRESS_DIR / problem
    stress_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if platform.system() == "Windows" else ".out"
    exe_path = stress_dir / f"_{problem}_stress{suffix}"

    warn(f"Compiling {cpp_file.name}...")
    try:
        proc = subprocess.run(
            [compiler_path, *runner_cpp_flags(config), str(cpp_file), "-o", str(exe_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=runner_compile_timeout(config),
        )
    except subprocess.TimeoutExpired:
        raise StressError(f"Compile timed out after {runner_compile_timeout(config)} seconds.")
    except OSError as e:
        raise StressError(str(e))

    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or f"compiler exited with status {proc.returncode}"
        raise StressError(f"Compile failed:\n{message}")

    return StressProgram(command=[str(exe_path)], path=cpp_file, cleanup_path=exe_path)


def _prepare_solution(cwd: Path, problem: str, language: Optional[str], config: dict) -> tuple[str, StressProgram]:
    run_language = normalize_run_language(language, config)
    if not run_language:
        raise StressError("Invalid language. Use py, python, pypy, or cpp.")

    if run_language == "cpp":
        cpp_file = (cwd / f"{problem}.cpp").resolve()
        _ensure_file(cpp_file, "solution")
        return "cpp", _compile_cpp_solution(cwd, problem, cpp_file, config)

    py_file = (cwd / f"{problem}.py").resolve()
    _ensure_file(py_file, "solution")
    python_key = "pypy" if run_language == "pypy" else "python"
    return "py", StressProgram(command=[_python_command(config, python_key), str(py_file)], path=py_file)


def _run_process(command: list, input_text: Optional[str], timeout: float, label: str) -> StressRunOutput:
    run_kwargs = {"stdin": subprocess.DEVNULL} if input_text is None else {"input": input_text}
    try:
        proc = subprocess.run(
            command,
            **run_kwargs,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise StressError(f"{label} timed out after {timeout} seconds.")
    except OSError as e:
        raise StressError(f"{label} failed: {e}")
    return StressRunOutput(stdout=proc.stdout, stderr=proc.stderr, returncode=proc.returncode)


def save_failure(
    cwd: Path,
    problem: str,
    language: str,
    case_number: int,
    base_seed: int,
    seed: int,
    gen_path: Path,
    brute_path: Path,
    solution_path: Path,
    compare: str,
    input_text: str,
    your_output: str,
    brute_output: str,
) -> Path:
    stress_dir = cwd / STRESS_DIR / problem
    stress_dir.mkdir(parents=True, exist_ok=True)

    (stress_dir / "failed.in").write_text(input_text, encoding="utf-8")
    (stress_dir / "your.out").write_text(your_output, encoding="utf-8")
    (stress_dir / "brute.out").write_text(brute_output, encoding="utf-8")
    meta = {
        "problem": problem,
        "language": language,
        "case": case_number,
        "base_seed": base_seed,
        "seed": seed,
        "gen": _display_path(gen_path, cwd),
        "brute": _display_path(brute_path, cwd),
        "solution": _display_path(solution_path, cwd),
        "compare": compare,
    }
    (stress_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stress_dir


def _print_failure(case_number: int, seed: int, input_text: str, your_output: str, brute_output: str, saved_dir: Path) -> None:
    print_stress_failure(
        case_number,
        seed,
        input_text,
        your_output,
        brute_output,
        [saved_dir / name for name in ["failed.in", "your.out", "brute.out", "meta.json"]],
    )


def cmd_stress(
    problem: str,
    language: Optional[str] = None,
    count: int = DEFAULT_STRESS_COUNT,
    seed: Optional[int] = None,
    gen: Optional[str] = None,
    brute: Optional[str] = None,
    timeout: Optional[float] = None,
    compare: str = "strip",
) -> int:
    cwd = Path.cwd()
    config = load_config(cwd)
    problem = normalize_problem(problem)

    try:
        count = validate_count(count)
        compare = normalize_compare_mode(compare)
        timeout = resolve_stress_timeout(timeout, config)
        base_seed = int(seed) if seed is not None else random.randrange(0, 2**31)
        display_language, solution = _prepare_solution(cwd, problem, language, config)
        generator = _prepare_generator(cwd, problem, gen, config)
        brute_program = _prepare_brute(cwd, problem, brute, config)
    except StressError as e:
        error(f"Error: {e}")
        return 1

    print_stress_header(
        problem=problem,
        language=display_language,
        solution=_display_path(solution.path, cwd),
        generator=_display_path(generator.path, cwd),
        brute=_display_path(brute_program.path, cwd),
        count=count,
        seed=base_seed,
        compare=compare,
        timeout=timeout,
    )

    try:
        for case_number in range(1, count + 1):
            case_seed = seed_for_case(base_seed, case_number)
            generated = _run_process([*generator.command, str(case_seed)], None, timeout, "generator")
            if generated.returncode != 0:
                raise StressError(f"generator failed at case {case_number}: {generated.stderr.strip() or generated.stdout.strip()}")

            your = _run_process(solution.command, generated.stdout, timeout, "solution")
            if your.returncode != 0:
                raise StressError(f"solution failed at case {case_number}: {your.stderr.strip() or your.stdout.strip()}")

            brute_output = _run_process(brute_program.command, generated.stdout, timeout, "brute")
            if brute_output.returncode != 0:
                raise StressError(f"brute failed at case {case_number}: {brute_output.stderr.strip() or brute_output.stdout.strip()}")

            if not compare_outputs(your.stdout, brute_output.stdout, compare):
                saved_dir = save_failure(
                    cwd=cwd,
                    problem=problem,
                    language=display_language,
                    case_number=case_number,
                    base_seed=base_seed,
                    seed=case_seed,
                    gen_path=generator.path,
                    brute_path=brute_program.path,
                    solution_path=solution.path,
                    compare=compare,
                    input_text=generated.stdout,
                    your_output=your.stdout,
                    brute_output=brute_output.stdout,
                )
                _print_failure(case_number, case_seed, generated.stdout, your.stdout, brute_output.stdout, saved_dir)
                return 1

            print_text(f"[{case_number}] OK")
    except StressError as e:
        error(f"Error: {e}")
        return 1
    finally:
        if solution.cleanup_path and solution.cleanup_path.exists():
            try:
                solution.cleanup_path.unlink()
            except OSError:
                pass

    print_text()
    ok(f"PASS: all {count} cases matched")
    return 0
