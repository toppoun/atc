# atc

AtCoder の問題用フォルダ作成、サンプル取得、ローカルテスト実行を簡単にするためのコマンドラインツールです。

## 機能

- AtCoder のコンテスト用フォルダを作成
- A〜E 問題のファイルを自動作成
- `templates/template.py` または `templates/template.cpp` からテンプレートを読み込み
- `online-judge-tools` を使ってサンプルケースを自動取得
- Python / PyPy / C++ のローカルテスト実行
- ファイル保存後に関連する問題だけを自動テスト
- 手動で問題ファイルを追加作成

## 必要なもの

Python 3 が必要です。

サンプル取得には `online-judge-tools` を使います。

## 使い方

```Bash
atc new abc413
```

デフォルトではcppファイルが生成されます

```Bash
abc413/
├── A.cpp
├── B.cpp
├── C.cpp
├── D.cpp
├── E.cpp
└── tests/
    ├── A/
    ├── B/
    ├── C/
    ├── D/
    └── E/
```

Pythonで作成したい場合は、最後に `py` を指定します。

## テンプレート

テンプレートファイルは `templates` フォルダに置きます。

Python用: `templates/template.py`

C++用: `templates/template.cpp`

## テスト実行

作成したコンテストフォルダに移動します。

```Bash
cd abc413
```

A 問題を実行する場合：

```Bash
atc run a
```

短縮コマンドも使えます。

```Bash
atc r A
atc test A
atc t A
```

全問題をまとめて確認する場合：

```Bash
atc run all
```

直前に失敗したケースだけを再実行する場合：

```Bash
atc rerun
```

## 自動テスト

編集中にテストを自動実行したい場合は、コンテストフォルダで `watch` を使います。

```Bash
atc watch
```

起動時に一度テストを実行し、その後は A〜E のソースファイルと `tests` フォルダを監視します。

- `A.py` または `A.cpp` が変わったら A 問題だけ実行
- `tests/A` のサンプルが変わったら A 問題だけ実行
- `pyproject.toml` や `requirements.txt` などの設定ファイルが変わったら、検出できる問題をまとめて実行
- 変更直後には実行せず、1.5 秒待ってから実行

特定の問題だけ監視することもできます。

```Bash
atc watch A
```

PyPy で実行したい場合：

```Bash
atc watch A pypy
```

自動テストではターミナルに詳細ログを流し続けず、結果の要約だけを表示します。

```Text
PASS A: 3 tests in 0.42s
Full log: .atc/test-runs/last.log
```

失敗時もターミナルには失敗したケースの一覧だけを出します。期待値、出力、エラー内容などの詳細は `.atc/test-runs/last.log` に保存されます。

## 手動で問題ファイルを作成する

現在のフォルダに A.py, B.py, C.py を作成する場合：

```Bash
atc manual A B C
```

範囲指定もできます。

```Bash
atc manual A-E
```

または

```Bash
atc manual A~E
```

現在のコンテストフォルダ名からサンプルケースだけ取得する場合：

```Bash
atc manual tests
```

## コマンド一覧

| コマンド | 説明 |
| - | - |
| `atc new abc413` | abc413 フォルダを作成し、A〜E の C++ ファイルとサンプルを取得 |
| `atc run A` | A問題をテスト実行 |
| `atc run all` | 検出できる問題をまとめてテスト実行 |
| `atc rerun` | 直前に失敗したケースだけ再実行 |
| `atc watch` | 変更された問題を自動テスト |
| `atc watch A` | A問題だけを監視して自動テスト |
| `atc manual A B C` | A.py, B.py, C.py を手動作成 |
| `atc manual A-E` | A.py 〜 E.cpp を手動作成 |
| `atc manual tests` | 現在のフォルダ名をコンテストIDとしてサンプルを取得 |

## 注意点

- `atc new` は A〜E 問題を対象にしています。
- `atc run` は、現在のフォルダにある `A.py` または `A.cpp` を実行します。
- `atc watch` は、現在のフォルダにある A〜E のソースと `tests/A` 〜 `tests/E` を監視します。
- Python ファイルと C++ ファイルの両方がある場合、C++ が優先されます。

## 使用例

```Bash
atc new abc413
cd abc413
atc run A
atc watch A
```
