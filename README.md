# atc
AtCoder の問題用フォルダ作成、サンプル取得、ローカルテスト実行を簡単にするためのコマンドラインツールです。

## 機能
- AtCoder のコンテスト用フォルダを作成
- A〜E 問題のファイルを自動作成
- `templates/template.py` または `templates/template.cpp` からテンプレートを読み込み
- `online-judge-tools` を使ってサンプルケースを自動取得
- Python / PyPy / C++ のローカルテスト実行
- 手動で問題ファイルを追加作成

## 必要なもの

Python 3 が必要です。

サンプル取得には `online-judge-tools` を使います。

## 使い方
```Bash
atc new abc413
```
デフォルトではcppファイルが生成されます

```
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

## コマンド一覧
| コマンド | 説明 |
| - | - |
| `atc new abc413` | abc413 フォルダを作成し、A〜E の C++ ファイルとサンプルを取得 |
| `atc run A` | A問題をテスト実行 |
| `atc manual A B C` | A.py, B.py, C.py を手動作成 |
| `atc manual A-E` | A.py 〜 E.cpp を手動作成 |

## 注意点
- `atc new` は A〜E 問題を対象にしています。
- `atc run` は、現在のフォルダにある `A.py` または `A.cpp` を実行します。
- Python ファイルと C++ ファイルの両方がある場合、C++ が優先されます。

## 使用例
```Bash
atc new abc413
cd abc413
atc run A
```
