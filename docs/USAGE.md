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

## `atc contest` / `atc contests` / `atc c`

```bash
atc contest abc335 cpp
atc contests abc335 py
atc c abc335 cpp
```

「なければ作る、あればそのコンテストをアクティブにする」コマンドです。

- contest フォルダ作成または既存確認
- 問題ファイルをテンプレートから作成
- `oj` でサンプル取得
- `.atc/current-contest.json` を更新
- VS Code 拡張機能が監視していれば分割 terminal を開く

既に contest フォルダがある場合、作成とサンプル取得はスキップします。

## `atc refresh`

古い contest フォルダを現在の `atc` 形式に更新します。

```bash
cd abc335
atc refresh
atc refresh --yes
atc refresh -y
```

config の `[paths.contests]` から contest フォルダを解決したい場合は、contest ID も指定できます。

```bash
atc refresh abc335
```

`atc refresh` は AtCoder の tasks page を取得し、tasks page に載っている全問題を対象にします。

- `.atc/contest.toml` を再生成
- 不足している `tests/<problem>` だけサンプル取得
- 既に中身がある `tests/<problem>` はスキップ
- `A.py` / `A.cpp` などの source files は作成・上書き・削除しない
- `.atc/current-contest.json` は更新しない

`atc refresh` は contest ディレクトリ内で実行してください。
contest を active にしたり、VS Code の分割ターミナルを起動したりはしません。

デフォルトでは確認が出ます。確認を省略する場合は `--yes` または `-y` を付けます。

tasks page の取得や parse に失敗した場合、`defaults.problems` には fallback せず終了します。

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
atc w
atc auto
```

ファイル保存を監視して、保存された1問の sample 結果を固定表示で更新します。

- 問題ファイルの変更を検知
- 保存された問題だけ再実行
- config やビルド関連ファイルが変わった場合は、直前に表示していた問題だけ再実行
- ログは `.atc/test-runs/last.log`
- 失敗ケースは `.atc/test-runs/last_failed.txt`

起動時の動き:

- `atc watch` は initial run をしません。保存された問題だけ実行します。
- `atc watch A01` のように明示した場合は、A01 だけ initial run し、保存時も A01 だけ実行します。
- `atc watch --all` と `atc watch all` は deprecated です。全問題をまとめて確認する場合は `atc test all` を使います。

起動直後は待機状態を表示します。

```text
Watching D:\atcoder\tessoku-book
Save a source file to run its samples.
```

この状態で `A01.py` を保存すると、A01 だけが実行され、sampleごとの結果テーブルが更新されます。

```text
Case          Result       Time
sample-1.in   AC        58.79 ms
sample-2.in   AC        57.40 ms
```

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
atc stress init A
atc stress promote A
atc stress promote A --name corner
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

`atc stress init A` は stress 用テンプレートから `A_gen.py` / `A_brute.py` だけを作ります。`A.py` / `A.cpp` は作らず、既存ファイルも上書きしません。

`atc stress promote A` は、最後に見つかった反例を通常テストへ昇格します。入力は `.atc/stress/A/failed.in`、期待出力は `.atc/stress/A/brute.out` を使い、`tests/A/stress-1.in` / `tests/A/stress-1.out` に保存します。既にある場合は `stress-2`, `stress-3`, ... の次の空き番号を使います。

名前を指定する場合:

```bash
atc stress promote A --name corner
atc t A
```

この場合は `tests/A/corner.in` / `tests/A/corner.out` に保存します。既存ファイルは上書きしません。上書きする場合だけ `--force` を付けます。

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
atc template list stress
atc template show py default
atc template show cpp acl
atc template show stress gen
atc template show stress brute
```

- `list`: manifest から利用可能なテンプレート名、説明、path を表示
- `list py` / `list cpp` / `list stress`: 指定カテゴリだけ表示
- `show <py|cpp|stress> <name>`: 指定テンプレートの本文を stdout に表示

## `atc config`

```bash
atc config init
atc config show
atc config doctor
```

- `init`: カレントディレクトリに `.atc/config.toml` を作成
- `show`: 現在読み込まれる config を表示
- `doctor`: Python、config、templates、runner、watch、`oj` と AtCoder login status、VS Code 連携、`current-contest.json` を診断

AtCoder に未ログインの場合は、次を実行してください。

```bash
oj login https://atcoder.jp/
```

ログイン確認だけしたい場合:

```bash
oj login --check https://atcoder.jp/
```

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
