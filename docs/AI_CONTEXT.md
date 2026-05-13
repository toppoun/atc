# AI Context

このファイルは Codex / ChatGPT に読ませるための詳細仕様です。通常ユーザーは読む必要はありません。

## まず読むファイル

- `README.md`: 人間向けの概要
- `docs/AI_CONTEXT.md`: AI向け仕様
- `docs/CONFIG.md`: config の詳細
- `docs/DEVELOPMENT.md`: 開発手順
- `atc/cli.py`: Python CLI 本体
- `vscode/atc-helper/src/extension.ts`: VS Code 拡張本体

## 概要

このリポジトリは AtCoder 用の Python CLI と VS Code 拡張機能です。

- CLI: `atc/cli.py`
- VS Code 拡張: `vscode/atc-helper/src/extension.ts`
- 連携ファイル: `.atc/current-contest.json`
- 設定ファイル: `.atc/config.toml`

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
- `atc watch [A] [python|pypy|cpp]`
- `atc visual [--port PORT] [--no-open]`
- `atc vis [--port PORT] [--no-open]`
- `atc vizui [--port PORT] [--no-open]`
- `atc manual A B C [py|cpp]`
- `atc manual A~E [py|cpp]`
- `atc manual tests`
- `atc config show`
- `atc config init`
- `atc config doctor`

未実装:

- `atc submit`
- `atc open`
- Marketplace 公開
- VS Code Tasks 自動生成

## config 探索順

CLI:

1. cwd から親方向に `.atc/config.toml`
2. `~/.atc/config.toml`
3. デフォルト設定

VS Code 拡張:

1. workspace folder ごとに親方向へ `.atc/config.toml` を探し、最初に見つかったものを使う
2. 見つからない workspace がある場合は `~/.atc/config.toml` も候補
3. それも無ければ workspace 推定へ fallback

## root 解決仕様

`paths.root`:

- 空文字なら root 未指定
- 絶対パスならそのまま
- `~` は home に展開
- 相対パスなら `.atc/config.toml` の project root 基準

`.atc/config.toml` の project root は `.atc` の親ディレクトリ。

例:

```text
/Users/friend/atcoder/.atc/config.toml
```

```toml
[paths]
root = "."
```

root:

```text
/Users/friend/atcoder
```

## watch config

`[watch]` は任意設定。既存ユーザーの `.atc/config.toml` に無くても、`load_config()` の default config と deep merge で補完される。

デフォルト:

```toml
[watch]
poll_seconds = 0.25
debounce_seconds = 1.5
```

- `poll_seconds`: 推奨範囲 `0.1` 〜 `5.0`
- `debounce_seconds`: 推奨範囲 `0.0` 〜 `10.0`

一部だけ指定された場合、未指定キーは default で補完する。値が不正な場合は `atc config doctor` で WARN を出し、`atc watch` 実行時は安全な default に fallback する。既存 config を勝手に書き換えない。

```toml
root = "contests"
```

root:

```text
/Users/friend/atcoder/contests
```

## contest dir 解決

`atc contest abc335 cpp` の場合:

- `paths.root` が空: `cwd/abc335`
- `paths.root` があり `paths.abc` がある: `root/paths.abc/abc335`
- `paths.root` があり `paths.abc = ""`: `root/abc335`

`arc` / `agc` も同様。

`atc new` は現在の cwd 基準の新規作成コマンドとして残す。

## current-contest.json

`atc contest` は contest 作成または既存確認後に `.atc/current-contest.json` を書く。

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

- `contestDir` は絶対パス
- `requestId` は毎回更新
- VS Code 拡張は `requestId` で重複処理を避ける

## VS Code watcher 仕様

VS Code 拡張は起動時に watcher を登録するが、既存の `current-contest.json` を読んで即 terminal を開くことはしない。

terminal が開く条件:

- `current-contest.json` が作成または変更された
- Command Palette の `AtC: Open Contest Terminals` を手動実行した

開く terminal:

- 左: `atc terminal`
- 右: `atc watch`

watcher 候補:

- config root の `.atc/current-contest.json`
- workspace folder 直下
- workspace folder の親1〜2階層
- workspace folder 配下の浅い階層
  - `<workspace>/.atc/current-contest.json`
  - `<workspace>/*/.atc/current-contest.json`
  - `<workspace>/*/*/.atc/current-contest.json`

固定カテゴリ名 `ABC(Atcoder Beginner Contest)` などは後方互換 fallback。config がある場合は config root を優先する。

## テンプレート

標準テンプレート:

- `atc/templates/template.py`
- `atc/templates/template.cpp`

`pyproject.toml` の package-data に含める。

ユーザーごとのテンプレートは `templates/` に置き、`[templates]` で指定する。

## runner

`[runner]`:

- `python`
- `pypy`
- `cpp_compiler`
- `cpp_flags`
- `timeout_seconds`
- `compile_timeout_seconds`

Python 実行で `runner.python` が見つからない場合は `sys.executable` fallback。

PyPy 実行を指定していて見つからない場合は ERROR。

C++ 実行で compiler が見つからない場合は ERROR。

## config doctor

`atc config doctor` は配布先の環境確認用コマンド。

確認項目:

- Python executable / version
- `atc` command が PATH にあるか
- 読み込まれる config file
- resolved root
- `paths.abc` / `paths.arc` / `paths.agc`
- Python / C++ templates
- runner.python / runner.pypy / runner.cpp_compiler / timeouts
- `oj`
- VS Code `code` command
- VS Code extension `kouki.atc-helper`
- `<resolved-root>/.atc/current-contest.json`

終了コード:

- ERROR が 0 個なら exit 0
- ERROR が 1 個以上なら exit 1
- WARN だけなら exit 0

doctor では、PyPy / C++ compiler / `oj` / VS Code `code` command が無い場合は WARN 扱い。
実際にその runner や機能を使うコマンドでは ERROR になり得る。

## 既知の制限

- VS Code 拡張は主に `[paths]` だけを読む
- config 変更後は VS Code reload 推奨
- `atc submit` は未実装
- `atc open` は未実装
- ADT や tessoku など特殊 URL 形式の完全対応は未実装
- VS Code Marketplace には未公開
- 既存 terminal 再利用は未実装。現在は実行ごとに terminal を作る

## 今後の TODO

優先度高:

- `atc status`
- tests 再取得コマンド
- VS Code terminal 再利用

優先度中:

- `atc open A`
- config validation 強化
- doctor 結果の copy 用出力

後回し:

- `atc submit`
- VS Code Tasks 連携
- Marketplace 公開

## Codex に依頼するときの注意

- まず `docs/AI_CONTEXT.md` を読んでから作業すること
- 実装済みでない機能を README に実装済みとして書かないこと
- 既存コマンドの挙動を壊さないこと
- CLI と VS Code 拡張の root 解決がズレないようにすること
- config が無い場合の既存動作を維持すること
- 変更後は以下を確認すること
  - `python -m compileall atc`
  - `cd vscode/atc-helper && npm run compile`
  
