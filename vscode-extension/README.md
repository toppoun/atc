# ATC Helper VS Code Extension

AtCoder 用の `atc` CLI を VS Code のサイドバーから操作する拡張機能です。

## できること

- コンテストフォルダ作成とサンプル取得
- A〜F のローカルテスト実行
- A〜F ボタンからのワンクリックテスト実行
- 問題ファイルの手動作成
- `ABC(Atcoder Beginner Contest)` や `typical90` などのカテゴリ別フォルダ切り替え
- 実行ログの確認と処理停止

## 開発中に起動する

このリポジトリを VS Code で開き、実行とデバッグから `Run ATC VS Code Extension` を選びます。

新しい Extension Development Host が開いたら、左の Activity Bar にある `ATC` アイコンから操作パネルを開けます。

## 作業場所を切り替える

操作パネル上部の `基準フォルダ` から、ワークスペース直下のカテゴリフォルダを選べます。

たとえば `atcoder-submittion` を VS Code で開いている場合、`ABC(Atcoder Beginner Contest)`、`typical90`、`過去問精選 100問` などを選ぶと、そのフォルダ内を基準にしてコンテスト作成やテスト実行を行います。

一覧に出ない場所を使いたいときは `選択` から任意のフォルダを選べます。

## すばやくテストする

`コンテスト名` に `abc413` などを入れておくと、`作成` も `テストケース実行` も同じコンテスト名を使います。

コンテスト名は保持されるので、操作パネルから離れて戻っても入力し直す必要はありません。A〜F のボタンを押すと、その問題をすぐに実行できます。

## 設定

| 設定 | 説明 |
| - | - |
| `atcHelper.pythonPath` | リポジトリ内の Python CLI を使うときの Python コマンドです。デフォルトは `python3` です。 |
| `atcHelper.cliPath` | インストール済みの `atc` コマンドを直接使いたい場合に指定します。空欄なら同じリポジトリ内の CLI を優先します。 |

## 前提

サンプル取得には、既存 CLI と同じく `online-judge-tools` の `oj` コマンドが必要です。
