import sys
import shutil
from pathlib import Path

try:
    from .config import (
        CONFIG_FILE_NAME,
        _config_to_toml,
        _default_config,
        _find_config_file,
        load_config,
    )
    from .console import error, warn
    from .contest import cmd_contest, cmd_new
    from .doctor import cmd_config_doctor
    from .manual import cmd_manual, cmd_manual_tests
    from .runner import cmd_rerun, cmd_run, cmd_run_all
    from .watch import cmd_watch
except ImportError:
    from config import (
        CONFIG_FILE_NAME,
        _config_to_toml,
        _default_config,
        _find_config_file,
        load_config,
    )
    from console import error, warn
    from contest import cmd_contest, cmd_new
    from doctor import cmd_config_doctor
    from manual import cmd_manual, cmd_manual_tests
    from runner import cmd_rerun, cmd_run, cmd_run_all
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
