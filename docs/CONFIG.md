# Config

設定ファイルは TOML 形式の `.atc/config.toml` です。

## 探索順

CLI は次の順で config を探します。

1. 現在のディレクトリから親方向に `.atc/config.toml`
2. 見つからなければ `~/.atc/config.toml`
3. 見つからなければデフォルト設定

VS Code 拡張機能も workspace folder から親方向に `.atc/config.toml` を探します。見つからない場合は `~/.atc/config.toml` と fallback 探索を使います。

## 例

```toml
[paths]
root = "."
abc = "ABC"
arc = "ARC"
agc = "AGC"

[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"

[defaults]
language = "cpp"
problems = ["A", "B", "C", "D", "E"]

[runner]
python = "python"
pypy = "pypy"
cpp_compiler = "g++"
cpp_flags = ["-std=c++20", "-O2", "-Wall", "-Wextra"]
timeout_seconds = 2.0
compile_timeout_seconds = 10.0
```

## `[paths]`

### `paths.root`

AtCoder 用 root を指定します。

絶対パス推奨です。

```toml
[paths]
root = "/Users/friend/atcoder"
```

相対パスの場合は `.atc/config.toml` の project root 基準です。

```text
/Users/friend/atcoder/.atc/config.toml
```

この config に:

```toml
[paths]
root = "."
```

と書くと root は:

```text
/Users/friend/atcoder
```

になります。

```toml
[paths]
root = "contests"
```

なら:

```text
/Users/friend/atcoder/contests
```

になります。

`root = ""` の場合、`atc contest abc335` は現在のカレントディレクトリ直下に `abc335/` を作ります。

### `abc` / `arc` / `agc`

contest ID に応じたカテゴリフォルダです。

```toml
[paths]
root = "/Users/friend/atcoder"
abc = "ABC"
arc = "ARC"
agc = "AGC"
```

この場合:

```bash
atc contest abc335 cpp
```

は:

```text
/Users/friend/atcoder/ABC/abc335
```

を使います。

### root 直下に contest を置く

カテゴリ分けしない場合は空文字にします。

```toml
[paths]
root = "/Users/friend/atcoder"
abc = ""
arc = ""
agc = ""
```

この場合:

```text
/Users/friend/atcoder/abc335
/Users/friend/atcoder/arc180
```

のように root 直下に作ります。

## `[templates]`

問題ファイル作成時のテンプレートです。

```toml
[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"
```

ユーザーごとのテンプレートは project root の `templates/` に置くのを推奨します。

```text
<project-root>/templates/template.py
<project-root>/templates/template.cpp
```

テンプレートが見つからない場合は警告を出し、空ファイルを作ります。

## `[defaults]`

### `language`

作成言語のデフォルトです。

```toml
[defaults]
language = "cpp"
```

指定できる作成言語:

- `py`
- `cpp`

### `problems`

作成・取得・watch 対象の問題一覧です。

```toml
[defaults]
problems = ["A", "B", "C", "D", "E"]
```

F 以降を使う場合は増やしてください。

```toml
problems = ["A", "B", "C", "D", "E", "F"]
```

## `[runner]`

実行環境です。

```toml
[runner]
python = "python"
pypy = "pypy"
cpp_compiler = "g++"
cpp_flags = ["-std=c++20", "-O2", "-Wall", "-Wextra"]
timeout_seconds = 2.0
compile_timeout_seconds = 10.0
```

- `timeout_seconds`: テストケース実行時間
- `compile_timeout_seconds`: C++ コンパイル時間
- `python` が見つからない場合、CLI は `sys.executable` fallback を使います
- `pypy` が見つからない場合は分かりやすい ERROR を返します

## `[watch]`

`atc watch` の監視間隔です。任意設定なので、省略した場合はデフォルト値が使われます。

既に `.atc/config.toml` を作成済みの場合も、必ず追記する必要はありません。必要になった時だけ手動で `[watch]` を追記してください。

```toml
[watch]
poll_seconds = 0.25
debounce_seconds = 1.5
```

- `poll_seconds`: ファイル変更を確認する間隔です。推奨範囲は `0.1` 〜 `5.0` です。
- `debounce_seconds`: 変更検知後にテスト実行を待つ時間です。推奨範囲は `0.0` 〜 `10.0` です。

一部だけ指定した場合、指定していない値はデフォルトで補完されます。

```toml
[watch]
debounce_seconds = 2.0
```

この場合、`poll_seconds` はデフォルトの `0.25`、`debounce_seconds` は `2.0` になります。

値が不正な場合、`atc config doctor` で WARN を表示し、実行時は安全なデフォルト値に fallback します。

## VS Code 拡張機能との関係

VS Code 拡張機能は主に `[paths]` を読み、`.atc/current-contest.json` の場所を決めます。

config を変更した場合は、VS Code で `Developer: Reload Window` を実行するか、VS Code を再起動してください。
