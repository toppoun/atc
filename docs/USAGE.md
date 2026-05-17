# Usage

AtCoder 作業でよく使うコマンドの説明です。

## `atc new`

```bash
atc new abc335 cpp
atc new abc335 py
```

現在のディレクトリ直下に contest フォルダを新規作成します。

- 問題ファイルをテンプレートから作成
- `oj` でサンプル取得
- `.atc/current-contest.json` は更新しない

VS Code terminal 連携を起動したい場合は `atc contest` を使ってください。

## `atc contest` / `atc contests`

```bash
atc contest abc335 cpp
atc contests abc335 py
```

「なければ作る、あればそのコンテストをアクティブにする」コマンドです。

- contest フォルダ作成または既存確認
- 問題ファイルをテンプレートから作成
- `oj` でサンプル取得
- `.atc/current-contest.json` を更新
- VS Code 拡張機能が監視していれば分割 terminal を開く

既に contest フォルダがある場合、作成とサンプル取得はスキップします。

## `atc run` / `atc r` / `atc test` / `atc t`

```bash
cd abc335
atc run A
atc r A
atc test A python
atc t A pypy
atc t A cpp
```

1問だけテストします。

- `python` / `pypy`: `A.py` を実行
- `cpp`: `A.cpp` をコンパイルして実行
- 省略時は `[defaults].language`
- 指定言語のファイルが無い場合だけ、存在する別言語に fallback

全 AC なら exit code 0、WA / RE / TLE / CE / NO_TESTS / ERROR があれば exit code 1 です。

## `atc run all`

```bash
atc run all
atc run all cpp
```

検出できる全問題をまとめてテストします。

結果ログ:

```text
.atc/test-runs/last.log
.atc/test-runs/last_failed.txt
```

## `atc rerun` / `atc retry`

```bash
atc rerun
atc rerun cpp
atc retry
```

直前に失敗したケースだけ再実行します。失敗情報は `.atc/test-runs/last_failed.txt` を使います。

## `atc watch` / `atc w` / `atc auto`

```bash
atc watch
atc watch A
atc watch A cpp
atc watch all
atc w
atc auto
```

ファイル保存を監視して自動テストします。

- 問題ファイルの変更を検知
- 対象問題だけ再実行
- config やビルド関連ファイルが変わった場合は検出できる問題をまとめて再実行
- ログは `.atc/test-runs/last.log`
- 失敗ケースは `.atc/test-runs/last_failed.txt`

終了は `Ctrl+C` です。

## `atc stress`

提出予定解と愚直解を、ランダム生成した入力で比較します。

```bash
atc stress A
atc stress A py
atc stress A cpp
atc stress A py --count 100 --seed 42
atc stress A --gen A_gen.py --brute A_brute.py
atc stress A --timeout 2.0 --compare strip
```

必要ファイル:

```text
A.py / A.cpp
A_gen.py
A_brute.py
```

`A_gen.py` は seed を argv で受け取ります。

```bash
python A_gen.py 42
```

比較モード:

- `exact`: stdout を完全一致で比較
- `strip`: 前後空白を除去して比較
- `tokens`: 空白区切り tokens として比較

不一致が見つかった場合は `.atc/stress/A/` に入力、出力、meta 情報を保存します。

## `atc manual`

問題ファイルを手動で作ります。

```bash
atc manual A B C cpp
atc manual A~E py
atc manual A-E cpp
```

既存ファイルは上書きしません。

## `atc manual tests`

現在のフォルダ名を contest ID としてサンプルだけ取得します。

```bash
atc manual tests
```

## `atc template`

利用可能なテンプレートを確認したり、テンプレート本文を表示します。

```bash
atc template list
atc template list py
atc template list cpp
atc template show py default
atc template show cpp acl
```

- `list`: manifest から利用可能なテンプレート名、説明、path を表示
- `list py` / `list cpp`: 指定言語だけ表示
- `show <py|cpp> <name>`: 指定テンプレートの本文を stdout に表示

## `atc config`

```bash
atc config init
atc config show
atc config doctor
```

- `init`: カレントディレクトリに `.atc/config.toml` を作成
- `show`: 現在読み込まれる config を表示
- `doctor`: Python、config、templates、runner、watch、`oj`、VS Code 連携、`current-contest.json` を診断

config の詳細は [CONFIG.md](CONFIG.md) を見てください。

## `atc visual` / `atc vis` / `atc vizui`

```bash
atc visual
atc vis
atc vizui
atc vis --live-preview
atc vis --live-preview --no-fallback
atc vis --no-live-preview
atc vis --live-preview-url "http://127.0.0.1:3000/tools/visualizer.html?vscode-livepreview=true"
atc visual --port 8000
atc visual --no-open
atc vis --no-open
```

`tools/visualizer.html` をブラウザで開きます。デフォルトでは VS Code Live Preview を優先し、使えない場合だけローカルHTTPサーバーに fallback します。

- デフォルトの Live Preview URL は `http://127.0.0.1:3000/tools/visualizer.html?vscode-livepreview=true`
- `--live-preview` で Live Preview URL を明示的に使う
- `--no-fallback` を併用すると、Live Preview が使えない場合にローカルHTTPサーバーへ fallback せず終了
- `--no-live-preview` で Live Preview を使わず、必ずローカルHTTPサーバーを使う
- `--live-preview-url` で Live Preview URL を変更
- ローカルHTTPサーバーのデフォルトは `http://127.0.0.1:8765/visualizer.html`
- `--port` でローカルHTTPサーバーの開始ポートを指定
- 指定ポートが使用中なら、近い空きポートに fallback
- `--no-open` を付けるとブラウザを自動で開かず、URLだけ表示
- 停止は `Ctrl+C`

## 未対応

以下は現時点では未対応です。

- `atc submit`
- `atc open`
- `--lang python` のような flag 指定
- コマンドラインからのテンプレートパス指定
- VS Code Marketplace 公開
