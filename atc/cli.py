import sys
import subprocess
import shutil
import time
from pathlib import Path

# ===== 設定 =====
PROBLEMS = ["A", "B", "C", "D", "E"]
TEMPLATE = """import sys
from collections import deque, defaultdict, Counter
from heapq import heappop, heappush, heapify
from itertools import product, combinations, accumulate, permutations, groupby
from math import sqrt, isqrt, comb, gcd

input = sys.stdin.readline
sys.setrecursionlimit(10**7)

DIR4 = [(1,0),(-1,0),(0,1),(0,-1)]
DIR8 = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

INF = 10**18
YES,NO = "Yes", "No"

def ni(): return int(input())
def nm(): return map(int,input().split())
def nl(): return list(nm())

def si(): return input().strip()
def sm(): return si().split()
def sl(): return list(si())


def main():
    n = ni()
    a = nl()

    print()

if __name__ == '__main__':
    main()"""
# =================
RED   = "\033[31m"
GREEN = "\033[32m"
YELLOW= "\033[33m"
RESET = "\033[0m"


# ---------- interpreter ----------

def detect_pypy():
    for name in ["pypy3", "pypy"]:
        path = shutil.which(name)
        if path:
            return path
    return None


# ---------- usage ----------

def usage():
    print("使い方:")
    print("  atc new abc413")
    print("  atc run A [python|pypy]")
    sys.exit(1)

# ---------- new ----------
def cmd_new(contest: str):
    base = Path(contest)
    tests = base / "tests"
    tmp = base / ".oj_tmp"

    base.mkdir(exist_ok=True)
    tests.mkdir(exist_ok=True)

    # A.py ~ E.py
    for p in PROBLEMS:
        py = base / f"{p}.py"
        if not py.exists():
            py.write_text(TEMPLATE, encoding="utf-8")

    # サンプル取得
    for p in PROBLEMS:
        print(f"fetching {p} ...")
        url = f"https://atcoder.jp/contests/{contest}/tasks/{contest}_{p.lower()}"
        dst = tests / p

        shutil.rmtree(tmp, ignore_errors=True)

        subprocess.run(
            ["oj", "d", url, "-d", str(tmp)],
            check=True
        )

        dst.mkdir(parents=True, exist_ok=True)
        for f in tmp.iterdir():
            shutil.move(str(f), dst / f.name)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{contest} ready.")

# ---------- run ----------
def cmd_run(problem: str, interpreter="python"):
    cwd = Path.cwd()
    py = cwd / f"{problem}.py"
    testdir = cwd / "tests" / problem

    if interpreter == "pypy":
        exe = detect_pypy()
        if exe is None:
            print("PyPy が見つからない")
            sys.exit(1)
    else:
        exe = sys.executable

    if not py.exists():
        print(f"{py} が見つからない")
        sys.exit(1)

    if not testdir.exists():
        print(f"{testdir} が見つからない")
        sys.exit(1)

    ins = sorted(testdir.glob("*.in"))
    if not ins:
        print("テストケースが存在しない")
        sys.exit(1)

    ok = 0
    total = len(ins)

    for infile in ins:
        outfile = infile.with_suffix(".out")
        print(f"=== {infile.name} ===")

        with open(infile, "r", encoding="utf-8") as fin:
            start = time.perf_counter()

            proc = subprocess.run(
                [exe, py],
                stdin=fin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            end = time.perf_counter()
            elapsed = end - start

        # ランタイムエラー
        if proc.returncode != 0:
            print(f" {RED}RE{RESET}")
            print(f" {YELLOW}stderr:{RESET}")
            print(proc.stderr.strip())
            print(f" time: {elapsed*1000:.2f} ms")
            continue

        out = proc.stdout.strip()

        if not outfile.exists():
            print(" expected: (なし)")
            print(" output:")
            print(out)
            print(f" time: {elapsed*1000:.2f} ms")
            continue

        exp = outfile.read_text(encoding="utf-8").strip()

        if out == exp:
            print(f" {GREEN}AC{RESET}")
            ok += 1
        else:
            print(f" {RED}WA{RESET}")
            print(" expected:")
            print(exp)
            print(" output:")
            print(out)

        print(f" time: {elapsed*1000:.2f} ms")

    print(f"\n結果: {ok}/{total} AC")

# ---------- main ----------
def main():
    if len(sys.argv) < 2:
        usage()

    cmd = sys.argv[1]

    if cmd == "new" and len(sys.argv) == 3:
        cmd_new(sys.argv[2])
    elif (cmd in ["test", "t", "run"]) and len(sys.argv) >= 3:
        interpreter = sys.argv[3] if len(sys.argv) == 4 else "python"
        cmd_run(sys.argv[2], interpreter)
    else:
        usage()

if __name__ == "__main__":
    main()
