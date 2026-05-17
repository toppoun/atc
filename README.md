# atc

AtCoder 用の CLI + VS Code 補助 + グラフ可視化ツールです。

できること:

- contest フォルダ作成
- template 展開
- sample download
- local test
- watch mode
- config doctor
- visualizer 起動
- VS Code 分割 terminal 連携

README は短い入口です。詳しい仕様や開発者向け情報は `docs/` を見てください。

## インストール

macOS では `install.sh` で Python CLI と VS Code 拡張をまとめて入れられます。

```bash
./install.sh
```

手動で CLI だけ入れる場合:

```bash
python3 -m pip install -e .
```

VS Code 拡張込みの詳しい手順は [docs/INSTALL.md](docs/INSTALL.md) を見てください。

## 初回セットアップ

```bash
atc config init
atc config doctor
```

`config doctor` は Python、`oj`、C++ compiler、templates、VS Code 連携などを確認します。

## よく使うコマンド

| コマンド | 用途 |
| - | - |
| `atc contest abc335 cpp` | contest 作成または既存 contest をアクティブ化 |
| `atc run A` | A 問題をテスト |
| `atc run all` | 検出できる全問題をテスト |
| `atc rerun` | 直前に失敗したケースだけ再実行 |
| `atc watch` | ファイル変更を監視して自動テスト |
| `atc stress A py` | ランダムケースで提出予定解と愚直解を比較 |
| `atc stress init A` | stress 用 generator / brute を作成 |
| `atc manual A B C py` | 問題ファイルを手動作成 |
| `atc template list` | 利用可能なテンプレートを表示 |
| `atc visual` | visualizer を開く |

詳しい使い方は [docs/USAGE.md](docs/USAGE.md) を見てください。

## config

`.atc/config.toml` の例:

```toml
[paths]
root = "."
abc = "ABC"
arc = "ARC"
agc = "AGC"

[defaults]
language = "cpp"
problems = ["A", "B", "C", "D", "E"]

[templates]
manifest = "templates/manifest.json"
py = "fast"
cpp = "acl"
```

従来通り、直接テンプレートファイルを指定する形式も使えます。

```toml
[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"
```

詳細は [docs/CONFIG.md](docs/CONFIG.md) を見てください。

## atc visual

```bash
atc visual
atc vis
```

VS Code Live Preview が使える場合はそれを優先し、使えない場合はローカルサーバーに fallback して `visualizer.html` を開きます。

## ドキュメント

- [docs/INSTALL.md](docs/INSTALL.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/CONFIG.md](docs/CONFIG.md)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md)
