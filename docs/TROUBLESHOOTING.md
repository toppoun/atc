# Troubleshooting

困ったときは、まず診断結果を確認します。

```bash
atc config doctor
```

出力をそのまま共有すると、Python / `oj` / C++ compiler / VS Code 連携 / config / templates / `current-contest.json` のどこで詰まっているか分かりやすくなります。

## `atc` が見つからない

確認:

```bash
which atc
atc config doctor
```

対処:

- `python3 -m pip install -e .` を実行したか確認
- 仮想環境を使っている場合は activate する
- pip の script path が PATH に入っているか確認

## `oj` が見つからない

確認:

```bash
oj --version
```

対処:

```bash
python3 -m pip install online-judge-tools
oj login https://atcoder.jp/
```

## サンプル取得に失敗する

原因候補:

- contest ID が違う
- URL 形式が未対応
- `oj` が未インストール
- AtCoder に未ログイン
- ネットワークエラー
- AtCoder 側のページ構成変更

手動確認:

```bash
oj d https://atcoder.jp/contests/abc335/tasks/abc335_a -d tests/A
```

## `g++` / `clang++` が見つからない

確認:

```bash
clang++ --version
g++ --version
```

macOS では Xcode Command Line Tools を入れてください。

```bash
xcode-select --install
```

使うコンパイラは `.atc/config.toml` の `[runner].cpp_compiler` で変更できます。

## VS Code の `code` コマンドが確認できない

VS Code で Command Palette を開き、次を実行してください。

```text
Shell Command: Install 'code' command in PATH
```

確認:

```bash
code --version
```

`atc config doctor` は VS Code を不用意に開かないため、`code --list-extensions` は自動実行しません。

## VS Code extension が確認できない

`doctor` が extension を確認できない場合でも、未インストールとは断定しません。VS Code の Extensions 画面で `AtC Helper` / `atc-helper` を確認してください。

手動確認:

```bash
code --list-extensions | grep -i atc
```

Windows では:

```powershell
code.cmd --list-extensions | Select-String -Pattern "atc"
```

## VS Code 連携が反応しない

確認:

- VS Code 拡張機能 `atc-helper` がインストールされているか
- VS Code を reload したか
- AtCoder root、またはその配下のフォルダを VS Code で開いているか
- `.atc/current-contest.json` が更新されているか
- `AtC: Open Contest Terminals` が Command Palette に出るか

VS Code 拡張機能は `config.toml` の `[paths]` を読み、`<paths.root>/.atc/current-contest.json` を監視します。

config を変更した場合は `Developer: Reload Window` を実行してください。

## `atc visual` が開かない

まずブラウザを自動で開かず URL だけ確認します。

```bash
atc visual --no-open
```

Live Preview を使わずローカルサーバーだけ確認する場合:

```bash
atc vis --no-live-preview --no-open
```

ローカルサーバーの URL は次の形式です。

```text
http://127.0.0.1:<port>/visualizer.html
```

## Live Preview が使われない

`atc visual` / `atc vis` は、まず VS Code Live Preview の URL を確認します。Live Preview が起動していない、または接続できない場合は、自前のローカルHTTPサーバーに fallback します。

Live Preview を使いたくない場合:

```bash
atc vis --no-live-preview
```

fallback せず Live Preview だけを確認したい場合:

```bash
atc vis --live-preview --no-fallback --no-open
```

## `config.toml` が壊れている

確認:

```bash
atc config doctor
atc config show
```

よくある原因:

- `[` や `]` の閉じ忘れ
- 文字列の quote 忘れ
- 配列の comma 忘れ

直せない場合は、既存ファイルを退避して作り直します。

```bash
mv .atc/config.toml .atc/config.toml.bak
atc config init
```

## template manifest が壊れている

確認:

```bash
atc config doctor
```

よくある原因:

- `manifest.json` が JSON として壊れている
- `[templates] manifest` のパスが間違っている
- `py` / `cpp` に指定したテンプレート名が manifest に無い
- manifest の `path` が存在しないファイルを指している

従来の直接パス指定に戻すこともできます。

```toml
[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"
```

## watch が頻繁に走る

`atc watch` は polling 方式です。

```toml
[watch]
poll_seconds = 0.25
debounce_seconds = 1.5
```

保存を連続で行うエディタ設定や formatter によって、頻繁に再実行されることがあります。

## VS Code 拡張機能を更新したのに反映されない

```bash
cd vscode/atc-helper
npm run compile
npx @vscode/vsce package --allow-missing-repository
code --install-extension ./atc-helper-0.0.1.vsix --force
```

その後、VS Code で `Developer: Reload Window` を実行してください。
