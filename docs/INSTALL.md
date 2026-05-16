# Install

macOS 向けの導入手順です。Windows 用 `install.ps1` はありません。

## 必要なもの

- macOS
- Python 3
- Git
- Node.js / npm
- VS Code
- VS Code の `code` コマンド
- C++ を使う場合は Xcode Command Line Tools

`install.sh` は Python CLI と VS Code 拡張機能をまとめて入れます。`online-judge-tools` は Python package dependency として入ります。

## 最短手順

```bash
git clone <repo>
cd <repo>
chmod +x install.sh update.sh uninstall.sh
./install.sh
```

`install.sh` が行うこと:

- 必要コマンドの確認
- `python3 -m pip install -e .`
- `vscode/atc-helper` の `npm install`
- `npm run compile`
- `npx @vscode/vsce package --allow-missing-repository`
- `code --install-extension <vsix> --force`
- `atc`, `oj`, `clang++` / `g++`, `pypy3` の簡易チェック

インストール後は VS Code で `Developer: Reload Window` を実行するか、VS Code を再起動してください。

環境確認:

```bash
atc config doctor
```

## 更新

```bash
./update.sh
```

`update.sh` は `git pull`、Python CLI の再インストール、VS Code 拡張機能の再ビルドと再インストールを行います。

## アンインストール

```bash
./uninstall.sh
```

`uninstall.sh` は VS Code 拡張機能と Python package `atc` を削除します。

以下はユーザーデータなので削除しません。

- `.atc/config.toml`
- `.atc/current-contest.json`
- `.atc/test-runs/`
- 各 contest フォルダ
- `templates/`

不要な場合だけ手動で削除してください。

## `code` コマンドが無い場合

VS Code で Command Palette を開き、次を実行してください。

```text
Shell Command: Install 'code' command in PATH
```

その後、terminal を開き直して確認します。

```bash
code --version
```

## Xcode Command Line Tools

C++ を使う場合は `clang++` または `g++` が必要です。

```bash
xcode-select --install
clang++ --version
```

## online-judge-tools

サンプル取得には `oj` を使います。見つからない場合は入れ直してください。

```bash
python3 -m pip install online-judge-tools
oj --version
oj login https://atcoder.jp/
```

## 手動インストール

補助スクリプトを使わない場合:

```bash
python3 -m pip install -e .

cd vscode/atc-helper
npm install
npm run compile
npx @vscode/vsce package --allow-missing-repository
code --install-extension ./atc-helper-0.0.1.vsix --force
```

VS Code を reload してください。
