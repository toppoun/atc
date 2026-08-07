# Install

macOS向けの導入手順です。Windows用`install.ps1`はありません。

## 必要なもの

- macOS
- Node.js 22以上 / npm
- VS Code
- VS Codeの`code`コマンド
- C++を使う場合はXcode Command Line Tools

`install.sh`はPython CLIとVS Code拡張機能をまとめてインストールします。Python CLIはpipx + uvによるstandalone Python 3.11の独立環境へ入り、dependencyの`online-judge-tools`が提供する`oj`も通常のshellから利用できるようになります。

pipxが既にあればそのまま使います。なければHomebrewが利用可能な環境では`brew install pipx`を実行します。Homebrewもない場合は、`python3`、`python`の順にvenvを利用できるPython 3.10以上を探し、一時venvからpipx自身をpipx管理環境へbootstrapします。

uvがなければHomebrew環境では`brew install uv`を実行します。Homebrewもない場合は、uvを安全にインストールしてPATHへ追加するよう案内して終了します。

`atc` runtimeは`--python 3.11 --fetch-python=always`で取得するstandalone Pythonを使うため、Anaconda / CondaやHomebrew Pythonに依存せず、既存環境を変更しません。Python 3.11を使用するのは、現在の`online-judge-tools`をPython 3.12以降の`distutils`削除の影響から避けるためです。

## 初回インストール

```bash
git clone <repository>
cd <repository>
./install.sh
```

`install.sh`が行うこと:

- Node.js / npm / `code`とrepository metadataの確認
- pipxの検出、またはHomebrew / 専用venvによるpipx導入
- uvの検出、またはHomebrewによるuv導入
- uv backendとstandalone Python 3.11を指定したpipx editable install
- `--include-resources-from online-judge-tools`による`atc` / `oj`の公開
- `PIPX_BIN_DIR`の現在位置に応じた`pipx ensurepath --prepend`（既存append設定の修復時だけ`--force`）
- 現在のscript内でのpipx application directoryのPATH先頭反映
- `atc --help`と`oj --help`の確認
- `vscode/atc-helper`で`npm ci`
- TypeScript compileと、固定されたlocal `@vscode/vsce`によるVSIX package
- `code --install-extension <vsix> --force`

インストール後は新しいterminalを開き、pipxのPATH設定を反映してください。既にPATH先頭ならshell設定を変更せず、過去のappend設定がある場合だけprependへ修復します。VS Codeでは`Developer: Reload Window`を実行するか、VS Codeを再起動してください。

確認:

```bash
atc --help
oj --help
atc config doctor
```

## 更新

```bash
cd <repository>
git pull
./update.sh
```

Git操作はユーザーが`update.sh`の前に行います。`update.sh`自体はGit working treeを変更しません。

`update.sh`は既存のpipx / uvと`atc`環境を確認し、その環境がPython 3.11である場合だけ、既存interpreterを維持して現在のlocal sourceを`--force`で再適用します。Python 3.11以外の場合は更新せず、`install.sh`による再構築を案内します。これにより、Python sourceだけでなく`pyproject.toml`のdependency、entry point、Python requirementの変更もpipx環境へ反映します。その後、`npm ci`、compile、VSIX package、VS Code拡張機能の再インストールを行います。

pipxや既存の`atc`環境が見つからない場合は、先に`./install.sh`を実行してください。

## アンインストール

```bash
./uninstall.sh
```

`uninstall.sh`は次だけをbest-effortで削除します。

- pipx管理のPython package`atc`（dependency appの`oj`を含む）
- VS Code extension`kouki.atc-helper`

未インストールの項目やmetadata不足だけで、削除可能なもう一方の処理を中止しません。pipx、Homebrew、Python、Node.js、npm、VS Code自体は削除しません。

以下はユーザーデータなので削除しません。

- `.atc/config.toml`
- `.atc/current-contest.json`
- `.atc/test-runs/`
- 各contestフォルダ
- `templates/`

不要な場合だけ手動で削除してください。

## `code`コマンドがない場合

VS CodeでCommand Paletteを開き、次を実行してください。

```text
Shell Command: Install 'code' command in PATH
```

その後、terminalを開き直して確認します。

```bash
code --version
```

## Xcode Command Line Tools

C++を使う場合は`clang++`または`g++`が必要です。

```bash
xcode-select --install
clang++ --version
```

## online-judge-tools

サンプル取得には`oj`を使います。`install.sh`は`--include-resources-from online-judge-tools`により、pipx管理の`atc`環境から必要な`oj`だけを追加公開します。

```bash
oj --version
oj login https://atcoder.jp/
```

`oj`が見つからない場合は、新しいterminalでPATHを再確認するか、repository内で`./update.sh`を実行してください。

## 手動インストール

補助scriptを使わない場合:

```bash
pipx install \
  --backend uv \
  --python 3.11 \
  --fetch-python=always \
  --force \
  --editable \
  --include-resources-from online-judge-tools \
  .
pipx ensurepath --prepend

cd vscode/atc-helper
npm ci
npm run compile
npm run package -- --out ./atc-helper.vsix
code --install-extension ./atc-helper.vsix --force
```

新しいterminalを開き、VS Codeをreloadしてください。
