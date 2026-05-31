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

contest ID に応じたカテゴリフォルダを決める regex map です。
上から順に `re.fullmatch(pattern, contest_id.lower())` で照合し、最初に一致した保存先を使います。
どのルールにも一致しない contest ID は root 直下に作られます。

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

`"abc\\d+"` は Python の正規表現としては `abc\d+` です。TOML 文字列内では `\` をエスケープするため、`\\d+` と書きます。

例:

```text
abc460             -> "abc\\d+" に一致
abc460_extra       -> "abc\\d+" に一致しない
adt_all_20260525_1 -> "adt_.*" に一致
```

不正な正規表現はエラーになります。

```toml
[paths.contests]
"abc(" = "ABC"
```

```text
Error: invalid contest path regex: abc(
```

## `[templates]`

問題ファイル作成時のテンプレートです。

### manifest 方式の応用例

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

問題一覧を自動解決できない場合の最後の fallback です。

```toml
[defaults]
problems = ["A", "B", "C", "D", "E"]
```

`atc contest` / `atc c` は AtCoder の tasks ページから取得した問題一覧を `.atc/contest.toml` に保存します。
`atc run all` と `atc watch` は、通常はその metadata の `[[problems]]` を優先し、metadata がない場合は `A.py` / `A.cpp` など実在する source files から対象を推測します。
`defaults.problems` は metadata も source files もない場合だけ使われます。

`atc manual tests` も metadata がある場合は `[[problems]].url` を使います。
metadata がない場合は source files または `defaults.problems` の問題記号から従来どおり URL を推測します。

古い contest フォルダや手動作成フォルダで F 以降を fallback 対象にしたい場合は増やしてください。

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

VS Code 拡張機能は主に `[paths].root` と `[paths.contests]` を読み、`.atc/current-contest.json` の場所を決めます。

config を変更した場合は、VS Code で `Developer: Reload Window` を実行するか、VS Code を再起動してください。
