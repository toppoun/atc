#!/usr/bin/env bash
set -euo pipefail

# Uninstall only the atc pipx environment and local VS Code extension.
# User data such as .atc/config.toml and contest folders is intentionally kept.

PACKAGE_NAME="atc"
EXTENSION_ID="kouki.atc-helper"
PIPX_CMD=""

log() {
  printf '\n==> %s\n' "$1"
}

warn() {
  printf '\n[WARN] %s\n' "$1" >&2
}

has_command() {
  command -v "$1" >/dev/null 2>&1
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

log "VS Code拡張機能をアンインストールしています"
if has_command "code"; then
  if INSTALLED_EXTENSIONS="$(code --list-extensions 2>/dev/null)"; then
    if grep -Fxiq "$EXTENSION_ID" <<< "$INSTALLED_EXTENSIONS"; then
      if code --uninstall-extension "$EXTENSION_ID"; then
        printf 'VS Code extension removed: %s\n' "$EXTENSION_ID"
      else
        warn "VS Code拡張機能のアンインストールに失敗しました: $EXTENSION_ID"
      fi
    else
      printf 'VS Code extension is not installed; skip: %s\n' "$EXTENSION_ID"
    fi
  else
    warn "installed extensionの確認に失敗したため、$EXTENSION_IDの削除を試します。"
    if code --uninstall-extension "$EXTENSION_ID"; then
      printf 'VS Code extension removed: %s\n' "$EXTENSION_ID"
    else
      warn "VS Code拡張機能のアンインストールに失敗しました: $EXTENSION_ID"
    fi
  fi
else
  warn "codeコマンドが見つかりません。VS CodeのExtensionsから$EXTENSION_IDを手動で削除してください。"
fi

log "Python CLIをアンインストールしています"
PIPX_CMD="$(find_pipx || true)"
if [[ -n "$PIPX_CMD" ]]; then
  PIPX_HOME="$("$PIPX_CMD" environment --value PIPX_HOME 2>/dev/null || true)"
  if [[ -n "$PIPX_HOME" && ! -d "$PIPX_HOME/venvs/$PACKAGE_NAME" ]]; then
    printf 'pipx package is not installed; skip: %s\n' "$PACKAGE_NAME"
  elif "$PIPX_CMD" uninstall "$PACKAGE_NAME"; then
    printf 'pipx package removed: %s\n' "$PACKAGE_NAME"
  else
    warn "pipx packageのアンインストールに失敗しました: $PACKAGE_NAME"
  fi
else
  warn "pipxが見つからないため、atcのpipx環境を削除できませんでした。pipx自体は削除しません。"
fi

cat <<'EOF'

==> アンインストール処理が完了しました

以下はユーザーデータなので削除していません。

  .atc/config.toml
  .atc/current-contest.json
  .atc/test-runs/
  各contestフォルダ
  templates/

不要な場合だけ、手動で削除してください。
pipx、Homebrew、Python、Node.js、npm、VS Code自体は削除していません。

EOF
