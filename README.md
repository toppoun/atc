# atc

AtCoder のコンテスト準備、サンプル取得、ローカルテスト、watch 実行、VS Code の分割ターミナル起動をまとめて扱うための CLI ツールです。

README は最初に読む入口です。詳しい説明は `docs/` に分けています。

## できること

- `atc contest abc335 cpp` で、コンテストフォルダを作る、または既存フォルダを開く
- `online-judge-tools` を使ってサンプルテストを取得する
- `atc t A` / `atc run all` でローカルテストする
- `atc watch` で保存時に自動テストする
- VS Code 拡張機能 `atc-helper` と連携し、手動用 terminal と `atc watch` 用 terminal を左右分割で開く
- `.atc/config.toml` で root、テンプレート、問題一覧、実行環境を設定する

## macOS 最短インストール

友達に配る場合は、まずこれだけで始められる想定です。

```bash
git clone <repo>
cd <repo>
chmod +x install.sh update.sh uninstall.sh
./install.sh
```

必要なもの:

- Python 3
- Node.js / npm
- VS Code
- VS Code の `code` コマンド
- Git
- C++ を使う場合は Xcode Command Line Tools

`code` コマンドが無い場合は、VS Code の Command Palette で次を実行してください。

```text
Shell Command: Install 'code' command in PATH
```

C++ コンパイラが無い場合:

```bash
xcode-select --install
```

更新:

```bash
./update.sh
```

アンインストール:

```bash
./uninstall.sh
```

詳しくは [docs/INSTALL.md](docs/INSTALL.md) を見てください。

## 最初にやること

AtCoder 用の root ディレクトリ、またはその配下を VS Code で開いてから:

```bash
atc config init
atc config doctor
atc contest abc335 cpp
```

`atc config init` は `.atc/config.toml` を作ります。`atc config doctor` は Python、`oj`、C++ compiler、VS Code 連携などを確認します。必要なら `paths.root` や `paths.abc` を編集してください。

## よく使うコマンド

| コマンド | 用途 |
| - | - |
| `atc contest abc335 cpp` | なければ作成、あれば既存コンテストをアクティブ化 |
| `atc new abc335 py` | 純粋に新規作成とサンプル取得 |
| `atc t A` | A 問題をテスト |
| `atc t A python` | A.py を Python でテスト |
| `atc t A cpp` | A.cpp を C++ でテスト |
| `atc run all` | 全問題をまとめてテスト |
| `atc rerun` | 直前に失敗したケースだけ再実行 |
| `atc watch` | ファイル保存を監視して自動テスト |
| `atc manual A B C cpp` | 問題ファイルを手動作成 |
| `atc manual tests` | 現在のフォルダ名を contest ID としてサンプル取得 |
| `atc config show` | 現在の設定を表示 |
| `atc config doctor` | 環境と設定を診断 |

詳しい使い方は [docs/USAGE.md](docs/USAGE.md) を見てください。

## ドキュメント

- インストール: [docs/INSTALL.md](docs/INSTALL.md)
- 使い方: [docs/USAGE.md](docs/USAGE.md)
- config: [docs/CONFIG.md](docs/CONFIG.md)
- 困ったとき: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- 開発者向け: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- AI/Codex 向け詳細仕様: [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md)

## 注意

- VS Code Marketplace にはまだ公開していません。ローカル VSIX インストールで使います。
- VS Code 拡張機能を更新したら、`Developer: Reload Window` または VS Code 再起動をしてください。
- `atc contest` は VS Code の `code` コマンドを直接起動しません。`.atc/current-contest.json` を更新し、VS Code 拡張機能がそれを監視します。
- `atc submit` や `atc open` は現時点では未対応です。
