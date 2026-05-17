# AI Context

このファイルは Codex / ChatGPT に読ませるための詳細仕様です。通常ユーザーは読む必要はありません。

## まず読むファイル

コード変更時にまず読むべきファイル:

- `docs/AI_CONTEXT.md`: AI向け仕様
- `docs/DEVELOPMENT.md`: モジュール構造と開発ルール
- `atc/cli.py`: entrypoint / command dispatch
- `atc/commands.py`: command registry / aliases / usage
- 変更対象の feature module

必要に応じて読むファイル:

- `docs/CONFIG.md`: config の詳細
- `docs/USAGE.md`: ユーザー向けコマンド説明
- `atc/config.py`: config / path / runner / watch settings
- `atc/templates.py`: template manifest / template resolution
- `atc/template_commands.py`: template list/show CLI 表示
- `atc/stress.py`: random stress test
- `vscode/atc-helper/src/extension.ts`: VS Code 拡張本体

## 概要

このリポジトリは AtCoder 用の Python CLI、VS Code 補助、visualizer を提供します。

- CLI: `atc/cli.py`
- Command registry: `atc/commands.py`
- VS Code 拡張: `vscode/atc-helper/src/extension.ts`
- Visualizer: `tools/visualizer.html`
- 連携ファイル: `.atc/current-contest.json`
- 設定ファイル: `.atc/config.toml`

## 現在のモジュール構成

```text
atc/
├── cli.py          # entrypoint / command dispatch
├── commands.py     # command registry / aliases / usage
├── config.py       # config.toml / path / runner / watch settings
├── console.py      # colors and console helpers
├── models.py       # CaseResult / ProblemResult
├── templates.py    # template / manifest handling
├── template_commands.py # atc template list/show
├── samples.py      # oj sample download
├── contest.py      # atc new / atc contest
├── manual.py       # atc manual
├── runner.py       # atc run / test / rerun
├── stress.py       # atc stress
├── watch.py        # atc watch
├── doctor.py       # atc config doctor
└── visual.py       # atc visual / vis
```

`cli.py` は dispatcher です。コマンド名、alias、usage、handler wrapper は `commands.py` に集約します。処理本体は feature module に置きます。

## 実装済みコマンド

- `atc new abc335 [py|cpp]`
- `atc contest abc335 [py|cpp]`
- `atc contests abc335 [py|cpp]`
- `atc run A [python|pypy|cpp]`
- `atc r A [python|pypy|cpp]`
- `atc test A [python|pypy|cpp]`
- `atc t A [python|pypy|cpp]`
- `atc run all [python|pypy|cpp]`
- `atc rerun [python|pypy|cpp]`
- `atc retry [python|pypy|cpp]`
- `atc stress A [py|cpp] [--count N] [--seed S] [--gen PATH] [--brute PATH] [--timeout SEC] [--compare exact|strip|tokens]`
- `atc watch [A|all] [python|pypy|cpp]`
- `atc w [A|all] [python|pypy|cpp]`
- `atc auto [A|all] [python|pypy|cpp]`
- `atc visual [--live-preview|--no-live-preview] [--live-preview-url URL] [--no-fallback] [--port PORT] [--no-open]`
- `atc vis [--live-preview|--no-live-preview] [--live-preview-url URL] [--no-fallback] [--port PORT] [--no-open]`
- `atc vizui [--live-preview|--no-live-preview] [--live-preview-url URL] [--no-fallback] [--port PORT] [--no-open]`
- `atc manual A B C [py|cpp]`
- `atc manual A~E [py|cpp]`
- `atc manual A-E [py|cpp]`
- `atc manual tests`
- `atc template list [py|cpp]`
- `atc template show <py|cpp> <name>`
- `atc config show`
- `atc config init`
- `atc config doctor`

未実装:

- `atc submit`
- `atc open`
- Marketplace 公開
- VS Code Tasks 自動生成

## 新機能追加時の編集場所

```text
新しいCLIコマンド -> commands.py + 専用module
config仕様変更 -> config.py
template仕様変更 -> templates.py
template CLI表示 -> template_commands.py
sample download -> samples.py
contest作成 -> contest.py
test実行 -> runner.py
stress test -> stress.py
watch -> watch.py
doctor診断項目 -> doctor.py
visualizer起動 -> visual.py
表示色・console出力 -> console.py
共通データ構造 -> models.py
```

## 触らない方がよいもの

必要がない限り触らない:

- `tools/visualizer.html`
- `vscode/atc-helper/`
- 既存コマンドの引数仕様
- config 探索順
- template 探索順
- 出力文言と exit code

## config 探索順

CLI:

1. cwd から親方向に `.atc/config.toml`
2. `~/.atc/config.toml`
3. デフォルト設定

VS Code 拡張:

