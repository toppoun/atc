import sys
import subprocess
import shutil
import time
import platform
from pathlib import Path

# ===== 設定 =====
PROBLEMS = ["A", "B", "C", "D", "E"]
TEMPLATE_DIR = Path(__file__).parent / "templates"

# =================
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

# ---------- 共通・補助関数 ----------

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
    print("  atc manual A B C")
    print("  atc manual tests [contest_id]")
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

# ---------- run ----------
def cmd_run(problem: str, interpreter="python"):
    cwd = Path.cwd()
    py_file = cwd / f"{problem}.py"
    cpp_file = cwd / f"{problem}.cpp"
    testdir = cwd / "tests" / problem

    # 言語判定と実行ファイルの準備
    if cpp_file.exists():
        mode = "cpp"
        suffix = ".exe" if platform.system() == "Windows" else ".out"
        exe_path = cwd / f"_{problem}{suffix}"
        
        print(f"{YELLOW}Compiling {cpp_file.name}...{RESET}")
        c_proc = subprocess.run(["g++", "-O2", str(cpp_file), "-o", str(exe_path)], stderr=subprocess.PIPE, text=True)
        if c_proc.returncode != 0:
            print(f"{RED}CE{RESET}\n{c_proc.stderr.strip()}")
            sys.exit(1)
        run_cmd = [str(exe_path)]
    elif py_file.exists():
        mode = "py"
        exe = sys.executable if interpreter != "pypy" else detect_pypy()
        run_cmd = [exe, str(py_file)]
    else:
        print(f"{RED}ファイルが見つかりません。{RESET}")
        sys.exit(1)

    # テスト実行
    ins = sorted(testdir.glob("*.in")) if testdir.exists() else []
    if not ins:
        print(f"{RED}テストケースがありません。{RESET}")
        sys.exit(1)

    ok = 0
    for infile in ins:
        outfile = infile.with_suffix(".out")
        with open(infile, "r") as fin:
            start = time.perf_counter()
            proc = subprocess.run(run_cmd, stdin=fin, capture_output=True, text=True)
            elapsed = (time.perf_counter() - start) * 1000

        print(f"=== {infile.name} ===")
        if proc.returncode != 0:
            print(f" {RED}RE{RESET}\n{proc.stderr.strip()}")
        else:
            out = proc.stdout.strip()
            exp = outfile.read_text().strip() if outfile.exists() else None
            if out == exp:
                print(f" {GREEN}AC{RESET}"); ok += 1
            else:
                print(f" {RED}WA{RESET}\n expected:\n{exp}\n output:\n{out}")
        print(f" time: {elapsed:.2f} ms")

    if mode == "cpp" and exe_path.exists(): exe_path.unlink()
    print(f"\n結果: {ok}/{len(ins)} AC")

# ---------- main ----------
def main():
    if len(sys.argv) < 2: usage()
    cmd = sys.argv[1]

    if cmd == "new" and len(sys.argv) >= 3:
        lang = sys.argv[3] if len(sys.argv) == 4 else "cpp"
        cmd_new(sys.argv[2], lang)
    elif cmd in ["run", "r", "test", "t"] and len(sys.argv) >= 3:
        interp = sys.argv[3] if len(sys.argv) == 4 else "python"
        cmd_run(sys.argv[2], interp)
    elif cmd == "manual":
        if len(sys.argv) >= 3 and sys.argv[2] == "tests":
            from_folder = sys.argv[3] if len(sys.argv) >= 4 else None
            # 前述の manual_tests 関数を呼び出し（省略）
        else:
            cmd_manual(sys.argv[2:])
    else:
        usage()

if __name__ == "__main__":
    main()