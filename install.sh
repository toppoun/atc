#!/usr/bin/env bash
set -euo pipefail

# macOS helper installer for the atc Python CLI and local VS Code extension.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
EXT_DIR="$PROJECT_ROOT/vscode/atc-helper"
VSIX_PATH="$EXT_DIR/atc-helper.vsix"
PIPX_CMD=""
PIPX_BIN_DIR=""
BOOTSTRAP_DIR=""

log() {
  printf '\n==> %s\n' "$1"
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

find_pipx() {
  if has_command "pipx"; then
    command -v pipx
  elif [[ -x "$HOME/.local/bin/pipx" ]]; then
    printf '%s\n' "$HOME/.local/bin/pipx"
  else
    return 1
  fi
}

find_bootstrap_python() {
  local candidate
  for candidate in python3 python; do
    if has_command "$candidate" \
      && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1 \
      && "$candidate" -m venv --help >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

cleanup_bootstrap() {
  if [[ -n "$BOOTSTRAP_DIR" && -d "$BOOTSTRAP_DIR" ]]; then
    rm -rf "$BOOTSTRAP_DIR"
  fi
}

require_pipx_features() {
  local install_help
  local ensurepath_help
  if ! install_help="$("$PIPX_CMD" install --help 2>&1)"; then
    die "pipx を実行できません。pipx installationを確認してください: $PIPX_CMD"
  fi
  if [[ "$install_help" != *"--backend"* \
    || "$install_help" != *"--python"* \
    || "$install_help" != *"--fetch-python"* \
    || "$install_help" != *"--editable"* \
    || "$install_help" != *"--include-resources-from"* \
    || "$install_help" != *"--force"* ]]; then
    die "現在のpipxは必要なoptionに対応していません。pipxを更新してから再実行してください。"
  fi
  if ! ensurepath_help="$("$PIPX_CMD" ensurepath --help 2>&1)" \
    || [[ "$ensurepath_help" != *"--prepend"* ]]; then
    die "現在のpipxはensurepath --prependに対応していません。pipxを更新してから再実行してください。"
  fi
}

bootstrap_pipx() {
  local python_cmd
  local bootstrap_pipx
  if ! python_cmd="$(find_bootstrap_python)"; then
    die "pipxの導入にはvenvを利用できるPython 3.10以上が必要です。python3またはpythonを用意してください。"
  fi

  BOOTSTRAP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/atc-pipx-bootstrap.XXXXXX")"
  trap cleanup_bootstrap EXIT

  log "専用の一時venvからpipxをbootstrapしています ($python_cmd)"
  "$python_cmd" -m venv "$BOOTSTRAP_DIR"
  "$BOOTSTRAP_DIR/bin/python" -m pip install pipx
  bootstrap_pipx="$BOOTSTRAP_DIR/bin/pipx"
  "$bootstrap_pipx" install pipx
  "$bootstrap_pipx" ensurepath --prepend

  PIPX_BIN_DIR="$("$bootstrap_pipx" environment --value PIPX_BIN_DIR)"
  PIPX_CMD="$PIPX_BIN_DIR/pipx"
  [[ -x "$PIPX_CMD" ]] || die "bootstrapしたpipx executableが見つかりません: $PIPX_CMD"
}

ensure_pipx() {
  PIPX_CMD="$(find_pipx || true)"
  if [[ -z "$PIPX_CMD" ]]; then
    if has_command "brew"; then
      log "Homebrewでpipxをインストールしています"
      brew install pipx
      PIPX_CMD="$(find_pipx || true)"
      [[ -n "$PIPX_CMD" ]] || die "brew install後もpipxが見つかりません。HomebrewのPATHを確認してください。"
    else
      bootstrap_pipx
    fi
  fi

  require_pipx_features
  if [[ -z "$PIPX_BIN_DIR" ]]; then
    PIPX_BIN_DIR="$("$PIPX_CMD" environment --value PIPX_BIN_DIR)"
  fi
  [[ -n "$PIPX_BIN_DIR" ]] || die "pipx application directoryを取得できません。"

  "$PIPX_CMD" ensurepath --prepend
  export PATH="$PIPX_BIN_DIR:$PATH"
}

ensure_uv() {
  if has_command "uv"; then
    return 0
  fi
  if has_command "brew"; then
    log "Homebrewでuvをインストールしています"
    brew install uv
    has_command "uv" || die "brew install後もuvが見つかりません。HomebrewのPATHを確認してください。"
    return 0
  fi
  die "uvが見つかりません。Homebrewがない場合はuvを安全にインストールしてPATHに追加してから再実行してください。"
}

require_node() {
  require_command "node" "Node.js 22以上をインストールしてください。例: brew install node"
  require_command "npm" "Node.js / npmをインストールしてください。例: brew install node"
  if ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)'; then
    die "VS Code拡張機能のbuildにはNode.js 22以上が必要です。"
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

log "必要なコマンドを確認しています"
require_node
require_command "code" "VS CodeのCommand Paletteで Shell Command: Install 'code' command in PATH を実行してください。"
[[ -d "$EXT_DIR" ]] || die "VS Code拡張機能ディレクトリが見つかりません: $EXT_DIR"
[[ -f "$EXT_DIR/package-lock.json" ]] || die "package-lock.jsonが見つかりません: $EXT_DIR/package-lock.json"

log "pipxを確認しています"
ensure_pipx

log "uvを確認しています"
ensure_uv

log "Python CLIをstandalone Python 3.11のpipx環境へインストールしています"
"$PIPX_CMD" install \
  --backend uv \
  --python 3.11 \
  --fetch-python=always \
  --force \
  --editable \
  --include-resources-from online-judge-tools \
  "$PROJECT_ROOT"

[[ -x "$PIPX_BIN_DIR/atc" ]] || die "pipx application directoryにatcが見つかりません: $PIPX_BIN_DIR"
[[ -x "$PIPX_BIN_DIR/oj" ]] || die "pipx application directoryにojが見つかりません: $PIPX_BIN_DIR"
"$PIPX_BIN_DIR/atc" --help >/dev/null
"$PIPX_BIN_DIR/oj" --help >/dev/null

log "VS Code拡張機能をビルドしています"
cd "$EXT_DIR"
npm ci
npm run compile
npm run package -- --out "$VSIX_PATH"

[[ -f "$VSIX_PATH" ]] || die ".vsixファイルが見つかりません: $VSIX_PATH"

log "VS Code拡張機能をインストールしています"
code --install-extension "$VSIX_PATH" --force

log "doctorチェック"
doctor_command "atc" "atc CLI" "新しいterminalを開き、pipx ensurepath --prependの変更を反映してください。"
doctor_command "oj" "online-judge-tools" "新しいterminalを開き、pipx ensurepath --prependの変更を反映してください。"

if has_command "clang++"; then
  printf '[OK] C++ compiler: %s\n' "$(command -v clang++)"
elif has_command "g++"; then
  printf '[OK] C++ compiler: %s\n' "$(command -v g++)"
else
  printf '[WARN] C++ compiler: not found\n'
  printf '       C++を使う場合はXcode Command Line Toolsを入れてください: xcode-select --install\n'
fi

doctor_command "pypy3" "pypy3" "PyPyを使う場合だけ必要です。例: brew install pypy3"

cat <<EOF

==> インストールが完了しました

pipxのPATH設定を確実に反映するため、新しいterminalを開いてください。
pipx版atc/ojは次のdirectoryにあります: $PIPX_BIN_DIR
VS Code連携を使う場合は、Developer: Reload Windowを実行するか、VS Codeを再起動してください。

次に試すコマンド:

  atc --help
  oj --help
  atc config init
  atc contest abc335 cpp

EOF
