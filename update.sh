#!/usr/bin/env bash
set -euo pipefail

# Apply the current local checkout to an existing macOS installation.
# Updating the Git checkout itself is intentionally the user's responsibility.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
EXT_DIR="$PROJECT_ROOT/vscode/atc-helper"
VSIX_PATH="$EXT_DIR/atc-helper.vsix"
PACKAGE_NAME="atc"
PIPX_CMD=""
PIPX_HOME=""
PIPX_BIN_DIR=""

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

require_pipx_features() {
  local install_help
  if ! install_help="$("$PIPX_CMD" install --help 2>&1)"; then
    die "pipxを実行できません。./install.shを先に実行してください。"
  fi
  if [[ "$install_help" != *"--editable"* \
    || "$install_help" != *"--include-deps"* \
    || "$install_help" != *"--force"* ]]; then
    die "現在のpipxは必要なoptionに対応していません。pipxを更新するか、./install.shを実行してください。"
  fi
}

require_node() {
  require_command "node" "Node.js 20以上をインストールしてください。例: brew install node"
  require_command "npm" "Node.js / npmをインストールしてください。例: brew install node"
  if ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)'; then
    die "VS Code拡張機能のbuildにはNode.js 20以上が必要です。"
  fi
}

log "既存installationを確認しています"
PIPX_CMD="$(find_pipx || true)"
[[ -n "$PIPX_CMD" ]] || die "pipxが見つかりません。./install.shを先に実行してください。"
require_pipx_features
require_node
require_command "code" "VS CodeのCommand Paletteで Shell Command: Install 'code' command in PATH を実行してください。"
[[ -d "$EXT_DIR" ]] || die "VS Code拡張機能ディレクトリが見つかりません: $EXT_DIR"
[[ -f "$EXT_DIR/package-lock.json" ]] || die "package-lock.jsonが見つかりません: $EXT_DIR/package-lock.json"

PIPX_HOME="$("$PIPX_CMD" environment --value PIPX_HOME)"
PIPX_BIN_DIR="$("$PIPX_CMD" environment --value PIPX_BIN_DIR)"
[[ -d "$PIPX_HOME/venvs/$PACKAGE_NAME" ]] || die "pipx管理のatc環境が見つかりません。./install.shを先に実行してください。"
export PATH="$PIPX_BIN_DIR:$PATH"

log "現在のlocal sourceからPython CLI環境を更新しています"
"$PIPX_CMD" install --force --editable --include-deps "$PROJECT_ROOT"

[[ -x "$PIPX_BIN_DIR/atc" ]] || die "pipx application directoryにatcが見つかりません: $PIPX_BIN_DIR"
[[ -x "$PIPX_BIN_DIR/oj" ]] || die "pipx application directoryにojが見つかりません: $PIPX_BIN_DIR"
"$PIPX_BIN_DIR/atc" --help >/dev/null
"$PIPX_BIN_DIR/oj" --help >/dev/null

log "VS Code拡張機能を更新しています"
cd "$EXT_DIR"
npm ci
npm run compile
npm run package -- --out "$VSIX_PATH"

[[ -f "$VSIX_PATH" ]] || die ".vsixファイルが見つかりません: $VSIX_PATH"

log "VS Code拡張機能を再インストールしています"
code --install-extension "$VSIX_PATH" --force

cat <<'EOF'

==> 更新が完了しました

VS CodeでDeveloper: Reload Windowを実行するか、VS Codeを再起動してください。

EOF
