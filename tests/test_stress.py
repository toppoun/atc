import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from atc.stress import (
    StressError,
    compare_outputs,
    resolve_stress_timeout,
    save_failure,
    seed_for_case,
    validate_count,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "atc.cli", *args],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _assert_no_traceback(proc: subprocess.CompletedProcess) -> None:
    assert "Traceback" not in proc.stdout + proc.stderr


def _write_stress_files(cwd: Path, solution: str, brute: str) -> None:
    (cwd / "A_gen.py").write_text(
        "\n".join(
            [
                "import random",
                "import sys",
                "seed = int(sys.argv[1])",
                "random.seed(seed)",
                "print(random.randint(1, 5))",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (cwd / "A.py").write_text(solution, encoding="utf-8")
    (cwd / "A_brute.py").write_text(brute, encoding="utf-8")


def test_compare_outputs_modes():
    assert compare_outputs("hello\n", "hello\n", "exact") is True
    assert compare_outputs("hello\n", "hello", "exact") is False
    assert compare_outputs(" hello\n", "hello\n\n", "strip") is True
    assert compare_outputs("1  2\n3", "1 2 3\n", "tokens") is True


def test_compare_outputs_invalid_mode():
    with pytest.raises(StressError):
        compare_outputs("a", "a", "bad")


def test_seed_for_case_is_base_seed_plus_index():
    assert seed_for_case(42, 1) == 42
    assert seed_for_case(42, 3) == 44


def test_validate_count_rejects_non_positive_values():
    assert validate_count(1) == 1
    with pytest.raises(StressError):
        validate_count(0)


def test_resolve_stress_timeout_rejects_non_positive_values():
    config = {"runner": {"timeout_seconds": 2.0}}

    assert resolve_stress_timeout(None, config) == 2.0
    assert resolve_stress_timeout(1.5, config) == 1.5
    with pytest.raises(StressError):
        resolve_stress_timeout(0, config)


def test_save_failure_writes_files_and_meta(tmp_path):
    saved_dir = save_failure(
        cwd=tmp_path,
        problem="A",
        language="py",
        case_number=2,
        base_seed=10,
        seed=11,
        gen_path=tmp_path / "A_gen.py",
        brute_path=tmp_path / "A_brute.py",
        solution_path=tmp_path / "A.py",
        compare="strip",
        input_text="3\n",
        your_output="4\n",
        brute_output="6\n",
    )

    assert (saved_dir / "failed.in").read_text(encoding="utf-8") == "3\n"
    assert (saved_dir / "your.out").read_text(encoding="utf-8") == "4\n"
    assert (saved_dir / "brute.out").read_text(encoding="utf-8") == "6\n"
    meta = json.loads((saved_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["problem"] == "A"
    assert meta["case"] == 2
    assert meta["seed"] == 11
    assert meta["gen"] == "A_gen.py"


def test_cli_stress_ac_flow(tmp_path):
    _write_stress_files(
        tmp_path,
        solution="n = int(input())\nprint(n * n)\n",
        brute="n = int(input())\nprint(n * n)\n",
    )

    result = _run_cli(tmp_path, "stress", "A", "py", "--count", "3", "--seed", "1")

    _assert_no_traceback(result)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "PASS" in result.stdout
    assert "all 3 cases matched" in result.stdout


def test_cli_stress_wa_flow_saves_failure(tmp_path):
    _write_stress_files(
        tmp_path,
        solution="n = int(input())\nprint(n)\n",
        brute="n = int(input())\nprint(n + 1)\n",
    )

    result = _run_cli(tmp_path, "stress", "A", "py", "--count", "3", "--seed", "1")

    _assert_no_traceback(result)
    assert result.returncode == 1
    assert "WA found" in result.stdout

    stress_dir = tmp_path / ".atc" / "stress" / "A"
    assert (stress_dir / "failed.in").is_file()
    assert (stress_dir / "your.out").is_file()
    assert (stress_dir / "brute.out").is_file()
    meta = json.loads((stress_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["problem"] == "A"
    assert meta["language"] == "py"
    assert meta["case"] == 1
    assert meta["base_seed"] == 1
    assert meta["seed"] == 1


def test_cli_stress_missing_generator_reports_error(tmp_path):
    (tmp_path / "A.py").write_text("print(input())\n", encoding="utf-8")
    (tmp_path / "A_brute.py").write_text("print(input())\n", encoding="utf-8")

    result = _run_cli(tmp_path, "stress", "A", "py")

    _assert_no_traceback(result)
    assert result.returncode == 1
    assert "Error" in result.stdout
    assert "generator" in result.stdout


def test_cli_stress_rejects_invalid_arguments(tmp_path):
    _write_stress_files(
        tmp_path,
        solution="print(input())\n",
        brute="print(input())\n",
    )
    cases = [
        ("stress", "A", "py", "--compare", "bad"),
        ("stress", "A", "py", "--count", "0"),
        ("stress", "A", "py", "--timeout", "0"),
    ]

    for args in cases:
        result = _run_cli(tmp_path, *args)
        _assert_no_traceback(result)
        assert result.returncode == 1
        assert "Error" in result.stdout or "使い方" in result.stdout
