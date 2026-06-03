# Development

開発者向けの構造メモです。ユーザー向けの使い方は `README.md` と `docs/USAGE.md` を見てください。

## Commit message rule

\<type>: <内容>

```text
feat:     新機能追加
fix:      バグ修正
refactor: 挙動を変えない整理・設計改善
remove:   不要機能や不要コードの削除
docs:     READMEやコメントだけ
test:     テスト追加・修正
chore:    設定・依存関係・雑務
style:    フォーマットだけ
```

## Module responsibilities

```text
cli.py        entrypoint / command dispatch
commands.py   command registry / aliases / usage
config.py     config.toml / path / runner / watch settings
console.py    colors and console helpers
models.py     CaseResult / ProblemResult
templates.py  template manifest and template resolution
template_commands.py template list/show CLI
samples.py    oj sample download
contest.py    atc new / atc contest
manual.py     atc manual
runner.py     atc run / test
stress.py     atc stress / stress promote
watch.py      atc watch
doctor.py     atc config doctor
visual.py     atc visual / vis
```

## 新機能を追加するときの置き場所

```text
新しいCLIコマンド -> commands.py + 専用module
config仕様変更 -> config.py
template仕様変更 -> templates.py
template CLI表示 -> template_commands.py
sample download -> samples.py
contest作成 -> contest.py
test実行 -> runner.py
stress test / stress init / stress promote -> stress.py
watch -> watch.py
doctor診断項目 -> doctor.py
visualizer起動 -> visual.py
表示色・console出力 -> console.py
共通データ構造 -> models.py
```

`cli.py` は薄い entrypoint として保ちます。新しい処理本体を `cli.py` に戻さないでください。

## 依存方向

循環 import を避けるため、基本の依存方向は次の通りです。

```text
cli.py / commands.py
  -> feature modules

feature modules
  -> config.py / console.py / models.py

config.py / models.py / console.py
  -> lower-level modules
```

避けたい例:

```text
config.py -> contest.py
runner.py -> watch.py
templates.py -> doctor.py
```

## リファクタ時のルール

- 挙動を変えない
- 先に `python -m compileall atc`
- 一時ディレクトリでコマンド確認
- visualizer.html と VS Code拡張は必要がない限り触らない
- 新コマンド追加と大規模リファクタを同時にやらない
- config 探索順、テンプレート探索順、出力文言、exit code を変える場合は明示的に扱う

## テスト例

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

## package-data / templates

`pyproject.toml` の package-data には、標準テンプレート、manifest 用テンプレート階層、配布用 visualizer asset を含めます。

```text
atc/templates/template.py
atc/templates/template.cpp
atc/templates/manifest.json
atc/templates/python/*.py
atc/templates/cpp/*.cpp
atc/templates/stress/*.py
atc/assets/visualizer.html
```

stress 用 generator / brute テンプレートは `atc/templates/stress/` に置き、manifest の `stress` section に登録します。`atc stress init A` はこのテンプレートから `A_gen.py` / `A_brute.py` だけを作ります。`atc stress promote A` は保存済みの `.atc/stress/A/failed.in` と `brute.out` を通常テスト `tests/A/*.in` / `*.out` へコピーします。

## visualizer assets

`visualizer.html` は `tools/visualizer.html` を本体として編集します。package 配布用には、同じ内容を `atc/assets/visualizer.html` にコピーします。

`atc visual` は開発環境では `tools/visualizer.html` を優先し、配布環境では `atc/assets/visualizer.html` を fallback として使います。2つの内容がズレると `tests/test_visual_assets.py` が失敗します。
