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
MOD = 10**9 + 7
MOD2  = 998244353

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
    print("  atc manual A B C (または atc manual A~E)")
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

# ---------- manual ----------
def cmd_manual(args):
    cwd = Path.cwd()
    targets = []

    for arg in args:
        # "A~E" や "A-E" のような範囲指定を展開
        if "~" in arg or "-" in arg:
            sep = "~" if "~" in arg else "-"
            parts = arg.split(sep)
            if len(parts) == 2 and len(parts[0]) == 1 and len(parts[1]) == 1:
                start, end = ord(parts[0]), ord(parts[1])
                if start <= end:
                    for c in range(start, end + 1):
                        targets.append(chr(c))
                    continue
        # 通常の指定（"A" など）
        targets.append(arg)

    if not targets:
        print("作成するファイル名を指定してください。(例: A B C または A~E)")
        sys.exit(1)

    for p in targets:
        py = cwd / f"{p}.py"
        if not py.exists():
            py.write_text(TEMPLATE, encoding="utf-8")
            print(f" {GREEN}Created{RESET}: {py.name}")
        else:
            print(f" {YELLOW}Skipped{RESET}: {py.name} (すでに存在します)")

# ---------- manual tests ----------
def cmd_manual_tests(contest: str = None):
    cwd = Path.cwd()
    
    # 引数がない場合はカレントディレクトリ名を利用
    if not contest:
        contest = cwd.name
        print(f"{YELLOW}コンテスト名が指定されなかったため、フォルダ名 '{contest}' を使用します。{RESET}")

    tests = cwd / "tests"
    tmp = cwd / ".oj_tmp"

    tests.mkdir(exist_ok=True)

    for p in PROBLEMS:
        print(f"fetching {p} ...")
        url = f"https://atcoder.jp/contests/{contest}/tasks/{contest}_{p.lower()}"
        dst = tests / p

        # 既にテストケースがある場合はスキップ
        if dst.exists() and any(dst.iterdir()):
            print(f"  {YELLOW}Skipped{RESET}: tests/{p} (すでに存在します)")
            continue

        shutil.rmtree(tmp, ignore_errors=True)

        try:
            # ojコマンドを実行。不要なエラー出力で画面が埋まらないようにstderrをキャプチャ
            subprocess.run(
                ["oj", "d", url, "-d", str(tmp)],
                check=True,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            print(f"  {RED}Failed{RESET}: {p} のテストが見つかりませんでした。(URL: {url})")
            continue

        dst.mkdir(parents=True, exist_ok=True)
        for f in tmp.iterdir():
            shutil.move(str(f), dst / f.name)
        
        print(f"  {GREEN}Success{RESET}: tests/{p}")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"テストケースの準備が完了しました。")
    
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
    elif cmd == "manual" and len(sys.argv) >= 3:
            # manual tests の場合
            if sys.argv[2] == "tests":
                contest_name = sys.argv[3] if len(sys.argv) >= 4 else None
                cmd_manual_tests(contest_name)
            # manual A~E などの場合
            else:
                cmd_manual(sys.argv[2:])
    else:
        usage()

if __name__ == "__main__":
    main()