1. workspace folder ごとに親方向へ `.atc/config.toml` を探す
2. 見つからない workspace がある場合は `~/.atc/config.toml` も候補
3. それも無ければ workspace 推定へ fallback

## root 解決仕様

`paths.root`:

- 空文字なら root 未指定
- 絶対パスならそのまま
- `~` は home に展開
- 相対パスなら `.atc/config.toml` の project root 基準

`.atc/config.toml` の project root は `.atc` の親ディレクトリです。

`atc contest abc335 cpp` の場合:

- `paths.root` が空: `cwd/abc335`
- `paths.root` があり `paths.abc` がある: `root/paths.abc/abc335`
- `paths.root` があり `paths.abc = ""`: `root/abc335`

## templates

標準テンプレート:

- `atc/templates/template.py`
- `atc/templates/template.cpp`

manifest 対応済みです。

```toml
[templates]
manifest = "templates/manifest.json"
py = "fast"
cpp = "acl"
```

テンプレート本文は JSON に入れず、`.py` / `.cpp` ファイルとして管理します。従来の直接パス指定も維持します。

```toml
[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"
```

manifest が明示されていて壊れている場合、`atc config doctor` では ERROR として表示します。

## runner / watch

`runner.py` は `run / test / rerun` を担当します。

- Python / PyPy 実行
- C++ compile
- AC / WA / RE / TLE / CE / NO_TESTS / ERROR 判定
- `.atc/test-runs/last.log`
- `.atc/test-runs/last_failed.txt`

`watch.py` はファイル変更検知、debounce、runner 呼び出しを担当します。

## stress

`atc stress` は `stress.py` が担当します。

- `A.py` / `A.cpp` と `A_gen.py` / `A_brute.py` を使う
- generator / brute は Python 固定
- seed は generator の argv に渡す
- compare mode は `exact` / `strip` / `tokens`
- 不一致時は `.atc/stress/<problem>/` に `failed.in`、`your.out`、`brute.out`、`meta.json` を保存

## visual

`atc visual` / `atc vis` / `atc vizui` は `visual.py` が担当します。

デフォルトでは VS Code Live Preview URL を優先します。

```text
http://127.0.0.1:3000/tools/visualizer.html?vscode-livepreview=true
```

Live Preview が使えない場合はローカルHTTPサーバーに fallback します。Live Preview を使わない場合は `--no-live-preview` を指定します。

## current-contest.json

`atc contest` は contest 作成または既存確認後に `.atc/current-contest.json` を書きます。

保存先:

- `paths.root` がある: `<resolved-root>/.atc/current-contest.json`
- `paths.root` が空: project root 推定結果の `.atc/current-contest.json`

形式:

```json
{
  "contestDir": "/absolute/path/to/abc335",
  "requestId": "2026-05-10T12:34:56.789",
  "createdAt": "2026-05-10T12:34:56.789"
}
```

VS Code 拡張は `requestId` で重複処理を避けます。

## VS Code watcher 仕様

VS Code 拡張は起動時に watcher を登録しますが、既存の `current-contest.json` を読んで即 terminal を開くことはしません。

terminal が開く条件:

- `current-contest.json` が作成または変更された
- Command Palette の `AtC: Open Contest Terminals` を手動実行した

開く terminal:

- 左: `atc terminal`
- 右: `atc watch`

## config doctor

`atc config doctor` は `doctor.py` が担当します。

確認項目:

- Python executable / version
- `atc` command が PATH にあるか
- 読み込まれる config file
- resolved root
- `paths.abc` / `paths.arc` / `paths.agc`
- Python / C++ templates
- runner.python / runner.pypy / runner.cpp_compiler / timeouts
- watch settings
- `oj`
- VS Code `code` command
- VS Code extension `kouki.atc-helper`
- `<resolved-root>/.atc/current-contest.json`

終了コード:

- ERROR が 0 個なら exit 0
- ERROR が 1 個以上なら exit 1
- WARN だけなら exit 0

## よく使う確認コマンド

```bash
python -m compileall atc
atc config show
atc config doctor
atc visual --no-open
atc vis --no-live-preview --no-open
```

一時ディレクトリで:

```bash
atc manual A py
atc run A py
atc watch A py
```

VS Code 拡張を触った場合だけ:

```bash
cd vscode/atc-helper
npm run compile
```

## Codex に依頼するときの注意

- まず `docs/AI_CONTEXT.md` と `docs/DEVELOPMENT.md` を読むこと
- 実装済みでない機能を README に実装済みとして書かないこと
- 既存コマンドの挙動を壊さないこと
- CLI と VS Code 拡張の root 解決がズレないようにすること
- config が無い場合の既存動作を維持すること
- 新コマンド追加と大規模リファクタを同時にやらないこと
