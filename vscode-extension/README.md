# ATC Helper VS Code Extension

AtCoder 用の `atc` CLI を VS Code のサイドバーから操作する拡張機能です。

## できること

- コンテストフォルダ作成とサンプル取得
- A〜F のローカルテスト実行
- 問題ファイルの手動作成
- 実行ログの確認と処理停止

## 開発中に起動する

このリポジトリを VS Code で開き、実行とデバッグから `Run ATC VS Code Extension` を選びます。

新しい Extension Development Host が開いたら、左の Activity Bar にある `ATC` アイコンから操作パネルを開けます。

## 設定

| 設定 | 説明 |
| - | - |
| `atcHelper.pythonPath` | リポジトリ内の Python CLI を使うときの Python コマンドです。デフォルトは `python3` です。 |
| `atcHelper.cliPath` | インストール済みの `atc` コマンドを直接使いたい場合に指定します。空欄なら同じリポジトリ内の CLI を優先します。 |

## 前提

サンプル取得には、既存 CLI と同じく `online-judge-tools` の `oj` コマンドが必要です。
