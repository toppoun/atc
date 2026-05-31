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

[paths.contests]
"abc\\d+" = "ABC"
"arc\\d+" = "ARC"
"agc\\d+" = "AGC"
"adt_.*" = "ATD"

[templates]
manifest = "templates/manifest.json"
py = "fast"
cpp = "acl"

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

[watch]
poll_seconds = 0.25
debounce_seconds = 1.5
```

## `[paths]`

### `paths.root`

AtCoder 用 root を指定します。

```toml
[paths]
root = "/Users/friend/atcoder"
```

相対パスの場合は `.atc/config.toml` の project root 基準です。

```toml
[paths]
root = "."
```

この config が `/Users/friend/atcoder/.atc/config.toml` にある場合、root は `/Users/friend/atcoder` になります。

`root = ""` の場合、`atc contest abc335` は現在のカレントディレクトリ直下に `abc335/` を作ります。

### `paths.contests`

contest ID に応じたカテゴリフォルダを正規表現で指定できます。
上から順に `re.fullmatch()` で照合し、最初に一致したルールを使います。

```toml
[paths]
root = "/Users/friend/atcoder"

[paths.contests]
"abc\\d+" = "ABC"
"arc\\d+" = "ARC"
"agc\\d+" = "AGC"
"adt_.*" = "ATD"
```

この場合、`atc contest abc335 cpp` は `/Users/friend/atcoder/ABC/abc335` を使い、`atc contest adt_all_20260525_1 cpp` は `/Users/friend/atcoder/ATD/adt_all_20260525_1` を使います。

どのルールにも一致しない contest ID は root 直下に作られます。

## `[templates]`

問題ファイル作成時のテンプレートです。

### manifest 方式

```toml
[templates]
manifest = "templates/manifest.json"
py = "fast"
cpp = "acl"
```

`py` / `cpp` には manifest 内のテンプレート名を指定できます。テンプレート本文は JSON ではなく `.py` / `.cpp` ファイルとして管理します。

例:

```text
templates/
├── manifest.json
├── python/
│   ├── default.py
│   └── fast.py
└── cpp/
    ├── default.cpp
    └── acl.cpp
```

manifest が壊れている場合、`atc config doctor` は ERROR を表示します。

### 従来の直接パス指定

従来通り、テンプレートファイルを直接指定できます。

```toml
[templates]
py = "templates/template.py"
cpp = "templates/template.cpp"
```

テンプレートが見つからない場合は警告を出し、空ファイルを作ります。

## `[defaults]`

### `defaults.language`

作成言語のデフォルトです。

```toml
[defaults]
language = "cpp"
```

指定できる作成言語:

- `py`
- `cpp`

### `defaults.problems`

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

- `runner.python`: Python 実行コマンド。見つからない場合は `sys.executable` fallback
- `runner.pypy`: PyPy 実行コマンド。見つからない場合は ERROR
- `runner.cpp_compiler`: C++ compiler
- `runner.cpp_flags`: C++ compile flags
- `runner.timeout_seconds`: テストケース実行時間
- `runner.compile_timeout_seconds`: C++ コンパイル時間

## `[watch]`

`atc watch` の監視間隔です。省略した場合はデフォルト値が使われます。

```toml
[watch]
poll_seconds = 0.25
debounce_seconds = 1.5
```

- `watch.poll_seconds`: ファイル変更を確認する間隔。推奨範囲は `0.1` 〜 `5.0`
- `watch.debounce_seconds`: 変更検知後にテスト実行を待つ時間。推奨範囲は `0.0` 〜 `10.0`

一部だけ指定した場合、指定していない値はデフォルトで補完されます。

```toml
[watch]
debounce_seconds = 2.0
```

値が不正な場合、`atc config doctor` で WARN を表示し、実行時は安全なデフォルト値に fallback します。

## VS Code 拡張機能との関係

VS Code 拡張機能は主に `[paths]` を読み、`.atc/current-contest.json` の場所を決めます。

config を変更した場合は、VS Code で `Developer: Reload Window` を実行するか、VS Code を再起動してください。
