# Usage

よく使うコマンドの説明です。

## `atc contest`

```bash
atc contest abc335 cpp
atc contest abc335 py
```

「なければ作る、あればそのコンテストをアクティブにする」コマンドです。

- contest フォルダが無ければ作成
- 問題ファイルをテンプレートから作成
- `oj` でサンプル取得
- `.atc/current-contest.json` を更新
- VS Code 拡張機能が監視していれば分割 terminal を開く

既に contest フォルダがある場合、作成とサンプル取得はスキップします。

複数形も同じ動作です。

```bash
atc contests abc335 cpp
```

## `atc new`

```bash
atc new abc335 cpp
atc new abc335 py
```

純粋な新規作成コマンドです。

- contest フォルダ作成
- `A.cpp` などの問題ファイル作成
- サンプル取得

`.atc/current-contest.json` は更新しません。VS Code terminal 連携を起動したい場合は `atc contest` を使ってください。

## `atc run` / `atc test` / `atc t`

```bash
cd abc335
atc t A
atc t A python
atc t A pypy
atc t A cpp
```

`atc run A`, `atc test A`, `atc t A` は同じ用途です。

- `python` / `pypy`: `A.py` を実行
- `cpp`: `A.cpp` をコンパイルして実行
- 省略時は `[defaults].language`
- 指定言語のファイルが無い場合だけ、存在する別言語に fallback

全問題をまとめて実行:

```bash
atc run all
atc run all cpp
```

全 AC なら exit code 0、WA / RE / TLE / CE / NO_TESTS / ERROR があれば exit code 1 です。

## `atc watch`

```bash
atc watch
atc watch A
atc watch A cpp
```

ファイル保存を監視して自動テストします。

- 問題ファイルの変更を検知
- 対象問題だけ再実行
- 設定ファイルやビルド関連ファイルが変わった場合は検出できる問題をまとめて再実行
- ログは `.atc/test-runs/last.log`
- 失敗ケースは `.atc/test-runs/last_failed.txt`

終了は `Ctrl+C` です。

## `atc rerun`

```bash
atc rerun
atc rerun cpp
atc retry
```

直前に失敗したケースだけ再実行します。`atc retry` は alias です。

失敗情報は `.atc/test-runs/last_failed.txt` を使います。

## `atc manual`

問題ファイルを手動で作ります。

```bash
atc manual A B C cpp
atc manual A~E py
atc manual A-E cpp
```

現在のフォルダ名を contest ID としてサンプルだけ取得:

```bash
atc manual tests
```

## `atc config`

```bash
atc config init
atc config show
atc config doctor
```

- `init`: カレントディレクトリに `.atc/config.toml` を作成
- `show`: 現在読み込まれる config を表示
- `doctor`: Python、config、templates、runner、`oj`、VS Code 連携、`current-contest.json` を診断

config の詳細は [CONFIG.md](CONFIG.md) を見てください。

## 未対応

以下は現時点では未対応です。

- `atc submit`
- `atc open`
- `--lang python` のような flag 指定
- コマンドラインからのテンプレートパス指定
- VS Code Marketplace 公開
