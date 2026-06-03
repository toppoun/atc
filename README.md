# atc

AtCoder 用の CLI + VS Code 補助 + グラフ可視化ツールです。

できること:

- contest フォルダ作成
- 既存 contest フォルダの metadata / samples 更新
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

`config doctor` は Python、`oj` と AtCoder ログイン状態、C++ compiler、templates、VS Code 連携などを確認します。

## よく使うコマンド

| コマンド | 用途 |
| - | - |
| `atc contest abc335 cpp` | contest 作成または既存 contest をアクティブ化 |
| `atc c abc335 cpp` | `atc contest` の省略形 |
| `atc refresh` | 既存 contest の `.atc/contest.toml` と不足 samples を更新 |
| `atc run A` | A 問題をテスト |
| `atc run all` | 検出できる全問題をテスト |
| `atc rerun` | 非推奨 |
| `atc watch` | ファイル変更を監視して自動テスト |
| `atc stress A py` | ランダムケースで提出予定解と愚直解を比較 |
| `atc stress init A` | stress 用 generator / brute を作成 |
| `atc manual A B C py` | 問題ファイルを手動作成 |
| `atc template list` | 利用可能なテンプレートを表示 |
| `atc visual` | visualizer を開く |

詳しい使い方は [docs/USAGE.md](docs/USAGE.md) を見てください。

`atc refresh` は contest ディレクトリ内で実行してください。workspace root では、root の `.atc/config.toml` を contest-local metadata と混同しないように禁止しています。contest を active にしたり、VS Code の分割ターミナルを起動したりはしません。

sample の取得が一部失敗した場合でも、metadata の更新結果と失敗した問題を表示します。

`atc watch` は保存した1問の sample 結果を固定表示で更新します。全問題をまとめて確認したい場合は `atc test all` を使います。

## config

`.atc/config.toml` の例:

```toml
[paths]
root = "."

[paths.contests]
"abc\\d+" = "ABC"
"arc\\d+" = "ARC"
"agc\\d+" = "AGC"
"adt_.*" = "ATD"

[defaults]
language = "cpp"
problems = ["A", "B", "C", "D", "E"]

[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"
```

コンテストの作成先は `[paths].root` と `[paths.contests]` の正規表現ルールで決まります。

```text
abc460 -> <root>/ABC/abc460
adt_all_20260525_1 -> <root>/ATD/adt_all_20260525_1
unknown -> <root>/unknown
```

テンプレートを名前で選びたい場合は、manifest 方式も使えます。

```toml
[templates]
manifest = "templates/manifest.json"
py = "fast"
cpp = "acl"
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
