# atc

AtCoder のコンテスト準備、サンプル取得、ローカルテスト、watch 実行、VS Code の分割ターミナル起動をまとめて扱うための個人用 CLI ツールです。

主な用途は次の通りです。

- `atc new abc413 cpp` でコンテストフォルダ、問題ファイル、サンプルテストを作成する
- `atc contest abc413 cpp` で、コンテストがなければ作成し、既にあればアクティブ化だけ行う
- `atc run A` / `atc t A` / `atc run all` でローカルテストする
- `atc watch` で保存時に対象問題だけ自動テストする
- VS Code 拡張機能 `atc-helper` と連携し、手動用ターミナルと `atc watch` 用ターミナルを左右分割で開く

この README は現在の実装に合わせています。未実装の機能は「現時点では未対応」と明記しています。

## 目次

- [インストール](#-インストール)
- [セットアップ](#-セットアップ)
- [対応コンテスト](#-対応コンテスト)
- [コマンドの詳細オプション](#️-コマンドの詳細オプション)
- [トラブルシューティング](#-トラブルシューティング)
- [使用例](#-使用例)
- [プロジェクト構造](#️-プロジェクト構造)
- [ライセンス](#-ライセンス)
- [貢献ガイド](#-貢献ガイド)
- [パフォーマンス情報](#-パフォーマンス情報)
- [関連リンク](#-関連リンク)
- [FAQ](#-faq)
- [サポート情報](#-サポート情報)

## 📦 インストール

### 必要なもの

- Python 3.x
- Python 3.10 以上推奨
- `online-judge-tools`
- C++ を使う場合は `g++`
- VS Code 拡張機能を使う場合は Node.js / npm / VS Code

`pyproject.toml` 上の `requires-python` は `>=3.8` ですが、開発・利用環境としては Python 3.10 以上を推奨します。

### Python CLI のインストール

リポジトリ直下で以下を実行します。

```bash
python -m pip install -e .
```

依存パッケージとして `online-judge-tools` が指定されていますが、個別に入れ直したい場合は次を実行します。

```bash
python -m pip install online-judge-tools
```

インストール後、`atc` コマンドが見えるか確認します。

```bash
atc
```

Windows の場合:

```powershell
where atc
```

macOS / Linux の場合:

```bash
which atc
```

### Windows で `atc` が見つからない場合

`pip` がインストールした Scripts ディレクトリが PATH に入っていない可能性があります。

代表的な場所:

```text
C:\Users\<ユーザー名>\AppData\Local\Programs\Python\Python3xx\Scripts
C:\Users\<ユーザー名>\AppData\Roaming\Python\Python3xx\Scripts
```

仮想環境を使っている場合:

```text
<プロジェクト>\.venv\Scripts
```

確認:

```powershell
where atc
where python
```

PATH を追加した後は、ターミナルや VS Code を開き直してください。

### Windows / macOS / Linux の環境構築例

Windows:

```powershell
cd D:\atc
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
python -m pip install online-judge-tools
```

macOS:

```bash
cd ~/atc
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m pip install online-judge-tools
```

Linux:

```bash
cd ~/atc
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m pip install online-judge-tools
```

### C++ を使う場合の g++ 環境

この CLI は `A.cpp` などが存在する場合、`g++` でコンパイルしてからテストします。コンパイラやオプションは `config.toml` の `[runner]` で変更できます。デフォルトは概ね次の形です。

```bash
g++ -std=c++20 -O2 -Wall -Wextra A.cpp -o _A.exe
```

Windows では MSYS2 UCRT64 を推奨します。

```powershell
where g++
```

MSYS2 UCRT64 の代表的な PATH:

```text
C:\msys64\ucrt64\bin
```

macOS:

- Xcode Command Line Tools
- または Homebrew の gcc

```bash
xcode-select --install
g++ --version
```

Linux:

```bash
sudo apt update
sudo apt install build-essential
g++ --version
```

## 🔧 セットアップ

### テンプレート

新規問題ファイルはテンプレートから作成されます。

このリポジトリでは実際のテンプレートは次の場所にあります。

```text
atc/templates/template.py
atc/templates/template.cpp
```

CLI 内ではパッケージ内の `templates/template.py` / `templates/template.cpp` として読み込まれます。内容を変えたい場合は、上記ファイルを直接編集してください。

`pip install .` でインストールした場合も、パッケージ内の標準テンプレートは同梱されます。

ユーザーごとのテンプレートを持つ場合は、project root の `templates/` 配下に置き、`.atc/config.toml` から参照する形を推奨します。

```text
<project-root>/templates/template.py
<project-root>/templates/template.cpp
```

`.atc/config.toml` または `~/.atc/config.toml` がある場合は、`[templates]` の `py` / `cpp` でテンプレートパスを指定できます。相対パスは config の場所や project root から解決されます。

テンプレートが存在しない場合は、警告を表示し、空ファイルを作成します。

```text
Warning: ... が見つかりません。空ファイルを作成します。
```

カスタムテンプレートをコマンドラインオプションで指定する機能は、現時点では未対応です。config の `[templates]` を使ってください。

### 初期設定ファイル

TOML 形式の設定ファイル `config.toml` に対応しています。

探索順:

1. カレントディレクトリから親方向に `.atc/config.toml` を探す
2. 見つからなければ `~/.atc/config.toml` を探す
3. それも無ければデフォルト設定を使う

設定ファイルを作成する場合:

```bash
atc config init
```

現在読み込まれている設定を確認する場合:

```bash
atc config show
```

現在、設定ファイルは以下に使われます。

- `atc config show`: 読み込まれている設定の確認
- `atc config init`: カレントディレクトリへの `.atc/config.toml` 初期生成
- `atc contest abcxxx`: `paths.root` と `paths.abc` を使って作成・利用するディレクトリを決定
- `atc contest arcxxx`: `paths.root` と `paths.arc` を使って作成・利用するディレクトリを決定
- `atc contest agcxxx`: `paths.root` と `paths.agc` を使って作成・利用するディレクトリを決定
- `.atc/current-contest.json`: `paths.root` が設定されている場合は `paths.root/.atc/current-contest.json` に保存
- `[templates]`: `atc new`, `atc contest`, `atc manual` で作成するファイルのテンプレート
- `[defaults].language`: `py` / `cpp` を省略した時の作成言語
- `[defaults].problems`: `atc new`, `atc contest`, `atc manual tests`, `atc run all`, `atc watch` の対象問題一覧

`atc contest` の作成・利用先は次のように決まります。

- `paths.root` が空の場合、現在のカレントディレクトリ直下を使う
- `paths.root` が設定されていて、contest ID が `abc数字` / `arc数字` / `agc数字` 形式の場合、`paths.abc` / `paths.arc` / `paths.agc` に自動振り分けする
- `config.toml` はデフォルト設定とマージされるため、`abc` / `arc` / `agc` を書かなくてもデフォルトのカテゴリ名が使われる
- 自動振り分けを無効化したい場合は、該当カテゴリを空文字にする

例:

```toml
[paths]
root = "D:/atcoder"
abc = ""
```

この場合、`atc contest abc335 py` は `D:/atcoder/ABC(Atcoder Beginner Contest)/abc335` ではなく、現在のカレントディレクトリ直下の `abc335/` を使います。

`runner` の設定値は実行処理に反映されます。`python`, `pypy`, `cpp_compiler`, `cpp_flags`, `timeout_seconds`, `compile_timeout_seconds` を変更できます。

設定例:

```toml
[paths]
root = ""
abc = "ABC(Atcoder Beginner Contest)"
arc = "ARC(Atcoder Regular Contest)"
agc = "AGC(Atcoder Grand Contest)"

[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"

[defaults]
language = "cpp"
problems = ["A", "B", "C", "D", "E"]

[runner]
python = "python"
pypy = "pypy"
cpp_compiler = "g++"
cpp_flags = ["-std=c++20", "-O2", "-Wall", "-Wextra"]
timeout_seconds = 2.0
compile_timeout_seconds = 10.0
```

ただし、watch の再実行対象判定では以下のような設定ファイルの変更を検知します。

```text
pyproject.toml
requirements.txt
poetry.lock
uv.lock
Pipfile
Pipfile.lock
Makefile
CMakeLists.txt
```

これらが変更された場合、検出できる問題をまとめて再実行します。

### online-judge-tools

サンプル取得には `online-judge-tools` の `oj` コマンドを使います。

```bash
python -m pip install online-judge-tools
oj --version
```

AtCoder のサンプル取得でログインが必要な場合があります。

```bash
oj login https://atcoder.jp/
```

手動でサンプル取得を試す場合:

```bash
oj d https://atcoder.jp/contests/abc413/tasks/abc413_a -d tests/A
```

### VS Code 拡張機能

VS Code 拡張機能は次の場所にあります。

```text
vscode/atc-helper/
```

役割:

- `.atc/current-contest.json` の変更を監視
- 変更を検知したら、今開いている VS Code ワークスペース内で分割ターミナルを開く
- 左側: `atc terminal`
- 右側: `atc watch`

VS Code 連携を使う場合は、AtCoder 用の root ディレクトリ、または `.atc/current-contest.json` が作られる project root を VS Code で開くことを推奨します。

現時点の VS Code 拡張機能は `config.toml` を直接読みません。CLI が更新する `.atc/current-contest.json` を監視して動作します。

### ディレクトリ構造について

特定のディレクトリ構造は必須ではありません。`ABC(Atcoder Beginner Contest)` のようなカテゴリフォルダが無い環境でも利用できます。

`atc contest abc335 py` は、`paths.root` が未設定なら現在のカレントディレクトリを基準に `abc335/` を作成または利用します。

`paths.root` が設定されていて contest ID が `abc数字` の場合は、`paths.root / paths.abc / abc335` を使います。`arc数字` と `agc数字` も同様に `paths.arc`, `paths.agc` を使います。`abc` / `arc` / `agc` はデフォルト値を持つため、config に明示しなくても自動振り分けされます。

自動振り分けを無効化したい場合は、該当カテゴリを空文字にしてください。

```toml
[paths]
root = "D:/atcoder"
abc = ""
```

この場合、`abc335` は現在のカレントディレクトリ直下に作成されます。

例:

```text
atcoder/
└── abc335/
```

```text
atcoder/
└── ABC/
    └── abc335/
```

```text
competitive/
└── atcoder/
    └── abc335/
```

`.atc/current-contest.json` の保存先 root は、`paths.root` が設定されている場合はその場所になります。未設定の場合は、現在地から親方向に `.git`, `.vscode`, `pyproject.toml` を探して推定します。見つからない場合は現在のディレクトリを root とします。`ABC(Atcoder Beginner Contest)` などのカテゴリ名は後方互換の fallback として扱いますが、必須条件ではありません。

#### ローカル VSIX インストール

通常利用では、Extension Development Host ではなく VSIX としてローカルインストールします。

```powershell
cd vscode/atc-helper
npm install
npm run compile
npx @vscode/vsce package --allow-missing-repository
```

VS Code の UI からインストールする場合:

```text
Extensions → ... → Install from VSIX...
```

生成された `atc-helper-0.0.1.vsix` を選択してください。

コマンドでインストールする場合:

```powershell
code --install-extension .\atc-helper-0.0.1.vsix --force
```

ただし、`code --install-extension` は環境によって VS Code が新しく開くことがあります。通常は VS Code の UI から `Install from VSIX...` を使う方が分かりやすいです。

インストール後は VS Code で `Developer: Reload Window` を実行してください。

#### 拡張機能を変更した後の更新

拡張機能のコードを変更したら、VSIX を作り直して再インストールします。

```powershell
cd vscode/atc-helper
npm install
npm run compile
npx @vscode/vsce package --allow-missing-repository
```

その後:

```text
Extensions → ... → Install from VSIX...
Developer: Reload Window
```

コマンドで入れ直す場合:

```powershell
code --install-extension .\atc-helper-0.0.1.vsix --force
```

同じ `0.0.1` のまま入れ直す場合も、`--force` を付ければ上書きできます。

## 🎯 対応コンテスト

主な対象は AtCoder の以下の形式です。

- ABC: AtCoder Beginner Contest
- ARC: AtCoder Regular Contest
- AGC: AtCoder Grand Contest

デフォルトの標準問題セットは `A`, `B`, `C`, `D`, `E` です。

```python
PROBLEMS = ["A", "B", "C", "D", "E"]
```

通常は `.atc/config.toml` の `[defaults].problems` を変更すれば、作成・取得・watch 対象の問題リストを変えられます。config が無い場合は、CLI 内のデフォルト値として `PROBLEMS` が使われます。

サンプル取得時の URL は、現在は次の形式に依存しています。

```text
https://atcoder.jp/contests/{contest}/tasks/{contest}_{problem}
```

例:

```text
https://atcoder.jp/contests/abc413/tasks/abc413_a
```

そのため、ADT、鉄則本、特殊な練習コンテストなど、URL 形式が異なるものは制限がある可能性があります。サンプル取得は `online-judge-tools` に依存しており、AtCoder 側のページ構成変更やログイン状態、ネットワーク状態の影響を受けます。

問題レベル自体に制限はありませんが、標準では A-E だけを対象にします。F 以降を扱う場合は `[defaults].problems` を変更してください。

## ⚙️ コマンドの詳細オプション

| コマンド | 説明 | 備考 |
| - | - | - |
| `atc new abc413 [py\|cpp]` | `abc413/` を作成し、設定された問題ファイルとサンプルを作成 | 既存フォルダでも `cmd_new` は走るため、サンプル取得を再試行します |
| `atc contest abc413 [py\|cpp]` | なければ作成、あれば作成とサンプル取得をスキップし、`.atc/current-contest.json` を更新 | `paths.root` があれば `abc` / `arc` / `agc` を自動振り分け |
| `atc contests abc413 [py\|cpp]` | `atc contest` と同じ | 複数形エイリアス |
| `atc config show` | 現在読み込まれる設定を表示 | `.atc/config.toml`、ホーム設定、デフォルトの順で解決 |
| `atc config init` | カレントディレクトリに `.atc/config.toml` を作成 | 既に存在する場合は上書きしません |
| `atc run A [python\|pypy\|cpp]` | A 問題を詳細表示付きでテスト | 省略時は `[defaults].language`。指定言語のファイルが無い場合だけ別言語に fallback |
| `atc r A [python\|pypy\|cpp]` | `atc run A` の短縮 | 同上 |
| `atc test A [python\|pypy\|cpp]` | `atc run A` のエイリアス | 同上 |
| `atc t A [python\|pypy\|cpp]` | `atc run A` の短縮エイリアス | よく使う短縮形 |
| `atc run all [python\|pypy\|cpp]` | 検出できる全問題をまとめてテスト | 省略時は `[defaults].language` |
| `atc rerun [python\|pypy\|cpp]` | 直前に失敗したケースだけ再実行 | `.atc/test-runs/last_failed.txt` を使用 |
| `atc retry [python\|pypy\|cpp]` | `atc rerun` のエイリアス | 同上 |
| `atc watch [A] [python\|pypy\|cpp]` | ファイル変更を監視して自動テスト | 省略時は `[defaults].language` |
| `atc manual A B C [py\|cpp]` | 現在のフォルダに指定問題ファイルを作成 | デフォルトは `[defaults].language`、未設定なら `cpp` |
| `atc manual A~E [py\|cpp]` | 範囲指定で問題ファイルを作成 | `A-E` 形式も使用可能 |
| `atc manual tests` | 現在のフォルダ名を contest ID としてサンプル取得 | `[defaults].problems` が対象 |

### 言語指定

作成時:

- `py`
- `cpp`
- 省略時は `[defaults].language`
- config が無い場合の省略時デフォルトは `cpp`

例:

```bash
atc new abc413 py
atc contest abc413 cpp
```

実行時:

- `python`
- `pypy`
- `cpp`
- 省略時は `[defaults].language`
- 指定言語のファイルが無い場合だけ、存在する別言語に fallback

例:

```bash
atc run A
atc run A pypy
atc run A cpp
```

現時点では `--lang python` のようなフラグ形式は未対応です。位置引数で指定してください。

### C++ 実行について

同じ問題に `A.py` と `A.cpp` がある場合、実行言語の指定が優先されます。

- `atc t A python`: `A.py`
- `atc t A pypy`: `A.py`
- `atc t A cpp`: `A.cpp`
- `atc t A`: `[defaults].language`

指定した言語のファイルが無い場合だけ、存在する別言語に fallback します。

### 未対応のオプション

以下は現時点では未対応です。

- `--lang python` のようなフラグ形式
- コマンドラインからのカスタムテンプレート指定
- ABC / ARC / AGC 以外の contest ID のカテゴリ自動振り分け

テンプレートを変える場合は `[templates]` を設定するか、`atc/templates/template.py` と `atc/templates/template.cpp` を直接編集してください。

## 📋 トラブルシューティング

### `atc` が見つからない

原因:

- pip でインストールされた Scripts ディレクトリが PATH に入っていない
- 仮想環境を有効化していない

確認:

```powershell
where atc
```

対処:

- Windows の場合、`C:\Users\<ユーザー名>\AppData\Local\Python\...\Scripts` を PATH に追加
- 仮想環境を使っている場合は `.venv\Scripts\Activate.ps1` を実行
- PATH 変更後はターミナルや VS Code を開き直す

### `oj` が見つからない

確認:

```bash
oj --version
```

対処:

```bash
python -m pip install online-judge-tools
```

仮想環境を使っている場合は、仮想環境を有効化した状態で実行してください。

### テストケース取得に失敗する

原因候補:

- contest ID が間違っている
- URL 形式が非対応
- online-judge-tools が未ログイン
- ネットワークエラー
- AtCoder 側のページ構成変更
- Python / pip 環境に `oj` が入っていない

対処:

```bash
oj login https://atcoder.jp/
```

手動で `oj d <URL>` を試します。

```bash
oj d https://atcoder.jp/contests/abc413/tasks/abc413_a -d tests/A
```

現在の CLI は `oj` のダウンロード失敗時に `failed` と reason を表示します。さらに詳しく見たい場合は、手動で `oj d` を実行してください。

### `config.toml` が壊れている

`config.toml` の TOML 構文が壊れている場合、CLI は読み込めなかった config ファイルのパスと理由を表示して終了します。

確認:

```bash
atc config show
```

よくある原因:

- `[` や `]` の閉じ忘れ
- 文字列のクォート忘れ
- 配列のカンマ忘れ

対処:

- エラーに表示された `.atc/config.toml` または `~/.atc/config.toml` を修正する
- 分からなければ一度別名に退避して `atc config init` で作り直す

### `g++` が見つからない

確認:

```powershell
where g++
```

Windows:

- MSYS2 UCRT64 をインストール
- `C:\msys64\ucrt64\bin` を PATH に追加
- ターミナルを開き直す

macOS:

```bash
xcode-select --install
g++ --version
```

Linux:

```bash
sudo apt install build-essential
g++ --version
```

### `#include <bits/stdc++.h>` に VS Code で赤波線が出る

原因:

- VS Code C/C++ 拡張が g++ の includePath を認識していない

対処例:

- `compilerPath` を `C:/msys64/ucrt64/bin/g++.exe` に設定
- `intelliSenseMode` を `windows-gcc-x64` に設定

`.vscode/c_cpp_properties.json` の例:

```json
{
  "configurations": [
    {
      "name": "Win32",
      "compilerPath": "C:/msys64/ucrt64/bin/g++.exe",
      "intelliSenseMode": "windows-gcc-x64",
      "cppStandard": "c++20"
    }
  ],
  "version": 4
}
```

このファイルの自動生成は現時点では未対応です。

### VS Code 拡張機能が動かない

確認:

- 拡張機能がインストールされているか
- VS Code を Reload したか
- AtCoder 用の root ディレクトリ、または `.atc/current-contest.json` が置かれる root ディレクトリを VS Code で開いているか
- `.atc/current-contest.json` がワークスペース直下、または拡張機能が探索する場所に作られているか
- `AtC: Open Contest Terminals` がコマンドパレットに出るか

VS Code 拡張機能は現時点では `.atc/config.toml` を直接読みません。`atc contest` によって更新された `.atc/current-contest.json` を見て動作します。

インストール確認:

```powershell
code --list-extensions --show-versions | findstr atc-helper
```

期待例:

```text
kouki.atc-helper@0.0.1
```

### VS Code 拡張機能を更新したのに反映されない

対処:

```powershell
cd vscode/atc-helper
npm run compile
npx @vscode/vsce package --allow-missing-repository
```

その後:

- Extensions → ... → Install from VSIX...
- Developer: Reload Window

コマンドで入れ直す場合:

```powershell
code --install-extension .\atc-helper-0.0.1.vsix --force
```

### `atc contest` で VS Code が反応しない

確認:

- VS Code 拡張機能がインストール済みか
- VS Code で `paths.root`、または `.atc/current-contest.json` が作られる project root を開いているか
- `atc contest` 実行後に `.atc/current-contest.json` の `requestId` が更新されているか
- VS Code を Reload したか

`atc contest` は VS Code の `code` コマンドを直接起動しません。CLI が `.atc/current-contest.json` を更新し、VS Code 拡張機能がそれを監視して反応します。
VS Code 拡張機能は `config.toml` を直接読まないため、VS Code 連携を使う場合は `.atc/current-contest.json` が作られる AtCoder root / project root を VS Code で開く運用を推奨します。

## 📝 使用例

### 新しいABCを始める

```powershell
cd "<atcoder-root>"
atc contest abc413 cpp
```

期待される動作:

- `paths.root` が設定済みなら、`abc413/` は `paths.root / paths.abc` 配下に作成
- `paths.root` が空なら、現在のディレクトリ直下に `abc413/` を作成
- デフォルトでは `A.cpp` から `E.cpp` を作成
- 作成する問題リストは `[defaults].problems` で変更可能
- サンプル取得
- `paths.root` が設定済みなら `<paths.root>\.atc\current-contest.json` を更新
- 未設定なら `<project-root>\.atc\current-contest.json` を更新
- VS Code 拡張が分割ターミナルを開く
- 左が手動用
- 右が `atc watch` 用

### 既存コンテストを開く

```powershell
cd "<atcoder-root>"
atc contest abc413 cpp
```

期待される動作:

- `abc413/` が既に存在する場合、作成とサンプル取得はスキップ
- `.atc/current-contest.json` だけ更新
- VS Code 拡張が変更を検知
- ターミナル分割だけ起動

表示例:

```text
abc413 already exists. Skip creation and sample download.
current contest saved: <project-root>\.atc\current-contest.json
```

### 純粋に新規作成だけ行う

```powershell
cd "<atcoder-root>"
atc new abc413 py
```

期待される動作:

- `abc413/` を作成
- デフォルトでは `A.py` から `E.py` を作成
- 作成する問題リストは `[defaults].problems` で変更可能
- サンプル取得
- VS Code 拡張機能用の `current-contest.json` は更新しない

### 手動でテストする

```powershell
cd abc413
atc t A
```

省略時は `[defaults].language` を使います。config が無い場合は `cpp` です。

```powershell
atc t A python
atc t A pypy
atc t A cpp
```

- `atc t A python`: `A.py` を Python で実行
- `atc t A pypy`: `A.py` を PyPy で実行
- `atc t A cpp`: `A.cpp` を C++ でコンパイルして実行
- 指定した言語のファイルが無い場合だけ、存在する別言語に fallback

### 全問題をテストする

```powershell
atc run all
```

検出できる問題をまとめて実行し、結果を要約表示します。

### 失敗したテストケースだけ再実行する

```powershell
atc rerun
```

`.atc/test-runs/last_failed.txt` に保存された失敗ケースだけを再実行します。

### watch モード中のワークフロー

```powershell
atc watch
```

動作:

- 起動時に一度テストを実行
- ファイル保存を検知
- 対象問題だけ自動実行
- `.atc/test-runs/last.log` にログ保存
- `.atc/test-runs/last_failed.txt` に失敗ケース保存
- `Ctrl+C` で終了

特定問題だけ監視:

```powershell
atc watch A
```

PyPy で実行:

```powershell
atc watch A pypy
```

### 手動で問題ファイルを追加する

```powershell
atc manual A B C py
```

範囲指定:

```powershell
atc manual A~E cpp
atc manual A-E py
```

### 現在のフォルダ名でサンプルだけ取得する

```powershell
cd abc413
atc manual tests
```

現在のフォルダ名 `abc413` を contest ID として、`[defaults].problems` のサンプルを取得します。config が無い場合は A-E が対象です。

## 🏗️ プロジェクト構造

実際の主な構成:

```text
.
├── atc/
│   ├── cli.py
│   └── templates/
│       ├── template.py
│       └── template.cpp
├── vscode/
│   └── atc-helper/
│       ├── package.json
│       ├── tsconfig.json
│       ├── README.md
│       ├── out/
│       │   └── extension.js
│       └── src/
│           └── extension.ts
├── .atc/
│   ├── current-contest.json
│   └── test-runs/
│       ├── last.log
│       └── last_failed.txt
├── pyproject.toml
└── README.md
```

各ディレクトリの役割:

- `atc/`: Python CLI 本体
- `atc/cli.py`: `atc` コマンドの実装
- `atc/templates/`: 新規問題ファイルの雛形
- `vscode/atc-helper/`: VS Code 拡張機能
- `vscode/atc-helper/src/extension.ts`: 拡張機能の TypeScript ソース
- `vscode/atc-helper/out/extension.js`: コンパイル後の拡張機能本体
- `.atc/`: 実行時に生成される作業ディレクトリ
- `.atc/current-contest.json`: CLI と VS Code 拡張機能の連携用ファイル
- `.atc/test-runs/`: テストログ保存用

`.atc/` は config や project root 推定結果に応じて作られます。`paths.root` が設定されている場合、`atc contest` は `paths.root/.atc/current-contest.json` に書き込みます。未設定の場合は現在地から親方向に `.git`, `.vscode`, `pyproject.toml` を探し、見つかった root の `.atc/current-contest.json` に書き込みます。特定のカテゴリフォルダ名は必須ではありません。

## 📄 ライセンス

現時点ではリポジトリの LICENSE ファイルは未設定です。

個人利用の範囲ならこのままでも使えますが、公開や再配布を考える場合は MIT License などの明示的なライセンス設定を推奨します。

使用している外部ツール:

- online-judge-tools
- VS Code API
- TypeScript
- @vscode/vsce

外部ツールのライセンスは各プロジェクトに従います。

## 🤝 貢献ガイド

現時点では個人用ツールとして開発していますが、改善提案や修正は歓迎です。

### バグ報告

バグ報告では、次の情報があると調査しやすくなります。

- OS
- Python バージョン
- `atc` の実行コマンド
- エラーメッセージ
- コンテスト ID
- Python / C++ どちらを使っているか
- VS Code 拡張機能の有無

### 新機能提案

新機能提案では、次を説明してください。

- 何をしたいか
- どのコマンドに追加したいか
- 既存機能との違い
- 手作業では何が面倒か

### プルリクエスト

作業ブランチ例:

```bash
git switch -c feature/your-feature-name
```

PR 前に確認すること:

- Python CLI の対象コマンドを実行する
- VS Code 拡張機能を変更した場合は `npm run compile` を実行する
- VSIX インストールが必要な変更なら、`npx @vscode/vsce package --allow-missing-repository` でパッケージできるか確認する
- Python CLI と VS Code 拡張機能は別々に確認する

## ⚡ パフォーマンス情報

watch モードはポーリング方式です。

現在の設定:

```python
WATCH_POLL_SECONDS = 0.25
WATCH_DEBOUNCE_SECONDS = 1.5
```

意味:

- 0.25 秒ごとに対象ファイルの更新状態を確認
- 変更後すぐには実行せず、1.5 秒待ってからテスト実行
- 連続保存や生成途中のファイルに対する過剰実行を減らす

メモリ使用量は通常小さいですが、巨大な `tests/` ディレクトリでは監視対象が増えるため、多少増える可能性があります。

テスト実行時間は以下に依存します。

- 提出コードの実行時間
- Python / PyPy / C++ の違い
- テストケース数
- C++ のコンパイル時間

最大対応ファイルサイズは明示的には設けていません。ただし、巨大な入力・出力ファイルを大量に置く使い方は非推奨です。

## 🔗 関連リンク

- AtCoder 公式サイト: <https://atcoder.jp/>
- online-judge-tools: <https://github.com/online-judge-tools/oj>
- VS Code: <https://code.visualstudio.com/>
- VS Code Extension API: <https://code.visualstudio.com/api>
- MSYS2: <https://www.msys2.org/>

VS Code Marketplace について:

- 現在は未公開です
- ローカル VSIX インストールで利用してください

## ❓ FAQ

### Q. 複数コンテストを並行できますか？

フォルダを分ければ可能です。

ただし、VS Code 拡張機能が見る `current-contest.json` は基本的に1つです。`atc contest` を最後に実行したコンテストがアクティブになります。

### Q. テンプレートはどう変えますか？

config を使う場合は `[templates]` を設定してください。

```toml
[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"
```

config を使わない場合は、以下を編集してください。

```text
atc/templates/template.py
atc/templates/template.cpp
```

コマンドラインから別テンプレートを指定する機能は、現時点では未対応です。

### Q. C++ のコンパイルオプションはどこで変えますか？

`config.toml` の `[runner]` で変更できます。

```toml
[runner]
cpp_compiler = "g++"
cpp_flags = ["-std=c++20", "-O2", "-Wall", "-Wextra"]
timeout_seconds = 2.0
compile_timeout_seconds = 10.0
```

### Q. Python のバージョンを切り替えたいです

仮想環境を使ってください。

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

PyPy を使う場合:

```bash
atc run A pypy
```

### Q. `atc contest` と `atc new` の違いは？

`atc new` は純粋な新規作成コマンドです。

- フォルダ作成
- テンプレート作成
- サンプル取得

`atc contest` は「なければ作る、あればアクティブ化する」コマンドです。

- フォルダがなければ `cmd_new` 相当を実行
- 既にあれば作成とサンプル取得をスキップ
- `.atc/current-contest.json` を更新
- VS Code 拡張機能が監視していれば分割ターミナルを開く

### Q. VS Code を開いた瞬間にターミナルが開きますか？

開きません。

VS Code 拡張機能は起動時に `current-contest.json` の監視を登録しますが、既存ファイルを読んで即座にターミナルを開く挙動にはしていません。ターミナルが開くのは、`atc contest` によって `current-contest.json` が更新された時、または `AtC: Open Contest Terminals` を手動実行した時です。

### Q. `atc watch A cpp` は使えますか？

使えます。`atc watch A cpp` は `A.cpp` を使います。省略時は `[defaults].language` が使われます。

## 📊 サポート情報

Issue トラッカー:

- GitHub 未公開の場合は未設定

メンテナー:

- 個人メンテナンス

開発状況:

- アクティブ開発中
- 破壊的変更の可能性あり

サポート対象:

- Windows
- macOS
- Linux

主な検証環境:

- Windows
- VS Code
- MSYS2 UCRT64
- Python 3.x

macOS / Linux でも動作する想定ですが、特に Windows + VS Code + MSYS2 UCRT64 を主な検証環境としています。
