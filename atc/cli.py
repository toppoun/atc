import sys
import shutil

try:
    from .commands import USAGE_ERROR, resolve_command, usage_lines
except ImportError:
    from commands import USAGE_ERROR, resolve_command, usage_lines

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
    for line in usage_lines():
        print(f"  {line}")
    sys.exit(1)

# ---------- main ----------
def main():
    if len(sys.argv) < 2:
        usage()
    spec = resolve_command(sys.argv[1])
    if not spec:
        usage()

    result = spec.handler(sys.argv[2:])
    if result is USAGE_ERROR:
        usage()
    if result is not None:
        sys.exit(result)

if __name__ == "__main__":
    main()
