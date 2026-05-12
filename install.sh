#!/usr/bin/env bash
set -euo pipefail

# macOS helper installer for the atc Python CLI and local VS Code extension.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
EXT_DIR="$PROJECT_ROOT/vscode/atc-helper"

log() {
  printf '\n==> %s\n' "$1"
}

warn() {
  printf '\n[WARN] %s\n' "$1" >&2
}

die() {
  printf '\n[ERROR] %s\n' "$1" >&2
  exit 1
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

require_command() {
  local cmd="$1"
  local hint="$2"
  if ! has_command "$cmd"; then
    die "$cmd が見つかりません。$hint"
  fi
}

require_python_pip() {
  require_command "python3" "Python 公式サイト、または Homebrew でインストールしてください: brew install python"
  if ! python3 -m pip --version >/dev/null 2>&1; then
    die "pip が使えません。python3 -m ensurepip --upgrade または Python の再インストールを試してください。"
  fi
  if ! has_command "pip" && ! has_command "pip3"; then
    warn "pip / pip3 コマンドは PATH にありませんが、python3 -m pip は使えるため続行します。"
  fi
}

latest_vsix() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

directory = Path(sys.argv[1])
files = sorted(directory.glob("*.vsix"), key=lambda p: p.stat().st_mtime, reverse=True)
if not files:
    raise SystemExit(1)
print(files[0])
PY
}

show_path_hint() {
  local user_base
  user_base="$(python3 -m site --user-base 2>/dev/null || true)"
  warn "atc コマンドが PATH から見つかりません。"
  if [[ -n "$user_base" ]]; then
    warn "pip の script path が PATH に入っていない可能性があります: $user_base/bin"
    warn "例: echo 'export PATH=\"$user_base/bin:\$PATH\"' >> ~/.zshrc"
  fi
}

doctor_command() {
  local cmd="$1"
  local label="$2"
  local hint="$3"
  if has_command "$cmd"; then
    printf '[OK] %s: %s\n' "$label" "$(command -v "$cmd")"
  else
    printf '[WARN] %s: not found\n' "$label"
    printf '       %s\n' "$hint"
  fi
}

install_python_cli() {
  if ! python3 -m pip install -e .; then
    die "Python CLI のインストールに失敗しました。pip のエラー内容を確認してください。Homebrew Python で externally-managed-environment と表示される場合は、仮想環境を有効化してから再実行してください。"
  fi
}

log "必要なコマンドを確認しています"
require_python_pip
require_command "node" "Node.js / npm をインストールしてください: brew install node"
require_command "npm" "Node.js / npm をインストールしてください: brew install node"
require_command "code" "VS Code の Command Palette で Shell Command: Install 'code' command in PATH を実行してください。"
require_command "git" "Git をインストールしてください: xcode-select --install または brew install git"

[[ -d "$EXT_DIR" ]] || die "VS Code 拡張機能ディレクトリが見つかりません: $EXT_DIR"

log "Python CLI をインストールしています"
cd "$PROJECT_ROOT"
install_python_cli

log "atc コマンドを確認しています"
if has_command "atc"; then
  atc config show
else
  show_path_hint
fi

log "VS Code 拡張機能をビルドしています"
cd "$EXT_DIR"
npm install
npm run compile
npx @vscode/vsce package --allow-missing-repository

VSIX_PATH="$(latest_vsix "$EXT_DIR")" || die ".vsix ファイルが見つかりません。vsce package の結果を確認してください。"

log "VS Code 拡張機能をインストールしています"
code --install-extension "$VSIX_PATH" --force

log "doctor チェック"
doctor_command "atc" "atc CLI" "pip の script path を PATH に追加してください。"
doctor_command "oj" "online-judge-tools" "python3 -m pip install online-judge-tools"

if has_command "clang++"; then
  printf '[OK] C++ compiler: %s\n' "$(command -v clang++)"
elif has_command "g++"; then
  printf '[OK] C++ compiler: %s\n' "$(command -v g++)"
else
  printf '[WARN] C++ compiler: not found\n'
  printf '       C++ を使う場合は Xcode Command Line Tools を入れてください: xcode-select --install\n'
fi

doctor_command "pypy3" "pypy3" "PyPy を使う場合だけ必要です。例: brew install pypy3"

cat <<'EOF'

==> インストールが完了しました

VS Code 連携を使う場合は、VS Code で Developer: Reload Window を実行するか、VS Code を再起動してください。
AtCoder 用の root ディレクトリ、または .atc/current-contest.json が作られる project root を VS Code で開くのがおすすめです。

次に試すコマンド:

  atc config init
  atc contest abc335 cpp

EOF
