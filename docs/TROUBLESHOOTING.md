# Troubleshooting

困ったときの確認ポイントです。

## `atc` が見つからない

確認:

```bash
which atc
atc config show
```

対処:

- `python3 -m pip install -e .` を実行したか確認
- 仮想環境を使っている場合は activate する
- pip の script path が PATH に入っているか確認

macOS の user install では、次のような場所が PATH に必要なことがあります。

```bash
python3 -m site --user-base
```

出力されたパスの `bin` を PATH に追加してください。

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

## VS Code の `code` コマンドが見つからない

VS Code で Command Palette を開き、次を実行してください。

```text
Shell Command: Install 'code' command in PATH
```

確認:

```bash
code --version
```

## `config.toml` が壊れている

確認:

```bash
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

## VS Code 連携が反応しない

確認:

- VS Code 拡張機能 `atc-helper` がインストールされているか
- VS Code を reload したか
- AtCoder root、またはその配下のフォルダを VS Code で開いているか
- `.atc/current-contest.json` が更新されているか
- `AtC: Open Contest Terminals` が Command Palette に出るか

VS Code 拡張機能は `config.toml` の `[paths]` を読み、`<paths.root>/.atc/current-contest.json` を監視します。

config を変更した場合は `Developer: Reload Window` を実行してください。

## watch が頻繁に走る

`atc watch` は polling 方式です。

現在の値:

```text
WATCH_POLL_SECONDS = 0.25
WATCH_DEBOUNCE_SECONDS = 1.5
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
