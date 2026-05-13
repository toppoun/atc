#!/usr/bin/env bash
set -euo pipefail

# Uninstall the atc Python CLI and local VS Code extension.
# User data such as .atc/config.toml and contest folders is intentionally kept.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

log() {
  printf '\n==> %s\n' "$1"
}

warn() {
  printf '\n[WARN] %s\n' "$1" >&2
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

read_package_name() {
  python3 - "$PROJECT_ROOT/pyproject.toml" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r'(?m)^name\s*=\s*"([^"]+)"', text)
print(match.group(1) if match else "atc")
PY
}

read_extension_id() {
  python3 - "$PROJECT_ROOT/vscode/atc-helper/package.json" <<'PY'
import json
import sys
from pathlib import Path

package_json = Path(sys.argv[1])
data = json.loads(package_json.read_text(encoding="utf-8"))
print(f"{data.get('publisher', 'kouki')}.{data.get('name', 'atc-helper')}")
PY
}

PACKAGE_NAME="atc"
EXTENSION_ID="kouki.atc-helper"

if has_command "python3"; then
  PACKAGE_NAME="$(read_package_name)"
  EXTENSION_ID="$(read_extension_id)"
else
  warn "python3 が見つからないため、既定値で削除を試します: package=$PACKAGE_NAME extension=$EXTENSION_ID"
fi

log "VS Code 拡張機能をアンインストールしています"
if has_command "code"; then
  if code --uninstall-extension "$EXTENSION_ID"; then
    printf 'VS Code extension removed: %s\n' "$EXTENSION_ID"
  else
    warn "VS Code 拡張機能のアンインストールに失敗しました。未インストールの可能性もあります。"
  fi
else
  warn "code コマンドが見つかりません。VS Code の Extensions から $EXTENSION_ID を手動で削除してください。"
fi

log "Python CLI をアンインストールしています"
if has_command "python3"; then
  if python3 -m pip uninstall -y "$PACKAGE_NAME"; then
    printf 'Python package removed: %s\n' "$PACKAGE_NAME"
  else
    warn "Python パッケージのアンインストールに失敗しました。pip 環境を確認してください。"
  fi
else
  warn "python3 が見つからないため、Python CLI のアンインストールをスキップしました。"
fi

cat <<'EOF'

==> アンインストールが完了しました

以下はユーザーデータなので削除していません。

  .atc/config.toml
  .atc/current-contest.json
  .atc/test-runs/
  各 contest フォルダ
  templates/

不要な場合だけ、手動で削除してください。

EOF
